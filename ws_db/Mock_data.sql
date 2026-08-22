-- ============================================================
-- Mock Data (v1)
-- 기반 문서: Mock_data.md, DB_DDL.sql (v5)
-- 시나리오: 대륭 포스트타워 8차 태양광 발전 시설 A 설치 작업
-- 대상 DBMS: PostgreSQL 15+
-- ============================================================

-- 재실행 시 아래 주석 해제
-- TRUNCATE force_torque_data, work_event, error_log,
--          operation_execution, work_execution, work_order,
--          component, operation, sensor, robot,
--          installation_target, site, project
-- RESTART IDENTITY CASCADE;

BEGIN;

-- ============================================================
-- A. 생산/작업 기준정보
-- ============================================================

-- 1. project
INSERT INTO project (project_id, code, name, description, status) VALUES
(1, 'PRJ-DLPT8', '대륭 포스트타워 8차 태양광 발전 시설 도입',
 '대륭 포스트타워 8차 옥상 태양광 발전 시설 로봇 설치 프로젝트', 'ACTIVE');

-- 2. site
INSERT INTO site (site_id, project_id, name, address, region, contact_person, contact_phone) VALUES
(1, 1, '대륭 포스트타워 8차 옥상',
 '서울특별시 중구 을지로 100 대륭포스트타워8차', '서울', '김태양', '010-1234-5678');

-- 3. installation_target
INSERT INTO installation_target (installation_target_id, site_id, target_code, name, type, specification, serial_number) VALUES
(1, 1, 'IT-SOLAR-A', '태양광 발전 시설 A', '태양광 발전 설비',
 '옥상형 태양광 발전 시설 (포스트 6 + 프레임 1 + 패널 20)', 'SN-SOLAR-A-001');

-- 4. operation (postA~postF, frameA, solarpanelA)
INSERT INTO operation (operation_id, installation_target_id, code, name, sequence, description, is_required, estimated_duration_sec, parameter) VALUES
(1, 1, 'postA', '포스트 A 설치', 1, '좌측 전단 포스트 설치', TRUE, 600,
 '{"tool": "gripper_post", "tcp": {"x": 0, "y": 0, "z": 150}, "position": "post_a_pick", "speed": 80, "force": 30, "fixture": "jig_post", "coordinate_system": "BASE"}'),
(2, 1, 'postB', '포스트 B 설치', 2, '중앙 전단 포스트 설치', TRUE, 600,
 '{"tool": "gripper_post", "tcp": {"x": 0, "y": 0, "z": 150}, "position": "post_b_pick", "speed": 80, "force": 30, "fixture": "jig_post", "coordinate_system": "BASE"}'),
(3, 1, 'postC', '포스트 C 설치', 3, '우측 전단 포스트 설치', TRUE, 600,
 '{"tool": "gripper_post", "tcp": {"x": 0, "y": 0, "z": 150}, "position": "post_c_pick", "speed": 80, "force": 30, "fixture": "jig_post", "coordinate_system": "BASE"}'),
(4, 1, 'postD', '포스트 D 설치', 4, '좌측 후단 포스트 설치', TRUE, 600,
 '{"tool": "gripper_post", "tcp": {"x": 0, "y": 0, "z": 150}, "position": "post_d_pick", "speed": 80, "force": 30, "fixture": "jig_post", "coordinate_system": "BASE"}'),
(5, 1, 'postE', '포스트 E 설치', 5, '중앙 후단 포스트 설치', TRUE, 600,
 '{"tool": "gripper_post", "tcp": {"x": 0, "y": 0, "z": 150}, "position": "post_e_pick", "speed": 80, "force": 30, "fixture": "jig_post", "coordinate_system": "BASE"}'),
(6, 1, 'postF', '포스트 F 설치', 6, '우측 후단 포스트 설치', TRUE, 600,
 '{"tool": "gripper_post", "tcp": {"x": 0, "y": 0, "z": 150}, "position": "post_f_pick", "speed": 80, "force": 30, "fixture": "jig_post", "coordinate_system": "BASE"}'),
(7, 1, 'frameA', '프레임 A 조립', 7, '상부 프레임 결합', TRUE, 900,
 '{"tool": "gripper_frame", "tcp": {"x": 0, "y": 0, "z": 200}, "position": "frame_a_pick", "speed": 60, "force": 40, "fixture": "jig_frame", "coordinate_system": "BASE"}'),
(8, 1, 'solarpanelA', '태양광 패널 A 설치', 8, '패널 20장 양중 및 체결', TRUE, 1200,
 '{"tool": "suction_cup", "tcp": {"x": 0, "y": 0, "z": 250}, "position": "panel_pick", "speed": 50, "force": 20, "fixture": "jig_panel", "coordinate_system": "BASE"}');

-- 5. component (18건)
-- 포스트 본체: current_position = 자재 보관 위치, assembly_position = 조립 위치
INSERT INTO component (component_id, operation_id, code, name, category, specification, quantity, current_position, assembly_position) VALUES
(1, 1, 'CMP-POST-A', '포스트 A', '구조재', 'H-beam 200x100, L=2500', 1,
 '{"x": 200.0, "y": 200.0, "z": 300.0, "orientation": {"rx": 0.0, "ry": 0.0, "rz": 90.0}, "frame": "BASE"}',
 '{"x": 1000.0, "y": 1000.0, "z": 50.0, "orientation": {"rx": 0.0, "ry": 0.0, "rz": 0.0}, "frame": "BASE"}'),
(2, 1, 'CMP-BOLT-M16', '앵커 볼트 M16', '체결부품', 'M16x120, HV 볼트', 4, NULL, NULL),
(3, 2, 'CMP-POST-B', '포스트 B', '구조재', 'H-beam 200x100, L=2500', 1,
 '{"x": 350.0, "y": 200.0, "z": 300.0, "orientation": {"rx": 0.0, "ry": 0.0, "rz": 90.0}, "frame": "BASE"}',
 '{"x": 3000.0, "y": 1000.0, "z": 50.0, "orientation": {"rx": 0.0, "ry": 0.0, "rz": 0.0}, "frame": "BASE"}'),
(4, 2, 'CMP-BOLT-M16', '앵커 볼트 M16', '체결부품', 'M16x120, HV 볼트', 4, NULL, NULL),
(5, 3, 'CMP-POST-C', '포스트 C', '구조재', 'H-beam 200x100, L=2500', 1,
 '{"x": 500.0, "y": 200.0, "z": 300.0, "orientation": {"rx": 0.0, "ry": 0.0, "rz": 90.0}, "frame": "BASE"}',
 '{"x": 5000.0, "y": 1000.0, "z": 50.0, "orientation": {"rx": 0.0, "ry": 0.0, "rz": 0.0}, "frame": "BASE"}'),
(6, 3, 'CMP-BOLT-M16', '앵커 볼트 M16', '체결부품', 'M16x120, HV 볼트', 4, NULL, NULL),
(7, 4, 'CMP-POST-D', '포스트 D', '구조재', 'H-beam 200x100, L=2500', 1,
 '{"x": 650.0, "y": 200.0, "z": 300.0, "orientation": {"rx": 0.0, "ry": 0.0, "rz": 90.0}, "frame": "BASE"}',
 '{"x": 1000.0, "y": 4000.0, "z": 50.0, "orientation": {"rx": 0.0, "ry": 0.0, "rz": 0.0}, "frame": "BASE"}'),
(8, 4, 'CMP-BOLT-M16', '앵커 볼트 M16', '체결부품', 'M16x120, HV 볼트', 4, NULL, NULL),
(9, 5, 'CMP-POST-E', '포스트 E', '구조재', 'H-beam 200x100, L=2500', 1,
 '{"x": 800.0, "y": 200.0, "z": 300.0, "orientation": {"rx": 0.0, "ry": 0.0, "rz": 90.0}, "frame": "BASE"}',
 '{"x": 3000.0, "y": 4000.0, "z": 50.0, "orientation": {"rx": 0.0, "ry": 0.0, "rz": 0.0}, "frame": "BASE"}'),
(10, 5, 'CMP-BOLT-M16', '앵커 볼트 M16', '체결부품', 'M16x120, HV 볼트', 4, NULL, NULL),
(11, 6, 'CMP-POST-F', '포스트 F', '구조재', 'H-beam 200x100, L=2500', 1,
 '{"x": 950.0, "y": 200.0, "z": 300.0, "orientation": {"rx": 0.0, "ry": 0.0, "rz": 90.0}, "frame": "BASE"}',
 '{"x": 5000.0, "y": 4000.0, "z": 50.0, "orientation": {"rx": 0.0, "ry": 0.0, "rz": 0.0}, "frame": "BASE"}'),
(12, 6, 'CMP-BOLT-M16', '앵커 볼트 M16', '체결부품', 'M16x120, HV 볼트', 4, NULL, NULL),
(13, 7, 'CMP-FRAME-A', '프레임 A', '구조재', 'C-channel 250x80, L=5200', 1,
 '{"x": 1100.0, "y": 200.0, "z": 300.0, "orientation": {"rx": 0.0, "ry": 0.0, "rz": 0.0}, "frame": "BASE"}',
 '{"x": 3000.0, "y": 2500.0, "z": 700.0, "orientation": {"rx": 0.0, "ry": 0.0, "rz": 0.0}, "frame": "BASE"}'),
(14, 7, 'CMP-BRKT-L', '브라켓 L형', '체결부품', 'L-125x125x12, t=12', 8, NULL, NULL),
(15, 7, 'CMP-BOLT-M16', '볼트 M16', '체결부품', 'M16x60, HV 볼트', 32, NULL, NULL),
(16, 8, 'CMP-PANEL-450W', '태양광 패널 450W', '발전모듈', '단결정 450W, 2108x1048x35', 20,
 '{"x": 1250.0, "y": 200.0, "z": 300.0, "orientation": {"rx": 0.0, "ry": 0.0, "rz": 0.0}, "frame": "BASE"}',
 '{"x": 1500.0, "y": 2500.0, "z": 900.0, "orientation": {"rx": 0.0, "ry": 30.0, "rz": 0.0}, "frame": "BASE"}'),
(17, 8, 'CMP-BRKT-PV', '마운트 브라켓', '체결부품', 'AL 중간 브라켓', 40, NULL, NULL),
(18, 8, 'CMP-BOLT-M8', '볼트 M8', '체결부품', 'M8x25, SS400', 160, NULL, NULL);

-- ============================================================
-- B. 로봇/센서 기준정보
-- ============================================================

-- 6. robot
INSERT INTO robot (robot_id, robot_code, name, manufacturer, model, serial_number, status, dofs, payload_kg) VALUES
(1, 'RB-01', '조립 로봇 1호', 'Universal Robots', 'UR10e', 'UR10E-2026-001', 'IDLE', 6, 12.5);

-- 7. sensor
INSERT INTO sensor (sensor_id, robot_id, sensor_code, name, type, manufacturer, model, serial_number, force_max_n, torque_max_nm, is_active) VALUES
(1, 1, 'SNS-FT-01', 'F/T 센서 1호', 'FORCE_TORQUE', 'ATI', 'AXIA80', 'AXIA-001', 500.00, 50.00, TRUE);

-- ============================================================
-- C. 작업
-- ============================================================

-- 8. work_order
INSERT INTO work_order (work_order_id, order_number, title, installation_target_id, priority, status, planned_start_date, planned_end_date, remark, created_by) VALUES
(1, 'WO-20260821-001', '태양광 발전 시설 A 설치 작업', 1, 1, 'COMPLETED',
 '2026-08-19 08:00:00', '2026-08-21 18:00:00', '옥상 크레인 협조 하에 진행', '관리자');

-- 9. work_execution
INSERT INTO work_execution (work_execution_id, work_order_id, robot_id, execution_number, status, start_time, end_time, retry_count, result_summary, remark) VALUES
(1, 1, 1, 'EX-20260821-001', 'COMPLETED',
 '2026-08-21 09:00:00', '2026-08-21 11:35:00', 0,
 '8개 Operation 전체 성공', '체결 구간 토크 경고 1회 있었으나 정상 완료');

-- 10. operation_execution (8건)
INSERT INTO operation_execution (operation_execution_id, work_execution_id, operation_id, sequence, status, start_time, end_time, error_message, retry_count) VALUES
(1, 1, 1, 1, 'SUCCESS', '2026-08-21 09:00:00', '2026-08-21 09:12:00', NULL, 0),
(2, 1, 2, 2, 'SUCCESS', '2026-08-21 09:13:00', '2026-08-21 09:25:00', NULL, 0),
(3, 1, 3, 3, 'SUCCESS', '2026-08-21 09:26:00', '2026-08-21 09:38:00', NULL, 0),
(4, 1, 4, 4, 'SUCCESS', '2026-08-21 09:39:00', '2026-08-21 09:51:00', NULL, 0),
(5, 1, 5, 5, 'SUCCESS', '2026-08-21 09:52:00', '2026-08-21 10:04:00', NULL, 0),
(6, 1, 6, 6, 'SUCCESS', '2026-08-21 10:05:00', '2026-08-21 10:17:00', NULL, 0),
(7, 1, 7, 7, 'SUCCESS', '2026-08-21 10:18:00', '2026-08-21 10:36:00', NULL, 0),
(8, 1, 8, 8, 'SUCCESS', '2026-08-21 10:37:00', '2026-08-21 11:35:00', NULL, 0);

-- ============================================================
-- D. 로그/측정
-- ============================================================

-- 11. work_event (5건)
INSERT INTO work_event (work_event_id, work_execution_id, operation_execution_id, event_type, event_message, severity, timestamp) VALUES
(1, 1, NULL, 'WORK_STARTED', '작업 실행 시작', 'INFO', '2026-08-21 09:00:00'),
(2, 1, 1, 'OPERATION_COMPLETED', 'postA 설치 완료', 'INFO', '2026-08-21 09:12:00'),
(3, 1, 7, 'OPERATION_COMPLETED', 'frameA 조립 완료', 'INFO', '2026-08-21 10:36:00'),
(4, 1, 8, 'TORQUE_WARNING', '패널 체결 중 토크 상한 근접', 'WARNING', '2026-08-21 10:52:19'),
(5, 1, NULL, 'WORK_COMPLETED', '전체 작업 완료', 'INFO', '2026-08-21 11:35:00');

-- 12. error_log (1건)
INSERT INTO error_log (error_log_id, work_execution_id, operation_execution_id, robot_id, error_code, error_type, error_message, severity, is_resolved, resolved_at, resolved_by, timestamp) VALUES
(1, 1, 8, 1, 'ERR-TORQUE-HIGH', 'TORQUE_LIMIT',
 '패널 체결 중 토크 상한 근접 (측정 43.2Nm / 한계 45Nm)', 'HIGH',
 TRUE, '2026-08-21 10:55:00', '김현장', '2026-08-21 10:52:19');

-- 13. force_torque_data (5건, oe 8 체결 구간 샘플)
INSERT INTO force_torque_data (force_torque_data_id, sensor_id, operation_execution_id, fx, fy, fz, tx, ty, tz, magnitude_n, magnitude_nm, timestamp) VALUES
(1, 1, 8, 2.1, -1.3, 35.2, 0.4, -0.6, 1.2, 35.29, 1.41, '2026-08-21 10:51:58'),
(2, 1, 8, 2.0, -1.1, 39.8, 0.5, -0.7, 1.6, 39.87, 1.83, '2026-08-21 10:52:05'),
(3, 1, 8, 1.8, -0.9, 42.6, 0.6, -0.8, 1.9, 42.65, 2.30, '2026-08-21 10:52:12'),
(4, 1, 8, 1.9, -1.0, 43.2, 0.6, -0.9, 2.1, 43.25, 2.44, '2026-08-21 10:52:19'),
(5, 1, 8, 1.5, -0.8, 41.9, 0.4, -0.6, 1.5, 41.94, 1.70, '2026-08-21 10:52:26');

COMMIT;
