#!/bin/bash

# --- 로그 및 색상 설정 ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

function log_info() { echo -e "${GREEN}[INFO] $(date '+%H:%M:%S') > $1${NC}"; }
function log_warn() { echo -e "${YELLOW}[WARN] $(date '+%H:%M:%S') > $1${NC}"; }
function log_error() { echo -e "${RED}[ERROR] $(date '+%H:%M:%S') > $1${NC}"; }

log_info "스크립트 시작: Pika Dual System (Final Version)"
log_info "전략: 모터는 스크립트가(Phase 1), 카메라는 런치 파일이(Phase 2) 실행합니다."

# =========================================================
# 1. 장치 설정
# =========================================================
# Right Sensor
SENSOR_SERIAL_LINK="/dev/pika_sensor_right_serial"
SENSOR_VIDEO_LINK="/dev/pika_sensor_right_video"
SENSOR_SN="315122270900"

# Right Gripper
GRIPPER_SERIAL_LINK="/dev/pika_gripper_right_serial"
GRIPPER_VIDEO_LINK="/dev/pika_gripper_right_video"
GRIPPER_SN="315122270807"

# [중요] FPS 15 (USB 대역폭 보호)
CAMERA_FPS=30
WIDTH=640
HEIGHT=480

# =========================================================
# 2. 링크 확인 및 인덱스 추출
# =========================================================
function check_and_get_index() {
    local link_path=$1
    if [ ! -e "$link_path" ]; then
        log_error "실패: $link_path 장치가 없습니다. setup_devices.bash를 실행하세요."
        exit 1
    fi
    local real_path=$(readlink -f "$link_path")
    local idx=$(basename "$real_path" | grep -o "[0-9]*")
    echo "$idx"
}

log_info "장치 연결 확인 중..."

SENSOR_IDX=$(check_and_get_index "$SENSOR_VIDEO_LINK")
GRIPPER_IDX=$(check_and_get_index "$GRIPPER_VIDEO_LINK")

log_info "매핑 확인:"
echo "  [Sensor]  Serial: $SENSOR_SERIAL_LINK | Video: $SENSOR_IDX"
echo "  [Gripper] Serial: $GRIPPER_SERIAL_LINK | Video: $GRIPPER_IDX"

# 권한 부여
sudo chmod a+rw /dev/ttyUSB* /dev/video* 2>/dev/null

# =========================================================
# 3. [Phase 1] 모터 실행 (pika_custom_tools)
# =========================================================
trap "kill 0" EXIT

log_info "1. 모터 드라이버 실행 중 (Remapping 적용됨)..."

# (1) Sensor Motor
(source /root/pika_ros/install_new/setup.bash && \
 ros2 launch pika_custom_tools pika_custom_tools.launch.py \
 serial_port:=$SENSOR_SERIAL_LINK \
 joint_name:=sensor_joint \
 node_name:=sensor_custom_node \
 topic_imu:=/sensor/imu/data \
 topic_gripper_data:=/sensor/gripper/data \
 topic_gripper_ctrl:=/sensor/gripper/ctrl \
 topic_gripper_joint_state:=/sensor/gripper/joint_state \
 topic_gripper_joint_state_ctrl:=/sensor/gripper/joint_state_ctrl \
 topic_joint_state_info:=/joint_states \
 topic_joint_state_gripper:=/joint_states_gripper \
 topic_data_capture_status:=/data_tools_dataCapture/status \
 topic_teleop_status:=/teleop_status \
 topic_localization_status:=/pika_localization_status \
 topic_arm_control_status:=/arm_control_status) &

# ---------------------------------------------------------
# (2) Gripper Motor (gripper_custom_node)
# ---------------------------------------------------------
(source /root/pika_ros/install_new/setup.bash && \
 ros2 launch pika_custom_tools pika_custom_tools.launch.py \
 serial_port:=$GRIPPER_SERIAL_LINK \
 joint_name:=gripper_joint \
 node_name:=gripper_custom_node \
 topic_imu:=/imu/data \
 topic_gripper_data:=/gripper/gripper/data \
 topic_gripper_ctrl:=/gripper/gripper/ctrl \
 topic_gripper_joint_state:=/gripper/gripper/joint_state \
 topic_gripper_joint_state_ctrl:=/sensor/gripper/joint_state \
 topic_joint_state_info:=/joint_states_single \
 topic_joint_state_gripper:=/joint_states_single_gripper) &

log_info "   -> 모터 실행 완료. 5초 대기..."
sleep 5

# =========================================================
# 4. [Phase 2] 카메라 실행 (Launch File)
# =========================================================
log_info "2. 듀얼 카메라 노드 실행..."

# 환경 설정 로드
source /opt/ros/humble/setup.bash
source /root/pika_ros/install/setup.bash
source /root/pika_ros/install_new/setup.bash

# 런치 파일 실행
# (여기서는 카메라만 켜집니다. 모터는 위에서 켰고, 런치파일에선 주석처리 했으니까요)
ros2 launch sensor_tools open_sensor_gripper.launch.py \
    sensor_depth_camera_no:=_$SENSOR_SN \
    gripper_depth_camera_no:=_$GRIPPER_SN \
    sensor_serial_port:=$SENSOR_SERIAL_LINK \
    gripper_serial_port:=$GRIPPER_SERIAL_LINK \
    sensor_fisheye_port:=$SENSOR_IDX \
    gripper_fisheye_port:=$GRIPPER_IDX \
    camera_fps:=$CAMERA_FPS \
    camera_width:=$WIDTH \
    camera_height:=$HEIGHT \
    camera_profile:="${WIDTH}x${HEIGHT}x${CAMERA_FPS}"