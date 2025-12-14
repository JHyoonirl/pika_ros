// generated from rosidl_typesupport_fastrtps_cpp/resource/idl__type_support.cpp.em
// with input from data_msgs:msg/CaptureStatus.idl
// generated code does not contain a copyright notice
#include "data_msgs/msg/detail/capture_status__rosidl_typesupport_fastrtps_cpp.hpp"
#include "data_msgs/msg/detail/capture_status__struct.hpp"

#include <limits>
#include <stdexcept>
#include <string>
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_fastrtps_cpp/identifier.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_fastrtps_cpp/wstring_conversion.hpp"
#include "fastcdr/Cdr.h"


// forward declaration of message dependencies and their conversion functions

namespace data_msgs
{

namespace msg
{

namespace typesupport_fastrtps_cpp
{

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_data_msgs
cdr_serialize(
  const data_msgs::msg::CaptureStatus & ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  // Member: topics
  {
    cdr << ros_message.topics;
  }
  // Member: count_in_seconds
  {
    cdr << ros_message.count_in_seconds;
  }
  // Member: frequencies
  {
    cdr << ros_message.frequencies;
  }
  // Member: fail
  cdr << (ros_message.fail ? true : false);
  // Member: quit
  cdr << (ros_message.quit ? true : false);
  return true;
}

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_data_msgs
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  data_msgs::msg::CaptureStatus & ros_message)
{
  // Member: topics
  {
    cdr >> ros_message.topics;
  }

  // Member: count_in_seconds
  {
    cdr >> ros_message.count_in_seconds;
  }

  // Member: frequencies
  {
    cdr >> ros_message.frequencies;
  }

  // Member: fail
  {
    uint8_t tmp;
    cdr >> tmp;
    ros_message.fail = tmp ? true : false;
  }

  // Member: quit
  {
    uint8_t tmp;
    cdr >> tmp;
    ros_message.quit = tmp ? true : false;
  }

  return true;
}  // NOLINT(readability/fn_size)

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_data_msgs
get_serialized_size(
  const data_msgs::msg::CaptureStatus & ros_message,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // Member: topics
  {
    size_t array_size = ros_message.topics.size();

    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);
    for (size_t index = 0; index < array_size; ++index) {
      current_alignment += padding +
        eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
        (ros_message.topics[index].size() + 1);
    }
  }
  // Member: count_in_seconds
  {
    size_t array_size = ros_message.count_in_seconds.size();

    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);
    size_t item_size = sizeof(ros_message.count_in_seconds[0]);
    current_alignment += array_size * item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: frequencies
  {
    size_t array_size = ros_message.frequencies.size();

    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);
    size_t item_size = sizeof(ros_message.frequencies[0]);
    current_alignment += array_size * item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: fail
  {
    size_t item_size = sizeof(ros_message.fail);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: quit
  {
    size_t item_size = sizeof(ros_message.quit);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_data_msgs
max_serialized_size_CaptureStatus(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  size_t last_member_size = 0;
  (void)last_member_size;
  (void)padding;
  (void)wchar_size;

  full_bounded = true;
  is_plain = true;


  // Member: topics
  {
    size_t array_size = 0;
    full_bounded = false;
    is_plain = false;
    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);

    full_bounded = false;
    is_plain = false;
    for (size_t index = 0; index < array_size; ++index) {
      current_alignment += padding +
        eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
        1;
    }
  }

  // Member: count_in_seconds
  {
    size_t array_size = 0;
    full_bounded = false;
    is_plain = false;
    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }

  // Member: frequencies
  {
    size_t array_size = 0;
    full_bounded = false;
    is_plain = false;
    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }

  // Member: fail
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint8_t);
    current_alignment += array_size * sizeof(uint8_t);
  }

  // Member: quit
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint8_t);
    current_alignment += array_size * sizeof(uint8_t);
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = data_msgs::msg::CaptureStatus;
    is_plain =
      (
      offsetof(DataType, quit) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static bool _CaptureStatus__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  auto typed_message =
    static_cast<const data_msgs::msg::CaptureStatus *>(
    untyped_ros_message);
  return cdr_serialize(*typed_message, cdr);
}

static bool _CaptureStatus__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  auto typed_message =
    static_cast<data_msgs::msg::CaptureStatus *>(
    untyped_ros_message);
  return cdr_deserialize(cdr, *typed_message);
}

static uint32_t _CaptureStatus__get_serialized_size(
  const void * untyped_ros_message)
{
  auto typed_message =
    static_cast<const data_msgs::msg::CaptureStatus *>(
    untyped_ros_message);
  return static_cast<uint32_t>(get_serialized_size(*typed_message, 0));
}

static size_t _CaptureStatus__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_CaptureStatus(full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}

static message_type_support_callbacks_t _CaptureStatus__callbacks = {
  "data_msgs::msg",
  "CaptureStatus",
  _CaptureStatus__cdr_serialize,
  _CaptureStatus__cdr_deserialize,
  _CaptureStatus__get_serialized_size,
  _CaptureStatus__max_serialized_size
};

static rosidl_message_type_support_t _CaptureStatus__handle = {
  rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
  &_CaptureStatus__callbacks,
  get_message_typesupport_handle_function,
};

}  // namespace typesupport_fastrtps_cpp

}  // namespace msg

}  // namespace data_msgs

namespace rosidl_typesupport_fastrtps_cpp
{

template<>
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_EXPORT_data_msgs
const rosidl_message_type_support_t *
get_message_type_support_handle<data_msgs::msg::CaptureStatus>()
{
  return &data_msgs::msg::typesupport_fastrtps_cpp::_CaptureStatus__handle;
}

}  // namespace rosidl_typesupport_fastrtps_cpp

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, data_msgs, msg, CaptureStatus)() {
  return &data_msgs::msg::typesupport_fastrtps_cpp::_CaptureStatus__handle;
}

#ifdef __cplusplus
}
#endif
