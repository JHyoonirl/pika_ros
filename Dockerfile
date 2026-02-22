# 1. ROS 2 Humble 베이스 이미지 사용
FROM ros:humble-ros-base

RUN sed -i 's/archive.ubuntu.com/kr.archive.ubuntu.com/g' /etc/apt/sources.list

# apt-get을 non-interactive 모드로 설정
ENV DEBIAN_FRONTEND=noninteractive

# 2. 시스템 기본 의존성 설치 (Pika + libsurvive 공통 패키지 통합)
RUN apt-get update && apt-get install -y --fix-missing\
    software-properties-common libjsoncpp-dev libpcap-dev python3-pcl \
    build-essential zlib1g-dev libx11-dev libusb-1.0-0-dev freeglut3-dev \
    liblapacke-dev libopenblas-dev libatlas-base-dev cmake git libssl-dev \
    pkg-config libgtk-3-dev libglfw3-dev libgl1-mesa-dev libglu1-mesa-dev \
    g++ python3-pip libopenvr-dev ros-humble-diagnostic-updater \
    ros-humble-cv-bridge ros-humble-pcl-conversions cutecom unzip \
    libgif-dev xorg-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. GCC-13 및 libcurl-dev 설치 (PPA 추가)
RUN add-apt-repository ppa:ubuntu-toolchain-r/test -y \
    && apt-get update \
    && apt-get install -y gcc-13 g++-13 libstdc++6 libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. pika_ros 프로젝트 클론 및 설정
WORKDIR /root
RUN git clone https://github.com/agilexrobotics/pika_ros.git
WORKDIR /root/pika_ros
RUN git checkout ros2
RUN git submodule update --init --recursive

# 5. librealsense2 및 curl 소스 빌드
WORKDIR /root
RUN unzip /root/pika_ros/source/librealsense-2.55.1.zip -d /root
RUN unzip /root/pika_ros/source/curl-7.75.0.zip -d /root

# 경로 패치
RUN sed -i 's|/home/agilex/pika_ros/source/curl-7.75.0|/root/curl-7.75.0|g' /root/librealsense-2.55.1/CMake/external_libcurl.cmake

# librealsense2 빌드
WORKDIR /root/librealsense-2.55.1
RUN mkdir -p build && cd build && \
    cmake .. -DFORCE_RSUSB_BACKEND=true -DCMAKE_BUILD_TYPE=Release -DBUILD_EXAMPLES=false -DBUILD_GRAPHICAL_EXAMPLES=false \
    && make -j$(nproc) install

# 6. ROS 2 추가 패키지 설치 및 pika_ros 기본 세팅
WORKDIR /root/pika_ros
RUN apt-get update && apt-get install -y \
    ros-humble-image-transport \
    ros-humble-pcl-conversions \
    ros-humble-rviz2 \
    ros-humble-rqt \
    ros-humble-rmw-cyclonedds-cpp \
    ros-humble-image-transport-plugins \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root/pika_ros/source
RUN unzip /root/pika_ros/source/install.zip -d /root/pika_ros

# 7. Python 의존성 설치 (Vive Tracker용 pynput 추가)
RUN pip3 install opencv-python "numpy<2.0" pyserial scipy pynput

# ==========================================
# 8. libsurvive 빌드 및 파이썬 바인딩(pysurvive) 설치
# ==========================================
WORKDIR /root
RUN git clone https://github.com/cntools/libsurvive.git
WORKDIR /root/libsurvive
RUN make -j$(nproc)
RUN make install

WORKDIR /root/libsurvive
# 1. 빌드 도구 설치
RUN pip3 install wheel setuptools

# 2. wxPython 공식 리눅스 저장소에서 우분투 22.04용 빌드본을 강제로 낚아채서 즉시 설치합니다.
RUN pip3 install wxPython -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-22.04
RUN pip3 install .
RUN ldconfig

# 9. 환경 변수 세팅 및 패키지 빌드
RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc 
RUN echo "source /root/pika_ros/install/setup.bash" >> /root/.bashrc 
RUN echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> /root/.bashrc
# RUN echo "source /root/pika_ros/pika_env.sh" >> /root/.bashrc
RUN echo "export pika_R_code=LHR-FBF3A347" >> /root/.bashrc

WORKDIR /root/pika_ros
# ROS 2 소싱 후 pika_custom_tools 빌드
RUN /bin/bash -c "source /opt/ros/humble/setup.bash && colcon build --packages-select pika_custom_tools"

RUN mkdir -p /root/.config/libsurvive

# 컨테이너 실행 시 bash 셸 실행
CMD ["/bin/bash"]