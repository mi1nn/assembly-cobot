-- ============================================================
-- 로봇 작업 공정 관리 시스템 - DB DDL (FINAL)
-- 구조: 9개 테이블 / PostgreSQL 16
-- ============================================================

-- A. 생산/작업 기준정보
CREATE TABLE IF NOT EXISTS installation (
    installation_id BIGSERIAL PRIMARY KEY,
    project_code VARCHAR(50) NOT NULL,
    project_name VARCHAR(200) NOT NULL,
    site_name VARCHAR(200) NOT NULL,
    site_address VARCHAR(500),
    contact_person VARCHAR(100),
    target_code VARCHAR(50) NOT NULL UNIQUE,
    target_name VARCHAR(200) NOT NULL,
    specification TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    CONSTRAINT chk_installation_status
    CHECK (status IN (
        'ACTIVE',
        'INACTIVE',
        'MAINTENANCE',
        'ARCHIVED'
    )),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_installation_project_code ON installation(project_code);

CREATE TABLE IF NOT EXISTS operation (
    operation_id BIGSERIAL PRIMARY KEY,
    installation_id BIGINT NOT NULL REFERENCES installation(installation_id),
    code VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    sequence INT NOT NULL,
    description TEXT,
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    estimated_duration_sec INT,
    parameter JSONB,
    components JSONB NOT NULL DEFAULT '[]'::JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (installation_id, code),
    UNIQUE (installation_id, sequence)
);
CREATE INDEX IF NOT EXISTS idx_operation_target_seq ON operation(installation_id, sequence);

-- B. 로봇/센서 기준정보
CREATE TABLE IF NOT EXISTS robot (
    robot_id BIGSERIAL PRIMARY KEY,
    robot_code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    status VARCHAR(30) NOT NULL DEFAULT 'IDLE',
    CONSTRAINT chk_robot_status
    CHECK (status IN (
        'IDLE',
        'RUNNING',
        'ERROR',
        'OFFLINE',
        'MAINTENANCE'
    )),
    dofs INT,
    payload_kg DECIMAL(8,2),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sensor (
    sensor_id BIGSERIAL PRIMARY KEY,
    robot_id BIGINT REFERENCES robot(robot_id),
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL,
    force_max_n DECIMAL(10,2),
    torque_max_nm DECIMAL(10,2),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sensor_robot ON sensor(robot_id);

-- C. 작업
CREATE TABLE IF NOT EXISTS work_order (
    work_order_id BIGSERIAL PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(300) NOT NULL,
    installation_id BIGINT NOT NULL REFERENCES installation(installation_id),
    priority INT NOT NULL DEFAULT 3,
    status VARCHAR(30) NOT NULL DEFAULT 'CREATED',
    CONSTRAINT chk_work_order_status
    CHECK (
        status IN(
            'CREATED',
            'READY',
            'RUNNING',
            'COMPLETED',
            'FAILED',
            'CANCELLED'
    )),
    planned_start_date TIMESTAMP,
    planned_end_date TIMESTAMP,
    remark TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_wo_installation ON work_order(installation_id);
CREATE INDEX IF NOT EXISTS idx_wo_status ON work_order(status);
CREATE INDEX IF NOT EXISTS idx_wo_priority ON work_order(priority);

CREATE TABLE IF NOT EXISTS work_execution (
    work_execution_id BIGSERIAL PRIMARY KEY,
    work_order_id BIGINT NOT NULL REFERENCES work_order(work_order_id),
    robot_id BIGINT NOT NULL REFERENCES robot(robot_id),
    execution_number VARCHAR(50) NOT NULL UNIQUE,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    CONSTRAINT chk_work_execution_status
    CHECK (status IN (
        'PENDING',
        'RUNNING',
        'COMPLETED',
        'FAILED',
        'CANCELLED'
    )),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_we_work_order ON work_execution(work_order_id);
CREATE INDEX IF NOT EXISTS idx_we_robot ON work_execution(robot_id);
CREATE INDEX IF NOT EXISTS idx_we_status ON work_execution(status);

CREATE TABLE IF NOT EXISTS operation_execution (
    operation_execution_id BIGSERIAL PRIMARY KEY,
    work_execution_id BIGINT NOT NULL REFERENCES work_execution(work_execution_id),
    operation_id BIGINT NOT NULL REFERENCES operation(operation_id),
    sequence INT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    CONSTRAINT chk_operation_execution_status
    CHECK (status IN (
        'PENDING',
        'RUNNING',
        'COMPLETED',
        'FAILED',
        'CANCELLED'
    )),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    retry_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_oe_work_exec ON operation_execution(work_execution_id);
CREATE INDEX IF NOT EXISTS idx_oe_operation ON operation_execution(operation_id);
CREATE INDEX IF NOT EXISTS idx_oe_status ON operation_execution(status);

-- D. 로그/측정
CREATE TABLE IF NOT EXISTS log (
    log_id BIGSERIAL PRIMARY KEY,
    work_execution_id BIGINT REFERENCES work_execution(work_execution_id),
    operation_execution_id BIGINT REFERENCES operation_execution(operation_execution_id),
    robot_id BIGINT REFERENCES robot(robot_id),
    log_type VARCHAR(50) NOT NULL
    CONSTRAINT chk_log_type
    CHECK (log_type IN (
        'EVENT',
        'ERROR',
        'SYSTEM',
        'ROBOT'
    )),
    code VARCHAR(50),
    severity VARCHAR(20) NOT NULL DEFAULT 'INFO',
    CONSTRAINT chk_log_severity
    CHECK (severity IN (
        'DEBUG',
        'INFO',
        'WARNING',
        'ERROR',
        'CRITICAL'
    )),
    message TEXT NOT NULL,
    detail JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_log_work_exec ON log(work_execution_id);
CREATE INDEX IF NOT EXISTS idx_log_op_exec ON log(operation_execution_id);
CREATE INDEX IF NOT EXISTS idx_log_robot ON log(robot_id);
CREATE INDEX IF NOT EXISTS idx_log_type ON log(log_type);
CREATE INDEX IF NOT EXISTS idx_log_code ON log(code);
CREATE INDEX IF NOT EXISTS idx_log_timestamp ON log(timestamp);

CREATE TABLE IF NOT EXISTS sensor_data (
    sensor_data_id BIGSERIAL PRIMARY KEY,
    sensor_id BIGINT NOT NULL REFERENCES sensor(sensor_id),
    operation_execution_id BIGINT NOT NULL REFERENCES operation_execution(operation_execution_id),
    data_type VARCHAR(50) NOT NULL,
    data JSONB NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sensor_data_sensor ON sensor_data(sensor_id);
CREATE INDEX IF NOT EXISTS idx_sensor_data_op_exec ON sensor_data(operation_execution_id);
CREATE INDEX IF NOT EXISTS idx_sensor_data_type ON sensor_data(data_type);
CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data(timestamp);

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_installation_updated ON installation;
CREATE TRIGGER trg_installation_updated BEFORE UPDATE ON installation
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS trg_operation_updated ON operation;
CREATE TRIGGER trg_operation_updated BEFORE UPDATE ON operation
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS trg_robot_updated ON robot;
CREATE TRIGGER trg_robot_updated BEFORE UPDATE ON robot
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS trg_sensor_updated ON sensor;
CREATE TRIGGER trg_sensor_updated BEFORE UPDATE ON sensor
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS trg_work_order_updated ON work_order;
CREATE TRIGGER trg_work_order_updated BEFORE UPDATE ON work_order
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS trg_work_execution_updated ON work_execution;
CREATE TRIGGER trg_work_execution_updated BEFORE UPDATE ON work_execution
FOR EACH ROW EXECUTE FUNCTION update_timestamp();
