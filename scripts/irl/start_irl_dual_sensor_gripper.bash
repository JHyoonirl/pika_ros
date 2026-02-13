#!/bin/bash

# =============================================================================
# Pika Dual Arm System (Left + Right, Each with Sensor + Gripper)
# =============================================================================
#
# 사용법: ./start_irl_dual_sensor_gripper.bash <ARM1_SIDE> <ARM2_SIDE>
# 예시:   ./start_irl_dual_sensor_gripper.bash left right
#
# 구조 (4개 pika 디바이스):
#   ARM1(left):  left_sensor  + left_gripper   (teleop: left_gripper ← left_sensor)
#   ARM2(right): right_sensor + right_gripper   (teleop: right_gripper ← right_sensor)
#
# 토픽 네임스페이스:
#   /left_sensor/gripper/joint_state, /left_sensor/imu/data, ...
#   /left_gripper/gripper/joint_state, /left_gripper/imu/data, ...
#   /right_sensor/gripper/joint_state, /right_sensor/imu/data, ...
#   /right_gripper/gripper/joint_state, /right_gripper/imu/data, ...
#
# 필요 환경변수 (setup_realsense.bash 에서 source):
#   L_SENSOR_DEPTH_SN_R, L_GRIPPER_DEPTH_SN_R
#   R_SENSOR_DEPTH_SN_R, R_GRIPPER_DEPTH_SN_R
# =============================================================================

# --- 로그 및 색상 설정 ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

function log_info() { echo -e "${GREEN}[INFO] $(date '+%H:%M:%S') > $1${NC}"; }
function log_warn() { echo -e "${YELLOW}[WARN] $(date '+%H:%M:%S') > $1${NC}"; }
function log_error() { echo -e "${RED}[ERROR] $(date '+%H:%M:%S') > $1${NC}"; }

# =========================================================
# 0. 인자 검증
# =========================================================
if [ $# -ne 2 ]; then
    echo "사용법: $0 <ARM1_SIDE> <ARM2_SIDE>"
    echo "예시:   $0 left right"
    echo ""
    echo "  ARM_SIDE: left 또는 right (물리적 장치 위치)"
    exit 1
fi

ARM1=$1  # e.g., "left"
ARM2=$2  # e.g., "right"

# 유효성 검사
for arm in "$ARM1" "$ARM2"; do
    if [[ "$arm" != "left" && "$arm" != "right" ]]; then
        log_error "잘못된 인자: '$arm' (left 또는 right만 가능)"
        exit 1
    fi
done

if [ "$ARM1" == "$ARM2" ]; then
    log_error "두 인자가 동일합니다: '$ARM1'. 서로 다른 쪽을 지정하세요."
    exit 1
fi

log_info "========================================"
log_info "Pika Dual Arm System 시작"
log_info "  ARM1: $ARM1 (${ARM1}_sensor + ${ARM1}_gripper)"
log_info "  ARM2: $ARM2 (${ARM2}_sensor + ${ARM2}_gripper)"
log_info "========================================"

# =========================================================
# 1. 장치 매핑 함수
# =========================================================
function get_device_vars() {
    local side=$1
    case $side in
        left)
            echo "/dev/pika_sensor_left_serial"
            echo "/dev/pika_sensor_left_video"
            echo "/dev/pika_gripper_left_serial"
            echo "/dev/pika_gripper_left_video"
            echo "$L_SENSOR_DEPTH_SN_R"
            echo "$L_GRIPPER_DEPTH_SN_R"
            ;;
        right)
            echo "/dev/pika_sensor_right_serial"
            echo "/dev/pika_sensor_right_video"
            echo "/dev/pika_gripper_right_serial"
            echo "/dev/pika_gripper_right_video"
            echo "$R_SENSOR_DEPTH_SN_R"
            echo "$R_GRIPPER_DEPTH_SN_R"
            ;;
    esac
}

# =========================================================
# 2. 장치 확인 함수 (multi_sensor 방식)
# =========================================================
function check_device() {
    local link_path=$1
    local device_name=$2
    if [ ! -e "$link_path" ]; then
        log_warn "$device_name 장치를 찾을 수 없습니다: $link_path"
        return 1
    fi
    return 0
}

function get_video_num() {
    local video_link=$1
    local real_path=$(readlink -f "$video_link")
    echo $(basename "$real_path" | grep -o "[0-9]*")
}

# =========================================================
# 3. 장치 설정 로드
# =========================================================

# --- ARM1 장치 ---
readarray -t ARM1_DEVS < <(get_device_vars "$ARM1")
ARM1_SENSOR_SERIAL="${ARM1_DEVS[0]}"
ARM1_SENSOR_VIDEO="${ARM1_DEVS[1]}"
ARM1_GRIPPER_SERIAL="${ARM1_DEVS[2]}"
ARM1_GRIPPER_VIDEO="${ARM1_DEVS[3]}"
ARM1_SENSOR_SN="${ARM1_DEVS[4]}"
ARM1_GRIPPER_SN="${ARM1_DEVS[5]}"

# --- ARM2 장치 ---
readarray -t ARM2_DEVS < <(get_device_vars "$ARM2")
ARM2_SENSOR_SERIAL="${ARM2_DEVS[0]}"
ARM2_SENSOR_VIDEO="${ARM2_DEVS[1]}"
ARM2_GRIPPER_SERIAL="${ARM2_DEVS[2]}"
ARM2_GRIPPER_VIDEO="${ARM2_DEVS[3]}"
ARM2_SENSOR_SN="${ARM2_DEVS[4]}"
ARM2_GRIPPER_SN="${ARM2_DEVS[5]}"

# =========================================================
# 4. 장치 연결 확인 (multi_sensor 방식: 각 arm 별로 체크)
# =========================================================
log_info "장치 연결 확인 중..."

ARM1_AVAILABLE=true
if ! check_device "$ARM1_SENSOR_SERIAL" "${ARM1} Sensor Serial"; then ARM1_AVAILABLE=false; fi
if ! check_device "$ARM1_SENSOR_VIDEO" "${ARM1} Sensor Video"; then ARM1_AVAILABLE=false; fi
if ! check_device "$ARM1_GRIPPER_SERIAL" "${ARM1} Gripper Serial"; then ARM1_AVAILABLE=false; fi
if ! check_device "$ARM1_GRIPPER_VIDEO" "${ARM1} Gripper Video"; then ARM1_AVAILABLE=false; fi

ARM2_AVAILABLE=true
if ! check_device "$ARM2_SENSOR_SERIAL" "${ARM2} Sensor Serial"; then ARM2_AVAILABLE=false; fi
if ! check_device "$ARM2_SENSOR_VIDEO" "${ARM2} Sensor Video"; then ARM2_AVAILABLE=false; fi
if ! check_device "$ARM2_GRIPPER_SERIAL" "${ARM2} Gripper Serial"; then ARM2_AVAILABLE=false; fi
if ! check_device "$ARM2_GRIPPER_VIDEO" "${ARM2} Gripper Video"; then ARM2_AVAILABLE=false; fi

# 최소 하나는 있어야 함
if [ "$ARM1_AVAILABLE" = false ] && [ "$ARM2_AVAILABLE" = false ]; then
    log_error "ARM1(${ARM1})과 ARM2(${ARM2}) 모두 장치를 찾을 수 없습니다."
    log_error "먼저 'setup_devices.bash'를 실행해서 링크를 생성해주세요."
    exit 1
fi

# =========================================================
# 5. 환경변수 검증 (가용한 ARM만)
# =========================================================
MISSING=0
if [ "$ARM1_AVAILABLE" = true ]; then
    if [ -z "$ARM1_SENSOR_SN" ]; then
        log_error "RealSense 시리얼 번호 누락: ${ARM1} Sensor Depth SN"
        MISSING=1
    fi
    if [ -z "$ARM1_GRIPPER_SN" ]; then
        log_error "RealSense 시리얼 번호 누락: ${ARM1} Gripper Depth SN"
        MISSING=1
    fi
fi
if [ "$ARM2_AVAILABLE" = true ]; then
    if [ -z "$ARM2_SENSOR_SN" ]; then
        log_error "RealSense 시리얼 번호 누락: ${ARM2} Sensor Depth SN"
        MISSING=1
    fi
    if [ -z "$ARM2_GRIPPER_SN" ]; then
        log_error "RealSense 시리얼 번호 누락: ${ARM2} Gripper Depth SN"
        MISSING=1
    fi
fi

if [ $MISSING -eq 1 ]; then
    log_error "setup_realsense.bash를 먼저 source 하세요:"
    log_info "  source /root/pika_ros/scripts/setup_realsense.bash"
    exit 1
fi

log_info "RealSense 시리얼 번호 확인:"
if [ "$ARM1_AVAILABLE" = true ]; then
    echo "  [${ARM1}] Sensor: $ARM1_SENSOR_SN | Gripper: $ARM1_GRIPPER_SN"
fi
if [ "$ARM2_AVAILABLE" = true ]; then
    echo "  [${ARM2}] Sensor: $ARM2_SENSOR_SN | Gripper: $ARM2_GRIPPER_SN"
fi

# =========================================================
# 6. 카메라 설정
# =========================================================
CAMERA_FPS=30
WIDTH=640
HEIGHT=480
CAMERA_PROFILE="${WIDTH}x${HEIGHT}x${CAMERA_FPS}"

# =========================================================
# 7. 비디오 인덱스 추출 및 권한 부여
# =========================================================
if [ "$ARM1_AVAILABLE" = true ]; then
    ARM1_SENSOR_FISHEYE_IDX=$(get_video_num "$ARM1_SENSOR_VIDEO")
    ARM1_GRIPPER_FISHEYE_IDX=$(get_video_num "$ARM1_GRIPPER_VIDEO")
    ARM1_SENSOR_VIDEO_REAL=$(readlink -f "$ARM1_SENSOR_VIDEO")
    ARM1_GRIPPER_VIDEO_REAL=$(readlink -f "$ARM1_GRIPPER_VIDEO")
    log_info "-> [${ARM1}_sensor]  Serial: $ARM1_SENSOR_SERIAL  | Fisheye: $ARM1_SENSOR_FISHEYE_IDX  | Depth SN: $ARM1_SENSOR_SN"
    log_info "-> [${ARM1}_gripper] Serial: $ARM1_GRIPPER_SERIAL | Fisheye: $ARM1_GRIPPER_FISHEYE_IDX | Depth SN: $ARM1_GRIPPER_SN"
fi

if [ "$ARM2_AVAILABLE" = true ]; then
    ARM2_SENSOR_FISHEYE_IDX=$(get_video_num "$ARM2_SENSOR_VIDEO")
    ARM2_GRIPPER_FISHEYE_IDX=$(get_video_num "$ARM2_GRIPPER_VIDEO")
    ARM2_SENSOR_VIDEO_REAL=$(readlink -f "$ARM2_SENSOR_VIDEO")
    ARM2_GRIPPER_VIDEO_REAL=$(readlink -f "$ARM2_GRIPPER_VIDEO")
    log_info "-> [${ARM2}_sensor]  Serial: $ARM2_SENSOR_SERIAL  | Fisheye: $ARM2_SENSOR_FISHEYE_IDX  | Depth SN: $ARM2_SENSOR_SN"
    log_info "-> [${ARM2}_gripper] Serial: $ARM2_GRIPPER_SERIAL | Fisheye: $ARM2_GRIPPER_FISHEYE_IDX | Depth SN: $ARM2_GRIPPER_SN"
fi

# 권한 부여
sudo chmod a+rw /dev/ttyUSB* /dev/video* 2>/dev/null

# 파이썬 스크립트 실행 권한
TARGET_SCRIPT="/root/pika_ros/install/sensor_tools/share/sensor_tools/scripts/usb_camera.py"
[ -f "$TARGET_SCRIPT" ] && sudo chmod 777 "$TARGET_SCRIPT"

# =========================================================
# 8. 환경 설정 로드
# =========================================================
source /opt/ros/humble/setup.bash
source /root/pika_ros/install/setup.bash
source /root/pika_ros/install_new/setup.bash

trap "kill 0" EXIT

# =========================================================
# 9. [Phase 3] Locator 실행 (마지막)
# =========================================================
log_info "========== Phase 9: Locator 시작 (마지막) =========="

log_info "  [locator] pika_double_locator 시작..."
log_info "   -> Locator 초기화는 시간이 걸립니다 (약 30초). 백그라운드에서 진행됩니다."
ros2 launch pika_locator pika_double_locator.launch.py &
sleep 2




# =========================================================
# 10. [Phase 2] 모터 실행 (pika_custom_tools)
# =========================================================
log_info "========== Phase 10: 모터 드라이버 실행 =========="

# --- ARM1 (Sensor + Gripper) ---
if [ "$ARM1_AVAILABLE" = true ]; then
    log_info "  [${ARM1}_sensor] 모터 시작..."
    (source /root/pika_ros/install_new/setup.bash && \
     ros2 launch pika_custom_tools pika_custom_tools.launch.py \
     prefix:=${ARM1}_sensor \
     serial_port:=$ARM1_SENSOR_SERIAL \
     joint_name:=${ARM1}_sensor_joint \
     node_name:=${ARM1}_sensor_node \
     topic_joint_state_info:=/joint_states \
     topic_joint_state_gripper:=/joint_states_gripper \
     topic_data_capture_status:=/data_tools_dataCapture/status \
     topic_teleop_status:=/teleop_status \
     topic_localization_status:=/pika_localization_status \
     topic_arm_control_status:=/arm_control_status) &

    log_info "  [${ARM1}_gripper] 모터 시작 (teleop ← /${ARM1}_sensor/gripper/joint_state)..."
    (source /root/pika_ros/install_new/setup.bash && \
     ros2 launch pika_custom_tools pika_custom_tools.launch.py \
     prefix:=${ARM1}_gripper \
     serial_port:=$ARM1_GRIPPER_SERIAL \
     joint_name:=${ARM1}_gripper_joint \
     node_name:=${ARM1}_gripper_node \
     topic_gripper_joint_state_ctrl:=/${ARM1}_sensor/gripper/joint_state \
     topic_joint_state_info:=/joint_states \
     topic_joint_state_gripper:=/joint_states_gripper \
     topic_data_capture_status:=/data_tools_dataCapture/status \
     topic_teleop_status:=/teleop_status \
     topic_localization_status:=/pika_localization_status \
     topic_arm_control_status:=/arm_control_status) &
fi

# --- ARM2 (Sensor + Gripper) ---
if [ "$ARM2_AVAILABLE" = true ]; then
    log_info "  [${ARM2}_sensor] 모터 시작..."
    (source /root/pika_ros/install_new/setup.bash && \
     ros2 launch pika_custom_tools pika_custom_tools.launch.py \
     prefix:=${ARM2}_sensor \
     serial_port:=$ARM2_SENSOR_SERIAL \
     joint_name:=${ARM2}_sensor_joint \
     node_name:=${ARM2}_sensor_node \
     topic_joint_state_info:=/joint_states \
     topic_joint_state_gripper:=/joint_states_gripper \
     topic_data_capture_status:=/data_tools_dataCapture/status \
     topic_teleop_status:=/teleop_status \
     topic_localization_status:=/pika_localization_status \
     topic_arm_control_status:=/arm_control_status) &

    log_info "  [${ARM2}_gripper] 모터 시작 (teleop ← /${ARM2}_sensor/gripper/joint_state)..."
    (source /root/pika_ros/install_new/setup.bash && \
     ros2 launch pika_custom_tools pika_custom_tools.launch.py \
     prefix:=${ARM2}_gripper \
     serial_port:=$ARM2_GRIPPER_SERIAL \
     joint_name:=${ARM2}_gripper_joint \
     node_name:=${ARM2}_gripper_node \
     topic_gripper_joint_state_ctrl:=/${ARM2}_sensor/gripper/joint_state \
     topic_joint_state_info:=/joint_states \
     topic_joint_state_gripper:=/joint_states_gripper \
     topic_data_capture_status:=/data_tools_dataCapture/status \
     topic_teleop_status:=/teleop_status \
     topic_localization_status:=/pika_localization_status \
     topic_arm_control_status:=/arm_control_status) &
fi

log_info "   -> 모터 드라이버 초기화 대기 (10초)..."
sleep 10

# =========================================================
# 10. [Phase 2] 카메라 실행
# =========================================================
log_info "========== Phase 2: 카메라 노드 실행 =========="

# ---------------------------------------------------------
# RealSense Depth 카메라 (순차 실행으로 충돌 방지)
# ---------------------------------------------------------
log_info "RealSense 카메라를 순차적으로 시작합니다 (충돌 방지)..."

if [ "$ARM1_AVAILABLE" = true ]; then
    log_info "  [${ARM1}_sensor] Depth 카메라 (SN: $ARM1_SENSOR_SN)..."
    ros2 launch realsense2_camera rs_launch.py \
        serial_no:="'$ARM1_SENSOR_SN'" \
        camera_namespace:=${ARM1}_sensor \
        camera_name:=camera \
        rgb_camera.color_profile:=$CAMERA_PROFILE \
        depth_module.color_profile:=$CAMERA_PROFILE \
        depth_module.depth_profile:=$CAMERA_PROFILE \
        depth_module.infra_profile:=$CAMERA_PROFILE &
    sleep 5

    log_info "  [${ARM1}_gripper] Depth 카메라 (SN: $ARM1_GRIPPER_SN)..."
    ros2 launch realsense2_camera rs_launch.py \
        serial_no:="'$ARM1_GRIPPER_SN'" \
        camera_namespace:=${ARM1}_gripper \
        camera_name:=camera \
        rgb_camera.color_profile:=$CAMERA_PROFILE \
        depth_module.color_profile:=$CAMERA_PROFILE \
        depth_module.depth_profile:=$CAMERA_PROFILE \
        depth_module.infra_profile:=$CAMERA_PROFILE &
    sleep 5
fi

if [ "$ARM2_AVAILABLE" = true ]; then
    log_info "  [${ARM2}_sensor] Depth 카메라 (SN: $ARM2_SENSOR_SN)..."
    ros2 launch realsense2_camera rs_launch.py \
        serial_no:="'$ARM2_SENSOR_SN'" \
        camera_namespace:=${ARM2}_sensor \
        camera_name:=camera \
        rgb_camera.color_profile:=$CAMERA_PROFILE \
        depth_module.color_profile:=$CAMERA_PROFILE \
        depth_module.depth_profile:=$CAMERA_PROFILE \
        depth_module.infra_profile:=$CAMERA_PROFILE &
    sleep 5

    log_info "  [${ARM2}_gripper] Depth 카메라 (SN: $ARM2_GRIPPER_SN)..."
    ros2 launch realsense2_camera rs_launch.py \
        serial_no:="'$ARM2_GRIPPER_SN'" \
        camera_namespace:=${ARM2}_gripper \
        camera_name:=camera \
        rgb_camera.color_profile:=$CAMERA_PROFILE \
        depth_module.color_profile:=$CAMERA_PROFILE \
        depth_module.depth_profile:=$CAMERA_PROFILE \
        depth_module.infra_profile:=$CAMERA_PROFILE &
    sleep 5
fi

sleep 2

# ---------------------------------------------------------
# Fisheye USB 카메라
# ---------------------------------------------------------
if [ "$ARM1_AVAILABLE" = true ]; then
    log_info "  [${ARM1}_sensor] Fisheye 카메라 (port: $ARM1_SENSOR_FISHEYE_IDX)..."
    ros2 run sensor_tools usb_camera.py --ros-args \
        -p camera_port:=$ARM1_SENSOR_FISHEYE_IDX \
        -p camera_fps:=$CAMERA_FPS \
        -p camera_height:=$HEIGHT \
        -p camera_width:=$WIDTH \
        -p camera_frame_id:=${ARM1}_sensor/camera_fisheye_link \
        -r __node:=${ARM1}_sensor_camera_fisheye \
        -r /camera_rgb/color/image_raw:=/${ARM1}_sensor/camera_fisheye/color/image_raw \
        -r /camera_rgb/color/camera_info:=/${ARM1}_sensor/camera_fisheye/color/camera_info &
    sleep 2
    log_info "  [${ARM1}_gripper] Fisheye 카메라 (port: $ARM1_GRIPPER_FISHEYE_IDX)..."
    ros2 run sensor_tools usb_camera.py --ros-args \
        -p camera_port:=$ARM1_GRIPPER_FISHEYE_IDX \
        -p camera_fps:=$CAMERA_FPS \
        -p camera_height:=$HEIGHT \
        -p camera_width:=$WIDTH \
        -p camera_frame_id:=${ARM1}_gripper/camera_fisheye_link \
        -r __node:=${ARM1}_gripper_camera_fisheye \
        -r /camera_rgb/color/image_raw:=/${ARM1}_gripper/camera_fisheye/color/image_raw \
        -r /camera_rgb/color/camera_info:=/${ARM1}_gripper/camera_fisheye/color/camera_info &
    sleep 2
fi

if [ "$ARM2_AVAILABLE" = true ]; then
    log_info "  [${ARM2}_sensor] Fisheye 카메라 (port: $ARM2_SENSOR_FISHEYE_IDX)..."
    ros2 run sensor_tools usb_camera.py --ros-args \
        -p camera_port:=$ARM2_SENSOR_FISHEYE_IDX \
        -p camera_fps:=$CAMERA_FPS \
        -p camera_height:=$HEIGHT \
        -p camera_width:=$WIDTH \
        -p camera_frame_id:=${ARM2}_sensor/camera_fisheye_link \
        -r __node:=${ARM2}_sensor_camera_fisheye \
        -r /camera_rgb/color/image_raw:=/${ARM2}_sensor/camera_fisheye/color/image_raw \
        -r /camera_rgb/color/camera_info:=/${ARM2}_sensor/camera_fisheye/color/camera_info &
    sleep 2
    log_info "  [${ARM2}_gripper] Fisheye 카메라 (port: $ARM2_GRIPPER_FISHEYE_IDX)..."
    ros2 run sensor_tools usb_camera.py --ros-args \
        -p camera_port:=$ARM2_GRIPPER_FISHEYE_IDX \
        -p camera_fps:=$CAMERA_FPS \
        -p camera_height:=$HEIGHT \
        -p camera_width:=$WIDTH \
        -p camera_frame_id:=${ARM2}_gripper/camera_fisheye_link \
        -r __node:=${ARM2}_gripper_camera_fisheye \
        -r /camera_rgb/color/image_raw:=/${ARM2}_gripper/camera_fisheye/color/image_raw \
        -r /camera_rgb/color/camera_info:=/${ARM2}_gripper/camera_fisheye/color/camera_info &
    sleep 2
fi


# =========================================================
# 12. 완료
# =========================================================
MOTOR_COUNT=0
CAMERA_COUNT=0
if [ "$ARM1_AVAILABLE" = true ]; then MOTOR_COUNT=$((MOTOR_COUNT+2)); CAMERA_COUNT=$((CAMERA_COUNT+4)); fi
if [ "$ARM2_AVAILABLE" = true ]; then MOTOR_COUNT=$((MOTOR_COUNT+2)); CAMERA_COUNT=$((CAMERA_COUNT+4)); fi

log_info "========================================"
log_info "모든 노드 실행 완료!"
log_info "  모터:    ${MOTOR_COUNT}개"
log_info "  카메라:  ${CAMERA_COUNT}개 (Depth + Fisheye)"
log_info "  Locator: pika_double_locator"
if [ "$ARM1_AVAILABLE" = true ]; then
    log_info "  Teleop: ${ARM1}_gripper ← ${ARM1}_sensor"
fi
if [ "$ARM2_AVAILABLE" = true ]; then
    log_info "  Teleop: ${ARM2}_gripper ← ${ARM2}_sensor"
fi
log_info "========================================"
log_info "종료하려면 Ctrl+C 를 누르세요."

wait