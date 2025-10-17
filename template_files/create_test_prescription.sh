#!/bin/bash
# 创建完整的测试处方数据

echo "🔍 步骤1: 创建问诊并生成处方"

# 生成唯一的conversation_id
CONV_ID="test_prescription_$(date +%s)"

# 问诊请求 - 确保AI生成处方
RESPONSE=$(curl -s -X POST http://localhost:8000/api/consultation/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"医生您好，我最近头痛很严重，主要是太阳穴和额头位置疼痛，伴有失眠多梦，心烦易怒，血压测量是150/95mmHg。舌质红，苔黄腻，脉弦数。请医生帮我看看是什么问题，需要怎么治疗？请给我开个方子吧。\",
    \"conversation_id\": \"$CONV_ID\",
    \"selected_doctor\": \"zhang_zhongjing\",
    \"patient_id\": \"usr_20250920_5741e17a78e8\"
  }")

echo "API响应:"
echo "$RESPONSE" | python3 -m json.tool

# 提取prescription_id
PRESCRIPTION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('prescription_id', 'none'))" 2>/dev/null || echo "none")

echo ""
echo "提取到的prescription_id: $PRESCRIPTION_ID"

if [ "$PRESCRIPTION_ID" = "none" ] || [ -z "$PRESCRIPTION_ID" ]; then
    echo "❌ 未生成处方，检查API响应中的contains_prescription字段"
    echo "$RESPONSE" | python3 -m json.tool | grep -A5 "contains_prescription"
    exit 1
fi

echo ""
echo "✅ 步骤1完成: 问诊已创建，处方ID=$PRESCRIPTION_ID"
echo ""
echo "🔍 步骤2: 验证处方数据"

# 查询数据库中的处方
sqlite3 /opt/tcm-ai/data/user_history.sqlite << EOF
.mode line
SELECT id, status, review_status, payment_status,
       substr(ai_prescription, 1, 100) || '...' as ai_prescription_preview,
       substr(diagnosis, 1, 100) || '...' as diagnosis_preview
FROM prescriptions
WHERE id = $PRESCRIPTION_ID;
EOF

echo ""
echo "✅ 步骤2完成: 处方数据已验证"
echo ""
echo "🔍 步骤3: 模拟支付（如果需要）"
echo "运行以下命令进行支付测试:"
echo "curl -X POST http://localhost:8000/api/prescription-review/payment-confirm \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"prescription_id\": $PRESCRIPTION_ID, \"payment_amount\": 88.0, \"payment_method\": \"alipay\"}'"
echo ""
echo "🔍 步骤4: 模拟医生审核（如果需要）"
echo "curl -X POST http://localhost:8000/api/prescription-review/doctor-review \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"prescription_id\": $PRESCRIPTION_ID, \"action\": \"approve\", \"doctor_notes\": \"处方合理，可以配药\"}'"
echo ""
echo "💾 保存prescription_id到文件"
echo "$PRESCRIPTION_ID" > /tmp/last_prescription_id.txt
echo "Prescription ID已保存到: /tmp/last_prescription_id.txt"
