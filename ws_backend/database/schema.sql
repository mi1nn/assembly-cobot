-- ============================================================
-- 로봇 작업 공정 관리 시스템 - DB DDL (v5)
-- 기반 문서: DB_specs.md (v5)
-- 구조: 13개 테이블
-- 대상 DBMS: PostgreSQL 15+
--
-- setup_db.sh 반복 실행을 고려하여
-- Table / Index / Trigger 중복 생성에 대응
-- ============================================================


-- ============================================================
-- Extension
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ============================================================
-- A. 생산/작업 기준정보
-- ============================================================


-- ------------------------------------------------------------
-- 1. project
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS project (
    project_id      BIGSERIAL PRIMARY KEY,
    code            VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    status          VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);


-- ------------------------------------------------------------
-- 2. site
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS site (
    site_id         BIGSERIAL PRIMARY KEY,
    project_id      BIGINT NOT NULL REFERENCES project(project_id),
    name            VARCHAR(200) NOT NULL,
    address         VARCHAR(500),
    region          VARCHAR(100),
    contact_person  VARCHAR(100),
    contact_phone   VARCHAR(30),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_site_project
ON site(project_id);


-- ------------------------------------------------------------
-- 3. installation_target
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS installation_target (
    installation_target_id  BIGSERIAL PRIMARY KEY,
    site_id                 BIGINT NOT NULL REFERENCES site(site_id),
    target_code             VARCHAR(50) NOT NULL UNIQUE,
    name                    VARCHAR(200) NOT NULL,
    type                    VARCHAR(50),
    specification           TEXT,
    serial_number           VARCHAR(100),
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_installation_target_site
ON installation_target(site_id);


-- ------------------------------------------------------------
-- 4. operation
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS operation (
    operation_id            BIGSERIAL PRIMARY KEY,
    installation_target_id  BIGINT NOT NULL
                            REFERENCES installation_target(installation_target_id),
    code                    VARCHAR(50),
    name                    VARCHAR(200) NOT NULL,
    sequence                INT NOT NULL,
    description             TEXT,
    is_required             BOOLEAN NOT NULL DEFAULT TRUE,
    estimated_duration_sec  INT,
    parameter               JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (installation_target_id, code)
);

CREATE INDEX IF NOT EXISTS idx_operation_target_seq
ON operation(installation_target_id, sequence);


-- ------------------------------------------------------------
-- 5. component
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS component (
    component_id        BIGSERIAL PRIMARY KEY,
    operation_id        BIGINT NOT NULL REFERENCES operation(operation_id),
    code                VARCHAR(50),
    name                VARCHAR(200) NOT NULL,
    category            VARCHAR(100),
    specification       TEXT,
    quantity            INT NOT NULL,
    current_position    JSONB,
    assembly_position   JSONB,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (operation_id, code)
);

CREATE INDEX IF NOT EXISTS idx_component_operation
ON component(operation_id);


-- ============================================================
-- B. 로봇/센서 기준정보
-- ============================================================


-- ------------------------------------------------------------
-- 6. robot
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS robot (
    robot_id        BIGSERIAL PRIMARY KEY,
    robot_code      VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(200) NOT NULL,
    manufacturer    VARCHAR(100),
    model           VARCHAR(100),
    serial_number   VARCHAR(100),
    status          VARCHAR(30) NOT NULL DEFAULT 'IDLE',
    dofs            INT,
    payload_kg      DECIMAL(8,2),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);


-- ------------------------------------------------------------
-- 7. sensor
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS sensor (
    sensor_id       BIGSERIAL PRIMARY KEY,
    robot_id        BIGINT REFERENCES robot(robot_id),
    sensor_code     VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(200) NOT NULL,
    type            VARCHAR(50) NOT NULL,
    manufacturer    VARCHAR(100),
    model           VARCHAR(100),
    serial_number   VARCHAR(100),
    force_max_n     DECIMAL(10,2),
    torque_max_nm   DECIMAL(10,2),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sensor_robot
ON sensor(robot_id);


-- ============================================================
-- C. 작업
-- ============================================================


-- ------------------------------------------------------------
-- 8. work_order
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS work_order (
    work_order_id           BIGSERIAL PRIMARY KEY,
    order_number            VARCHAR(50) NOT NULL UNIQUE,
    title                   VARCHAR(300) NOT NULL,
    installation_target_id  BIGINT NOT NULL
                            REFERENCES installation_target(installation_target_id),
    priority                INT NOT NULL DEFAULT 3,
    status                  VARCHAR(30) NOT NULL DEFAULT 'CREATED',
    planned_start_date      TIMESTAMP,
    planned_end_date        TIMESTAMP,
    remark                  TEXT,
    created_by              VARCHAR(100),
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wo_inst_target
ON work_order(installation_target_id);

CREATE INDEX IF NOT EXISTS idx_wo_status
ON work_order(status);

CREATE INDEX IF NOT EXISTS idx_wo_priority
ON work_order(priority);


-- ------------------------------------------------------------
-- 9. work_execution
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS work_execution (
    work_execution_id   BIGSERIAL PRIMARY KEY,
    work_order_id       BIGINT NOT NULL REFERENCES work_order(work_order_id),
    robot_id            BIGINT NOT NULL REFERENCES robot(robot_id),
    execution_number    VARCHAR(50) NOT NULL UNIQUE,
    status              VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    start_time          TIMESTAMP,
    end_time            TIMESTAMP,
    retry_count         INT NOT NULL DEFAULT 0,
    result_summary      TEXT,
    remark              TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_we_work_order
ON work_execution(work_order_id);

CREATE INDEX IF NOT EXISTS idx_we_robot
ON work_execution(robot_id);

CREATE INDEX IF NOT EXISTS idx_we_status
ON work_execution(status);


-- ------------------------------------------------------------
-- 10. operation_execution
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS operation_execution (
    operation_execution_id  BIGSERIAL PRIMARY KEY,
    work_execution_id       BIGINT NOT NULL
                            REFERENCES work_execution(work_execution_id),
    operation_id            BIGINT NOT NULL
                            REFERENCES operation(operation_id),
    sequence                INT NOT NULL,
    status                  VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    start_time              TIMESTAMP,
    end_time                TIMESTAMP,
    error_message           TEXT,
    retry_count             INT NOT NULL DEFAULT 0,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_oe_work_exec
ON operation_execution(work_execution_id);

CREATE INDEX IF NOT EXISTS idx_oe_operation
ON operation_execution(operation_id);

CREATE INDEX IF NOT EXISTS idx_oe_status
ON operation_execution(status);


-- ============================================================
-- D. 로그/측정
-- ============================================================


-- ------------------------------------------------------------
-- 11. work_event
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS work_event (
    work_event_id           BIGSERIAL PRIMARY KEY,
    work_execution_id       BIGINT NOT NULL
                            REFERENCES work_execution(work_execution_id),
    operation_execution_id  BIGINT
                            REFERENCES operation_execution(operation_execution_id),
    event_type              VARCHAR(50) NOT NULL,
    event_message           TEXT NOT NULL,
    severity                VARCHAR(20) NOT NULL DEFAULT 'INFO',
    timestamp               TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wevt_work_exec
ON work_event(work_execution_id);

CREATE INDEX IF NOT EXISTS idx_wevt_op_exec
ON work_event(operation_execution_id);

CREATE INDEX IF NOT EXISTS idx_wevt_type
ON work_event(event_type);

CREATE INDEX IF NOT EXISTS idx_wevt_timestamp
ON work_event(timestamp);


-- ------------------------------------------------------------
-- 12. error_log
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS error_log (
    error_log_id            BIGSERIAL PRIMARY KEY,
    work_execution_id       BIGINT
                            REFERENCES work_execution(work_execution_id),
    operation_execution_id  BIGINT
                            REFERENCES operation_execution(operation_execution_id),
    robot_id                BIGINT REFERENCES robot(robot_id),
    error_code              VARCHAR(50) NOT NULL,
    error_type              VARCHAR(50) NOT NULL,
    error_message           TEXT NOT NULL,
    severity                VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    is_resolved             BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at             TIMESTAMP,
    resolved_by             VARCHAR(100),
    timestamp               TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_err_work_exec
ON error_log(work_execution_id);

CREATE INDEX IF NOT EXISTS idx_err_op_exec
ON error_log(operation_execution_id);

CREATE INDEX IF NOT EXISTS idx_err_robot
ON error_log(robot_id);

CREATE INDEX IF NOT EXISTS idx_err_code
ON error_log(error_code);

CREATE INDEX IF NOT EXISTS idx_err_severity
ON error_log(severity);

CREATE INDEX IF NOT EXISTS idx_err_timestamp
ON error_log(timestamp);


-- ------------------------------------------------------------
-- 13. force_torque_data
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS force_torque_data (
    force_torque_data_id    BIGSERIAL PRIMARY KEY,
    sensor_id               BIGINT NOT NULL
                            REFERENCES sensor(sensor_id),
    operation_execution_id  BIGINT NOT NULL
                            REFERENCES operation_execution(operation_execution_id),
    fx                      DECIMAL(12,6) NOT NULL,
    fy                      DECIMAL(12,6) NOT NULL,
    fz                      DECIMAL(12,6) NOT NULL,
    tx                      DECIMAL(12,6) NOT NULL,
    ty                      DECIMAL(12,6) NOT NULL,
    tz                      DECIMAL(12,6) NOT NULL,
    magnitude_n             DECIMAL(12,6),
    magnitude_nm            DECIMAL(12,6),
    timestamp               TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ftd_sensor
ON force_torque_data(sensor_id);

CREATE INDEX IF NOT EXISTS idx_ftd_op_exec
ON force_torque_data(operation_execution_id);

CREATE INDEX IF NOT EXISTS idx_ftd_timestamp
ON force_torque_data(timestamp);


-- ============================================================
-- Trigger Function
-- updated_at 자동 갱신
-- ============================================================

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- Triggers
--
-- PostgreSQL CREATE TRIGGER에는 일반적인
-- IF NOT EXISTS 문법이 없으므로
-- 기존 Trigger 삭제 후 재생성한다.
-- ============================================================


-- project
DROP TRIGGER IF EXISTS trg_project_updated
ON project;

CREATE TRIGGER trg_project_updated
BEFORE UPDATE ON project
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();


-- site
DROP TRIGGER IF EXISTS trg_site_updated
ON site;

CREATE TRIGGER trg_site_updated
BEFORE UPDATE ON site
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();


-- installation_target
DROP TRIGGER IF EXISTS trg_inst_target_updated
ON installation_target;

CREATE TRIGGER trg_inst_target_updated
BEFORE UPDATE ON installation_target
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();


-- operation
DROP TRIGGER IF EXISTS trg_operation_updated
ON operation;

CREATE TRIGGER trg_operation_updated
BEFORE UPDATE ON operation
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();


-- component
DROP TRIGGER IF EXISTS trg_component_updated
ON component;

CREATE TRIGGER trg_component_updated
BEFORE UPDATE ON component
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();


-- robot
DROP TRIGGER IF EXISTS trg_robot_updated
ON robot;

CREATE TRIGGER trg_robot_updated
BEFORE UPDATE ON robot
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();


-- sensor
DROP TRIGGER IF EXISTS trg_sensor_updated
ON sensor;

CREATE TRIGGER trg_sensor_updated
BEFORE UPDATE ON sensor
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();


-- work_order
DROP TRIGGER IF EXISTS trg_work_order_updated
ON work_order;

CREATE TRIGGER trg_work_order_updated
BEFORE UPDATE ON work_order
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();


-- work_execution
DROP TRIGGER IF EXISTS trg_work_execution_updated
ON work_execution;

CREATE TRIGGER trg_work_execution_updated
BEFORE UPDATE ON work_execution
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();


-- ============================================================
-- 완료
-- 13 Tables
-- ============================================================