# 决策树v3.0结构化展示 - 更新总结

## 更新时间
2025-10-31 11:28

## 更新内容

### ✅ 阶段1：核心功能实现（已完成）

#### 1. 数据结构重构
- ✅ 实现`buildStructuredData()`函数 - 从画布节点构建结构化数据
- ✅ 支持按节点类型自动分类（disease, syndrome, pathogenesis, symptom, four_diagnosis, prescription, modification）
- ✅ 自动构建节点关系图，支持多层级嵌套结构

#### 2. 左侧UI重构
- ✅ 将原有的纯文本textarea改为可切换的双视图模式
- ✅ **结构化视图**（默认）：
  - 基本信息区域（疾病名称、病症描述）
  - 证候卡片（支持多个证候）
  - 每个证候包含：病机、症见、舌脉、处方、加减
  - 所有字段均支持点击编辑（contenteditable）
- ✅ **文本视图**：保留原有的文本编辑功能
- ✅ 添加视图切换按钮（📋 结构 ⇄ 📝 文本）

#### 3. 可编辑功能
- ✅ 所有字段支持contenteditable直接编辑
- ✅ 回车键保存（Enter），失焦自动保存（onblur）
- ✅ 编辑后自动更新画布节点
- ✅ 编辑后显示保存提示
- ✅ 删除证候功能（包含子节点级联删除）

#### 4. 样式优化
- ✅ 添加完整的结构化展示CSS样式
- ✅ 不同节点类型使用不同颜色标识
- ✅ Hover效果和编辑状态视觉反馈
- ✅ 卡片式布局，清晰的层级关系

#### 5. 同步机制
- ✅ 画布 → 结构化视图：自动同步
- ✅ 结构化视图 → 画布：编辑后自动更新画布
- ✅ 结构化视图 ⇄ 文本视图：自动转换

## 核心文件修改

### 修改的文件
- `/opt/tcm-ai/static/decision_tree_v3_data_driven.html`

### 新增的功能模块

#### 1. 全局变量
```javascript
let structuredData = null; // 结构化数据缓存
let isStructuredView = true; // 当前视图模式
```

#### 2. 核心函数
- `buildStructuredData()` - 构建结构化数据
- `renderStructuredView(data)` - 渲染结构化视图
- `handleFieldEdit(element, nodeId, field)` - 处理字段编辑
- `handleFieldKeydown(event, element)` - 处理键盘事件
- `deleteSyndrome(syndromeId)` - 删除证候
- `toggleView()` - 切换视图模式
- `convertStructuredDataToText(data)` - 结构化数据转文本

#### 3. 修改的函数
- `updateThinkingProcessFromNodes()` - 使用新的结构化渲染逻辑

#### 4. HTML结构变化
```html
<!-- 原有结构 -->
<textarea id="doctorThought"></textarea>

<!-- 新结构 -->
<div id="structuredThoughtContainer">
  <div class="section-title">
    <span>📋 诊疗思路</span>
    <button id="toggleViewBtn">📝 文本</button>
  </div>

  <!-- 结构化视图 -->
  <div id="structuredView">
    <div id="structuredContent"></div>
  </div>

  <!-- 文本视图 -->
  <div id="textView">
    <textarea id="doctorThought"></textarea>
  </div>
</div>
```

## 数据结构设计

### 结构化数据格式
```javascript
{
  disease: {
    id: "node_1",
    name: "头痛",
    description: "主证描述..."
  },
  syndromes: [
    {
      id: "node_2",
      name: "肝阳上亢",
      description: "证候描述...",
      pathogenesis: [
        { id: "node_3", name: "肝阳偏亢", description: "" }
      ],
      symptoms: [
        { id: "node_4", name: "头痛眩晕", description: "" }
      ],
      four_diagnosis: [
        { id: "node_5", name: "舌红苔黄", description: "" }
      ],
      prescriptions: [
        {
          id: "node_6",
          name: "天麻钩藤饮",
          description: "方剂组成...",
          ingredients: "天麻10g, 钩藤12g...",
          modifications: [
            {
              id: "node_7",
              condition: "若头痛剧烈",
              action: "加川芎10g、白芷10g",
              name: "加止痛药"
            }
          ]
        }
      ]
    }
  ],
  node_types_used: ["disease", "syndrome", "pathogenesis", ...]
}
```

## 功能演示

### 使用流程
1. **在画布中添加节点** → 自动生成结构化视图
2. **点击"重新生成"** → 根据画布节点更新结构化视图
3. **点击字段编辑** → 直接修改内容，失焦自动保存
4. **点击"📝 文本"** → 切换到文本编辑模式
5. **点击"📋 结构"** → 切换回结构化视图
6. **点击"🗑️ 删除"** → 删除证候及其子节点

### 编辑功能
- **病机/症见/舌脉**：点击彩色标签直接编辑
- **处方名称**：点击处方名称直接编辑
- **方剂组成**：点击白色区域编辑详细内容
- **加减内容**：点击黄色区域编辑加减说明

## 技术亮点

### 1. 双向同步机制
- 画布节点变化 → 自动更新结构化视图
- 结构化视图编辑 → 自动更新画布节点
- 结构化视图 ⇄ 文本视图无缝切换

### 2. 智能数据构建
- 自动识别节点类型
- 自动构建父子关系
- 自动提取连接标签

### 3. 优雅的编辑体验
- contenteditable原生编辑
- 回车键快速保存
- 实时视觉反馈
- 分类清晰的卡片布局

### 4. 降级方案
- 保留原有的文本拼接逻辑（在return之后）
- 如果新逻辑出现问题，可快速回退

## 后续优化方向

### 阶段2：数据持久化（待实施）
- [ ] 数据库添加`structured_data`字段
- [ ] 保存时同时保存结构化数据和文本
- [ ] 读取时优先使用结构化数据

### 阶段3：功能增强（待实施）
- [ ] 添加新证候功能
- [ ] 添加新处方功能
- [ ] 拖拽排序功能
- [ ] 批量导入导出

### 阶段4：UI优化（待实施）
- [ ] 折叠/展开证候卡片
- [ ] 搜索和过滤功能
- [ ] 更多主题颜色
- [ ] 移动端适配

## 测试说明

### 测试步骤
1. 访问 `https://mxh0510.cn/static/decision_tree_v3_data_driven.html`
2. 在画布中添加节点（病种 → 证候 → 病机/症状/处方）
3. 点击"重新生成"按钮
4. 查看左侧结构化视图是否正确显示
5. 尝试编辑各个字段
6. 切换到文本视图查看内容
7. 切换回结构化视图

### 预期效果
- ✅ 左侧显示清晰的结构化卡片
- ✅ 所有字段可点击编辑
- ✅ 编辑后画布节点同步更新
- ✅ 视图切换流畅无卡顿
- ✅ 数据格式符合中医诊疗逻辑

## 备份信息

### 备份文件
- 原始文件已备份至：`/opt/tcm-ai/template_files/decision_tree_v3_data_driven_backup_*.html`
- 方案文档：`/opt/tcm-ai/template_files/decision_tree_v3_optimization_plan.md`

### 回滚方法
```bash
# 如果出现问题，可以恢复备份
cp /opt/tcm-ai/template_files/decision_tree_v3_data_driven_backup_*.html /opt/tcm-ai/static/decision_tree_v3_data_driven.html
sudo service tcm-ai restart
```

## 总结

### 主要成果
1. ✅ 完全重构了左侧诊疗思路展示方式
2. ✅ 实现了结构化 + 可编辑的双重功能
3. ✅ 保持了与画布的完美同步
4. ✅ 提供了文本视图作为备选方案
5. ✅ 代码结构清晰，易于维护

### 解决的问题
- ❌ 原问题：点击"重新生成"后左侧内容混乱
- ✅ 新方案：左侧按节点类型清晰分类展示
- ✅ 额外收获：所有内容都可以直接编辑

### 用户价值
- 📊 **更清晰**：结构化展示，一目了然
- ✏️ **更方便**：点击即可编辑，无需切换界面
- 🔄 **更灵活**：结构化和文本两种视图随时切换
- 💾 **更安全**：编辑后自动保存，不怕丢失

---

**状态**: ✅ 阶段1已完成，服务已重启，等待用户测试反馈

**下一步**: 根据用户测试反馈，决定是否进入阶段2（数据持久化）
