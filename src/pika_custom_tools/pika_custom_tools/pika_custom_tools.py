import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

import serial
import struct
import re  # 고속 데이터 추출을 위한 정규표현식
import json  # JSON 파싱
import threading
import time
import math
import numpy as np
import os
from queue import Queue, Empty

from sensor_msgs.msg import Imu, JointState
from geometry_msgs.msg import Quaternion
from std_srvs.srv import Trigger
from data_msgs.msg import Gripper, CaptureStatus, TeleopStatus, LocalizationStatus, ArmControlStatus
from data_msgs.srv import CaptureService

class SendFlag:
    DISABLE = 10; ENABLE = 11; SET_ZERO = 12
    VELOCITY_CTRL = 13; EFFORT_CTRL = 15
    POSITION_CTRL_MIT = 22; POSITION_CTRL_POS_VEL = 23
    LIGHT_CTRL = 50; VIBRATE_CTRL = 51

class Color:
    WHITE = 0; RED = 1; GREEN = 2; BLUE = 3; YELLOW = 4; SIZE = 5

class Vibrate:
    NONE = 0; ONE = 1; SIZE = 2

class RosOperator(Node):
    def __init__(self):
        super().__init__('pika_high_speed_operator')
        self.get_logger().info('Initializing Pika High-Speed Operator...')

        self.callback_group = ReentrantCallbackGroup()

        # 1. Parameters & Constants
        self.declare_parameter("serial_port", "/dev/ttyUSB0")
        self.serial_port_name = self.get_parameter("serial_port").value
        self.declare_parameter("joint_name", "center_joint")
        self.joint_name = self.get_parameter("joint_name").value
        self.declare_parameter("ctrl_rate", 100.0)
        self.ctrl_freq = 1.0 / self.get_parameter("ctrl_rate").value
        self.declare_parameter("mit_mode", True)
        self.mit_mode = self.get_parameter("mit_mode").value

        # 2. 정규표현식 엔진 (AS5047의 rad와 Motor의 Position 동시 지원)
        self.rad_pattern = re.compile(b'"rad":\s*([-+]?\d*\.\d+|\d+)')
        self.pos_pattern = re.compile(b'"Position":\s*([-+]?\d*\.\d+|\d+)')
        self.cmd_pattern = re.compile(b'"Command":\s*(\d+)')
        self.status_pattern = re.compile(b'"Status":\s*"0x([0-9A-Fa-f]{2})')

        # 3. Kinematics & LUT
        self._dist_zero = self.get_distance(0.0)
        self._init_lut()

        # 4. State Variables
        self.running = True
        self.enable = False  # 시작 시 False, motorstatus에서 업데이트
        self.distance = 0.0
        self.angle = 0.0
        self.command_id = -1
        self._last_ctrl_time = 0.0
        self.serial_queue = Queue(maxsize=10) # 최신 명령 우선

        # 5. Serial Connection
        try:
            self.serial = serial.Serial(port=self.serial_port_name, baudrate=460800, timeout=0)
            self.get_logger().info(f"[SERIAL] Connected to {self.serial_port_name}")
        except Exception as e:
            self.get_logger().error(f"Serial Error: {e}"); return

        # 6. Pub/Sub/Services Setup
        qos = QoSProfile(reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST, depth=1)
        self.pub_gripper = self.create_publisher(Gripper, "gripper/data", qos)
        self.pub_js = self.create_publisher(JointState, "gripper/joint_state", qos)
        
        self.sub_js_ctrl = self.create_subscription(JointState, "gripper/joint_state_ctrl", self.joint_state_ctrl_handler, qos, callback_group=self.callback_group)
        self.client_teleop = self.create_client(Trigger, "teleop_trigger", callback_group=self.callback_group)
        self.client_capture = self.create_client(CaptureService, "data_tools_dataCapture/capture_service", callback_group=self.callback_group)

        # 7. Threads
        threading.Thread(target=self.receiving_thread, daemon=True).start()
        threading.Thread(target=self.serial_sending_thread, daemon=True).start()

    def get_distance(self, angle):
        """그리퍼 기구학 (Forward Kinematics)"""
        theta = (136.01 / 180.0) * math.pi - angle
        height = 0.0325 * math.sin(theta)
        term = max(0, (0.058**2) - (height - 0.01456)**2)
        return math.sqrt(term) + 0.0325 * math.cos(theta)

    def _init_lut(self):
        self._lut_angles = np.linspace(0.0, 1.67, 2000)
        self._lut_widths = np.array([self.get_distance(a) for a in self._lut_angles])

    def get_angle_from_width(self, target_width):
        return float(np.interp(target_width, self._lut_widths, self._lut_angles))

    def serial_sending_thread(self):
        while self.running:
            try:
                data = self.serial_queue.get(timeout=0.01)
                if self.serial.is_open: self.serial.write(data)
            except Empty: continue

    def send_serial_cmd(self, cmd, values):
        packed = bytearray([cmd])
        for v in values: packed.extend(struct.pack('<f', float(v)))
        packed.extend(b'\r\n')
        try: self.serial_queue.put_nowait(bytes(packed))
        except: pass

    def joint_state_ctrl_handler(self, msg):
        """Teleoperation: 수신된 목표 위치를 시리얼 명령으로 즉시 변환"""
        now = time.time()
        if now - self._last_ctrl_time < self.ctrl_freq: return
        self._last_ctrl_time = now

        if not self.enable:
            self.send_serial_cmd(SendFlag.ENABLE, [0.0]); return

        pos = msg.position[-1] if msg.position else 0.0
        pos = max(0.0, min(pos, 0.098))
        target_width = pos * 0.5 + self._dist_zero-0.005
        angle = self.get_angle_from_width(target_width)
        angle = max(0.0, min(angle, 1.67))  # 각도 범위 제한
        
        flag = SendFlag.POSITION_CTRL_MIT if self.mit_mode else SendFlag.POSITION_CTRL_POS_VEL
        self.send_serial_cmd(flag, [angle])

    def receiving_thread(self):
        """초고속 Regex 전용 샘플링"""
        buffer = b""
        stats_count = 0
        last_stats_time = time.time()

        while self.running:
            if not self.serial.is_open:
                time.sleep(0.1); continue
            try:
                wait = self.serial.in_waiting
                if wait > 0:
                    buffer += self.serial.read(wait)
                else:
                    time.sleep(0.0001); continue

                if len(buffer) > 2000: buffer = buffer[-1000:]

                # ⚡ Regex 추출
                rad_matches = self.rad_pattern.findall(buffer)
                pos_matches = self.pos_pattern.findall(buffer)
                status_matches = self.status_pattern.findall(buffer)

                # Position 발행
                latest_rad = float(rad_matches[-1]) if rad_matches else None
                latest_pos = float(pos_matches[-1]) if pos_matches else None
                active_val = latest_rad if latest_rad is not None else latest_pos
                
                if active_val is not None:
                    self.angle = active_val
                    self.distance = 2.0 * (self.get_distance(active_val) - self._dist_zero)
                    ts = self.get_clock().now().to_msg()
                    js = JointState()
                    js.header.stamp, js.name = ts, [self.joint_name]
                    js.position = [float(self.distance)]
                    self.pub_js.publish(js)
                    stats_count += 1
                    buffer = b""

                # Enable 상태 업데이트
                if status_matches:
                    status_hex = status_matches[-1].decode('ascii')
                    status_byte = int(status_hex, 16)
                    self.enable = bool(status_byte & 0x40)

            except Exception: pass

            if (time.time() - last_stats_time) > 2.0:
                self.get_logger().info(f"📡 {stats_count/2.0:.1f}Hz | Enable:{self.enable}")
                stats_count = 0; last_stats_time = time.time()

    def destroy_node(self):
        self.running = False
        if hasattr(self, 'serial'): self.serial.close()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = RosOperator()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()