-- TCM-AI 认证系统统一迁移
-- 生成时间: 2025-09-12T14:23:17.169587
-- 执行前请备份数据库!

-- 第一步: 扩展users表结构
ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'patient';
ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1;
ALTER TABLE users ADD COLUMN updated_at TEXT;

-- 第二步: 迁移admin_accounts数据到users表
INSERT INTO users (
            user_id, username, email, password_hash, nickname,
            registration_type, role, is_active, created_at, updated_at, is_verified
        )
        SELECT 
            user_id, username, email, password_hash, username as nickname,
            'authenticated' as registration_type, role, is_active, 
            created_at, updated_at, 1 as is_verified
        FROM admin_accounts
        WHERE user_id NOT IN (SELECT user_id FROM users);

-- 第三步: 更新现有users表用户角色
UPDATE users SET role = 'patient' WHERE role IS NULL OR role = '';

-- 第四步: 优化索引
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- 第五步: 数据验证
-- SELECT COUNT(*) as total_users FROM users;
-- SELECT role, COUNT(*) FROM users GROUP BY role;

-- 第六步: 备份admin_accounts表后删除 (谨慎执行)
-- DROP TABLE admin_accounts;
