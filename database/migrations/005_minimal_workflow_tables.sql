-- 智汇中医工作流最小表结构创建
-- 只创建核心功能所需的新表

-- 1. 患者评价表
CREATE TABLE IF NOT EXISTS patient_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid VARCHAR(50) UNIQUE NOT NULL,
    consultation_id VARCHAR(50) NOT NULL,
    patient_id VARCHAR(50) NOT NULL,
    doctor_id VARCHAR(50) NOT NULL,
    overall_rating INTEGER NOT NULL CHECK(overall_rating >= 1 AND overall_rating <= 5),
    professional_score INTEGER CHECK(professional_score >= 1 AND professional_score <= 5),
    service_score INTEGER CHECK(service_score >= 1 AND service_score <= 5),
    effect_score INTEGER CHECK(effect_score >= 1 AND effect_score <= 5),
    review_content TEXT,
    is_anonymous BOOLEAN DEFAULT 0,
    is_visible BOOLEAN DEFAULT 1,
    doctor_reply TEXT,
    doctor_reply_time TIMESTAMP,
    helpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 医生选择偏好表
CREATE TABLE IF NOT EXISTS doctor_selection_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id VARCHAR(50) NOT NULL,
    preferred_specialties TEXT, -- JSON格式存储偏好专科
    preferred_doctor_id VARCHAR(50),
    avoid_doctor_ids TEXT, -- JSON格式存储避免的医生ID列表
    preferred_consultation_time VARCHAR(50),
    gender_preference VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 医患关系表
CREATE TABLE IF NOT EXISTS doctor_patient_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id VARCHAR(50) NOT NULL,
    patient_id VARCHAR(50) NOT NULL,
    relationship_type VARCHAR(20) DEFAULT 'consultation',
    first_consultation_date TIMESTAMP,
    last_consultation_date TIMESTAMP,
    total_consultations INTEGER DEFAULT 0,
    total_prescriptions INTEGER DEFAULT 0,
    total_amount_spent DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(doctor_id, patient_id)
);

-- 4. 问诊记录表（简化版）
CREATE TABLE IF NOT EXISTS consultations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid VARCHAR(50) UNIQUE NOT NULL,
    patient_id VARCHAR(50) NOT NULL,
    selected_doctor_id VARCHAR(50),
    doctor_selection_method VARCHAR(20) DEFAULT 'recommended',
    service_type VARCHAR(20) DEFAULT 'prescription_only',
    symptoms_analysis TEXT,
    tcm_syndrome VARCHAR(200),
    conversation_log TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    patient_rating INTEGER,
    patient_review TEXT,
    review_created_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. 扩展处方表的必要列
-- 检查列是否已存在，如果不存在则添加
-- SQLite doesn't support ALTER COLUMN IF NOT EXISTS, so we'll use a different approach

-- 创建一个临时表来检查列是否存在
CREATE TEMP TABLE temp_check_columns AS SELECT * FROM prescriptions LIMIT 0;

-- 尝试添加列，如果失败则忽略
BEGIN TRANSACTION;

-- 添加可见性控制列
ALTER TABLE prescriptions ADD COLUMN is_visible_to_patient BOOLEAN DEFAULT 0;
ALTER TABLE prescriptions ADD COLUMN visibility_unlock_time TIMESTAMP;
ALTER TABLE prescriptions ADD COLUMN prescription_fee DECIMAL(10,2) DEFAULT 88.00;
ALTER TABLE prescriptions ADD COLUMN consultation_id VARCHAR(50);

-- 添加问诊关联到订单表
ALTER TABLE orders ADD COLUMN consultation_id VARCHAR(50);

COMMIT;

-- 6. 创建索引
CREATE INDEX IF NOT EXISTS idx_patient_reviews_doctor ON patient_reviews(doctor_id);
CREATE INDEX IF NOT EXISTS idx_patient_reviews_patient ON patient_reviews(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_reviews_consultation ON patient_reviews(consultation_id);
CREATE INDEX IF NOT EXISTS idx_consultations_patient ON consultations(patient_id);
CREATE INDEX IF NOT EXISTS idx_consultations_doctor ON consultations(selected_doctor_id);
CREATE INDEX IF NOT EXISTS idx_doctor_relationships ON doctor_patient_relationships(doctor_id, patient_id);

-- 7. 添加一些测试数据
-- 创建一个测试医生记录（使用自增ID）
INSERT OR IGNORE INTO doctors (name, license_no, speciality, specialties, introduction, average_rating, total_reviews, consultation_count) VALUES
('张医生', 'LICENSE001', '内科', '["内科", "脾胃病科"]', '从事中医临床工作15年，擅长脾胃疾病调理', 4.8, 156, 890);

INSERT OR IGNORE INTO doctors (name, license_no, speciality, specialties, introduction, average_rating, total_reviews, consultation_count) VALUES
('李医生', 'LICENSE002', '妇科', '["妇科", "内科"]', '中医妇科专家，擅长妇科疾病治疗', 4.9, 203, 1200);

INSERT OR IGNORE INTO doctors (name, license_no, speciality, specialties, introduction, average_rating, total_reviews, consultation_count) VALUES
('王医生', 'LICENSE003', '骨科', '["骨伤科", "针灸科"]', '中医正骨专家，擅长筋骨疼痛治疗', 4.7, 89, 456);