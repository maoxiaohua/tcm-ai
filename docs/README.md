# 🏥 TCM AI 中医智能诊断系统

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📖 项目简介

TCM AI是一款基于人工智能的中医智能诊断系统，集成了传统中医理论与现代AI技术，为用户提供专业的中医问诊、证候分析、方剂推荐等服务。

### 🌟 核心特色

- **五大中医流派**: 集成张仲景、叶天士、李东垣、刘渡舟、郑钦安五位名医的诊疗思维
- **智能问诊**: AI驱动的症状分析和辨证论治
- **处方检测**: 支持文字和图片处方的智能识别与分析
- **个性化治疗**: 基于用户历史和体质的个性化治疗建议
- **多端适配**: 支持PC、移动端、微信等多平台访问

## 🚀 快速开始

### 环境要求

- Python 3.11+
- PostgreSQL 12+
- 阿里云DashScope API密钥

### 安装部署

1. **克隆项目**
```bash
git clone https://github.com/maoxiaohua/tcm.git
cd tcm
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑.env文件，填入您的API密钥和数据库配置
```

5. **启动服务**
```bash
python main.py
```

访问 `http://localhost:8000` 开始使用

## 🏗️ 系统架构

### 核心模块

- **主服务**: `main.py` - FastAPI应用服务器
- **医生系统**: `tcm_doctor_personas.py` - 五大流派医生角色
- **诊断控制**: `medical_diagnosis_controller.py` - 诊断流程控制
- **处方系统**: `prescription_checker.py` - 处方检测和分析
- **用户系统**: `user_history_system.py` - 用户历史和数据管理
- **缓存系统**: `intelligent_cache_system.py` - 智能响应缓存

### 技术栈

- **后端框架**: FastAPI + Uvicorn
- **数据库**: PostgreSQL + SQLite
- **AI模型**: 阿里云DashScope (通义千问)
- **向量数据库**: FAISS
- **OCR识别**: 多模态LLM + 传统OCR
- **前端**: 原生HTML5 + JavaScript (响应式设计)

## 💡 主要功能

### 1. 智能问诊系统
- **多轮对话**: 智能引导用户描述症状
- **辨证分析**: 基于中医理论的证候分析
- **流派特色**: 不同医生展现独特的诊疗风格
- **历史记录**: 完整的问诊历史追踪

### 2. 处方检测系统
- **文字处方**: 智能解析文字描述的处方
- **图片识别**: OCR + AI双重识别处方图片
- **药物分析**: 君臣佐使分析、剂量评估
- **安全检查**: 智能检测和清理不当医疗信息

### 3. 用户管理系统
- **用户注册**: 支持手机验证码注册
- **历史记录**: 完整的诊疗历史管理
- **数据导出**: 支持病历导出功能
- **隐私保护**: 严格的医疗数据保护

### 4. 医生端功能
- **思维录入**: 医生可录入自己的诊疗经验
- **模式学习**: 系统学习名医诊疗模式
- **知识管理**: 中医知识库管理和更新

## 📱 使用指南

### 用户端使用

1. **访问系统**: 打开 `http://你的域名` 
2. **选择医生**: 选择适合的中医流派医生
3. **描述症状**: 详细描述您的症状和不适
4. **获得建议**: 获取专业的中医诊断建议
5. **查看历史**: 在历史记录中查看往期咨询

### 医生端使用

1. **访问医生端**: `http://你的域名/doctor`
2. **录入经验**: 在思维录入页面分享诊疗经验
3. **管理知识**: 通过医生管理页面维护知识库
4. **查看统计**: 了解系统使用情况和效果

### 管理员功能

1. **系统监控**: `http://你的域名/monitor` 
2. **状态检查**: `http://你的域名/debug_status`
3. **处方检测**: `http://你的域名/prescription/checker`

## ⚙️ 配置说明

### 环境变量 (.env)

```bash
# 阿里云DashScope配置
DASHSCOPE_API_KEY=your_api_key_here

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost/tcm_db

# 服务配置
HOST=0.0.0.0
PORT=8000
WORKERS=1

# 安全配置
SECRET_KEY=your_secret_key
```

### 数据库配置

系统支持PostgreSQL作为主数据库，SQLite作为缓存数据库：

- 知识库: PostgreSQL
- 用户数据: SQLite
- 缓存数据: SQLite

## 🔧 开发指南

### 目录结构

```
tcm/
├── main.py                     # 主服务入口
├── tcm_doctor_personas.py      # 医生角色系统
├── prescription_checker.py     # 处方检测
├── user_history_system.py      # 用户系统
├── static/                     # 前端静态文件
│   ├── index_v2.html          # 主界面
│   ├── register.html          # 注册页面
│   └── ...
├── data/                       # 数据目录
├── conversation_logs/          # 对话日志
└── knowledge_db/              # 知识库
```

### API接口

主要API端点：

- `POST /chat_with_ai` - AI对话接口
- `POST /api/prescription/check` - 处方检测
- `GET /history` - 用户历史
- `GET /debug_status` - 系统状态

详细API文档访问: `http://localhost:8000/docs`

## 🛡️ 医疗安全

系统内置多重医疗安全保障：

- **信息验证**: 严格检测AI编造的医疗信息
- **安全清理**: 自动清理不当的诊断描述
- **医师提醒**: 所有建议都附带"请咨询专业医师"提醒
- **隐私保护**: 用户医疗数据加密存储

## 📈 性能特性

- **智能缓存**: 常见症状秒级响应
- **负载均衡**: 支持多worker并发
- **故障降级**: AI服务异常时自动降级
- **实时监控**: 完整的系统健康监控

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系方式

- 项目维护者: [@maoxiaohua](https://github.com/maoxiaohua)
- 问题反馈: [GitHub Issues](https://github.com/maoxiaohua/tcm/issues)

## 🙏 致谢

感谢以下开源项目的支持：

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Python Web框架
- [FAISS](https://github.com/facebookresearch/faiss) - 高效的向量相似度搜索
- [阿里云DashScope](https://dashscope.aliyun.com/) - 提供强大的AI模型支持

---

**⚠️ 医疗免责声明**: 本系统仅供学习和参考使用，不能替代专业医疗诊断。任何医疗决策都应咨询执业医师。