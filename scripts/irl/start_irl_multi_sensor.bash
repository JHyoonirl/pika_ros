#!/bin/bash

# --- 로그 및 색상 설정 ---
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

function log_info() { echo -e "${GREEN}[INFO] $(date '+%H:%M:%S') > $1${NC}"; }
function log_warn() { echo -e "${YELLOW}[WARN] $(date '+%H:%M:%S') > $1${NC}"; }
function log_error() { echo -e "${RED}[ERROR] $(date '+%H:%M:%S') > $1${NC}"; }

# =========================================================
# PREFIX 설정 (LEFT, RIGHT 각각 별도로 받기)
# 사용법: ./start_custom_multi_sensor.bash [left_prefix] [right_prefix]
# 예: ./start_custom_multi_sensor.bash pika_L pika_R
# =========================================================
PIKA_PREFIX_L="${1:-}"
PIKA_PREFIX_R="${2:-}"

log_info "스크립트 시작: Run Multi Sensor (LEFT + RIGHT)"
if [ -n "$PIKA_PREFIX_L" ]; then
    log_info "  -> LEFT PREFIX: '$PIKA_PREFIX_L'"
else
    log_info "  -> LEFT PREFIX: (없음)"
fi
if [ -n "$PIKA_PREFIX_R" ]; then
    log_info "  -> RIGHT PREFIX: '$PIKA_PREFIX_R'"
else
    log_info "  -> RIGHT PREFIX: (없음)"
fi

# =========================================================
# 1. 장치 이름 설정 (Setup 스크립트가 만들어준 이름)
# realsense 카메라 시리얼 번호를 환경 변수로부터 가져오기
# =========================================================

# --- LEFT Sensor ---
L_SERIAL_LINK="/dev/pika_sensor_left_serial"
L_VIDEO_LINK="/dev/pika_sensor_left_video"
L_DEPTH_SN="$L_SENSOR_DEPTH_SN_R"  # LEFT 깊이 카메라 시리얼 번호 (환경에 맞게 수정)

# --- RIGHT Sensor ---
R_SERIAL_LINK="/dev/pika_sensor_right_serial"
R_VIDEO_LINK="/dev/pika_sensor_right_video"
R_DEPTH_SN="$R_SENSOR_DEPTH_SN_R"  # RIGHT 깊이 카메라 시리얼 번호 (환경에 맞게 수정)

# 카메라 공통 설정
camera_fps=30
camera_width=640
camera_height=480

# =========================================================
# 2. 장치 확인 함수
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
# 3. 장치 연결 확인
# =========================================================
log_info "장치 연결 확인 중..."

# LEFT 장치 확인
L_AVAILABLE=true
if ! check_device "$L_SERIAL_LINK" "LEFT Serial"; then L_AVAILABLE=false; fi
if ! check_device "$L_VIDEO_LINK" "LEFT Video"; then L_AVAILABLE=false; fi

# RIGHT 장치 확인
R_AVAILABLE=true
if ! check_device "$R_SERIAL_LINK" "RIGHT Serial"; then R_AVAILABLE=false; fi
if ! check_device "$R_VIDEO_LINK" "RIGHT Video"; then R_AVAILABLE=false; fi

# 최소 하나는 있어야 함
if [ "$L_AVAILABLE" = false ] && [ "$R_AVAILABLE" = false ]; then
    log_error "LEFT와 RIGHT 모두 장치를 찾을 수 없습니다."
    log_error "먼저 'setup_devices.bash'를 실행해서 링크를 생성해주세요."
    exit 1
fi

# 비디오 번호 추출
if [ "$L_AVAILABLE" = true ]; then
    L_VIDEO_NUM=$(get_video_num "$L_VIDEO_LINK")
    L_REAL_VIDEO_PATH=$(readlink -f "$L_VIDEO_LINK")
    log_info "-> [LEFT] 시리얼: $L_SERIAL_LINK, 카메라: video$L_VIDEO_NUM"
fi

if [ "$R_AVAILABLE" = true ]; then
    R_VIDEO_NUM=$(get_video_num "$R_VIDEO_LINK")
    R_REAL_VIDEO_PATH=$(readlink -f "$R_VIDEO_LINK")
    log_info "-> [RIGHT] 시리얼: $R_SERIAL_LINK, 카메라: video$R_VIDEO_NUM"
fi

# =========================================================
# 4. 권한 부여
# =========================================================
log_info "장치 권한 설정 중..."

if [ "$L_AVAILABLE" = true ]; then
    sudo chmod a+rw "$L_SERIAL_LINK" "$L_REAL_VIDEO_PATH" 2>/dev/null
fi

if [ "$R_AVAILABLE" = true ]; then
    sudo chmod a+rw "$R_SERIAL_LINK" "$R_REAL_VIDEO_PATH" 2>/dev/null
fi

# 파이썬 스크립트 실행 권한
TARGET_SCRIPT="/root/pika_ros/install/sensor_tools/share/sensor_tools/scripts/usb_camera.py"
[ -f "$TARGET_SCRIPT" ] && sudo chmod 777 "$TARGET_SCRIPT"

# =========================================================
# 5. ROS2 노드 실행
# =========================================================
log_info "=== ROS2 실행 시작 (Multi Sensor) ==="
trap "kill 0" EXIT

# ---------------------------------------------------------
# (1) LEFT Motor Driver 실행
# ---------------------------------------------------------
if [ "$L_AVAILABLE" = true ]; then
    log_info "1-L. [LEFT Motor] Driver 실행..."
    
    if [ -n "$PIKA_PREFIX_L" ]; then
        (source /root/pika_ros/install_new/setup.bash && \
         ros2 launch pika_custom_tools pika_custom_tools.launch.py \
         serial_port:=$L_SERIAL_LINK \
         joint_name:=gripper_l_center_joint \
         node_name:=pika_custom_tools_l \
         prefix:=$PIKA_PREFIX_L \
         topic_imu:=imu_l/data \
         topic_gripper_data:=gripper_l/data \
         topic_gripper_ctrl:=gripper_l/ctrl \
         topic_gripper_joint_state:=gripper_l/joint_state \
         topic_gripper_joint_state_ctrl:=joint_states_l \
         topic_joint_state_info:=joint_states_l \
         topic_joint_state_gripper:=joint_states_gripper_l \
         topic_teleop_status:=teleop_status_l \
         topic_localization_status:=/pika_localization_status_l \
         topic_arm_control_status:=arm_control_status_l) &
    else
        (source /root/pika_ros/install_new/setup.bash && \
         ros2 launch pika_custom_tools pika_custom_tools.launch.py \
         serial_port:=$L_SERIAL_LINK \
         joint_name:=gripper_l_center_joint \
         node_name:=pika_custom_tools_l \
         topic_imu:=imu_l/data \
         topic_gripper_data:=gripper_l/data \
         topic_gripper_ctrl:=gripper_l/ctrl \
         topic_gripper_joint_state:=gripper_l/joint_state \
         topic_gripper_joint_state_ctrl:=joint_states_l \
         topic_joint_state_info:=joint_states_l \
         topic_joint_state_gripper:=joint_states_gripper_l \
         topic_teleop_status:=teleop_status_l \
         topic_localization_status:=/pika_localization_status_l \
         topic_arm_control_status:=arm_control_status_l) &
    fi
fi

# ---------------------------------------------------------
# (2) RIGHT Motor Driver 실행
# ---------------------------------------------------------
if [ "$R_AVAILABLE" = true ]; then
    log_info "1-R. [RIGHT Motor] Driver 실행..."
    
    if [ -n "$PIKA_PREFIX_R" ]; then
        (source /root/pika_ros/install_new/setup.bash && \
         ros2 launch pika_custom_tools pika_custom_tools.launch.py \
         serial_port:=$R_SERIAL_LINK \
         joint_name:=gripper_r_center_joint \
         node_name:=pika_custom_tools_r \
         prefix:=$PIKA_PREFIX_R \
         topic_imu:=imu_r/data \
         topic_gripper_data:=gripper_r/data \
         topic_gripper_ctrl:=gripper_r/ctrl \
         topic_gripper_joint_state:=gripper_r/joint_state \
         topic_gripper_joint_state_ctrl:=joint_states_r \
         topic_joint_state_info:=joint_states_r \
         topic_joint_state_gripper:=joint_states_gripper_r \
         topic_teleop_status:=teleop_status_r \
         topic_localization_status:=/pika_localization_status_r \
         topic_arm_control_status:=arm_control_status_r) &
    else
        (source /root/pika_ros/install_new/setup.bash && \
         ros2 launch pika_custom_tools pika_custom_tools.launch.py \
         serial_port:=$R_SERIAL_LINK \
         joint_name:=gripper_r_center_joint \
         node_name:=pika_custom_tools_r \
         topic_imu:=imu_r/data \
         topic_gripper_data:=gripper_r/data \
         topic_gripper_ctrl:=gripper_r/ctrl \
         topic_gripper_joint_state:=gripper_r/joint_state \
         topic_gripper_joint_state_ctrl:=joint_states_r \
         topic_joint_state_info:=joint_states_r \
         topic_joint_state_gripper:=joint_states_gripper_r \
         topic_teleop_status:=teleop_status_r \
         topic_localization_status:=/pika_localization_status_r \
         topic_arm_control_status:=arm_control_status_r) &
    fi
fi

log_info "   -> 모터 드라이버 초기화 대기 (3초)..."
sleep 3

# ---------------------------------------------------------
# (3) 카메라 및 Locator 실행 (open_multi_sensor.launch.py)
# ---------------------------------------------------------
log_info "2. [Camera + Locator] Multi Sensor 실행..."

# launch 인자 구성
LAUNCH_ARGS=""
LAUNCH_ARGS+=" camera_fps:=$camera_fps"
LAUNCH_ARGS+=" camera_width:=$camera_width"
LAUNCH_ARGS+=" camera_height:=$camera_height"
LAUNCH_ARGS+=" camera_profile:=${camera_width}x${camera_height}x${camera_fps}"

if [ "$L_AVAILABLE" = true ]; then
    LAUNCH_ARGS+=" l_serial_port:=$L_SERIAL_LINK"
    LAUNCH_ARGS+=" l_fisheye_port:=$L_VIDEO_NUM"
    LAUNCH_ARGS+=" l_depth_camera_no:=_$L_DEPTH_SN"
    LAUNCH_ARGS+=" l_joint_name:=gripper_l_center_joint"
    
    # LEFT PREFIX
    if [ -n "$PIKA_PREFIX_L" ]; then
        LAUNCH_ARGS+=" l_name:=/$PIKA_PREFIX_L"
        LAUNCH_ARGS+=" l_name_index:=${PIKA_PREFIX_L}_"
    else
        LAUNCH_ARGS+=" l_name:="
        LAUNCH_ARGS+=" l_name_index:="
    fi
fi

if [ "$R_AVAILABLE" = true ]; then
    LAUNCH_ARGS+=" r_serial_port:=$R_SERIAL_LINK"
    LAUNCH_ARGS+=" r_fisheye_port:=$R_VIDEO_NUM"
    LAUNCH_ARGS+=" r_depth_camera_no:=_$R_DEPTH_SN"
    LAUNCH_ARGS+=" r_joint_name:=gripper_r_center_joint"
    
    # RIGHT PREFIX
    if [ -n "$PIKA_PREFIX_R" ]; then
        LAUNCH_ARGS+=" r_name:=/$PIKA_PREFIX_R"
        LAUNCH_ARGS+=" r_name_index:=${PIKA_PREFIX_R}_"
    else
        LAUNCH_ARGS+=" r_name:="
        LAUNCH_ARGS+=" r_name_index:="
    fi
fi

log_info "Launch 인자: $LAUNCH_ARGS"

source /root/pika_ros/install/setup.bash && \
ros2 launch sensor_tools open_multi_sensor.launch.py $LAUNCH_ARGS