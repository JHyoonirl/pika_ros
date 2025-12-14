SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
camera_fps=30
camera_width=640
camera_height=480
sudo sh -c 'echo "KERNEL==\"ttyUSB*\", ATTRS{idVendor}==\"1a86\", ATTRS{idProduct}==\"7522\", MODE:=\"0777\", SYMLINK+=\"ttyUSB0\"" > /etc/udev/rules.d/sensor_serial.rules'
sudo sh -c 'echo "KERNEL==\"video*\", ATTRS{idVendor}==\"1bcf\", ATTRS{idProduct}==\"2cd1\", MODE:=\"0777\", SYMLINK+=\"video7\"" > /etc/udev/rules.d/sensor_fisheye.rules'
sudo udevadm control --reload-rules && sudo service udev restart && sudo udevadm trigger

sudo chmod a+rw /dev/ttyUSB*
sudo chmod a+rw /dev/video*

source /opt/ros/humble/setup.bash && cd /root/pika_ros/install/sensor_tools/share/sensor_tools/scripts/ && chmod 777 usb_camera.py
source /root/pika_ros/install/setup.bash && ros2 launch sensor_tools open_single_sensor.launch.py serial_port:=/dev/ttyUSB0 fisheye_port:=6 camera_fps:=$camera_fps camera_width:=$camera_width camera_height:=$camera_height camera_profile:=$camera_width,$camera_height,$camera_fps joint_name:=center_joint
# source /root/pika_ros/install_new/setup.bash && ros2 launch pika_custom_tools pika_custom_tools.launch.py serial_port:=/dev/ttyUSB0 joint_name:=center_joint

