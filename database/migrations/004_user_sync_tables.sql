-- 用户数据同步相关表结构
-- 解决患者跨设备登录问诊记录丢失问题

-- 用户同步历史表
CREATE TABLE IF NOT EXISTS user_sync_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    sync_type TEXT NOT NULL, -- full_sync, incremental, emergency
    status TEXT NOT NULL, -- completed, failed, pending
    device_fingerprint TEXT,
    conflict_count INTEGER DEFAULT 0,
    data_size INTEGER DEFAULT 0,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    INDEX idx_user_sync_history_user_id (user_id),
    INDEX idx_user_sync_history_sync_id (sync_id)
);

-- 数据冲突记录表
CREATE TABLE IF NOT EXISTS sync_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    conflict_type TEXT NOT NULL, -- conversation, consultation, prescription
    conflict_item_id TEXT NOT NULL,
    client_version TEXT, -- JSON格式存储客户端版本
    server_version TEXT, -- JSON格式存储服务器版本
    resolution_strategy TEXT, -- client_wins, server_wins, merge, manual
    resolved_version TEXT, -- JSON格式存储解决后的版本
    resolved_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sync_conflicts_sync_id (sync_id),
    INDEX idx_sync_conflicts_user_id (user_id)
);

-- 紧急备份表
CREATE TABLE IF NOT EXISTS emergency_backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    backup_data TEXT NOT NULL, -- JSON格式存储完整用户数据
    backup_type TEXT DEFAULT 'emergency', -- emergency, scheduled, manual
    backup_size INTEGER,
    compression_type TEXT DEFAULT 'none',
    checksum TEXT, -- 数据完整性校验
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    INDEX idx_emergency_backups_user_id (user_id),
    INDEX idx_emergency_backups_backup_id (backup_id)
);

-- 设备同步状态表
CREATE TABLE IF NOT EXISTS device_sync_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    device_fingerprint TEXT NOT NULL,
    last_sync_time DATETIME,
    sync_version INTEGER DEFAULT 1,
    sync_conflicts_count INTEGER DEFAULT 0,
    data_version_hash TEXT, -- 数据版本哈希，用于快速比较
    is_primary_device BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, device_fingerprint),
    INDEX idx_device_sync_user_id (user_id),
    INDEX idx_device_sync_device (device_fingerprint)
);

-- 数据变更日志表（用于增量同步）
CREATE TABLE IF NOT EXISTS data_change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    operation_type TEXT NOT NULL, -- insert, update, delete
    old_data TEXT, -- JSON格式存储变更前数据
    new_data TEXT, -- JSON格式存储变更后数据
    change_hash TEXT, -- 变更内容哈希
    device_fingerprint TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced_devices TEXT DEFAULT '[]', -- JSON数组，记录已同步的设备
    INDEX idx_data_change_log_user_id (user_id),
    INDEX idx_data_change_log_table (table_name),
    INDEX idx_data_change_log_time (created_at)
);

-- 同步配置表
CREATE TABLE IF NOT EXISTS user_sync_config (
    user_id TEXT PRIMARY KEY,
    auto_sync_enabled BOOLEAN DEFAULT 1,
    sync_frequency_minutes INTEGER DEFAULT 5, -- 同步频率（分钟）
    conflict_resolution_strategy TEXT DEFAULT 'ask_user', -- ask_user, server_wins, client_wins, merge
    max_devices INTEGER DEFAULT 5, -- 最大允许设备数
    backup_retention_days INTEGER DEFAULT 30,
    enable_real_time_sync BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 实时同步事件表（WebSocket支持）
CREATE TABLE IF NOT EXISTS realtime_sync_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- state_change, message_sent, prescription_created
    event_data TEXT NOT NULL, -- JSON格式事件数据
    target_devices TEXT, -- JSON数组，目标设备列表
    sent_devices TEXT DEFAULT '[]', -- JSON数组，已发送设备列表
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    INDEX idx_realtime_events_user_id (user_id),
    INDEX idx_realtime_events_time (created_at)
);

-- 为现有表添加同步支持字段
-- 为conversation_states表添加同步字段
ALTER TABLE conversation_states ADD COLUMN sync_version INTEGER DEFAULT 1;
ALTER TABLE conversation_states ADD COLUMN last_sync_time DATETIME;
ALTER TABLE conversation_states ADD COLUMN data_hash TEXT;

-- 为consultations表添加同步字段
ALTER TABLE consultations ADD COLUMN sync_version INTEGER DEFAULT 1;
ALTER TABLE consultations ADD COLUMN last_sync_time DATETIME;
ALTER TABLE consultations ADD COLUMN data_hash TEXT;

-- 插入默认同步配置
INSERT OR IGNORE INTO user_sync_config (user_id, auto_sync_enabled) 
SELECT DISTINCT user_id, 1 FROM users WHERE user_id NOT LIKE 'temp_%';

-- 创建触发器，自动记录数据变更
CREATE TRIGGER IF NOT EXISTS conversation_states_change_log
AFTER UPDATE ON conversation_states
FOR EACH ROW
BEGIN
    INSERT INTO data_change_log (
        user_id, table_name, record_id, operation_type, 
        old_data, new_data, change_hash, created_at
    ) VALUES (
        NEW.user_id, 'conversation_states', NEW.conversation_id, 'update',
        json_object(
            'current_stage', OLD.current_stage,
            'last_activity', OLD.last_activity,
            'turn_count', OLD.turn_count
        ),
        json_object(
            'current_stage', NEW.current_stage,
            'last_activity', NEW.last_activity,
            'turn_count', NEW.turn_count
        ),
        hex(randomblob(16)),
        datetime('now')
    );
END;

CREATE TRIGGER IF NOT EXISTS consultations_change_log
AFTER INSERT ON consultations
FOR EACH ROW
BEGIN
    INSERT INTO data_change_log (
        user_id, table_name, record_id, operation_type, 
        new_data, change_hash, created_at
    ) VALUES (
        NEW.patient_id, 'consultations', NEW.uuid, 'insert',
        json_object(
            'uuid', NEW.uuid,
            'selected_doctor_id', NEW.selected_doctor_id,
            'status', NEW.status
        ),
        hex(randomblob(16)),
        datetime('now')
    );
END;

-- 数据操作日志表（导出、导入、迁移记录）
CREATE TABLE IF NOT EXISTS data_operation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    operation_type TEXT NOT NULL, -- export, import, migration, cleanup
    target_user_id TEXT, -- 迁移操作的目标用户
    file_format TEXT, -- json, csv, zip
    file_size INTEGER,
    records_processed INTEGER DEFAULT 0,
    status TEXT NOT NULL, -- success, failed, partial_success
    error_message TEXT,
    metadata TEXT, -- JSON格式存储额外信息
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_data_operation_log_user_id (user_id),
    INDEX idx_data_operation_log_type (operation_type),
    INDEX idx_data_operation_log_time (created_at)
);

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_conversation_states_sync ON conversation_states(user_id, last_sync_time);
CREATE INDEX IF NOT EXISTS idx_consultations_sync ON consultations(patient_id, last_sync_time);
CREATE INDEX IF NOT EXISTS idx_users_sync_config ON user_sync_config(user_id, auto_sync_enabled);