# AI智能思维导图系统 - 完整文档

## 📋 系统概述

这是一个基于Vue 3 + FastAPI + qwen-max的通用智能思维导图生成系统，支持多行业应用场景。

### 核心特点

✅ **AI驱动生成**: 使用阿里云qwen-max模型智能分析，自动构建思维导图结构
✅ **多领域支持**: 医疗诊断、技术方案、商业决策等多个行业场景
✅ **层级结构清晰**: 支持2-6层的可配置层级深度
✅ **可视化交互**: 基于ECharts的树状图展示，支持节点展开/收起
✅ **完整CRUD**: 生成、保存、加载、删除、导出功能完备
✅ **现代化UI**: Vue 3 + Element Plus打造的美观界面

## 🚀 访问地址

```
主页面: http://your-domain:8000/mindmap
API文档: http://your-domain:8000/docs (查看 /api/mindmap 相关接口)
```

## 📂 文件结构

```
/opt/tcm-ai/
├── core/mindmap/                          # 核心业务逻辑
│   ├── __init__.py                       # 模块初始化
│   └── ai_mindmap_generator.py           # AI思维导图生成器
│
├── api/routes/
│   └── mindmap_routes.py                 # API路由定义
│
├── static/mindmap/
│   └── index.html                        # Vue前端页面
│
└── data/
    └── user_history.sqlite               # 数据库（mindmaps表）
```

## 🔧 技术架构

### 后端技术栈

- **Web框架**: FastAPI (异步高性能)
- **AI模型**: 阿里云Dashscope - qwen-max
- **数据存储**: SQLite (mindmaps表)
- **数据结构**: 标准化树形结构

### 前端技术栈

- **框架**: Vue 3 (Composition API)
- **UI组件**: Element Plus 2.4.2
- **可视化**: ECharts 5.4.3
- **图标**: Element Plus Icons

### 数据库表结构

```sql
CREATE TABLE mindmaps (
    id TEXT PRIMARY KEY,              -- 思维导图ID
    title TEXT NOT NULL,              -- 标题
    description TEXT,                 -- 描述
    domain TEXT DEFAULT 'general',    -- 领域 (medical/technical/business/general)
    data TEXT NOT NULL,               -- JSON数据
    user_id TEXT,                     -- 用户ID (可选)
    created_at TEXT NOT NULL,         -- 创建时间
    updated_at TEXT NOT NULL          -- 更新时间
);
```

## 📡 API接口说明

### 1. 生成思维导图

**接口**: `POST /api/mindmap/generate`

**请求示例**:
```json
{
  "topic": "感冒的中医诊断",
  "description": "基于中医理论，分析感冒的病因、症状、证型和治疗方案",
  "domain": "medical",
  "max_levels": 4,
  "max_children": 5
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "思维导图生成成功",
  "data": {
    "mindmap": {
      "id": "mindmap_20251105_172248",
      "title": "感冒的中医诊断",
      "nodes": { ... }
    },
    "echarts": {
      "title": "感冒的中医诊断",
      "data": { ... }
    }
  }
}
```

### 2. 保存思维导图

**接口**: `POST /api/mindmap/save`

**请求示例**:
```json
{
  "mindmap_id": "mindmap_20251105_172248",
  "title": "感冒的中医诊断",
  "description": "完整的感冒诊断思维导图",
  "domain": "medical",
  "data": { ... },
  "user_id": "user123"
}
```

### 3. 加载思维导图

**接口**: `GET /api/mindmap/load/{mindmap_id}`

**示例**: `GET /api/mindmap/load/mindmap_20251105_172248`

### 4. 获取列表

**接口**: `GET /api/mindmap/list?user_id=xxx&limit=20`

### 5. 删除思维导图

**接口**: `DELETE /api/mindmap/delete/{mindmap_id}`

## 💡 使用场景示例

### 场景1: 医疗诊断思路

```
主题: 高血压中医诊疗方案
描述: 从中医角度分析高血压的病因病机、辨证分型和治疗原则
领域: medical
```

**生成结果**:
```
高血压中医诊疗
├── 病因病机
│   ├── 肝阳上亢
│   ├── 痰湿中阻
│   └── 阴虚阳亢
├── 辨证分型
│   ├── 肝火亢盛证
│   ├── 痰湿壅盛证
│   └── 肝肾阴虚证
└── 治疗原则
    ├── 平肝潜阳
    ├── 化痰祛湿
    └── 滋阴降火
```

### 场景2: 技术故障排查

```
主题: 网络连接故障诊断
描述: 当服务器无法访问时，系统性排查网络问题的步骤
领域: technical
```

**生成结果**:
```
网络连接故障诊断
├── 物理层检查
│   ├── 检查网线连接
│   ├── 检查交换机指示灯
│   └── 测试端口状态
├── 网络层检查
│   ├── ping测试连通性
│   ├── 检查IP配置
│   └── 查看路由表
├── 传输层检查
│   ├── 检查端口开放状态
│   ├── 查看防火墙规则
│   └── 测试TCP连接
└── 应用层检查
    ├── 检查服务运行状态
    ├── 查看应用日志
    └── 验证应用配置
```

### 场景3: 商业决策分析

```
主题: 新产品上市策略
描述: 分析新产品从市场调研到上市推广的完整决策流程
领域: business
```

**生成结果**:
```
新产品上市策略
├── 市场调研
│   ├── 竞品分析
│   ├── 用户需求调研
│   └── 市场容量评估
├── 产品定位
│   ├── 目标客户群
│   ├── 差异化优势
│   └── 价格策略
├── 营销推广
│   ├── 渠道选择
│   ├── 广告投放
│   └── 促销活动
└── 风险管理
    ├── 市场风险
    ├── 运营风险
    └── 财务风险
```

## 🎨 界面功能说明

### 左侧配置面板

1. **主题标题**: 2-100字，简明扼要
2. **详细描述**: 5-1000字，详细说明思维导图的核心内容
3. **应用领域**: 4个选项
   - 🏥 医疗诊断
   - 💻 技术方案
   - 💼 商业决策
   - 📊 通用主题
4. **层级设置**: 2-6层可选
5. **分支数量**: 每个节点2-10个子节点

### 右侧画布区域

- **空状态提示**: 引导用户创建第一个思维导图
- **加载动画**: AI生成过程的视觉反馈
- **交互式树图**:
  - 鼠标悬停显示详细内容
  - 点击节点展开/收起
  - 支持缩放和拖拽

### 功能按钮

- **🚀 生成思维导图**: 调用AI生成新的思维导图
- **💾 保存**: 将当前思维导图保存到数据库
- **📥 导出图片**: 导出为PNG格式的高清图片
- **🔄 重置视图**: 恢复画布到初始状态

### 历史记录

- 显示最近10个思维导图
- 点击快速加载历史记录
- 显示标题、领域和更新时间

## 🔄 数据流程

```
用户输入主题和描述
    ↓
前端表单验证
    ↓
POST /api/mindmap/generate
    ↓
后端调用 AIMindMapGenerator
    ↓
构建AI提示词
    ↓
调用 qwen-max API
    ↓
解析AI响应JSON
    ↓
构建思维导图结构
    ↓
转换为ECharts格式
    ↓
返回前端渲染
    ↓
用户可保存到数据库
```

## 🛠️ 核心类说明

### 1. AIMindMapGenerator

**位置**: `/opt/tcm-ai/core/mindmap/ai_mindmap_generator.py`

**核心方法**:
- `generate_mindmap()`: 生成思维导图主方法
- `_build_generation_prompt()`: 构建AI提示词
- `_call_qwen_api()`: 调用千问API
- `_parse_ai_response()`: 解析AI返回的JSON
- `export_to_dict()`: 导出为字典格式
- `export_to_echarts_format()`: 转换为ECharts树图格式

**数据结构**:
```python
@dataclass
class MindMapNode:
    id: str                    # 节点ID
    title: str                 # 节点标题
    content: str               # 详细内容
    level: int                 # 层级 (0=根节点)
    parent_id: Optional[str]   # 父节点ID
    children: List[str]        # 子节点ID列表
    category: str              # 分类标签
    color: str                 # 节点颜色
    metadata: Dict[str, Any]   # 扩展元数据
```

### 2. API路由

**位置**: `/opt/tcm-ai/api/routes/mindmap_routes.py`

**路由列表**:
- `POST /api/mindmap/generate` - 生成思维导图
- `POST /api/mindmap/save` - 保存思维导图
- `GET /api/mindmap/load/{id}` - 加载思维导图
- `GET /api/mindmap/list` - 获取列表
- `DELETE /api/mindmap/delete/{id}` - 删除思维导图

## 🎯 AI提示词设计

系统使用精心设计的提示词来确保AI生成高质量的思维导图：

```
请帮我生成一个思维导图结构，要求如下：

**主题**: {topic}
**描述**: {description}
**领域**: {domain_desc}
**层级要求**: 最多{max_levels}层
**分支要求**: 每个节点最多{max_children}个子节点

请按照JSON格式输出，包含：
1. 节点ID、标题、内容、层级
2. 父子关系
3. 分类标签
4. 结构清晰、层次分明
5. 内容专业、有深度
```

## 🔐 安全考虑

1. **输入验证**:
   - 主题长度限制: 2-100字
   - 描述长度限制: 5-1000字
   - 层级范围: 2-6层
   - 分支数量: 2-10个

2. **API安全**:
   - 请求参数验证 (Pydantic模型)
   - SQL注入防护 (参数化查询)
   - 错误处理和日志记录

3. **数据隔离**:
   - 支持user_id字段实现多用户数据隔离
   - 可扩展权限控制

## 📊 性能优化

1. **AI调用优化**:
   - 使用qwen-max模型平衡速度和质量
   - 温度设置0.7保证创造性和稳定性
   - 超时控制避免长时间等待

2. **前端优化**:
   - CDN加速加载Vue、ECharts等库
   - 响应式设计适配多端
   - 懒加载历史记录

3. **数据库优化**:
   - 使用索引加速查询
   - JSON字段存储灵活数据
   - 分页加载历史记录

## 🐛 故障排查

### 问题1: 生成失败

**症状**: 点击生成按钮后报错

**排查步骤**:
```bash
# 1. 检查服务状态
sudo service tcm-ai status

# 2. 检查API密钥
env | grep DASHSCOPE_API_KEY

# 3. 查看日志
tail -f /opt/tcm-ai/logs/api.log

# 4. 测试API
curl -X POST "http://localhost:8000/api/mindmap/generate" \
  -H "Content-Type: application/json" \
  -d '{"topic":"测试","description":"测试描述","domain":"general"}'
```

### 问题2: 页面无法访问

**症状**: 访问 /mindmap 返回404

**排查步骤**:
```bash
# 1. 检查文件是否存在
ls -la /opt/tcm-ai/static/mindmap/index.html

# 2. 检查路由是否注册
grep "mindmap_main" /opt/tcm-ai/api/main.py

# 3. 重启服务
sudo service tcm-ai restart
```

### 问题3: 保存失败

**症状**: 点击保存按钮报错

**排查步骤**:
```bash
# 1. 检查数据库
sqlite3 /opt/tcm-ai/data/user_history.sqlite ".tables" | grep mindmap

# 2. 检查表结构
sqlite3 /opt/tcm-ai/data/user_history.sqlite ".schema mindmaps"

# 3. 测试保存API
curl -X POST "http://localhost:8000/api/mindmap/save" \
  -H "Content-Type: application/json" \
  -d '{"mindmap_id":"test_001","title":"测试","data":{}}'
```

## 🚀 扩展开发

### 添加新领域

编辑 `/opt/tcm-ai/core/mindmap/ai_mindmap_generator.py`:

```python
domain_examples = {
    "medical": "医疗诊断思路、疾病分析、治疗方案",
    "technical": "技术问题排查、系统架构、故障诊断",
    "business": "商业决策、项目规划、战略分析",
    "education": "教学设计、课程规划、知识体系",  # 新增
    "general": "通用主题分析"
}
```

同步修改前端 `/opt/tcm-ai/static/mindmap/index.html`:

```javascript
const domains = ref([
    { label: '医疗诊断', value: 'medical', icon: '🏥' },
    { label: '技术方案', value: 'technical', icon: '💻' },
    { label: '商业决策', value: 'business', icon: '💼' },
    { label: '教育培训', value: 'education', icon: '📚' },  // 新增
    { label: '通用主题', value: 'general', icon: '📊' }
]);
```

### 自定义颜色方案

编辑颜色配置:

```python
color_scheme = {
    0: "#5470c6",  # 蓝色 - 根节点
    1: "#91cc75",  # 绿色 - 一级节点
    2: "#fac858",  # 黄色 - 二级节点
    3: "#ee6666",  # 红色 - 三级节点
    4: "#73c0de",  # 青色 - 四级节点
    5: "#9a60b4",  # 紫色 - 五级节点
}
```

### 添加导出格式

扩展导出功能，支持JSON、Markdown等格式：

```python
def export_to_markdown(self, mindmap: MindMapStructure) -> str:
    """导出为Markdown格式"""
    # 实现Markdown格式导出
    pass

def export_to_json(self, mindmap: MindMapStructure) -> str:
    """导出为JSON格式"""
    # 实现JSON格式导出
    pass
```

## 📝 更新日志

### v1.0.0 (2025-11-05)

**首次发布**:
- ✅ 完整的AI思维导图生成系统
- ✅ 支持医疗、技术、商业、通用4个领域
- ✅ Vue 3 + ECharts的现代化界面
- ✅ 完整的CRUD操作
- ✅ 图片导出功能
- ✅ 历史记录管理

## 📞 技术支持

- **项目文档**: `/opt/tcm-ai/CLAUDE.md`
- **API文档**: `http://your-domain:8000/docs`
- **日志位置**: `/opt/tcm-ai/logs/api.log`

## 🎉 总结

这个AI智能思维导图系统具有以下优势：

1. **通用性强**: 支持多行业应用，不局限于单一领域
2. **智能化高**: AI自动分析生成，无需手动构建
3. **界面友好**: 现代化UI设计，操作简单直观
4. **功能完整**: 生成、保存、加载、导出一应俱全
5. **可扩展性**: 架构清晰，易于扩展新功能
6. **性能优秀**: 异步架构，响应快速

适用于需要快速构建思维导图的各类场景，是知识管理、决策分析、问题诊断的得力工具。

---

**开发团队**: TCM-AI Development Team
**创建时间**: 2025-11-05
**文档版本**: v1.0.0
