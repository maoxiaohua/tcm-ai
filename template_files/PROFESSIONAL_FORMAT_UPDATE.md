# 诊疗思路专业格式生成优化

## 问题描述
用户反馈：自动生成的诊疗思路格式过于简单（箭头层级结构），不如手动编辑的专业中医临床格式。

## 期望格式（专业中医临床格式）
```
主病：头痛
主证：

【证候1】脑袋瓜前面疼
病机：
症见：脑袋瓜前面疼
舌脉：
处方：处方1
加减：
  若因为喝酒过多：加 去痛片

【证候2】后脑疼
病机：
症见：后脑疼
舌脉：
处方：处方2
```

## 解决方案

### 核心改进
完全重写 `updateThinkingProcessFromNodes()` 函数（第4606-4736行），改为以**证候节点为核心**的专业格式生成器。

### 新算法逻辑

#### 1. 数据准备阶段
```javascript
// 按节点类型分组
const nodesByType = {
    'disease': [...],      // 疾病节点
    'syndrome': [...],     // 证候节点
    'pathogenesis': [...], // 病机节点
    'symptom': [...],      // 症状节点
    'four_diagnosis': [...],// 舌脉节点
    'prescription': [...], // 方剂节点
    'modification': [...]  // 加减节点
};

// 构建关系图谱
const nodeMap = {
    'node_id': {
        node: {...},
        children: [{nodeId, node, label}, ...],
        parents: [...]
    }
};
```

#### 2. 生成主病和主证
```javascript
if (nodesByType['disease']?.length > 0) {
    thinkingText += `主病：${nodesByType['disease'][0].name}\n`;
    thinkingText += `主证：\n\n`;
}
```

#### 3. 遍历证候节点（核心结构）
对每个证候节点，按以下格式生成内容：

```javascript
syndromes.forEach((syndrome, index) => {
    // 标题
    thinkingText += `【证候${index + 1}】${syndrome.name}\n`;

    // 病机：找连接到该证候的所有病机节点
    const pathogenesisChildren = nodeMap[syndrome.id]?.children
        .filter(c => c.node?.type === 'pathogenesis');
    thinkingText += `病机：${pathogenesisChildren.map(c => c.node.name).join('、')}\n`;

    // 症见：找连接到该证候的所有症状节点
    const symptomChildren = nodeMap[syndrome.id]?.children
        .filter(c => c.node?.type === 'symptom');
    thinkingText += `症见：${symptomChildren.map(c => c.node.name).join('、')}\n`;

    // 舌脉：找连接到该证候的四诊节点
    const fourDiagnosisChildren = nodeMap[syndrome.id]?.children
        .filter(c => c.node?.type === 'four_diagnosis');
    thinkingText += `舌脉：${fourDiagnosisChildren.map(c => c.node.name).join('、')}\n`;

    // 处方：找连接到该证候的方剂节点
    const prescriptionChildren = nodeMap[syndrome.id]?.children
        .filter(c => c.node?.type === 'prescription');
    thinkingText += `处方：${prescriptionChildren[0]?.node.name || ''}\n`;

    // 加减：找连接到方剂的加减节点（带条件标签）
    thinkingText += `加减：\n`;
    if (prescriptionChildren.length > 0) {
        const prescription = prescriptionChildren[0];
        const modificationChildren = nodeMap[prescription.nodeId]?.children
            .filter(c => c.node?.type === 'modification');

        modificationChildren.forEach(modChild => {
            const conditionLabel = modChild.label || '';
            if (conditionLabel) {
                thinkingText += `  ${conditionLabel}：${modChild.node.name}\n`;
            } else {
                thinkingText += `  ${modChild.node.name}\n`;
            }
        });
    }
    thinkingText += '\n';
});
```

#### 4. 降级方案（无证候节点时）
```javascript
if (syndromes.length === 0) {
    thinkingText += '【诊疗方案】\n\n';
    ['symptom', 'pathogenesis', 'prescription', 'modification'].forEach(type => {
        const typeNodes = nodesByType[type] || [];
        if (typeNodes.length > 0) {
            const typeName = {
                'symptom': '症状',
                'pathogenesis': '病机',
                'prescription': '方剂',
                'modification': '加减'
            }[type];
            thinkingText += `${typeName}：${typeNodes.map(n => n.name).join('、')}\n`;
        }
    });
}
```

### 关键改进点

#### 1. 证候中心结构
**修改前**：简单的层级遍历，生成箭头式结构
```
【证候】头痛
  → 前额痛：脑袋瓜前面疼
    → 黄芩汤：处方1
      → 加减1：若因为喝酒过多：加 去痛片
```

**修改后**：专业中医格式，证候为核心结构
```
【证候1】脑袋瓜前面疼
病机：
症见：脑袋瓜前面疼
舌脉：
处方：处方1
加减：
  若因为喝酒过多：加 去痛片
```

#### 2. 节点类型智能匹配
通过连接关系，智能查找每个证候的相关内容：
- **病机**：查找type='pathogenesis'的子节点
- **症见**：查找type='symptom'的子节点
- **舌脉**：查找type='four_diagnosis'的子节点
- **处方**：查找type='prescription'的子节点
- **加减**：查找处方节点的type='modification'子节点

#### 3. 连接标签利用
- **加减条件**：使用连接线的label作为条件描述
- 例如："若因为喝酒过多" 这个label会显示在加减项前面

#### 4. 空值处理
- 每个部分如果没有连接的节点，会留空或使用默认值
- 病机、舌脉可以为空
- 症见如果为空，使用证候名称本身
- 加减如果没有条件标签，只显示药物名称

## 使用方式

### 手动触发更新
1. 在画布上编辑节点和连接关系
2. 点击右上角"🔄 更新思路"按钮
3. 确认覆盖提醒后，自动生成专业格式

### 自动保护机制
- **不再自动更新**：创建/删除连接时不会自动覆盖诊疗思路
- **确认对话框**：更新前会弹出提醒，需要用户确认
- **保留手动编辑**：用户手动编辑的详细内容不会被意外覆盖

## 技术细节

### 文件位置
`/opt/tcm-ai/static/decision_tree_visual_builder.html`

### 关键代码位置
- **第4606-4736行**：`updateThinkingProcessFromNodes()` 函数
- **第2171-2186行**：`manualUpdateThinking()` 手动更新触发函数
- **第836-852行**：HTML中的"更新思路"按钮

### 节点类型定义
```javascript
const nodeTypes = {
    'disease': '疾病',
    'syndrome': '证候',
    'pathogenesis': '病机',
    'symptom': '症状',
    'four_diagnosis': '四诊',
    'prescription': '方剂',
    'modification': '加减'
};
```

### 连接关系遍历
```javascript
// 查找某节点的所有子节点
nodeMap[nodeId].children.forEach(child => {
    // child.nodeId: 子节点ID
    // child.node: 子节点对象
    // child.label: 连接线标签（用于加减条件）
});
```

## 测试建议

### 测试用例1：完整证候结构
```
疾病：头痛
└─ 证候1：前额疼
   ├─ 病机：风热上扰
   ├─ 症状：前额疼痛
   ├─ 舌脉：舌红苔黄
   └─ 方剂：黄芩汤
      ├─ 加减1（若喝酒过多）：加葛根
      └─ 加减2（若头痛剧烈）：加川芎
```

**期望输出**：
```
主病：头痛
主证：

【证候1】前额疼
病机：风热上扰
症见：前额疼痛
舌脉：舌红苔黄
处方：黄芩汤
加减：
  若喝酒过多：加葛根
  若头痛剧烈：加川芎
```

### 测试用例2：多证候
```
疾病：头痛
├─ 证候1：前额疼
│  └─ 处方：黄芩汤
└─ 证候2：后脑疼
   └─ 处方：川芎茶调散
```

**期望输出**：
```
主病：头痛
主证：

【证候1】前额疼
病机：
症见：前额疼
舌脉：
处方：黄芩汤
加减：

【证候2】后脑疼
病机：
症见：后脑疼
舌脉：
处方：川芎茶调散
加减：
```

### 测试用例3：无证候节点（降级模式）
```
症状1：头痛
症状2：发热
方剂：小柴胡汤
```

**期望输出**：
```
【诊疗方案】

症状：头痛、发热
方剂：小柴胡汤
```

## 相关文档
- `MANUAL_UPDATE_THINKING.md` - 手动更新策略说明
- `CONNECTION_FEATURE.md` - 连接功能完整文档
- `TOOLBAR_FIX.md` - 工具栏显示修复

## 更新时间
2025-10-28 13:53

## 状态
✅ 已部署
✅ 服务已重启
⏳ 等待用户测试反馈
