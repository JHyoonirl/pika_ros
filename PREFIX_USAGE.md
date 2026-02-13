# Pika ROS - PREFIX 사용 가이드

## 개요
여러 대의 Pika를 동시에 운영하기 위해 prefix 기능이 추가되었습니다. 각 pika는 고유한 prefix를 받아 모든 ROS2 토픽이 자동으로 namespace로 분리됩니다.

## 사용 방법

### 1. 단일 Pika 운영 (prefix 없이)
```bash
# prefix 없이 실행
./scripts/start_custom_single_sensor.bash

# 생성되는 토픽들:
# - /imu/data
# - /gripper/data
# - /joint_states
# - /sensor/camera/color/image_raw
# - /camera_fisheye/color/image_raw
```

### 2. 여러 대의 Pika 운영 (prefix 사용)
```bash
# 터미널 1 - Pika 1번
./scripts/start_custom_single_sensor.bash pika1

# 생성되는 토픽들:
# - /pika1/imu/data
# - /pika1/gripper/data
# - /pika1/joint_states
# - /pika1/sensor/camera/color/image_raw
# - /pika1/camera_fisheye/color/image_raw

# 터미널 2 - Pika 2번
./scripts/start_custom_single_sensor.bash pika2

# 생성되는 토픽들:
# - /pika2/imu/data
# - /pika2/gripper/data
# - /pika2/joint_states
# - /pika2/sensor/camera/color/image_raw
# - /pika2/camera_fisheye/color/image_raw
```

### 3. Gripper 운영
```bash
# prefix 없이
./scripts/start_custom_single_gripper.bash

# prefix와 함께
./scripts/start_custom_single_gripper.bash pika1
```

## 수정된 파일 목록

### Bash 스크립트
1. **scripts/start_custom_single_sensor.bash**
   - 첫 번째 인자로 prefix를 받음
   - ros2 launch 명령에 `prefix:=$PIKA_PREFIX` 추가

2. **scripts/start_custom_single_gripper.bash**
   - 첫 번째 인자로 prefix를 받음
   - ros2 launch 명령에 `prefix:=$PIKA_PREFIX` 추가

### Launch 파일
1. **src/pika_custom_tools/launch/pika_custom_tools.launch.py**
   - `prefix` 파라미터 추가 (기본값: '')
   - Node에 `namespace=prefix` 추가
   - 모든 토픽이 prefix namespace 아래에 생성됨

2. **src/sensor_tools/launch/open_single_sensor.launch.py**
   - `prefix` 파라미터 추가 (기본값: '')
   - camera_namespace를 동적으로 생성 (prefix가 있으면 "{prefix}/sensor", 없으면 "sensor")
   - camera_fisheye Node에 `namespace=prefix` 추가

3. **src/sensor_tools/launch/open_single_gripper.launch.py**
   - `prefix` 파라미터 추가 (기본값: '')
   - camera_namespace를 동적으로 생성 (prefix가 있으면 "{prefix}/gripper", 없으면 "gripper")
   - 모든 Node에 `namespace=prefix` 추가

## 토픽 네이밍 규칙

### prefix 없을 때:
```
/imu/data
/gripper/data
/joint_states
/sensor/camera/color/image_raw
/camera_fisheye/color/image_raw
```

### prefix="pika1"일 때:
```
/pika1/imu/data
/pika1/gripper/data
/pika1/joint_states
/pika1/sensor/camera/color/image_raw
/pika1/camera_fisheye/color/image_raw
```

## Indy7 연동

Indy7에서 pika 토픽을 구독할 때는 prefix를 고려해야 합니다:

```python
# prefix가 없는 경우
joint_states_topic = "/joint_states"
imu_topic = "/imu/data"

# prefix가 있는 경우
prefix = "pika1"
joint_states_topic = f"/{prefix}/joint_states"
imu_topic = f"/{prefix}/imu/data"
```

## 빌드 방법

prefix는 런타임에만 적용되므로 빌드는 기존과 동일:

```bash
source /opt/ros/humble/setup.bash
cd /root/pika_ros

# pika_custom_tools 빌드
colcon build --packages-select pika_custom_tools \
    --build-base build_new \
    --install-base install_new \
    --symlink-install

# sensor_tools 빌드
colcon build --packages-select sensor_tools data_msgs \
    --build-base build \
    --install-base install \
    --symlink-install
```

## 확인 방법

실행 후 토픽 리스트 확인:
```bash
# 모든 토픽 확인
ros2 topic list

# 특정 prefix의 토픽만 필터링
ros2 topic list | grep pika1
ros2 topic list | grep pika2

# 특정 토픽 데이터 확인
ros2 topic echo /pika1/imu/data
ros2 topic echo /pika2/joint_states
```

## 주의사항

1. **고유한 prefix**: 각 pika는 서로 다른 prefix를 사용해야 합니다
2. **디바이스 구분**: 각 pika는 서로 다른 시리얼 포트와 카메라를 사용해야 합니다
3. **prefix 형식**: prefix는 ROS2 namespace 규칙을 따라야 합니다 (슬래시 없이, 영문자/숫자/언더스코어만)
