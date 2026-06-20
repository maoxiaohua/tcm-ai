# TCM-AI 对话状态管理机制

## 🎯 系统概述

TCM-AI对话状态管理机制是一个完善的智能对话流程控制系统，专门为中医问诊场景设计。它能够智能管理对话的各个阶段，优化用户体验，确保问诊流程的专业性和连续性。

### 🏗️ 核心架构

```
┌─────────────────────────────────────┐
│         对话状态管理器               │  状态转换、生命周期管理
├─────────────────────────────────────┤
│         对话内容分析器               │  语义分析、意图识别
├─────────────────────────────────────┤
│         统一问诊服务                 │  AI集成、流程编排
├─────────────────────────────────────┤
│         数据持久化层                 │  状态存储、历史记录
└─────────────────────────────────────┘
```

## 📊 对话状态定义

### 状态枚举设计

```python
class ConversationStage(Enum):
    INQUIRY = "inquiry"                          # 初始问诊阶段
    DETAILED_INQUIRY = "detailed_inquiry"        # 详细问诊阶段  
    INTERIM_ADVICE = "interim_advice"            # 临时建议阶段
    DIAGNOSIS = "diagnosis"                      # 诊断阶段
    PRESCRIPTION = "prescription"                # 处方阶段
    PRESCRIPTION_CONFIRM = "prescription_confirm" # 处方确认阶段
    COMPLETED = "completed"                      # 对话结束阶段
    TIMEOUT = "timeout"                          # 超时状态
    EMERGENCY = "emergency"                      # 紧急状态
```

### 状态转换规则

```
inquiry → detailed_inquiry → interim_advice ⇄ diagnosis → prescription → prescription_confirm → completed
    ↓           ↓                   ↓              ↓            ↓
emergency   emergency          emergency      emergency   emergency
```

**关键特性：**
- **循环转换**: `interim_advice` ⇄ `diagnosis` 可以相互转换（补充信息）
- **紧急中断**: 任何阶段都可以转换到 `emergency` 状态
- **灵活回退**: 处方阶段可以回到问诊阶段（患者要求）

## 🔄 状态转换逻辑

### 自动转换触发条件

| 当前阶段 | 目标阶段 | 触发条件 | 置信度要求 |
|---------|----------|----------|------------|
| inquiry | detailed_inquiry | 收到症状描述 | > 0.5 |
| detailed_inquiry | interim_advice | AI给出初步建议 | > 0.6 |
| interim_advice | diagnosis | 收集足够信息 | > 0.7 |
| diagnosis | prescription | 证候明确 | > 0.8 |
| prescription | prescription_confirm | 用户确认意图 | > 0.9 |

### 手动转换控制

```python
# 医生主动推进阶段
state_manager.update_stage(
    conversation_id,
    ConversationStage.PRESCRIPTION,
    reason="医生判断信息充足",
    confidence=0.9
)
```

## 🎯 处方确认流程优化

### 三阶段确认机制

1. **处方生成阶段** (`prescription`)
   - AI生成完整处方
   - 显示详细用药信息
   - 提供安全提醒

2. **用户选择阶段** (`prescription_confirm`)
   - 明确的确认/拒绝选项
   - 继续咨询的可能性
   - 风险提示展示

3. **确认完成阶段** (`completed`)
   - 进入支付流程
   - 生成处方记录
   - 触发后续服务

### 确认界面设计

```html
<div class="prescription-confirm">
    <h3>📋 处方确认</h3>
    <div class="prescription-content">
        <!-- 处方详情 -->
    </div>
    <div class="risk-warning">
        ⚠️ 本处方为AI预诊建议，请务必咨询专业中医师后使用
    </div>
    <div class="action-buttons">
        <button onclick="confirmPrescription()">✅ 确认处方</button>
        <button onclick="continueConsultation()">💬 继续咨询</button>
        <button onclick="savePrescription()">💾 暂存处方</button>
    </div>
</div>
```

## ⏰ 超时机制设计

### 分级超时策略

```python
class ConversationStateManager:
    RESPONSE_TIMEOUT = 300      # 5分钟响应超时
    SESSION_TIMEOUT = 1800      # 30分钟会话超时
    MAX_TURNS = 20              # 最大对话轮数
    MAX_TIMEOUT_WARNINGS = 3    # 最大超时警告次数
```

### 超时处理流程

1. **响应超时** (5分钟)
   - 发送友好提醒
   - 记录警告次数
   - 继续等待用户

2. **会话超时** (30分钟)
   - 自动保存对话状态
   - 发送超时通知
   - 标记对话结束

3. **多次警告** (3次响应超时)
   - 强制结束对话
   - 保存完整记录
   - 提供恢复选项

### 恢复机制

```python
def resume_conversation(conversation_id: str) -> bool:
    """恢复超时的对话"""
    state = state_manager.get_conversation_state(conversation_id)
    if state and not state.is_active:
        # 检查超时时间是否在可恢复范围内
        if can_resume(state):
            state.is_active = True
            state.timeout_warnings = 0
            state_manager._save_state(state)
            return True
    return False
```

## 🏁 对话结束条件判断

### 自然结束条件

1. **明确结束表态**
   ```python
   end_keywords = [
       "谢谢", "感谢", "明白了", "知道了", "了解了",
       "暂时这样", "先这样吧", "够了", "可以了", "不用了"
   ]
   ```

2. **处方确认完成**
   - 用户确认处方
   - 完成支付流程
   - 进入药物配送阶段

3. **目标达成**
   - 获得满意的诊疗建议
   - 解决了主要问题
   - 用户表示满意

### 异常结束条件

1. **紧急情况检测**
   ```python
   emergency_keywords = [
       "剧痛", "剧烈疼痛", "无法忍受", "呼吸困难",
       "昏迷", "意识不清", "抽搐", "大出血"
   ]
   ```
   **处理方式**: 立即建议就医，终止AI诊疗

2. **系统限制触发**
   - 达到最大对话轮数(20轮)
   - 检测到危险药物推荐
   - 用户行为异常

3. **超时机制触发**
   - 会话超时(30分钟)
   - 多次响应超时(3次)

## 🎨 用户体验改进方案

### 智能进度提示

```python
def get_conversation_progress(conversation_id: str) -> Dict[str, Any]:
    """获取对话进度信息"""
    stage_weights = {
        ConversationStage.INQUIRY: 0.1,           # 10%
        ConversationStage.DETAILED_INQUIRY: 0.3,  # 30%
        ConversationStage.INTERIM_ADVICE: 0.5,    # 50%
        ConversationStage.DIAGNOSIS: 0.7,         # 70%
        ConversationStage.PRESCRIPTION: 0.9,      # 90%
        ConversationStage.PRESCRIPTION_CONFIRM: 0.95, # 95%
        ConversationStage.COMPLETED: 1.0          # 100%
    }
```

### 阶段引导系统

每个阶段都提供：
- **当前任务说明**: 让用户明确当前阶段的目标
- **操作建议**: 提示用户应该做什么
- **预期时间**: 告知大概需要多长时间
- **常见问题**: 提供快速回复选项

### 智能提醒功能

```python
def get_stage_guidance(conversation_id: str) -> Dict[str, Any]:
    """获取阶段引导信息"""
    guidance = {
        ConversationStage.INQUIRY: {
            "title": "症状收集",
            "description": "请详细描述您的主要不适症状",
            "suggestions": [
                "症状具体表现如何？",
                "什么时候开始出现的？",
                "有什么诱发因素吗？"
            ],
            "estimated_time": "2-3分钟"
        }
        # ... 其他阶段
    }
```

## 🔧 核心技术实现

### 状态持久化

```sql
-- 对话状态表
CREATE TABLE conversation_states (
    conversation_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    doctor_id TEXT NOT NULL,
    current_stage TEXT NOT NULL,
    start_time DATETIME NOT NULL,
    last_activity DATETIME NOT NULL,
    turn_count INTEGER DEFAULT 0,
    has_prescription BOOLEAN DEFAULT 0,
    symptoms_collected TEXT,  -- JSON格式
    diagnosis_confidence REAL DEFAULT 0.0,
    stage_history TEXT,       -- JSON格式
    timeout_warnings INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 智能分析引擎

```python
class ConversationAnalyzer:
    """对话内容分析器"""
    
    def analyze_user_message(self, message: str, current_stage: ConversationStage,
                           turn_count: int, conversation_history: List[Dict]) -> AnalysisResult:
        """分析用户消息，返回建议的状态转换"""
        # 1. 意图识别
        intent = self._analyze_user_intent(message)
        
        # 2. 症状提取
        symptoms = self._extract_symptoms(message)
        
        # 3. 结束条件检查
        should_end = self._check_end_conditions(message)
        
        # 4. 阶段转换建议
        suggested_stage = self._suggest_stage_transition(
            current_stage, intent, symptoms, turn_count
        )
        
        return AnalysisResult(...)
```

### API接口设计

```python
# RESTful API 接口
GET    /api/consultation/conversation/{id}/progress     # 获取进度
GET    /api/consultation/conversation/{id}/guidance     # 获取引导
POST   /api/consultation/conversation/{id}/confirm      # 确认处方
POST   /api/consultation/conversation/{id}/end          # 结束对话
GET    /api/consultation/conversation/{id}/summary      # 获取摘要
```

## 📈 性能与监控

### 关键指标

- **状态转换准确率**: > 85%
- **用户满意度**: > 4.2/5.0
- **对话完成率**: > 78%
- **平均问诊轮数**: 8-12轮
- **平均会话时长**: 15-25分钟

### 监控告警

```python
# 异常情况监控
def monitor_conversation_health():
    metrics = {
        "stuck_conversations": get_stuck_count(),      # 卡住的对话
        "timeout_rate": get_timeout_rate(),            # 超时率
        "error_rate": get_error_rate(),                # 错误率
        "avg_completion_time": get_avg_completion()    # 平均完成时间
    }
    
    # 触发告警
    if metrics["timeout_rate"] > 0.1:  # 10%
        alert_admin("对话超时率过高")
```

## 🚀 部署与运维

### 数据库迁移

```bash
# 初始化对话状态数据库
sqlite3 data/user_history.sqlite < migrations/004_conversation_states.sql

# 创建索引优化查询
CREATE INDEX idx_conversation_active ON conversation_states(is_active, last_activity);
CREATE INDEX idx_conversation_stage ON conversation_states(current_stage);
```

### 定期维护

```python
# 清理过期对话
def cleanup_expired_conversations():
    """清理30天前的非活跃对话"""
    cutoff_date = datetime.now() - timedelta(days=30)
    count = state_manager.cleanup_expired_conversations(30)
    logger.info(f"清理过期对话: {count} 个")

# 定时任务
schedule.every(1).hours.do(cleanup_expired_conversations)
```

### 故障恢复

```python
def recover_conversation_system():
    """系统故障后的恢复流程"""
    # 1. 检查数据库完整性
    check_database_integrity()
    
    # 2. 重新初始化活跃对话
    active_conversations = get_active_conversations()
    for conv_id in active_conversations:
        validate_conversation_state(conv_id)
    
    # 3. 重建缓存
    rebuild_conversation_cache()
    
    logger.info("对话状态系统恢复完成")
```

## 📝 测试用例

### 完整对话流程测试

```python
async def test_complete_conversation_flow():
    """测试完整的对话流程"""
    conversation_id = "test_" + uuid.uuid4().hex[:8]
    
    # 1. 创建对话
    state = state_manager.create_conversation(conversation_id, "user123", "zhang_zhongjing")
    assert state.current_stage == ConversationStage.INQUIRY
    
    # 2. 症状描述
    await simulate_user_message("我最近头痛，失眠")
    state = state_manager.get_conversation_state(conversation_id)
    assert state.current_stage == ConversationStage.DETAILED_INQUIRY
    
    # 3. 详细问诊
    await simulate_multiple_rounds(5)
    
    # 4. 诊断阶段
    state = state_manager.get_conversation_state(conversation_id)
    assert state.current_stage == ConversationStage.DIAGNOSIS
    
    # 5. 处方确认
    await simulate_prescription_flow(conversation_id)
    
    # 6. 对话结束
    final_state = state_manager.get_conversation_state(conversation_id)
    assert not final_state.is_active
```

## 🎉 使用示例

### 启动演示

```bash
# 1. 启动测试服务
python api/main.py

# 2. 运行对话状态测试
python test_conversation_state.py

# 3. 访问演示页面
http://localhost:8000/static/conversation_state_demo.html
```

### 基本使用

```python
from core.consultation.unified_consultation_service import get_consultation_service

# 获取服务实例
service = get_consultation_service()

# 创建问诊请求
request = ConsultationRequest(
    message="医生您好，我最近头痛",
    conversation_id="conv_123",
    selected_doctor="zhang_zhongjing"
)

# 处理问诊
response = await service.process_consultation(request)

# 检查状态
print(f"当前阶段: {response.stage}")
print(f"对话活跃: {response.conversation_active}")
print(f"需要确认: {response.requires_confirmation}")
```

## 📋 总结

TCM-AI对话状态管理机制提供了：

✅ **智能状态转换**: 基于AI分析的自动状态管理  
✅ **用户体验优化**: 清晰的进度指示和引导信息  
✅ **处方确认流程**: 安全的处方确认和风险提示  
✅ **超时保护机制**: 多级超时检查和恢复功能  
✅ **灵活结束条件**: 自然和异常情况的智能识别  
✅ **完整生命周期**: 从创建到结束的全程管理  
✅ **数据持久化**: 可靠的状态存储和历史记录  
✅ **监控告警**: 实时的系统健康监控  

这个系统显著改善了中医问诊的用户体验，使得AI问诊流程更加自然、专业和可控。

---

**更新时间**: 2025-09-14  
**版本**: v1.0.0  
**维护者**: TCM-AI Development Team