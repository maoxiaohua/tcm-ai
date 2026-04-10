-- 021_add_prescriptions_consultation_unique_index.sql
-- 目标：保证每个 consultation_id 最多只对应一条 prescriptions 记录（忽略空值）
-- 注意：执行前请先完成离线清理和去重，否则可能因历史重复数据导致失败。

BEGIN TRANSACTION;

-- 可选：如果已存在普通索引，可删除以减少重复维护成本
DROP INDEX IF EXISTS idx_prescriptions_consultation;

-- 非空 consultation_id 唯一约束（SQLite 通过唯一索引实现）
CREATE UNIQUE INDEX IF NOT EXISTS ux_prescriptions_consultation_id
ON prescriptions(consultation_id)
WHERE consultation_id IS NOT NULL
  AND TRIM(consultation_id) <> '';

COMMIT;
