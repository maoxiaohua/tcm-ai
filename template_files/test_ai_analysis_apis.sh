#!/bin/bash
###############################################################################
# 测试医生端AI分析API
# 用途：验证AI洞察分析和风险分析API是否正常工作
###############################################################################

echo "🧪 测试医生端AI分析API"
echo "=========================================="

# 获取一个有效的医生session token
DOCTOR_TOKEN=$(sqlite3 /opt/tcm-ai/data/user_history.sqlite "SELECT us.session_id FROM unified_sessions us JOIN unified_users uu ON us.user_id = uu.global_user_id LEFT JOIN user_roles_new ur ON uu.global_user_id = ur.user_id WHERE us.session_status='active' AND us.expires_at > datetime('now') AND ur.role_name='DOCTOR' LIMIT 1")

if [ -z "$DOCTOR_TOKEN" ]; then
    echo "❌ 未找到有效的医生session token"
    exit 1
fi

echo "✓ 找到医生token: ${DOCTOR_TOKEN:0:20}..."
echo ""

# 测试AI洞察分析API
echo "📊 测试 /api/prescription/ai/insights"
INSIGHTS_RESPONSE=$(curl -s -H "Authorization: Bearer $DOCTOR_TOKEN" http://localhost:8000/api/prescription/ai/insights)
INSIGHTS_SUCCESS=$(echo $INSIGHTS_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))")

if [ "$INSIGHTS_SUCCESS" = "True" ]; then
    echo "✅ AI洞察分析API测试成功"
    echo "   - 返回数据包含: trends, patterns, alerts, recommendations"
else
    echo "❌ AI洞察分析API测试失败"
    echo "   响应: $INSIGHTS_RESPONSE"
fi
echo ""

# 测试风险分析API
echo "⚠️  测试 /api/prescription/ai/risk-analysis"
RISK_RESPONSE=$(curl -s -H "Authorization: Bearer $DOCTOR_TOKEN" http://localhost:8000/api/prescription/ai/risk-analysis)
RISK_SUCCESS=$(echo $RISK_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))")

if [ "$RISK_SUCCESS" = "True" ]; then
    echo "✅ 风险分析API测试成功"
    echo "   - 返回数据包含: risk_distribution, risk_factors, recommendations"
else
    echo "❌ 风险分析API测试失败"
    echo "   响应: $RISK_RESPONSE"
fi
echo ""

echo "=========================================="
if [ "$INSIGHTS_SUCCESS" = "True" ] && [ "$RISK_SUCCESS" = "True" ]; then
    echo "🎉 所有测试通过！"
    exit 0
else
    echo "⚠️  部分测试失败，请检查日志"
    exit 1
fi
