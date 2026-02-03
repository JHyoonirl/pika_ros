// generated from rosidl_typesupport_fastrtps_c/resource/idl__type_support_c.cpp.em
// with input from data_msgs:msg/TeleopStatus.idl
// generated code does not contain a copyright notice
#include "data_msgs/msg/detail/teleop_status__rosidl_typesupport_fastrtps_c.h"


#include <cassert>
#include <limits>
#include <string>
#include "rosidl_typesupport_fastrtps_c/identifier.h"
#include "rosidl_typesupport_fastrtps_c/wstring_conversion.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "data_msgs/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
#include "data_msgs/msg/detail/teleop_status__struct.h"
#include "data_msgs/msg/detail/teleop_status__functions.h"
#include "fastcdr/Cdr.h"

#ifndef _WIN32
# pragma GCC diagnostic push
# pragma GCC diagnostic ignored "-Wunused-parameter"
# ifdef __clang__
#  pragma clang diagnostic ignored "-Wdeprecated-register"
#  pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
# endif
#endif
#ifndef _WIN32
# pragma GCC diagnostic pop
#endif

// includes and forward declarations of message dependencies and their conversion functions

#if defined(__cplusplus)
extern "C"
{
#endif

#include "rosidl_runtime_c/string.h"  // topics
#include "rosidl_runtime_c/string_functions.h"  // topics

// forward declare type support functions


using _TeleopStatus__ros_msg_type = data_msgs__msg__TeleopStatus;

static bool _TeleopStatus__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  const _TeleopStatus__ros_msg_type * ros_message = static_cast<const _TeleopStatus__ros_msg_type *>(untyped_ros_message);
  // Field name: topics
  {
    size_t size = ros_message->topics.size;
    auto array_ptr = ros_message->topics.data;
    cdr << static_cast<uint32_t>(size);
    for (size_t i = 0; i < size; ++i) {
      const rosidl_runtime_c__String * str = &array_ptr[i];
      if (str->capacity == 0 || str->capacity <= str->size) {
        fprintf(stderr, "string capacity not greater than size\n");
        return false;
      }
      if (str->data[str->size] != '\0') {
        fprintf(stderr, "string not null-terminated\n");
        return false;
      }
      cdr << str->data;
    }
  }

  // Field name: fail
  {
    cdr << (ros_message->fail ? true : false);
  }

  // Field name: quit
  {
    cdr << (ros_message->quit ? true : false);
  }

  return true;
}

static bool _TeleopStatus__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  _TeleopStatus__ros_msg_type * ros_message = static_cast<_TeleopStatus__ros_msg_type *>(untyped_ros_message);
  // Field name: topics
  {
    uint32_t cdrSize;
    cdr >> cdrSize;
    size_t size = static_cast<size_t>(cdrSize);

    // Check there are at least 'size' remaining bytes in the CDR stream before resizing
    auto old_state = cdr.getState();
    bool correct_size = cdr.jump(size);
    cdr.setState(old_state);
    if (!correct_size) {
      fprintf(stderr, "sequence size exceeds remaining buffer\n");
      return false;
    }

    if (ros_message->topics.data) {
      rosidl_runtime_c__String__Sequence__fini(&ros_message->topics);
    }
    if (!rosidl_runtime_c__String__Sequence__init(&ros_message->topics, size)) {
      fprintf(stderr, "failed to create array for field 'topics'");
      return false;
    }
    auto array_ptr = ros_message->topics.data;
    for (size_t i = 0; i < size; ++i) {
      std::string tmp;
      cdr >> tmp;
      auto & ros_i = array_ptr[i];
      if (!ros_i.data) {
        rosidl_runtime_c__String__init(&ros_i);
      }
      bool succeeded = rosidl_runtime_c__String__assign(
        &ros_i,
        tmp.c_str());
      if (!succeeded) {
        fprintf(stderr, "failed to assign string into field 'topics'\n");
        return false;
      }
    }
  }

  // Field name: fail
  {
    uint8_t tmp;
    cdr >> tmp;
    ros_message->fail = tmp ? true : false;
  }

  // Field name: quit
  {
    uint8_t tmp;
    cdr >> tmp;
    ros_message->quit = tmp ? true : false;
  }

  return true;
}  // NOLINT(readability/fn_size)

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_data_msgs
size_t get_serialized_size_data_msgs__msg__TeleopStatus(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _TeleopStatus__ros_msg_type * ros_message = static_cast<const _TeleopStatus__ros_msg_type *>(untyped_ros_message);
  (void)ros_message;
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // field.name topics
  {
    size_t array_size = ros_message->topics.size;
    auto array_ptr = ros_message->topics.data;
    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);
    for (size_t index = 0; index < array_size; ++index) {
      current_alignment += padding +
        eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
        (array_ptr[index].size + 1);
    }
  }
  // field.name fail
  {
    size_t item_size = sizeof(ros_message->fail);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name quit
  {
    size_t item_size = sizeof(ros_message->quit);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

static uint32_t _TeleopStatus__get_serialized_size(const void * untyped_ros_message)
{
  return static_cast<uint32_t>(
    get_serialized_size_data_msgs__msg__TeleopStatus(
      untyped_ros_message, 0));
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_data_msgs
size_t max_serialized_size_data_msgs__msg__TeleopStatus(
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

  // member: topics
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
  // member: fail
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint8_t);
    current_alignment += array_size * sizeof(uint8_t);
  }
  // member: quit
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
    using DataType = data_msgs__msg__TeleopStatus;
    is_plain =
      (
      offsetof(DataType, quit) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static size_t _TeleopStatus__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_data_msgs__msg__TeleopStatus(
    full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}


static message_type_support_callbacks_t __callbacks_TeleopStatus = {
  "data_msgs::msg",
  "TeleopStatus",
  _TeleopStatus__cdr_serialize,
  _TeleopStatus__cdr_deserialize,
  _TeleopStatus__get_serialized_size,
  _TeleopStatus__max_serialized_size
};

static rosidl_message_type_support_t _TeleopStatus__type_support = {
  rosidl_typesupport_fastrtps_c__identifier,
  &__callbacks_TeleopStatus,
  get_message_typesupport_handle_function,
};

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, data_msgs, msg, TeleopStatus)() {
  return &_TeleopStatus__type_support;
}

#if defined(__cplusplus)
}
#endif
