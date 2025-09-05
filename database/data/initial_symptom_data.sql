-- 中医症状关系初始数据
-- 基于经典中医理论和临床经验构建

-- 插入常见疾病/证候
INSERT OR IGNORE INTO tcm_diseases (name, category, description) VALUES
('失眠', '内科', '不寐，难以入睡或睡后易醒'),
('胃痛', '内科', '胃脘疼痛，常伴胀满'),
('头痛', '内科', '头部疼痛，可见于多种疾病'),
('便秘', '内科', '大便干燥，排便困难'),
('腹泻', '内科', '大便溏薄，次数增多'),
('咳嗽', '内科', '咳嗽有痰或干咳'),
('心悸', '内科', '心中悸动不安'),
('眩晕', '内科', '头晕目眩，视物旋转'),
('水肿', '内科', '肢体面目浮肿'),
('月经不调', '妇科', '月经周期、量、色异常'),
('痛经', '妇科', '经期或经前后小腹疼痛'),
('感冒', '内科', '外感风寒或风热之邪'),
('发热', '内科', '体温升高，恶寒或不恶寒'),
('汗证', '内科', '异常出汗，自汗或盗汗'),
('哮喘', '内科', '呼吸困难，喉中哮鸣');

-- 插入常见症状
INSERT OR IGNORE INTO tcm_symptoms (name, category, description) VALUES
-- 失眠相关症状群
('失眠', '主症', '夜间难以入睡'),
('早醒', '兼症', '睡后过早醒来'),
('多梦', '兼症', '睡中梦扰'),
('入睡困难', '兼症', '躺下后难以入睡'),
('睡眠浅', '兼症', '睡眠深度不够'),
('易惊醒', '兼症', '睡中容易被惊醒'),
('夜醒', '兼症', '夜间频繁醒来'),
('心烦', '兼症', '心中烦躁不安'),
('健忘', '兼症', '记忆力减退'),
('头晕', '兼症', '头部眩晕'),
('疲乏', '兼症', '精神疲倦'),
('精神不振', '兼症', '精神状态不佳'),

-- 胃痛相关症状群
('胃痛', '主症', '胃脘部疼痛'),
('胃胀', '兼症', '胃部胀满感'),
('反酸', '兼症', '胃酸上涌'),
('嗳气', '兼症', '气从胃中上逆'),
('恶心', '兼症', '欲吐不吐'),
('呕吐', '兼症', '胃内容物从口吐出'),
('胃脘痛', '兼症', '上腹部疼痛'),
('胃部不适', '兼症', '胃部不舒服感觉'),
('食欲不振', '兼症', '不思饮食'),
('乏力', '兼症', '全身无力'),
('腹胀', '兼症', '腹部胀满'),

-- 头痛相关症状群
('头痛', '主症', '头部疼痛'),
('头胀', '兼症', '头部胀痛'),
('偏头痛', '兼症', '一侧头痛'),
('太阳穴痛', '兼症', '颞部疼痛'),
('后脑痛', '兼症', '枕部疼痛'),
('颈项强直', '兼症', '颈部僵硬'),

-- 便秘相关症状群
('便秘', '主症', '大便干燥难解'),
('大便干燥', '兼症', '粪便干硬'),
('排便困难', '兼症', '排便费力'),
('大便干结', '兼症', '大便干硬成块'),
('便干如栗', '兼症', '大便干硬如栗子'),
('口干', '兼症', '口中干燥'),

-- 腹泻相关症状群
('腹泻', '主症', '大便溏薄频繁'),
('便溏', '兼症', '大便不成形'),
('泄泻', '兼症', '腹泻的中医术语'),
('水泻', '兼症', '大便如水样'),
('大便稀薄', '兼症', '粪便稀软'),
('腹痛', '兼症', '腹部疼痛'),
('肠鸣', '兼症', '肠中雷鸣'),
('里急后重', '兼症', '便意频繁但排便不畅'),

-- 咳嗽相关症状群
('咳嗽', '主症', '咳嗽有声'),
('咳痰', '兼症', '咳嗽有痰'),
('干咳', '兼症', '咳嗽无痰'),
('咳喘', '兼症', '咳嗽伴气喘'),
('痰多', '兼症', '痰液较多'),
('喉痒', '兼症', '咽喉瘙痒'),
('胸闷', '兼症', '胸部闷塞感'),
('气短', '兼症', '呼吸短浅'),

-- 心悸相关症状群
('心悸', '主症', '心中悸动不安'),
('心慌', '兼症', '心中慌乱'),
('胸闷心悸', '兼症', '胸闷伴心悸'),
('心跳加快', '兼症', '心率增快'),

-- 其他常见症状
('发热', '主症', '体温升高'),
('恶寒', '兼症', '怕冷畏寒'),
('出汗', '兼症', '汗液外泄'),
('口渴', '兼症', '想要饮水'),
('小便不利', '兼症', '排尿困难'),
('大便溏薄', '兼症', '大便稀软'),
('舌苔厚腻', '舌象', '舌苔厚而腻'),
('脉弦', '脉象', '脉象如弓弦'),
('脉滑', '脉象', '脉象滑利'),
('脉沉', '脉象', '脉象沉伏');

-- 建立症状关系 (失眠证候群)
INSERT OR IGNORE INTO symptom_relationships (disease_id, main_symptom_id, related_symptom_id, relationship_type, confidence_score, frequency, notes) 
SELECT 
    d.id as disease_id,
    ms.id as main_symptom_id, 
    rs.id as related_symptom_id,
    'direct' as relationship_type,
    0.9 as confidence_score,
    'frequent' as frequency,
    '失眠直接相关症状'
FROM tcm_diseases d, tcm_symptoms ms, tcm_symptoms rs 
WHERE d.name = '失眠' AND ms.name = '失眠' 
AND rs.name IN ('早醒', '多梦', '入睡困难', '睡眠浅', '易惊醒', '夜醒');

-- 失眠伴随症状
INSERT OR IGNORE INTO symptom_relationships (disease_id, main_symptom_id, related_symptom_id, relationship_type, confidence_score, frequency, notes)
SELECT 
    d.id, ms.id, rs.id, 'accompanying', 0.8, 'common', '失眠常见伴随症状'
FROM tcm_diseases d, tcm_symptoms ms, tcm_symptoms rs 
WHERE d.name = '失眠' AND ms.name = '失眠' 
AND rs.name IN ('心烦', '健忘', '头晕', '疲乏', '精神不振');

-- 胃痛症状群
INSERT OR IGNORE INTO symptom_relationships (disease_id, main_symptom_id, related_symptom_id, relationship_type, confidence_score, frequency, notes)
SELECT 
    d.id, ms.id, rs.id, 'direct', 0.9, 'frequent', '胃痛直接相关症状'
FROM tcm_diseases d, tcm_symptoms ms, tcm_symptoms rs 
WHERE d.name = '胃痛' AND ms.name = '胃痛' 
AND rs.name IN ('胃胀', '反酸', '嗳气', '恶心', '胃脘痛', '胃部不适');

INSERT OR IGNORE INTO symptom_relationships (disease_id, main_symptom_id, related_symptom_id, relationship_type, confidence_score, frequency, notes)
SELECT 
    d.id, ms.id, rs.id, 'accompanying', 0.75, 'common', '胃痛伴随症状'
FROM tcm_diseases d, tcm_symptoms ms, tcm_symptoms rs 
WHERE d.name = '胃痛' AND ms.name = '胃痛' 
AND rs.name IN ('食欲不振', '恶心', '呕吐', '乏力', '腹胀');

-- 头痛症状群
INSERT OR IGNORE INTO symptom_relationships (disease_id, main_symptom_id, related_symptom_id, relationship_type, confidence_score, frequency, notes)
SELECT 
    d.id, ms.id, rs.id, 'direct', 0.85, 'frequent', '头痛相关症状'
FROM tcm_diseases d, tcm_symptoms ms, tcm_symptoms rs 
WHERE d.name = '头痛' AND ms.name = '头痛' 
AND rs.name IN ('头胀', '头晕', '偏头痛', '太阳穴痛', '后脑痛', '颈项强直', '恶心');

-- 便秘症状群  
INSERT OR IGNORE INTO symptom_relationships (disease_id, main_symptom_id, related_symptom_id, relationship_type, confidence_score, frequency, notes)
SELECT 
    d.id, ms.id, rs.id, 'direct', 0.9, 'frequent', '便秘直接症状'
FROM tcm_diseases d, tcm_symptoms ms, tcm_symptoms rs 
WHERE d.name = '便秘' AND ms.name = '便秘' 
AND rs.name IN ('大便干燥', '排便困难', '大便干结', '便干如栗', '腹胀', '口干');

-- 腹泻症状群
INSERT OR IGNORE INTO symptom_relationships (disease_id, main_symptom_id, related_symptom_id, relationship_type, confidence_score, frequency, notes)
SELECT 
    d.id, ms.id, rs.id, 'direct', 0.9, 'frequent', '腹泻直接症状'
FROM tcm_diseases d, tcm_symptoms ms, tcm_symptoms rs 
WHERE d.name = '腹泻' AND ms.name = '腹泻' 
AND rs.name IN ('便溏', '泄泻', '水泻', '大便稀薄', '腹痛', '肠鸣', '里急后重');

-- 咳嗽症状群
INSERT OR IGNORE INTO symptom_relationships (disease_id, main_symptom_id, related_symptom_id, relationship_type, confidence_score, frequency, notes)
SELECT 
    d.id, ms.id, rs.id, 'direct', 0.85, 'frequent', '咳嗽相关症状'
FROM tcm_diseases d, tcm_symptoms ms, tcm_symptoms rs 
WHERE d.name = '咳嗽' AND ms.name = '咳嗽' 
AND rs.name IN ('咳痰', '干咳', '咳喘', '痰多', '喉痒', '胸闷', '气短');

-- 心悸症状群
INSERT OR IGNORE INTO symptom_relationships (disease_id, main_symptom_id, related_symptom_id, relationship_type, confidence_score, frequency, notes)
SELECT 
    d.id, ms.id, rs.id, 'direct', 0.8, 'common', '心悸相关症状'
FROM tcm_diseases d, tcm_symptoms ms, tcm_symptoms rs 
WHERE d.name = '心悸' AND ms.name = '心悸' 
AND rs.name IN ('心慌', '胸闷心悸', '心跳加快');

-- 创建症状聚类缓存 (性能优化)
INSERT OR IGNORE INTO symptom_clusters (cluster_name, main_symptom_id, related_symptoms, confidence_score)
SELECT 
    '失眠症状群',
    ms.id,
    json_array('早醒', '多梦', '入睡困难', '睡眠浅', '易惊醒', '夜醒', '心烦', '健忘', '头晕', '疲乏'),
    0.85
FROM tcm_symptoms ms WHERE ms.name = '失眠';

INSERT OR IGNORE INTO symptom_clusters (cluster_name, main_symptom_id, related_symptoms, confidence_score)
SELECT 
    '胃痛症状群',
    ms.id,
    json_array('胃胀', '反酸', '嗳气', '恶心', '胃脘痛', '胃部不适', '食欲不振', '呕吐'),
    0.85
FROM tcm_symptoms ms WHERE ms.name = '胃痛';