#!/bin/bash

# --- 디버깅용 함수 정의 (색상 출력) ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function log_info() {
    echo -e "${GREEN}[INFO] $(date '+%H:%M:%S') > $1${NC}"
}

function log_warn() {
    echo -e "${YELLOW}[WARN] $(date '+%H:%M:%S') > $1${NC}"
}

function log_error() {
    echo -e "${RED}[ERROR] $(date '+%H:%M:%S') > $1${NC}"
}


# 1. 스크립트 시작 및 경로 확인
log_info "스크립트 시작: $0"
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
log_info "현재 스크립트 경로: $SCRIPT_DIR"

# 2. 파라미터 설정 및 확인
camera_fps=30
camera_width=640
camera_height=480

log_info "설정된 카메라 파라미터 확인:"
echo "  - FPS: $camera_fps"
echo "  - Width: $camera_width"
echo "  - Height: $camera_height"


# 3. Udev 규칙 생성 (sudo 권한 필요)
log_info "Udev 규칙 파일 생성 중... (sudo 권한 필요)"

# sensor_serial.rules 생성
log_info "Creating /etc/udev/rules.d/sensor_serial.rules..."
if sudo sh -c 'echo "KERNEL==\"ttyUSB*\", ATTRS{idVendor}==\"1a86\", ATTRS{idProduct}==\"7522\", MODE:=\"0777\", SYMLINK+=\"ttyUSB0\"" > /etc/udev/rules.d/sensor_serial.rules'; then
    log_info "sensor_serial.rules 생성 성공"
else
    log_error "sensor_serial.rules 생성 실패"
    # exit 1  # 필요 시 주석 해제하여 스크립트 중단
fi


# sensor_fisheye.rules 생성
log_info "Creating /etc/udev/rules.d/sensor_fisheye.rules..."
if sudo sh -c 'echo "KERNEL==\"video*\", ATTRS{idVendor}==\"1bcf\", ATTRS{idProduct}==\"2cd1\", MODE:=\"0777\", SYMLINK+=\"video7\"" > /etc/udev/rules.d/sensor_fisheye.rules'; then
    log_info "sensor_fisheye.rules 생성 성공"
else
    log_error "sensor_fisheye.rules 생성 실패"
fi

# 4. Udev 리로드 및 트리거
log_info "Udev 규칙 리로드 및 적용 중..."
sudo udevadm control --reload-rules && sudo service udev restart && sudo udevadm trigger
log_info "Udev 리로드 완료"

# 5. 장치 권한 변경 (확인 및 적용)
log_info "장치 권한 변경 중 (/dev/ttyUSB*, /dev/video*)..."
sudo chmod a+rw /dev/ttyUSB* 2>/dev/null
sudo chmod a+rw /dev/video* 2>/dev/null
log_info "장치 권한 변경 완료"

# 6. 파이썬 스크립트 실행 권한 부여
# (경로가 길어서 변수로 처리, 실패 시 경고 출력)
TARGET_SCRIPT="/root/pika_ros/install/sensor_tools/share/sensor_tools/scripts/usb_camera.py"

if [ -f "$TARGET_SCRIPT" ]; then
    sudo chmod 777 "$TARGET_SCRIPT"
    log_info "usb_camera.py 실행 권한(777) 부여 완료"
else
    log_warn "파일을 찾을 수 없음: $TARGET_SCRIPT (경로 확인 필요)"
fi

# ---------------------------------------------------------
# 7. ROS2 런치 동시 실행 (핵심 부분)
# ---------------------------------------------------------
log_info "=== ROS2 노드 동시 실행을 시작합니다 ==="

# [종료 시그널 처리] 
# 스크립트가 종료될 때(Ctrl+C), 백그라운드에서 실행된 프로세스도 같이 죽이도록 설정
trap "kill 0" EXIT

# (1) 제어/모터 노드 실행 -> 백그라운드(&)
# 설명: 이 노드는 터미널을 잡고 있으면 안 되므로 뒤로 보냅니다.
log_info "1. Pika Custom Tools (Motor/Control) 실행 중... (Background)"
(source /root/pika_ros/install_new/setup.bash && ros2 launch pika_custom_tools pika_custom_tools.launch.py serial_port:=/dev/ttyUSB0 joint_name:=center_joint) &
PID_TOOLS=$!
log_info "   -> Custom Tools PID: $PID_TOOLS"

# 안정적인 실행을 위해 3초 대기 (모터 드라이버 초기화 시간 확보)
log_info "   -> 초기화 대기 중 (3초)..."
sleep 3

# (2) 카메라/센서 노드 실행 -> 포그라운드
# 설명: 이 노드가 실행되는 동안 스크립트는 종료되지 않고 계속 떠 있게 됩니다.
log_info "2. Open Single Sensor (Camera/Sensor) 실행 중... (Foreground)"
source /root/pika_ros/install/setup.bash && ros2 launch sensor_tools open_single_sensor.launch.py \
    serial_port:=/dev/ttyUSB0 \
    fisheye_port:=6 \
    camera_fps:=$camera_fps \
    camera_width:=$camera_width \
    camera_height:=$camera_height \
    camera_profile:=$camera_width,$camera_height,$camera_fps \
    joint_name:=center_joint