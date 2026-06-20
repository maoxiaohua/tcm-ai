-- AI增强处方管理系统数据库迁移
-- 创建AI分析相关表

-- 处方AI分析结果表
CREATE TABLE IF NOT EXISTS prescription_ai_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER NOT NULL,
    analysis_type VARCHAR(50) NOT NULL,  -- comprehensive, safety, efficacy, batch_check
    analysis_result TEXT NOT NULL,       -- JSON格式的分析结果
    analyzed_by VARCHAR(255),            -- 分析发起人
    analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id)
);

-- 处方AI推荐表
CREATE TABLE IF NOT EXISTS prescription_ai_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER NOT NULL,
    recommendation TEXT NOT NULL,        -- JSON格式的推荐内容
    recommended_by VARCHAR(255),         -- 推荐发起人
    recommended_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_applied BOOLEAN DEFAULT FALSE,    -- 是否已应用推荐
    applied_at DATETIME,
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id)
);

-- 处方变更历史表（如果不存在）
CREATE TABLE IF NOT EXISTS prescription_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER NOT NULL,
    changed_by VARCHAR(255) NOT NULL,
    change_type VARCHAR(50) NOT NULL,    -- modified, approved, rejected, ai_analyzed
    original_prescription TEXT,
    new_prescription TEXT,
    change_reason TEXT,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id)
);

-- 医生审查效率统计表
CREATE TABLE IF NOT EXISTS doctor_review_efficiency (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    total_reviews INTEGER DEFAULT 0,
    avg_review_time_seconds INTEGER DEFAULT 0,
    ai_assisted_reviews INTEGER DEFAULT 0,
    manual_reviews INTEGER DEFAULT 0,
    high_risk_reviews INTEGER DEFAULT 0,
    approval_rate DECIMAL(5,2) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(doctor_id, date)
);

-- 处方风险评级表
CREATE TABLE IF NOT EXISTS prescription_risk_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER NOT NULL,
    risk_level VARCHAR(20) NOT NULL,     -- low, medium, high
    risk_score DECIMAL(3,2) DEFAULT 0,   -- 0.00-1.00
    risk_factors TEXT,                   -- JSON格式风险因素
    assessed_by VARCHAR(50) DEFAULT 'ai', -- ai, doctor, system
    assessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id)
);

-- AI学习反馈表
CREATE TABLE IF NOT EXISTS ai_learning_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER NOT NULL,
    ai_recommendation TEXT NOT NULL,     -- AI的推荐
    doctor_decision TEXT NOT NULL,       -- 医生的实际决定
    doctor_feedback TEXT,                -- 医生对AI推荐的反馈
    feedback_score INTEGER,              -- 1-5分评价AI推荐质量
    learning_points TEXT,                -- JSON格式学习要点
    created_by VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id)
);

-- 批量操作记录表
CREATE TABLE IF NOT EXISTS batch_operations_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type VARCHAR(50) NOT NULL, -- batch_approve, batch_reject, batch_ai_check
    prescription_ids TEXT NOT NULL,      -- JSON数组格式的处方ID列表
    operation_params TEXT,               -- JSON格式操作参数
    executed_by VARCHAR(255) NOT NULL,
    execution_status VARCHAR(20) DEFAULT 'pending', -- pending, completed, failed, partial
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    error_details TEXT,                  -- JSON格式错误详情
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

-- 智能提醒配置表
CREATE TABLE IF NOT EXISTS smart_alerts_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type VARCHAR(50) NOT NULL,     -- high_risk, drug_interaction, dosage_warning
    alert_name VARCHAR(100) NOT NULL,
    alert_condition TEXT NOT NULL,       -- JSON格式条件配置
    alert_action TEXT NOT NULL,          -- JSON格式动作配置
    is_enabled BOOLEAN DEFAULT TRUE,
    priority_level INTEGER DEFAULT 1,    -- 1-5优先级
    created_by VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 医生学习进度表
CREATE TABLE IF NOT EXISTS doctor_learning_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id VARCHAR(255) NOT NULL,
    learning_module VARCHAR(100) NOT NULL, -- drug_interactions, tcm_theory, safety_guidelines
    progress_percentage INTEGER DEFAULT 0,  -- 0-100
    completed_lessons TEXT,                 -- JSON数组格式
    current_lesson VARCHAR(100),
    last_accessed_at DATETIME,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(doctor_id, learning_module)
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_prescription_ai_analysis_prescription_id ON prescription_ai_analysis(prescription_id);
CREATE INDEX IF NOT EXISTS idx_prescription_ai_analysis_type ON prescription_ai_analysis(analysis_type);
CREATE INDEX IF NOT EXISTS idx_prescription_ai_recommendations_prescription_id ON prescription_ai_recommendations(prescription_id);
CREATE INDEX IF NOT EXISTS idx_prescription_changes_prescription_id ON prescription_changes(prescription_id);
CREATE INDEX IF NOT EXISTS idx_doctor_review_efficiency_doctor_date ON doctor_review_efficiency(doctor_id, date);
CREATE INDEX IF NOT EXISTS idx_prescription_risk_ratings_prescription_id ON prescription_risk_ratings(prescription_id);
CREATE INDEX IF NOT EXISTS idx_prescription_risk_ratings_risk_level ON prescription_risk_ratings(risk_level);
CREATE INDEX IF NOT EXISTS idx_ai_learning_feedback_prescription_id ON ai_learning_feedback(prescription_id);
CREATE INDEX IF NOT EXISTS idx_batch_operations_log_executed_by ON batch_operations_log(executed_by);
CREATE INDEX IF NOT EXISTS idx_smart_alerts_config_alert_type ON smart_alerts_config(alert_type);
CREATE INDEX IF NOT EXISTS idx_doctor_learning_progress_doctor_id ON doctor_learning_progress(doctor_id);

-- 插入默认的智能提醒配置
INSERT OR IGNORE INTO smart_alerts_config (alert_type, alert_name, alert_condition, alert_action, priority_level) VALUES
('high_risk', '高风险处方提醒', 
 '{"risk_score": {">=": 0.8}, "risk_factors": ["dosage_exceeded", "drug_interaction"]}',
 '{"notification": true, "priority_queue": true, "auto_flag": true}', 
 5),
('drug_interaction', '药物相互作用警告',
 '{"interaction_level": ["major", "moderate"], "interaction_count": {">=": 1}}',
 '{"warning_popup": true, "require_confirmation": true}',
 4),
('dosage_warning', '剂量安全警告',
 '{"dosage_ratio": {">=": 1.2}, "safety_margin": {"<=": 0.1}}',
 '{"highlight": true, "suggest_adjustment": true}',
 3),
('pregnancy_contraindication', '妊娠禁忌提醒',
 '{"patient_condition": "pregnant", "contraindicated_herbs": {"count": {">=": 1}}}',
 '{"block_approval": true, "require_senior_review": true}',
 5),
('elderly_caution', '老年患者用药提醒',
 '{"patient_age": {">=": 65}, "caution_herbs": {"count": {">=": 1}}}',
 '{"dosage_review": true, "monitoring_reminder": true}',
 3);

-- 插入默认学习模块
INSERT OR IGNORE INTO doctor_learning_progress (doctor_id, learning_module, progress_percentage) 
SELECT 'zhangzhongjing_001', module, 0 FROM (
    SELECT 'drug_interactions' as module
    UNION SELECT 'tcm_theory'
    UNION SELECT 'safety_guidelines'
    UNION SELECT 'prescription_optimization'
    UNION SELECT 'ai_assisted_diagnosis'
);