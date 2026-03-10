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

# realsense serial numbers 를 환경변수로 설정

# Right Sensor
SENSOR_SERIAL_LINK="/dev/pika_sensor_right_serial"
SENSOR_VIDEO_LINK="/dev/pika_sensor_right_video"
SENSOR_SN=$R_SENSOR_DEPTH_SN_R

# Right Gripper
GRIPPER_SERIAL_LINK="/dev/pika_gripper_right_serial"
GRIPPER_VIDEO_LINK="/dev/pika_gripper_right_video"
GRIPPER_SN=$R_GRIPPER_DEPTH_SN_R

# Trolley
TROLLEY_SN=$TROLLEY_DEPTH_SN

# 환경변수 검증
if [ -z "$SENSOR_SN" ]; then
    log_error "환경변수 R_SENSOR_DEPTH_SN_R이 설정되지 않았습니다."
    log_info "예: export R_SENSOR_DEPTH_SN_R=230322270688"
    exit 1
fi

if [ -z "$GRIPPER_SN" ]; then
    log_error "환경변수 R_GRIPPER_DEPTH_SN_R이 설정되지 않았습니다."
    log_info "예: export R_GRIPPER_DEPTH_SN_R=230322272619"
    exit 1
fi

if [ -z "$TROLLEY_SN" ]; then
    log_error "환경변수 R_TROLLEY_DEPTH_SN_R이 설정되지 않았습니다."
    log_info "예: export R_TROLLEY_DEPTH_SN_R=230322272619"
    exit 1
fi

log_info "RealSense 시리얼 번호:"
echo "  Sensor:  $SENSOR_SN"
echo "  Gripper: $GRIPPER_SN"
echo "  Trolley: $TROLLEY_SN"

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

log_info "1. 모터 드라이버 실행 중 (Namespace 사용)..."

# (1) Sensor Motor - namespace: sensor
(source /root/pika_ros/install_new/setup.bash && \
 ros2 launch pika_custom_tools pika_custom_tools.launch.py \
 prefix:=sensor \
 serial_port:=$SENSOR_SERIAL_LINK \
 joint_name:=sensor_joint \
 node_name:=sensor_custom_node \
 topic_joint_state_info:=/joint_states \
 topic_joint_state_gripper:=/joint_states_gripper \
 topic_data_capture_status:=/data_tools_dataCapture/status \
 topic_teleop_status:=/teleop_status \
 topic_localization_status:=/pika_localization_status \
 topic_arm_control_status:=/arm_control_status) &

# ---------------------------------------------------------
# (2) Gripper Motor - namespace: gripper
#     [중요] Teleoperation: Sensor의 gripper/joint_state를 구독하여 제어
# ---------------------------------------------------------
(source /root/pika_ros/install_new/setup.bash && \
 ros2 launch pika_custom_tools pika_custom_tools.launch.py \
 prefix:=gripper \
 serial_port:=$GRIPPER_SERIAL_LINK \
 joint_name:=gripper_joint \
 node_name:=gripper_custom_node \
 topic_gripper_joint_state_ctrl:=/sensor/gripper/joint_state \
 topic_joint_state_info:=/joint_states \
 topic_joint_state_gripper:=/joint_states_gripper \
 topic_data_capture_status:=/data_tools_dataCapture/status \
 topic_teleop_status:=/teleop_status \
 topic_localization_status:=/pika_localization_status \
 topic_arm_control_status:=/arm_control_status) &

log_info "   -> 모터 실행 완료. 5초 대기..."
sleep 5

# =========================================================
# 3. [Phase 2] 로케이터 실행 (pika_single_locator)
# =========================================================
log_info "2. 로케이터 실행 중 (pika_single_locator)..."
ros2 launch pika_locator pika_single_locator.launch.py &
sleep 3

# =========================================================
# 4. [Phase 3] 리얼센스 카메라 실행 (순차적 딜레이)
# =========================================================
log_info "3. 리얼센스 카메라 실행 중 (타입 충돌 방지 적용)..."

# (1) Sensor RealSense
ros2 launch realsense2_camera rs_launch.py \
    camera_namespace:=sensor camera_name:=camera \
    serial_no:="'$SENSOR_SN'" \
    rgb_camera.color_profile:="${WIDTH}x${HEIGHT}x${CAMERA_FPS}" \
    depth_module.depth_profile:="${WIDTH}x${HEIGHT}x${CAMERA_FPS}" &
sleep 3

# (2) Gripper RealSense
ros2 launch realsense2_camera rs_launch.py \
    camera_namespace:=gripper camera_name:=camera \
    serial_no:="'$GRIPPER_SN'" \
    rgb_camera.color_profile:="${WIDTH}x${HEIGHT}x${CAMERA_FPS}" \
    depth_module.depth_profile:="${WIDTH}x${HEIGHT}x${CAMERA_FPS}" &
sleep 3

# (3) Trolley RealSense
ros2 launch realsense2_camera rs_launch.py \
    camera_namespace:=trolley camera_name:=camera \
    serial_no:="'$TROLLEY_SN'" \
    rgb_camera.color_profile:="${WIDTH}x${HEIGHT}x${CAMERA_FPS}" \
    depth_module.depth_profile:="${WIDTH}x${HEIGHT}x${CAMERA_FPS}" &
sleep 3

# =========================================================
# 5. [Phase 4] 어안 카메라(Fisheye) 실행
# =========================================================
log_info "4. 듀얼 어안 카메라 실행 중..."

# Sensor Fisheye (640x480 해상도 및 30fps 강제 지정)
ros2 run sensor_tools usb_camera.py --ros-args \
    -p camera_port:=$SENSOR_IDX -p camera_frame_id:="sensor/camera_fisheye_link" \
    -p camera_width:=640 -p camera_height:=480 -p camera_fps:=30 \
    -r /camera_rgb/color/image_raw:=/sensor/camera_fisheye/color/image_raw &

# Gripper Fisheye (640x480 해상도 및 30fps 강제 지정)
ros2 run sensor_tools usb_camera.py --ros-args \
    -p camera_port:=$GRIPPER_IDX -p camera_frame_id:="gripper/camera_fisheye_link" \
    -p camera_width:=640 -p camera_height:=480 -p camera_fps:=30 \
    -r /camera_rgb/color/image_raw:=/gripper/camera_fisheye/color/image_raw &

log_info "✅ 모든 시스템이 가동되었습니다. Ctrl+C를 누르면 전체 종료됩니다."
wait