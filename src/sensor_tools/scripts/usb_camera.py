#!/usr/bin/env python3
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge, CvBridgeError
import cv2
import os
import threading 
import signal
import sys
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped


class RosOperator(Node):
    def __init__(self): 
        super().__init__('camera_fisheye')
        self.cap = None
        self.camera_port = None
        self.camera_hz = None
        self.camera_height = None
        self.camera_width = None
        self.bridge = None
        self.camera_color_publisher = None
        self.camera_config_publisher = None
        self.camera_frame_id = None
        self.tf_broadcaster = None
        self.running = False  # 添加运行状态标志
        self.camera_thread = None  # 添加线程引用
        self.init_ros()

    def init_ros(self):
        self.declare_parameter('camera_port', 22)
        self.declare_parameter('camera_fps', 30)
        self.declare_parameter('camera_height', 480)
        self.declare_parameter('camera_width', 640)
        self.declare_parameter('camera_frame_id', "camera_rgb")
        self.camera_port = self.get_parameter('camera_port').get_parameter_value().integer_value
        self.camera_hz = int(self.get_parameter('camera_fps').get_parameter_value().integer_value)
        self.camera_height = int(self.get_parameter('camera_height').get_parameter_value().integer_value)
        self.camera_width = int(self.get_parameter('camera_width').get_parameter_value().integer_value)
        self.camera_frame_id = self.get_parameter('camera_frame_id').get_parameter_value().string_value
        if self.camera_frame_id.startswith('/'):
            self.camera_frame_id = self.camera_frame_id[1:]
        self.bridge = CvBridge()
        self.camera_color_publisher = self.create_publisher(Image, '/camera_rgb/color/image_raw', 10)
        self.camera_config_publisher = self.create_publisher(CameraInfo, '/camera_rgb/color/camera_info', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

    def init_camera(self):
        symlink_path = '/dev/video' + str(self.camera_port)
        if os.path.islink(symlink_path):
            target_path = os.readlink(symlink_path)
            target_path = int(target_path[5:])
            target_paths = []
            if target_path % 2 == 1:
                target_paths.append(target_path - 1)
                target_paths.append(target_path)
            else:
                target_paths.append(target_path)
                target_paths.append(target_path - 1)
        else:
            target_paths = [int(self.camera_port)]
        for i in target_paths:
            self.cap = cv2.VideoCapture(int(i))
            self.fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            self.cap.set(cv2.CAP_PROP_FOURCC, self.fourcc)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.camera_hz)
            if self.cap.isOpened():
                return True
            else:
                if self.cap:
                    self.cap.release()  # 释放失败的摄像头
                continue
        return False
    
    def run(self):
        rate = self.create_rate(self.camera_hz)
        self.running = True
        try:
            # rclpy.ok()를 체크하여 셧다운 시 루프 즉시 탈출
            while rclpy.ok() and self.running and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    # 컨텍스트 유효성 체크 후 퍼블리시
                    if rclpy.ok():
                        self.publish_camera_color(frame)
                rate.sleep()
        except Exception as e:
            if rclpy.ok(): # 셧다운 중 발생하는 에러는 무시
                self.get_logger().error(f"Camera error: {e}")
        finally:
            self.cleanup_camera()

    def cleanup_camera(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()
            # 노드가 살아있을 때만 로깅
            if rclpy.ok():
                self.get_logger().info("Camera released")
    
    def stop(self):
        """停止摄像头操作"""
        self.running = False
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.join(timeout=2.0)  # 等待线程结束

    def publish_camera_color(self, color):
        img = self.bridge.cv2_to_imgmsg(color, "bgr8")
        img.header.stamp = self.get_clock().now().to_msg()
        img.header.frame_id = self.camera_frame_id + "_color"
        self.camera_color_publisher.publish(img)
        camera_info = CameraInfo()
        camera_info.header.frame_id = self.camera_frame_id + "_color"
        camera_info.header.stamp = self.get_clock().now().to_msg()
        self.camera_config_publisher.publish(camera_info)
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = self.camera_frame_id
        t.child_frame_id = self.camera_frame_id + "_color"
        t.transform.translation.x = 0.0
        t.transform.translation.y = 0.0
        t.transform.translation.z = 0.0
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = 0.0
        t.transform.rotation.w = 1.0
        self.tf_broadcaster.sendTransform(t)


# 全局变量用于信号处理
ros_operator_instance = None

def signal_handler(signum, frame):
    """신호가 오면 플래그만 변경하여 안전하게 종료 유도"""
    global ros_operator_instance
    if ros_operator_instance:
        ros_operator_instance.running = False
    # rclpy.shutdown()을 여기서 하지 않습니다. 
    # rclpy.spin()이 KeyboardInterrupt 등으로 깨어나게 됩니다.

def main():
    global ros_operator_instance
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    rclpy.init()
    ros_operator_instance = RosOperator()
    
    try:
        if ros_operator_instance.init_camera():
            print("camera opened")
            ros_operator_instance.camera_thread = threading.Thread(target=ros_operator_instance.run)
            # daemon=True는 유지하되, stop()으로 명시적 join 권장
            ros_operator_instance.camera_thread.daemon = True 
            ros_operator_instance.camera_thread.start()
            
            rclpy.spin(ros_operator_instance)
        else:
            print("camera error")
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except Exception as e:
        print(f"Main Error: {e}")
    finally:
        # 종료 처리는 오직 여기서 딱 한 번만!
        if ros_operator_instance:
            ros_operator_instance.stop()
        
        if rclpy.ok():
            rclpy.shutdown()
        print("Program terminated safely")


if __name__ == '__main__':
    main()



# #!/usr/bin/env python3
# import rclpy
# from rclpy.node import Node
# from sensor_msgs.msg import Image, CameraInfo
# from cv_bridge import CvBridge, CvBridgeError
# import cv2
# import os
# import threading 
# from tf2_ros import TransformBroadcaster
# from geometry_msgs.msg import TransformStamped


# class RosOperator(Node):
#     def __init__(self): 
#         super().__init__('camera_fisheye')
#         self.cap = None
#         self.camera_port = None
#         self.camera_hz = None
#         self.camera_height = None
#         self.camera_width = None
#         self.bridge = None
#         self.camera_color_publisher = None
#         self.camera_config_publisher = None
#         self.camera_frame_id = None
#         self.tf_broadcaster = None
#         self.init_ros()

#     def init_ros(self):
#         self.declare_parameter('camera_port', 22)
#         self.declare_parameter('camera_fps', 30)
#         self.declare_parameter('camera_height', 480)
#         self.declare_parameter('camera_width', 640)
#         self.declare_parameter('camera_frame_id', "camera_rgb")
#         self.camera_port = self.get_parameter('camera_port').get_parameter_value().integer_value
#         self.camera_hz = int(self.get_parameter('camera_fps').get_parameter_value().integer_value)
#         self.camera_height = int(self.get_parameter('camera_height').get_parameter_value().integer_value)
#         self.camera_width = int(self.get_parameter('camera_width').get_parameter_value().integer_value)
#         self.camera_frame_id = self.get_parameter('camera_frame_id').get_parameter_value().string_value
#         self.bridge = CvBridge()
#         self.camera_color_publisher = self.create_publisher(Image, '/camera_rgb/color/image_raw', 10)
#         self.camera_config_publisher = self.create_publisher(CameraInfo, '/camera_rgb/color/camera_info', 10)
#         self.tf_broadcaster = TransformBroadcaster(self)

#     def init_camera(self):
#         symlink_path = '/dev/video' + str(self.camera_port)
#         if os.path.islink(symlink_path):
#             target_path = os.readlink(symlink_path)
#             target_path = int(target_path[5:])
#             target_paths = []
#             if target_path % 2 == 1:
#                 target_paths.append(target_path - 1)
#                 target_paths.append(target_path)
#             else:
#                 target_paths.append(target_path)
#                 target_paths.append(target_path - 1)
#         else:
#             target_paths = [int(self.camera_port)]
#         for i in target_paths:
#             self.cap = cv2.VideoCapture(int(i))
#             self.fourcc = cv2.VideoWriter_fourcc(*'MJPG')
#             self.cap.set(cv2.CAP_PROP_FOURCC, self.fourcc)
#             self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
#             self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
#             self.cap.set(cv2.CAP_PROP_FPS, self.camera_hz)
#             if self.cap.isOpened():
#                 return True
#             else:
#                 continue
#         return False
    
#     def run(self):
#         rate = self.create_rate(self.camera_hz)
#         while self.cap.isOpened() and rclpy.ok():
#             ret, frame = self.cap.read()
#             self.publish_camera_color(frame)
#             rate.sleep()

#     def publish_camera_color(self, color):
#         img = self.bridge.cv2_to_imgmsg(color, "bgr8")
#         img.header.frame_id = "camera"
#         img.header.stamp = self.get_clock().now().to_msg()
#         img.header.frame_id = self.camera_frame_id + "_color"
#         self.camera_color_publisher.publish(img)
#         camera_info = CameraInfo()
#         camera_info.header.frame_id = self.camera_frame_id + "_color"
#         camera_info.header.stamp = self.get_clock().now().to_msg()
#         self.camera_config_publisher.publish(camera_info)
#         t = TransformStamped()
#         t.header.stamp = self.get_clock().now().to_msg()
#         t.header.frame_id = self.camera_frame_id
#         t.child_frame_id = self.camera_frame_id + "_color"
#         t.transform.translation.x = 0.0
#         t.transform.translation.y = 0.0
#         t.transform.translation.z = 0.0
#         t.transform.rotation.x = 0.0
#         t.transform.rotation.y = 0.0
#         t.transform.rotation.z = 0.0
#         t.transform.rotation.w = 1.0
#         self.tf_broadcaster.sendTransform(t)


# def main():
#     rclpy.init()
#     ros_operator = RosOperator()
#     if ros_operator.init_camera():
#         print("camera opened")
#         thread = threading.Thread(target=ros_operator.run)
#         thread.start()
#         rclpy.spin(ros_operator)
#     else:
#         print("camera error")
#     rclpy.shutdown()


# if __name__ == '__main__':
#     main()
