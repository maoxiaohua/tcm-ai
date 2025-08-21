#!/bin/bash
# TCM测试环境快速搭建脚本
# 作者: Claude Code Assistant
# 日期: 2025-08-04

set -e  # 遇到错误立即退出

echo "🚀 开始创建TCM测试环境..."

# 检查权限
if [[ $EUID -ne 0 ]]; then
   echo "❌ 此脚本需要root权限运行"
   echo "请使用: sudo bash setup_test_environment.sh"
   exit 1
fi

# 检查生产环境是否存在
if [ ! -d "/opt/tcm" ]; then
    echo "❌ 生产环境 /opt/tcm 不存在"
    exit 1
fi

echo "📋 检查当前状态..."
echo "生产环境: $(systemctl is-active tcm-api.service 2>/dev/null || echo '未运行')"
echo "测试环境: $(systemctl is-active tcm-test.service 2>/dev/null || echo '不存在')"

# 创建测试环境目录
echo "📁 创建测试环境目录..."
if [ -d "/opt/tcm-test" ]; then
    echo "⚠️  测试环境已存在，是否覆盖? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        systemctl stop tcm-test.service 2>/dev/null || true
        rm -rf /opt/tcm-test
    else
        echo "❌ 取消创建"
        exit 1
    fi
fi

# 复制生产环境
echo "📦 复制生产环境到测试环境..."
cp -r /opt/tcm /opt/tcm-test
cd /opt/tcm-test

# 修改端口配置
echo "🔧 配置测试环境端口为8001..."
if grep -q "port=8000" main.py; then
    sed -i 's/port=8000/port=8001/g' main.py
    echo "✅ 端口修改完成"
elif grep -q 'host="0.0.0.0"' main.py; then
    # 如果没有找到port=8000，寻找uvicorn.run并添加端口
    sed -i 's/uvicorn.run(app, host="0.0.0.0")/uvicorn.run(app, host="0.0.0.0", port=8001)/g' main.py
    echo "✅ 添加端口配置完成"
else
    echo "⚠️  未找到端口配置，请手动修改main.py中的端口为8001"
fi

# 清理测试数据
echo "🗑️  清理测试数据..."
rm -rf data/cache.sqlite 2>/dev/null || true
rm -rf conversation_logs/* 2>/dev/null || true
mkdir -p data conversation_logs

# 创建测试环境专用配置
echo "⚙️  创建测试环境配置..."
cat > test_config.txt << EOF
=== TCM测试环境配置 ===
端口: 8001
数据库: 独立测试数据库
缓存: 独立测试缓存
创建时间: $(date)
EOF

# 创建测试服务配置文件
echo "🔧 创建systemd服务配置..."
cp /etc/systemd/system/tcm-api.service /etc/systemd/system/tcm-test.service

# 修改服务配置
sed -i 's|/opt/tcm|/opt/tcm-test|g' /etc/systemd/system/tcm-test.service
sed -i 's/tcm-api/tcm-test/g' /etc/systemd/system/tcm-test.service
sed -i 's/AI中医智能问诊系统/AI中医智能问诊系统-测试版/g' /etc/systemd/system/tcm-test.service

# 重新加载systemd配置
echo "🔄 重新加载系统服务配置..."
systemctl daemon-reload

# 启动测试服务
echo "🚀 启动测试服务..."
systemctl enable tcm-test.service
systemctl start tcm-test.service

# 等待服务启动
echo "⏳ 等待测试服务启动..."
sleep 5

# 检查服务状态
if systemctl is-active --quiet tcm-test.service; then
    echo "✅ 测试服务启动成功!"
else
    echo "❌ 测试服务启动失败，查看日志:"
    journalctl -u tcm-test.service --no-pager -n 10
    exit 1
fi

# 创建便捷管理脚本
echo "📝 创建管理脚本..."
cat > /opt/tcm-test/manage_test.sh << 'EOF'
#!/bin/bash
# TCM测试环境管理脚本

case "$1" in
start)
    sudo systemctl start tcm-test.service
    echo "✅ 测试服务已启动"
    ;;
stop)
    sudo systemctl stop tcm-test.service
    echo "⏹️  测试服务已停止"
    ;;
restart)
    sudo systemctl restart tcm-test.service
    echo "🔄 测试服务已重启"
    ;;
status)
    systemctl status tcm-test.service
    ;;
logs)
    sudo journalctl -u tcm-test.service -f
    ;;
test)
    echo "🧪 测试API连接..."
    curl -s http://localhost:8001/debug_status | head -100
    ;;
sync)
    echo "🔄 从生产环境同步代码..."
    sudo cp /opt/tcm/main.py /opt/tcm-test/main.py
    sudo systemctl restart tcm-test.service
    echo "✅ 同步完成"
    ;;
*)
    echo "TCM测试环境管理脚本"
    echo "用法: $0 {start|stop|restart|status|logs|test|sync}"
    echo ""
    echo "命令说明:"
    echo "  start   - 启动测试服务"
    echo "  stop    - 停止测试服务"  
    echo "  restart - 重启测试服务"
    echo "  status  - 查看服务状态"
    echo "  logs    - 查看实时日志"
    echo "  test    - 测试API连接"
    echo "  sync    - 从生产环境同步代码"
    ;;
esac
EOF

chmod +x /opt/tcm-test/manage_test.sh

# 创建快速测试脚本
cat > /opt/tcm-test/quick_test.sh << 'EOF'
#!/bin/bash
# 快速API测试脚本

echo "🧪 快速测试TCM测试环境..."

# 测试健康检查
echo "1. 测试系统状态..."
curl -s http://localhost:8001/debug_status | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'✅ 服务状态: {data.get(\"server_status\", \"未知\")}')
    print(f'✅ 缓存系统: {data.get(\"cache_system_available\", \"未知\")}')
except:
    print('❌ API无响应')
"

# 测试聊天功能
echo "2. 测试聊天API..."
curl -s -X POST http://localhost:8001/chat_with_ai \
  -H "Content-Type: application/json" \
  -d '{
    "message": "头痛测试",
    "conversation_id": "test_001",
    "selected_doctor": "张仲景"
  }' | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('reply'):
        print('✅ 聊天API正常，响应长度:', len(data.get('reply', '')))
    else:
        print('❌ 聊天API异常')
except Exception as e:
    print('❌ 聊天API测试失败:', e)
"

echo "🎯 测试完成!"
EOF

chmod +x /opt/tcm-test/quick_test.sh

# 最终状态检查
echo ""
echo "🎉 TCM测试环境创建完成!"
echo ""
echo "📊 环境信息:"
echo "├── 生产环境: http://localhost:8000 (端口8000)"
echo "├── 测试环境: http://localhost:8001 (端口8001)"
echo "├── 生产服务: sudo systemctl status tcm-api.service"
echo "└── 测试服务: sudo systemctl status tcm-test.service"
echo ""
echo "🔧 管理命令:"
echo "├── 测试环境管理: /opt/tcm-test/manage_test.sh {start|stop|restart|status|logs|test|sync}"
echo "├── 快速测试: /opt/tcm-test/quick_test.sh"
echo "├── 查看测试日志: sudo journalctl -u tcm-test.service -f"
echo "└── 同步生产代码: /opt/tcm-test/manage_test.sh sync"
echo ""
echo "🧪 立即测试:"
echo "curl http://localhost:8001/debug_status"
echo ""
echo "✅ 现在可以安全地在端口8001上进行测试，不会影响生产环境!"

# 运行快速测试
echo ""
echo "🚀 运行快速测试验证..."
cd /opt/tcm-test
./quick_test.sh