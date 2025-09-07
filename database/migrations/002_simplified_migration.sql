-- 简化版数据库迁移脚本
BEGIN TRANSACTION;

-- 1. 创建系统配置表
CREATE TABLE IF NOT EXISTS system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    data_type TEXT DEFAULT 'string' CHECK (data_type IN ('string', 'number', 'boolean', 'json')),
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_settings_key ON system_settings(setting_key);

-- 2. 创建审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    user_type TEXT DEFAULT 'patient' CHECK (user_type IN ('patient', 'doctor', 'admin')),
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    old_values TEXT DEFAULT '{}',
    new_values TEXT DEFAULT '{}',
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_user_time ON audit_logs(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action, created_at);

-- 3. 为现有处方表添加UUID列（如果不存在）
ALTER TABLE prescriptions ADD COLUMN uuid TEXT;

-- 4. 为处方生成UUID
UPDATE prescriptions SET uuid = 'prescription_' || id WHERE uuid IS NULL;

-- 5. 添加处方类型列
ALTER TABLE prescriptions ADD COLUMN prescriber_type TEXT DEFAULT 'ai';
UPDATE prescriptions SET prescriber_type = CASE 
    WHEN doctor_id IS NOT NULL THEN 'doctor' 
    ELSE 'ai' 
END;

-- 6. 添加用户类型到doctors表
ALTER TABLE doctors ADD COLUMN user_type TEXT DEFAULT 'doctor';

-- 7. 创建状态变更审计触发器
CREATE TRIGGER IF NOT EXISTS trigger_prescription_status_audit
    AFTER UPDATE OF status ON prescriptions
    FOR EACH ROW
    WHEN OLD.status != NEW.status
    BEGIN
        INSERT INTO audit_logs (
            user_id, user_type, action, resource_type, resource_id, 
            old_values, new_values, created_at
        ) VALUES (
            COALESCE(NEW.doctor_id, NEW.patient_id), 
            CASE WHEN NEW.doctor_id IS NOT NULL THEN 'doctor' ELSE 'patient' END,
            'status_change', 'prescription', NEW.uuid,
            json_object('status', OLD.status),
            json_object('status', NEW.status),
            CURRENT_TIMESTAMP
        );
    END;

-- 8. 插入初始系统配置
INSERT OR IGNORE INTO system_settings (setting_key, setting_value, description, data_type) VALUES
('system_name', '中医AI智能问诊系统', '系统名称', 'string'),
('default_prescription_fee', '88.00', '基础诊疗费', 'number'),
('default_herb_fee', '120.00', '药材费用', 'number'),
('decoction_fee', '30.00', '代煎服务费', 'number'),
('max_prescription_duration', '30', '最大处方疗程天数', 'number'),
('enable_sms_notification', 'true', '启用短信通知', 'boolean'),
('payment_timeout_minutes', '30', '支付超时时间(分钟)', 'number'),
('doctor_portal_url', '/doctor', '医生端访问地址', 'string'),
('patient_portal_url', '/', '患者端访问地址', 'string'),
('admin_portal_url', '/admin', '管理端访问地址', 'string');

COMMIT;

-- 验证结果
SELECT 'Migration completed. Tables created:';
SELECT 'System Settings: ' || COUNT(*) FROM system_settings;
SELECT 'Existing Prescriptions: ' || COUNT(*) FROM prescriptions WHERE uuid IS NOT NULL;
SELECT 'Existing Doctors: ' || COUNT(*) FROM doctors;