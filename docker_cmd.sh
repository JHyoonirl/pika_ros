#!/bin/bash

# X11 권한 허용 (GUI 실행을 위해 필요)
xhost +local:docker

docker run -it --rm --gpus all\
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
    pika_ros:humble