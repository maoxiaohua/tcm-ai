-- ================================================================
-- 迁移脚本: 为doctors表添加uuid字段
-- Migration: Add UUID field to doctors table
--
-- 目的: 统一用户ID格式，支持与unified_users系统集成
-- Version: 1.0
-- Date: 2025-10-12
-- ================================================================

BEGIN TRANSACTION;

-- 1. 为doctors表添加uuid字段
ALTER TABLE doctors ADD COLUMN uuid VARCHAR(50) UNIQUE;

-- 2. 为现有医生生成uuid
-- 格式: D + 8位数字ID (例如: D00000001, D00000002...)
UPDATE doctors
SET uuid = 'D' || printf('%08d', id)
WHERE uuid IS NULL;

-- 3. 创建索引以优化uuid查询
CREATE INDEX IF NOT EXISTS idx_doctors_uuid ON doctors(uuid);

-- 4. 验证数据完整性
-- 检查是否所有医生都有uuid
SELECT CASE
    WHEN COUNT(*) = 0 THEN '✅ 所有医生都已分配UUID'
    ELSE '❌ 发现 ' || COUNT(*) || ' 个医生未分配UUID'
END AS validation_result
FROM doctors
WHERE uuid IS NULL;

-- 5. 输出医生UUID映射表（用于验证）
SELECT
    id AS doctor_id,
    uuid AS doctor_uuid,
    name AS doctor_name,
    email
FROM doctors
ORDER BY id;

COMMIT;

-- ================================================================
-- 回滚脚本 (如果需要)
-- ================================================================
-- BEGIN TRANSACTION;
-- ALTER TABLE doctors DROP COLUMN uuid;
-- DROP INDEX IF EXISTS idx_doctors_uuid;
-- COMMIT;
