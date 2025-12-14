import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.qos import QoSProfile

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
# 사용자 정의 메시지/서비스 (data_msgs 패키지가 있다고 가정)
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
    WHITE = 0
    RED = 1
    GREEN = 2
    BLUE = 3
    YELLOW = 4
    SIZE = 5

class Vibrate:
    NONE = 0
    ONE = 1
    SIZE = 2

# --- Helper Functions ---

def euler_to_quaternion(roll, pitch, yaw):
    """
    Euler angles (RPY) to Quaternion (x, y, z, w)
    """
    qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
    qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
    qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    return Quaternion(x=qx, y=qy, z=qz, w=qw)

def find_json(msg):
    """
    Finds the first valid JSON object string {...} in the buffer.
    Returns (found, start_index, end_index)
    """
    stack = []
    for i, ch in enumerate(msg):
        if ch == '{':
            stack.append(i)
        elif ch == '}':
            if stack:
                start_index = stack.pop()
                # 스택이 비었고 (최상위 객체 닫힘), 바로 앞이 ':'가 아닌 경우 (JSON 구조상 값 내부가 아님을 체크하는 휴리스틱)
                if not stack: 
                    # C++ 로직: if(stack.empty() || (index > 0 && msg[index-1]!=':'))
                    # 파이썬에서는 안전하게 범위 체크
                    if start_index > 0 and msg[start_index-1] != ':': 
                         return True, start_index, i
                    # 단순하게 최상위 괄호가 닫히면 반환하도록 처리 (C++ 로직 유사 구현)
                    return True, start_index, i
    return False, -1, -1

class RosOperator(Node):
    def __init__(self):
        super().__init__('serial_gripper_imu')

        self.get_logger().info('custom_node open')

        # Parameters
        self.declare_parameter("serial_port", "/dev/ttyUSB0")
        self.serial_port_name = self.get_parameter("serial_port").value
        
        self.declare_parameter("joint_name", "center_joint")
        self.joint_name = self.get_parameter("joint_name").value
        
        self.declare_parameter("motor_current_limit", 1000.0)
        self.motor_current_limit = self.get_parameter("motor_current_limit").value
        
        self.declare_parameter("motor_current_redundancy", 500.0)
        self.motor_current_redundancy = self.get_parameter("motor_current_redundancy").value
        
        self.declare_parameter("ctrl_rate", 50.0)
        self.ctrl_rate = self.get_parameter("ctrl_rate").value
        
        self.declare_parameter("mit_mode", True)
        self.mit_mode = self.get_parameter("mit_mode").value

        self.ctrl_freq = 1.0 / self.ctrl_rate
        self.is_gripper = False
        
        # Symlink resolution
        if self.serial_port_name in ["/dev/ttyUSB60", "/dev/ttyUSB61"]:
            self.is_gripper = True
        
        if os.path.islink(self.serial_port_name):
            self.serial_port_name = os.path.realpath(self.serial_port_name)

        # Environment Variable for Frame ID
        self.pika_r_code = os.environ.get("pika_R_code", "")
        self.pika_l_code = os.environ.get("pika_L_code", "")
        self.frame_id = "gripper_link" # Default fallback

        if self.pika_r_code:
            self.frame_id = "right_hand"
            self.get_logger().info(f"Found pika_R_code: {self.pika_r_code}. Set Frame ID to: {self.frame_id}")
        elif self.pika_l_code:
            self.frame_id = "left_hand"
            self.get_logger().info(f"Found pika_L_code: {self.pika_l_code}. Set Frame ID to: {self.frame_id}")
        else:
            self.get_logger().info(f"No pika code env var found. Frame ID defaulting to: {self.frame_id}")

        # State Variables
        self.effort = -1.0
        self.velocity = -1.0
        self.angle = 0.0
        self.distance = 0.0
        self.motor_current = 0.0
        self.voltage = 0.0
        self.driver_temp = 0.0
        self.motor_temp = 0.0
        self.bus_current = 0.0
        self.status_str = ""
        self.enable = True
        self.command_id = -1
        self.last_command_angle = -1.0

        # Hardware Control Status
        self.color_status = [False] * Color.SIZE
        self.color_status[Color.WHITE] = True
        
        self.vibrate_status = [False] * Vibrate.SIZE
        self.vibrate_status[Vibrate.NONE] = True

        # Mutexes
        self.serial_mtx = threading.Lock()
        self.receive_data_mtx = threading.Lock()
        self.color_status_mtx = threading.Lock()
        self.vibrate_status_mtx = threading.Lock()

        # Serial Setup
        self.serial = None
        if not self.init_serial():
            self.get_logger().error("Failed to initialize serial port. Exiting...")
            # Node shutdown logic handled in main

        # Publishers
        self.pub_gripper = self.create_publisher(Gripper, "/gripper/data", 1)
        self.pub_imu = self.create_publisher(Imu, "/imu/data", 1)
        self.pub_gripper_joint_state = self.create_publisher(JointState, "/gripper/joint_state", 1)
        self.pub_arm_joint_state_with_gripper = self.create_publisher(JointState, "/joint_state_gripper", 1)

        # Subscribers
        self.sub_gripper = self.create_subscription(Gripper, "gripper/ctrl", self.gripper_ctrl_handler, 1)
        self.sub_joint_state_ctrl = self.create_subscription(JointState, "/gripper/joint_state_ctrl", self.joint_state_ctrl_handler, 1)
        self.sub_joint_state_info = self.create_subscription(JointState, "/joint_state_info", self.joint_state_info_handler, 1)
        self.sub_data_capture_status = self.create_subscription(CaptureStatus, "/data_capture_status", self.data_capture_status_handler, 1)
        self.sub_teleop_status = self.create_subscription(TeleopStatus, "/teleop_status", self.teleop_status_handler, 1)
        self.sub_localization_status = self.create_subscription(LocalizationStatus, "/localization_status", self.localization_status_handler, 1)
        self.sub_arm_control_status = self.create_subscription(ArmControlStatus, "/arm_control_status", self.arm_control_status_handler, 1)

        # Clients
        self.client_capture = self.create_client(CaptureService, "/data_tools_dataCapture/capture_service")
        self.client_teleop = self.create_client(Trigger, "/teleop_trigger")

        # Threads
        self.running = True
        self.thread_receiving = threading.Thread(target=self.receiving_thread)
        self.thread_status_sending = threading.Thread(target=self.status_sending_thread)
        
        self.thread_receiving.start()
        self.thread_status_sending.start()

        # Initial Command
        self.motor_current_limit /= 1000.0
        init_cmd = self.create_binary_command(SendFlag.EFFORT_CTRL, [self.motor_current_limit])
        self.send_serial(init_cmd)

    def init_serial(self):
        try:
            self.serial = serial.Serial(
                port=self.serial_port_name,
                baudrate=460800,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.01 
            )
            return self.serial.is_open
        except serial.SerialException as e:
            self.get_logger().error(f"Serial Open Error: {e}")
            return False

    def __del__(self):
        self.running = False
        if hasattr(self, 'serial') and self.serial and self.serial.is_open:
            self.serial.close()
        if hasattr(self, 'thread_receiving') and self.thread_receiving.is_alive():
            self.thread_receiving.join()
        if hasattr(self, 'thread_status_sending') and self.thread_status_sending.is_alive():
            self.thread_status_sending.join()

    def send_serial(self, data):
        with self.serial_mtx:
            if self.serial and self.serial.is_open:
                try:
                    self.serial.write(data)
                except Exception as e:
                    self.get_logger().error(f"Serial Write Error: {e}")

    def create_binary_command(self, cmd, values, big_endian=False):
        """
        Packs command and float/int values into bytes.
        Protocol: [CMD (1byte)] [Val1 (4bytes)] ... [ValN (4bytes)] [\r\n]
        """
        packed_data = bytearray()
        packed_data.append(cmd)
        
        # Endianness: '>' for Big Endian, '<' for Little Endian
        fmt_char = '>' if big_endian else '<'
        
        for val in values:
            if isinstance(val, int):
                packed_data.extend(struct.pack(f'{fmt_char}I', val)) # unsigned int
            else:
                packed_data.extend(struct.pack(f'{fmt_char}f', val)) # float

        packed_data.extend(b'\r\n')
        return bytes(packed_data)

    # --- Kinematics Math ---
    def get_distance(self, angle):
        # angle = (180.0-43.99)/180.0*PI - angle
        theta = (180.0 - 43.99) / 180.0 * math.pi - angle
        height = 0.0325 * math.sin(theta)
        # width logic
        term = (0.058**2) - (height - 0.01456)**2
        if term < 0: term = 0 # Safety for sqrt
        width_d = 0.0325 * math.cos(theta)
        width = math.sqrt(term) + width_d
        return width

    def get_angle(self, target_width, tol=1e-6, max_iter=1000):
        # Binary search for inverse kinematics
        left = 0.0
        right = math.pi
        
        for _ in range(max_iter):
            mid = (left + right) / 2.0
            current_width = self.get_distance(mid)
            
            if abs(current_width - target_width) < tol:
                return mid
            
            # Note: Assuming get_distance is monotonic in the search range
            if current_width < target_width:
                left = mid
            else:
                right = mid
        return (left + right) / 2.0

    # --- ROS Callbacks ---

    def data_capture_status_handler(self, msg):
        with self.color_status_mtx:
            if msg.fail:
                self.color_status[Color.YELLOW] = True
            elif not msg.quit:
                self.color_status[Color.GREEN] = True
            else:
                self.color_status[Color.GREEN] = False
                self.color_status[Color.YELLOW] = False

    def teleop_status_handler(self, msg):
        with self.color_status_mtx:
            if msg.fail:
                self.color_status[Color.YELLOW] = True
            elif not msg.quit:
                self.color_status[Color.GREEN] = True
            else:
                self.color_status[Color.GREEN] = False
                self.color_status[Color.YELLOW] = False

    def localization_status_handler(self, msg):
        with self.color_status_mtx:
            if msg.accurate:
                self.color_status[Color.RED] = False
            else:
                self.color_status[Color.RED] = True

    def arm_control_status_handler(self, msg):
        if msg.over_limit:
            with self.vibrate_status_mtx:
                self.vibrate_status[Vibrate.ONE] = True

    def joint_state_ctrl_handler(self, msg):
        # Throttle logic handled by simple time check if needed, but python is slow enough usually.
        # Strict rate limiting:
        now = self.get_clock().now().seconds_nanoseconds()[0] + \
              self.get_clock().now().seconds_nanoseconds()[1] * 1e-9
        
        if not hasattr(self, '_last_ctrl_time'): self._last_ctrl_time = -1
        if now - self._last_ctrl_time < self.ctrl_freq:
            return
        self._last_ctrl_time = now

        with self.receive_data_mtx:
            curr_enable = self.enable
            curr_effort = self.effort
            curr_velocity = self.velocity
        
        if not curr_enable:
            cmd = self.create_binary_command(SendFlag.ENABLE, [0.0])
            self.send_serial(cmd)

        if len(msg.effort) > 0 and msg.effort[-1] != 0 and curr_effort != msg.effort[-1]:
            self.effort = msg.effort[-1]
            cmd = self.create_binary_command(SendFlag.EFFORT_CTRL, [self.effort])
            self.send_serial(cmd)
        
        if len(msg.velocity) > 0 and msg.velocity[-1] != 0 and curr_velocity != msg.velocity[-1]:
            self.velocity = msg.velocity[-1]
            cmd = self.create_binary_command(SendFlag.VELOCITY_CTRL, [self.velocity, self.velocity])
            self.send_serial(cmd)

        distance = msg.position[-1]
        distance = min(max(distance, 0.0), 0.098)
        
        # Convert Linear Distance to Angular
        angle = self.get_angle(distance / 2.0 + self.get_distance(0.0))
        angle = min(max(angle, 0.0), 1.67)

        send_cmd_flag = SendFlag.POSITION_CTRL_MIT if self.mit_mode else SendFlag.POSITION_CTRL_POS_VEL
        cmd = self.create_binary_command(send_cmd_flag, [angle])
        self.send_serial(cmd)
        self.last_command_angle = angle

    def gripper_ctrl_handler(self, msg):
        now = self.get_clock().now().seconds_nanoseconds()[0] + \
              self.get_clock().now().seconds_nanoseconds()[1] * 1e-9
        
        if not hasattr(self, '_last_grip_time'): self._last_grip_time = -1
        if now - self._last_grip_time < self.ctrl_freq:
            return
        self._last_grip_time = now

        with self.receive_data_mtx:
            curr_enable = self.enable
            curr_effort = self.effort
            curr_velocity = self.velocity

        if msg.enable != curr_enable:
            if msg.enable:
                self.send_serial(self.create_binary_command(SendFlag.ENABLE, [0.0]))
            else:
                self.send_serial(self.create_binary_command(SendFlag.DISABLE, [0.0]))
        elif msg.set_zero:
            self.send_serial(self.create_binary_command(SendFlag.SET_ZERO, [0.0]))
        else:
            if msg.effort != 0 and msg.effort != self.effort:
                self.effort = msg.effort
                self.send_serial(self.create_binary_command(SendFlag.EFFORT_CTRL, [self.effort]))
            
            if msg.velocity != 0 and msg.velocity != self.velocity:
                self.velocity = msg.velocity
                self.send_serial(self.create_binary_command(SendFlag.VELOCITY_CTRL, [self.velocity, self.velocity]))
            
            angle = msg.angle
            distance = msg.distance
            
            if distance != 0:
                distance = min(max(distance, 0.0), 0.098)
                angle = self.get_angle(distance / 2.0 + self.get_distance(0.0))
            
            angle = min(max(angle, 0.0), 1.67)

            send_cmd_flag = SendFlag.POSITION_CTRL_MIT if self.mit_mode else SendFlag.POSITION_CTRL_POS_VEL
            self.send_serial(self.create_binary_command(send_cmd_flag, [angle]))
            self.last_command_angle = angle

    def joint_state_info_handler(self, msg):
        # Update JointState with gripper position
        new_msg = JointState()
        new_msg.header = msg.header
        new_msg.name = list(msg.name)
        new_msg.position = list(msg.position)
        new_msg.velocity = list(msg.velocity)
        new_msg.effort = list(msg.effort)

        if len(new_msg.position) < 7:
             new_msg.position.extend([0.0]*(7 - len(new_msg.position)))
        
        with self.receive_data_mtx:
            current_dist = self.distance
        
        # 7th element (index 6) override
        if len(new_msg.position) > 6:
            new_msg.position[6] = current_dist
        
        self.pub_arm_joint_state_with_gripper.publish(new_msg)

    # --- Threads ---

    def status_sending_thread(self):
        rate1 = 50.0 # Hz
        rate2 = 100.0 # Hz
        interval_1 = 1.0/rate1
        interval_2 = 1.0/rate2
        
        last_color_status = -1
        last_color_status_time = -1
        
        next_run_1 = time.time()
        next_run_2 = time.time()

        while self.running and rclpy.ok():
            now = time.time()
            
            # Task 2: Vibrate Control (Faster loop)
            if now >= next_run_2:
                now_vibrate = Vibrate.NONE
                with self.vibrate_status_mtx:
                    if self.vibrate_status[Vibrate.ONE]:
                        now_vibrate = Vibrate.ONE
                        self.vibrate_status[Vibrate.ONE] = False
                
                if now_vibrate != Vibrate.NONE:
                    # Note: Big Endian used here per C++ logic
                    cmd = self.create_binary_command(SendFlag.VIBRATE_CTRL, [int(now_vibrate)], big_endian=True)
                    self.send_serial(cmd)
                next_run_2 += interval_2

            # Task 1: Color Control (Slower loop)
            if now >= next_run_1:
                with self.color_status_mtx:
                    # Blue Reset Logic
                    if self.color_status[Color.BLUE]:
                        if last_color_status == Color.BLUE:
                            if time.time() - last_color_status_time > 1.0:
                                self.color_status[Color.BLUE] = False
                    
                    # Priority Logic
                    now_color = Color.WHITE
                    if self.color_status[Color.BLUE]: now_color = Color.BLUE
                    elif self.color_status[Color.RED]: now_color = Color.RED
                    elif self.color_status[Color.YELLOW]: now_color = Color.YELLOW
                    elif self.color_status[Color.GREEN]: now_color = Color.GREEN
                    
                    if now_color != last_color_status:
                        last_color_status_time = time.time()
                        last_color_status = now_color
                    
                    # Note: Big Endian used here per C++ logic
                    cmd = self.create_binary_command(SendFlag.LIGHT_CTRL, [int(now_color)], big_endian=True)
                    self.send_serial(cmd)
                next_run_1 += interval_1
            
            time.sleep(0.001) # Small sleep to prevent CPU hogging

    def receiving_thread(self):
        buffer_str = ""
        while self.running and rclpy.ok():
            if not self.serial or not self.serial.is_open:
                time.sleep(0.1)
                continue
            
            try:
                # Read available data
                waiting = self.serial.in_waiting
                if waiting > 0:
                    raw_data = self.serial.read(waiting)
                    # Try decoding (ignore errors for binary garbage)
                    data_str = raw_data.decode('utf-8', errors='ignore')
                    buffer_str += data_str
                else:
                    time.sleep(0.005)
                    continue

                if len(buffer_str) > 2000:
                    buffer_str = "" # Clear buffer if overflow/garbage

                while True:
                    found, start, end = find_json(buffer_str)
                    if not found:
                        break
                    
                    json_str = buffer_str[start : end+1]
                    # Update buffer (remove processed part)
                    if end + 1 < len(buffer_str):
                        buffer_str = buffer_str[end+1:]
                    else:
                        buffer_str = ""
                    
                    current_ros_time = self.get_clock().now().to_msg()
                    
                    try:
                        root = json.loads(json_str)
                        
                        # Process AS5047 (Encoder)
                        if "AS5047" in root:
                            as5047 = root["AS5047"]
                            # self.get_logger().info(f"AS5047 Raw Data: {as5047}")

                            if "error" not in as5047:
                                gripper_msg = Gripper()
                                gripper_msg.header.stamp = current_ros_time
                                gripper_msg.header.frame_id = self.frame_id
                                gripper_msg.enable = True
                                
                                angle = as5047.get("rad", 0.0)
                                gripper_msg.error = False
                                
                                # Constraints
                                if angle < 0:
                                    gripper_msg.error = True
                                    angle = 0
                                elif angle > 1.67:
                                    gripper_msg.error = True
                                    angle = 1.67
                                gripper_msg.angle = angle
                                
                                dist1 = self.get_distance(angle)
                                dist0 = self.get_distance(0)
                                gripper_msg.distance = 2 * (dist1 - dist0)
                                
                                with self.receive_data_mtx:
                                    self.angle = angle
                                    self.distance = gripper_msg.distance
                                
                                self.pub_gripper.publish(gripper_msg)
                                
                                # Publish JointState
                                js_msg = JointState()
                                js_msg.header.stamp = current_ros_time
                                js_msg.header.frame_id = self.frame_id
                                js_msg.name = [self.joint_name]
                                js_msg.position = [gripper_msg.distance]
                                
                                self.pub_gripper_joint_state.publish(js_msg)

                        # Process IMU
                        if "IMU" in root:
                            imu_val = root["IMU"]
                            imu_msg = Imu()
                            imu_msg.header.stamp = current_ros_time
                            imu_msg.header.frame_id = self.frame_id
                            
                            # RPY to Quaternion
                            roll = imu_val.get("roll", 0.0)
                            pitch = imu_val.get("pitch", 0.0)
                            yaw = imu_val.get("yaw", 0.0)
                            imu_msg.orientation = euler_to_quaternion(roll, pitch, yaw)
                            
                            gyr = imu_val.get("gyr", [0,0,0])
                            imu_msg.angular_velocity.x = float(gyr[0])
                            imu_msg.angular_velocity.y = float(gyr[1])
                            imu_msg.angular_velocity.z = float(gyr[2])
                            
                            acc = imu_val.get("acc", [0,0,0])
                            imu_msg.linear_acceleration.x = float(acc[0])
                            imu_msg.linear_acceleration.y = float(acc[1])
                            imu_msg.linear_acceleration.z = float(acc[2])
                            
                            self.pub_imu.publish(imu_msg)

                        # Process Motor
                        if "motor" in root:
                            motor_val = root["motor"]
                            gripper_msg = Gripper()
                            gripper_msg.header.stamp = current_ros_time
                            gripper_msg.header.frame_id = self.frame_id
                            
                            angle = motor_val.get("Position", 0.0)
                            gripper_msg.error = False
                             # Constraints
                            if angle < 0:
                                gripper_msg.error = True
                                angle = 0
                            elif angle > 1.67:
                                gripper_msg.error = True
                                angle = 1.67
                            gripper_msg.angle = angle

                            dist1 = self.get_distance(angle)
                            dist0 = self.get_distance(0)
                            gripper_msg.distance = 2 * (dist1 - dist0)
                            
                            gripper_msg.effort = motor_val.get("Current", 0.0)
                            gripper_msg.velocity = motor_val.get("Speed", 0.0)
                            gripper_msg.enable = self.enable
                            gripper_msg.voltage = self.voltage
                            gripper_msg.driver_temp = self.driver_temp
                            gripper_msg.motor_temp = self.motor_temp
                            gripper_msg.bus_current = self.bus_current
                            gripper_msg.status = self.status_str
                            
                            self.pub_gripper.publish(gripper_msg)

                            with self.receive_data_mtx:
                                self.angle = angle
                                self.distance = gripper_msg.distance
                                self.motor_current = gripper_msg.effort

                            js_msg = JointState()
                            js_msg.header.stamp = current_ros_time
                            js_msg.header.frame_id = self.frame_id
                            js_msg.name = [self.joint_name]
                            js_msg.position = [gripper_msg.distance]
                            self.get_logger().info(f"motor Raw Data: {js_msg}")
                            self.pub_gripper_joint_state.publish(js_msg)

                        # Process Motor Status
                        if "motorstatus" in root:
                            ms_val = root["motorstatus"]
                            with self.receive_data_mtx:
                                self.voltage = ms_val.get("Voltage", 0.0)
                                self.driver_temp = ms_val.get("DriverTemp", 0.0)
                                self.motor_temp = ms_val.get("MotorTemp", 0.0)
                                self.bus_current = ms_val.get("BusCurrent", 0.0)
                                self.status_str = ms_val.get("Status", "")
                            
                            # Check enable status from Hex string (e.g. "0x40")
                            # Assuming string is like "0x40" or similar
                            status_hex_str = self.status_str
                            if len(status_hex_str) >= 4: # e.g., 0x40
                                try:
                                    # Extract relevant byte (similar to substr(2,2))
                                    hex_part = status_hex_str[2:4]
                                    status_byte = int(hex_part, 16)
                                    with self.receive_data_mtx:
                                        self.enable = bool(0b01000000 & status_byte)
                                except ValueError:
                                    pass

                        # Process Command (Triggers)
                        if "Command" in root:
                            cmd_val = int(root["Command"])
                            if self.command_id == -1:
                                self.command_id = cmd_val
                            
                            if cmd_val != self.command_id:
                                with self.color_status_mtx:
                                    self.color_status[Color.BLUE] = True
                                
                                self.command_id = cmd_val
                                
                                # Call Trigger Service
                                if self.client_teleop.wait_for_service(timeout_sec=0.1):
                                    req_teleop = Trigger.Request()
                                    self.client_teleop.call_async(req_teleop)
                                
                                # Call Capture Service
                                if self.client_capture.wait_for_service(timeout_sec=0.1):
                                    req_cap = CaptureService.Request()
                                    req_cap.dataset_dir = ""
                                    req_cap.episode_index = -1
                                    req_cap.instructions = "[null]"
                                    req_cap.start = True
                                    req_cap.end = True
                                    self.client_capture.call_async(req_cap)

                        

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        self.get_logger().warn(f"JSON Parse Error: {e}")

            except Exception as e:
                self.get_logger().error(f"Serial Read Error: {e}")
                time.sleep(1)

def main(args=None):
    rclpy.init(args=args)
    node = RosOperator()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()