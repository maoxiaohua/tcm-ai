# 中医AI问诊系统 - 数据库架构重设计

## 1. 核心设计原则

### 1.1 ACID 合规性
- 所有事务必须保证原子性、一致性、隔离性、持久性
- 关键业务逻辑使用数据库约束而非应用层校验
- 外键约束确保数据完整性

### 1.2 数据分离与职责清晰
- 用户管理表（患者、医生、管理员）
- 医疗业务表（问诊、处方、审查）
- 系统运营表（支付、物流、统计）
- 配置管理表（系统设置、权限）

### 1.3 可扩展性设计
- 预留字段用于功能扩展
- 版本控制字段追踪数据变更
- 软删除机制保护历史数据
- 分表策略应对大数据量

## 2. 重新设计的表结构

### 2.1 用户管理模块

#### users 表 (统一用户表)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,                    -- UUID 作为外部标识
    user_type TEXT NOT NULL CHECK (user_type IN ('patient', 'doctor', 'admin')),
    phone TEXT,
    email TEXT,
    name TEXT,
    avatar_url TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    metadata TEXT,                                 -- JSON 存储扩展信息
    version INTEGER DEFAULT 1
);

CREATE UNIQUE INDEX idx_users_phone ON users(phone) WHERE phone IS NOT NULL;
CREATE UNIQUE INDEX idx_users_email ON users(email) WHERE email IS NOT NULL;
CREATE INDEX idx_users_type_status ON users(user_type, status);
```

#### patients 表 (患者详细信息)
```sql
CREATE TABLE patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    birth_date DATE,
    gender TEXT CHECK (gender IN ('male', 'female', 'other')),
    height REAL,
    weight REAL,
    blood_type TEXT,
    allergies TEXT,                                -- JSON 数组存储过敏信息
    medical_history TEXT,                          -- JSON 存储病史
    emergency_contact TEXT,                        -- JSON 存储紧急联系人
    preferences TEXT,                              -- JSON 存储偏好设置
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);

CREATE UNIQUE INDEX idx_patients_user_id ON patients(user_id);
```

#### doctors 表 (医生详细信息)
```sql
CREATE TABLE doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    license_no TEXT UNIQUE NOT NULL,               -- 执业证书号
    license_expiry DATE,
    speciality TEXT NOT NULL,
    hospital TEXT,
    department TEXT,
    title TEXT,                                    -- 职称
    years_experience INTEGER,
    education TEXT,
    research_areas TEXT,                           -- JSON 数组
    password_hash TEXT NOT NULL,
    auth_salt TEXT NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'pending_review')),
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);

CREATE UNIQUE INDEX idx_doctors_license ON doctors(license_no);
CREATE UNIQUE INDEX idx_doctors_user_id ON doctors(user_id);
CREATE INDEX idx_doctors_speciality ON doctors(speciality);
```

### 2.2 医疗业务模块

#### consultations 表 (问诊记录)
```sql
CREATE TABLE consultations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,                    -- 外部引用UUID
    patient_id INTEGER NOT NULL REFERENCES users(id),
    doctor_persona TEXT,                           -- AI医生角色
    chief_complaint TEXT,                          -- 主诉
    present_illness TEXT,                          -- 现病史
    past_history TEXT,                             -- 既往史
    family_history TEXT,                           -- 家族史
    physical_exam TEXT,                            -- 体格检查
    symptoms_analysis TEXT,                        -- 症状分析(JSON)
    tcm_syndrome TEXT,                             -- 中医证候
    diagnosis TEXT,                                -- 诊断
    conversation_log TEXT,                         -- 对话记录(JSON)
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

CREATE UNIQUE INDEX idx_consultations_uuid ON consultations(uuid);
CREATE INDEX idx_consultations_patient ON consultations(patient_id, status);
CREATE INDEX idx_consultations_date ON consultations(created_at);
```

#### prescriptions 表 (处方管理)
```sql
CREATE TABLE prescriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    consultation_id INTEGER NOT NULL REFERENCES consultations(id),
    patient_id INTEGER NOT NULL REFERENCES users(id),
    prescriber_type TEXT NOT NULL CHECK (prescriber_type IN ('ai', 'doctor')),
    prescriber_id INTEGER REFERENCES users(id),    -- 如果是医生开具
    
    -- 处方内容
    herbs TEXT NOT NULL,                           -- JSON 数组存储药材信息
    dosage_instructions TEXT,                      -- 用法用量
    treatment_duration INTEGER,                    -- 疗程天数
    special_instructions TEXT,                     -- 特殊说明
    
    -- 状态管理
    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending', 'doctor_reviewing', 'approved', 'rejected', 
        'patient_confirmed', 'paid', 'dispensing', 'shipped', 'completed'
    )),
    
    -- 审查信息
    reviewed_by INTEGER REFERENCES users(id),
    reviewed_at TIMESTAMP,
    review_notes TEXT,
    
    -- 患者确认
    patient_confirmed_at TIMESTAMP,
    patient_notes TEXT,
    
    -- 版本控制
    parent_prescription_id INTEGER REFERENCES prescriptions(id),  -- 修改版本的父处方
    revision_reason TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    
    -- 确保处方内容不为空
    CHECK (length(herbs) > 0)
);

CREATE UNIQUE INDEX idx_prescriptions_uuid ON prescriptions(uuid);
CREATE INDEX idx_prescriptions_consultation ON prescriptions(consultation_id);
CREATE INDEX idx_prescriptions_patient ON prescriptions(patient_id, status);
CREATE INDEX idx_prescriptions_doctor_review ON prescriptions(reviewed_by, status);
CREATE INDEX idx_prescriptions_status ON prescriptions(status, created_at);
```

### 2.3 系统运营模块

#### orders 表 (订单管理)
```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT UNIQUE NOT NULL,                -- 订单号
    prescription_id INTEGER NOT NULL REFERENCES prescriptions(id),
    patient_id INTEGER NOT NULL REFERENCES users(id),
    
    -- 订单内容
    items TEXT NOT NULL,                          -- JSON 数组：药材、代煎服务等
    subtotal_amount DECIMAL(10,2) NOT NULL,       -- 药材费用
    service_amount DECIMAL(10,2) DEFAULT 0,       -- 服务费（代煎等）
    shipping_amount DECIMAL(10,2) DEFAULT 0,      -- 运费
    total_amount DECIMAL(10,2) NOT NULL,          -- 总金额
    
    -- 配送信息
    needs_decoction BOOLEAN DEFAULT FALSE,       -- 是否需要代煎
    shipping_address TEXT,                        -- JSON 存储收货地址
    
    -- 状态管理
    status TEXT DEFAULT 'created' CHECK (status IN (
        'created', 'paid', 'processing', 'shipping', 'delivered', 'completed', 'cancelled'
    )),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,                         -- 订单过期时间
    version INTEGER DEFAULT 1,
    
    CHECK (total_amount >= 0),
    CHECK (subtotal_amount >= 0)
);

CREATE UNIQUE INDEX idx_orders_order_no ON orders(order_no);
CREATE INDEX idx_orders_prescription ON orders(prescription_id);
CREATE INDEX idx_orders_patient ON orders(patient_id, status);
CREATE INDEX idx_orders_status ON orders(status, created_at);
```

#### payments 表 (支付管理)
```sql
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    payment_method TEXT NOT NULL CHECK (payment_method IN ('alipay', 'wechat', 'bank')),
    payment_provider TEXT,                        -- 支付提供商
    
    amount DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'CNY',
    
    -- 外部支付信息
    external_trade_no TEXT,                       -- 外部交易号
    external_transaction_id TEXT,                 -- 外部事务ID
    
    status TEXT DEFAULT 'created' CHECK (status IN (
        'created', 'paying', 'paid', 'failed', 'cancelled', 'refunded'
    )),
    
    paid_at TIMESTAMP,
    failed_reason TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    
    CHECK (amount > 0)
);

CREATE INDEX idx_payments_order ON payments(order_id);
CREATE INDEX idx_payments_external ON payments(external_trade_no);
CREATE INDEX idx_payments_status ON payments(status, created_at);
```

### 2.4 系统配置模块

#### system_settings 表 (系统配置)
```sql
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
```

#### audit_logs 表 (审计日志)
```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,                         -- 操作类型
    resource_type TEXT NOT NULL,                  -- 资源类型
    resource_id TEXT,                             -- 资源ID
    old_values TEXT,                              -- 修改前的值(JSON)
    new_values TEXT,                              -- 修改后的值(JSON)
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user_time ON audit_logs(user_id, created_at);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_action ON audit_logs(action, created_at);
```

## 3. 数据库触发器（确保数据一致性）

### 3.1 自动更新时间戳
```sql
-- 通用的 updated_at 触发器模板
CREATE TRIGGER trigger_users_updated_at 
    AFTER UPDATE ON users
    FOR EACH ROW
    BEGIN
        UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- 为所有主要表创建类似触发器
```

### 3.2 版本控制触发器
```sql
CREATE TRIGGER trigger_prescriptions_version
    AFTER UPDATE ON prescriptions
    FOR EACH ROW
    BEGIN
        UPDATE prescriptions SET version = version + 1 WHERE id = NEW.id;
    END;
```

### 3.3 状态变更审计触发器
```sql
CREATE TRIGGER trigger_prescription_status_audit
    AFTER UPDATE OF status ON prescriptions
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
```

## 4. 数据迁移策略

### 4.1 现有数据迁移脚本
```sql
-- 1. 创建新表结构
-- 2. 迁移现有用户数据
-- 3. 迁移现有处方数据
-- 4. 验证数据完整性
-- 5. 切换到新结构
```

## 5. 性能优化建议

### 5.1 索引策略
- 为所有外键创建索引
- 为常用查询条件创建复合索引
- 定期维护索引统计信息

### 5.2 查询优化
- 使用预编译语句防止SQL注入
- 合理使用事务边界
- 避免N+1查询问题

### 5.3 数据归档
- 定期归档历史数据
- 实现数据生命周期管理
- 建立数据备份恢复机制

## 6. 安全考虑

### 6.1 数据加密
- 敏感信息字段加密存储
- 传输过程SSL加密
- 数据库连接加密

### 6.2 访问控制
- 基于角色的数据访问控制
- API级别的权限验证
- 数据脱敏处理

## 7. 监控与告警

### 7.1 数据库监控
- 连接池状态监控
- 慢查询日志分析
- 数据库锁等待监控

### 7.2 业务监控
- 关键业务指标监控
- 数据一致性检查
- 异常数据告警