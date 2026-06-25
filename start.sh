#!/bin/bash
# TCM-AI 中医智能诊断系统 - 启动脚本
# 项目路径: /home/ute/tcm-ai

PROJECT_DIR="/home/ute/tcm-ai"
VENV_DIR="$PROJECT_DIR/venv"
HOST="0.0.0.0"
PORT="8000"

cd "$PROJECT_DIR" || exit 1

# 激活虚拟环境
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "❌ 虚拟环境未找到，请先运行 setup.sh"
    exit 1
fi

# 设置 Python 路径
export PYTHONPATH="$PROJECT_DIR:$PROJECT_DIR/core:$PROJECT_DIR/services:$PROJECT_DIR/database"

echo "=============================================="
echo "  🏥 TCM-AI 中医智能诊断系统"
echo "=============================================="
echo "  项目路径: $PROJECT_DIR"
echo "  访问地址: http://localhost:$PORT"
echo "  页面入口:"
echo "    - 登录页:     http://localhost:$PORT/login"
echo "    - 智能问诊:   http://localhost:$PORT/smart"
echo "    - 医生工作台: http://localhost:$PORT/doctor"
echo "    - 管理后台:   http://localhost:$PORT/admin"
echo "=============================================="
echo ""

# 启动服务器
uvicorn api.main:app --host "$HOST" --port "$PORT" --log-level info
