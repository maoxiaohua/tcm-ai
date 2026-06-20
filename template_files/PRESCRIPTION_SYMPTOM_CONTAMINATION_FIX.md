# 处方症状混乱问题修复方案

## 问题描述

用户反馈：咨询张仲景医生时输入咳嗽症状（干咳、白痰、嗓子痒），但生成的处方中【辨证分析】部分却包含完全不同的糖尿病症状（口干、多饮、夜尿频多、体重下降、血糖偏高）。

## 根本原因分析

### 1. 核心问题：**AI生成处方时混入了其他问诊的症状信息**

通过数据库调查发现：

**患者问诊历史**（patient_id: usr_20250920_5741e17a78e8）：
1. **问诊1** (uuid: f9b9-38c6-4f9b-a330-4a3b)
   - 时间：2025-11-24 07:10
   - 医生：jin_daifu
   - 症状：口干口渴、多饮、夜尿频多、体重下降、血糖偏高（糖尿病症状）

2. **问诊2** (uuid: e0eb-64cf-409a-9d53-e9ff)  ⚠️ 问题问诊
   - 时间：2025-11-25 01:47
   - 医生：zhang_zhongjing
   - 症状：干咳、白痰、嗓子痒（咳嗽症状）
   - **AI响应中错误包含**: "结合既往病史（口干、多饮、夜尿频多、体重下降、血糖偏高）"

3. **问诊3** (uuid: 4344-fe0e-4dfb-9ad0-523b)
   - 时间：2025-11-25 01:49
   - 医生：jin_daifu
   - 症状：与问诊2完全相同（复制）

### 2. 问题根源定位

#### 问题1：**前端conversation_history管理混乱**

**代码位置**: `/opt/tcm-ai/api/routes/unified_consultation_routes.py` Line 89

```python
conversation_history=request.conversation_history or [],
```

前端直接传递conversation_history给后端，如果前端管理不当：
- ✅ 同一个localStorage对象被多个问诊共享
- ✅ 切换医生时没有清空conversation_history
- ✅ 新开问诊时复用了旧问诊的history

#### 问题2：**AI被传入了混合的对话历史**

**代码位置**: `/opt/tcm-ai/core/consultation/unified_consultation_service.py` Line 1496

```python
for turn in request.conversation_history[-10:]:  # 只保留最近10轮
```

AI接收到的messages包含了来自不同问诊的对话，导致：
- AI认为患者有"既往病史（糖尿病症状）"
- AI将其他问诊的症状作为背景信息整合到当前处方中

#### 问题3：**医疗安全检查未能拦截症状编造**

**代码位置**: `/opt/tcm-ai/core/consultation/unified_consultation_service.py` Line 125-127

```python
# 医疗安全提示
绝对禁止添加、推测、编造患者未明确描述的任何症状细节
```

虽然有医疗安全提示，但AI仍然生成了患者从未提及的"既往病史"。

## 解决方案

### 方案A：**前端隔离方案**（推荐，快速有效）

**目标**: 确保每个问诊使用独立的conversation_history

**修改位置**: 前端问诊页面 (index_smart_workflow.html 或类似文件)

#### 1. 修改localStorage存储结构

**修改前**:
```javascript
// 全局共享的conversation_history（错误）
localStorage.setItem('conversationHistory', JSON.stringify(history));
```

**修改后**:
```javascript
// 基于conversation_id的独立存储（正确）
const storageKey = `consultation_${conversationId}`;
localStorage.setItem(storageKey, JSON.stringify({
    conversation_id: conversationId,
    selected_doctor: selectedDoctor,
    conversation_history: history,
    created_at: new Date().toISOString()
}));
```

#### 2. 新开问诊时生成新的conversation_id

```javascript
function startNewConsultation(doctorId) {
    // 生成新的唯一ID
    const newConversationId = generateUUID();

    // 清空当前会话
    currentConversationHistory = [];

    // 初始化新的存储
    const storageKey = `consultation_${newConversationId}`;
    localStorage.setItem(storageKey, JSON.stringify({
        conversation_id: newConversationId,
        selected_doctor: doctorId,
        conversation_history: [],
        created_at: new Date().toISOString()
    }));

    return newConversationId;
}
```

#### 3. 加载对话时严格按conversation_id隔离

```javascript
function loadConversationHistory(conversationId) {
    const storageKey = `consultation_${conversationId}`;
    const data = localStorage.getItem(storageKey);

    if (data) {
        const parsed = JSON.parse(data);
        // 验证conversation_id匹配
        if (parsed.conversation_id === conversationId) {
            return parsed.conversation_history || [];
        }
    }

    return []; // 找不到或不匹配则返回空数组
}
```

#### 4. 切换医生时强制重新开始

```javascript
function changeDoctorSelection(newDoctorId) {
    // 询问用户是否保存当前问诊
    if (currentConversationHistory.length > 0) {
        if (confirm('切换医生将开始新的问诊，是否保存当前问诊？')) {
            saveCurrentConsultation();
        }
    }

    // 生成新的conversation_id，清空history
    const newConversationId = startNewConsultation(newDoctorId);

    // 更新UI
    currentConversationId = newConversationId;
    currentConversationHistory = [];
    selectedDoctor = newDoctorId;

    // 清空聊天界面
    clearChatInterface();
}
```

### 方案B：**后端校验方案**（补充防护）

**目标**: 在后端再次校验conversation_history与当前consultation的一致性

**修改位置**: `/opt/tcm-ai/core/consultation/unified_consultation_service.py`

#### 1. 添加conversation_history校验函数

```python
def _validate_conversation_history(self, request: ConsultationRequest) -> List[Dict]:
    """
    校验并清理conversation_history，确保不包含其他问诊的内容
    """
    if not request.conversation_history:
        return []

    # 连接数据库检查当前consultation
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    cursor = conn.cursor()

    try:
        # 查询当前consultation的conversation_log
        cursor.execute("""
            SELECT conversation_log FROM consultations
            WHERE uuid = ? AND patient_id = ?
        """, (request.conversation_id, request.patient_id))

        result = cursor.fetchone()

        if result:
            # 如果consultation已存在，使用数据库中的conversation_log
            stored_log = json.loads(result[0])
            stored_history = stored_log.get('conversation_history', [])

            # 对比并返回数据库中的历史（权威来源）
            logger.info(f"✅ 使用数据库存储的conversation_history (轮数: {len(stored_history)})")
            return stored_history
        else:
            # 新问诊，清空history防止污染
            logger.warning(f"⚠️ 新问诊 {request.conversation_id}，忽略前端传入的history")
            return []

    except Exception as e:
        logger.error(f"校验conversation_history失败: {e}")
        # 出错时返回空，避免混乱
        return []
    finally:
        conn.close()
```

#### 2. 在process_consultation中调用校验

**修改位置**: Line 145-148

```python
async def process_consultation(self, request: ConsultationRequest) -> ConsultationResponse:
    """处理问诊请求"""
    start_time = datetime.now()

    try:
        # 🔑 新增：校验并清理conversation_history
        validated_history = self._validate_conversation_history(request)
        request.conversation_history = validated_history

        # 1. 对话状态管理
        conversation_state = await self._manage_conversation_state(request)
        ...
```

### 方案C：**AI提示词增强**（最后一道防线）

**修改位置**: `/opt/tcm-ai/core/consultation/unified_consultation_service.py` Line 125-143

```python
medical_safety_prompt = f"""
🚨 **严格医疗安全要求**（违反将记录审计日志）

1. **症状描述严格限制** ⚠️ 最高优先级：
   - 绝对禁止添加、推测、编造患者未明确描述的任何症状细节
   - 绝对禁止从"便秘"推测出"大便干结如栗，数日一行"
   - 🔥 绝对禁止编造"既往病史"，如果对话历史中没有提及，就不要写
   - 只能使用患者确切的原始表述

2. **处方辨证分析要求**：
   - 只能基于"当前对话"中患者明确描述的症状
   - 如需参考既往病史，必须在对话中明确获得患者确认
   - 禁止使用"结合既往病史"这样的措辞，除非患者在本次对话中提供

3. **舌象脉象信息严格限制**：
   - 绝对禁止在没有患者上传舌象图片时描述任何具体的舌象特征
   - 绝对禁止编造任何脉象描述
   - 如无图像和患者描述，写"未见舌象脉象信息"

4. **西药过滤**：
   - 严禁推荐任何西药成分
   - 只能使用中药材和经典方剂
   - 如发现西药成分立即过滤

5. **处方责任声明**：
   - 所有处方建议必须包含"本处方为AI预诊建议，请务必咨询专业中医师后使用"

⚠️ 违反以上任何一条都是严重的医疗安全事故！将触发系统告警和人工审查！
"""
```

## 数据修复方案

### 修复已存在的错误数据

对于已经生成的包含错误症状的处方，需要：

1. **标记问题处方**：
```sql
-- 查找包含"既往病史"但对话中未提及的处方
SELECT p.id, p.conversation_id, p.ai_prescription
FROM prescriptions p
JOIN consultations c ON p.consultation_id = c.uuid
WHERE p.ai_prescription LIKE '%既往病史%'
AND c.conversation_log NOT LIKE '%既往%';
```

2. **通知医生重新审查**：
```sql
-- 添加审查备注
UPDATE prescriptions
SET review_notes = '⚠️ 检测到辨证分析可能包含其他问诊信息，请重点审查症状描述准确性'
WHERE id IN (
    SELECT p.id
    FROM prescriptions p
    JOIN consultations c ON p.consultation_id = c.uuid
    WHERE p.ai_prescription LIKE '%既往病史%'
    AND c.conversation_log NOT LIKE '%既往%'
);
```

## 测试验证方案

### 1. 前端隔离测试

```javascript
// 测试脚本：验证conversation_history隔离
function testConversationIsolation() {
    // 1. 开始问诊A（张仲景）
    const convA = startNewConsultation('zhang_zhongjing');
    sendMessage(convA, '我口干多饮');
    const historyA = loadConversationHistory(convA);
    console.assert(historyA.length === 2, 'A应该有2条记录');

    // 2. 切换到问诊B（金大夫）
    const convB = startNewConsultation('jin_daifu');
    const historyB = loadConversationHistory(convB);
    console.assert(historyB.length === 0, 'B应该是空的');

    // 3. 发送消息到B
    sendMessage(convB, '我咳嗽');
    const historyB2 = loadConversationHistory(convB);
    console.assert(historyB2.length === 2, 'B应该有2条记录');

    // 4. 验证A没有被污染
    const historyA2 = loadConversationHistory(convA);
    console.assert(historyA2.length === 2, 'A仍然只有2条记录');
    console.assert(!JSON.stringify(historyA2).includes('咳嗽'), 'A不应包含B的症状');

    console.log('✅ 隔离测试通过');
}
```

### 2. 后端校验测试

```bash
# 测试1：新问诊，前端传入了旧history
curl -X POST http://localhost:8000/api/consultation/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "new_conv_123",
    "patient_id": "test_patient",
    "selected_doctor": "zhang_zhongjing",
    "message": "我咳嗽",
    "conversation_history": [
        {"role": "user", "content": "我口干多饮"},
        {"role": "assistant", "content": "您有消渴症状..."}
    ]
  }'

# 预期：后端应该忽略conversation_history，返回空的history上下文
```

### 3. AI安全测试

```python
# 测试AI是否会编造既往病史
test_cases = [
    {
        "message": "我咳嗽一周了",
        "conversation_history": [],
        "expected": "辨证分析中不应包含'既往病史'、'口干'、'多饮'等未提及症状"
    },
    {
        "message": "我头疼",
        "conversation_history": [
            {"role": "user", "content": "我咳嗽"},
            {"role": "assistant", "content": "需要详细了解..."}
        ],
        "expected": "辨证分析只应涉及'头疼'和'咳嗽'，不应编造其他症状"
    }
]

for test in test_cases:
    response = await consultation_service.process_consultation(test)
    assert '既往病史' not in response.reply or verify_history_mentioned(test['conversation_history'])
```

## 实施步骤

### 第一阶段：紧急修复（1-2小时）

1. ✅ **前端代码修改** - 实施方案A的1-4点
2. ✅ **后端校验添加** - 实施方案B的1-2点
3. ✅ **部署更新** - 重启服务
4. ✅ **快速验证** - 测试新开问诊是否隔离

### 第二阶段：增强防护（2-4小时）

1. ✅ **AI提示词增强** - 实施方案C
2. ✅ **数据审查** - 标记问题处方
3. ✅ **全面测试** - 运行完整测试套件
4. ✅ **监控告警** - 添加症状混乱检测告警

### 第三阶段：长期改进（1-2天）

1. ✅ **前端重构** - 建立完善的会话管理系统
2. ✅ **后端审计** - 添加conversation_history审计日志
3. ✅ **AI训练** - 收集错误案例，改进提示词
4. ✅ **文档完善** - 更新开发规范和最佳实践

## 预期效果

修复后应达到：

1. ✅ **前端隔离**：每个问诊使用独立的conversation_history，localStorage按conversation_id隔离存储
2. ✅ **后端校验**：即使前端传错，后端也能识别并使用正确的history
3. ✅ **AI安全**：AI不再编造"既往病史"或混入其他问诊症状
4. ✅ **医生审查**：问题处方被标记，医生重点审查
5. ✅ **监控告警**：实时检测症状混乱，触发告警

## 附录

### A. conversation_id生成规范

```javascript
// 标准UUID v4生成
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// 或使用更短的格式（推荐）
function generateConversationId() {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 6);
    return `${timestamp}-${random}`;
}
```

### B. 关键数据表结构

```sql
-- consultations表
CREATE TABLE consultations (
    uuid TEXT PRIMARY KEY,           -- conversation_id
    patient_id TEXT NOT NULL,        -- 患者ID
    selected_doctor_id TEXT,         -- 医生ID（字符串）
    conversation_log TEXT,           -- JSON存储对话历史
    status TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- prescriptions表
CREATE TABLE prescriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT,            -- 关联conversation
    consultation_id TEXT,            -- 关联consultation UUID
    patient_id TEXT,
    doctor_id TEXT,
    symptoms TEXT,                   -- 从AI响应提取
    diagnosis TEXT,                  -- 从AI响应提取
    ai_prescription TEXT,            -- 完整AI响应
    status TEXT,
    created_at TEXT
);
```

---

**文档版本**: v1.0
**创建时间**: 2025-11-25
**最后更新**: 2025-11-25
**负责人**: AI Assistant (Droid)
**状态**: 待实施
