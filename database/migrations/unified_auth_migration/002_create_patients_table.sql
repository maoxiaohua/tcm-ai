-- ========================================
-- 统一认证系统迁移 - 第2步
-- 创建patients扩展表
-- ========================================

-- 创建患者扩展信息表
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(50) UNIQUE NOT NULL,  -- 关联unified_users.global_user_id
    patient_no VARCHAR(50) UNIQUE,        -- 病历号
    id_card_hash VARCHAR(64),             -- 身份证哈希(脱敏)
    gender VARCHAR(10),                   -- 性别: 男/女/其他
    birth_date DATE,                      -- 出生日期
    age INTEGER,                          -- 年龄
    blood_type VARCHAR(10),               -- 血型: A/B/AB/O
    height DECIMAL(5,2),                  -- 身高(cm)
    weight DECIMAL(5,2),                  -- 体重(kg)

    -- 医疗信息
    allergy_history TEXT,                 -- 过敏史(JSON格式)
    family_history TEXT,                  -- 家族病史(JSON格式)
    chronic_diseases TEXT,                -- 慢性病史(JSON格式)
    surgery_history TEXT,                 -- 手术史(JSON格式)
    medication_history TEXT,              -- 用药史(JSON格式)

    -- 中医体质
    tcm_constitution VARCHAR(50),         -- 中医体质类型
    constitution_score TEXT,              -- 体质评分(JSON)

    -- 紧急联系人
    emergency_contact VARCHAR(100),       -- 紧急联系人姓名
    emergency_phone VARCHAR(20),          -- 紧急联系电话
    emergency_relation VARCHAR(50),       -- 与患者关系

    -- 偏好设置
    preferred_language VARCHAR(20) DEFAULT 'zh-CN',
    preferred_doctor_id INTEGER,          -- 偏好医生ID
    notification_preferences TEXT,        -- 通知偏好(JSON)

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_consultation_at TIMESTAMP,       -- 最后问诊时间

    -- 统计信息
    total_consultations INTEGER DEFAULT 0,
    total_prescriptions INTEGER DEFAULT 0,

    -- 状态
    status VARCHAR(20) DEFAULT 'active',  -- active/inactive/suspended

    -- 备注
    notes TEXT
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_patients_user_id ON patients(user_id);
CREATE INDEX IF NOT EXISTS idx_patients_patient_no ON patients(patient_no);
CREATE INDEX IF NOT EXISTS idx_patients_status ON patients(status);
CREATE INDEX IF NOT EXISTS idx_patients_created_at ON patients(created_at DESC);

-- 创建触发器: 自动更新updated_at
CREATE TRIGGER IF NOT EXISTS patients_updated_at
AFTER UPDATE ON patients
BEGIN
    UPDATE patients SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- 验证
SELECT 'patients表创建成功' as message;
SELECT COUNT(*) as total_patients FROM patients;
