# 🧠 决策树智能匹配功能 - 完整实现说明

**实现时间**: 2025-10-19
**功能状态**: ✅ 已完成并部署

## 📋 功能概述

实现了**患者问诊时智能匹配医生决策树**的完整功能，让医生保存的诊疗经验能够自动应用到实际问诊中。

### 核心价值

1. **知识复用**: 医生保存的决策树自动应用到相似病例
2. **提升效率**: 减少重复性诊疗思考，提高问诊效率
3. **保证质量**: 基于医生经验的标准化诊疗流程
4. **持续优化**: 记录使用情况和成功率，不断优化决策树

---

## 🏗️ 系统架构

### 1. 核心组件

```
┌─────────────────────────────────────────────┐
│         患者问诊流程                        │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  UnifiedConsultationService                 │
│  (统一问诊服务)                            │
│                                             │
│  - 接收患者消息                            │
│  - 提取疾病和症状                          │
│  - 调用决策树匹配器 ◄────────┐            │
└──────────────┬──────────────────│───────────┘
               │                  │
               ▼                  │
┌─────────────────────────────────┴───────────┐
│  DecisionTreeMatcher                        │
│  (决策树智能匹配器)                        │
│                                             │
│  - 基于疾病名称匹配                        │
│  - 基于症状列表匹配                        │
│  - 基于文本相似度匹配                      │
│  - 综合评分排序                            │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  doctor_clinical_patterns 表                │
│  (医生决策树数据库)                        │
│                                             │
│  - pattern_id: 决策树ID                    │
│  - doctor_id: 医生ID                       │
│  - disease_name: 疾病名称                  │
│  - thinking_process: 诊疗思路              │
│  - tree_structure: 决策树结构              │
│  - usage_count: 使用次数                   │
│  - success_count: 成功次数                 │
└─────────────────────────────────────────────┘
```

### 2. 匹配算法

**匹配分数计算公式**:

```python
总分 = 疾病匹配分(40%) + 症状匹配分(40%) + 文本相似度(20%)

其中:
- 疾病完全匹配: 0.4分
- 疾病别名匹配: 0.3分
- 疾病部分匹配: 0.2分

- 症状匹配度 = 匹配症状数 / 总症状数

- 文本相似度 = Jaccard相似度(基于分词)

最终置信度 = (历史成功率 * 0.7) + (匹配分数 * 0.3)
```

---

## 📁 新增文件

### 1. 决策树匹配服务
**文件**: `/opt/tcm-ai/core/consultation/decision_tree_matcher.py`

**核心类**:
- `DecisionTreeMatch`: 匹配结果数据类
- `DecisionTreeMatcher`: 智能匹配器

**主要方法**:
```python
async def find_matching_patterns(
    disease_name: str,
    symptoms: List[str],
    patient_description: str,
    doctor_id: Optional[str] = None,
    min_match_score: float = 0.3
) -> List[DecisionTreeMatch]
```

### 2. 使用记录API
**文件**: `/opt/tcm-ai/api/routes/decision_tree_usage_routes.py`

**API端点**:
- `POST /api/decision-tree/record-usage` - 记录使用情况
- `GET /api/decision-tree/stats/{pattern_id}` - 获取统计数据

---

## 🔧 修改的文件

### 1. 统一问诊服务
**文件**: `/opt/tcm-ai/core/consultation/unified_consultation_service.py`

**主要修改**:

#### 新增导入
```python
from core.consultation.decision_tree_matcher import get_decision_tree_matcher
```

#### 初始化决策树匹配器
```python
# 🧠 决策树匹配服务（新增）
self.decision_tree_matcher = get_decision_tree_matcher()

# 决策树匹配结果缓存
self.pattern_match_cache = {}
```

#### 增强思维库查询函数
```python
async def _get_thinking_library_context(
    self,
    request: ConsultationRequest,
    conversation_state
) -> Optional[Dict]:
    """🧠 获取思维库上下文（智能决策树匹配版本）"""

    # 1. 检查缓存
    # 2. 提取疾病和症状
    # 3. 调用智能匹配器
    # 4. 返回最佳匹配结果
```

#### 新增辅助函数
```python
def _extract_symptoms_from_conversation() -> List[str]
def _build_patient_description() -> str
def _format_pattern_context(pattern) -> Dict
```

#### 增强AI提示词
```python
# 集成决策树信息到提示词
🧠 **智能决策树匹配** (匹配度: 85%, 置信度: 90%, 历史成功率: 95%)

**匹配的疾病**: 失眠

**您的诊疗思路** (来自您保存的决策树):
失眠多因心火旺盛或心脾两虚所致...

**🎯 重要指示**:
1. **优先使用决策树思路**: 上述诊疗思路是您之前针对该疾病总结的宝贵经验，请作为首要参考
2. **处方生成**: 如果需要开具处方，请严格遵循决策树中的用药思路和方剂选择
3. **个性化调整**: 根据当前患者的具体症状，对决策树方案进行必要的加减化裁
4. **保持一致性**: 确保您的诊疗建议与决策树中的思维模式保持一致
```

### 2. 主应用路由
**文件**: `/opt/tcm-ai/api/main.py`

**修改内容**:
```python
# 导入新路由
from api.routes.decision_tree_usage_routes import router as decision_tree_usage_router

# 注册路由
app.include_router(decision_tree_usage_router)  # 🧠 决策树使用记录
```

---

## 🔄 完整工作流程

### 患者问诊流程

```
1. 患者发送消息: "我最近失眠，每天睡不着觉"
   ↓
2. UnifiedConsultationService 接收并分析:
   - 提取疾病: "失眠"
   - 提取症状: ["失眠", "睡不着"]
   - 构建描述: "我最近失眠，每天睡不着觉"
   ↓
3. 调用 DecisionTreeMatcher.find_matching_patterns():
   - 查询数据库中所有决策树
   - 计算匹配分数:
     * 疾病匹配: 失眠 = 失眠 (完全匹配) → 0.4分
     * 症状匹配: 2/5 → 0.16分
     * 文本相似度: 0.25 → 0.05分
     * 总分: 0.61 (61%)
   - 返回最佳匹配
   ↓
4. 格式化决策树上下文:
   - 疾病名称: 失眠
   - 诊疗思路: "失眠多因心火旺盛或心脾两虚所致..."
   - 匹配度: 61%
   - 历史成功率: 85%
   ↓
5. 构建AI提示词:
   - 基础医生人格提示
   - 🧠 决策树智能匹配上下文
   - 对话历史
   ↓
6. 调用AI生成回复:
   - AI基于决策树思路回答
   - 如果需要开方，遵循决策树方案
   ↓
7. 返回给患者:
   - 包含诊疗建议
   - 如有处方，基于决策树生成
   ↓
8. (可选) 处方确认后记录使用:
   - 调用 /api/decision-tree/record-usage
   - 更新 usage_count 和 success_count
```

---

## 📊 使用示例

### 示例1: 医生保存决策树

**决策树页面操作**:
```
1. 医生访问: https://mxh0510.cn/static/decision_tree_visual_builder.html
2. 登录后自动加载医生信息
3. 填写:
   - 疾病名称: 失眠
   - 诊疗思路: 失眠多因心火旺盛或心脾两虚所致。
     心火旺盛者常伴心烦、口干、舌尖红；
     心脾两虚者常伴心悸、健忘、面色萎黄。
     治疗当清心安神或补益心脾。
4. 点击"🤖 智能生成决策树"
5. AI生成完整决策树结构
6. 点击"💾 保存到思维库"
```

**数据库记录**:
```sql
INSERT INTO doctor_clinical_patterns (
    id, doctor_id, disease_name, thinking_process,
    tree_structure, clinical_patterns, doctor_expertise,
    usage_count, success_count, created_at, updated_at
) VALUES (
    'pattern_失眠_20251019_001',
    'zhang_zhongjing',
    '失眠',
    '失眠多因心火旺盛或心脾两虚所致...',
    '{"nodes": [...], "edges": [...]}',
    '{"key_decision_points": [...]}',
    '{"specialization": "心神疾病"}',
    0, 0, '2025-10-19 00:00:00', '2025-10-19 00:00:00'
);
```

### 示例2: 患者问诊自动匹配

**患者端操作**:
```
患者: 我最近失眠，晚上睡不着，心烦口干

系统后台自动处理:
1. 识别疾病: 失眠
2. 提取症状: [失眠, 心烦, 口干]
3. 匹配决策树: pattern_失眠_20251019_001
4. 匹配分数: 78%
5. 置信度: 85%

AI医生回复:
根据您的症状 - 失眠伴心烦口干，这是典型的心火旺盛证候。

【辨证分析】
心火旺盛，扰动心神，故见失眠心烦；
火热内盛，津液耗伤，故见口干。

【治疗思路】
治以清心泻火，养心安神。

【处方建议】
黄连阿胶汤加减:
- 黄连 6g (清心泻火)
- 阿胶 9g (养心安神)
- 白芍 12g (养血柔肝)
- 鸡子黄 2枚 (滋阴安神)
...
```

**系统日志**:
```
INFO:  🔍 识别到疾病: 失眠
INFO:  🔍 提取到症状: ['失眠', '心烦', '口干']
INFO:  ✅ 找到最佳决策树匹配: pattern_失眠_20251019_001,
       疾病=失眠, 匹配分数=78%, 置信度=85%
INFO:  🧠 决策树智能匹配已集成 (匹配度:78%, ID:pattern_失眠_20251019_001)
```

### 示例3: 记录使用情况

**患者确认处方后**:
```javascript
// 前端调用
await fetch('/api/decision-tree/record-usage', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        pattern_id: 'pattern_失眠_20251019_001',
        conversation_id: 'conv_123',
        success: true,  // 患者确认了处方
        feedback: '患者对处方表示满意'
    })
});
```

**数据库更新**:
```sql
UPDATE doctor_clinical_patterns
SET usage_count = usage_count + 1,
    success_count = success_count + 1,
    last_used_at = '2025-10-19 00:10:00'
WHERE id = 'pattern_失眠_20251019_001';

-- 结果: usage_count=1, success_count=1, success_rate=100%
```

---

## 📈 监控和统计

### 查看决策树统计

**API调用**:
```bash
curl https://mxh0510.cn/api/decision-tree/stats/pattern_失眠_20251019_001
```

**响应**:
```json
{
    "success": true,
    "data": {
        "pattern_id": "pattern_失眠_20251019_001",
        "disease_name": "失眠",
        "doctor_id": "zhang_zhongjing",
        "usage_count": 15,
        "success_count": 13,
        "success_rate": 86.67,
        "confidence": 0.88
    }
}
```

### 系统日志监控

**查看实时日志**:
```bash
sudo journalctl -u tcm-ai -f | grep "决策树"
```

**关键日志**:
```
Oct 19 00:10:00 tcm-ai[xxx]: INFO 🔍 识别到疾病: 失眠
Oct 19 00:10:00 tcm-ai[xxx]: INFO ✅ 找到最佳决策树匹配
Oct 19 00:10:00 tcm-ai[xxx]: INFO 🧠 决策树智能匹配已集成
Oct 19 00:10:05 tcm-ai[xxx]: INFO ✅ 记录决策树使用: pattern_xxx, 成功=True
```

---

## 🎯 性能优化

### 1. 缓存机制
```python
# 对话级别缓存
self.pattern_match_cache = {
    conversation_id: (pattern_id, match_score, matched_pattern)
}

# 好处:
# - 同一对话多次匹配无需重复查询
# - 减少数据库访问
# - 提升响应速度
```

### 2. 数据库索引
```sql
-- 已有索引
CREATE INDEX idx_patterns_doctor ON doctor_clinical_patterns(doctor_id);
CREATE INDEX idx_patterns_disease ON doctor_clinical_patterns(disease_name);
CREATE INDEX idx_patterns_usage ON doctor_clinical_patterns(usage_count DESC);
```

---

## 🔒 安全和质量保证

### 1. 匹配阈值控制
```python
min_match_score = 0.3  # 最小30%匹配度才使用
```

### 2. 置信度评估
```python
confidence = (success_rate * 0.7) + (match_score * 0.3)
# 综合历史成功率和当前匹配度
```

### 3. 医疗安全
- 决策树仅作为参考，AI仍会根据具体症状调整
- 保留医疗安全检查机制
- 所有处方包含免责声明

---

## 🚀 后续优化方向

### 1. 机器学习增强
- 基于使用反馈自动调整匹配权重
- 学习医生决策偏好

### 2. 多决策树融合
- 当匹配到多个相关决策树时，融合建议
- 提供综合诊疗方案

### 3. 可视化展示
- 在医生端显示决策树使用统计
- 患者端显示诊疗依据来源

### 4. A/B测试
- 对比有无决策树的诊疗效果
- 持续优化匹配算法

---

## 📚 相关文档

- [决策树构建指南](./DECISION_TREE_USER_GUIDE.md)
- [CLAUDE.md](../CLAUDE.md) - 项目总体说明
- [API文档](../api/routes/decision_tree_usage_routes.py)

---

**实现完成**: ✅ 2025-10-19
**服务状态**: 🟢 运行中
**下次更新**: 根据实际使用反馈优化

