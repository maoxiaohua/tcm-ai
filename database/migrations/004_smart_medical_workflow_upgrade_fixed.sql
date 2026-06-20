-- 智汇中医工作流升级 - 数据库迁移脚本 (修正版)
-- 创建时间: 2025-09-09
-- 版本: v2.4 第一阶段

-- ====================================
-- 1. 扩展现有表结构
-- ====================================

-- 1.1 扩展用户表 - 支持推荐人系统
ALTER TABLE users ADD COLUMN referrer_id VARCHAR(50);
ALTER TABLE users ADD COLUMN referral_code VARCHAR(20) UNIQUE;
ALTER TABLE users ADD COLUMN registration_source VARCHAR(20) DEFAULT 'direct'; -- direct, referral, guide

-- 1.2 扩展医生表 - 支持专科标签和评价
ALTER TABLE doctors ADD COLUMN specialties TEXT; -- JSON格式存储专科标签
ALTER TABLE doctors ADD COLUMN average_rating DECIMAL(3,2) DEFAULT 0.00;
ALTER TABLE doctors ADD COLUMN total_reviews INTEGER DEFAULT 0;
ALTER TABLE doctors ADD COLUMN consultation_count INTEGER DEFAULT 0;
ALTER TABLE doctors ADD COLUMN commission_rate DECIMAL(5,2) DEFAULT 0.00;
ALTER TABLE doctors ADD COLUMN available_hours TEXT; -- JSON格式存储可用时间
ALTER TABLE doctors ADD COLUMN introduction TEXT;
ALTER TABLE doctors ADD COLUMN avatar_url VARCHAR(255);

-- 1.3 创建问诊表（如果不存在）
CREATE TABLE IF NOT EXISTS consultations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid VARCHAR(50) UNIQUE NOT NULL,
    patient_id VARCHAR(50) NOT NULL,
    selected_doctor_id VARCHAR(50),
    doctor_selection_method VARCHAR(20) DEFAULT 'recommended', -- specified, recommended, guide
    service_type VARCHAR(20) DEFAULT 'prescription_only', -- prescription_only, with_delivery
    guide_doctor_id VARCHAR(50),
    symptoms_analysis TEXT,
    tcm_syndrome VARCHAR(200),
    conversation_log TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    patient_rating INTEGER,
    patient_review TEXT,
    review_created_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES users(uuid),
    FOREIGN KEY (selected_doctor_id) REFERENCES doctors(uuid)
);

-- 1.4 扩展处方表 - 支持隐藏和付费控制
ALTER TABLE prescriptions ADD COLUMN is_visible_to_patient BOOLEAN DEFAULT 0;
ALTER TABLE prescriptions ADD COLUMN visibility_unlock_time TIMESTAMP;
ALTER TABLE prescriptions ADD COLUMN payment_required_amount DECIMAL(10,2);
ALTER TABLE prescriptions ADD COLUMN prescription_fee DECIMAL(10,2) DEFAULT 88.00;
ALTER TABLE prescriptions ADD COLUMN consultation_id VARCHAR(50);

-- 1.5 扩展订单表 - 支持分成机制
ALTER TABLE orders ADD COLUMN consultation_id VARCHAR(50);
ALTER TABLE orders ADD COLUMN doctor_commission DECIMAL(10,2) DEFAULT 0.00;
ALTER TABLE orders ADD COLUMN referrer_commission DECIMAL(10,2) DEFAULT 0.00;
ALTER TABLE orders ADD COLUMN platform_revenue DECIMAL(10,2) DEFAULT 0.00;

-- ====================================
-- 2. 新增表结构
-- ====================================

-- 2.1 医生选择偏好表
CREATE TABLE IF NOT EXISTS doctor_selection_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id VARCHAR(50) NOT NULL,
    preferred_specialties TEXT, -- JSON格式存储偏好专科
    preferred_doctor_id VARCHAR(50),
    avoid_doctor_ids TEXT, -- JSON格式存储避免的医生ID列表
    preferred_consultation_time VARCHAR(50),
    gender_preference VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES users(uuid),
    FOREIGN KEY (preferred_doctor_id) REFERENCES doctors(uuid)
);

-- 2.2 医患关系表
CREATE TABLE IF NOT EXISTS doctor_patient_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id VARCHAR(50) NOT NULL,
    patient_id VARCHAR(50) NOT NULL,
    relationship_type VARCHAR(20) DEFAULT 'consultation', -- consultation, follow_up, guide
    first_consultation_date TIMESTAMP,
    last_consultation_date TIMESTAMP,
    total_consultations INTEGER DEFAULT 0,
    total_prescriptions INTEGER DEFAULT 0,
    total_amount_spent DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctors(uuid),
    FOREIGN KEY (patient_id) REFERENCES users(uuid),
    UNIQUE(doctor_id, patient_id)
);

-- 2.3 患者评价表
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (consultation_id) REFERENCES consultations(uuid),
    FOREIGN KEY (patient_id) REFERENCES users(uuid),
    FOREIGN KEY (doctor_id) REFERENCES doctors(uuid)
);

-- 2.4 医生工作统计表
CREATE TABLE IF NOT EXISTS doctor_work_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    consultations_count INTEGER DEFAULT 0,
    prescriptions_count INTEGER DEFAULT 0,
    revenue_generated DECIMAL(10,2) DEFAULT 0.00,
    commission_earned DECIMAL(10,2) DEFAULT 0.00,
    online_duration_minutes INTEGER DEFAULT 0,
    average_rating DECIMAL(3,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctors(uuid),
    UNIQUE(doctor_id, date)
);

-- 2.5 服务类型表
CREATE TABLE IF NOT EXISTS service_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    base_price DECIMAL(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2.6 医生可用时间表
CREATE TABLE IF NOT EXISTS doctor_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id VARCHAR(50) NOT NULL,
    day_of_week INTEGER NOT NULL CHECK(day_of_week >= 0 AND day_of_week <= 6), -- 0=周日
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_available BOOLEAN DEFAULT 1,
    max_consultations_per_hour INTEGER DEFAULT 4,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctors(uuid)
);

-- 2.7 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(50),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(50),
    details TEXT, -- JSON格式存储详细信息
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ====================================
-- 3. 创建索引
-- ====================================

-- 3.1 性能优化索引
CREATE INDEX IF NOT EXISTS idx_consultations_patient ON consultations(patient_id);
CREATE INDEX IF NOT EXISTS idx_consultations_doctor ON consultations(selected_doctor_id);
CREATE INDEX IF NOT EXISTS idx_consultations_status ON consultations(status);
CREATE INDEX IF NOT EXISTS idx_reviews_doctor ON patient_reviews(doctor_id);
CREATE INDEX IF NOT EXISTS idx_reviews_patient ON patient_reviews(patient_id);
CREATE INDEX IF NOT EXISTS idx_reviews_created ON patient_reviews(created_at);
CREATE INDEX IF NOT EXISTS idx_prescriptions_consultation ON prescriptions(consultation_id);
CREATE INDEX IF NOT EXISTS idx_orders_consultation ON orders(consultation_id);

-- ====================================
-- 4. 触发器
-- ====================================

-- 4.1 处方支付后自动显示触发器
CREATE TRIGGER IF NOT EXISTS show_prescription_after_payment
    AFTER UPDATE ON orders
    WHEN NEW.status = 'paid' AND OLD.status != 'paid'
BEGIN
    UPDATE prescriptions SET
        is_visible_to_patient = 1,
        visibility_unlock_time = CURRENT_TIMESTAMP
    WHERE consultation_id = NEW.consultation_id;
END;

-- 4.2 评价后自动更新医生统计触发器
CREATE TRIGGER IF NOT EXISTS update_doctor_rating_after_review
    AFTER INSERT ON patient_reviews
BEGIN
    UPDATE doctors SET
        total_reviews = total_reviews + 1,
        average_rating = (
            SELECT AVG(overall_rating) 
            FROM patient_reviews 
            WHERE doctor_id = NEW.doctor_id AND is_visible = 1
        )
    WHERE uuid = NEW.doctor_id;
END;

-- 4.3 问诊完成后更新统计触发器
CREATE TRIGGER IF NOT EXISTS update_consultation_stats
    AFTER UPDATE ON consultations
    WHEN NEW.status = 'completed' AND OLD.status != 'completed'
BEGIN
    UPDATE doctors SET
        consultation_count = consultation_count + 1
    WHERE uuid = NEW.selected_doctor_id;
    
    -- 更新医患关系
    INSERT OR REPLACE INTO doctor_patient_relationships (
        doctor_id, patient_id, relationship_type, 
        first_consultation_date, last_consultation_date,
        total_consultations, total_prescriptions,
        created_at, updated_at
    ) VALUES (
        NEW.selected_doctor_id, NEW.patient_id, 'consultation',
        COALESCE((
            SELECT first_consultation_date 
            FROM doctor_patient_relationships 
            WHERE doctor_id = NEW.selected_doctor_id AND patient_id = NEW.patient_id
        ), NEW.created_at),
        NEW.updated_at,
        COALESCE((
            SELECT total_consultations 
            FROM doctor_patient_relationships 
            WHERE doctor_id = NEW.selected_doctor_id AND patient_id = NEW.patient_id
        ), 0) + 1,
        COALESCE((
            SELECT total_prescriptions 
            FROM doctor_patient_relationships 
            WHERE doctor_id = NEW.selected_doctor_id AND patient_id = NEW.patient_id
        ), 0),
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    );
END;

-- ====================================
-- 5. 插入默认数据
-- ====================================

-- 5.1 插入服务类型
INSERT OR IGNORE INTO service_types (code, name, description, base_price) VALUES
('prescription_only', '处方开具', '仅开具处方，患者自行抓药', 88.00),
('with_delivery', '处方配送', '开具处方并提供代煎配送服务', 158.00),
('consultation_only', '咨询问诊', '仅提供医疗咨询，不开具处方', 58.00);

-- 5.2 插入测试医生数据（如果表为空）
INSERT OR IGNORE INTO doctors (uuid, name, title, specialties, introduction, average_rating, total_reviews, consultation_count) VALUES
('doctor-zhangsan-001', '张三', '主治医师', '["内科", "脾胃病科"]', '从事中医临床工作15年，擅长脾胃疾病、失眠调理', 4.8, 156, 890),
('doctor-lisi-002', '李四', '副主任医师', '["妇科", "内科"]', '中医妇科专家，擅长月经不调、不孕不育等妇科疾病', 4.9, 203, 1200),
('doctor-wangwu-003', '王五', '主任医师', '["骨伤科", "针灸科"]', '中医正骨专家，擅长颈肩腰腿痛、运动损伤', 4.7, 89, 456);

-- 5.3 更新现有处方的关联关系（如果需要）
-- 这部分根据实际数据情况调整

-- ====================================
-- 6. 系统设置更新
-- ====================================

-- 6.1 添加系统配置
INSERT OR REPLACE INTO system_settings (setting_key, setting_value, description) VALUES
('prescription_default_fee', '88.00', '处方默认费用'),
('doctor_commission_rate', '0.30', '医生默认分成比例'),
('referrer_commission_rate', '0.10', '推荐人分成比例'),
('prescription_visibility_enabled', 'true', '是否启用处方付费查看功能'),
('review_time_limit_days', '7', '评价时限（天数）'),
('max_consultations_per_doctor_per_hour', '4', '每位医生每小时最大问诊数');