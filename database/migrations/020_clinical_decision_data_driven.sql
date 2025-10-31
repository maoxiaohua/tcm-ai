-- =====================================================
-- 决策树数据驱动架构 - 数据库Schema
-- 版本: v3.0-Beta
-- 日期: 2025-10-31
-- 说明: 新的数据驱动架构，支持左右同步和统一数据源
-- =====================================================

-- =====================================
-- 1. 主数据表：临床决策数据
-- =====================================
CREATE TABLE IF NOT EXISTS clinical_decision_data (
    -- 基础信息
    id TEXT PRIMARY KEY,                    -- 唯一ID
    doctor_id TEXT NOT NULL,                -- 医生ID
    disease_id TEXT,                        -- 疾病ID（关联标准库）
    disease_name TEXT NOT NULL,             -- 疾病名称

    -- 核心数据（三种格式，同一份数据的不同表现）
    structured_content TEXT NOT NULL,       -- JSON: 结构化数据（主数据）
    text_format TEXT NOT NULL,              -- 文本格式（左侧展示）
    tree_structure TEXT NOT NULL,           -- 树形结构（右侧画布）

    -- 版本控制
    version INTEGER DEFAULT 1,              -- 数据版本
    is_active BOOLEAN DEFAULT 1,            -- 是否激活

    -- 审计信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified_from TEXT,                -- 'text' 或 'canvas' 或 'ai'
    modification_count INTEGER DEFAULT 0,   -- 修改次数

    -- 使用统计
    usage_count INTEGER DEFAULT 0,          -- 使用次数
    success_count INTEGER DEFAULT 0,        -- 成功次数
    last_used_at TIMESTAMP,                 -- 最后使用时间

    -- 备注
    notes TEXT,                             -- 备注说明
    tags TEXT                               -- JSON: 标签数组
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_cdd_doctor ON clinical_decision_data(doctor_id);
CREATE INDEX IF NOT EXISTS idx_cdd_disease ON clinical_decision_data(disease_id);
CREATE INDEX IF NOT EXISTS idx_cdd_disease_name ON clinical_decision_data(disease_name);
CREATE INDEX IF NOT EXISTS idx_cdd_active ON clinical_decision_data(is_active);
CREATE INDEX IF NOT EXISTS idx_cdd_usage ON clinical_decision_data(usage_count DESC);

-- 创建更新时间触发器
CREATE TRIGGER IF NOT EXISTS update_cdd_timestamp
AFTER UPDATE ON clinical_decision_data
FOR EACH ROW
BEGIN
    UPDATE clinical_decision_data
    SET updated_at = CURRENT_TIMESTAMP,
        modification_count = modification_count + 1
    WHERE id = NEW.id;
END;

-- =====================================
-- 2. 疾病标准库
-- =====================================
CREATE TABLE IF NOT EXISTS tcm_diseases_standard (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,              -- 疾病名称
    category TEXT NOT NULL,                 -- 疾病分类
    alias TEXT,                             -- 别名（JSON数组）
    description TEXT,                       -- 疾病描述
    common_syndromes TEXT,                  -- JSON: 常见证候
    typical_symptoms TEXT,                  -- JSON: 典型症状
    differential_diagnosis TEXT,            -- JSON: 鉴别诊断要点
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 初始化常见疾病
INSERT OR IGNORE INTO tcm_diseases_standard (id, name, category, description, common_syndromes) VALUES
('disease_001', '风寒感冒', '外感病', '感受风寒之邪，导致肺卫失宣', '["风寒表证", "风寒束表证"]'),
('disease_002', '风热感冒', '外感病', '感受风热之邪，或风寒化热', '["风热表证", "风热犯表证"]'),
('disease_003', '脾胃虚弱', '内伤病', '脾胃运化功能减退，气血生化不足', '["脾气虚证", "脾阳虚证"]'),
('disease_004', '肝气郁结', '内伤病', '情志不遂，肝失疏泄，气机郁滞', '["肝气郁结证", "肝郁气滞证"]'),
('disease_005', '肾阳虚证', '内伤病', '肾阳不足，温煦失职', '["肾阳虚证", "命门火衰证"]');

-- =====================================
-- 3. 症状标准库（增强版）
-- =====================================
CREATE TABLE IF NOT EXISTS tcm_symptoms_standard (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,              -- 症状名称
    category TEXT NOT NULL,                 -- 类别：主症/兼症/舌象/脉象
    subcategory TEXT,                       -- 子类别
    severity_levels TEXT,                   -- JSON: 严重程度级别
    typical_description TEXT,               -- 典型描述
    differential_points TEXT,               -- JSON: 鉴别要点
    related_syndromes TEXT,                 -- JSON: 相关证候
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 初始化常见症状
INSERT OR IGNORE INTO tcm_symptoms_standard (id, name, category, severity_levels, typical_description) VALUES
('symptom_001', '恶寒发热', '主症', '["轻", "中", "重"]', '恶寒与发热同时出现'),
('symptom_002', '头痛', '主症', '["轻", "中", "重"]', '头部疼痛'),
('symptom_003', '身痛', '主症', '["轻", "中", "重"]', '全身肌肉关节疼痛'),
('symptom_004', '鼻塞', '兼症', '["轻", "中", "重"]', '鼻腔堵塞不通'),
('symptom_005', '流涕', '兼症', '["清涕", "黄涕", "浊涕"]', '鼻涕流出'),
('symptom_006', '咳嗽', '兼症', '["轻", "中", "重"]', '咳嗽有痰或无痰'),
('symptom_007', '舌淡红', '舌象', NULL, '舌色淡红，正常'),
('symptom_008', '苔薄白', '舌象', NULL, '舌苔薄白，正常或风寒'),
('symptom_009', '脉浮', '脉象', NULL, '脉浮于表，主表证'),
('symptom_010', '脉紧', '脉象', NULL, '脉来紧张有力，主寒主痛');

-- =====================================
-- 4. 处方标准库（增强版）
-- =====================================
CREATE TABLE IF NOT EXISTS tcm_prescriptions_standard (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,              -- 处方名称
    alias TEXT,                             -- 别名
    source TEXT,                            -- 出处（书籍）
    category TEXT,                          -- 分类
    composition TEXT NOT NULL,              -- JSON: 方剂组成（详细）
    effects TEXT NOT NULL,                  -- 功效
    indications TEXT NOT NULL,              -- 主治
    usage TEXT,                             -- 用法用量
    contraindications TEXT,                 -- 禁忌
    modifications TEXT,                     -- JSON: 常见加减
    clinical_notes TEXT,                    -- JSON: 临床要点
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 初始化经典处方
INSERT OR IGNORE INTO tcm_prescriptions_standard (
    id, name, source, category, composition, effects, indications, usage
) VALUES
(
    'prescription_001',
    '麻黄汤',
    '《伤寒论》',
    '解表剂',
    '[
        {"herb_id": "herb_001", "name": "麻黄", "dosage": 9, "unit": "克", "role": "君药", "effect": "发汗解表，宣肺平喘"},
        {"herb_id": "herb_002", "name": "桂枝", "dosage": 6, "unit": "克", "role": "臣药", "effect": "解肌发表，温通经脉"},
        {"herb_id": "herb_003", "name": "杏仁", "dosage": 6, "unit": "克", "role": "佐药", "effect": "止咳平喘"},
        {"herb_id": "herb_004", "name": "甘草", "dosage": 3, "unit": "克", "role": "使药", "effect": "调和诸药"}
    ]',
    '发汗解表，宣肺平喘',
    '外感风寒表实证。恶寒发热，头身疼痛，无汗而喘，舌苔薄白，脉浮紧',
    '水煎服，日一剂，温服取微汗'
),
(
    'prescription_002',
    '桂枝汤',
    '《伤寒论》',
    '解表剂',
    '[
        {"herb_id": "herb_002", "name": "桂枝", "dosage": 9, "unit": "克", "role": "君药", "effect": "解肌发表，温通经脉"},
        {"herb_id": "herb_005", "name": "白芍", "dosage": 9, "unit": "克", "role": "臣药", "effect": "养血敛阴，和营止痛"},
        {"herb_id": "herb_006", "name": "生姜", "dosage": 9, "unit": "克", "role": "佐药", "effect": "温胃散寒，助桂枝解表"},
        {"herb_id": "herb_007", "name": "大枣", "dosage": 12, "unit": "枚", "role": "佐药", "effect": "补中益气，滋养营血"},
        {"herb_id": "herb_004", "name": "甘草", "dosage": 6, "unit": "克", "role": "使药", "effect": "调和诸药"}
    ]',
    '解肌发表，调和营卫',
    '外感风寒表虚证。发热恶风，汗出头痛，鼻鸣干呕，苔白不渴，脉浮缓',
    '水煎服，温服取微汗'
);

-- =====================================
-- 5. 中药标准库
-- =====================================
CREATE TABLE IF NOT EXISTS tcm_herbs_standard (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,              -- 药材名称
    pinyin TEXT,                            -- 拼音
    alias TEXT,                             -- 别名
    category TEXT NOT NULL,                 -- 分类
    nature TEXT,                            -- 性味
    meridians TEXT,                         -- 归经
    effects TEXT,                           -- 功效
    indications TEXT,                       -- 主治
    dosage_range TEXT,                      -- 常用量范围
    contraindications TEXT,                 -- 禁忌
    incompatibilities TEXT,                 -- 配伍禁忌
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 初始化常用中药
INSERT OR IGNORE INTO tcm_herbs_standard (id, name, pinyin, category, nature, meridians, effects, dosage_range) VALUES
('herb_001', '麻黄', 'mahuang', '解表药', '辛、微苦，温', '肺、膀胱', '发汗解表，宣肺平喘，利水消肿', '3-10克'),
('herb_002', '桂枝', 'guizhi', '解表药', '辛、甘，温', '心、肺、膀胱', '发汗解肌，温通经脉，助阳化气', '3-10克'),
('herb_003', '杏仁', 'xingren', '止咳平喘药', '苦，微温', '肺、大肠', '止咳平喘，润肠通便', '5-10克'),
('herb_004', '甘草', 'gancao', '补益药', '甘，平', '心、肺、脾、胃', '补脾益气，清热解毒，祛痰止咳，调和诸药', '3-10克'),
('herb_005', '白芍', 'baishao', '补血药', '苦、酸，微寒', '肝、脾', '养血调经，敛阴止汗，柔肝止痛', '6-15克'),
('herb_006', '生姜', 'shengjiang', '解表药', '辛，温', '肺、脾、胃', '解表散寒，温中止呕，化痰止咳', '3-10克'),
('herb_007', '大枣', 'dazao', '补益药', '甘，温', '脾、胃', '补中益气，养血安神，缓和药性', '3-12枚');

-- =====================================
-- 6. 版本历史表（用于回滚）
-- =====================================
CREATE TABLE IF NOT EXISTS clinical_decision_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL,              -- 关联clinical_decision_data.id
    version INTEGER NOT NULL,               -- 版本号
    structured_content TEXT NOT NULL,       -- 当时的数据快照
    text_format TEXT NOT NULL,
    tree_structure TEXT NOT NULL,
    modified_from TEXT,                     -- 修改来源
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT                              -- 版本说明
);

CREATE INDEX IF NOT EXISTS idx_cdh_decision ON clinical_decision_history(decision_id);
CREATE INDEX IF NOT EXISTS idx_cdh_version ON clinical_decision_history(version DESC);

-- =====================================
-- 7. 数据一致性视图
-- =====================================
CREATE VIEW IF NOT EXISTS v_decision_data_summary AS
SELECT
    d.id,
    d.doctor_id,
    d.disease_name,
    d.version,
    d.modification_count,
    d.usage_count,
    d.success_count,
    CASE
        WHEN d.success_count > 0 THEN ROUND(d.success_count * 100.0 / d.usage_count, 2)
        ELSE 0
    END as success_rate,
    d.last_modified_from,
    d.created_at,
    d.updated_at,
    d.last_used_at,
    -- 检查数据一致性
    CASE
        WHEN d.structured_content IS NULL OR d.text_format IS NULL OR d.tree_structure IS NULL
        THEN 'incomplete'
        WHEN LENGTH(d.structured_content) < 100
        THEN 'insufficient'
        ELSE 'complete'
    END as data_status
FROM clinical_decision_data d
WHERE d.is_active = 1;

-- =====================================
-- 8. 使用日志表（追踪使用情况）
-- =====================================
CREATE TABLE IF NOT EXISTS clinical_decision_usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL,
    consultation_id TEXT,                   -- 关联问诊记录
    doctor_id TEXT NOT NULL,
    patient_id TEXT,
    match_score DECIMAL(3,2),              -- 匹配度分数
    outcome TEXT,                           -- 'success', 'partial', 'failed'
    feedback TEXT,                          -- 反馈
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cdul_decision ON clinical_decision_usage_log(decision_id);
CREATE INDEX IF NOT EXISTS idx_cdul_doctor ON clinical_decision_usage_log(doctor_id);

-- =====================================
-- 完成消息
-- =====================================
SELECT '✅ 数据驱动决策树架构数据库Schema创建完成！' as result;
SELECT '📊 主表: clinical_decision_data' as info;
SELECT '📚 标准库: diseases, symptoms, prescriptions, herbs' as info;
SELECT '📝 辅助表: history, usage_log' as info;
SELECT '🔍 视图: v_decision_data_summary' as info;
