# 1. ROS 2 Humble 베이스 이미지 사용
FROM ros:humble-ros-base

# apt-get을 non-interactive 모드로 설정하여 빌드 중 묻는 창이 뜨지 않도록 함
ENV DEBIAN_FRONTEND=noninteractive

# 2. 기본 툴 및 pika_ros apt 의존성 설치
RUN apt-get update && apt-get install -y \
    software-properties-common \
    libjsoncpp-dev \
    libpcap-dev \
    python3-pcl \
    build-essential \
    zlib1g-dev \
    libx11-dev \
    libusb-1.0-0-dev \
    freeglut3-dev \
    liblapacke-dev \
    libopenblas-dev \
    libatlas-base-dev \
    cmake \
    git \
    libssl-dev \
    pkg-config \
    libgtk-3-dev \
    libglfw3-dev \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    g++ \
    python3-pip \
    libopenvr-dev \
    ros-humble-diagnostic-updater \
    ros-humble-cv-bridge \
    ros-humble-pcl-conversions \
    cutecom \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 3. GCC-13 및 libcurl-dev 설치 (PPA 추가)
RUN add-apt-repository ppa:ubuntu-toolchain-r/test -y \
    && apt-get update \
    && apt-get install -y \
        gcc-13 \
        g++-13 \
        libstdc++6 \
        libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. pip 의존성 설치
RUN pip3 install opencv-python

# 5. pika_ros 프로젝트 클론 및 설정
# 작업 디렉터리를 /root로 설정
WORKDIR /root

RUN git clone https://github.com/agilexrobotics/pika_ros.git
WORKDIR /root/pika_ros
RUN git checkout ros2
RUN git submodule update --init --recursive

# 6. librealsense2 및 curl 소스 빌드 (사용자 지침 기반)
# /root 에 압축 해제
WORKDIR /root
RUN unzip /root/pika_ros/source/librealsense-2.55.1.zip -d /root
RUN unzip /root/pika_ros/source/curl-7.75.0.zip -d /root

# 7. [중요] 사용자가 제공한 이미지의 패치 작업 수행
# pika_ros 개발자가 의도한 /home/agilex/... 경로를 우리가 실제로 압축 해제한 /root/curl... 경로로 변경
RUN sed -i 's|/home/agilex/pika_ros/source/curl-7.75.0|/root/curl-7.75.0|g' /root/librealsense-2.55.1/CMake/external_libcurl.cmake

# 8. librealsense2 소스 빌드 및 설치
WORKDIR /root/librealsense-2.55.1
RUN mkdir -p build && cd build && \
    cmake .. \
    -DFORCE_RSUSB_BACKEND=true \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_EXAMPLES=false \
    -DBUILD_GRAPHICAL_EXAMPLES=false \
    && make -j$(nproc) install

# 9. pika_ros 워크스페이스 빌드
WORKDIR /root/pika_ros
RUN apt-get update && apt-get install -y ros-humble-image-transport && rm -rf /var/lib/apt/lists/*
# ROS 2 환경을 소싱(source)한 후 colcon build 실행
RUN /bin/bash -c "source /opt/ros/humble/setup.bash"

WORKDIR /root/pika_ros/source
RUN unzip /root/pika_ros/source/install.zip -d /root/pika_ros

RUN apt-get update && apt-get install -y \
    ros-humble-pcl-conversions \
    ros-humble-image-transport \
    ros-humble-rviz2 \
    ros-humble-rqt \
    ros-humble-rmw-cyclonedds-cpp \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install "numpy<2.0"
RUN pip3 install pyserial

RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc 
RUN echo "source /root/pika_ros/install/setup.bash" >> /root/.bashrc 
RUN echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> /root/.bashrc

WORKDIR /root/pika_ros
RUN . /opt/ros/$ROS_DISTRO/setup.sh && colcon build --packages-select pika_custom_tools

RUN mkdir -p /root/.config/libsurvive
# && colcon build --packages-select data_msgs && source /root/pika_ros/install/setup.bash && colcon build"

# 컨테이너 실행 시 기본 경로 설정
WORKDIR /root/pika_ros

RUN echo "export pika_R_code=LHR-FBF3A347" >> /root/.bashrc

# 컨테이너 실행 시 bash 셸 실행
CMD ["/bin/bash"]