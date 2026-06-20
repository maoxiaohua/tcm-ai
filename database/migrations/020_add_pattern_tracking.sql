-- ============================================================
-- Migration: 添加决策树使用追踪功能
-- Version: 020
-- Date: 2025-10-18
-- Description:
--   1. 在consultations表添加决策树使用追踪字段
--   2. 创建doctor_clinical_patterns表（思维库）
--   3. 创建统计视图，提高查询性能
-- ============================================================

-- 1. 修改consultations表，添加决策树追踪字段
ALTER TABLE consultations
ADD COLUMN used_pattern_id VARCHAR(50);

ALTER TABLE consultations
ADD COLUMN pattern_match_score DECIMAL(3,2);

-- 添加索引，提高查询性能
CREATE INDEX IF NOT EXISTS idx_consultations_pattern
ON consultations(used_pattern_id);

-- 2. 创建医生临床决策模式表（思维库）
CREATE TABLE IF NOT EXISTS doctor_clinical_patterns (
    id TEXT PRIMARY KEY,
    doctor_id TEXT NOT NULL,
    disease_name TEXT NOT NULL,
    thinking_process TEXT NOT NULL,
    tree_structure TEXT NOT NULL,
    clinical_patterns TEXT NOT NULL,
    doctor_expertise TEXT NOT NULL,
    usage_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(doctor_id, disease_name)
);

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_patterns_doctor
ON doctor_clinical_patterns(doctor_id);

CREATE INDEX IF NOT EXISTS idx_patterns_disease
ON doctor_clinical_patterns(disease_name);

CREATE INDEX IF NOT EXISTS idx_patterns_usage
ON doctor_clinical_patterns(usage_count DESC);

-- 3. 创建决策树使用统计视图
CREATE VIEW IF NOT EXISTS v_pattern_usage_stats AS
SELECT
    p.id as pattern_id,
    p.doctor_id,
    p.disease_name,
    p.usage_count as total_usage,
    p.success_count,
    p.last_used_at,
    p.created_at,
    COUNT(DISTINCT c.uuid) as consultation_count,
    COUNT(DISTINCT CASE WHEN pr.status = 'reviewed' THEN c.uuid END) as success_consultation_count,
    ROUND(CAST(COUNT(DISTINCT CASE WHEN pr.status = 'reviewed' THEN c.uuid END) AS FLOAT) /
          NULLIF(COUNT(DISTINCT c.uuid), 0) * 100, 2) as success_rate
FROM doctor_clinical_patterns p
LEFT JOIN consultations c ON c.used_pattern_id = p.id
LEFT JOIN prescriptions pr ON pr.consultation_id = c.uuid
GROUP BY p.id, p.doctor_id, p.disease_name;

-- 4. 创建医生决策树使用详情视图
CREATE VIEW IF NOT EXISTS v_doctor_pattern_details AS
SELECT
    c.uuid as consultation_id,
    c.patient_id,
    c.used_pattern_id as pattern_id,
    c.pattern_match_score,
    c.created_at as consultation_date,
    p.id as prescription_id,
    p.status as prescription_status,
    p.review_status,
    p.payment_status,
    pat.disease_name,
    pat.doctor_id
FROM consultations c
LEFT JOIN prescriptions p ON p.consultation_id = c.uuid
LEFT JOIN doctor_clinical_patterns pat ON pat.id = c.used_pattern_id
WHERE c.used_pattern_id IS NOT NULL
ORDER BY c.created_at DESC;

-- 5. 创建触发器：自动更新usage_count
-- SQLite不支持AFTER UPDATE触发器更新其他表，所以我们用定期统计的方式

-- 备注：
-- - used_pattern_id: 记录问诊使用了哪个决策树（外键关联doctor_clinical_patterns.id）
-- - pattern_match_score: 决策树匹配置信度（0.0-1.0）
-- - 统计视图提供实时的使用数据，避免频繁join查询
