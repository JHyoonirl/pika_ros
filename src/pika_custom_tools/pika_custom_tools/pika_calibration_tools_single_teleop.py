import sys
import signal
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, TransformStamped
from tf2_ros import Buffer, TransformListener, TransformBroadcaster
from scipy.spatial.transform import Rotation as R
import numpy as np
# [수정됨] GUI에 체크박스를 추가하기 위해 QCheckBox 임포트
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QCheckBox) 
from PyQt5.QtCore import Qt, QTimer
import threading
import yaml
import os

class PikaTfIntegrator(Node):
    def __init__(self, config_file=None):
        super().__init__('pika_tf_integrator')
        self.tf_buffer = Buffer(rclpy.duration.Duration(seconds=10.0))
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.current_pika_pose = None
        self.is_calibrated = False
        self.T_target = np.eye(4)
        self.M_world_from_pika = np.eye(4)
        
        # --- 필터 설정 변수 ---
        self.alpha = 0.2
        self.filtered_pos = None
        self.filtered_quat = None

        # [수정할 부분] 변수명을 직관적으로 xz로 변경
        self.enable_mirror_xz = False

        self.parent_frame = '/world' 
        self.local_frame = '/pika_local'
        self.target_frame = '/pika_target'
        
        # YAML 설정 파일 경로 (Docker 환경 고려)
        if config_file is None:
            config_dir = os.environ.get('PIKA_CONFIG_DIR')
            if config_dir is None:
                if os.path.exists('/root/pika_ros'):
                    workspace_root = '/root/pika_ros'
                elif os.path.exists('/home/irl/pika_ros'):
                    workspace_root = '/home/irl/pika_ros'
                else:
                    current_file = os.path.abspath(__file__)
                    workspace_root = os.path.abspath(os.path.join(current_file, '../../../../../..'))
                
                config_dir = os.path.join(workspace_root, 'src', 'pika_custom_tools', 'config')
            
            os.makedirs(config_dir, exist_ok=True)
            self.config_file = os.path.join(config_dir, 'pika_calibration_single_config.yaml')
            self.get_logger().info(f"[DEBUG] Config directory: {config_dir}")
            self.get_logger().info(f"[DEBUG] Config file: {self.config_file}")
        else:
            self.config_file = config_file
        
        self.create_subscription(PoseStamped, '/pika_pose', self.pika_cb, 10)
        self.create_timer(0.02, self.publish_loop)
        
        # 설정 로드
        self.load_config()

    def pika_cb(self, msg):
        raw_p = np.array([msg.pose.position.x, msg.pose.position.y, msg.pose.position.z])
        raw_q = np.array([msg.pose.orientation.x, msg.pose.orientation.y, 
                          msg.pose.orientation.z, msg.pose.orientation.w])

        if self.filtered_pos is None:
            self.filtered_pos = raw_p
            self.filtered_quat = raw_q
            self.current_pika_pose = msg
            return

        self.filtered_pos = self.alpha * raw_p + (1.0 - self.alpha) * self.filtered_pos

        if np.dot(self.filtered_quat, raw_q) < 0:
            raw_q = -raw_q
        
        new_q = self.alpha * raw_q + (1.0 - self.alpha) * self.filtered_quat
        self.filtered_quat = new_q / np.linalg.norm(new_q)

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

        T_out_mat = np.copy(T_local_mat)

        # [수정할 부분] 조건문의 변수명 변경
        if self.enable_mirror_xz: 
            M = np.array([[ 1.0,  0.0,  0.0],
                          [ 0.0, -1.0,  0.0],
                          [ 0.0,  0.0,  1.0]])
            
            T_out_mat[1, 3] = -T_out_mat[1, 3] 
            
            R_orig = T_out_mat[:3, :3]
            T_out_mat[:3, :3] = M @ R_orig @ M
        # --- XZ 평면 미러링 적용 로직 끝 ---

        T_target_mat = T_out_mat 
        self.broadcast_tf(T_out_mat, self.local_frame)
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
    
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    if config:
                        if 'target_xyz' in config:
                            self.T_target[:3, 3] = config['target_xyz']
                        if 'M_world_from_pika' in config:
                            self.M_world_from_pika = np.array(config['M_world_from_pika'])
                        if 'is_calibrated' in config:
                            self.is_calibrated = config['is_calibrated']
                        self.get_logger().info(f"Loaded calibration from {self.config_file}")
            except Exception as e:
                self.get_logger().warn(f"Failed to load config: {e}")
    
    def save_config(self):
        config = {
            'target_xyz': self.T_target[:3, 3].tolist(),
            'M_world_from_pika': self.M_world_from_pika.tolist(),
            'is_calibrated': self.is_calibrated
        }
        try:
            config_dir = os.path.dirname(self.config_file)
            self.get_logger().info(f"[DEBUG] Attempting to save to: {self.config_file}")
            self.get_logger().info(f"[DEBUG] Directory exists: {os.path.exists(config_dir)}")
            self.get_logger().info(f"[DEBUG] Directory writable: {os.access(config_dir, os.W_OK)}")
            
            os.makedirs(config_dir, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            if os.path.exists(self.config_file):
                file_size = os.path.getsize(self.config_file)
                self.get_logger().info(f"✓ Saved calibration to {self.config_file} ({file_size} bytes)")
            else:
                self.get_logger().warn(f"⚠ File write succeeded but file not found at {self.config_file}")
            return True
        except Exception as e:
            self.get_logger().error(f"✗ Failed to save config: {e}")
            import traceback
            self.get_logger().error(traceback.format_exc())
            return False

class CalibWindow(QWidget):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.initUI()

    def initUI(self):
        target_xyz = self.node.T_target[:3, 3]
        
        main_layout = QVBoxLayout()
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("X:")); self.edit_x = QLineEdit(str(target_xyz[0])); input_layout.addWidget(self.edit_x)
        input_layout.addWidget(QLabel("Y:")); self.edit_y = QLineEdit(str(target_xyz[1])); input_layout.addWidget(self.edit_y)
        input_layout.addWidget(QLabel("Z:")); self.edit_z = QLineEdit(str(target_xyz[2])); input_layout.addWidget(self.edit_z)
        
        self.btn = QPushButton('Calibration: Set Zero-point')
        self.btn.clicked.connect(self.on_click)
        self.btn.setMinimumHeight(40)
        
        # [수정됨] 미러링 On/Off 체크박스 인스턴스 생성 및 이벤트 연결
        self.mirror_cb = QCheckBox("Enable XZ Plane Mirroring (Y-axis Inverted)")
        self.mirror_cb.stateChanged.connect(self.on_mirror_toggle)

        self.status = QLabel('Status: Waiting for Calibration...')
        self.status.setAlignment(Qt.AlignCenter)

        self.btn_save = QPushButton('Save Config to YAML')
        self.btn_save.clicked.connect(self.on_save)
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setStyleSheet("background-color: #D1E7FF")
        
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.btn)
        # [수정됨] 레이아웃에 미러링 체크박스 추가
        main_layout.addWidget(self.mirror_cb) 
        main_layout.addWidget(self.status)
        main_layout.addWidget(self.btn_save)
        self.setLayout(main_layout)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           
        
        self.setWindowTitle('Pika Mapping Tools (Real-robot)')
        # [수정됨] 체크박스 추가로 인한 위젯 공간 확보 (높이를 240에서 280으로 늘림)
        self.resize(450, 280) 
        self.show()

    # [수정됨] 체크박스 토글 시 미러링 플래그를 변경하는 핸들러 함수
    def on_mirror_toggle(self, state):
        self.node.enable_mirror_xz = (state == Qt.Checked)
        
        if self.node.enable_mirror_xz:
            self.status.setText("Status: XZ Mirroring (Y-Inverted) ENABLED")
        else:
            self.status.setText("Status: Mirroring DISABLED")

    def on_click(self):
        try:
            x, y, z = float(self.edit_x.text()), float(self.edit_y.text()), float(self.edit_z.text())
            success, msg = self.node.run_calibration([x, y, z])
            self.status.setText(f"Status: {msg}")
            if success: self.btn.setStyleSheet("background-color: #D1FFD1")
        except ValueError:
            self.status.setText("Status: Error! Please enter valid numbers.")
            self.btn.setStyleSheet("background-color: #FFD1D1")
    
    def on_save(self):
        if self.node.save_config():
            self.btn_save.setStyleSheet("background-color: #A8D5A8")
            self.btn_save.setText("Config Saved!")
            QTimer.singleShot(2000, lambda: (
                self.btn_save.setText("Save Config to YAML"),
                self.btn_save.setStyleSheet("background-color: #D1E7FF")
            ))
        else:
            self.btn_save.setStyleSheet("background-color: #FFD1D1")
            self.btn_save.setText("Save Failed!")
            QTimer.singleShot(2000, lambda: (
                self.btn_save.setText("Save Config to YAML"),
                self.btn_save.setStyleSheet("background-color: #D1E7FF")
            ))

def main():
    rclpy.init()
    node = PikaTfIntegrator()
    
    ros_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    ros_thread.start()
    
    app = QApplication(sys.argv)
    window = CalibWindow(node)

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None) 

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