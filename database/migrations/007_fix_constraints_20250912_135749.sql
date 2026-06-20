-- TCM-AI 数据库约束修复
-- 生成时间: 2025-09-12T13:57:49.154773
-- 请在执行前备份数据库

-- 修复 user_history.sqlite
PRAGMA foreign_keys = ON;
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_phone_number ON users(phone_number);
CREATE INDEX IF NOT EXISTS idx_prescriptions_patient_id ON prescriptions(patient_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_conversation_id ON prescriptions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_status ON prescriptions(status);
CREATE INDEX IF NOT EXISTS idx_prescriptions_created_at ON prescriptions(created_at);
CREATE INDEX IF NOT EXISTS idx_consultations_patient_id ON consultations(patient_id);
CREATE INDEX IF NOT EXISTS idx_consultations_status ON consultations(status);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_created_at ON user_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

-- 修复 famous_doctors.sqlite
PRAGMA foreign_keys = ON;

-- 修复 cache.sqlite
PRAGMA foreign_keys = ON;

-- 修复 intelligent_cache.db
PRAGMA foreign_keys = ON;
