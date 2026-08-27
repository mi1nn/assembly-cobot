# Frame 및 Snapfit 작업 단위 테스트

실제 `solar_panel_robot controller`의 `/execute_operation` Action을 직접 호출해
Frame과 Snapfit 동작을 Pick/Place 단위로 시험하는 절차다.

> 아래 명령은 실제 로봇을 움직인다. 작업 좌표, TCP, Tool, Robot mode와 이동
> 경로를 현장에서 확인하고 비상 정지 수단을 준비한 뒤 실행한다.

## 1. 준비 및 실행

Mock Action Server와 실제 Controller는 동시에 실행하지 않는다. 소스를 변경했다면
빌드한 후 Controller를 실행한다.

```bash
cd ~/workspace/assembly-cobot
source /opt/ros/jazzy/setup.bash
colcon build --packages-select solar_panel_interface solar_panel_robot
source install/setup.bash
ros2 run solar_panel_robot controller
```

Controller 로그에 `READY`가 표시된 뒤 새 터미널에서 환경과 인터페이스를 확인한다.

```bash
cd ~/workspace/assembly-cobot
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 action info /execute_operation
ros2 topic echo /dsr01/status
```

모든 Goal ID는 0보다 커야 한다. `robot_id`는 Controller 파라미터와 같아야 하며
기본값은 `1`이다. `operation_execution_id`는 동작별로 다른 값을 사용한다.

## 2. Frame 테스트

현재 `CMP-FRAME-A` 좌표:

| 구분 | x | y | z | A | B | C |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Pick | -427.64 | 53.79 | 309.31 | 14.08 | -179.84 | -74.73 |
| Place | 387.13 | 81.77 | 276.88 | 42.64 | -179.35 | -45.74 |

### 2.1 Frame Pick

`Home → Arc 안전 접근 → Pick → Gripper Close → 안전 접근점 복귀` 순서다.
아래 설정의 안전 접근점은 BASE Z 방향 60 mm 위인 z=369.31이다.

```bash
ros2 action send_goal --feedback /execute_operation \
  solar_panel_interface/action/ExecuteOperation \
  "{work_order_id: 1, work_execution_id: 1, operation_id: 7,
    operation_code: 'FRAME_PICK', operation_execution_id: 701, robot_id: 1,
    parameters: [{key: 'speed', value: '30'},
      {key: 'acceleration', value: '60'},
      {key: 'frame_pick_distance', value: '60'},
      {key: 'frame_arc_height', value: '100'},
      {key: 'frame_arc_steps', value: '6'}],
    components: '[{\"code\":\"CMP-FRAME-A\",\"pickup_position\":{\"x\":-427.64,\"y\":53.79,\"z\":309.31,\"A\":14.08,\"B\":-179.84,\"C\":-74.73}}]'}"
```

### 2.2 Frame Place

Frame을 정상적으로 파지한 상태에서만 실행한다. `현재 TCP → Arc 안전 접근 →
Place → Gripper Open → 안전 접근점 복귀` 순서다.

```bash
ros2 action send_goal --feedback /execute_operation \
  solar_panel_interface/action/ExecuteOperation \
  "{work_order_id: 1, work_execution_id: 1, operation_id: 7,
    operation_code: 'FRAME_PLACE', operation_execution_id: 702, robot_id: 1,
    parameters: [{key: 'speed', value: '30'},
      {key: 'acceleration', value: '60'},
      {key: 'frame_place_distance', value: '50'},
      {key: 'frame_arc_height', value: '100'},
      {key: 'frame_arc_steps', value: '6'}],
    components: '[{\"code\":\"CMP-FRAME-A\",\"assembly_position\":{\"x\":387.13,\"y\":81.77,\"z\":276.88,\"A\":42.64,\"B\":-179.35,\"C\":-45.74}}]'}"
```

## 3. Snapfit 테스트

다음 예시는 `SNAPFIT-A-01`을 사용한다.

| 구분 | x | y | z | A | B | C |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Pick | 489.30 | -343.10 | 127.37 | 33.28 | -179.13 | -54.92 |
| Place | 288.30 | 282.54 | 327.76 | 55.83 | -178.62 | -32.85 |

### 3.1 Snapfit Pick

```bash
ros2 action send_goal --feedback /execute_operation \
  solar_panel_interface/action/ExecuteOperation \
  "{work_order_id: 1, work_execution_id: 1, operation_id: 7,
    operation_code: 'SNAPFIT_PICK', operation_execution_id: 711, robot_id: 1,
    parameters: [{key: 'speed', value: '20'},
      {key: 'acceleration', value: '40'},
      {key: 'snapfit_pick_distance', value: '50'}],
    components: '[{\"code\":\"SNAPFIT-A-01\",\"pickup_position\":{\"x\":489.30,\"y\":-343.10,\"z\":127.37,\"A\":33.28,\"B\":-179.13,\"C\":-54.92}}]'}"
```

### 3.2 Snapfit Place

Snapfit을 파지한 상태에서만 실행한다. `assembly_position`까지 이동한 후 TOOL +Z
방향으로 Force 삽입하므로 삽입 방향과 Force 설정을 반드시 확인한다.

```bash
ros2 action send_goal --feedback /execute_operation \
  solar_panel_interface/action/ExecuteOperation \
  "{work_order_id: 1, work_execution_id: 1, operation_id: 7,
    operation_code: 'SNAPFIT_PLACE', operation_execution_id: 712, robot_id: 1,
    parameters: [{key: 'speed', value: '10'},
      {key: 'acceleration', value: '20'},
      {key: 'snapfit_place_distance', value: '30'},
      {key: 'snapfit_place_force', value: '20'},
      {key: 'snapfit_place_force_threshold', value: '10'},
      {key: 'snapfit_place_stiffness_z', value: '500'},
      {key: 'snapfit_place_timeout', value: '5'}],
    components: '[{\"code\":\"SNAPFIT-A-01\",\"assembly_position\":{\"x\":288.30,\"y\":282.54,\"z\":327.76,\"A\":55.83,\"B\":-178.62,\"C\":-32.85}}]'}"
```

## 4. 결과 확인

정상 실행은 Goal 수락 후 `STATUS_RUNNING`, `STATUS_COMPLETED` feedback과
`success: true` 결과를 반환한다. Goal이 거절되면 Controller 터미널의 경고를
확인한다. 주요 원인은 Controller 미준비, 정지 상태, 0 이하 ID, 잘못된
components JSON, `robot_id` 불일치, 미지원 operation code, 다른 Operation 실행
중이다.

## 5. 정지 및 복구

정지는 현재 Goal과 같은 `work_execution_id`, `operation_execution_id`,
`robot_id`로 요청한다. Frame Pick 예시는 다음과 같다.

```bash
ros2 service call /stop_operation \
  solar_panel_interface/srv/StopOperation \
  '{work_execution_id: 1, operation_execution_id: 701, robot_id: 1}'
```

정지된 Operation이 끝난 것을 확인한 뒤 복구한다.

```bash
ros2 service call /recover_robot \
  solar_panel_interface/srv/RecoverRobot \
  '{robot_id: 1}'
```

복구 후 `/dsr01/status`가 `READY`인지 확인한다.
