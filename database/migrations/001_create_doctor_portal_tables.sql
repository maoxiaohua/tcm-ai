-- 医生客户端闭环系统数据库表创建脚本
-- 创建时间: 2025-08-26
-- 版本: v1.0

-- 1. 医生表
CREATE TABLE IF NOT EXISTS doctors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    license_no VARCHAR(50) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    email VARCHAR(100) UNIQUE,
    speciality VARCHAR(100),
    hospital VARCHAR(200),
    auth_token VARCHAR(255),
    password_hash VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- 2. 处方表
CREATE TABLE IF NOT EXISTS prescriptions (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(100) NOT NULL,
    conversation_id VARCHAR(100) NOT NULL,
    patient_name VARCHAR(100),
    patient_phone VARCHAR(20),
    symptoms TEXT,
    diagnosis TEXT,
    ai_prescription TEXT NOT NULL,
    doctor_prescription TEXT,
    doctor_id INTEGER REFERENCES doctors(id),
    doctor_notes TEXT,
    status VARCHAR(30) DEFAULT 'pending' CHECK (status IN (
        'pending', 'doctor_reviewing', 'approved', 'rejected', 
        'patient_confirmed', 'paid', 'decoction_submitted', 
        'processing', 'shipped', 'delivered', 'completed'
    )),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    confirmed_at TIMESTAMP,
    version INTEGER DEFAULT 1
);

-- 3. 订单表
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_no VARCHAR(50) UNIQUE NOT NULL,
    prescription_id INTEGER REFERENCES prescriptions(id),
    patient_id VARCHAR(100) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(20) CHECK (payment_method IN ('alipay', 'wechat')),
    payment_status VARCHAR(20) DEFAULT 'pending' CHECK (payment_status IN (
        'pending', 'paid', 'failed', 'refunded', 'cancelled'
    )),
    payment_time TIMESTAMP,
    payment_transaction_id VARCHAR(100),
    decoction_required BOOLEAN DEFAULT false,
    shipping_name VARCHAR(100),
    shipping_phone VARCHAR(20),
    shipping_address TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 代煎订单表
CREATE TABLE IF NOT EXISTS decoction_orders (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    provider_id VARCHAR(50),
    provider_name VARCHAR(100),
    decoction_order_no VARCHAR(100),
    status VARCHAR(20) DEFAULT 'submitted' CHECK (status IN (
        'submitted', 'confirmed', 'processing', 'completed', 'shipped', 'delivered'
    )),
    tracking_no VARCHAR(100),
    estimated_delivery DATE,
    actual_delivery_date DATE,
    provider_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. 处方变更记录表
CREATE TABLE IF NOT EXISTS prescription_changes (
    id SERIAL PRIMARY KEY,
    prescription_id INTEGER REFERENCES prescriptions(id),
    changed_by INTEGER REFERENCES doctors(id),
    change_type VARCHAR(20) CHECK (change_type IN ('modified', 'approved', 'rejected')),
    original_prescription TEXT,
    new_prescription TEXT,
    change_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_prescriptions_status ON prescriptions(status);
CREATE INDEX IF NOT EXISTS idx_prescriptions_patient ON prescriptions(patient_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_doctor ON prescriptions(doctor_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_created ON prescriptions(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(payment_status);
CREATE INDEX IF NOT EXISTS idx_orders_patient ON orders(patient_id);
CREATE INDEX IF NOT EXISTS idx_decoction_status ON decoction_orders(status);

-- 插入测试医生数据
INSERT INTO doctors (name, license_no, phone, email, speciality, hospital, password_hash) VALUES 
('张仲景', 'TCM001', '13800138001', 'zhangzhongjing@tcm.com', '伤寒杂病', '仲景医院', '$2b$12$example_hash_1'),
('李时珍', 'TCM002', '13800138002', 'lishizhen@tcm.com', '本草方剂', '本草医院', '$2b$12$example_hash_2'),
('华佗', 'TCM003', '13800138003', 'huatuo@tcm.com', '外科手术', '华佗医院', '$2b$12$example_hash_3')
ON CONFLICT (license_no) DO NOTHING;