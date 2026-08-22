-- Mock Data (v2): 통합 스키마
BEGIN;

INSERT INTO installation (
    installation_id, project_code, project_name, site_name, site_address,
    contact_person, target_code, target_name, specification, status
) VALUES (
    1, 'PRJ-DLPT8', '대륭 포스트타워 8차 태양광 발전 시설 도입',
    '대륭 포스트타워 8차 옥상', '서울특별시 중구 을지로 100 대륭포스트타워8차',
    '김태양', 'IT-SOLAR-A', '태양광 발전 시설 A',
    '옥상형 태양광 발전 시설 (포스트 6 + 프레임 1 + 패널 20)', 'ACTIVE'
);

INSERT INTO operation (
    operation_id, installation_id, code, name, sequence, description,
    is_required, estimated_duration_sec, parameter, components
) VALUES
(1, 1, 'postA', '포스트 A 설치', 1, '좌측 전단 포스트 설치', TRUE, 600,
 '{"tool":"gripper_post","tcp":{"x":0,"y":0,"z":150},"speed":80,"force":30,"fixture":"jig_post","coordinate_system":"BASE"}',
 '[{"code":"CMP-POST-A","name":"포스트 A","category":"구조재","specification":"H-beam 200x100, L=2500","quantity":1,"pickup_position":{"x":200,"y":200,"z":300,"frame":"BASE"},"assembly_position":{"x":1000,"y":1000,"z":50,"frame":"BASE"}},{"code":"CMP-BOLT-M16","name":"앵커 볼트 M16","category":"체결부품","specification":"M16x120, HV 볼트","quantity":4}]'),
(2, 1, 'postB', '포스트 B 설치', 2, '중앙 전단 포스트 설치', TRUE, 600,
 '{"tool":"gripper_post","tcp":{"x":0,"y":0,"z":150},"speed":80,"force":30,"fixture":"jig_post","coordinate_system":"BASE"}',
 '[{"code":"CMP-POST-B","name":"포스트 B","quantity":1,"pickup_position":{"x":350,"y":200,"z":300,"frame":"BASE"},"assembly_position":{"x":3000,"y":1000,"z":50,"frame":"BASE"}},{"code":"CMP-BOLT-M16","name":"앵커 볼트 M16","quantity":4}]'),
(3, 1, 'postC', '포스트 C 설치', 3, '우측 전단 포스트 설치', TRUE, 600,
 '{"tool":"gripper_post","tcp":{"x":0,"y":0,"z":150},"speed":80,"force":30,"fixture":"jig_post","coordinate_system":"BASE"}',
 '[{"code":"CMP-POST-C","name":"포스트 C","quantity":1,"pickup_position":{"x":500,"y":200,"z":300,"frame":"BASE"},"assembly_position":{"x":5000,"y":1000,"z":50,"frame":"BASE"}},{"code":"CMP-BOLT-M16","name":"앵커 볼트 M16","quantity":4}]'),
(4, 1, 'postD', '포스트 D 설치', 4, '좌측 후단 포스트 설치', TRUE, 600,
 '{"tool":"gripper_post","tcp":{"x":0,"y":0,"z":150},"speed":80,"force":30,"fixture":"jig_post","coordinate_system":"BASE"}',
 '[{"code":"CMP-POST-D","name":"포스트 D","quantity":1,"pickup_position":{"x":650,"y":200,"z":300,"frame":"BASE"},"assembly_position":{"x":1000,"y":4000,"z":50,"frame":"BASE"}},{"code":"CMP-BOLT-M16","name":"앵커 볼트 M16","quantity":4}]'),
(5, 1, 'postE', '포스트 E 설치', 5, '중앙 후단 포스트 설치', TRUE, 600,
 '{"tool":"gripper_post","tcp":{"x":0,"y":0,"z":150},"speed":80,"force":30,"fixture":"jig_post","coordinate_system":"BASE"}',
 '[{"code":"CMP-POST-E","name":"포스트 E","quantity":1,"pickup_position":{"x":800,"y":200,"z":300,"frame":"BASE"},"assembly_position":{"x":3000,"y":4000,"z":50,"frame":"BASE"}},{"code":"CMP-BOLT-M16","name":"앵커 볼트 M16","quantity":4}]'),
(6, 1, 'postF', '포스트 F 설치', 6, '우측 후단 포스트 설치', TRUE, 600,
 '{"tool":"gripper_post","tcp":{"x":0,"y":0,"z":150},"speed":80,"force":30,"fixture":"jig_post","coordinate_system":"BASE"}',
 '[{"code":"CMP-POST-F","name":"포스트 F","quantity":1,"pickup_position":{"x":950,"y":200,"z":300,"frame":"BASE"},"assembly_position":{"x":5000,"y":4000,"z":50,"frame":"BASE"}},{"code":"CMP-BOLT-M16","name":"앵커 볼트 M16","quantity":4}]'),
(7, 1, 'frameA', '프레임 A 조립', 7, '상부 프레임 결합', TRUE, 900,
 '{"tool":"gripper_frame","tcp":{"x":0,"y":0,"z":200},"speed":60,"force":40,"fixture":"jig_frame","coordinate_system":"BASE"}',
 '[{"code":"CMP-FRAME-A","name":"프레임 A","quantity":1,"pickup_position":{"x":1100,"y":200,"z":300,"frame":"BASE"},"assembly_position":{"x":3000,"y":2500,"z":700,"frame":"BASE"}},{"code":"CMP-BRKT-L","name":"브라켓 L형","quantity":8},{"code":"CMP-BOLT-M16","name":"볼트 M16","quantity":32}]'),
(8, 1, 'solarpanelA', '태양광 패널 A 설치', 8, '패널 20장 양중 및 체결', TRUE, 1200,
 '{"tool":"suction_cup","tcp":{"x":0,"y":0,"z":250},"speed":50,"force":20,"fixture":"jig_panel","coordinate_system":"BASE"}',
 '[{"code":"CMP-PANEL-450W","name":"태양광 패널 450W","quantity":20,"pickup_position":{"x":1250,"y":200,"z":300,"frame":"BASE"},"assembly_position":{"x":1500,"y":2500,"z":900,"frame":"BASE"}},{"code":"CMP-BRKT-PV","name":"마운트 브라켓","quantity":40},{"code":"CMP-BOLT-M8","name":"볼트 M8","quantity":160}]');

INSERT INTO robot (robot_id, robot_code, name, manufacturer, model, status, dofs, payload_kg)
VALUES (1, 'RB-01', '조립 로봇 1호', 'Universal Robots', 'UR10e', 'IDLE', 6, 12.5);

INSERT INTO sensor (sensor_id, robot_id, name, type, force_max_n, torque_max_nm, is_active)
VALUES (1, 1, 'F/T 센서 1호', 'FORCE_TORQUE', 500, 50, TRUE);

INSERT INTO work_order (work_order_id, order_number, title, installation_id, priority, status, planned_start_date, planned_end_date, remark, created_by)
VALUES (1, 'WO-20260821-001', '태양광 발전 시설 A 설치 작업', 1, 1, 'COMPLETED', '2026-08-19 08:00:00', '2026-08-21 18:00:00', '옥상 크레인 협조 하에 진행', '관리자');

INSERT INTO work_execution (work_execution_id, work_order_id, robot_id, execution_number, status, start_time, end_time)
VALUES (1, 1, 1, 'EX-20260821-001', 'COMPLETED', '2026-08-21 09:00:00', '2026-08-21 11:35:00');

INSERT INTO operation_execution (operation_execution_id, work_execution_id, operation_id, sequence, status, start_time, end_time, retry_count) VALUES
(1,1,1,1,'SUCCESS','2026-08-21 09:00:00','2026-08-21 09:12:00',0),
(2,1,2,2,'SUCCESS','2026-08-21 09:13:00','2026-08-21 09:25:00',0),
(3,1,3,3,'SUCCESS','2026-08-21 09:26:00','2026-08-21 09:38:00',0),
(4,1,4,4,'SUCCESS','2026-08-21 09:39:00','2026-08-21 09:51:00',0),
(5,1,5,5,'SUCCESS','2026-08-21 09:52:00','2026-08-21 10:04:00',0),
(6,1,6,6,'SUCCESS','2026-08-21 10:05:00','2026-08-21 10:17:00',0),
(7,1,7,7,'SUCCESS','2026-08-21 10:18:00','2026-08-21 10:36:00',0),
(8,1,8,8,'SUCCESS','2026-08-21 10:37:00','2026-08-21 11:35:00',0);

INSERT INTO log (log_id, work_execution_id, operation_execution_id, robot_id, log_type, code, severity, message, detail, timestamp) VALUES
(1,1,NULL,1,'EVENT','WORK_STARTED','INFO','작업 실행 시작',NULL,'2026-08-21 09:00:00'),
(2,1,1,1,'EVENT','OPERATION_COMPLETED','INFO','postA 설치 완료',NULL,'2026-08-21 09:12:00'),
(3,1,7,1,'EVENT','OPERATION_COMPLETED','INFO','frameA 조립 완료',NULL,'2026-08-21 10:36:00'),
(4,1,8,1,'EVENT','TORQUE_WARNING','WARNING','패널 체결 중 토크 상한 근접',NULL,'2026-08-21 10:52:19'),
(5,1,NULL,1,'EVENT','WORK_COMPLETED','INFO','전체 작업 완료',NULL,'2026-08-21 11:35:00'),
(6,1,8,1,'ERROR','ERR-TORQUE-HIGH','ERROR','패널 체결 중 토크 상한 근접 (측정 43.2Nm / 한계 45Nm)',
 '{"error_type":"TORQUE_LIMIT","is_resolved":true,"resolved_at":"2026-08-21T10:55:00","resolved_by":"김현장"}','2026-08-21 10:52:19');

INSERT INTO sensor_data (sensor_data_id, sensor_id, operation_execution_id, data_type, data, timestamp) VALUES
(1,1,8,'FORCE_TORQUE','{"fx":2.1,"fy":-1.3,"fz":35.2,"tx":0.4,"ty":-0.6,"tz":1.2,"magnitude_n":35.29,"magnitude_nm":1.41}','2026-08-21 10:51:58'),
(2,1,8,'FORCE_TORQUE','{"fx":2.0,"fy":-1.1,"fz":39.8,"tx":0.5,"ty":-0.7,"tz":1.6,"magnitude_n":39.87,"magnitude_nm":1.83}','2026-08-21 10:52:05'),
(3,1,8,'FORCE_TORQUE','{"fx":1.8,"fy":-0.9,"fz":42.6,"tx":0.6,"ty":-0.8,"tz":1.9,"magnitude_n":42.65,"magnitude_nm":2.30}','2026-08-21 10:52:12'),
(4,1,8,'FORCE_TORQUE','{"fx":1.9,"fy":-1.0,"fz":43.2,"tx":0.6,"ty":-0.9,"tz":2.1,"magnitude_n":43.25,"magnitude_nm":2.44}','2026-08-21 10:52:19'),
(5,1,8,'FORCE_TORQUE','{"fx":1.5,"fy":-0.8,"fz":41.9,"tx":0.4,"ty":-0.6,"tz":1.5,"magnitude_n":41.94,"magnitude_nm":1.70}','2026-08-21 10:52:26');

SELECT setval(pg_get_serial_sequence('installation','installation_id'), (SELECT MAX(installation_id) FROM installation));
SELECT setval(pg_get_serial_sequence('operation','operation_id'), (SELECT MAX(operation_id) FROM operation));
SELECT setval(pg_get_serial_sequence('robot','robot_id'), (SELECT MAX(robot_id) FROM robot));
SELECT setval(pg_get_serial_sequence('sensor','sensor_id'), (SELECT MAX(sensor_id) FROM sensor));
SELECT setval(pg_get_serial_sequence('work_order','work_order_id'), (SELECT MAX(work_order_id) FROM work_order));
SELECT setval(pg_get_serial_sequence('work_execution','work_execution_id'), (SELECT MAX(work_execution_id) FROM work_execution));
SELECT setval(pg_get_serial_sequence('operation_execution','operation_execution_id'), (SELECT MAX(operation_execution_id) FROM operation_execution));
SELECT setval(pg_get_serial_sequence('log','log_id'), (SELECT MAX(log_id) FROM log));
SELECT setval(pg_get_serial_sequence('sensor_data','sensor_data_id'), (SELECT MAX(sensor_data_id) FROM sensor_data));

COMMIT;
