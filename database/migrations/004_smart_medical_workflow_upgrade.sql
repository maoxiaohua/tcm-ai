-- 智汇中医工作流升级 - 数据库迁移脚本
-- 创建时间: 2025-09-08
-- 版本: v2.4 第一阶段

-- ====================================
-- 1. 扩展现有表结构
-- ====================================

-- 1.1 扩展用户表 - 支持推荐人系统
ALTER TABLE users_new ADD COLUMN referrer_id VARCHAR(50);
ALTER TABLE users_new ADD COLUMN referral_code VARCHAR(20) UNIQUE;
ALTER TABLE users_new ADD COLUMN registration_source VARCHAR(20) DEFAULT 'direct'; -- direct, referral, guide

-- 1.2 扩展医生表 - 支持专科标签和评价
ALTER TABLE doctors_new ADD COLUMN specialties TEXT; -- JSON格式存储专科标签
ALTER TABLE doctors_new ADD COLUMN average_rating DECIMAL(3,2) DEFAULT 0.00;
ALTER TABLE doctors_new ADD COLUMN total_reviews INTEGER DEFAULT 0;
ALTER TABLE doctors_new ADD COLUMN consultation_count INTEGER DEFAULT 0;
ALTER TABLE doctors_new ADD COLUMN commission_rate DECIMAL(5,2) DEFAULT 0.00;
ALTER TABLE doctors_new ADD COLUMN available_hours TEXT; -- JSON格式存储可用时间
ALTER TABLE doctors_new ADD COLUMN introduction TEXT;
ALTER TABLE doctors_new ADD COLUMN avatar_url VARCHAR(255);

-- 1.3 扩展问诊表 - 支持医生选择和服务类型
ALTER TABLE consultations_new ADD COLUMN selected_doctor_id VARCHAR(50);
ALTER TABLE consultations_new ADD COLUMN doctor_selection_method VARCHAR(20); -- specified, recommended, guide
ALTER TABLE consultations_new ADD COLUMN service_type VARCHAR(20) DEFAULT 'prescription_only'; -- prescription_only, with_delivery
ALTER TABLE consultations_new ADD COLUMN guide_doctor_id VARCHAR(50);
ALTER TABLE consultations_new ADD COLUMN patient_rating INTEGER;
ALTER TABLE consultations_new ADD COLUMN patient_review TEXT;
ALTER TABLE consultations_new ADD COLUMN review_created_at TIMESTAMP;

-- 1.4 扩展处方表 - 支持隐藏和付费控制
ALTER TABLE prescriptions_new ADD COLUMN is_visible_to_patient BOOLEAN DEFAULT FALSE;
ALTER TABLE prescriptions_new ADD COLUMN visibility_unlock_time TIMESTAMP;
ALTER TABLE prescriptions_new ADD COLUMN payment_required_amount DECIMAL(10,2);
ALTER TABLE prescriptions_new ADD COLUMN prescription_fee DECIMAL(10,2) DEFAULT 88.00;

-- 1.5 扩展订单表 - 支持分成机制
ALTER TABLE orders_new ADD COLUMN doctor_commission DECIMAL(10,2) DEFAULT 0.00;
ALTER TABLE orders_new ADD COLUMN referrer_commission DECIMAL(10,2) DEFAULT 0.00;
ALTER TABLE orders_new ADD COLUMN platform_revenue DECIMAL(10,2) DEFAULT 0.00;

-- ====================================
-- 2. 新增表结构
-- ====================================

-- 2.1 医生选择偏好表
CREATE TABLE IF NOT EXISTS doctor_selection_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid VARCHAR(50) NOT NULL UNIQUE,
    patient_id VARCHAR(50) NOT NULL,
    preferred_specialties TEXT, -- JSON数组
    preferred_doctor_id VARCHAR(50),
    avoid_doctor_ids TEXT, -- JSON数组  
    preferred_consultation_time VARCHAR(20), -- morning, afternoon, evening, anytime
    language_preference VARCHAR(10) DEFAULT 'zh-CN',
    gender_preference VARCHAR(10), -- male, female, no_preference
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients_new(uuid)
);

-- 2.2 医生患者关系表
CREATE TABLE IF NOT EXISTS doctor_patient_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid VARCHAR(50) NOT NULL UNIQUE,
    doctor_id VARCHAR(50) NOT NULL,
    patient_id VARCHAR(50) NOT NULL,
    relationship_type VARCHAR(20) NOT NULL, -- assigned, preferred, blacklisted
    first_consultation_date TIMESTAMP,
    last_consultation_date TIMESTAMP,
    total_consultations INTEGER DEFAULT 0,
    total_amount_paid DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctors_new(uuid),
    FOREIGN KEY (patient_id) REFERENCES patients_new(uuid),
    UNIQUE(doctor_id, patient_id)
);

-- 2.3 患者评价表
CREATE TABLE IF NOT EXISTS patient_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid VARCHAR(50) NOT NULL UNIQUE,
    consultation_id VARCHAR(50) NOT NULL,
    patient_id VARCHAR(50) NOT NULL,
    doctor_id VARCHAR(50) NOT NULL,
    overall_rating INTEGER NOT NULL CHECK (overall_rating >= 1 AND overall_rating <= 5),
    professional_score INTEGER CHECK (professional_score >= 1 AND professional_score <= 5),
    service_score INTEGER CHECK (service_score >= 1 AND service_score <= 5),
    effect_score INTEGER CHECK (effect_score >= 1 AND effect_score <= 5),
    review_content TEXT,
    is_anonymous BOOLEAN DEFAULT FALSE,
    is_visible BOOLEAN DEFAULT TRUE,
    doctor_reply TEXT,
    doctor_reply_time TIMESTAMP,
    helpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (consultation_id) REFERENCES consultations_new(uuid),
    FOREIGN KEY (patient_id) REFERENCES patients_new(uuid),
    FOREIGN KEY (doctor_id) REFERENCES doctors_new(uuid)
);

-- 2.4 医生工作统计表
CREATE TABLE IF NOT EXISTS doctor_work_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid VARCHAR(50) NOT NULL UNIQUE,
    doctor_id VARCHAR(50) NOT NULL,
    date_period DATE NOT NULL,
    period_type VARCHAR(10) NOT NULL, -- daily, weekly, monthly
    consultations_count INTEGER DEFAULT 0,
    prescriptions_count INTEGER DEFAULT 0,
    total_revenue DECIMAL(10,2) DEFAULT 0.00,
    commission_earned DECIMAL(10,2) DEFAULT 0.00,
    average_rating DECIMAL(3,2) DEFAULT 0.00,
    reviews_received INTEGER DEFAULT 0,
    online_hours DECIMAL(5,2) DEFAULT 0.00,
    response_time_avg DECIMAL(5,2) DEFAULT 0.00, -- 平均响应时间(分钟)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctors_new(uuid),
    UNIQUE(doctor_id, date_period, period_type)
);

-- 2.5 服务类型定义表
CREATE TABLE IF NOT EXISTS service_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid VARCHAR(50) NOT NULL UNIQUE,
    service_code VARCHAR(20) NOT NULL UNIQUE,
    service_name VARCHAR(50) NOT NULL,
    description TEXT,
    base_price DECIMAL(10,2) NOT NULL,
    includes_delivery BOOLEAN DEFAULT FALSE,
    delivery_fee DECIMAL(10,2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2.6 医生可用时间表
CREATE TABLE IF NOT EXISTS doctor_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid VARCHAR(50) NOT NULL UNIQUE,
    doctor_id VARCHAR(50) NOT NULL,
    day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6), -- 0=Sunday
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    max_consultations INTEGER DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctors_new(uuid)
);

-- ====================================
-- 3. 初始化数据
-- ====================================

-- 3.1 插入基础服务类型
INSERT OR IGNORE INTO service_types (uuid, service_code, service_name, description, base_price, includes_delivery, delivery_fee) VALUES
('svc-001', 'prescription_only', '仅开处方', 'AI智能问诊+医生审核处方，患者自行购药', 88.00, FALSE, 0.00),
('svc-002', 'with_delivery', '开方+配送', 'AI智能问诊+医生审核处方+中药配送到家', 118.00, TRUE, 30.00);

-- 3.2 为现有医生初始化评价数据
UPDATE doctors_new SET 
    average_rating = 4.5,
    total_reviews = 0,
    consultation_count = 0,
    specialties = '["内科", "妇科", "儿科"]'
WHERE specialties IS NULL;

-- 3.3 为现有处方设置默认可见性（已支付的处方可见）
UPDATE prescriptions_new SET 
    is_visible_to_patient = TRUE,
    prescription_fee = 88.00
WHERE status IN ('approved', 'completed') AND is_visible_to_patient IS NULL;

-- ====================================
-- 4. 创建索引优化查询性能
-- ====================================

-- 医生选择相关索引
CREATE INDEX IF NOT EXISTS idx_doctor_selection_patient ON doctor_selection_preferences(patient_id);
CREATE INDEX IF NOT EXISTS idx_doctor_patient_relationship ON doctor_patient_relationships(doctor_id, patient_id);

-- 评价系统相关索引
CREATE INDEX IF NOT EXISTS idx_patient_reviews_doctor ON patient_reviews(doctor_id, is_visible);
CREATE INDEX IF NOT EXISTS idx_patient_reviews_consultation ON patient_reviews(consultation_id);
CREATE INDEX IF NOT EXISTS idx_patient_reviews_rating ON patient_reviews(overall_rating, created_at);

-- 统计相关索引
CREATE INDEX IF NOT EXISTS idx_doctor_statistics ON doctor_work_statistics(doctor_id, date_period);
CREATE INDEX IF NOT EXISTS idx_doctors_rating ON doctors_new(average_rating DESC, total_reviews DESC);

-- 可用性相关索引
CREATE INDEX IF NOT EXISTS idx_doctor_availability ON doctor_availability(doctor_id, day_of_week, is_available);

-- ====================================
-- 5. 触发器 - 自动维护统计数据
-- ====================================

-- 5.1 评价后自动更新医生评分
CREATE TRIGGER IF NOT EXISTS update_doctor_rating_after_review
    AFTER INSERT ON patient_reviews
BEGIN
    UPDATE doctors_new SET
        total_reviews = (
            SELECT COUNT(*) FROM patient_reviews 
            WHERE doctor_id = NEW.doctor_id AND is_visible = TRUE
        ),
        average_rating = (
            SELECT ROUND(AVG(CAST(overall_rating AS REAL)), 2) 
            FROM patient_reviews 
            WHERE doctor_id = NEW.doctor_id AND is_visible = TRUE
        )
    WHERE uuid = NEW.doctor_id;
END;

-- 5.2 问诊完成后自动增加医生问诊计数
CREATE TRIGGER IF NOT EXISTS update_doctor_consultation_count
    AFTER UPDATE ON consultations_new
    WHEN NEW.status = 'completed' AND OLD.status != 'completed'
BEGIN
    UPDATE doctors_new SET
        consultation_count = consultation_count + 1
    WHERE uuid = NEW.selected_doctor_id;
END;

-- 5.3 处方支付后自动显示给患者
CREATE TRIGGER IF NOT EXISTS show_prescription_after_payment
    AFTER UPDATE ON orders_new
    WHEN NEW.status = 'paid' AND OLD.status != 'paid'
BEGIN
    UPDATE prescriptions_new SET
        is_visible_to_patient = TRUE,
        visibility_unlock_time = CURRENT_TIMESTAMP
    WHERE uuid IN (
        SELECT prescription_id FROM consultations_new 
        WHERE uuid = NEW.consultation_id
    );
END;

-- ====================================
-- 迁移完成标记
-- ====================================
INSERT OR REPLACE INTO system_settings (key, value, description, created_at) VALUES
('db_version', '2.4.1', '智汇中医工作流升级 - 第一阶段', CURRENT_TIMESTAMP);

-- 迁移日志
INSERT INTO audit_logs (uuid, user_id, action, resource_type, resource_id, details, created_at) VALUES
('audit-' || lower(hex(randomblob(16))), 'system', 'database_migration', 'system', 'db_v2.4.1', 
'智汇中医工作流数据库升级完成：医生选择、评价系统、处方隐藏机制', CURRENT_TIMESTAMP);