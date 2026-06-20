-- ========================================
-- 统一认证系统迁移 - 第3步
-- 迁移现有医生数据到unified_users
-- ========================================

-- 为现有医生创建unified_users记录和角色

-- 1. 为金大夫创建unified账户(如果还没有)
INSERT OR IGNORE INTO unified_users (
    global_user_id,
    username,
    email,
    phone_number,
    display_name,
    password_hash,
    salt,
    auth_methods,
    account_status,
    email_verified,
    security_level,
    registration_source
)
SELECT
    'usr_doctor_' || id,                          -- global_user_id
    COALESCE(license_no, 'doctor_' || id),        -- username (使用执业证号)
    email,                                         -- email
    phone,                                         -- phone_number
    name,                                          -- display_name
    COALESCE(password_hash, ''),                  -- password_hash (临时)
    CASE
        WHEN password_hash IS NOT NULL THEN substr(password_hash, 1, instr(password_hash, ':') - 1)
        ELSE hex(randomblob(16))
    END,                                          -- salt
    '["password"]',                               -- auth_methods
    CASE WHEN status = 'active' THEN 'active' ELSE 'inactive' END,  -- account_status
    CASE WHEN email IS NOT NULL THEN 1 ELSE 0 END,  -- email_verified
    'verified',                                   -- security_level (医生默认已验证)
    'doctor_migration'                            -- registration_source
FROM doctors
WHERE id IN (SELECT id FROM doctors WHERE status = 'active' LIMIT 5);  -- 先迁移前5个医生

-- 2. 为迁移的医生分配DOCTOR角色
INSERT OR IGNORE INTO user_roles_new (
    user_id,
    role_name,
    scope,
    is_primary,
    assigned_by,
    assigned_reason,
    is_active
)
SELECT
    'usr_doctor_' || d.id,          -- user_id
    'DOCTOR',                        -- role_name
    'global',                        -- scope
    1,                               -- is_primary
    'system',                        -- assigned_by
    '医生数据迁移',                  -- assigned_reason
    1                                -- is_active
FROM doctors d
WHERE d.status = 'active'
AND d.id IN (SELECT id FROM doctors WHERE status = 'active' LIMIT 5)
AND NOT EXISTS (
    SELECT 1 FROM user_roles_new ur
    WHERE ur.user_id = 'usr_doctor_' || d.id
);

-- 3. 更新doctors表的user_id关联
UPDATE doctors
SET user_id = 'usr_doctor_' || id
WHERE status = 'active'
AND id IN (SELECT id FROM doctors WHERE status = 'active' LIMIT 5);

-- 4. 验证迁移结果
SELECT '=== 迁移统计 ===' as title;

SELECT
    COUNT(*) as total_doctors,
    COUNT(user_id) as doctors_with_user_id,
    COUNT(*) - COUNT(user_id) as doctors_without_user_id
FROM doctors
WHERE status = 'active';

SELECT
    COUNT(*) as doctor_accounts_in_unified_users
FROM unified_users
WHERE global_user_id LIKE 'usr_doctor_%';

SELECT
    COUNT(*) as doctor_roles_assigned
FROM user_roles_new
WHERE role_name = 'DOCTOR' AND is_active = 1;

-- 5. 显示迁移的医生列表
SELECT
    d.id,
    d.name,
    d.license_no,
    d.user_id,
    uu.username,
    uu.account_status,
    ur.role_name
FROM doctors d
LEFT JOIN unified_users uu ON d.user_id = uu.global_user_id
LEFT JOIN user_roles_new ur ON uu.global_user_id = ur.user_id AND ur.is_active = 1
WHERE d.user_id IS NOT NULL
ORDER BY d.id;
