#!/bin/bash

# RealSense 카메라 시리얼 번호 찾기 스크립트

# 색상 설정
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

function log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
function log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
function log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "================================================"
echo "  RealSense Camera Serial Number Finder"
echo "================================================"
echo ""

# 방법 1: rs-enumerate-devices 명령어 사용
if command -v rs-enumerate-devices &> /dev/null; then
    log_info "방법 1: rs-enumerate-devices 명령어 사용"
    echo ""
    rs-enumerate-devices | grep -E "Serial Number|Device Name"
    echo ""
else
    log_warn "rs-enumerate-devices 명령어를 찾을 수 없습니다."
    log_info "Intel RealSense SDK가 설치되어 있지 않을 수 있습니다."
    echo ""
fi

# # 방법 2: Python을 사용한 방법
# log_info "방법 2: Python pyrealsense2 사용"
# echo ""

# python3 << 'EOF'
# try:
#     import pyrealsense2 as rs
    
#     # RealSense 컨텍스트 생성
#     ctx = rs.context()
#     devices = ctx.query_devices()
    
#     if len(devices) == 0:
#         print("연결된 RealSense 카메라가 없습니다.")
#     else:
#         print(f"발견된 카메라 수: {len(devices)}")
#         print("")
        
#         for i, device in enumerate(devices):
#             print(f"카메라 #{i+1}:")
#             print(f"  - 이름: {device.get_info(rs.camera_info.name)}")
#             print(f"  - 시리얼 번호: {device.get_info(rs.camera_info.serial_number)}")
#             print(f"  - 펌웨어 버전: {device.get_info(rs.camera_info.firmware_version)}")
#             print(f"  - USB 타입: {device.get_info(rs.camera_info.usb_type_descriptor)}")
#             print("")
            
# except ImportError:
#     print("pyrealsense2 모듈을 찾을 수 없습니다.")
#     print("설치: pip install pyrealsense2")
# except Exception as e:
#     print(f"오류 발생: {e}")
# EOF

# echo ""
# echo "================================================"

# # 방법 3: udev 규칙을 통한 확인 (디바이스 정보)
# log_info "방법 3: USB 디바이스 정보 확인"
# echo ""
# log_info "Intel RealSense 카메라 (Vendor ID: 8086):"
# lsusb | grep "8086" || echo "  Intel 디바이스를 찾을 수 없습니다."

# echo ""
# echo "================================================"
# echo "TIP: 시리얼 번호는 launch 파일에서 다음과 같이 사용됩니다:"
# echo "  depth_camera_no:=\"'315122270900'\""
# echo "================================================"
