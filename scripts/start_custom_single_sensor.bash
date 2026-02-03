#!/bin/bash

# --- 로그 및 색상 설정 ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

function log_info() { echo -e "${GREEN}[INFO] $(date '+%H:%M:%S') > $1${NC}"; }
function log_error() { echo -e "${RED}[ERROR] $(date '+%H:%M:%S') > $1${NC}"; }

log_info "스크립트 시작: Run Right Sensor (Using Setup Links)"

# =========================================================
# 1. 사용할 장치 이름 (Setup 스크립트가 만들어준 이름)
# =========================================================
TARGET_SERIAL_LINK="/dev/pika_sensor_right_serial"
TARGET_VIDEO_LINK="/dev/pika_sensor_right_video"
SENSOR_SN="315122270900"

# 카메라 설정
camera_fps=15
camera_width=848
camera_height=480

# =========================================================
# 2. 링크 확인 및 '진짜 번호' 추출
# =========================================================
log_info "장치 연결 확인 중..."

# (1) 시리얼 포트 확인
if [ ! -e "$TARGET_SERIAL_LINK" ]; then
    log_error "실패: $TARGET_SERIAL_LINK 를 찾을 수 없습니다."
    log_error "먼저 'setup_devices.bash'를 실행해서 링크를 생성해주세요."
    exit 1
fi

# (2) 비디오 포트 확인 및 인덱스 추출 (중요!)
if [ ! -e "$TARGET_VIDEO_LINK" ]; then
    log_error "실패: $TARGET_VIDEO_LINK 를 찾을 수 없습니다."
    exit 1
fi

# 심볼릭 링크가 가리키는 원본 경로 찾기 (예: /dev/video6)
REAL_VIDEO_PATH=$(readlink -f "$TARGET_VIDEO_LINK")
# 숫자만 추출 (video6 -> 6)
REAL_VIDEO_NUM=$(basename "$REAL_VIDEO_PATH" | grep -o "[0-9]*")

log_info "-> 시리얼 포트: $TARGET_SERIAL_LINK"
log_info "-> 카메라 경로: $TARGET_VIDEO_LINK (실제: video$REAL_VIDEO_NUM)"

# =========================================================
# 3. 권한 부여 (혹시 몰라 한 번 더)
# =========================================================
# 원본 장치에 권한 부여
sudo chmod a+rw "$TARGET_SERIAL_LINK" "$REAL_VIDEO_PATH" 2>/dev/null

# 파이썬 스크립트 실행 권한
TARGET_SCRIPT="/root/pika_ros/install/sensor_tools/share/sensor_tools/scripts/usb_camera.py"
[ -f "$TARGET_SCRIPT" ] && sudo chmod 777 "$TARGET_SCRIPT"

# =========================================================
# 4. ROS2 노드 실행
# =========================================================
log_info "=== ROS2 실행 시작 (Right Sensor) ==="
trap "kill 0" EXIT

# (1) 모터 드라이버 실행
log_info "1. [Motor] Driver 실행..."
(source /root/pika_ros/install_new/setup.bash && \
 ros2 launch pika_custom_tools pika_custom_tools.launch.py \
 serial_port:=$TARGET_SERIAL_LINK \
 joint_name:=sensor_joint) &

log_info "   -> 초기화 대기 (3초)..."
sleep 3

# (2) 카메라 노드 실행 (추출한 번호 사용)
log_info "2. [Camera] Node 실행 (Index: $REAL_VIDEO_NUM)..."
source /root/pika_ros/install/setup.bash && \
ros2 launch sensor_tools open_single_sensor.launch.py \
    serial_port:=$TARGET_SERIAL_LINK \
    fisheye_port:=$REAL_VIDEO_NUM \
    depth_camera_no:="'$SENSOR_SN'" \
    camera_fps:=$camera_fps \
    camera_width:=$camera_width \
    camera_height:=$camera_height \
    camera_profile:="${camera_width}x${camera_height}x${camera_fps}" \
    joint_name:=sensor_joint