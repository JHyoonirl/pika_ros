// generated from rosidl_typesupport_fastrtps_c/resource/idl__type_support_c.cpp.em
// with input from data_msgs:msg/CaptureStatus.idl
// generated code does not contain a copyright notice
#include "data_msgs/msg/detail/capture_status__rosidl_typesupport_fastrtps_c.h"


#include <cassert>
#include <limits>
#include <string>
#include "rosidl_typesupport_fastrtps_c/identifier.h"
#include "rosidl_typesupport_fastrtps_c/wstring_conversion.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "data_msgs/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
#include "data_msgs/msg/detail/capture_status__struct.h"
#include "data_msgs/msg/detail/capture_status__functions.h"
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

#include "rosidl_runtime_c/primitives_sequence.h"  // count_in_seconds, frequencies
#include "rosidl_runtime_c/primitives_sequence_functions.h"  // count_in_seconds, frequencies
#include "rosidl_runtime_c/string.h"  // topics
#include "rosidl_runtime_c/string_functions.h"  // topics

// forward declare type support functions


using _CaptureStatus__ros_msg_type = data_msgs__msg__CaptureStatus;

static bool _CaptureStatus__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  const _CaptureStatus__ros_msg_type * ros_message = static_cast<const _CaptureStatus__ros_msg_type *>(untyped_ros_message);
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

  // Field name: count_in_seconds
  {
    size_t size = ros_message->count_in_seconds.size;
    auto array_ptr = ros_message->count_in_seconds.data;
    cdr << static_cast<uint32_t>(size);
    cdr.serializeArray(array_ptr, size);
  }

  // Field name: frequencies
  {
    size_t size = ros_message->frequencies.size;
    auto array_ptr = ros_message->frequencies.data;
    cdr << static_cast<uint32_t>(size);
    cdr.serializeArray(array_ptr, size);
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

static bool _CaptureStatus__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  _CaptureStatus__ros_msg_type * ros_message = static_cast<_CaptureStatus__ros_msg_type *>(untyped_ros_message);
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

  // Field name: count_in_seconds
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

    if (ros_message->count_in_seconds.data) {
      rosidl_runtime_c__int32__Sequence__fini(&ros_message->count_in_seconds);
    }
    if (!rosidl_runtime_c__int32__Sequence__init(&ros_message->count_in_seconds, size)) {
      fprintf(stderr, "failed to create array for field 'count_in_seconds'");
      return false;
    }
    auto array_ptr = ros_message->count_in_seconds.data;
    cdr.deserializeArray(array_ptr, size);
  }

  // Field name: frequencies
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

    if (ros_message->frequencies.data) {
      rosidl_runtime_c__float__Sequence__fini(&ros_message->frequencies);
    }
    if (!rosidl_runtime_c__float__Sequence__init(&ros_message->frequencies, size)) {
      fprintf(stderr, "failed to create array for field 'frequencies'");
      return false;
    }
    auto array_ptr = ros_message->frequencies.data;
    cdr.deserializeArray(array_ptr, size);
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
size_t get_serialized_size_data_msgs__msg__CaptureStatus(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _CaptureStatus__ros_msg_type * ros_message = static_cast<const _CaptureStatus__ros_msg_type *>(untyped_ros_message);
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
  // field.name count_in_seconds
  {
    size_t array_size = ros_message->count_in_seconds.size;
    auto array_ptr = ros_message->count_in_seconds.data;
    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);
    (void)array_ptr;
    size_t item_size = sizeof(array_ptr[0]);
    current_alignment += array_size * item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name frequencies
  {
    size_t array_size = ros_message->frequencies.size;
    auto array_ptr = ros_message->frequencies.data;
    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);
    (void)array_ptr;
    size_t item_size = sizeof(array_ptr[0]);
    current_alignment += array_size * item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
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

static uint32_t _CaptureStatus__get_serialized_size(const void * untyped_ros_message)
{
  return static_cast<uint32_t>(
    get_serialized_size_data_msgs__msg__CaptureStatus(
      untyped_ros_message, 0));
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_data_msgs
size_t max_serialized_size_data_msgs__msg__CaptureStatus(
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
  // member: count_in_seconds
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
  // member: frequencies
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
    using DataType = data_msgs__msg__CaptureStatus;
    is_plain =
      (
      offsetof(DataType, quit) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static size_t _CaptureStatus__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_data_msgs__msg__CaptureStatus(
    full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}


static message_type_support_callbacks_t __callbacks_CaptureStatus = {
  "data_msgs::msg",
  "CaptureStatus",
  _CaptureStatus__cdr_serialize,
  _CaptureStatus__cdr_deserialize,
  _CaptureStatus__get_serialized_size,
  _CaptureStatus__max_serialized_size
};

static rosidl_message_type_support_t _CaptureStatus__type_support = {
  rosidl_typesupport_fastrtps_c__identifier,
  &__callbacks_CaptureStatus,
  get_message_typesupport_handle_function,
};

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, data_msgs, msg, CaptureStatus)() {
  return &_CaptureStatus__type_support;
}

#if defined(__cplusplus)
}
#endif
