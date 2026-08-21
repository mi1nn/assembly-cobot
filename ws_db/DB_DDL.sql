-- ============================================================
-- 로봇 작업 공정 관리 시스템 - DB DDL (v4)
-- 기반 문서: DB 요구사항_봉승현.md
-- 구조: 16개 테이블
-- 대상 DBMS: PostgreSQL 15+
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- A. 기준정보
-- ============================================================

-- 1. project
CREATE TABLE project (
    project_id      BIGSERIAL PRIMARY KEY,
    code            VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    status          VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 2. site
CREATE TABLE site (
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

CREATE INDEX idx_site_project ON site(project_id);

-- 3. product
CREATE TABLE product (
    product_id      BIGSERIAL PRIMARY KEY,
    code            VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    category        VARCHAR(100),
    specification   JSONB,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 4. installation_target
CREATE TABLE installation_target (
    installation_target_id  BIGSERIAL PRIMARY KEY,
    site_id                 BIGINT NOT NULL REFERENCES site(site_id),
    product_id              BIGINT NOT NULL REFERENCES product(product_id),
    target_code             VARCHAR(50) NOT NULL UNIQUE,
    name                    VARCHAR(200) NOT NULL,
    type                    VARCHAR(50),
    specification           TEXT,
    serial_number           VARCHAR(100),
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_inst_target_site    ON installation_target(site_id);
CREATE INDEX idx_inst_target_product ON installation_target(product_id);

-- 5. recipe
CREATE TABLE recipe (
    recipe_id       BIGSERIAL PRIMARY KEY,
    product_id      BIGINT NOT NULL REFERENCES product(product_id),
    code            VARCHAR(50) NOT NULL,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_by      VARCHAR(100),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(product_id, code)
);

CREATE INDEX idx_recipe_product ON recipe(product_id);
CREATE INDEX idx_recipe_active  ON recipe(is_active);

-- 6. operation
CREATE TABLE operation (
    operation_id            BIGSERIAL PRIMARY KEY,
    recipe_id               BIGINT NOT NULL REFERENCES recipe(recipe_id),
    code                    VARCHAR(50),
    name                    VARCHAR(200) NOT NULL,
    sequence                INT NOT NULL,
    description             TEXT,
    is_required             BOOLEAN NOT NULL DEFAULT TRUE,
    estimated_duration_sec  INT,
    parameter               JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_operation_recipe_seq ON operation(recipe_id, sequence);

-- 7. component
CREATE TABLE component (
    component_id    BIGSERIAL PRIMARY KEY,
    code            VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(200) NOT NULL,
    category        VARCHAR(100),
    specification   TEXT,
    unit            VARCHAR(30) NOT NULL DEFAULT 'ea',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 8. recipe_component
CREATE TABLE recipe_component (
    recipe_component_id BIGSERIAL PRIMARY KEY,
    recipe_id           BIGINT NOT NULL REFERENCES recipe(recipe_id),
    component_id        BIGINT NOT NULL REFERENCES component(component_id),
    quantity            INT NOT NULL,
    remark              TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(recipe_id, component_id)
);

CREATE INDEX idx_rc_recipe    ON recipe_component(recipe_id);
CREATE INDEX idx_rc_component ON recipe_component(component_id);

-- ============================================================
-- B. 로봇/센서
-- ============================================================

-- 9. robot
CREATE TABLE robot (
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

-- 10. sensor
CREATE TABLE sensor (
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

CREATE INDEX idx_sensor_robot ON sensor(robot_id);

-- ============================================================
-- C. 작업
-- ============================================================

-- 11. work_order
CREATE TABLE work_order (
    work_order_id           BIGSERIAL PRIMARY KEY,
    order_number            VARCHAR(50) NOT NULL UNIQUE,
    title                   VARCHAR(300) NOT NULL,
    installation_target_id  BIGINT NOT NULL REFERENCES installation_target(installation_target_id),
    recipe_id               BIGINT NOT NULL REFERENCES recipe(recipe_id),
    priority                INT NOT NULL DEFAULT 3,
    status                  VARCHAR(30) NOT NULL DEFAULT 'CREATED',
    planned_start_date      TIMESTAMP,
    planned_end_date        TIMESTAMP,
    remark                  TEXT,
    created_by              VARCHAR(100),
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wo_inst_target ON work_order(installation_target_id);
CREATE INDEX idx_wo_recipe      ON work_order(recipe_id);
CREATE INDEX idx_wo_status      ON work_order(status);
CREATE INDEX idx_wo_priority    ON work_order(priority);

-- 12. work_execution
CREATE TABLE work_execution (
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

CREATE INDEX idx_we_work_order ON work_execution(work_order_id);
CREATE INDEX idx_we_robot      ON work_execution(robot_id);
CREATE INDEX idx_we_status     ON work_execution(status);

-- 13. operation_execution
CREATE TABLE operation_execution (
    operation_execution_id  BIGSERIAL PRIMARY KEY,
    work_execution_id       BIGINT NOT NULL REFERENCES work_execution(work_execution_id),
    operation_id            BIGINT NOT NULL REFERENCES operation(operation_id),
    sequence                INT NOT NULL,
    status                  VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    start_time              TIMESTAMP,
    end_time                TIMESTAMP,
    result                  VARCHAR(30),
    error_message           TEXT,
    retry_count             INT NOT NULL DEFAULT 0,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_oe_work_exec ON operation_execution(work_execution_id);
CREATE INDEX idx_oe_operation ON operation_execution(operation_id);
CREATE INDEX idx_oe_status    ON operation_execution(status);
CREATE INDEX idx_oe_result    ON operation_execution(result);

-- ============================================================
-- D. 로그/측정
-- ============================================================

-- 14. work_event
CREATE TABLE work_event (
    work_event_id           BIGSERIAL PRIMARY KEY,
    work_execution_id       BIGINT NOT NULL REFERENCES work_execution(work_execution_id),
    operation_execution_id  BIGINT REFERENCES operation_execution(operation_execution_id),
    event_type              VARCHAR(50) NOT NULL,
    event_message           TEXT NOT NULL,
    severity                VARCHAR(20) NOT NULL DEFAULT 'INFO',
    timestamp               TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wevt_work_exec ON work_event(work_execution_id);
CREATE INDEX idx_wevt_op_exec   ON work_event(operation_execution_id);
CREATE INDEX idx_wevt_type      ON work_event(event_type);
CREATE INDEX idx_wevt_timestamp ON work_event(timestamp);

-- 15. error_log
CREATE TABLE error_log (
    error_log_id            BIGSERIAL PRIMARY KEY,
    work_execution_id       BIGINT REFERENCES work_execution(work_execution_id),
    operation_execution_id  BIGINT REFERENCES operation_execution(operation_execution_id),
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

CREATE INDEX idx_err_work_exec ON error_log(work_execution_id);
CREATE INDEX idx_err_op_exec   ON error_log(operation_execution_id);
CREATE INDEX idx_err_robot     ON error_log(robot_id);
CREATE INDEX idx_err_code      ON error_log(error_code);
CREATE INDEX idx_err_severity  ON error_log(severity);
CREATE INDEX idx_err_timestamp ON error_log(timestamp);

-- 16. force_torque_data
CREATE TABLE force_torque_data (
    force_torque_data_id    BIGSERIAL PRIMARY KEY,
    sensor_id               BIGINT NOT NULL REFERENCES sensor(sensor_id),
    operation_execution_id  BIGINT NOT NULL REFERENCES operation_execution(operation_execution_id),
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

CREATE INDEX idx_ftd_sensor    ON force_torque_data(sensor_id);
CREATE INDEX idx_ftd_op_exec   ON force_torque_data(operation_execution_id);
CREATE INDEX idx_ftd_timestamp ON force_torque_data(timestamp);

-- ============================================================
-- 트리거 함수 (updated_at 자동 갱신)
-- ============================================================

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_project_updated          BEFORE UPDATE ON project          FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER trg_site_updated             BEFORE UPDATE ON site             FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER trg_inst_target_updated      BEFORE UPDATE ON installation_target FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER trg_product_updated          BEFORE UPDATE ON product          FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER trg_recipe_updated           BEFORE UPDATE ON recipe           FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER trg_operation_updated        BEFORE UPDATE ON operation        FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER trg_component_updated        BEFORE UPDATE ON component        FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER trg_robot_updated            BEFORE UPDATE ON robot            FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER trg_sensor_updated           BEFORE UPDATE ON sensor           FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER trg_work_order_updated       BEFORE UPDATE ON work_order       FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER trg_work_execution_updated   BEFORE UPDATE ON work_execution   FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ============================================================
-- 완료 (16개 테이블)
-- ============================================================
