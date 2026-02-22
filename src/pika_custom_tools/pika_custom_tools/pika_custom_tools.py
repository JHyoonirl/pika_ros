import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

import serial
import struct
import json
import threading
import time
import math
import numpy as np
import os

from sensor_msgs.msg import Imu, JointState
from geometry_msgs.msg import Quaternion
from std_srvs.srv import Trigger, SetBool
from data_msgs.msg import (
    Gripper, CaptureStatus, TeleopStatus, 
    LocalizationStatus, ArmControlStatus
)
from data_msgs.srv import CaptureService

# --- Enums ---
class SendFlag:
    DISABLE = 10
    ENABLE = 11
    SET_ZERO = 12
    VELOCITY_CTRL = 13
    EFFORT_CTRL = 15
    POSITION_CTRL_MIT = 22
    POSITION_CTRL_POS_VEL = 23
    LIGHT_CTRL = 50
    VIBRATE_CTRL = 51

class Color:
    WHITE = 0; RED = 1; GREEN = 2; BLUE = 3; YELLOW = 4; SIZE = 5

class Vibrate:
    NONE = 0; ONE = 1; SIZE = 2

# --- Helper Functions ---

def euler_to_quaternion(roll, pitch, yaw):
    """Euler angles (RPY) to Quaternion (x, y, z, w)"""
    qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
    qz = np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.cos(pitch/2) * np.min(yaw/2)
    qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    return Quaternion(x=float(qx), y=float(qy), z=float(qz), w=float(qw))

def find_json(msg):
    """인덱스 기반 최적화된 JSON 객체 찾기"""
    start = msg.find('{')
    if start == -1: return False, -1, -1
    
    stack = 0
    for i in range(start, len(msg)):
        if msg[i] == '{':
            stack += 1
        elif msg[i] == '}':
            stack -= 1
            if stack == 0:
                return True, start, i
    return False, -1, -1

class RosOperator(Node):
    def __init__(self):
        super().__init__('serial_gripper_imu')
        self.get_logger().info('Optimized RosOperator Node Starting...')

        # 병렬 처리를 위한 콜백 그룹
        self.callback_group = ReentrantCallbackGroup()

        # Parameters
        self.declare_parameter("serial_port", "/dev/ttyUSB0")
        self.serial_port_name = self.get_parameter("serial_port").value
        self.declare_parameter("joint_name", "center_joint")
        self.joint_name = self.get_parameter("joint_name").value
        self.declare_parameter("motor_current_limit", 1000.0)
        self.motor_current_limit = self.get_parameter("motor_current_limit").value
        self.declare_parameter("ctrl_rate", 50.0)
        self.ctrl_rate = self.get_parameter("ctrl_rate").value
        self.declare_parameter("mit_mode", True)
        self.mit_mode = self.get_parameter("mit_mode").value

        self.ctrl_freq = 1.0 / self.ctrl_rate
        self._last_ctrl_time = 0.0
        self._last_grip_time = 0.0

        # IK Look-up Table 초기화 (O(1) 연산을 위함)
        self._init_ik_lut()

        # Serial & Environment Setup
        if os.path.islink(self.serial_port_name):
            self.serial_port_name = os.path.realpath(self.serial_port_name)

        pika_r = os.environ.get("pika_R_code", "")
        pika_l = os.environ.get("pika_L_code", "")
        self.frame_id = "right_hand" if pika_r else ("left_hand" if pika_l else "gripper_link")

        # State Variables
        self.effort, self.velocity, self.angle, self.distance = -1.0, -1.0, 0.0, 0.0
        self.voltage, self.driver_temp, self.motor_temp, self.bus_current = 0.0, 0.0, 0.0, 0.0
        self.status_str = ""
        self.enable = True
        self.command_id = -1

        self.color_status = [False] * Color.SIZE
        self.color_status[Color.WHITE] = True
        self.vibrate_status = [False] * Vibrate.SIZE
        self.vibrate_status[Vibrate.NONE] = True

        self.serial_mtx = threading.Lock()
        self.receive_data_mtx = threading.Lock()
        self.color_status_mtx = threading.Lock()
        self.vibrate_status_mtx = threading.Lock()

        if not self.init_serial():
            self.get_logger().error("Critical: Could not open Serial Port.")
            return

        # QoS 설정 (최신성 우선)
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )

        # Publishers
        self.pub_gripper = self.create_publisher(Gripper, "gripper/data", qos)
        self.pub_imu = self.create_publisher(Imu, "imu/data", qos)
        self.pub_gripper_joint_state = self.create_publisher(JointState, "gripper/joint_state", qos)
        self.pub_arm_joint_state_with_gripper = self.create_publisher(JointState, "joint_state_gripper", qos)

        # Subscribers (Reentrant Callback Group 적용)
        self.sub_gripper = self.create_subscription(Gripper, "gripper/ctrl", self.gripper_ctrl_handler, qos, callback_group=self.callback_group)
        self.sub_joint_state_ctrl = self.create_subscription(JointState, "gripper/joint_state_ctrl", self.joint_state_ctrl_handler, qos, callback_group=self.callback_group)
        self.sub_joint_state_info = self.create_subscription(JointState, "joint_state_info", self.joint_state_info_handler, qos, callback_group=self.callback_group)
        self.sub_data_capture_status = self.create_subscription(CaptureStatus, "data_capture_status", self.data_capture_status_handler, qos, callback_group=self.callback_group)
        self.sub_teleop_status = self.create_subscription(TeleopStatus, "teleop_status", self.teleop_status_handler, qos, callback_group=self.callback_group)
        self.sub_localization_status = self.create_subscription(LocalizationStatus, "localization_status", self.localization_status_handler, qos, callback_group=self.callback_group)
        self.sub_arm_control_status = self.create_subscription(ArmControlStatus, "arm_control_status", self.arm_control_status_handler, qos, callback_group=self.callback_group)

        # Clients
        self.client_capture = self.create_client(CaptureService, "data_tools_dataCapture/capture_service", callback_group=self.callback_group)
        self.client_teleop = self.create_client(Trigger, "teleop_trigger", callback_group=self.callback_group)

        # Threads
        self.running = True
        self.thread_receiving = threading.Thread(target=self.receiving_thread, daemon=True)
        self.thread_status_sending = threading.Thread(target=self.status_sending_thread, daemon=True)
        self.thread_receiving.start()
        self.thread_status_sending.start()

        # Initial Setup Command
        init_cmd = self.create_binary_command(SendFlag.EFFORT_CTRL, [self.motor_current_limit / 1000.0])
        self.send_serial(init_cmd)

    def _init_ik_lut(self):
        """그리퍼 기구학 룩업 테이블 생성 (0 ~ 1.67 rad)"""
        # 해상도를 1000단계로 설정하여 정밀도 확보
        self._lut_angles = np.linspace(0.0, 1.67, 1000)
        # 각 각도에 대응하는 2 * (dist_theta - dist_0) 값 계산
        d0 = self.get_distance(0.0)
        self._lut_distances = np.array([2 * (self.get_distance(a) - d0) for a in self._lut_angles])
        self.get_logger().info("IK Look-up Table generation complete.")

    def init_serial(self):
        try:
            self.serial = serial.Serial(
                port=self.serial_port_name, baudrate=460800, timeout=0.001
            )
            return self.serial.is_open
        except Exception as e:
            self.get_logger().error(f"Serial Error: {e}")
            return False

    def send_serial(self, data):
        with self.serial_mtx:
            if self.serial and self.serial.is_open:
                try: self.serial.write(data)
                except: pass

    def create_binary_command(self, cmd, values, big_endian=False):
        packed = bytearray([cmd])
        fmt = '>' if big_endian else '<'
        for v in values:
            if isinstance(v, int): packed.extend(struct.pack(f'{fmt}I', v))
            else: packed.extend(struct.pack(f'{fmt}f', v))
        packed.extend(b'\r\n')
        return bytes(packed)

    def get_distance(self, angle):
        """Forward Kinematics: Angle -> Width/2"""
        theta = (136.01 / 180.0) * math.pi - angle # 180 - 43.99
        height = 0.0325 * math.sin(theta)
        term = max(0, (0.058**2) - (height - 0.01456)**2)
        return math.sqrt(term) + 0.0325 * math.cos(theta)

    def get_angle(self, target_distance):
        """Inverse Kinematics: Distance -> Angle (LUT 기반)"""
        return float(np.interp(target_distance, self._lut_distances, self._lut_angles))

    # --- Handlers ---

    def joint_state_ctrl_handler(self, msg):
        now = time.time()
        if now - self._last_ctrl_time < self.ctrl_freq: return
        self._last_ctrl_time = now

        with self.receive_data_mtx:
            curr_enable, curr_effort, curr_velocity = self.enable, self.effort, self.velocity

        if not curr_enable:
            self.send_serial(self.create_binary_command(SendFlag.ENABLE, [0.0]))

        # Effort/Velocity Update
        if msg.effort and msg.effort[-1] != 0 and abs(curr_effort - msg.effort[-1]) > 0.01:
            self.send_serial(self.create_binary_command(SendFlag.EFFORT_CTRL, [msg.effort[-1]]))
        if msg.velocity and msg.velocity[-1] != 0 and abs(curr_velocity - msg.velocity[-1]) > 0.01:
            self.send_serial(self.create_binary_command(SendFlag.VELOCITY_CTRL, [msg.velocity[-1], msg.velocity[-1]]))

        # Position Control (LUT 사용)
        dist = min(max(msg.position[-1], 0.0), 0.098)
        angle = self.get_angle(dist)
        cmd_flag = SendFlag.POSITION_CTRL_MIT if self.mit_mode else SendFlag.POSITION_CTRL_POS_VEL
        self.send_serial(self.create_binary_command(cmd_flag, [angle]))

    def gripper_ctrl_handler(self, msg):
        now = time.time()
        if now - self._last_grip_time < self.ctrl_freq: return
        self._last_grip_time = now

        if msg.enable != self.enable:
            self.send_serial(self.create_binary_command(SendFlag.ENABLE if msg.enable else SendFlag.DISABLE, [0.0]))
        elif msg.set_zero:
            self.send_serial(self.create_binary_command(SendFlag.SET_ZERO, [0.0]))
        else:
            # Velocity/Effort Logic (동일)
            if msg.effort != 0 and abs(self.effort - msg.effort) > 0.01:
                self.send_serial(self.create_binary_command(SendFlag.EFFORT_CTRL, [msg.effort]))
            if msg.velocity != 0 and abs(self.velocity - msg.velocity) > 0.01:
                self.send_serial(self.create_binary_command(SendFlag.VELOCITY_CTRL, [msg.velocity, msg.velocity]))
            
            # Position
            target_dist = msg.distance if msg.distance != 0 else 0.0 # 기존 로직 유지
            if msg.distance != 0:
                angle = self.get_angle(min(max(msg.distance, 0.0), 0.098))
            else:
                angle = min(max(msg.angle, 0.0), 1.67)
            
            cmd_flag = SendFlag.POSITION_CTRL_MIT if self.mit_mode else SendFlag.POSITION_CTRL_POS_VEL
            self.send_serial(self.create_binary_command(cmd_flag, [angle]))

    def joint_state_info_handler(self, msg):
        new_msg = JointState()
        new_msg.header = msg.header
        new_msg.name = list(msg.name)
        new_msg.position = list(msg.position)
        new_msg.velocity = list(msg.velocity)
        new_msg.effort = list(msg.effort)

        while len(new_msg.position) < 7: new_msg.position.append(0.0)
        with self.receive_data_mtx:
            new_msg.position[6] = self.distance
        
        self.pub_arm_joint_state_with_gripper.publish(new_msg)

    def data_capture_status_handler(self, msg):
        with self.color_status_mtx:
            if msg.fail: self.color_status[Color.YELLOW] = True
            elif not msg.quit: self.color_status[Color.GREEN] = True
            else: self.color_status[Color.GREEN] = self.color_status[Color.YELLOW] = False

    def teleop_status_handler(self, msg):
        with self.color_status_mtx:
            if msg.fail: self.color_status[Color.YELLOW] = True
            elif not msg.quit: self.color_status[Color.GREEN] = True
            else: self.color_status[Color.GREEN] = self.color_status[Color.YELLOW] = False

    def localization_status_handler(self, msg):
        with self.color_status_mtx:
            self.color_status[Color.RED] = not msg.accurate

    def arm_control_status_handler(self, msg):
        if msg.over_limit:
            with self.vibrate_status_mtx: self.vibrate_status[Vibrate.ONE] = True

    # --- Threads ---

    def status_sending_thread(self):
        last_color = -1
        last_color_time = 0
        while self.running:
            now = time.time()
            # Vibration (High Priority)
            now_vibrate = Vibrate.NONE
            with self.vibrate_status_mtx:
                if self.vibrate_status[Vibrate.ONE]:
                    now_vibrate = Vibrate.ONE
                    self.vibrate_status[Vibrate.ONE] = False
            if now_vibrate != Vibrate.NONE:
                self.send_serial(self.create_binary_command(SendFlag.VIBRATE_CTRL, [int(now_vibrate)], True))

            # LED Color (Change Driven)
            with self.color_status_mtx:
                if self.color_status[Color.BLUE] and (now - last_color_time > 1.0):
                    self.color_status[Color.BLUE] = False
                
                target_color = Color.WHITE
                if self.color_status[Color.BLUE]: target_color = Color.BLUE
                elif self.color_status[Color.RED]: target_color = Color.RED
                elif self.color_status[Color.YELLOW]: target_color = Color.YELLOW
                elif self.color_status[Color.GREEN]: target_color = Color.GREEN
                
                if target_color != last_color:
                    self.send_serial(self.create_binary_command(SendFlag.LIGHT_CTRL, [int(target_color)], True))
                    last_color = target_color
                    last_color_time = now
            time.sleep(0.02)

    def receiving_thread(self):
        def sf(v, d=0.0): # Safe Float
            try: return float(v) if v is not None else d
            except: return d

        raw_buffer = []
        while self.running:
            if not self.serial or not self.serial.is_open:
                time.sleep(0.1); continue
            
            try:
                if self.serial.in_waiting > 0:
                    chunk = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
                    raw_buffer.append(chunk)
                else:
                    time.sleep(0.001); continue

                full_str = "".join(raw_buffer)
                if len(full_str) > 5000: raw_buffer = []; continue

                while True:
                    found, start, end = find_json(full_str)
                    if not found:
                        raw_buffer = [full_str]
                        break
                    
                    obj_str = full_str[start:end+1]
                    full_str = full_str[end+1:]
                    
                    try:
                        root = json.loads(obj_str)
                        ts = self.get_clock().now().to_msg()

                        # 1. AS5047 (Encoder) / Motor Status
                        if "AS5047" in root or "motor" in root:
                            m = root.get("motor", root.get("AS5047", {}))
                            ang = min(max(sf(m.get("Position", m.get("rad"))), 0.0), 1.67)
                            dist = 2 * (self.get_distance(ang) - self.get_distance(0.0))
                            
                            with self.receive_data_mtx:
                                self.angle, self.distance = ang, dist
                                if "motor" in root: self.motor_current = sf(m.get("Current"))

                            # Publish Gripper
                            g_msg = Gripper()
                            g_msg.header.stamp, g_msg.header.frame_id = ts, self.frame_id
                            g_msg.angle, g_msg.distance, g_msg.enable = ang, dist, self.enable
                            if "motor" in root:
                                g_msg.effort, g_msg.velocity = sf(m.get("Current")), sf(m.get("Speed"))
                            self.pub_gripper.publish(g_msg)

                            # Publish JointState
                            js = JointState()
                            js.header.stamp, js.name = ts, [self.joint_name]
                            js.position = [float(dist)]
                            if "motor" in root:
                                js.velocity, js.effort = [sf(m.get("Speed"))], [sf(m.get("Current"))]
                            self.pub_gripper_joint_state.publish(js)

                        # 2. IMU
                        if "IMU" in root:
                            iv = root["IMU"]
                            imu = Imu()
                            imu.header.stamp, imu.header.frame_id = ts, self.frame_id
                            imu.orientation = euler_to_quaternion(sf(iv.get("roll")), sf(iv.get("pitch")), sf(iv.get("yaw")))
                            gyr, acc = iv.get("gyr", [0,0,0]), iv.get("acc", [0,0,0])
                            imu.angular_velocity.x, imu.angular_velocity.y, imu.angular_velocity.z = sf(gyr[0]), sf(gyr[1]), sf(gyr[2])
                            imu.linear_acceleration.x, imu.linear_acceleration.y, imu.linear_acceleration.z = sf(acc[0]), sf(acc[1]), sf(acc[2])
                            self.pub_imu.publish(imu)

                        # 3. Motor Status
                        if "motorstatus" in root:
                            mv = root["motorstatus"]
                            with self.receive_data_mtx:
                                self.voltage, self.driver_temp = sf(mv.get("Voltage")), sf(mv.get("DriverTemp"))
                                self.motor_temp, self.bus_current = sf(mv.get("MotorTemp")), sf(mv.get("BusCurrent"))
                                self.status_str = str(mv.get("Status", ""))
                                if len(self.status_str) >= 4:
                                    self.enable = bool(0b01000000 & int(self.status_str[2:4], 16))

                        # 4. Command
                        if "Command" in root:
                            c_id = int(sf(root.get("Command")))
                            if self.command_id != -1 and c_id != self.command_id:
                                with self.color_status_mtx: self.color_status[Color.BLUE] = True
                                self.client_teleop.call_async(Trigger.Request())
                                req = CaptureService.Request()
                                req.dataset_dir, req.episode_index, req.instructions = "", -1, "[null]"
                                req.start = req.end = True
                                self.client_capture.call_async(req)
                            self.command_id = c_id

                    except json.JSONDecodeError: continue
            except Exception as e:
                time.sleep(0.1)

def main(args=None):
    rclpy.init(args=args)
    node = RosOperator()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.running = False
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()