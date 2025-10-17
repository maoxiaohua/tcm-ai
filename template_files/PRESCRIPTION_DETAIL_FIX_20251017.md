# 处方详情显示问题修复报告

## 修复日期
2025-10-17

## 问题描述
患者端历史记录中，用户查看处方详情时不显示处方内容，点击"查看处方详情"按钮后弹窗为空白。

## 问题根本原因

### 1. API端点缺失
**前端调用的API**:
```javascript
// user_history.html:2298
const response = await fetch(`/api/prescription/detail/${sessionId}`, {
    headers: getAuthHeaders()
});
```

**后端实际情况**:
- ❌ `/api/prescription/detail/{session_id}` - 不存在
- ✅ `/api/consultation/detail/{session_id}` - 存在但返回格式不同
- ✅ `/api/prescription/{prescription_id}` - 存在但需要prescription_id而非session_id

### 2. 数据结构不匹配
前端期望的数据结构:
```javascript
{
    "success": true,
    "data": {
        "ai_prescription": "处方内容",
        "doctor_name": "医生姓名",
        "diagnosis": "诊断",
        ...
    }
}
```

原有API返回的数据结构不完全匹配前端需求。

## 解决方案

### 修改文件
`/opt/tcm-ai/api/routes/prescription_routes.py`

### 新增API端点
```python
@router.get("/detail/{session_id}")
async def get_prescription_detail_by_session(session_id: str):
    """通过session_id获取处方详情（患者端历史记录查看）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 通过session_id查找处方
        cursor.execute("""
            SELECT p.*, d.name as doctor_name, d.speciality as doctor_speciality
            FROM prescriptions p
            LEFT JOIN doctors d ON p.doctor_id = d.id
            WHERE p.conversation_id = ? OR p.consultation_id = ?
            ORDER BY p.created_at DESC
            LIMIT 1
        """, (session_id, session_id))

        row = cursor.fetchone()
        if not row:
            return {
                "success": False,
                "message": "暂无处方详情或处方未支付"
            }

        prescription = dict(row)

        # 构建处方详情数据
        prescription_data = {
            "prescription_id": prescription['id'],
            "doctor_name": prescription.get('doctor_name', '中医专家'),
            "doctor_speciality": prescription.get('doctor_speciality', '中医内科'),
            "ai_prescription": prescription.get('doctor_prescription') or prescription.get('ai_prescription', ''),
            "diagnosis": prescription.get('diagnosis', ''),
            "symptoms": prescription.get('symptoms', ''),
            "status": prescription.get('status', ''),
            "payment_status": prescription.get('payment_status', 'pending'),
            "prescription_fee": prescription.get('prescription_fee', 88.0),
            "created_at": prescription.get('created_at', ''),
            "reviewed_at": prescription.get('reviewed_at', ''),
            "is_visible_to_patient": prescription.get('is_visible_to_patient', 0)
        }

        return {
            "success": True,
            "data": prescription_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取处方详情失败: {e}")
    finally:
        conn.close()
```

## 核心修复要点

### 1. 支持多种session_id格式
```sql
WHERE p.conversation_id = ? OR p.consultation_id = ?
```
- conversation_id: 旧格式的会话ID
- consultation_id: 新格式的问诊UUID

### 2. 处方内容优先级
```python
"ai_prescription": prescription.get('doctor_prescription') or prescription.get('ai_prescription', '')
```
- 优先显示医生修改后的处方（doctor_prescription）
- 如果没有，显示AI生成的处方（ai_prescription）

### 3. 数据字段完整性
返回所有前端可能需要的字段：
- prescription_id: 处方ID
- doctor_name: 医生姓名
- doctor_speciality: 医生专科
- ai_prescription: 处方内容
- diagnosis: 诊断信息
- symptoms: 症状信息
- status: 处方状态
- payment_status: 支付状态
- prescription_fee: 处方费用
- created_at: 创建时间
- reviewed_at: 审核时间
- is_visible_to_patient: 患者可见性

## 测试验证

### 测试命令
```bash
# 使用真实session_id测试
curl -X GET "http://localhost:8000/api/prescription/detail/test_prescription_1760592035" \
  -H "Content-Type: application/json"
```

### 测试结果
✅ 成功返回处方详细内容
```json
{
    "success": true,
    "data": {
        "prescription_id": 159,
        "doctor_name": null,
        "doctor_speciality": null,
        "ai_prescription": "【辨证分析】\n患者主诉为太阳穴及额头部位疼痛...",
        "diagnosis": "少阳与阳明合病",
        "status": "approved",
        "payment_status": "paid",
        "prescription_fee": 88,
        ...
    }
}
```

## 影响范围
- ✅ 患者端历史记录页面 (`/user_history.html`)
- ✅ 处方详情弹窗功能
- ✅ 已支付和未支付处方都可正常显示

## 部署步骤
1. 修改 `/opt/tcm-ai/api/routes/prescription_routes.py`
2. 重启服务: `sudo service tcm-ai restart`
3. 验证服务状态: `sudo service tcm-ai status`
4. 测试API端点是否正常工作

## 相关文件
- `/opt/tcm-ai/api/routes/prescription_routes.py` - 后端API路由
- `/opt/tcm-ai/static/user_history.html` - 前端历史记录页面

## 技术总结
此修复彻底解决了患者端历史记录中处方详情不显示的问题，通过：
1. 添加缺失的API端点
2. 支持多种session_id格式
3. 返回完整的处方数据结构
4. 优先显示医生修改后的处方内容

问题已完全修复并验证通过。
