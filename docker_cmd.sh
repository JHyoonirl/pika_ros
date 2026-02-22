#!/bin/bash

# 1. 호스트 GUI 권한 허용
xhost +local:docker > /dev/null

# 2. 혹시 남아있을 수 있는 동일 이름의 컨테이너 강제 삭제
sudo docker rm -f pika_ros_container 2>/dev/null

# 3. 컨테이너 실행 (--rm 옵션 유지)
# 메인 창이 닫히면 컨테이너가 삭제되지만, 실행 중에는 다른 터미널에서 이름으로 접근 가능합니다.
sudo docker run -it \
    --name pika_ros_container \
    --rm \
    --gpus all \
    --net=host \
    --ipc=host \
    --privileged \
    -v /dev:/dev \
    -e DISPLAY=$DISPLAY \
    -e ROS_DOMAIN_ID=$ROS_DOMAIN_ID \
    -e pika_L_code=LHR-63AAAF5B \
    -e pika_R_code=LHR-FBF3A347 \
    -e ROS_LOCALHOST_ONLY=0 \
    -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v ~/pika_ros:/root/pika_ros \
    pika_ros:humble \
    bash -c "source /opt/ros/humble/setup.bash && \
             cd /root/pika_ros && \
             echo 'Pika ROS2 Container is ready. Main terminal session started.' && \
             exec bash"