import sys
import signal  # 추가
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, TransformStamped
from tf2_ros import Buffer, TransformListener, TransformBroadcaster
from scipy.spatial.transform import Rotation as R
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QGroupBox)
from PyQt5.QtCore import Qt, QTimer  # QTimer 추가
import threading
import yaml
import os

class PikaTfIntegrator(Node):
    def __init__(self, config_file=None):
        super().__init__('pika_tf_integrator')
        self.tf_buffer = Buffer(rclpy.duration.Duration(seconds=10.0))
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # 좌우 pika pose 데이터 저장
        self.current_pika_pose_l = None
        self.current_pika_pose_r = None
        
        # 좌우 캘리브레이션 상태
        self.is_calibrated_l = False
        self.is_calibrated_r = False
        
        # 좌우 변환 행렬
        self.T_target_l = np.eye(4)
        self.T_target_r = np.eye(4)
        self.M_world_from_pika_l = np.eye(4)
        self.M_world_from_pika_r = np.eye(4)
        
        # --- 필터 설정 변수 (좌우 각각) ---
        self.alpha = 0.2  # 필터 계수 (0.0 ~ 1.0): 낮을수록 부드럽고, 높을수록 반응 빠름
        self.filtered_pos_l = None
        self.filtered_quat_l = None
        self.filtered_pos_r = None
        self.filtered_quat_r = None

        self.parent_frame = '/world' 
        self.local_frame_l = '/pika_local_l'
        self.target_frame_l = '/pika_target_l'
        self.local_frame_r = '/pika_local_r'
        self.target_frame_r = '/pika_target_r'
        
        # YAML 설정 파일 경로 (소스 디렉토리의 config 폴더)
        if config_file is None:
            # 워크스페이스 루트 찾기 (build/install이 아닌 src 디렉토리 사용)
            current_file = os.path.abspath(__file__)
            # /path/to/pika_ros/build_new/pika_custom_tools/... 또는 /path/to/pika_ros/src/pika_custom_tools/...
            workspace_root = os.path.abspath(os.path.join(current_file, '../../../../../..'))
            config_dir = os.path.join(workspace_root, 'src', 'pika_custom_tools', 'config')
            os.makedirs(config_dir, exist_ok=True)
            self.config_file = os.path.join(config_dir, 'pika_calibration_config.yaml')
        else:
            self.config_file = config_file
        
        # 토픽 구독
        self.create_subscription(PoseStamped, '/pika_pose_l', self.pika_cb_l, 10)
        self.create_subscription(PoseStamped, '/pika_pose_r', self.pika_cb_r, 10)
        self.create_timer(0.02, self.publish_loop)
        
        # 설정 로드
        self.load_config()

    def pika_cb_l(self, msg):
        """왼쪽 pika pose 콜백"""
        self._apply_filter(msg, 'l')
    
    def pika_cb_r(self, msg):
        """오른쪽 pika pose 콜백"""
        self._apply_filter(msg, 'r')
    
    def _apply_filter(self, msg, side):
        """좌우 공통 필터 적용 로직"""
        # 1. 원본 데이터 추출
        raw_p = np.array([msg.pose.position.x, msg.pose.position.y, msg.pose.position.z])
        raw_q = np.array([msg.pose.orientation.x, msg.pose.orientation.y, 
                          msg.pose.orientation.z, msg.pose.orientation.w])

        # side에 따라 다른 변수 사용
        if side == 'l':
            filtered_pos = self.filtered_pos_l
            filtered_quat = self.filtered_quat_l
        else:
            filtered_pos = self.filtered_pos_r
            filtered_quat = self.filtered_quat_r

        # 2. 최초 데이터 처리
        if filtered_pos is None:
            if side == 'l':
                self.filtered_pos_l = raw_p
                self.filtered_quat_l = raw_q
                self.current_pika_pose_l = msg
            else:
                self.filtered_pos_r = raw_p
                self.filtered_quat_r = raw_q
                self.current_pika_pose_r = msg
            return

        # 3. 위치 필터링 (EMA)
        filtered_pos = self.alpha * raw_p + (1.0 - self.alpha) * filtered_pos

        # 4. 회전 필터링
        if np.dot(filtered_quat, raw_q) < 0:
            raw_q = -raw_q
        
        new_q = self.alpha * raw_q + (1.0 - self.alpha) * filtered_quat
        filtered_quat = new_q / np.linalg.norm(new_q)

        # 5. 필터링된 결과 저장
        if side == 'l':
            self.filtered_pos_l = filtered_pos
            self.filtered_quat_l = filtered_quat
            self.current_pika_pose_l = msg
            self.current_pika_pose_l.pose.position.x = filtered_pos[0]
            self.current_pika_pose_l.pose.position.y = filtered_pos[1]
            self.current_pika_pose_l.pose.position.z = filtered_pos[2]
            self.current_pika_pose_l.pose.orientation.x = filtered_quat[0]
            self.current_pika_pose_l.pose.orientation.y = filtered_quat[1]
            self.current_pika_pose_l.pose.orientation.z = filtered_quat[2]
            self.current_pika_pose_l.pose.orientation.w = filtered_quat[3]
        else:
            self.filtered_pos_r = filtered_pos
            self.filtered_quat_r = filtered_quat
            self.current_pika_pose_r = msg
            self.current_pika_pose_r.pose.position.x = filtered_pos[0]
            self.current_pika_pose_r.pose.position.y = filtered_pos[1]
            self.current_pika_pose_r.pose.position.z = filtered_pos[2]
            self.current_pika_pose_r.pose.orientation.x = filtered_quat[0]
            self.current_pika_pose_r.pose.orientation.y = filtered_quat[1]
            self.current_pika_pose_r.pose.orientation.z = filtered_quat[2]
            self.current_pika_pose_r.pose.orientation.w = filtered_quat[3]

    def run_calibration(self, target_xyz, side):
        """좌우 개별 캘리브레이션 실행"""
        if side == 'l':
            current_pose = self.current_pika_pose_l
            if current_pose is None:
                return False, "Error: No Left Pika data received yet."
            self.T_target_l[:3, 3] = target_xyz
            p, q = current_pose.pose.position, current_pose.pose.orientation
            T_pika_init = np.eye(4)
            T_pika_init[:3, :3] = R.from_quat([q.x, q.y, q.z, q.w]).as_matrix()
            T_pika_init[:3, 3] = [p.x, p.y, p.z]
            self.M_world_from_pika_l = self.T_target_l @ np.linalg.inv(T_pika_init)
            self.is_calibrated_l = True
            return True, f"Left Calibration Complete: {self.T_target_l[:3, 3]}"
        else:
            current_pose = self.current_pika_pose_r
            if current_pose is None:
                return False, "Error: No Right Pika data received yet."
            self.T_target_r[:3, 3] = target_xyz
            p, q = current_pose.pose.position, current_pose.pose.orientation
            T_pika_init = np.eye(4)
            T_pika_init[:3, :3] = R.from_quat([q.x, q.y, q.z, q.w]).as_matrix()
            T_pika_init[:3, 3] = [p.x, p.y, p.z]
            self.M_world_from_pika_r = self.T_target_r @ np.linalg.inv(T_pika_init)
            self.is_calibrated_r = True
            return True, f"Right Calibration Complete: {self.T_target_r[:3, 3]}"

    def publish_loop(self):
        """좌우 TF 브로드캐스트"""
        # 왼쪽 TF 퍼블리시
        if self.is_calibrated_l and self.current_pika_pose_l is not None:
            p, q = self.current_pika_pose_l.pose.position, self.current_pika_pose_l.pose.orientation
            T_pika_curr = np.eye(4)
            T_pika_curr[:3, :3] = R.from_quat([q.x, q.y, q.z, q.w]).as_matrix()
            T_pika_curr[:3, 3] = [p.x, p.y, p.z]
            T_local_mat = self.M_world_from_pika_l @ T_pika_curr
            R_y_90 = R.from_euler('y', 90, degrees=True).as_matrix()
            T_rot_offset = np.eye(4)
            T_rot_offset[:3, :3] = R_y_90
            T_target_mat = T_local_mat @ T_rot_offset
            self.broadcast_tf(T_local_mat, self.local_frame_l)
            self.broadcast_tf(T_target_mat, self.target_frame_l)
        
        # 오른쪽 TF 퍼블리시
        if self.is_calibrated_r and self.current_pika_pose_r is not None:
            p, q = self.current_pika_pose_r.pose.position, self.current_pika_pose_r.pose.orientation
            T_pika_curr = np.eye(4)
            T_pika_curr[:3, :3] = R.from_quat([q.x, q.y, q.z, q.w]).as_matrix()
            T_pika_curr[:3, 3] = [p.x, p.y, p.z]
            T_local_mat = self.M_world_from_pika_r @ T_pika_curr
            R_y_90 = R.from_euler('y', 90, degrees=True).as_matrix()
            T_rot_offset = np.eye(4)
            T_rot_offset[:3, :3] = R_y_90
            T_target_mat = T_local_mat @ T_rot_offset
            self.broadcast_tf(T_local_mat, self.local_frame_r)
            self.broadcast_tf(T_target_mat, self.target_frame_r)

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
        """YAML 파일에서 캘리브레이션 설정 로드"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    if config:
                        # 왼쪽 설정
                        if 'left' in config:
                            left_cfg = config['left']
                            if 'target_xyz' in left_cfg:
                                self.T_target_l[:3, 3] = left_cfg['target_xyz']
                            if 'M_world_from_pika' in left_cfg:
                                self.M_world_from_pika_l = np.array(left_cfg['M_world_from_pika'])
                            if 'is_calibrated' in left_cfg:
                                self.is_calibrated_l = left_cfg['is_calibrated']
                        
                        # 오른쪽 설정
                        if 'right' in config:
                            right_cfg = config['right']
                            if 'target_xyz' in right_cfg:
                                self.T_target_r[:3, 3] = right_cfg['target_xyz']
                            if 'M_world_from_pika' in right_cfg:
                                self.M_world_from_pika_r = np.array(right_cfg['M_world_from_pika'])
                            if 'is_calibrated' in right_cfg:
                                self.is_calibrated_r = right_cfg['is_calibrated']
                        
                        self.get_logger().info(f"Loaded calibration from {self.config_file}")
            except Exception as e:
                self.get_logger().warn(f"Failed to load config: {e}")
    
    def save_config(self):
        """YAML 파일에 캘리브레이션 설정 저장"""
        config = {
            'left': {
                'target_xyz': self.T_target_l[:3, 3].tolist(),
                'M_world_from_pika': self.M_world_from_pika_l.tolist(),
                'is_calibrated': self.is_calibrated_l
            },
            'right': {
                'target_xyz': self.T_target_r[:3, 3].tolist(),
                'M_world_from_pika': self.M_world_from_pika_r.tolist(),
                'is_calibrated': self.is_calibrated_r
            }
        }
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            self.get_logger().info(f"Saved calibration to {self.config_file}")
            return True
        except Exception as e:
            self.get_logger().error(f"Failed to save config: {e}")
            return False

class CalibWindow(QWidget):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        
        # YAML에서 로드된 값 가져오기 (없으면 기본값)
        left_xyz = self.node.T_target_l[:3, 3]
        right_xyz = self.node.T_target_r[:3, 3]
        
        # 왼쪽 Pika 그룹
        left_group = QGroupBox("Left Pika (/pika_pose_l)")
        left_layout = QVBoxLayout()
        left_input_layout = QHBoxLayout()
        left_input_layout.addWidget(QLabel("X:")); self.edit_x_l = QLineEdit(str(left_xyz[0])); left_input_layout.addWidget(self.edit_x_l)
        left_input_layout.addWidget(QLabel("Y:")); self.edit_y_l = QLineEdit(str(left_xyz[1])); left_input_layout.addWidget(self.edit_y_l)
        left_input_layout.addWidget(QLabel("Z:")); self.edit_z_l = QLineEdit(str(left_xyz[2])); left_input_layout.addWidget(self.edit_z_l)
        self.btn_l = QPushButton('Calibrate Left')
        self.btn_l.clicked.connect(lambda: self.on_click('l'))
        self.btn_l.setMinimumHeight(40)
        self.status_l = QLabel('Status: Waiting for Calibration...')
        self.status_l.setAlignment(Qt.AlignCenter)
        left_layout.addLayout(left_input_layout)
        left_layout.addWidget(self.btn_l)
        left_layout.addWidget(self.status_l)
        left_group.setLayout(left_layout)
        
        # 오른쪽 Pika 그룹
        right_group = QGroupBox("Right Pika (/pika_pose_r)")
        right_layout = QVBoxLayout()
        right_input_layout = QHBoxLayout()
        right_input_layout.addWidget(QLabel("X:")); self.edit_x_r = QLineEdit(str(right_xyz[0])); right_input_layout.addWidget(self.edit_x_r)
        right_input_layout.addWidget(QLabel("Y:")); self.edit_y_r = QLineEdit(str(right_xyz[1])); right_input_layout.addWidget(self.edit_y_r)
        right_input_layout.addWidget(QLabel("Z:")); self.edit_z_r = QLineEdit(str(right_xyz[2])); right_input_layout.addWidget(self.edit_z_r)
        self.btn_r = QPushButton('Calibrate Right')
        self.btn_r.clicked.connect(lambda: self.on_click('r'))
        self.btn_r.setMinimumHeight(40)
        self.status_r = QLabel('Status: Waiting for Calibration...')
        self.status_r.setAlignment(Qt.AlignCenter)
        right_layout.addLayout(right_input_layout)
        right_layout.addWidget(self.btn_r)
        right_layout.addWidget(self.status_r)
        right_group.setLayout(right_layout)
        
        # 저장 버튼
        self.btn_save = QPushButton('Save Config to YAML')
        self.btn_save.clicked.connect(self.on_save)
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setStyleSheet("background-color: #D1E7FF")
        
        main_layout.addWidget(left_group)
        main_layout.addWidget(right_group)
        main_layout.addWidget(self.btn_save)
        
        self.setLayout(main_layout)
        self.setWindowTitle('Pika Dual Mapping Tools (Real-robot)')
        self.resize(500, 450)
        self.show()

    def on_click(self, side):
        try:
            if side == 'l':
                x, y, z = float(self.edit_x_l.text()), float(self.edit_y_l.text()), float(self.edit_z_l.text())
                success, msg = self.node.run_calibration([x, y, z], 'l')
                self.status_l.setText(f"Status: {msg}")
                if success: self.btn_l.setStyleSheet("background-color: #D1FFD1")
            else:
                x, y, z = float(self.edit_x_r.text()), float(self.edit_y_r.text()), float(self.edit_z_r.text())
                success, msg = self.node.run_calibration([x, y, z], 'r')
                self.status_r.setText(f"Status: {msg}")
                if success: self.btn_r.setStyleSheet("background-color: #D1FFD1")
        except ValueError:
            if side == 'l':
                self.status_l.setText("Status: Error! Please enter valid numbers.")
                self.btn_l.setStyleSheet("background-color: #FFD1D1")
            else:
                self.status_r.setText("Status: Error! Please enter valid numbers.")
                self.btn_r.setStyleSheet("background-color: #FFD1D1")
    
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