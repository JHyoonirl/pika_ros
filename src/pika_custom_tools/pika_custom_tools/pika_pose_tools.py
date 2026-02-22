import sys
import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, TransformStamped
from tf2_ros import TransformBroadcaster
import pysurvive
from scipy.spatial.transform import Rotation as R

class ViveTrackerROS2(Node):
    def __init__(self):
        super().__init__('vive_tracker_node')
        
        # 1. TF 및 Pose 퍼블리셔 설정
        self.tf_broadcaster = TransformBroadcaster(self)
        self.pose_pub = self.create_publisher(PoseStamped, '/vive/tracker_pose', 10)
        
        # 2. libsurvive 초기화
        self.ctx = pysurvive.SimpleContext(sys.argv)
        
        # 3. 상태 관리 변수 (None이면 아직 캘리브레이션 전)
        self.origin_inv = None
        
        # 필터링을 위한 이전 값 저장 변수
        self.prev_pos = None
        self.prev_quat = None
        
        # 필터 계수 설정 (0.0 ~ 1.0)
        # 0.1 ~ 0.3 사이에서 지터와 지연 시간을 트레이드오프 해보세요.
        self.alpha = 0.2
        
        # 4. 업데이트 타이머 (약 60Hz)
        self.timer = self.create_timer(0.016, self.update_tracker)
        
        self.get_logger().info("Vive Tracker Node Started. Waiting for first valid pose to auto-calibrate...")

    def pose_to_matrix(self, pos, rot_wq):
        """[w, x, y, z] 쿼터니언을 [x, y, z, w]로 변환하여 4x4 행렬 생성"""
        # SciPy는 [x, y, z, w] 순서를 사용함
        r = R.from_quat([rot_wq[1], rot_wq[2], rot_wq[3], rot_wq[0]])
        mat = np.eye(4)
        mat[:3, :3] = r.as_matrix()
        mat[:3, 3] = pos
        return mat

    def update_tracker(self):
        """데이터 수신 시 자동 캘리브레이션 및 TF/Pose 발행"""
        updated_obj = self.ctx.NextUpdated()
        
        while updated_obj is not None:
            raw_name = updated_obj.Name()
            obj_name = raw_name.decode('utf-8') if isinstance(raw_name, bytes) else raw_name

            # 등대 기기는 제외
            if "LHB" in obj_name or "LH" == obj_name[:2]:
                updated_obj = self.ctx.NextUpdated()
                continue

            # 포즈 데이터 추출 (튜플의 첫 번째 요소인 객체 접근)
            pose_tuple = updated_obj.Pose()
            pose_obj = pose_tuple[0]
            curr_pos = pose_obj.Pos
            curr_rot = pose_obj.Rot

            # 0,0,0 데이터(인식 불량)인 경우 무시
            if np.all(curr_pos == 0.0):
                updated_obj = self.ctx.NextUpdated()
                continue

            # 현재 원시 행렬(Raw Matrix) 계산
            T_raw = self.pose_to_matrix(curr_pos, curr_rot)

            if self.origin_inv is None:
                self.origin_inv = np.linalg.inv(T_raw)
                self.get_logger().info("Auto-Calibration Done.")

            T_rel = self.origin_inv @ T_raw
            
            # --- [필터링 시작] ---
            raw_pos = T_rel[:3, 3]
            raw_quat = R.from_matrix(T_rel[:3, :3]).as_quat()

            if self.prev_pos is None:
                self.prev_pos = raw_pos
                self.prev_quat = raw_quat
            
            # 위치 필터링 (EMA)
            filtered_pos = (self.alpha * raw_pos) + ((1 - self.alpha) * self.prev_pos)
            
            # 회전 필터링 (Slerp를 써야 하지만, 작은 노이즈라면 EMA로도 효과가 있습니다)
            # 쿼터니언 필터링 후에는 반드시 정규화(Normalization)가 필요합니다.
            filtered_quat_raw = (self.alpha * raw_quat) + ((1 - self.alpha) * self.prev_quat)
            filtered_quat = filtered_quat_raw / np.linalg.norm(filtered_quat_raw)

            # 이전 값 업데이트
            self.prev_pos = filtered_pos
            self.prev_quat = filtered_quat
            # --- [필터링 끝] ---

            # 필터링된 데이터를 담은 T_final 생성
            T_final = np.eye(4)
            T_final[:3, :3] = R.from_quat(filtered_quat).as_matrix()
            T_final[:3, 3] = filtered_pos

            self.publish_data(T_final, obj_name)
            updated_obj = self.ctx.NextUpdated()

    def publish_data(self, T_matrix, frame_id):
        """TF와 PoseStamped를 동시에 발행"""
        pos = T_matrix[:3, 3]
        quat = R.from_matrix(T_matrix[:3, :3]).as_quat() # [x, y, z, w]

        now = self.get_clock().now().to_msg()

        # TF 발행
        t = TransformStamped()
        t.header.stamp = now
        t.header.frame_id = 'world'
        t.child_frame_id = frame_id
        t.transform.translation.x = pos[0]
        t.transform.translation.y = pos[1]
        t.transform.translation.z = pos[2]
        t.transform.rotation.x = quat[0]
        t.transform.rotation.y = quat[1]
        t.transform.rotation.z = quat[2]
        t.transform.rotation.w = quat[3]
        self.tf_broadcaster.sendTransform(t)

        # PoseStamped 발행
        p = PoseStamped()
        p.header = t.header
        p.pose.position.x = pos[0]
        p.pose.position.y = pos[1]
        p.pose.position.z = pos[2]
        p.pose.orientation.x = quat[0]
        p.pose.orientation.y = quat[1]
        p.pose.orientation.z = quat[2]
        p.pose.orientation.w = quat[3]
        self.pose_pub.publish(p)

def main(args=None):
    rclpy.init(args=args)
    node = ViveTrackerROS2()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()