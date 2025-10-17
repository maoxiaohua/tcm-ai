# TCM-AI 开发指导和错误防范手册

## 📋 常见错误及防范措施

### 🚨 高频错误清单

#### 1. API端点命名错误
**错误模式**: 
- 写成 `/chat` 但实际应该是 `/chat_with_ai`
- 写成 `/api/chat` 但实际应该是 `/api/consultation/chat`

**防范措施**:
```javascript
// ❌ 错误示例
fetch('/chat', { ... })  // 会导致404

// ✅ 正确做法 - 先确认端点
// 智能工作流程使用统一问诊服务
fetch('/api/consultation/chat', { ... })

// 原系统兼容接口
fetch('/chat_with_ai', { ... })
```

**检查清单**:
- [ ] 确认使用的是哪个系统（智能工作流程 vs 原系统）
- [ ] 检查 API 路由表中的实际端点名称
- [ ] 测试时先用 curl 验证端点存在

#### 2. 参数格式不匹配
**错误模式**:
- 前端传递数字ID (`"1", "2"`) 但后端期望医生名称 (`"zhang_zhongjing"`)
- 前端传递 `selected_doctor` 但后端期望 `doctor_name`

**防范措施**:
```javascript
// ❌ 错误示例  
{
  selected_doctor: "1"  // 数字ID
}

// ✅ 正确做法 - 使用映射
const doctorIdMapping = {
  '1': 'zhang_zhongjing',
  '2': 'ye_tianshi'
};

{
  selected_doctor: doctorIdMapping[selectedDoctorId] || 'zhang_zhongjing'
}
```

**检查清单**:
- [ ] 确认前端传递的参数名称和格式
- [ ] 确认后端期望的参数名称和格式  
- [ ] 检查是否需要ID映射或格式转换

#### 3. 响应数据结构不匹配
**错误模式**:
- 期望 `data.reply` 但实际是 `reply`
- 期望简单对象但实际是嵌套在 `data` 中

**防范措施**:
```javascript
// ❌ 错误示例
const data = await response.json();
addMessage('ai', data.reply);  // data.reply 可能不存在

// ✅ 正确做法 - 处理不同的响应格式
const result = await response.json();
let reply;

if (result.success && result.data) {
  // 统一问诊服务格式
  reply = result.data.reply;
} else if (result.reply) {
  // 原系统格式
  reply = result.reply;
} else {
  reply = '系统暂时无法响应';
}

addMessage('ai', reply);
```

#### 4. 数据库字段名称错误
**错误模式**:
- 查询中使用 `uuid` 但表中字段是 `id`
- 查询中使用 `specialties` 但表中字段是 `speciality`

**防范措施**:
```sql
-- ❌ 错误示例
SELECT * FROM doctors WHERE uuid = ?  -- uuid 字段不存在

-- ✅ 正确做法 - 先检查表结构
-- 使用：sqlite3 database.sqlite ".schema doctors"
SELECT * FROM doctors WHERE id = ?
```

**检查清单**:
- [ ] 使用 `.schema table_name` 确认表结构
- [ ] 注意单复数形式 (specialty vs specialties)
- [ ] 确认字段类型是否匹配

#### 5. 处方内容未正确隐藏错误
**错误模式**:
- 处方内容直接显示给患者，而不是付费后才显示
- `addMessage` 函数的 `hidePrescription` 默认值设置不当
- 处方检测逻辑存在但未正确调用

**防范措施**:
```javascript
// ❌ 错误示例 - 默认隐藏所有内容
function addMessage(sender, content, hidePrescription = true) {
    // 这样会默认隐藏所有AI回复
}

// ✅ 正确做法 - 明确指定何时隐藏处方
function addMessage(sender, content, hidePrescription = false) {
    // 只在明确检测到完整处方时才隐藏
}

// 调用时明确传递隐藏参数
let needsPayment = false;
if (data.stage === 'prescription' && data.contains_prescription) {
    needsPayment = true;
} else if (containsPrescriptionContent(reply) && !isTemporaryAdvice(reply)) {
    needsPayment = true;
}
addMessage('ai', reply, needsPayment);
```

**具体修复实例**:
```javascript
// 处方关键词必须包含中医特色格式
const prescriptionKeywords = [
    '处方如下', '方剂组成', '药物组成', '具体方药',
    '方解', '君药', '臣药', '佐药', '使药',
    '【君药】', '【臣药】', '【佐药】', '【使药】',  // 关键：中文标记格式
    '三、处方建议'  // 关键：结构化标题格式
];

// 正则表达式也要同步更新
const prescriptionStart = content.search(/(?:处方如下|方剂组成|【君药】|【臣药】|【佐药】|【使药】|三、处方建议)/);
```

**检查清单**:
- [ ] 确认 `addMessage` 函数默认值设置正确
- [ ] 验证处方检测逻辑被正确调用
- [ ] 确保 `containsPrescriptionContent` 和 `maskPrescriptionContent` 使用相同的关键词
- [ ] 测试支付流程和处方解锁功能
- [ ] 确保临时建议不会触发支付
- [ ] 验证中文标记格式【君药】【臣药】等被正确识别

#### 6. 医生问诊质量差异问题
**错误模式**:
- 不同医生的问诊深度差异很大，有些医生直接给出处方不详细问诊
- 临时建议关键词不全面，遗漏"待补充舌象信息后确认"等表述
- AI提示词中包含"积极开方"等导致过早处方的指导

**防范措施**:
```python
# 扩展临时建议关键词，覆盖更多表述
temporary_keywords = [
    '初步处方建议', '待确认', '若您能提供', '请补充', 
    '需要了解', '建议进一步', '完善信息后', '详细描述',
    '暂拟方药', '初步考虑', '待详诊后', '待补充',
    '补充舌象', '舌象信息后', '脉象信息后', '上传舌象',  # 关键补充
    '提供舌象', '确认处方', '后确认', '暂拟处方'
]

# 医生人格的思维模式强调详细问诊
thinking_pattern = "....**问诊原则：循序渐进，从主症到兼症，从现在到既往，必须详细了解患者的基本信息、症状特点、舌象脉象、病史等，信息充分后才能给出准确诊断和处方。宁可多问几轮，也不可草率开方**"
```

**AI提示词优化**:
```python
# 移除导致急于开方的指导
❌ "积极开方: 在症状和体征信息充足时，应给出具体的治疗方案"
✅ "循序渐进问诊: 需要充分了解患者信息，遵循中医四诊合参的传统"

❌ "一次性问诊原则：避免反复多轮问诊"  
✅ "循序渐进问诊：遵循中医传统，从主症到兼症，逐步了解病情"

❌ "应该一次性询问所缺失的关键信息，而非强制开方"
✅ "应该循序渐进地深入问诊，体现中医详细问诊的特色"
```

**检查清单**:
- [ ] 确保临时建议关键词覆盖中医特色表述
- [ ] 验证医生人格的思维模式强调详细问诊
- [ ] 移除AI提示词中"积极开方"相关指导
- [ ] 测试不同医生的问诊深度是否一致
- [ ] 确认舌象相关的临时建议被正确识别

#### 7. 处方关键词遗漏导致隐藏失效
**错误模式**:
- 系统生成包含"处方方案"、"治疗方案"的内容但未被隐藏
- 关键词检测不全面，遗漏常见的处方表述格式
- 前端和后端的处方关键词不同步

**防范措施**:
```javascript
// 前端处方关键词必须全面覆盖
const prescriptionKeywords = [
    '处方如下', '方剂组成', '药物组成', '具体方药',
    '方解', '君药', '臣药', '佐药', '使药',
    '【君药】', '【臣药】', '【佐药】', '【使药】',
    '三、处方建议', 
    '处方方案', '治疗方案', '用药方案'  // 🎯 关键补充
];

// 正则表达式同步更新
const prescriptionStart = content.search(/(?:处方如下|方剂组成|处方方案|治疗方案|用药方案)/);
```

```python
# 后端统一问诊服务同步更新
prescription_keywords = [
    '处方如下', '方剂组成', '药物组成', '具体方药',
    '方解', '君药', '臣药', '佐药', '使药',
    '处方方案', '治疗方案', '用药方案',  # 🎯 关键补充
    '【君药】', '【臣药】', '【佐药】', '【使药】'
]
```

**检查清单**:
- [ ] 收集AI实际输出的处方格式表述
- [ ] 确保前后端处方关键词列表完全一致
- [ ] 测试所有可能的处方表述格式
- [ ] 验证正则表达式包含所有关键词
- [ ] 进行回归测试确保修复有效

#### 8. AI过度问诊问题
**错误模式**:
- AI在患者提供充分信息时仍要求更多细节
- 开方条件过于严格，要求脉象等难以获得的信息
- 忽视已有信息的完整性和充分性

**防范措施**:
```python
# AI提示词中明确信息充分标准
"**信息充分标准**：当患者提供了主要症状（位置、性质、时间）+ 伴随症状 + 舌象描述 + 基本的食欲睡眠二便情况 + 相关病史时，即可进行辨证论治，不必过分追求脉象等难以获得的信息"

# 调整开方条件
"**开方条件**：主要症状清楚 + 舌象明确（或有详细描述）+ 证型基本确定。不必拘泥于脉象，可根据症状和舌象进行辨证"
```

**用户测试案例**:
```
用户提供: 头痛位置+性质+时间+伴随症状+舌象+食欲睡眠+病史+诱发因素
期望结果: 应给出诊断和处方，不再要求脉象、汗出等
实际结果: ❌ 仍要求补充脉象等信息
修复后: ✅ 信息充分时给出辨证论治
```

**检查清单**:
- [ ] 测试典型病例的问诊轮数是否合理
- [ ] 验证AI能识别信息充分的情况
- [ ] 确保不同医生的问诊深度一致
- [ ] 平衡详细问诊与用户体验

#### 9. 支付后处方解锁功能失效
**错误模式**:
- 支付成功后处方内容没有被正确解锁显示
- 只显示支付成功提示，但隐藏的处方依然不可见
- 原始处方内容没有被保存，无法在支付后恢复

**防范措施**:
```javascript
// 在隐藏处方时保存原始内容
if (hidePrescription) {
    // 保存原始内容到data属性中，用于支付后解锁
    messageDiv.setAttribute('data-original-content', formattedContent);
    formattedContent = maskPrescriptionContent(formattedContent);
    messageDiv.classList.add('prescription-hidden');  // 添加标记类
}

// 支付成功后恢复原始内容
function paymentSuccess() {
    const hiddenPrescriptionMessages = document.querySelectorAll('.message.prescription-hidden');
    hiddenPrescriptionMessages.forEach(messageDiv => {
        const originalContent = messageDiv.getAttribute('data-original-content');
        if (originalContent) {
            const messageContent = messageDiv.querySelector('.message-bubble');
            messageContent.innerHTML = originalContent;  // 恢复完整内容
            messageDiv.classList.remove('prescription-hidden');
        }
    });
}
```

**测试验证**:
```
操作步骤:
1. 医生提供完整处方（包含君臣佐使分类）
2. 确认处方内容被隐藏，显示付费提示
3. 点击"查看处方详情"弹出支付模态框
4. 选择微信/支付宝进行模拟支付
5. 支付成功后验证处方内容是否完整显示

期望结果:
- ✅ 支付前：处方内容被隐藏
- ✅ 支付后：完整处方内容显示，包含所有药物、剂量、君臣佐使分类
- ✅ 解锁提示：显示"支付成功解锁"标识
```

**检查清单**:
- [ ] 确认处方隐藏时原始内容被正确保存
- [ ] 验证支付成功后能找到隐藏的处方消息
- [ ] 测试原始内容能被完整恢复显示
- [ ] 确认解锁后的视觉反馈明确
- [ ] 验证多条处方消息的批量解锁功能

#### 10. 医生回答格式不一致问题
**错误模式**:
- 不同医生的回答结构和格式存在明显差异
- 部分医生缺乏结构化的辨证论治内容
- 医生人格的思维模式指导过于简单，缺乏具体指导

**防范措施**:
```python
# 医生人格的思维模式需要详细具体
❌ thinking_pattern="重视阳气，认为万病皆由阳气不足所致"  # 过于简单

✅ thinking_pattern="重视阳气，认为万病皆由阳气不足所致。**问诊原则：详细了解阳虚症状，包括四肢厥冷、神疲乏力、脉象沉微等。需充分收集阳虚证候信息，确定阳气衰微程度后才能合理运用扶阳药物。扶阳用药须谨慎，信息不全时不应急于开方，需继续问诊以明确阳虚程度和具体病位**"
```

**统一格式要求**:
```markdown
期望的医生回答格式应包含：
1. **问诊信息收集状况** - 当前已获得的信息总结
2. **循序渐进问诊** - 结构化的追问内容
3. **初步辨证分析** - 基于已有信息的初步判断
4. **下一步指导** - 明确的后续问诊或诊疗方向

避免格式：
- 简单的一问一答
- 缺乏中医理论支撑的内容
- 没有体现医生流派特色的通用回答
```

**检查清单**:
- [ ] 验证所有医生的thinking_pattern都包含详细问诊指导
- [ ] 确保医生回答体现流派特色（扶阳派、滋阴派等）
- [ ] 测试回答格式的一致性和结构化程度
- [ ] 验证四诊合参的完整体现

#### 11. 支付解锁功能调试增强
**调试策略**:
为了解决持续的支付解锁问题，已增加详细的调试日志：

```javascript
function paymentSuccess() {
    console.log('🔍 开始支付解锁调试...');
    const hiddenPrescriptionMessages = document.querySelectorAll('.message.prescription-hidden');
    console.log(`🔍 找到 ${hiddenPrescriptionMessages.length} 个隐藏的处方消息`);
    
    // 详细的调试信息输出
    const allAIMessages = document.querySelectorAll('.message.ai');
    allAIMessages.forEach((msg, i) => {
        const hasOriginalContent = msg.hasAttribute('data-original-content');
        const isPrescriptionHidden = msg.classList.contains('prescription-hidden');
        console.log(`🔍 消息${i+1}: 有原始内容=${hasOriginalContent}, 有隐藏标记=${isPrescriptionHidden}`);
    });
}
```

**测试步骤**:
1. 打开浏览器开发者工具 (F12)
2. 进行完整的问诊获得处方
3. 确认处方被隐藏
4. 执行支付流程
5. 检查控制台调试输出
6. 分析支付解锁失败的具体原因

#### 12. 问诊流程状态判断错误
**错误模式**:
- 临时建议（"初步处方建议（待确认）"）被误判为完整处方
- 问诊未结束就触发支付流程，阻断用户继续补充信息

**防范措施**:
```javascript
// ❌ 错误示例 - 简单关键词匹配
function containsPrescription(text) {
  return text.includes('处方') || text.includes('克');
}

// ✅ 正确做法 - 区分临时建议和完整处方
function containsPrescriptionContent(text) {
  // 检查临时建议关键词
  const temporaryKeywords = ['待确认', '若您能提供', '请补充'];
  if (temporaryKeywords.some(keyword => text.includes(keyword))) {
    return false;  // 临时建议，不算完整处方
  }
  
  // 同时检查处方关键词和具体剂量
  const hasKeywords = ['处方如下', '方剂组成'].some(k => text.includes(k));
  const hasDosage = /\d+[克g]\s*[，,]/.test(text);
  
  return hasKeywords && hasDosage;
}
```

**检查清单**:
- [ ] 区分临时建议和完整处方
- [ ] 确认问诊状态判断逻辑正确
- [ ] 测试支付流程触发时机
- [ ] 验证用户可以继续补充信息

#### 6. 前端事件绑定时机错误
**错误模式**:
- DOM 元素还未加载完成就绑定事件
- 异步加载内容的事件监听器丢失

**防范措施**:
```javascript
// ❌ 错误示例 - DOM可能还未加载
document.getElementById('button').onclick = handler;

// ✅ 正确做法 - 确保DOM加载完成
document.addEventListener('DOMContentLoaded', function() {
  const button = document.getElementById('button');
  if (button) {
    button.onclick = handler;
  }
});

// ✅ 更安全的做法 - 延迟绑定
setTimeout(function() {
  const button = document.getElementById('button');
  if (button) {
    button.onclick = handler;
  }
}, 1000);
```

### 🔧 开发最佳实践

#### 1. API开发流程
```bash
# 标准开发流程
1. 确认需求 → 明确输入输出格式
2. 检查现有API → 避免重复造轮子  
3. 设计接口 → 统一命名规范
4. 实现后端 → 包含完整错误处理
5. 测试接口 → 使用curl验证
6. 前端集成 → 处理各种响应情况
7. 集成测试 → 端到端功能验证
```

#### 2. 数据库操作规范
```python
# 标准数据库操作模式
try:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row  # 使用字典式访问
        cursor = conn.execute(query, params)
        results = cursor.fetchall()
        
        # 处理结果时检查字段是否存在
        for row in results:
            name = row.get('name', 'Unknown')  # 安全访问
            # 处理JSON字段时要有异常处理
            try:
                specialties = json.loads(row['specialties'] or '[]')
            except (json.JSONDecodeError, KeyError):
                specialties = []
                
except sqlite3.Error as e:
    logger.error(f"数据库操作失败: {e}")
    return []
```

#### 3. 前端错误处理规范
```javascript
// 标准fetch请求模式
async function makeAPIRequest(url, data) {
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    
    // 处理不同的响应格式
    if (result.success !== undefined) {
      // 新API格式
      return result.success ? result.data : { error: result.message };
    } else {
      // 原API格式  
      return result;
    }
    
  } catch (error) {
    console.error('API请求失败:', error);
    return { error: error.message };
  }
}
```

### 🔍 调试技巧和工具

#### 1. 快速问题定位
```bash
# 后端调试
journalctl -u tcm-ai.service -f  # 实时查看日志
curl -X GET "http://localhost:8000/docs"  # 查看API文档

# 前端调试
浏览器F12 → Console  # 查看JavaScript错误
浏览器F12 → Network  # 查看API请求响应

# 数据库调试  
sqlite3 database.sqlite ".schema"  # 查看表结构
sqlite3 database.sqlite "SELECT * FROM table LIMIT 5;"  # 查看数据样例
```

#### 2. 常用验证命令
```bash
# API端点验证
curl -X GET "http://localhost:8000/api/consultation/service-status"

# 数据库连接验证
sqlite3 /opt/tcm-ai/data/user_history.sqlite "SELECT COUNT(*) FROM doctors;"

# 服务状态验证
systemctl status tcm-ai
```

### 📝 代码审查清单

#### 每次修改前检查
- [ ] 是否与现有系统冲突？
- [ ] 参数格式是否匹配？
- [ ] 错误处理是否完整？
- [ ] 是否需要数据库迁移？
- [ ] 前后端接口是否对齐？

#### 每次修改后验证
- [ ] API端点是否可以访问？
- [ ] 前端是否正确显示？
- [ ] 错误情况是否妥善处理？
- [ ] 是否影响其他功能？
- [ ] 性能是否符合预期？

### 🚀 持续改进机制

#### 错误记录和学习
当发现新的重复性错误时：

1. **记录错误**:
   ```markdown
   ## 新发现错误: [错误描述]
   **错误模式**: [具体错误情况]
   **根本原因**: [为什么会发生]
   **防范措施**: [如何避免]
   **检查清单**: [验证步骤]
   ```

2. **更新文档**: 立即添加到本文档
3. **创建测试**: 编写测试用例防止回归
4. **分享经验**: 在团队中分享经验教训

#### 定期文档更新
- 每月回顾常见错误，更新防范措施
- 记录新的最佳实践和开发模式
- 整理有效的调试技巧和工具使用方法

---

## 💡 记住这些原则

1. **先理解，再实现**: 不确定时先查看现有代码和文档
2. **小步快跑**: 每次只改一个问题，立即验证
3. **日志为王**: 详细的日志是最好的调试工具
4. **测试驱动**: 重要功能必须有测试覆盖
5. **文档同步**: 代码改动时同步更新文档
6. **代码备份**: 每次修改代码前都需要确认是否git备份版本

**这个文档会持续更新，每次遇到新的重复性错误都会添加到这里，形成我们的开发知识库。**