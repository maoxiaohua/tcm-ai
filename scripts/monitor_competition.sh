#!/bin/bash
# TCM系统实时监控脚本

echo "📊 TCM系统实时监控"
echo "==================="

while true; do
    clear
    echo "📊 TCM系统实时监控 - $(date '+%H:%M:%S')"
    echo "============================================"
    
    # 服务状态
    if systemctl is-active --quiet tcm-api.service; then
        echo "🟢 服务状态: 运行中"
    else
        echo "🔴 服务状态: 停止"
    fi
    
    # 进程信息
    ps aux | grep -E "(python.*main|uvicorn)" | grep -v grep | \
      awk '{printf "⚡ 进程: %s (CPU: %s%%, MEM: %s%%)
", $2, $3, $4}'
    
    # 内存使用
    free -h | awk 'NR==2{printf "💾 内存: %s/%s (%.1f%%)
", $3, $2, $3/$2*100}'
    
    # 系统负载
    uptime | awk -F'load average:' '{printf "📈 负载: %s
", $2}'
    
    # 缓存状态
    curl -s "http://127.0.0.1:8000/debug_status" 2>/dev/null | \
      jq -r '"🎯 缓存命中率: " + (.cache_stats.hit_rate // "N/A")' 2>/dev/null || \
      echo "🎯 缓存状态: 获取失败"
    
    # 最近请求数
    tail -n 50 /var/log/syslog 2>/dev/null | grep "tcm-api" | grep "$(date '+%H:%M')" | wc -l | \
      xargs -I {} echo "📋 最近1分钟请求: {}次"
    
    echo ""
    echo "按Ctrl+C退出监控"
    
    sleep 5
done
