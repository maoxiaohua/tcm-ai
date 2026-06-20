-- ================================================================
-- 统一账户管理系统数据库架构设计
-- Version: 1.0
-- Author: TCM-AI架构师
-- Date: 2025-09-20
-- Description: 企业级账户权限管理系统，解决现有架构问题
-- ================================================================

-- 1. 统一用户身份表 (核心主表)
-- 解决问题：用户身份混乱，跨设备数据不一致
CREATE TABLE unified_users (
    -- 主键: 全局唯一用户ID
    global_user_id VARCHAR(50) PRIMARY KEY,  -- 格式: usr_YYYYMMDD_randomstring
    
    -- 基本信息
    username VARCHAR(100) UNIQUE NOT NULL,   -- 登录用户名
    email VARCHAR(255) UNIQUE,               -- 邮箱(可选)
    phone_number VARCHAR(20) UNIQUE,         -- 手机号(可选)
    display_name VARCHAR(100) NOT NULL,      -- 显示名称
    
    -- 认证信息
    password_hash VARCHAR(255) NOT NULL,     -- 密码哈希
    salt VARCHAR(100) NOT NULL,              -- 密码盐值
    auth_methods TEXT DEFAULT '["password"]', -- JSON: 认证方式列表
    
    -- 状态信息
    account_status VARCHAR(20) DEFAULT 'active', -- active, suspended, locked, deleted
    email_verified BOOLEAN DEFAULT false,
    phone_verified BOOLEAN DEFAULT false,
    
    -- 安全配置
    security_level VARCHAR(20) DEFAULT 'basic',  -- basic, enhanced, premium
    two_factor_enabled BOOLEAN DEFAULT false,
    login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP NULL,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL,
    password_changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 元数据
    registration_source VARCHAR(50) DEFAULT 'web',  -- web, mobile, api
    registration_ip VARCHAR(45),
    user_preferences TEXT DEFAULT '{}',  -- JSON: 用户偏好设置
    privacy_settings TEXT DEFAULT '{}',  -- JSON: 隐私设置
    
    -- 索引优化
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_phone (phone_number),
    INDEX idx_status (account_status),
    INDEX idx_created (created_at)
);

-- 2. 用户角色管理表
-- 解决问题：权限控制混乱，角色分配不规范
CREATE TABLE user_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(50) NOT NULL,
    role_name VARCHAR(50) NOT NULL,  -- SUPERADMIN, ADMIN, DOCTOR, PATIENT
    
    -- 权限范围
    scope VARCHAR(100) DEFAULT 'global',  -- global, department, specific
    scope_value VARCHAR(255),  -- 当scope为specific时的具体值
    
    -- 角色属性
    is_primary BOOLEAN DEFAULT false,  -- 是否为主要角色
    is_temporary BOOLEAN DEFAULT false, -- 是否为临时角色
    expires_at TIMESTAMP NULL,         -- 临时角色过期时间
    
    -- 分配信息
    assigned_by VARCHAR(50),  -- 分配者user_id
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_reason TEXT,     -- 分配原因
    
    -- 状态
    is_active BOOLEAN DEFAULT true,
    revoked_at TIMESTAMP NULL,
    revoked_by VARCHAR(50),
    revoked_reason TEXT,
    
    -- 外键约束
    FOREIGN KEY (user_id) REFERENCES unified_users(global_user_id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES unified_users(global_user_id),
    FOREIGN KEY (revoked_by) REFERENCES unified_users(global_user_id),
    
    -- 唯一约束: 同一用户的同一角色在同一范围内只能有一个激活状态
    UNIQUE(user_id, role_name, scope, scope_value, is_active),
    
    -- 索引
    INDEX idx_user_roles (user_id, role_name),
    INDEX idx_role_active (role_name, is_active),
    INDEX idx_expires (expires_at)
);

-- 3. 权限定义表
-- 解决问题：权限管理不统一，权限检查逻辑分散
CREATE TABLE permissions (
    permission_code VARCHAR(100) PRIMARY KEY,  -- 权限代码：模块:操作 如 consultation:create
    permission_name VARCHAR(200) NOT NULL,     -- 权限名称
    permission_category VARCHAR(50) NOT NULL,  -- 权限分类：user, medical, system, admin
    
    -- 权限描述
    description TEXT,
    risk_level VARCHAR(20) DEFAULT 'low',  -- low, medium, high, critical
    
    -- 权限属性
    is_active BOOLEAN DEFAULT true,
    requires_approval BOOLEAN DEFAULT false,  -- 是否需要审批
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_category (permission_category),
    INDEX idx_risk (risk_level)
);

-- 4. 角色权限映射表
-- 解决问题：角色权限关系不清晰
CREATE TABLE role_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name VARCHAR(50) NOT NULL,
    permission_code VARCHAR(100) NOT NULL,
    
    -- 权限配置
    is_granted BOOLEAN DEFAULT true,    -- 是否授予权限
    can_delegate BOOLEAN DEFAULT false, -- 是否可以委托给其他用户
    
    -- 条件限制
    conditions TEXT DEFAULT '{}',  -- JSON: 权限使用条件
    constraints TEXT DEFAULT '{}', -- JSON: 权限约束条件
    
    -- 审计信息
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(50),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (permission_code) REFERENCES permissions(permission_code),
    FOREIGN KEY (created_by) REFERENCES unified_users(global_user_id),
    FOREIGN KEY (updated_by) REFERENCES unified_users(global_user_id),
    
    UNIQUE(role_name, permission_code),
    INDEX idx_role_perms (role_name),
    INDEX idx_perm_roles (permission_code)
);

-- 5. 用户会话管理表 (统一会话)
-- 解决问题：多套会话系统，跨设备同步问题
CREATE TABLE unified_sessions (
    session_id VARCHAR(100) PRIMARY KEY,  -- 会话ID
    user_id VARCHAR(50) NOT NULL,         -- 用户ID
    
    -- 设备信息
    device_id VARCHAR(100),               -- 设备唯一标识
    device_type VARCHAR(50),              -- mobile, desktop, tablet, api
    device_name VARCHAR(200),             -- 设备名称
    
    -- 网络信息
    ip_address VARCHAR(45) NOT NULL,      -- IP地址
    user_agent TEXT,                      -- User-Agent
    geolocation TEXT DEFAULT '{}',        -- JSON: 地理位置信息
    
    -- 会话状态
    session_status VARCHAR(20) DEFAULT 'active',  -- active, expired, revoked
    login_method VARCHAR(50) DEFAULT 'password',  -- password, sms, biometric
    
    -- 时间管理
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    
    -- 安全信息
    login_success_count INTEGER DEFAULT 1,
    suspicious_activity_count INTEGER DEFAULT 0,
    risk_score DECIMAL(3,2) DEFAULT 0.0,  -- 0.0-1.0 风险评分
    
    -- 元数据
    session_data TEXT DEFAULT '{}',  -- JSON: 会话相关数据
    
    FOREIGN KEY (user_id) REFERENCES unified_users(global_user_id) ON DELETE CASCADE,
    
    INDEX idx_user_sessions (user_id, session_status),
    INDEX idx_device_sessions (device_id),
    INDEX idx_session_activity (last_activity_at),
    INDEX idx_session_expires (expires_at)
);

-- 6. 用户数据同步表
-- 解决问题：跨设备数据不同步
CREATE TABLE user_data_sync (
    sync_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    
    -- 数据类型
    data_type VARCHAR(50) NOT NULL,      -- consultation, prescription, profile, settings
    data_key VARCHAR(200) NOT NULL,      -- 数据标识
    
    -- 数据内容
    data_content TEXT NOT NULL,          -- JSON格式的数据内容
    data_version INTEGER DEFAULT 1,      -- 数据版本号
    
    -- 同步信息
    sync_status VARCHAR(20) DEFAULT 'pending',  -- pending, synced, conflict, error
    sync_source VARCHAR(50),             -- 数据来源设备/会话
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP NULL,
    
    -- 冲突解决
    conflict_resolution VARCHAR(50),     -- latest_wins, manual, merge
    conflict_data TEXT,                  -- 冲突时的数据
    
    FOREIGN KEY (user_id) REFERENCES unified_users(global_user_id) ON DELETE CASCADE,
    
    UNIQUE(user_id, data_type, data_key),
    INDEX idx_user_sync (user_id, data_type),
    INDEX idx_sync_status (sync_status),
    INDEX idx_sync_updated (updated_at)
);

-- 7. 安全审计日志表
-- 解决问题：缺乏完整的用户行为审计
CREATE TABLE security_audit_logs (
    log_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(50),                 -- 可为NULL（匿名操作）
    
    -- 事件信息
    event_type VARCHAR(100) NOT NULL,    -- login, logout, permission_change, data_access
    event_category VARCHAR(50) NOT NULL, -- auth, data, permission, security
    event_result VARCHAR(20) NOT NULL,   -- success, failure, warning
    
    -- 上下文信息
    ip_address VARCHAR(45),
    user_agent TEXT,
    session_id VARCHAR(100),
    
    -- 详细信息
    event_details TEXT DEFAULT '{}',     -- JSON: 事件详细信息
    affected_resources TEXT DEFAULT '[]', -- JSON: 受影响的资源列表
    
    -- 风险评估
    risk_level VARCHAR(20) DEFAULT 'low', -- low, medium, high, critical
    risk_score DECIMAL(3,2) DEFAULT 0.0,
    
    -- 时间戳
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 审计追踪
    audit_source VARCHAR(50) DEFAULT 'system',  -- system, admin, auto
    retention_period INTEGER DEFAULT 365,        -- 保留天数
    
    FOREIGN KEY (user_id) REFERENCES unified_users(global_user_id),
    FOREIGN KEY (session_id) REFERENCES unified_sessions(session_id),
    
    INDEX idx_user_audit (user_id, event_timestamp),
    INDEX idx_event_type (event_type, event_result),
    INDEX idx_risk_level (risk_level),
    INDEX idx_event_time (event_timestamp)
);

-- 8. 用户扩展配置表 (支持不同用户类型的特殊配置)
-- 解决问题：不同角色用户需要不同的配置字段
CREATE TABLE user_extended_profiles (
    user_id VARCHAR(50) PRIMARY KEY,
    
    -- 患者特有配置
    patient_config TEXT DEFAULT '{}',    -- JSON: 健康档案、过敏史等
    
    -- 医生特有配置
    doctor_config TEXT DEFAULT '{}',     -- JSON: 执业证号、专科、工作医院等
    
    -- 管理员特有配置
    admin_config TEXT DEFAULT '{}',      -- JSON: 管理范围、权限级别等
    
    -- 通用扩展配置
    custom_fields TEXT DEFAULT '{}',     -- JSON: 自定义字段
    integration_configs TEXT DEFAULT '{}', -- JSON: 第三方集成配置
    
    -- 版本控制
    config_version INTEGER DEFAULT 1,
    last_updated_by VARCHAR(50),
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES unified_users(global_user_id) ON DELETE CASCADE,
    FOREIGN KEY (last_updated_by) REFERENCES unified_users(global_user_id),
    
    INDEX idx_config_version (config_version),
    INDEX idx_updated (updated_at)
);

-- ================================================================
-- 数据迁移准备：创建视图兼容现有系统
-- ================================================================

-- 兼容视图：users表 (向后兼容)
CREATE VIEW users AS
SELECT 
    global_user_id as user_id,
    username,
    email,
    phone_number,
    display_name as nickname,
    CASE 
        WHEN EXISTS (SELECT 1 FROM user_roles WHERE user_id = global_user_id AND role_name = 'PATIENT' AND is_active = true) THEN 'patient'
        WHEN EXISTS (SELECT 1 FROM user_roles WHERE user_id = global_user_id AND role_name = 'DOCTOR' AND is_active = true) THEN 'doctor'
        WHEN EXISTS (SELECT 1 FROM user_roles WHERE user_id = global_user_id AND role_name = 'ADMIN' AND is_active = true) THEN 'admin'
        WHEN EXISTS (SELECT 1 FROM user_roles WHERE user_id = global_user_id AND role_name = 'SUPERADMIN' AND is_active = true) THEN 'superadmin'
        ELSE 'patient'
    END as role,
    CASE 
        WHEN account_status = 'active' THEN 1 
        ELSE 0 
    END as is_active,
    created_at,
    last_login_at as last_active,
    updated_at
FROM unified_users;

-- 兼容视图：user_sessions表 (向后兼容)
CREATE VIEW user_sessions AS
SELECT 
    session_id as session_token,
    user_id,
    created_at,
    expires_at,
    ip_address,
    user_agent,
    last_activity_at as last_activity,
    CASE 
        WHEN session_status = 'active' THEN 1 
        ELSE 0 
    END as is_active
FROM unified_sessions;

-- ================================================================
-- 初始化基础数据
-- ================================================================

-- 初始化权限定义
INSERT INTO permissions (permission_code, permission_name, permission_category, description, risk_level) VALUES
-- 患者权限
('consultation:create', '创建问诊', 'medical', '患者可以发起新的医疗问诊', 'low'),
('consultation:view_own', '查看个人问诊', 'medical', '患者可以查看自己的问诊记录', 'low'),
('prescription:view_own', '查看个人处方', 'medical', '患者可以查看自己的处方信息', 'low'),
('profile:edit_own', '编辑个人资料', 'user', '患者可以编辑自己的个人资料', 'low'),
('payment:create', '创建支付订单', 'financial', '患者可以创建支付订单', 'medium'),

-- 医生权限
('consultation:view_assigned', '查看分配问诊', 'medical', '医生可以查看分配给自己的问诊', 'medium'),
('prescription:create', '开具处方', 'medical', '医生可以为患者开具处方', 'high'),
('prescription:edit', '编辑处方', 'medical', '医生可以编辑处方内容', 'high'),
('patient:view_history', '查看患者历史', 'medical', '医生可以查看患者的医疗历史', 'medium'),
('decision_tree:create', '创建决策树', 'tools', '医生可以创建诊疗决策树', 'medium'),
('thinking_library:manage', '管理思维库', 'tools', '医生可以管理诊疗思维库', 'medium'),

-- 管理员权限
('user:view_all', '查看所有用户', 'admin', '管理员可以查看所有用户信息', 'medium'),
('user:edit_all', '编辑所有用户', 'admin', '管理员可以编辑所有用户信息', 'high'),
('consultation:view_all', '查看所有问诊', 'admin', '管理员可以查看所有问诊记录', 'high'),
('prescription:view_all', '查看所有处方', 'admin', '管理员可以查看所有处方记录', 'high'),
('audit:view', '查看审计日志', 'admin', '管理员可以查看系统审计日志', 'medium'),
('system:monitor', '系统监控', 'admin', '管理员可以监控系统状态', 'medium'),

-- 超级管理员权限
('system:config', '系统配置', 'system', '超级管理员可以修改系统配置', 'critical'),
('permission:manage', '权限管理', 'system', '超级管理员可以管理用户权限', 'critical'),
('database:access', '数据库访问', 'system', '超级管理员可以直接访问数据库', 'critical'),
('security:config', '安全配置', 'system', '超级管理员可以修改安全配置', 'critical');

-- 初始化角色权限映射
INSERT INTO role_permissions (role_name, permission_code, is_granted, can_delegate) VALUES
-- 患者角色权限
('PATIENT', 'consultation:create', true, false),
('PATIENT', 'consultation:view_own', true, false),
('PATIENT', 'prescription:view_own', true, false),
('PATIENT', 'profile:edit_own', true, false),
('PATIENT', 'payment:create', true, false),

-- 医生角色权限 (包含患者权限)
('DOCTOR', 'consultation:create', true, false),
('DOCTOR', 'consultation:view_own', true, false),
('DOCTOR', 'consultation:view_assigned', true, false),
('DOCTOR', 'prescription:view_own', true, false),
('DOCTOR', 'prescription:create', true, false),
('DOCTOR', 'prescription:edit', true, false),
('DOCTOR', 'profile:edit_own', true, false),
('DOCTOR', 'patient:view_history', true, false),
('DOCTOR', 'decision_tree:create', true, false),
('DOCTOR', 'thinking_library:manage', true, false),

-- 管理员角色权限 (包含医生权限)
('ADMIN', 'consultation:create', true, false),
('ADMIN', 'consultation:view_own', true, false),
('ADMIN', 'consultation:view_assigned', true, false),
('ADMIN', 'consultation:view_all', true, false),
('ADMIN', 'prescription:view_own', true, false),
('ADMIN', 'prescription:create', true, false),
('ADMIN', 'prescription:edit', true, false),
('ADMIN', 'prescription:view_all', true, false),
('ADMIN', 'profile:edit_own', true, false),
('ADMIN', 'patient:view_history', true, false),
('ADMIN', 'decision_tree:create', true, false),
('ADMIN', 'thinking_library:manage', true, false),
('ADMIN', 'user:view_all', true, false),
('ADMIN', 'user:edit_all', true, true),
('ADMIN', 'audit:view', true, false),
('ADMIN', 'system:monitor', true, false),

-- 超级管理员角色权限 (所有权限)
('SUPERADMIN', 'consultation:create', true, true),
('SUPERADMIN', 'consultation:view_own', true, true),
('SUPERADMIN', 'consultation:view_assigned', true, true),
('SUPERADMIN', 'consultation:view_all', true, true),
('SUPERADMIN', 'prescription:view_own', true, true),
('SUPERADMIN', 'prescription:create', true, true),
('SUPERADMIN', 'prescription:edit', true, true),
('SUPERADMIN', 'prescription:view_all', true, true),
('SUPERADMIN', 'profile:edit_own', true, true),
('SUPERADMIN', 'patient:view_history', true, true),
('SUPERADMIN', 'decision_tree:create', true, true),
('SUPERADMIN', 'thinking_library:manage', true, true),
('SUPERADMIN', 'user:view_all', true, true),
('SUPERADMIN', 'user:edit_all', true, true),
('SUPERADMIN', 'audit:view', true, true),
('SUPERADMIN', 'system:monitor', true, true),
('SUPERADMIN', 'system:config', true, true),
('SUPERADMIN', 'permission:manage', true, true),
('SUPERADMIN', 'database:access', true, true),
('SUPERADMIN', 'security:config', true, true);

-- ================================================================
-- 创建必要的触发器和函数
-- ================================================================

-- 触发器：自动更新updated_at字段
CREATE TRIGGER update_unified_users_timestamp 
    AFTER UPDATE ON unified_users
    FOR EACH ROW 
    BEGIN
        UPDATE unified_users SET updated_at = CURRENT_TIMESTAMP WHERE global_user_id = NEW.global_user_id;
    END;

CREATE TRIGGER update_user_extended_profiles_timestamp 
    AFTER UPDATE ON user_extended_profiles
    FOR EACH ROW 
    BEGIN
        UPDATE user_extended_profiles SET updated_at = CURRENT_TIMESTAMP WHERE user_id = NEW.user_id;
    END;

-- 触发器：记录重要安全事件
CREATE TRIGGER log_role_changes 
    AFTER INSERT ON user_roles
    FOR EACH ROW 
    BEGIN
        INSERT INTO security_audit_logs 
        (log_id, user_id, event_type, event_category, event_result, event_details, risk_level, audit_source)
        VALUES 
        (
            'audit_' || strftime('%Y%m%d%H%M%S', 'now') || '_' || substr(lower(hex(randomblob(8))), 1, 8),
            NEW.user_id,
            'role_assigned',
            'permission',
            'success',
            json_object('role', NEW.role_name, 'scope', NEW.scope, 'assigned_by', NEW.assigned_by),
            'medium',
            'system'
        );
    END;

-- ================================================================
-- 索引优化
-- ================================================================

-- 复合索引优化查询性能
CREATE INDEX idx_user_roles_composite ON user_roles(user_id, role_name, is_active);
CREATE INDEX idx_sessions_user_status ON unified_sessions(user_id, session_status, last_activity_at);
CREATE INDEX idx_audit_user_category ON security_audit_logs(user_id, event_category, event_timestamp);
CREATE INDEX idx_sync_user_type ON user_data_sync(user_id, data_type, sync_status);

-- ================================================================
-- 完成初始化
-- ================================================================

-- 插入迁移标记
INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('unified_account_system_version', '1.0', '统一账户系统版本'),
('migration_unified_accounts', 'completed', '统一账户系统迁移状态'),
('last_migration_date', datetime('now'), '最后迁移时间');

COMMIT;