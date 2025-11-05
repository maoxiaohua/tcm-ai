# 决策树v3.0数据驱动版本 - 优化方案

## 问题分析

### 当前问题
1. **左侧诊疗思路内容混乱**：点击"重新生成"后，左侧诊疗思路的内容变得乱七八糟
2. **数据结构不统一**：左侧和右侧使用不同的数据组织方式
3. **节点类型未充分利用**：虽然有多种节点类型，但数据存储时没有按类型分类

### 根本原因
- 当前的`updateThinkingProcessFromNodes()`函数采用"遍历节点拼接文本"的方式生成诊疗思路
- 这种方式依赖节点的连接关系和层级结构，容易产生混乱的文本输出
- 数据库保存的是原始文本（不包含结构信息），导致读取后无法正确重建结构

## 核心需求
1. **内容一致性**：左侧诊疗思路和右侧画布应该展示相同的内容
2. **按类型分组**：数据应该按照节点类型进行分类组织
3. **动态展示**：如果某个分类没有内容，则不显示；一旦新增，自动显示

## 优化方案

### 方案一：节点类型驱动的结构化数据（推荐）⭐

#### 数据结构设计
```javascript
{
  "disease": {
    "name": "头痛",
    "description": "主证描述..."
  },
  "syndromes": [
    {
      "id": "syndrome_1",
      "name": "肝阳上亢",
      "pathogenesis": ["肝阳偏亢", "气血上逆"],
      "symptoms": ["头痛眩晕", "面红目赤", "口苦咽干"],
      "four_diagnosis": ["舌红苔黄", "脉弦有力"],
      "prescriptions": [
        {
          "name": "天麻钩藤饮",
          "ingredients": "天麻10g, 钩藤12g...",
          "modifications": [
            {
              "condition": "若头痛剧烈",
              "action": "加川芎10g、白芷10g"
            }
          ]
        }
      ]
    }
  ],
  "node_types_used": ["disease", "syndrome", "pathogenesis", "symptom", "four_diagnosis", "prescription", "modification"]
}
```

#### 优势
1. ✅ **结构清晰**：数据按医疗逻辑分层组织
2. ✅ **易于维护**：增删改查都基于清晰的数据结构
3. ✅ **完美同步**：左右两侧渲染同一数据源
4. ✅ **支持动态分类**：根据`node_types_used`动态显示分类

#### 实现步骤
1. **定义节点类型映射**
   ```javascript
   const NODE_TYPE_CONFIG = {
     'disease': { label: '病种', icon: '🏥', order: 1 },
     'four_diagnosis': { label: '四诊信息', icon: '👁️', order: 2 },
     'syndrome': { label: '证候', icon: '📋', order: 3 },
     'pathogenesis': { label: '病机', icon: '⚙️', order: 4 },
     'symptom': { label: '症状', icon: '🤒', order: 5 },
     'prescription': { label: '处方', icon: '💊', order: 6 },
     'modification': { label: '加减', icon: '➕', order: 7 }
   };
   ```

2. **从画布节点构建结构化数据**
   ```javascript
   function buildStructuredData() {
     const data = {
       disease: null,
       syndromes: [],
       node_types_used: new Set()
     };

     // 按类型分组节点
     const nodesByType = groupNodesByType(nodes);

     // 构建disease信息
     if (nodesByType['disease']?.length > 0) {
       data.disease = {
         name: nodesByType['disease'][0].name,
         description: nodesByType['disease'][0].description
       };
       data.node_types_used.add('disease');
     }

     // 构建syndrome结构（包含子节点）
     const syndromes = [
       ...(nodesByType['syndrome'] || []),
       ...(nodesByType['syndrome_branch'] || [])
     ];

     syndromes.forEach(syndrome => {
       const syndromeData = {
         id: syndrome.id,
         name: syndrome.name,
         description: syndrome.description,
         pathogenesis: [],
         symptoms: [],
         four_diagnosis: [],
         prescriptions: []
       };

       // 查找子节点
       const children = getChildrenByNodeId(syndrome.id);

       // 按类型分组子节点
       children.forEach(child => {
         if (child.type === 'pathogenesis') {
           syndromeData.pathogenesis.push(child.name);
           data.node_types_used.add('pathogenesis');
         } else if (child.type === 'symptom') {
           syndromeData.symptoms.push(child.name);
           data.node_types_used.add('symptom');
         } else if (child.type === 'four_diagnosis') {
           syndromeData.four_diagnosis.push(child.name);
           data.node_types_used.add('four_diagnosis');
         } else if (child.type === 'prescription') {
           const prescData = {
             name: child.name,
             ingredients: child.description,
             modifications: []
           };

           // 查找处方的加减子节点
           const modChildren = getChildrenByNodeId(child.id);
           modChildren.forEach(mod => {
             if (mod.type === 'modification') {
               prescData.modifications.push({
                 condition: mod.label || '',
                 action: mod.description || mod.name
               });
               data.node_types_used.add('modification');
             }
           });

           syndromeData.prescriptions.push(prescData);
           data.node_types_used.add('prescription');
         }
       });

       data.syndromes.push(syndromeData);
       data.node_types_used.add('syndrome');
     });

     data.node_types_used = Array.from(data.node_types_used);
     return data;
   }
   ```

3. **渲染左侧诊疗思路（结构化显示）**
   ```javascript
   function renderThoughtProcess(structuredData) {
     const container = document.getElementById('thoughtContainer');
     let html = '';

     // 1. 基本信息
     if (structuredData.disease) {
       html += `
         <div class="thought-section">
           <h3 class="section-title">🏥 基本信息</h3>
           <div class="section-content">
             <div class="info-row">
               <span class="label">疾病名称:</span>
               <span class="value">${structuredData.disease.name}</span>
             </div>
           </div>
         </div>
       `;
     }

     // 2. 证候分类显示
     if (structuredData.syndromes.length > 0) {
       structuredData.syndromes.forEach((syndrome, index) => {
         html += `
           <div class="thought-section syndrome-section">
             <h3 class="section-title">📋 证候${index + 1}: ${syndrome.name}</h3>
             <div class="section-content">
         `;

         // 病机
         if (syndrome.pathogenesis.length > 0) {
           html += `
             <div class="subsection">
               <span class="subsection-label">⚙️ 病机:</span>
               <span>${syndrome.pathogenesis.join('、')}</span>
             </div>
           `;
         }

         // 症状
         if (syndrome.symptoms.length > 0) {
           html += `
             <div class="subsection">
               <span class="subsection-label">🤒 症见:</span>
               <span>${syndrome.symptoms.join('、')}</span>
             </div>
           `;
         }

         // 四诊
         if (syndrome.four_diagnosis.length > 0) {
           html += `
             <div class="subsection">
               <span class="subsection-label">👁️ 舌脉:</span>
               <span>${syndrome.four_diagnosis.join('、')}</span>
             </div>
           `;
         }

         // 处方
         if (syndrome.prescriptions.length > 0) {
           syndrome.prescriptions.forEach(presc => {
             html += `
               <div class="subsection">
                 <span class="subsection-label">💊 处方:</span>
                 <span>${presc.name}</span>
               </div>
             `;

             if (presc.ingredients) {
               html += `
                 <div class="ingredients">${presc.ingredients}</div>
               `;
             }

             // 加减
             if (presc.modifications.length > 0) {
               html += `<div class="modifications-label">➕ 加减:</div>`;
               presc.modifications.forEach(mod => {
                 html += `
                   <div class="modification-item">
                     ${mod.condition ? `<span class="condition">${mod.condition}:</span>` : ''}
                     <span class="action">${mod.action}</span>
                   </div>
                 `;
               });
             }
           });
         }

         html += `
             </div>
           </div>
         `;
       });
     }

     container.innerHTML = html;
   }
   ```

4. **渲染右侧画布（可视化）**
   ```javascript
   function renderCanvas(structuredData) {
     clearCanvas();

     // 根节点：病种
     if (structuredData.disease) {
       const diseaseNode = createNode({
         type: 'disease',
         name: structuredData.disease.name,
         description: structuredData.disease.description,
         x: 400,
         y: 50
       });
       addNode(diseaseNode);

       let yOffset = 200;

       // 为每个证候创建节点树
       structuredData.syndromes.forEach((syndrome, index) => {
         const syndromeNode = createNode({
           type: 'syndrome',
           name: syndrome.name,
           description: syndrome.description,
           x: 400,
           y: yOffset
         });
         addNode(syndromeNode);
         addConnection(diseaseNode.id, syndromeNode.id);

         // 布局子节点
         layoutChildNodes(syndromeNode, syndrome, yOffset);

         yOffset += 300;
       });
     }

     redrawCanvas();
   }
   ```

5. **数据库保存和读取**
   ```javascript
   function saveToDatabase() {
     const structuredData = buildStructuredData();
     const thinking_process = convertStructuredDataToText(structuredData);

     // 保存时同时保存结构化数据和文本格式
     const payload = {
       disease_name: structuredData.disease?.name || '',
       thinking_process: thinking_process,
       tree_data: JSON.stringify({
         nodes: nodes,
         connections: connections
       }),
       structured_data: JSON.stringify(structuredData) // 新增字段
     };

     // 调用API保存
     fetch('/api/save_decision_tree', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify(payload)
     });
   }

   function loadFromDatabase() {
     fetch('/api/load_decision_tree')
       .then(res => res.json())
       .then(data => {
         // 优先使用结构化数据
         if (data.structured_data) {
           const structuredData = JSON.parse(data.structured_data);
           renderThoughtProcess(structuredData);
           renderCanvas(structuredData);
         } else if (data.tree_data) {
           // 降级方案：从tree_data重建
           const treeData = JSON.parse(data.tree_data);
           nodes = treeData.nodes;
           connections = treeData.connections;
           redrawCanvas();
           updateThinkingProcessFromNodes();
         }
       });
   }
   ```

### 方案二：保持文本格式但增强解析（备选）

保持当前的文本格式，但增强解析逻辑：

```javascript
function parseThinkingText(text) {
  const data = {
    disease: null,
    syndromes: []
  };

  // 正则匹配不同部分
  const diseaseMatch = text.match(/主病[：:](.*?)(?:\n|$)/);
  if (diseaseMatch) {
    data.disease = { name: diseaseMatch[1].trim() };
  }

  // 匹配证候块
  const syndromeRegex = /【证候(\d+)】(.*?)\n病机[：:](.*?)\n症见[：:](.*?)\n舌脉[：:](.*?)\n处方[：:](.*?)(?:\n加减[：:]|$)/gs;
  let match;
  while ((match = syndromeRegex.exec(text)) !== null) {
    data.syndromes.push({
      name: match[2].trim(),
      pathogenesis: match[3].trim().split('、'),
      symptoms: match[4].trim().split('、'),
      four_diagnosis: match[5].trim().split('、'),
      prescription: match[6].trim()
    });
  }

  return data;
}
```

**问题**：正则解析容易出错，维护困难

## 推荐实施方案

### 阶段1：数据结构重构 ✅ **优先**
1. 实现`buildStructuredData()`函数
2. 修改数据库schema，添加`structured_data`字段
3. 实现新的保存和读取逻辑

### 阶段2：UI重构
1. 重构左侧诊疗思路区域（改为结构化显示）
2. 保持右侧画布的可视化逻辑
3. 添加CSS样式美化

### 阶段3：功能增强
1. 实现双向同步（编辑左侧自动更新右侧，反之亦然）
2. 添加节点类型过滤功能
3. 添加数据导出功能（JSON/Markdown）

## 技术细节

### 节点类型定义
```javascript
const SUPPORTED_NODE_TYPES = [
  'disease',          // 病种
  'four_diagnosis',   // 四诊
  'syndrome',         // 证候
  'syndrome_branch',  // 证候分支
  'pathogenesis',     // 病机
  'symptom',          // 症状
  'prescription',     // 处方
  'modification',     // 加减
  'principle',        // 治则
  'formula'           // 方剂
];
```

### 数据库Schema更新
```sql
ALTER TABLE doctor_clinical_patterns
ADD COLUMN structured_data TEXT;  -- JSON格式的结构化数据

-- 示例数据
UPDATE doctor_clinical_patterns
SET structured_data = '{"disease": {...}, "syndromes": [...]}'
WHERE id = 1;
```

## 预期效果

### 重新生成前
- 左侧：混乱的文本，难以阅读
- 右侧：正常的可视化节点树

### 重新生成后
- 左侧：结构清晰的分类展示（病种 → 证候 → 病机/症见/舌脉/处方/加减）
- 右侧：相同内容的可视化节点树
- 数据：完全一致，来自同一数据源

## 开发建议

1. **先小范围测试**：在测试环境实现基础功能
2. **渐进式迁移**：保留原有逻辑作为降级方案
3. **充分测试**：测试各种节点组合情况
4. **用户反馈**：根据实际使用反馈调整UI设计

## 总结

**核心思想**：从"文本拼接"转变为"结构化数据驱动"

- ✅ 左右两侧使用相同数据源
- ✅ 按节点类型组织数据
- ✅ 动态显示已使用的节点类型
- ✅ 易于维护和扩展
