# Controller -> ROS Bridge
# Robot/System 이벤트 및 Operation 세부 단계 로그

uint8 SEVERITY_INFO=0
uint8 SEVERITY_WARNING=1
uint8 SEVERITY_ERROR=2
uint8 SEVERITY_CRITICAL=3

# 항상 존재하는 Robot 식별자
uint64 robot_id

# Operation과 무관한 시스템 이벤트에서는 0
uint64 work_execution_id
uint64 operation_execution_id

# Operation과 무관한 시스템 이벤트에서는 빈 문자열
string operation_code
string phase
string status

uint8 severity
string code
string message

# JSON 문자열. 추가 구조화 정보가 없으면 "{}"
string detail
