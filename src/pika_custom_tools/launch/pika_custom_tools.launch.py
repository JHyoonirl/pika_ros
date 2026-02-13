import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():

    # 1. 기존 하드웨어 설정 인자
    declared_arguments = [
        DeclareLaunchArgument('serial_port', default_value='/dev/ttyUSB0'),
        DeclareLaunchArgument('joint_name', default_value='center_joint'),
        DeclareLaunchArgument('motor_current_limit', default_value='1000.0'),
        DeclareLaunchArgument('motor_current_redundancy', default_value='500.0'),
        DeclareLaunchArgument('mit_mode', default_value='true'),
        DeclareLaunchArgument('ctrl_rate', default_value='50.0'),
        
        # 2. [추가됨] prefix (여러 대 운영 시 사용)
        DeclareLaunchArgument('prefix', default_value=''),
        
        # 3. [추가됨] 노드 이름 변경용 인자
        DeclareLaunchArgument('node_name', default_value='pika_custom_tools'),

        # 3. [추가됨] 리매핑(Remapping)용 인자 (기본값은 기존 설정 유지)
        DeclareLaunchArgument('topic_imu', default_value='/imu/data'),
        DeclareLaunchArgument('topic_gripper_data', default_value='/gripper/data'),
        DeclareLaunchArgument('topic_gripper_ctrl', default_value='/gripper/ctrl'),
        DeclareLaunchArgument('topic_gripper_joint_state', default_value='/gripper/joint_state'),
        DeclareLaunchArgument('topic_gripper_joint_state_ctrl', default_value='/joint_states'),
        DeclareLaunchArgument('topic_joint_state_info', default_value='/joint_states_single'),
        DeclareLaunchArgument('topic_joint_state_gripper', default_value='/joint_states_single_gripper'),
        
        # 추가적인 상태 토픽들 (필요시 사용)
        DeclareLaunchArgument('topic_data_capture_status', default_value='/data_capture_status'),
        DeclareLaunchArgument('topic_teleop_status', default_value='/teleop_status'),
        DeclareLaunchArgument('topic_localization_status', default_value='/localization_status'),
        DeclareLaunchArgument('topic_arm_control_status', default_value='/arm_control_status'),
    ]

    # 설정값 변수 로드
    serial_port = LaunchConfiguration('serial_port')
    joint_name = LaunchConfiguration('joint_name')
    motor_current_limit = LaunchConfiguration('motor_current_limit')
    motor_current_redundancy = LaunchConfiguration('motor_current_redundancy')
    mit_mode = LaunchConfiguration('mit_mode')
    ctrl_rate = LaunchConfiguration('ctrl_rate')
    prefix = LaunchConfiguration('prefix')
    
    # 리매핑 변수 로드
    node_name = LaunchConfiguration('node_name')
    topic_imu = LaunchConfiguration('topic_imu')
    topic_gripper_data = LaunchConfiguration('topic_gripper_data')
    topic_gripper_ctrl = LaunchConfiguration('topic_gripper_ctrl')
    topic_gripper_joint_state = LaunchConfiguration('topic_gripper_joint_state')
    topic_gripper_joint_state_ctrl = LaunchConfiguration('topic_gripper_joint_state_ctrl')
    topic_joint_state_info = LaunchConfiguration('topic_joint_state_info')
    topic_joint_state_gripper = LaunchConfiguration('topic_joint_state_gripper')
    topic_data_capture_status = LaunchConfiguration('topic_data_capture_status')
    topic_teleop_status = LaunchConfiguration('topic_teleop_status')
    topic_localization_status = LaunchConfiguration('topic_localization_status')
    topic_arm_control_status = LaunchConfiguration('topic_arm_control_status')

    return LaunchDescription(declared_arguments + [
        Node(
            package='pika_custom_tools',
            executable='pika_custom_tools',
            name=node_name,
            namespace=prefix,
            parameters=[{'serial_port': serial_port,
                         'joint_name': joint_name,
                         'motor_current_limit': motor_current_limit,
                         'motor_current_redundancy': motor_current_redundancy,
                         'mit_mode': mit_mode,
                         'ctrl_rate': ctrl_rate}],
            remappings=[
                # Global 토픽만 remapping (절대경로)
                ('joint_state_info', topic_joint_state_info),
                ('joint_state_gripper', topic_joint_state_gripper),
                ('data_capture_status', topic_data_capture_status),
                ('teleop_status', topic_teleop_status),
                ('localization_status', topic_localization_status),
                ('arm_control_status', topic_arm_control_status),
                # Gripper control remapping (teleoperation용)
                ('gripper/joint_state_ctrl', topic_gripper_joint_state_ctrl),
            ],
            respawn=True,
            output='screen'
        )
    ])