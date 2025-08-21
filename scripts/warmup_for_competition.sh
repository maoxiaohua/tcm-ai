#!/bin/bash
# TCM系统比赛预热脚本

echo "🔥 TCM系统预热中..."

# 1. 清理旧日志
find /opt/tcm/conversation_logs -name "*.json" -mtime +1 -delete 2>/dev/null

# 2. 重启服务
sudo service tcm-api.service restart
echo "  ✅ 服务已重启"

# 3. 等待服务启动
sleep 10

# 4. 预热缓存 - 常见症状
curl -s -X POST "http://127.0.0.1:8000/chat_with_ai" \
  -H "Content-Type: application/json" \
  -d '{"message":"头痛","conversation_id":"warmup_1","selected_doctor":"zhang_zhongjing"}' \
  > /dev/null &

curl -s -X POST "http://127.0.0.1:8000/chat_with_ai" \
  -H "Content-Type: application/json" \
  -d '{"message":"失眠","conversation_id":"warmup_2","selected_doctor":"zhang_zhongjing"}' \
  > /dev/null &

curl -s -X POST "http://127.0.0.1:8000/chat_with_ai" \
  -H "Content-Type: application/json" \
  -d '{"message":"咳嗽","conversation_id":"warmup_3","selected_doctor":"zhang_zhongjing"}' \
  > /dev/null &

echo "  ✅ 缓存预热请求已发送"

# 5. 检查系统状态
sleep 30
curl -s "http://127.0.0.1:8000/debug_status" | jq -r '.cache_stats.hit_rate // "N/A"' | \
  xargs -I {} echo "  📊 缓存命中率: {}"

echo "🏆 系统预热完成，可以开始比赛！"
