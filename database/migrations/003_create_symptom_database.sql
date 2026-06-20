-- 中医症状关系数据库设计
-- 创建时间: 2025-01-09
-- 说明: 支持症状关联识别的智能数据库架构

-- 1. 主要疾病/证候表
CREATE TABLE IF NOT EXISTS tcm_diseases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50), -- 如: 内科、外科、妇科、儿科
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 症状表
CREATE TABLE IF NOT EXISTS tcm_symptoms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50), -- 如: 主症、兼症、舌象、脉象
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 症状关系表 (核心表)
CREATE TABLE IF NOT EXISTS symptom_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disease_id INTEGER,
    main_symptom_id INTEGER,
    related_symptom_id INTEGER,
    relationship_type VARCHAR(20), -- direct/accompanying/concurrent/conditional
    confidence_score FLOAT DEFAULT 0.8, -- 0-1, 关联度评分
    frequency VARCHAR(20), -- common/frequent/occasional/rare
    source VARCHAR(50) DEFAULT 'expert', -- expert/ai/literature/clinical
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (disease_id) REFERENCES tcm_diseases(id),
    FOREIGN KEY (main_symptom_id) REFERENCES tcm_symptoms(id),
    FOREIGN KEY (related_symptom_id) REFERENCES tcm_symptoms(id)
);

-- 4. 症状聚类缓存表 (性能优化)
CREATE TABLE IF NOT EXISTS symptom_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_name VARCHAR(100),
    main_symptom_id INTEGER,
    related_symptoms TEXT, -- JSON格式存储相关症状ID列表
    confidence_score FLOAT DEFAULT 0.8,
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (main_symptom_id) REFERENCES tcm_symptoms(id)
);

-- 5. AI分析日志表
CREATE TABLE IF NOT EXISTS ai_symptom_analysis_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_symptom VARCHAR(100),
    context_symptoms TEXT, -- JSON格式
    ai_response TEXT, -- AI返回的完整响应
    extracted_relationships TEXT, -- 提取的关系JSON
    confidence_score FLOAT,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_symptom_relationships_disease ON symptom_relationships(disease_id);
CREATE INDEX IF NOT EXISTS idx_symptom_relationships_main ON symptom_relationships(main_symptom_id);
CREATE INDEX IF NOT EXISTS idx_symptom_relationships_related ON symptom_relationships(related_symptom_id);
CREATE INDEX IF NOT EXISTS idx_symptom_relationships_type ON symptom_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_symptom_clusters_main ON symptom_clusters(main_symptom_id);
CREATE INDEX IF NOT EXISTS idx_symptoms_name ON tcm_symptoms(name);
CREATE INDEX IF NOT EXISTS idx_diseases_name ON tcm_diseases(name);