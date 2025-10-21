-- ========================================
-- 统一认证系统迁移 - 第1步
-- 为doctors表添加user_id字段,关联unified_users
-- ========================================

-- 1. 添加user_id字段
ALTER TABLE doctors ADD COLUMN user_id VARCHAR(50);

-- 2. 创建索引
CREATE INDEX IF NOT EXISTS idx_doctors_user_id ON doctors(user_id);

-- 3. 添加外键约束(SQLite需要重建表来添加外键,暂时使用索引)
-- 注释: SQLite的ALTER TABLE不支持添加外键,需要时可以重建表

-- 4. 验证
SELECT
    COUNT(*) as total_doctors,
    COUNT(user_id) as doctors_with_user_id,
    COUNT(*) - COUNT(user_id) as doctors_without_user_id
FROM doctors;
