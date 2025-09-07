-- SQLite版本：医生客户端闭环系统数据库表创建脚本

-- 1. 医生表
CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    license_no TEXT UNIQUE NOT NULL,
    phone TEXT UNIQUE,
    email TEXT UNIQUE,
    speciality TEXT,
    hospital TEXT,
    auth_token TEXT,
    password_hash TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    last_login TEXT
);

-- 2. 处方表
CREATE TABLE IF NOT EXISTS prescriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    patient_name TEXT,
    patient_phone TEXT,
    symptoms TEXT,
    diagnosis TEXT,
    ai_prescription TEXT NOT NULL,
    doctor_prescription TEXT,
    doctor_id INTEGER,
    doctor_notes TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now')),
    reviewed_at TEXT,
    confirmed_at TEXT,
    version INTEGER DEFAULT 1
);

-- 3. 订单表
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT UNIQUE NOT NULL,
    prescription_id INTEGER,
    patient_id TEXT NOT NULL,
    amount REAL NOT NULL,
    payment_method TEXT,
    payment_status TEXT DEFAULT 'pending',
    payment_time TEXT,
    payment_transaction_id TEXT,
    decoction_required INTEGER DEFAULT 0,
    shipping_name TEXT,
    shipping_phone TEXT,
    shipping_address TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 4. 代煎订单表
CREATE TABLE IF NOT EXISTS decoction_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    provider_id TEXT,
    provider_name TEXT,
    decoction_order_no TEXT,
    status TEXT DEFAULT 'submitted',
    tracking_no TEXT,
    estimated_delivery TEXT,
    actual_delivery_date TEXT,
    provider_notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 5. 处方变更记录表
CREATE TABLE IF NOT EXISTS prescription_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER,
    changed_by INTEGER,
    change_type TEXT,
    original_prescription TEXT,
    new_prescription TEXT,
    change_reason TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_prescriptions_status ON prescriptions(status);
CREATE INDEX IF NOT EXISTS idx_prescriptions_patient ON prescriptions(patient_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_doctor ON prescriptions(doctor_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_created ON prescriptions(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(payment_status);
CREATE INDEX IF NOT EXISTS idx_orders_patient ON orders(patient_id);
CREATE INDEX IF NOT EXISTS idx_decoction_status ON decoction_orders(status);