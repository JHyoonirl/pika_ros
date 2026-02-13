#!/bin/bash

# Pika Camera Serial Numbers
export L_SENSOR_DEPTH_SN_R="315122271136"
export R_SENSOR_DEPTH_SN_R="315122270900"
export L_GRIPPER_DEPTH_SN_R="315122270809"
export R_GRIPPER_DEPTH_SN_R="315122270807"

pika_bridge() {
    cat <<EOF > /tmp/pika_zenoh.json5
{
  "mode": "peer",
  "listen": { "endpoints": ["tcp/[::]:7448"] },
  "plugins": {
    "ros2dds": {
      "namespace": "/pika_bridge",
      "domain": 10,
      "allow": "/(pika|tf|joint_states|camera)/.*",
      // [추가] 브릿지가 직접 ROS discovery 정보를 관리하지 않도록 설정하여 패닉 방지
      "ros_automatic_discovery_range": "LOCALHOST" 
    }
  }
}
EOF
    zenoh-bridge-ros2dds -c /tmp/pika_zenoh.json5
}