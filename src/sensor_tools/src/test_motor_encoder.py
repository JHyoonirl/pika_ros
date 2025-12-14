import serial
import time
import json
import struct
import threading
import sys

# ==========================================
# 설정 (환경에 맞게 수정하세요)
# ==========================================
SERIAL_PORT = '/dev/ttyUSB0'  # 실제 연결된 포트로 변경 (예: /dev/ttyUSB0, /dev/ttyUSB60)
BAUDRATE = 460800             # C++ 코드와 동일하게 설정

# ==========================================
# JSON 파싱 헬퍼 함수 (C++ find_json 로직 포팅)
# ==========================================
def find_and_parse_json(buffer):
    """
    버퍼에서 유효한 JSON 문자열을 찾아내어 파싱합니다.
    중괄호 {} 짝을 맞추는 로직이 포함되어 있습니다.
    """
    stack = []
    start_index = -1
    
    for i, char in enumerate(buffer):
        if char == '{':
            if len(stack) == 0:
                start_index = i
            stack.append(i)
        elif char == '}':
            if len(stack) > 0:
                stack.pop()
                # 스택이 비었고, 이전에 시작점이 있었다면 JSON 하나 완성
                if len(stack) == 0 and start_index != -1:
                    json_str = buffer[start_index:i+1]
                    remaining_buffer = buffer[i+1:]
                    try:
                        parsed_data = json.loads(json_str)
                        return parsed_data, remaining_buffer
                    except json.JSONDecodeError:
                        # 깨진 JSON이면 무시하고 다음으로 넘어감
                        return None, remaining_buffer
    
    return None, buffer

# ==========================================
# 메인 테스트 로직
# ==========================================
def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=0.1)
        print(f"✅ 포트 열기 성공: {SERIAL_PORT} @ {BAUDRATE}")
    except Exception as e:
        print(f"❌ 포트 열기 실패: {e}")
        print("팁: sudo chmod 666 /dev/ttyUSB* 명령어로 권한을 확인하세요.")
        return

    print("📡 데이터 수신 대기 중... (Ctrl+C로 종료)")
    print("-" * 60)
    
    buffer = ""
    last_print_time = time.time()
    packet_count = 0

    try:
        while True:
            # 1. 데이터 읽기
            if ser.in_waiting > 0:
                # C++ 코드처럼 덩어리로 읽어서 버퍼에 추가
                try:
                    raw_data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    buffer += raw_data
                except Exception as e:
                    print(f"데이터 읽기 오류: {e}")
                    continue

                # 2. JSON 파싱 시도
                while True:
                    json_data, buffer = find_and_parse_json(buffer)
                    
                    if json_data:
                        packet_count += 1
                        
                        # ==============================================
                        # [중요] 모터 데이터 확인 로직
                        # ==============================================
                        found_motor = False
                        
                        # Case A: 외부 엔코더 (AS5047) 데이터 확인
                        if "AS5047" in json_data:
                            enc_data = json_data["AS5047"]
                            rad = enc_data.get("rad", "N/A")
                            print(f"[AS5047] 각도(rad): {rad}")
                            found_motor = True

                        # Case B: 내부 모터 컨트롤러 데이터 확인
                        if "motor" in json_data:
                            motor_data = json_data["motor"]
                            pos = motor_data.get("Position", "N/A")
                            current = motor_data.get("Current", "N/A")
                            speed = motor_data.get("Speed", "N/A")
                            print(f"[Motor]  위치: {pos:.4f} | 전류: {current:.4f} | 속도: {speed:.4f}")
                            found_motor = True
                            
                        # Case C: 모터 상태 확인
                        if "motorstatus" in json_data:
                            status = json_data["motorstatus"]
                            voltage = status.get("Voltage", 0)
                            err_status = status.get("Status", "Unknown")
                            # print(f"[Status] 전압: {voltage}V | 상태코드: {err_status}")

                        # 데이터는 오는데 모터 키값만 없는 경우 디버깅
                        if not found_motor and (time.time() - last_print_time > 1.0):
                            print(f"[Debug] 다른 데이터 수신 중... Keys: {list(json_data.keys())}")
                            last_print_time = time.time()
                    else:
                        # 더 이상 파싱할 JSON이 없으면 루프 탈출하고 다시 read 대기
                        break
            
            # 버퍼가 너무 커지면 비우기 (메모리 보호)
            if len(buffer) > 4096:
                buffer = ""
                
            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n종료합니다.")
    finally:
        ser.close()

if __name__ == "__main__":
    main()