-- 处方审核系统数据库表结构
-- 支持完整的处方审核流程

-- 1. 支付日志表
CREATE TABLE IF NOT EXISTS prescription_payment_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_method TEXT NOT NULL,
    payment_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'completed',
    transaction_id TEXT,
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id)
);

-- 2. 医生审核队列表
CREATE TABLE IF NOT EXISTS doctor_review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER NOT NULL,
    doctor_id TEXT NOT NULL,
    consultation_id TEXT NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'pending', -- pending, completed, cancelled
    priority TEXT DEFAULT 'normal', -- high, normal, low
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id)
);

-- 3. 处方审核历史表
CREATE TABLE IF NOT EXISTS prescription_review_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER NOT NULL,
    doctor_id TEXT NOT NULL,
    action TEXT NOT NULL, -- approve, modify, reject
    modified_prescription TEXT,
    doctor_notes TEXT,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id)
);

-- 4. 为prescriptions表添加审核相关字段（如果不存在）
ALTER TABLE prescriptions ADD COLUMN review_status TEXT DEFAULT 'pending';
ALTER TABLE prescriptions ADD COLUMN review_priority TEXT DEFAULT 'normal';
ALTER TABLE prescriptions ADD COLUMN auto_submitted BOOLEAN DEFAULT 0;

-- 5. 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_payment_logs_prescription ON prescription_payment_logs(prescription_id);
CREATE INDEX IF NOT EXISTS idx_review_queue_doctor ON doctor_review_queue(doctor_id, status);
CREATE INDEX IF NOT EXISTS idx_review_queue_status ON doctor_review_queue(status, submitted_at);
CREATE INDEX IF NOT EXISTS idx_review_history_prescription ON prescription_review_history(prescription_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_review_status ON prescriptions(review_status, status);

-- 6. 更新现有处方的状态（如果有的话）
UPDATE prescriptions 
SET review_status = CASE 
    WHEN status = 'pending' THEN 'not_submitted'
    WHEN status = 'patient_confirmed' THEN 'pending_review'
    ELSE 'completed'
END
WHERE review_status IS NULL OR review_status = 'pending';