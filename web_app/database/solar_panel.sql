-- Project Data: Solar_panel (v1)
BEGIN;

INSERT INTO installation (
    installation_id, project_code, project_name, site_name, site_address,
    contact_person, target_code, target_name, specification, status
) VALUES (
    1, 'PRJ-DLPT8', '대륭 포스트타워 8차 태양광 발전 시설 도입',
    '대륭 포스트타워 8차 옥상', '서울 구로구 디지털로26길 43 옥상',
    '봉승현', 'IT-SOLAR-A', '태양광 발전 시설 A',
    '옥상형 태양광 발전 시설 (포스트 6 + 프레임 1 + 패널 1)', 'ACTIVE'
);

-- NOTE: parameter에는 Controller/SolarMotion이 실제로 읽는 동작값만 저장한다.
-- pickup_position / assembly_position은 BASE 절대좌표이며 자세는 A/B/C를 사용한다.
INSERT INTO operation (
    operation_id, installation_id, code, name, sequence, description,
    is_required, estimated_duration_sec, parameter, components
) VALUES
(1, 1, 'post3', '숏 포스트 3번 설치', 1, '좌측 전단 포스트 설치', TRUE, 600,
 '{"speed":100,"acceleration":200,"pick_distance":60,"place_retreat_distance":50,"place_search_limit_z":0.0,"post_place_force":30.0,"post_contact_force":20.0,"post_insert_force":12.0,"place_stiffness_z":500.0,"place_search_velocity":10.0,"place_search_acceleration":20.0,"place_search_timeout":null,"place_direct_insert_base_z_threshold":180.0,"pin_pick_distance":60.0,"pin_place_force":20.0,"pin_place_force_threshold":10.0,"pin_place_stiffness_x":500.0,"pin_place_timeout":10.0}',
 '[{"code":"CMP-POST-03","name":"숏 포스트 A","category":"구조재","pickup_position":{"x":359.50,"y":-241.74,"z":220.0,"A":4.61,"B":179.12,"C":94.59},"assembly_position":{"x":493.50,"y":274.57,"z":225.0,"A":165.34,"B":-179.58,"C":-105.02}},
    {"code":"PIN-A-01","name":"포스트 체결용 핀","category":"평행핀","pickup_position":{"x":588.44,"y":-221.53,"z":75.20,"A":137.27,"B":-179.06,"C":-131.53},"assembly_position":{"x":540.50,"y":271.87,"z":45.12,"A":66.61,"B":-178.73,"C":157.69}}]'),
(2, 1, 'post4', '롱 포스트 4번 설치', 2, '좌측 후단 포스트 설치', TRUE, 600,
 '{"speed":100,"acceleration":200,"pick_distance":60,"place_retreat_distance":50,"place_search_limit_z":0.0,"post_place_force":30.0,"post_contact_force":20.0,"post_insert_force":12.0,"place_stiffness_z":500.0,"place_search_velocity":10.0,"place_search_acceleration":20.0,"place_search_timeout":null,"place_direct_insert_base_z_threshold":230.0,"pin_pick_distance":60.0,"pin_place_force":20.0,"pin_place_force_threshold":10.0,"pin_place_stiffness_x":500.0,"pin_place_timeout":10.0}',
 '[{"code":"CMP-POST-04","name":"롱 포스트 A","category":"구조재","pickup_position":{"x":349.95,"y":-293.97,"z":265.0,"A":3.74,"B":179.21,"C":93.83},"assembly_position":{"x":293.54,"y":278.52,"z":270.0,"A":84.20,"B":-179.06,"C":173.99}},
    {"code":"PIN-A-02","name":"포스트 체결용 핀 A","category":"평행핀","pickup_position":{"x":588.47,"y":-222.05,"z":41.67,"A":129.72,"B":-179.29,"C":-139.06},"assembly_position":{"x":343.81,"y":274.53,"z":44.73,"A":60.40,"B":-178.49,"C":151.40}}]'),
(3, 1, 'post2', '숏 포스트 2 설치', 3, '중앙 전단 포스트 설치', TRUE, 600,
 '{"speed":100,"acceleration":200,"pick_distance":60,"place_retreat_distance":50,"place_search_limit_z":0.0,"post_place_force":30.0,"post_contact_force":20.0,"post_insert_force":12.0,"place_stiffness_z":500.0,"place_search_velocity":10.0,"place_search_acceleration":20.0,"place_search_timeout":null,"place_direct_insert_base_z_threshold":180.0,"pin_pick_distance":60.0,"pin_place_force":20.0,"pin_place_force_threshold":10.0,"pin_place_stiffness_x":500.0,"pin_place_timeout":10.0}',
 '[{"code":"CMP-POST-02","name":"숏 포스트 A","category":"구조재","pickup_position":{"x":428.12,"y":-241.83,"z":220.0,"A":0.35,"B":179.0,"C":90.16},"assembly_position":{"x":488.98,"y":76.43,"z":270.0,"A":163.20,"B":-179.71,"C":-107.01}},
    {"code":"PIN-A-03","name":"포스트 체결용 핀 A","category":"평행핀","pickup_position":{"x":588.45,"y":-262.40,"z":67.12,"A":127.91,"B":-179.22,"C":-141.16},"assembly_position":{"x":537.40,"y":76.03,"z":46.76,"A":66.79,"B":-178.71,"C":158.08}}]'),
(4, 1, 'post5', '롱 포스트 5 설치', 4, '중앙 후단 포스트 설치', TRUE, 600,
 '{"speed":100,"acceleration":200,"pick_distance":60,"place_retreat_distance":50,"place_search_limit_z":0.0,"post_place_force":30.0,"post_contact_force":20.0,"post_insert_force":12.0,"place_stiffness_z":500.0,"place_search_velocity":10.0,"place_search_acceleration":20.0,"place_search_timeout":null,"place_direct_insert_base_z_threshold":230.0,"pin_pick_distance":60.0,"pin_place_force":20.0,"pin_place_force_threshold":10.0,"pin_place_stiffness_x":500.0,"pin_place_timeout":10.0}',
 '[{"code":"CMP-POST-05","name":"롱 포스트 A","category":"구조재","pickup_position":{"x":427.35,"y":-298.33,"z":265.0,"A":173.57,"B":-178.97,"C":-96.51},"assembly_position":{"x":291.81,"y":88.23,"z":270.0,"A":63.03,"B":-179.41,"C":152.76}},
    {"code":"PIN-A-04","name":"포스트 체결용 핀 A","category":"평행핀","pickup_position":{"x":588.16,"y":-262.34,"z":44.01,"A":120.42,"B":-179.37,"C":-148.66},"assembly_position":{"x":337.08,"y":86.14,"z":46.63,"A":57.49,"B":-178.68,"C":148.79}}]'),
(5, 1, 'post6', '롱 포스트 6 설치', 5, '우측 후단 포스트 설치', TRUE, 600,
 '{"speed":100,"acceleration":200,"pick_distance":60,"place_retreat_distance":50,"place_search_limit_z":0.0,"post_place_force":30.0,"post_contact_force":20.0,"post_insert_force":12.0,"place_stiffness_z":500.0,"place_search_velocity":10.0,"place_search_acceleration":20.0,"place_search_timeout":null,"place_direct_insert_base_z_threshold":230.0,"pin_pick_distance":60.0,"pin_place_force":20.0,"pin_place_force_threshold":10.0,"pin_place_stiffness_x":500.0,"pin_place_timeout":10.0}',
 '[{"code":"CMP-POST-06","name":"롱 포스트 A","category":"구조재","pickup_position":{"x":483.90,"y":-241.42,"z":265.0,"A":105.79,"B":179.65,"C":-164.60},"assembly_position":{"x":285.87,"y":-119.55,"z":214.77,"A":143.93,"B":178.63,"C":-126.73}},
    {"code":"PIN-A-05","name":"포스트 체결용 핀 A","category":"평행핀","pickup_position":{"x":587.94,"y":-305.06,"z":67.79,"A":56.99,"B":-179.50,"C":147.94},"assembly_position":{"x":337.22,"y":-118.14,"z":47.64,"A":57.57,"B":-178.56,"C":148.99}}]'),
(6, 1, 'post1', '숏 포스트 1 설치', 6, '우측 전단 포스트 설치', TRUE, 600,
 '{"speed":100,"acceleration":200,"pick_distance":60,"place_retreat_distance":50,"place_search_limit_z":0.0,"post_place_force":30.0,"post_contact_force":20.0,"post_insert_force":12.0,"place_stiffness_z":500.0,"place_search_velocity":10.0,"place_search_acceleration":20.0,"place_search_timeout":null,"place_direct_insert_base_z_threshold":180.0,"pin_pick_distance":60.0,"pin_place_force":20.0,"pin_place_force_threshold":10.0,"pin_place_stiffness_x":500.0,"pin_place_timeout":10.0}',
 '[{"code":"CMP-POST-01","name":"숏 포스트 A","category":"구조재","pickup_position":{"x":491.06,"y":-295.50,"z":220.0,"A":107.47,"B":179.70,"C":-162.62},"assembly_position":{"x":484.19,"y":-122.82,"z":230.0,"A":139.71,"B":179.38,"C":-130.44}},
    {"code":"PIN-A-06","name":"포스트 체결용 핀 A","category":"평행핀","pickup_position":{"x":586.87,"y":-307.07,"z":38.99,"A":55.72,"B":-178.98,"C":146.95},"assembly_position":{"x":533.44,"y":-124.67,"z":46.84,"A":53.28,"B":-178.41,"C":144.91}}]'),
(7, 1, 'frameA', '프레임 A 조립', 7, '상부 프레임 결합', TRUE, 900,
'{"speed":100,"acceleration":200,"frame_pick_distance":60.0,"frame_place_distance":50.0,"frame_place_force":30.0,"frame_place_force_threshold":10.0,"frame_place_stiffness_z":500.0,"frame_place_timeout":10.0,"frame_periodic_x_amplitude":8.0,"frame_periodic_y_amplitude":85.0,"frame_periodic_period":2.0,"frame_periodic_atime":0.5,"frame_periodic_repeat":2.0,"snapfit_pick_distance":60.0,"snapfit_arc_height":100.0,"snapfit_arc_steps":6.0,"snapfit_place_distance":50.0,"snapfit_place_force":20.0,"snapfit_place_force_threshold":10.0,"snapfit_place_stiffness_z":500.0,"snapfit_place_timeout":10.0}',
 '[{"code": "CMP-FRAME-A", "name": "일체형 프레임", "category": "구조재", "pickup_position": {"x": -427.64, "y": 53.79, "z": 249.31, "A": 14.08, "B": -179.84, "C": -74.73}, "assembly_position": {"x": 387.13, "y": 81.77, "z": 216.88, "A": 42.64, "B": -179.35, "C": -45.74}},
    {"code": "SNAPFIT-A-01", "name": "좌측 전단 포스트 체결용 핀 A", "category": "스냅핏", "pickup_position": {"x": 489.30, "y": -343.10, "z": 67.37, "A": 33.28, "B": -179.13, "C": -54.92}, "assembly_position": {"x": 288.30, "y": 282.54, "z": 267.76, "A": 55.83, "B": -178.62, "C": -32.85}},
    {"code": "SNAPFIT-A-02", "name": "중앙 전단 포스트 체결용 핀 A", "category": "스냅핏", "pickup_position": {"x": 447.99, "y": -343.84, "z": 64.34, "A": 37.94, "B": -179.19, "C": -49.94}, "assembly_position": {"x": 491.97, "y": 276.93, "z": 214.71, "A": 39.63, "B": -178.31, "C": -48.45}},
    {"code": "SNAPFIT-A-03", "name": "우측 전단 포스트 체결용 핀 A", "category": "스냅핏", "pickup_position": {"x": 400.14, "y": -345.37, "z": 64.95, "A": 23.68, "B": -179.17, "C": -64.05}, "assembly_position": {"x": 487.41, "y": 79.86, "z": 214.24, "A": 26.10, "B": -178.21, "C": -61.67}},
    {"code": "SNAPFIT-A-04", "name": "좌측 후단 포스트 체결용 핀 A", "category": "스냅핏", "pickup_position": {"x": 347.12, "y": -346.80, "z": 64.97, "A": 14.43, "B": -179.16, "C": -73.43}, "assembly_position": {"x": 285.27, "y": 85.03, "z": 264.87, "A": 33.93, "B": -178.43, "C": -54.32}},
    {"code": "SNAPFIT-A-05", "name": "중앙 후단 포스트 체결용 핀 A", "category": "스냅핏", "pickup_position": {"x": 491.56, "y": -393.21, "z": 63.28, "A": 53.46, "B": -179.15, "C": -34.61}, "assembly_position": {"x": 282.47, "y": -114.30, "z": 264.28, "A": 0.95, "B": -177.65, "C": -87.88}},
    {"code": "SNAPFIT-A-06", "name": "우측 후단 포스트 체결용 핀 A", "category": "스냅핏", "pickup_position": {"x": 444.16, "y": -391.49, "z": 63.68, "A": 39.39, "B": -179.17, "C": -48.57}, "assembly_position": {"x": 481.73, "y": -118.74, "z": 215.07, "A": 26.15, "B": -177.74, "C": -62.31}}]'),
(8, 1, 'solarpanelA', '태양광 패널 A 설치', 8, '패널 배치 및 양측 위치 검사', TRUE, 1200,
'{"speed":100,"acceleration":200,"panel_pick_distance":100.0,"panel_place_distance":50.0,"panel_place_speed":30.0,"panel_place_acceleration":50.0,"panel_release_wait":1.0,"panel_release_retreat_distance":30.0,"panel_periodic_y_amplitude":5.0,"panel_periodic_period":2.0,"panel_periodic_atime":0.5,"panel_periodic_repeat":1.0}',
 '[{"code":"CMP-PANEL-A","name":"태양광 패널 A","category":"태양광 패널","quantity":1,"pickup_position":{"x":-423.79,"y":-430.08,"z":158.03,"A":163.0,"B":179.65,"C":163.6},"assembly_position":{"x":470.11,"y":80.35,"z":348.06,"A":85.67,"B":-179.41,"C":86.05},"assembly_release_position":{"x":364.82,"y":71.54,"z":311.41,"A":173.77,"B":-138.44,"C":175.81},"assembly_side_positions":[{"x":384.96,"y":304.7,"z":220.0,"A":115.44,"B":-179.59,"C":116.03},{"x":366.34,"y":-138.45,"z":220.0,"A":157.72,"B":179.68,"C":158.07}]}]');

INSERT INTO robot (robot_id, robot_code, name, manufacturer, model, status, dofs, payload_kg)
VALUES (1, 'RB-01', '두산 M0609 협동 로봇', 'Doosan Robotics', 'M0609', 'IDLE', 6, 6.0);

INSERT INTO sensor (sensor_id, robot_id, name, type, force_max_n, torque_max_nm, is_active)
VALUES (1, 1, 'F/T 센서 1호', 'FORCE_TORQUE', 500, 50, TRUE);

SELECT setval(pg_get_serial_sequence('installation','installation_id'), COALESCE(MAX(installation_id), 1), MAX(installation_id) IS NOT NULL) FROM installation;
SELECT setval(pg_get_serial_sequence('operation','operation_id'), COALESCE(MAX(operation_id), 1), MAX(operation_id) IS NOT NULL) FROM operation;
SELECT setval(pg_get_serial_sequence('robot','robot_id'), COALESCE(MAX(robot_id), 1), MAX(robot_id) IS NOT NULL) FROM robot;
SELECT setval(pg_get_serial_sequence('sensor','sensor_id'), COALESCE(MAX(sensor_id), 1), MAX(sensor_id) IS NOT NULL) FROM sensor;
SELECT setval(pg_get_serial_sequence('work_order','work_order_id'), COALESCE(MAX(work_order_id), 1), MAX(work_order_id) IS NOT NULL) FROM work_order;
SELECT setval(pg_get_serial_sequence('work_execution','work_execution_id'), COALESCE(MAX(work_execution_id), 1), MAX(work_execution_id) IS NOT NULL) FROM work_execution;
SELECT setval(pg_get_serial_sequence('operation_execution','operation_execution_id'), COALESCE(MAX(operation_execution_id), 1), MAX(operation_execution_id) IS NOT NULL) FROM operation_execution;
SELECT setval(pg_get_serial_sequence('log','log_id'), COALESCE(MAX(log_id), 1), MAX(log_id) IS NOT NULL) FROM log;
SELECT setval(pg_get_serial_sequence('sensor_data','sensor_data_id'), COALESCE(MAX(sensor_data_id), 1), MAX(sensor_data_id) IS NOT NULL) FROM sensor_data;

COMMIT;