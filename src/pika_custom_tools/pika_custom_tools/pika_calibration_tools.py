import sys
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from scipy.spatial.transform import Rotation as R
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit
from PyQt5.QtCore import QTimer
import threading

class PikaOneShotCalibrator(Node):
    def __init__(self):
        super().__init__('pika_oneshot_calibrator')
        
        # 실시간 데이터 수신용
        self.current_tcp_pose = None
        self.current_pika_pose = None
        
        # 저장될 캘리브레이션 행렬 (초기값은 단위행렬)
        self.T_calib = np.eye(4)
        self.is_calibrated = False

        # Subscriptions
        self.create_subscription(PoseStamped, '/tcp_pose', self.tcp_cb, 10)
        self.create_subscription(PoseStamped, '/pika_pose', self.pika_cb, 10)
        
        # Publisher
        self.pub = self.create_publisher(PoseStamped, '/calibrated_pika_pose', 10)
        
        # 100Hz 연산 루프
        self.create_timer(0.01, self.publish_loop)

    def tcp_cb(self, msg): self.current_tcp_pose = msg
    def pika_cb(self, msg): self.current_pika_pose = msg

    def pose_to_mat(self, pose):
        p, q = pose.position, pose.orientation
        mat = np.eye(4)
        mat[:3, :3] = R.from_quat([q.x, q.y, q.z, q.w]).as_matrix()
        mat[:3, 3] = [p.x, p.y, p.z]
        return mat

    def mat_to_pose(self, mat, frame_id):
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = frame_id
        msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = mat[:3, 3]
        q = R.from_matrix(mat[:3, :3]).as_quat()
        msg.pose.orientation.x, msg.pose.orientation.y, msg.pose.orientation.z, msg.pose.orientation.w = q
        return msg

    def run_calibration(self):
        if self.current_tcp_pose is None or self.current_pika_pose is None:
            return False, "Data receiving..."

        # 1. 누르는 순간 두 로봇/그리퍼의 World Pose를 Reference로 고정
        self.T_pika_ref = self.pose_to_mat(self.current_pika_pose.pose)
        self.T_tcp_ref = self.pose_to_mat(self.current_tcp_pose.pose)
        
        self.is_calibrated = True
        return True, "Calibration_complete"

    def publish_loop(self):
        if not self.is_calibrated or self.current_pika_pose is None:
            return

        # 2. 현재 Pika의 실시간 World Pose
        T_pika_curr = self.pose_to_mat(self.current_pika_pose.pose)
        
        # 3. 기준점(Pika_ref)으로부터 현재 얼마나 움직였는지 계산 (Delta)
        # T_delta = (기준점의 역행렬) * 현재위치
        T_delta = np.linalg.inv(self.T_pika_ref) @ T_pika_curr
        
        # 4. 이 '움직임의 차이(Delta)'를 TCP의 기준점에 그대로 투영
        # T_final = TCP_ref * Delta
        T_final = self.T_tcp_ref @ T_delta
        
        out_msg = self.mat_to_pose(T_final, self.current_tcp_pose.header.frame_id)
        self.pub.publish(out_msg)

# --- GUI ---
class CalibWindow(QWidget):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.btn = QPushButton('Calibration Start (Align Pika to TCP)')
        self.btn.clicked.connect(self.on_click)
        self.status = QLabel('status: waiting')
        
        layout.addWidget(QLabel('calibration'))
        layout.addWidget(self.btn)
        layout.addWidget(self.status)
        
        self.setLayout(layout)
        self.setWindowTitle('Pika One-shot Calibrator')
        self.show()

    def on_click(self):
        success, msg = self.node.run_calibration()
        self.status.setText(f"status: {msg}")

def main():
    rclpy.init()
    node = PikaOneShotCalibrator()
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
    app = QApplication(sys.argv)
    window = CalibWindow(node)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()