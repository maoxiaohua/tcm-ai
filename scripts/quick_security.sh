#!/bin/bash
# 快速安全加固脚本

echo "🔒 TCM系统安全加固..."

# 1. 阻止外部直接访问8000端口
if command -v iptables >/dev/null 2>&1; then
    # 允许本地访问8000端口
    sudo iptables -I INPUT -s 127.0.0.1 -p tcp --dport 8000 -j ACCEPT
    sudo iptables -I INPUT -s 172.17.0.0/16 -p tcp --dport 8000 -j ACCEPT
    
    # 阻止外部访问8000端口
    sudo iptables -I INPUT -p tcp --dport 8000 -j DROP
    
    echo "✅ 已阻止外部访问8000端口"
else
    echo "⚠️ iptables未找到，请手动配置防火墙"
fi

# 2. 检查当前监听端口
echo "📊 当前监听端口:"
netstat -tlnp | grep :8000 || ss -tlnp | grep :8000

echo "🔧 优化完成！"
echo "推荐访问地址:"
echo "  主应用: https://mxh0510.cn/app"
echo "  分享页: https://mxh0510.cn/share"
