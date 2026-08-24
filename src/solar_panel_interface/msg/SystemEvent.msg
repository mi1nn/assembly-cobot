# Controller -> ROS Bridge
# Operation 외부 상태 변경 및 오류 이벤트

uint8 SEVERITY_INFO=0
uint8 SEVERITY_WARNING=1
uint8 SEVERITY_ERROR=2
uint8 SEVERITY_CRITICAL=3

uint64 robot_id
uint8 severity
string code
string message
