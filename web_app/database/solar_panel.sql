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

-- NOTE: Post 작업은 DB parameter/components 값을 Robot Motion에 직접 전달한다.
-- Post pickup/assembly 자세는 측정값을 사용하며, 미측정 핀 자세는 null로 둔다.
INSERT INTO operation (
    operation_id, installation_id, code, name, sequence, description,
    is_required, estimated_duration_sec, parameter, components
) VALUES
(1, 1, 'postSA', '숏 포스트 A 설치', 1, '좌측 전단 포스트 설치', TRUE, 600,
 '{"tcp":{"x":0,"y":0,"z":150},"ucs":null,"tool":"gripper_post","fixture":"jig_post","coordinate_system":"BASE","speed":100,"acceleration":200,"pick_distance":50,"place_retreat_distance":50,"place_search_limit_z":0.0,"place_force":40.0,"place_contact_force":20.0,"place_insert_force":12.0,"place_stiffness_z":500.0,"place_search_velocity":10.0,"place_search_acceleration":20.0,"place_search_timeout":null}',
 '[{"code":"CMP-POST-SA","name":"숏 포스트 A","category":"구조재","pickup_position":{"x":359.6,"y":-243.1,"z":160.0,"A":155.5,"B":177.7,"C":-116.3},"assembly_position":{"x":490.7,"y":271.8,"z":174.8,"A":179.3,"B":178.3,"C":-91.9}},
    {"code":"PIN-A","name":"포스트 체결용 핀","category":"평행핀","pickup_position":null,"assembly_position":null}]'),
(2, 1, 'postSB', '숏 포스트 B 설치', 2, '중앙 전단 포스트 설치', TRUE, 600,
 '{"tcp":{"x":0,"y":0,"z":150},"ucs":null,"tool":"gripper_post","fixture":"jig_post","coordinate_system":"BASE","speed":100,"acceleration":200,"pick_distance":50,"place_retreat_distance":50,"place_search_limit_z":0.0,"place_force":40.0,"place_contact_force":20.0,"place_insert_force":12.0,"place_stiffness_z":500.0,"place_search_velocity":10.0,"place_search_acceleration":20.0,"place_search_timeout":null}',
 '[{"code":"CMP-POST-SB","name":"숏 포스트 B","category":"구조재","pickup_position":{"x":425.5,"y":-240.6,"z":159.4,"A":157.4,"B":177.7,"C":-114.2},"assembly_position":{"x":487.1,"y":76.6,"z":173.1,"A":173.7,"B":178.2,"C":-97.4}},
    {"code":"PIN-A","name":"포스트 체결용 핀 A","category":"평행핀","pickup_position":null,"assembly_position":null}]'),
(3, 1, 'postSC', '숏 포스트 C 설치', 3, '우측 전단 포스트 설치', TRUE, 600,
 '{"tcp":{"x":0,"y":0,"z":150},"ucs":null,"tool":"gripper_post","fixture":"jig_post","coordinate_system":"BASE","speed":100,"acceleration":200,"pick_distance":50,"place_retreat_distance":50,"place_search_limit_z":0.0,"place_force":40.0,"place_contact_force":20.0,"place_insert_force":12.0,"place_stiffness_z":500.0,"place_search_velocity":10.0,"place_search_acceleration":20.0,"place_search_timeout":null}',
 '[{"code":"CMP-POST-SC","name":"숏 포스트 C","category":"구조재","pickup_position":{"x":493.2,"y":-242.5,"z":230.0,"A":162.2,"B":178.9,"C":-109.0},"assembly_position":{"x":489.0,"y":-125.1,"z":230.0,"A":168.8,"B":178.1,"C":-102.5}},
    {"code":"PIN-A","name":"포스트 체결용 핀 A","category":"평행핀","pickup_position":null,"assembly_position":null}]'),
(4, 1, 'postLA', '롱 포스트 A 설치', 4, '좌측 후단 포스트 설치', TRUE, 600,
'{"tcp":{"x":0,"y":0,"z":150},"ucs":null,"tool":"gripper_post","fixture":"jig_post","coordinate_system":"BASE","speed":100,"acceleration":200,"pick_distance":50,"place_retreat_distance":50,"place_search_limit_z":0.0,"place_force":40.0,"place_contact_force":20.0,"place_insert_force":12.0,"place_stiffness_z":500.0,"place_search_velocity":10.0,"place_search_acceleration":20.0,"place_search_timeout":null}',
 '[{"code":"CMP-POST-LA","name":"롱 포스트 A","category":"구조재","pickup_position":{"x":351.2,"y":-295.3,"z":207.3,"A":150.7,"B":177.5,"C":-121.1},"assembly_position":{"x":289.3,"y":277.1,"z":227.2,"A":9.8,"B":-178.0,"C":98.5}},
    {"code":"PIN-A","name":"포스트 체결용 핀 A","category":"평행핀","pickup_position":null,"assembly_position":null}]'),
(5, 1, 'postLB', '롱 포스트 B 설치', 5, '중앙 후단 포스트 설치', TRUE, 600,
'{"tcp":{"x":0,"y":0,"z":150},"ucs":null,"tool":"gripper_post","fixture":"jig_post","coordinate_system":"BASE","speed":100,"acceleration":200,"pick_distance":50,"place_retreat_distance":50,"place_search_limit_z":0.0,"place_force":40.0,"place_contact_force":20.0,"place_insert_force":12.0,"place_stiffness_z":500.0,"place_search_velocity":10.0,"place_search_acceleration":20.0,"place_search_timeout":null}',
 '[{"code":"CMP-POST-LB","name":"롱 포스트 B","category":"구조재","pickup_position":{"x":422.7,"y":-296.5,"z":207.3,"A":150.7,"B":177.7,"C":-120.9},"assembly_position":{"x":285.3,"y":85.9,"z":222.1,"A":11.2,"B":-177.7,"C":99.8}},
    {"code":"PIN-A","name":"포스트 체결용 핀 A","category":"평행핀","pickup_position":null,"assembly_position":null}]'),
(6, 1, 'postLC', '롱 포스트 C 설치', 6, '우측 후단 포스트 설치', TRUE, 600,
'{"tcp":{"x":0,"y":0,"z":150},"ucs":null,"tool":"gripper_post","fixture":"jig_post","coordinate_system":"BASE","speed":100,"acceleration":200,"pick_distance":50,"place_retreat_distance":50,"place_search_limit_z":0.0,"place_force":40.0,"place_contact_force":20.0,"place_insert_force":12.0,"place_stiffness_z":500.0,"place_search_velocity":10.0,"place_search_acceleration":20.0,"place_search_timeout":null}',
 '[{"code":"CMP-POST-LC","name":"롱 포스트 C","category":"구조재","pickup_position":{"x":492.6,"y":-296.4,"z":210.6,"A":153.2,"B":178.6,"C":-119.1},"assembly_position":{"x":280.1,"y":-116.5,"z":222.5,"A":11.2,"B":-178.0,"C":98.9}},
    {"code":"PIN-A","name":"포스트 체결용 핀 A","category":"평행핀","pickup_position":null,"assembly_position":null}]'),
(7, 1, 'frameA', '프레임 A 조립', 7, '상부 프레임 결합', TRUE, 900,
'{"tcp":{"x":0,"y":0,"z":150},"ucs":null,"tool":"gripper_post","fixture":"jig_frame","coordinate_system":"BASE","speed":100,"acceleration":200,"pick_distance":50,"place_retreat_distance":50,"place_search_limit_z":0.0,"place_force":40.0,"place_contact_force":20.0,"place_insert_force":12.0,"place_stiffness_z":500.0,"place_search_velocity":10.0,"place_search_acceleration":20.0,"place_search_timeout":null}',
 '[{"code": "CMP-FRAME-A", "name": "일체형 프레임", "category": "구조재", "pickup_position": null, "assembly_position": null},
    {"code": "SNAPFIT-A-01", "name": "좌측 전단 포스트 체결용 핀 A", "category": "스냅핏", "pickup_position": null, "assembly_position": null},
    {"code": "SNAPFIT-A-02", "name": "중앙 전단 포스트 체결용 핀 A", "category": "스냅핏", "pickup_position": null, "assembly_position": null},
    {"code": "SNAPFIT-A-03", "name": "우측 전단 포스트 체결용 핀 A", "category": "스냅핏", "pickup_position": null, "assembly_position": null},
    {"code": "SNAPFIT-A-04", "name": "좌측 후단 포스트 체결용 핀 A", "category": "스냅핏", "pickup_position": null, "assembly_position": null},
    {"code": "SNAPFIT-A-05", "name": "중앙 후단 포스트 체결용 핀 A", "category": "스냅핏", "pickup_position": null, "assembly_position": null},
    {"code": "SNAPFIT-A-06", "name": "우측 후단 포스트 체결용 핀 A", "category": "스냅핏", "pickup_position": null, "assembly_position": null}]'),
(8, 1, 'solarpanelA', '태양광 패널 A 설치', 8, '패널 20장 양중 및 체결', TRUE, 1200,
'{"tcp":{"x":0,"y":0,"z":150},"ucs":null,"tool":"gripper_post","fixture":"jig_panel","coordinate_system":"BASE","speed":100,"acceleration":200,"pick_distance":50,"place_retreat_distance":50,"place_search_limit_z":0.0,"place_force":40.0,"place_contact_force":20.0,"place_insert_force":12.0,"place_stiffness_z":500.0,"place_search_velocity":10.0,"place_search_acceleration":20.0,"place_search_timeout":null}',
 '[{"code": "CMP-PANEL-A", "name": "태양광 패널 A", "category": "태양광 패널", "pickup_position": null, "assembly_position": null},
    {"code": "SNAPFIT-B-01", "name": "좌측 전단 포스트 체결용 핀 B", "category": "스냅핏", "pickup_position": null, "assembly_position": null},
    {"code": "SNAPFIT-B-02", "name": "중앙 전단 포스트 체결용 핀 B", "category": "스냅핏", "pickup_position": null, "assembly_position": null},
    {"code": "SNAPFIT-B-03", "name": "우측 전단 포스트 체결용 핀 B", "category": "스냅핏", "pickup_position": null, "assembly_position": null},
    {"code": "SNAPFIT-B-04", "name": "좌측 후단 포스트 체결용 핀 B", "category": "스냅핏", "pickup_position": null, "assembly_position": null},
    {"code": "SNAPFIT-B-05", "name": "중앙 후단 포스트 체결용 핀 B", "category": "스냅핏", "pickup_position": null, "assembly_position": null},
    {"code": "SNAPFIT-B-06", "name": "우측 후단 포스트 체결용 핀 B", "category": "스냅핏", "pickup_position": null, "assembly_position": null}]');

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
