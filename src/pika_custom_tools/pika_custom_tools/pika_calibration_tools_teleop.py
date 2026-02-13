import sys
import signal  # 추가
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, TransformStamped
from tf2_ros import Buffer, TransformListener, TransformBroadcaster
from scipy.spatial.transform import Rotation as R
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit)
from PyQt5.QtCore import Qt, QTimer  # QTimer 추가
import threading

class PikaTfIntegrator(Node):
    # (PikaTfIntegrator 클래스 내용은 이전과 동일하므로 중복 생략)
    def __init__(self):
        super().__init__('pika_tf_integrator')
        self.tf_buffer = Buffer(rclpy.duration.Duration(seconds=10.0))
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.current_pika_pose = None
        self.is_calibrated = False
        self.T_target = np.eye(4)
        self.M_world_from_pika = np.eye(4)
        
        # --- 필터 설정 변수 ---
        self.alpha = 0.2  # 필터 계수 (0.0 ~ 1.0): 낮을수록 부드럽고, 높을수록 반응 빠름
        self.filtered_pos = None  # 필터링된 위치 저장
        self.filtered_quat = None # 필터링된 회전 저장

        self.parent_frame = '/world' 
        self.local_frame = '/pika_local'
        self.target_frame = '/pika_target'
        self.create_subscription(PoseStamped, '/pika_pose', self.pika_cb, 10)
        self.create_timer(0.02, self.publish_loop)

    def pika_cb(self, msg):
        # 1. 원본 데이터 추출
        raw_p = np.array([msg.pose.position.x, msg.pose.position.y, msg.pose.position.z])
        raw_q = np.array([msg.pose.orientation.x, msg.pose.orientation.y, 
                          msg.pose.orientation.z, msg.pose.orientation.w])

        # 2. 최초 데이터 처리
        if self.filtered_pos is None:
            self.filtered_pos = raw_p
            self.filtered_quat = raw_q
            self.current_pika_pose = msg
            return

        # 3. 위치 필터링 (EMA)
        self.filtered_pos = self.alpha * raw_p + (1.0 - self.alpha) * self.filtered_pos

        # 4. 회전 필터링 (Slerp가 이상적이나 연산량 위해 EMA 후 정규화 사용)
        # 이전 쿼터니언과 현재 쿼터니언의 내적을 확인하여 방향 반전 방지 (Shortest path)
        if np.dot(self.filtered_quat, raw_q) < 0:
            raw_q = -raw_q
        
        new_q = self.alpha * raw_q + (1.0 - self.alpha) * self.filtered_quat
        self.filtered_quat = new_q / np.linalg.norm(new_q) # 정규화 필수

        # 5. 필터링된 결과를 current_pika_pose에 반영
        self.current_pika_pose = msg
        self.current_pika_pose.pose.position.x = self.filtered_pos[0]
        self.current_pika_pose.pose.position.y = self.filtered_pos[1]
        self.current_pika_pose.pose.position.z = self.filtered_pos[2]
        self.current_pika_pose.pose.orientation.x = self.filtered_quat[0]
        self.current_pika_pose.pose.orientation.y = self.filtered_quat[1]
        self.current_pika_pose.pose.orientation.z = self.filtered_quat[2]
        self.current_pika_pose.pose.orientation.w = self.filtered_quat[3]

    def run_calibration(self, target_xyz):
        if self.current_pika_pose is None:
            return False, "Error: No Pika data received yet."
        self.T_target[:3, 3] = target_xyz
        p, q = self.current_pika_pose.pose.position, self.current_pika_pose.pose.orientation
        T_pika_init = np.eye(4)
        T_pika_init[:3, :3] = R.from_quat([q.x, q.y, q.z, q.w]).as_matrix()
        T_pika_init[:3, 3] = [p.x, p.y, p.z]
        self.M_world_from_pika = self.T_target @ np.linalg.inv(T_pika_init)
        self.is_calibrated = True
        return True, f"Calibration Complete: Pika mapped to {self.T_target[:3, 3]}"

    def publish_loop(self):
        if not self.is_calibrated or self.current_pika_pose is None:
            return
        p, q = self.current_pika_pose.pose.position, self.current_pika_pose.pose.orientation
        T_pika_curr = np.eye(4)
        T_pika_curr[:3, :3] = R.from_quat([q.x, q.y, q.z, q.w]).as_matrix()
        T_pika_curr[:3, 3] = [p.x, p.y, p.z]
        T_local_mat = self.M_world_from_pika @ T_pika_curr
        R_y_90 = R.from_euler('y', 90, degrees=True).as_matrix()
        T_rot_offset = np.eye(4)
        T_rot_offset[:3, :3] = R_y_90
        T_target_mat = T_local_mat @ T_rot_offset
        self.broadcast_tf(T_local_mat, self.local_frame)
        self.broadcast_tf(T_target_mat, self.target_frame)

    def broadcast_tf(self, matrix, child_frame_id):
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = self.parent_frame
        t.child_frame_id = child_frame_id
        t.transform.translation.x = matrix[0, 3]
        t.transform.translation.y = matrix[1, 3]
        t.transform.translation.z = matrix[2, 3]
        quat = R.from_matrix(matrix[:3, :3]).as_quat()
        t.transform.rotation.x, t.transform.rotation.y, t.transform.rotation.z, t.transform.rotation.w = quat
        self.tf_broadcaster.sendTransform(t)

class CalibWindow(QWidget):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("X:")); self.edit_x = QLineEdit("0.45"); input_layout.addWidget(self.edit_x)
        input_layout.addWidget(QLabel("Y:")); self.edit_y = QLineEdit("-0.3"); input_layout.addWidget(self.edit_y)
        input_layout.addWidget(QLabel("Z:")); self.edit_z = QLineEdit("0.2"); input_layout.addWidget(self.edit_z)
        self.btn = QPushButton('Calibration: Set Zero-point')
        self.btn.clicked.connect(self.on_click)
        self.btn.setMinimumHeight(40)
        self.status = QLabel('Status: Waiting for Calibration...')
        self.status.setAlignment(Qt.AlignCenter)
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.btn)
        main_layout.addWidget(self.status)
        self.setLayout(main_layout)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           
        self.setWindowTitle('Pika Mapping Tools (Real-robot)')
        self.resize(450, 180)
        self.show()

    def on_click(self):
        try:
            x, y, z = float(self.edit_x.text()), float(self.edit_y.text()), float(self.edit_z.text())
            success, msg = self.node.run_calibration([x, y, z])
            self.status.setText(f"Status: {msg}")
            if success: self.btn.setStyleSheet("background-color: #D1FFD1")
        except ValueError:
            self.status.setText("Status: Error! Please enter valid numbers.")
            self.btn.setStyleSheet("background-color: #FFD1D1")

# --- 메인 함수: 종료 로직의 핵심 ---
def main():
    # 1. ROS 2 초기화
    rclpy.init()
    node = PikaTfIntegrator()
    
    # 2. ROS 스핀을 데몬 스레드로 실행 (메인 스레드 종료 시 같이 종료됨)
    ros_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    ros_thread.start()
    
    # 3. Qt 앱 생성
    app = QApplication(sys.argv)
    window = CalibWindow(node)

    # 4. [핵심] SIGINT(Ctrl+C) 발생 시 앱이 종료되도록 설정
    # Python 기본 핸들러를 사용하여 인터럽트를 즉시 처리하도록 함
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # 5. [핵심] QTimer 추가
    # Qt의 이벤트 루프가 Python 인터프리터에게 제어권을 가끔 넘겨주도록 하여
    # 터미널의 Ctrl+C 신호를 잡아낼 수 있게 함 (500ms 주기)
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None) 

    # 6. GUI 실행 및 종료 처리
    try:
        exit_code = app.exec_()
    except KeyboardInterrupt:
        exit_code = 0
    finally:
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(exit_code)

if __name__ == '__main__':
    main()