import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch import LaunchContext

def generate_launch_description():

    declared_arguments = [
        DeclareLaunchArgument('serial_port', default_value='/dev/ttyUSB0'),
        DeclareLaunchArgument('joint_name', default_value='center_joint'),
        DeclareLaunchArgument('motor_current_limit', default_value='1000.0'),
        DeclareLaunchArgument('motor_current_redundancy', default_value='500.0'),
        DeclareLaunchArgument('mit_mode', default_value='true'),
        DeclareLaunchArgument('ctrl_rate', default_value='50.0')
    ]

    serial_port = LaunchConfiguration('serial_port')
    joint_name = LaunchConfiguration('joint_name')
    motor_current_limit = LaunchConfiguration('motor_current_limit')
    motor_current_redundancy = LaunchConfiguration('motor_current_redundancy')
    mit_mode = LaunchConfiguration('mit_mode')
    ctrl_rate = LaunchConfiguration('ctrl_rate')

    return LaunchDescription(declared_arguments+[
        Node(
            package='pika_custom_tools',
            executable='pika_custom_tools',
            name='pika_custom_tools',
            parameters=[{'serial_port': serial_port,
                         'joint_name': joint_name,
                         'motor_current_limit': motor_current_limit,
                         'motor_current_redundancy': motor_current_redundancy,
                         'mit_mode': mit_mode,
                         'ctrl_rate': ctrl_rate}],
            remappings=[
                ('/imu/data', '/imu/data'),
                ('/gripper/data', '/gripper/data'),
                ('/gripper/ctrl', '/gripper/ctrl'),
                ('/gripper/joint_state', '/gripper/joint_state'),
                ('/gripper/joint_state_ctrl', '/joint_states'),
                ('/joint_state_info', '/joint_states_single'),
                ('/joint_state_gripper', '/joint_states_single_gripper'),
            ],
            respawn=True,
            output='screen'
        )
    ])