# 医生工作台统计和风险分析优化

## 问题描述

用户反馈三个问题：
1. **今日已审查统计为0**：明明今天审查了处方，但统计显示0
2. **风险分析无数据**：提示"AI没有获取到处方数据"
3. **工作统计不准确**：医生管理端的各项统计数据不对

## 根本原因分析

### 1. doctor_id 类型不匹配 🔑

**数据库实际存储**：
```sql
SELECT doctor_id, typeof(doctor_id) FROM prescriptions;
-- 结果: jin_daifu | text
```

**API查询代码**（错误）：
```python
cursor.execute("""
    SELECT COUNT(*) FROM prescriptions
    WHERE doctor_id = ? AND DATE(reviewed_at) = DATE('now')
""", (current_doctor.id,))  # current_doctor.id = 1（整数）
```

**问题**：数据库中存储的是字符串`"jin_daifu"`，但查询使用整数`1`，导致匹配失败，统计结果为0。

### 2. 风险分析处方范围过窄

**原始逻辑**：只分析待审查处方（status IN 'pending', 'ai_generated', 'awaiting_review'）

**问题**：
- 如果所有处方都已审查（status='approved'），查询返回空结果
- 无法识别近期处方中的共性问题和趋势

**中医诊疗角度分析**：
从资深中医的角度，风险分析应该包括：
1. ✅ **待审查处方**（优先级最高）- 未经医生确认，存在潜在风险
2. ✅ **近期已审查处方**（7天内）- 识别共性问题、疾病模式、用药趋势
3. ✅ **综合分析** - 给出有价值的改进建议

这样的分析才能：
- 帮助医生快速识别高风险处方
- 发现诊疗中的系统性问题
- 提供基于数据的改进方向

## 解决方案

### 1. 修复 doctor_id 类型匹配

**修改文件**：`/opt/tcm-ai/api/routes/doctor_routes.py`

**修改内容**：
```python
@router.get("/statistics")
async def get_doctor_statistics(current_doctor: Doctor = Depends(get_current_doctor)):
    """获取医生工作统计"""

    # 🔑 医生ID映射：数据库中doctor_id是字符串类型
    doctor_id_mapping = {
        1: "jin_daifu",
        2: "ye_tianshi",
        3: "li_dongyuan",
        4: "zhang_zhongjing",
        5: "liu_duzhou",
        6: "zheng_qin_an"
    }
    doctor_id_str = doctor_id_mapping.get(current_doctor.id, str(current_doctor.id))

    # 使用字符串ID查询
    cursor.execute("""
        SELECT COUNT(*) FROM prescriptions
        WHERE doctor_id = ? AND DATE(reviewed_at) = DATE('now')
    """, (doctor_id_str,))  # 使用字符串类型
```

**同时优化待审查状态**：
```python
cursor.execute("""
    SELECT COUNT(*) FROM prescriptions
    WHERE status IN ('pending', 'doctor_reviewing', 'ai_generated', 'awaiting_review')
""")
```

### 2. 优化风险分析处方范围

**修改文件**：`/opt/tcm-ai/api/routes/prescription_ai_routes.py`

**优化逻辑**：
```python
@router.get("/risk-analysis")
async def get_risk_analysis(authorization: Optional[str] = Header(None)):
    """获取风险分析报告

    从中医诊疗角度，分析以下处方：
    1. 待审查处方：AI生成但未经医生确认，需优先关注
    2. 近期已审查处方：识别共性问题和改进趋势
    """

    # 1. 获取待审查处方（优先级最高）
    cursor.execute("""
        SELECT id, ai_prescription, doctor_prescription, diagnosis, symptoms,
               patient_name, created_at, status
        FROM prescriptions
        WHERE status IN ('pending', 'ai_generated', 'awaiting_review', 'doctor_reviewing')
        ORDER BY created_at DESC
        LIMIT 30
    """)
    pending_prescriptions = cursor.fetchall()

    # 2. 获取近7天已审查处方（识别趋势）
    cursor.execute("""
        SELECT id, ai_prescription, doctor_prescription, diagnosis, symptoms,
               patient_name, created_at, status, reviewed_at
        FROM prescriptions
        WHERE status IN ('approved', 'rejected')
          AND reviewed_at >= datetime('now', '-7 days')
        ORDER BY reviewed_at DESC
        LIMIT 30
    """)
    recent_reviewed = cursor.fetchall()

    # 准备处方数据
    prescriptions_data = []

    # 添加待审查处方（标记为高优先级）
    for p in pending_prescriptions:
        prescriptions_data.append({
            'id': p['id'],
            'prescription_content': p['ai_prescription'] or p['doctor_prescription'] or '',
            'diagnosis': p['diagnosis'] or '',
            'symptoms': p['symptoms'] or '',
            'status': p['status'],
            'priority': 'high'  # 待审查=高优先级
        })

    # 添加近期已审查处方（用于趋势分析）
    for p in recent_reviewed:
        prescriptions_data.append({
            'id': p['id'],
            'prescription_content': p['ai_prescription'] or p['doctor_prescription'] or '',
            'diagnosis': p['diagnosis'] or '',
            'symptoms': p['symptoms'] or '',
            'status': p['status'],
            'priority': 'normal'  # 已审查=正常优先级
        })

    risk_analysis = ai_analyzer.analyze_risk_assessment(prescriptions_data)

    # 添加统计信息
    risk_analysis['prescription_counts'] = {
        'pending': len(pending_prescriptions),
        'recent_reviewed': len(recent_reviewed),
        'total_analyzed': len(prescriptions_data)
    }
```

## 测试验证

### 1. 数据库验证
```bash
sqlite3 /opt/tcm-ai/data/user_history.sqlite "
  SELECT
    COUNT(*) as total,
    SUM(CASE WHEN DATE(reviewed_at)=DATE('now') THEN 1 ELSE 0 END) as today
  FROM prescriptions
  WHERE doctor_id='jin_daifu'"
```
**结果**：`7|2` - 总共7个，今天审查2个 ✅

### 2. 统计API测试
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/doctor/statistics
```

**结果**：
```json
{
  "success": true,
  "statistics": {
    "total_reviewed": 7,     ✅ 正确
    "approved": 7,           ✅ 正确
    "rejected": 0,           ✅ 正确
    "today_reviewed": 2,     ✅ 正确（之前是0）
    "pending_review": 0,     ✅ 正确
    "active_days": 3         ✅ 正确
  }
}
```

### 3. 风险分析API测试
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/prescription/ai/risk-analysis
```

**结果**：
```json
{
  "success": true,
  "risk_analysis": {
    "total_prescriptions": 7,
    "risk_distribution": {
      "high": 3,      ✅ 识别出高风险处方
      "medium": 3,
      "low": 1
    },
    "risk_factors": [
      {
        "factor": "糖尿病",
        "count": 3,
        "severity": "high",
        "description": "长期血糖控制不佳可能导致多种并发症"
      },
      {
        "factor": "脾胃虚弱",
        "count": 2,
        "severity": "medium",
        "description": "..."
      }
    ],
    "common_issues": [
      "患者普遍存在脾胃虚弱的情况",        ✅ 中医证型分析
      "多例患者存在水湿内停的症状",
      "糖尿病患者较多，提示需加强对该类患者的管理"
    ],
    "recommendations": [
      "对于糖尿病患者，应加强饮食控制和定期监测血糖水平",  ✅ 专业建议
      "考虑到多例患者存在脾胃虚弱的问题，建议在日常生活中注意饮食调节",
      "对于所有患者，都应鼓励适量运动，以促进气血运行，增强体质"
    ],
    "prescription_counts": {
      "pending": 0,              ✅ 待审查处方数
      "recent_reviewed": 7,      ✅ 近期已审查数
      "total_analyzed": 7        ✅ 总分析数
    }
  }
}
```

## 风险分析的中医价值

### 为什么同时分析待审查和已审查处方？

从中医临床实践角度：

**1. 待审查处方分析**（防患未然）
- **目的**：识别AI生成处方中的潜在问题
- **价值**：帮助医生优先审查高风险处方，提高审查效率
- **举例**：识别出用药剂量过大、配伍禁忌等问题

**2. 近期已审查处方分析**（总结经验）
- **目的**：发现诊疗中的系统性模式和趋势
- **价值**：
  - 识别常见证型（如"脾胃虚弱"、"水湿内停"）
  - 发现高发疾病（如"糖尿病患者较多"）
  - 优化诊疗策略（如"加强对糖尿病患者的管理"）
- **举例**：通过分析发现季节性疾病模式，提前做好准备

**3. 综合分析的优势**
- ✅ **完整视角**：既看当前风险，又看历史趋势
- ✅ **数据支撑**：基于真实诊疗数据的改进建议
- ✅ **持续改进**：形成"诊疗→分析→优化"的闭环

这就像老中医总结临床经验：不仅要处理眼前的病例，还要回顾既往案例，总结规律，持续提高诊疗水平。

## 影响范围

### 修改文件
1. `/opt/tcm-ai/api/routes/doctor_routes.py` - 修复统计API
2. `/opt/tcm-ai/api/routes/prescription_ai_routes.py` - 优化风险分析

### 受影响功能
- ✅ 医生工作台首页统计卡片 - 数据正确
- ✅ 处方审查模块统计 - 数据正确
- ✅ AI洞察分析 - 正常工作
- ✅ 风险分析 - 更全面、更有价值

## 后续建议

### 1. 数据一致性
建议在整个项目中统一`doctor_id`的数据类型：
- 选择A：全部使用字符串（如"jin_daifu"）
- 选择B：全部使用整数ID（需要数据迁移）

当前采用映射方案是权宜之计，长期应该统一。

### 2. 风险分析优化
可以考虑进一步优化：
- 按照中医证型分类统计（如"阳虚证"、"阴虚证"）
- 识别季节性疾病模式（如"秋季燥证增多"）
- 药材使用频率统计（如"附子用量趋势"）

### 3. 实时监控
建议添加：
- 统计数据异常告警（如今日审查量骤降）
- 高风险处方自动提醒
- 审查效率趋势分析

## 总结

本次修复解决了三个核心问题：
1. ✅ 修复统计数据不准确（doctor_id类型不匹配）
2. ✅ 优化风险分析范围（待审查+近期已审查）
3. ✅ 提升分析价值（中医视角的综合分析）

**最终效果**：
- 医生工作台统计数据准确无误
- 风险分析提供更全面、更有价值的中医诊疗洞察
- 帮助医生提高诊疗效率和质量

---
**修复日期**：2025-11-24
**测试状态**：✅ 通过
**Git Commit**：27a77ff
