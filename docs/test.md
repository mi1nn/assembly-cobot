# Operation 단위별 Action 테스트

DB의 `operation.parameter`와 `operation.components` 값을 기준으로 각 모션을 직접 테스트한다.
Backend/Bridge 작업지시 흐름은 사용하지 않고 `/execute_operation` Action Server로 Goal을 보낸다.

> 실제 로봇이 움직인다. 저속 확인, 비상정지 준비, 작업영역 간섭 확인 후 실행한다.
> Place는 대응하는 Pick을 먼저 완료해 부품을 잡은 상태에서 실행한다.

## 1. 공통 준비

아래 블록은 테스트할 터미널에서 한 번만 실행한다.

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 action info /execute_operation

send_operation() {
  local operation_code="$1"
  local operation_id="$2"
  local execution_id="$3"
  local parameters_json="$4"
  local components_json="$5"
  local goal

  goal=$(jq -cn \
    --arg code "$operation_code" \
    --argjson operation_id "$operation_id" \
    --argjson execution_id "$execution_id" \
    --argjson parameters "$parameters_json" \
    --arg components "$components_json" \
    '{
      work_order_id: 1,
      work_execution_id: 1,
      operation_id: $operation_id,
      operation_code: $code,
      operation_execution_id: $execution_id,
      robot_id: 1,
      parameters: ($parameters | to_entries | map({key: .key, value: (.value | tojson)})),
      components: $components
    }')

  ros2 action send_goal --feedback \
    /execute_operation \
    solar_panel_interface/action/ExecuteOperation \
    "$goal"
}
```

`ros2 action info`에서 Action server가 1개인지 확인한다. 각 명령의 execution ID는 재실행 시 다른 값으로 바꿔도 된다.

## 2. Post

샘플은 DB operation 1의 `CMP-POST-03` 좌표를 사용한다.

### POST_PICK

```bash
send_operation POST_PICK 1 1101 \
  '{"speed":50,"acceleration":50,"pick_distance":60}' \
  '[{"code":"CMP-POST-03","pickup_position":{"x":359.50,"y":-241.74,"z":220.0,"A":4.61,"B":179.12,"C":94.59}}]'
```

### POST_PLACE

```bash
send_operation POST_PLACE 1 1102 \
  '{"speed":50,"acceleration":50,"place_retreat_distance":50,"place_search_limit_z":0.0,"post_place_force":30.0,"post_contact_force":20.0,"post_insert_force":12.0,"place_stiffness_z":500.0,"place_search_velocity":10.0,"place_search_acceleration":20.0,"place_search_timeout":null,"place_direct_insert_base_z_threshold":180.0}' \
  '[{"code":"CMP-POST-03","assembly_position":{"x":493.50,"y":274.57,"z":225.0,"A":165.34,"B":-179.58,"C":-105.02}}]'
```

## 3. Pin

샘플은 DB operation 1의 `PIN-A-01` 좌표를 사용한다. `POST_PIN_PICK/PLACE`도 동일 메서드의 호환 별칭이다.

### PIN_PICK

```bash
send_operation PIN_PICK 1 1201 \
  '{"speed":50,"acceleration":50,"pin_pick_distance":60.0}' \
  '[{"code":"PIN-A-01","pickup_position":{"x":588.44,"y":-221.53,"z":75.20,"A":137.27,"B":-179.06,"C":-131.53}}]'
```

### PIN_PLACE

```bash
send_operation PIN_PLACE 1 1202 \
  '{"speed":50,"acceleration":50,"place_retreat_distance":50.0,"pin_place_force":20.0,"pin_place_force_threshold":10.0,"pin_place_stiffness_x":500.0,"pin_place_timeout":10.0}' \
  '[{"code":"PIN-A-01","assembly_position":{"x":540.50,"y":271.87,"z":45.12,"A":66.61,"B":-178.73,"C":157.69}}]'
```

## 4. Frame

DB operation 7의 `CMP-FRAME-A`를 사용한다.

### FRAME_PICK

```bash
send_operation FRAME_PICK 7 1701 \
  '{"speed":50,"acceleration":50,"frame_pick_distance":60.0}' \
  '[{"code":"CMP-FRAME-A","pickup_position":{"x":-427.64,"y":53.79,"z":249.31,"A":14.08,"B":-179.84,"C":-74.73}}]'
```

### FRAME_PLACE

```bash
send_operation FRAME_PLACE 7 1702 \
  '{"speed":50,"acceleration":50,"frame_place_distance":50.0,"frame_place_force":30.0,"frame_place_force_threshold":10.0,"frame_place_stiffness_z":500.0,"frame_place_timeout":10.0,"frame_periodic_x_amplitude":5.0,"frame_periodic_y_amplitude":90.0,"frame_periodic_period":2.0,"frame_periodic_atime":0.5,"frame_periodic_repeat":2.0}' \
  '[{"code":"CMP-FRAME-A","assembly_position":{"x":387.13,"y":81.77,"z":216.88,"A":42.64,"B":-179.35,"C":-45.74}}]'
```

## 5. Panel

DB operation 8의 `CMP-PANEL-A`를 사용한다.

### PANEL_PICK

```bash
send_operation PANEL_PICK 8 1801 \
  '{"speed":50,"acceleration":50,"panel_pick_distance":60.0}' \
  '[{"code":"CMP-PANEL-A","pickup_position":{"x":-423.79,"y":-430.08,"z":158.03,"A":163.0,"B":179.65,"C":163.6}}]'
```

### PANEL_PLACE

```bash
send_operation PANEL_PLACE 8 1802 \
  '{"speed":50,"acceleration":50,"panel_place_distance":50.0,"panel_place_speed":30.0,"panel_place_acceleration":50.0,"panel_release_wait":1.0,"panel_release_retreat_distance":30.0,"panel_periodic_y_amplitude":5.0,"panel_periodic_period":2.0,"panel_periodic_atime":0.5,"panel_periodic_repeat":1.0}' \
  '[{"code":"CMP-PANEL-A","assembly_position":{"x":470.11,"y":80.35,"z":348.06,"A":85.67,"B":-179.41,"C":86.05},"assembly_release_position":{"x":364.82,"y":71.54,"z":311.41,"A":173.77,"B":-138.44,"C":175.81},"assembly_side_positions":[{"x":384.96,"y":304.7,"z":220.0,"A":115.44,"B":-179.59,"C":116.03},{"x":366.34,"y":-138.45,"z":220.0,"A":157.72,"B":179.68,"C":158.07}]}]'
```

## 6. Snapfit

샘플은 DB operation 7의 `SNAPFIT-A-01` 좌표를 사용한다.

### SNAPFIT_PICK

```bash
send_operation SNAPFIT_PICK 7 1711 \
  '{"speed":50,"acceleration":50,"snapfit_pick_distance":60.0,"snapfit_arc_height":50.0,"snapfit_arc_steps":6.0}' \
  '[{"code":"SNAPFIT-A-01","pickup_position":{"x":489.30,"y":-343.10,"z":67.37,"A":33.28,"B":-179.13,"C":-54.92}}]'
```

### SNAPFIT_PLACE

```bash
send_operation SNAPFIT_PLACE 7 1712 \
  '{"speed":50,"acceleration":50,"snapfit_place_distance":50.0,"snapfit_place_force":20.0,"snapfit_place_force_threshold":10.0,"snapfit_place_stiffness_z":500.0,"snapfit_place_timeout":10.0}' \
  '[{"code":"SNAPFIT-A-01","assembly_position":{"x":288.30,"y":282.54,"z":267.76,"A":55.83,"B":-178.62,"C":-32.85}}]'
```

## 7. 권장 테스트 순서

각 부품은 반드시 Pick과 Place를 연속해서 실행한다.

```text
POST_PICK     -> POST_PLACE
PIN_PICK      -> PIN_PLACE
FRAME_PICK    -> FRAME_PLACE
PANEL_PICK    -> PANEL_PLACE
SNAPFIT_PICK  -> SNAPFIT_PLACE
```

첫 실물 테스트에서는 각 명령의 `speed`, `acceleration`과 별도 Place 속도를 낮춘 뒤 경로를 확인한다.
