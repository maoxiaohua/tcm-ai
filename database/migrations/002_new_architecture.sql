-- 中医AI系统新架构数据库迁移脚本
-- 执行前请备份现有数据：sqlite3 user_history.sqlite ".backup backup_$(date +%Y%m%d_%H%M%S).db"

BEGIN TRANSACTION;

-- 1. 创建新的用户管理表
CREATE TABLE users_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    user_type TEXT NOT NULL CHECK (user_type IN ('patient', 'doctor', 'admin')),
    phone TEXT,
    email TEXT,
    name TEXT,
    avatar_url TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    metadata TEXT DEFAULT '{}',
    version INTEGER DEFAULT 1
);

CREATE UNIQUE INDEX idx_users_new_phone ON users_new(phone) WHERE phone IS NOT NULL;
CREATE UNIQUE INDEX idx_users_new_email ON users_new(email) WHERE email IS NOT NULL;
CREATE INDEX idx_users_new_type_status ON users_new(user_type, status);

-- 2. 创建患者详细信息表
CREATE TABLE patients_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users_new(id) ON DELETE CASCADE,
    birth_date DATE,
    gender TEXT CHECK (gender IN ('male', 'female', 'other')),
    height REAL,
    weight REAL,
    blood_type TEXT,
    allergies TEXT DEFAULT '[]',
    medical_history TEXT DEFAULT '{}',
    emergency_contact TEXT DEFAULT '{}',
    preferences TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);

CREATE UNIQUE INDEX idx_patients_new_user_id ON patients_new(user_id);

-- 3. 创建医生详细信息表（重构现有doctors表）
CREATE TABLE doctors_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users_new(id) ON DELETE CASCADE,
    license_no TEXT UNIQUE NOT NULL,
    license_expiry DATE,
    speciality TEXT NOT NULL,
    hospital TEXT,
    department TEXT,
    title TEXT,
    years_experience INTEGER,
    education TEXT,
    research_areas TEXT DEFAULT '[]',
    password_hash TEXT NOT NULL,
    auth_salt TEXT NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'pending_review')),
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);

CREATE UNIQUE INDEX idx_doctors_new_license ON doctors_new(license_no);
CREATE UNIQUE INDEX idx_doctors_new_user_id ON doctors_new(user_id);
CREATE INDEX idx_doctors_new_speciality ON doctors_new(speciality);

-- 4. 创建问诊记录表
CREATE TABLE consultations_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    patient_id INTEGER NOT NULL REFERENCES users_new(id),
    doctor_persona TEXT,
    chief_complaint TEXT,
    present_illness TEXT,
    past_history TEXT,
    family_history TEXT,
    physical_exam TEXT,
    symptoms_analysis TEXT DEFAULT '{}',
    tcm_syndrome TEXT,
    diagnosis TEXT,
    conversation_log TEXT DEFAULT '[]',
    consultation_type TEXT DEFAULT 'ai_primary' CHECK (
        consultation_type IN ('ai_primary', 'doctor_review', 'follow_up')
    ),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled')),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);

CREATE UNIQUE INDEX idx_consultations_new_uuid ON consultations_new(uuid);
CREATE INDEX idx_consultations_new_patient ON consultations_new(patient_id, status);
CREATE INDEX idx_consultations_new_date ON consultations_new(created_at);

-- 5. 重构处方表
CREATE TABLE prescriptions_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    consultation_id INTEGER NOT NULL REFERENCES consultations_new(id),
    patient_id INTEGER NOT NULL REFERENCES users_new(id),
    prescriber_type TEXT NOT NULL CHECK (prescriber_type IN ('ai', 'doctor')),
    prescriber_id INTEGER REFERENCES users_new(id),
    
    -- 处方内容
    herbs TEXT NOT NULL CHECK (length(herbs) > 0),
    dosage_instructions TEXT,
    treatment_duration INTEGER,
    special_instructions TEXT,
    
    -- 状态管理
    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending', 'doctor_reviewing', 'approved', 'rejected', 
        'patient_confirmed', 'paid', 'dispensing', 'shipped', 'completed'
    )),
    
    -- 审查信息
    reviewed_by INTEGER REFERENCES users_new(id),
    reviewed_at TIMESTAMP,
    review_notes TEXT,
    
    -- 患者确认
    patient_confirmed_at TIMESTAMP,
    patient_notes TEXT,
    
    -- 版本控制
    parent_prescription_id INTEGER REFERENCES prescriptions_new(id),
    revision_reason TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);

CREATE UNIQUE INDEX idx_prescriptions_new_uuid ON prescriptions_new(uuid);
CREATE INDEX idx_prescriptions_new_consultation ON prescriptions_new(consultation_id);
CREATE INDEX idx_prescriptions_new_patient ON prescriptions_new(patient_id, status);
CREATE INDEX idx_prescriptions_new_doctor_review ON prescriptions_new(reviewed_by, status);
CREATE INDEX idx_prescriptions_new_status ON prescriptions_new(status, created_at);

-- 6. 创建订单管理表
CREATE TABLE orders_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT UNIQUE NOT NULL,
    prescription_id INTEGER NOT NULL REFERENCES prescriptions_new(id),
    patient_id INTEGER NOT NULL REFERENCES users_new(id),
    
    -- 订单内容
    items TEXT NOT NULL DEFAULT '[]',
    subtotal_amount DECIMAL(10,2) NOT NULL CHECK (subtotal_amount >= 0),
    service_amount DECIMAL(10,2) DEFAULT 0 CHECK (service_amount >= 0),
    shipping_amount DECIMAL(10,2) DEFAULT 0 CHECK (shipping_amount >= 0),
    total_amount DECIMAL(10,2) NOT NULL CHECK (total_amount >= 0),
    
    -- 配送信息
    needs_decoction BOOLEAN DEFAULT FALSE,
    shipping_address TEXT DEFAULT '{}',
    
    -- 状态管理
    status TEXT DEFAULT 'created' CHECK (status IN (
        'created', 'paid', 'processing', 'shipping', 'delivered', 'completed', 'cancelled'
    )),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    version INTEGER DEFAULT 1
);

CREATE UNIQUE INDEX idx_orders_new_order_no ON orders_new(order_no);
CREATE INDEX idx_orders_new_prescription ON orders_new(prescription_id);
CREATE INDEX idx_orders_new_patient ON orders_new(patient_id, status);
CREATE INDEX idx_orders_new_status ON orders_new(status, created_at);

-- 7. 创建支付管理表
CREATE TABLE payments_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders_new(id),
    payment_method TEXT NOT NULL CHECK (payment_method IN ('alipay', 'wechat', 'bank')),
    payment_provider TEXT,
    
    amount DECIMAL(10,2) NOT NULL CHECK (amount > 0),
    currency TEXT DEFAULT 'CNY',
    
    -- 外部支付信息
    external_trade_no TEXT,
    external_transaction_id TEXT,
    
    status TEXT DEFAULT 'created' CHECK (status IN (
        'created', 'paying', 'paid', 'failed', 'cancelled', 'refunded'
    )),
    
    paid_at TIMESTAMP,
    failed_reason TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);

CREATE INDEX idx_payments_new_order ON payments_new(order_id);
CREATE INDEX idx_payments_new_external ON payments_new(external_trade_no);
CREATE INDEX idx_payments_new_status ON payments_new(status, created_at);

-- 8. 创建系统配置表
CREATE TABLE system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    data_type TEXT DEFAULT 'string' CHECK (data_type IN ('string', 'number', 'boolean', 'json')),
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_settings_key ON system_settings(setting_key);

-- 9. 创建审计日志表
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users_new(id),
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    old_values TEXT DEFAULT '{}',
    new_values TEXT DEFAULT '{}',
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user_time ON audit_logs(user_id, created_at);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_action ON audit_logs(action, created_at);

-- 10. 数据迁移逻辑

-- 迁移现有医生数据
INSERT INTO users_new (uuid, user_type, phone, email, name, status, created_at)
SELECT 
    'doctor_' || id || '_' || substr(license_no, -6),  -- 生成UUID
    'doctor',
    phone,
    email, 
    name,
    CASE WHEN status = 'active' THEN 'active' ELSE 'suspended' END,
    created_at
FROM doctors;

-- 迁移医生详细信息
INSERT INTO doctors_new (
    user_id, license_no, speciality, hospital, password_hash, 
    auth_salt, status, created_at, updated_at, version
)
SELECT 
    u.id,
    d.license_no,
    d.speciality,
    d.hospital,
    d.password_hash,
    d.auth_salt,
    d.status,
    d.created_at,
    d.updated_at,
    d.version
FROM doctors d
JOIN users_new u ON u.uuid = 'doctor_' || d.id || '_' || substr(d.license_no, -6);

-- 迁移处方数据到问诊记录
INSERT INTO consultations_new (
    uuid, patient_id, doctor_persona, chief_complaint, 
    symptoms_analysis, diagnosis, consultation_type, 
    status, created_at
)
SELECT DISTINCT
    'consultation_' || patient_id || '_' || strftime('%s', created_at),
    (SELECT id FROM users_new WHERE uuid = 'patient_' || p.patient_id LIMIT 1),
    'AI智能诊疗',
    COALESCE(p.symptoms, '患者问诊'),
    '{}',
    COALESCE(p.diagnosis, 'AI诊断分析'),
    'ai_primary',
    CASE 
        WHEN p.status = 'completed' THEN 'completed'
        ELSE 'active'
    END,
    p.created_at
FROM prescriptions p;

-- 先为患者创建用户记录
INSERT OR IGNORE INTO users_new (uuid, user_type, name, status, created_at)
SELECT DISTINCT
    'patient_' || patient_id,
    'patient', 
    COALESCE(patient_name, 'Patient_' || substr(patient_id, 1, 8)),
    'active',
    MIN(created_at)
FROM prescriptions
GROUP BY patient_id;

-- 迁移处方数据
INSERT INTO prescriptions_new (
    uuid, consultation_id, patient_id, prescriber_type, prescriber_id,
    herbs, status, reviewed_by, reviewed_at, review_notes,
    created_at, updated_at, version
)
SELECT 
    'prescription_' || p.id,
    c.id,
    u.id,
    CASE WHEN p.doctor_id IS NOT NULL THEN 'doctor' ELSE 'ai' END,
    du.id,
    COALESCE(p.doctor_prescription, p.ai_prescription),
    p.status,
    du.id,
    p.reviewed_at,
    p.doctor_notes,
    p.created_at,
    p.updated_at,
    p.version
FROM prescriptions p
JOIN users_new u ON u.uuid = 'patient_' || p.patient_id
JOIN consultations_new c ON c.uuid = 'consultation_' || p.patient_id || '_' || strftime('%s', p.created_at)
LEFT JOIN users_new du ON du.uuid = 'doctor_' || p.doctor_id || '_' || (
    SELECT substr(license_no, -6) FROM doctors WHERE id = p.doctor_id
);

-- 11. 创建触发器

-- 自动更新时间戳
CREATE TRIGGER trigger_users_updated_at 
    AFTER UPDATE ON users_new
    FOR EACH ROW
    BEGIN
        UPDATE users_new SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER trigger_prescriptions_updated_at 
    AFTER UPDATE ON prescriptions_new
    FOR EACH ROW
    BEGIN
        UPDATE prescriptions_new SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- 版本控制触发器
CREATE TRIGGER trigger_prescriptions_version
    AFTER UPDATE ON prescriptions_new
    FOR EACH ROW
    BEGIN
        UPDATE prescriptions_new SET version = version + 1 WHERE id = NEW.id;
    END;

-- 状态变更审计触发器
CREATE TRIGGER trigger_prescription_status_audit
    AFTER UPDATE OF status ON prescriptions_new
    FOR EACH ROW
    WHEN OLD.status != NEW.status
    BEGIN
        INSERT INTO audit_logs (
            user_id, action, resource_type, resource_id, 
            old_values, new_values, created_at
        ) VALUES (
            NEW.reviewed_by, 'status_change', 'prescription', NEW.uuid,
            json_object('status', OLD.status),
            json_object('status', NEW.status),
            CURRENT_TIMESTAMP
        );
    END;

-- 12. 插入初始系统配置
INSERT INTO system_settings (setting_key, setting_value, description, data_type) VALUES
('system_name', '中医AI智能问诊系统', '系统名称', 'string'),
('default_prescription_fee', '88.00', '基础诊疗费', 'number'),
('default_herb_fee', '120.00', '药材费用', 'number'),
('decoction_fee', '30.00', '代煎服务费', 'number'),
('max_prescription_duration', '30', '最大处方疗程天数', 'number'),
('enable_sms_notification', 'true', '启用短信通知', 'boolean'),
('payment_timeout_minutes', '30', '支付超时时间(分钟)', 'number');

COMMIT;

-- 验证迁移结果
SELECT 'Migration completed successfully. Summary:';
SELECT 'Users: ' || COUNT(*) FROM users_new;
SELECT 'Doctors: ' || COUNT(*) FROM doctors_new; 
SELECT 'Consultations: ' || COUNT(*) FROM consultations_new;
SELECT 'Prescriptions: ' || COUNT(*) FROM prescriptions_new;
SELECT 'System Settings: ' || COUNT(*) FROM system_settings;