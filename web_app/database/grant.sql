-- ============================================================
-- grant.sql
-- PostgreSQL 권한 설정
--
-- Role
--   app_user : Flask Backend용 Read/Write 계정
-- ============================================================


-- ------------------------------------------------------------
-- 1. Database 접근 권한
-- ------------------------------------------------------------

GRANT CONNECT
ON DATABASE :"db_name"
TO :"app_user";


-- ------------------------------------------------------------
-- 2. Schema 접근 권한
-- ------------------------------------------------------------

GRANT USAGE, CREATE
ON SCHEMA public
TO :"app_user";


-- ------------------------------------------------------------
-- 3. 기존 Table 권한
-- ------------------------------------------------------------

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA public
TO :"app_user";


-- ------------------------------------------------------------
-- 4. 기존 Sequence 권한
-- ------------------------------------------------------------

GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA public
TO :"app_user";


-- ------------------------------------------------------------
-- 5. 앞으로 생성될 Table 기본 권한
-- ------------------------------------------------------------

ALTER DEFAULT PRIVILEGES
FOR ROLE :"app_user"
IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLES
TO :"app_user";


-- ------------------------------------------------------------
-- 6. 앞으로 생성될 Sequence 기본 권한
-- ------------------------------------------------------------

ALTER DEFAULT PRIVILEGES
FOR ROLE :"app_user"
IN SCHEMA public
GRANT USAGE, SELECT
ON SEQUENCES
TO :"app_user";