-- TCM-AI 外键约束补强
-- 生成时间: 2025-09-12
-- 请在执行前备份数据库 
-- 注意: 添加外键需要重建表，操作较危险，建议分步执行

-- 启用外键约束检查
PRAGMA foreign_keys = ON;

-- =============================================================================
-- 第一步: 修复 prescriptions 表外键关系
-- =============================================================================

-- 检查现有数据完整性
-- 这些查询会显示数据不一致的记录，执行前请检查
-- SELECT * FROM prescriptions WHERE patient_id NOT IN (SELECT user_id FROM users);
-- SELECT * FROM prescriptions WHERE doctor_id NOT IN (SELECT id FROM doctors) AND doctor_id IS NOT NULL;

-- 由于SQLite不支持直接添加外键，需要重建表
-- 暂时跳过重建操作，优先处理其他约束

-- =============================================================================  
-- 第二步: 添加唯一约束和检查约束
-- =============================================================================

-- 为用户表添加唯一约束（如果不存在）
-- 注意: 这些约束已在表创建时设置，此处仅作记录

-- 用户邮箱唯一性检查
-- CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email) WHERE email IS NOT NULL;

-- 用户名唯一性检查  
-- CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique ON users(username) WHERE username IS NOT NULL;

-- 手机号唯一性检查
-- CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_unique ON users(phone_number) WHERE phone_number IS NOT NULL;

-- =============================================================================
-- 第三步: 数据完整性触发器
-- =============================================================================

-- 创建触发器确保处方-患者关系完整性
CREATE TRIGGER IF NOT EXISTS check_prescription_patient
    BEFORE INSERT ON prescriptions
    FOR EACH ROW
    WHEN NEW.patient_id IS NOT NULL
    BEGIN
        SELECT CASE
            WHEN (SELECT user_id FROM users WHERE user_id = NEW.patient_id) IS NULL
            THEN RAISE(ABORT, '患者ID不存在: ' || NEW.patient_id)
        END;
    END;

-- 创建触发器确保订单-处方关系完整性
CREATE TRIGGER IF NOT EXISTS check_order_prescription
    BEFORE INSERT ON orders
    FOR EACH ROW  
    WHEN NEW.prescription_id IS NOT NULL
    BEGIN
        SELECT CASE
            WHEN (SELECT id FROM prescriptions WHERE id = NEW.prescription_id) IS NULL
            THEN RAISE(ABORT, '处方ID不存在: ' || NEW.prescription_id)
        END;
    END;

-- 创建触发器确保会话-用户关系完整性
CREATE TRIGGER IF NOT EXISTS check_session_user
    BEFORE INSERT ON user_sessions
    FOR EACH ROW
    WHEN NEW.user_id IS NOT NULL  
    BEGIN
        SELECT CASE
            WHEN (SELECT user_id FROM users WHERE user_id = NEW.user_id) IS NULL
            THEN RAISE(ABORT, '用户ID不存在: ' || NEW.user_id)
        END;
    END;

-- =============================================================================
-- 第四步: 清理孤立数据（可选 - 谨慎执行）
-- =============================================================================

-- 以下SQL会清理不一致的数据，执行前请谨慎评估

-- 清理没有对应用户的处方记录（警告：会丢失数据）
-- DELETE FROM prescriptions WHERE patient_id NOT IN (SELECT user_id FROM users);

-- 清理没有对应处方的订单记录（警告：会丢失数据）
-- DELETE FROM orders WHERE prescription_id IS NOT NULL AND prescription_id NOT IN (SELECT id FROM prescriptions);

-- 清理没有对应用户的会话记录（警告：会丢失大量数据）
-- DELETE FROM user_sessions WHERE user_id NOT IN (SELECT user_id FROM users);

-- =============================================================================
-- 第五步: 验证数据完整性
-- =============================================================================

-- 检查处方-用户关系
-- SELECT 'prescription-user violations: ' || COUNT(*) FROM prescriptions WHERE patient_id NOT IN (SELECT user_id FROM users);

-- 检查订单-处方关系
-- SELECT 'order-prescription violations: ' || COUNT(*) FROM orders WHERE prescription_id IS NOT NULL AND prescription_id NOT IN (SELECT id FROM prescriptions);

-- 检查会话-用户关系  
-- SELECT 'session-user violations: ' || COUNT(*) FROM user_sessions WHERE user_id NOT IN (SELECT user_id FROM users);

-- =============================================================================
-- 执行完成标记
-- =============================================================================

INSERT OR REPLACE INTO system_settings (key, value) VALUES ('foreign_keys_migration', '008_completed_' || datetime('now'));

-- 记录迁移日志
INSERT INTO audit_logs (action, resource_type, details, created_at) 
VALUES ('MIGRATION', 'DATABASE', '外键约束补强迁移完成', datetime('now'));