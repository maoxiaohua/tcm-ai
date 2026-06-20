#!/bin/bash

# 决策树v3.0前端功能测试脚本

echo "======================================="
echo "决策树v3.0 前端功能测试"
echo "======================================="

BASE_URL="http://localhost:8000"
DOCTOR_ID="zhang_zhongjing"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "测试1: 检查页面是否可访问"
echo "-----------------------------------"
response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/static/decision_tree_v3_data_driven.html")
if [ "$response" == "200" ]; then
    echo -e "${GREEN}✅ 页面可访问 (HTTP $response)${NC}"
else
    echo -e "${RED}❌ 页面无法访问 (HTTP $response)${NC}"
    exit 1
fi

echo ""
echo "测试2: 检查JavaScript文件是否加载"
echo "-----------------------------------"
response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/static/js/decision_tree_data_driven.js")
if [ "$response" == "200" ]; then
    echo -e "${GREEN}✅ JavaScript文件可访问 (HTTP $response)${NC}"
else
    echo -e "${RED}❌ JavaScript文件无法访问 (HTTP $response)${NC}"
    exit 1
fi

echo ""
echo "测试3: 测试文本保存API"
echo "-----------------------------------"
save_response=$(curl -s -X POST "$BASE_URL/api/decision-tree-data/save-from-text" \
    -H "Content-Type: application/json" \
    -d '{
    "text_content": "【疾病】测试疾病\n【主症】测试症状",
    "doctor_id": "'$DOCTOR_ID'"
}')

if echo "$save_response" | grep -q '"success":true'; then
    echo -e "${GREEN}✅ 文本保存API正常${NC}"
    DECISION_ID=$(echo "$save_response" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null)
    echo "决策ID: $DECISION_ID"
else
    echo -e "${RED}❌ 文本保存API异常${NC}"
    echo "$save_response" | python3 -m json.tool 2>/dev/null
fi

echo ""
echo "测试4: 检查HTML中是否包含数据驱动标识"
echo "-----------------------------------"
if curl -s "$BASE_URL/static/decision_tree_v3_data_driven.html" | grep -q "决策树数据驱动v3.0模块"; then
    echo -e "${GREEN}✅ HTML包含数据驱动模块标识${NC}"
else
    echo -e "${YELLOW}⚠️  HTML未找到数据驱动模块标识${NC}"
fi

echo ""
echo "测试5: 检查页面标题"
echo "-----------------------------------"
title=$(curl -s "$BASE_URL/static/decision_tree_v3_data_driven.html" | grep -o '<title>.*</title>' | head -1)
if echo "$title" | grep -q "v3.0-Beta"; then
    echo -e "${GREEN}✅ 页面标题正确: $title${NC}"
else
    echo -e "${YELLOW}⚠️  页面标题: $title${NC}"
fi

echo ""
echo "======================================="
echo "前端功能测试完成"
echo "======================================="
echo ""
echo "访问地址:"
echo "https://mxh0510.cn/static/decision_tree_v3_data_driven.html"
echo ""
echo "功能说明:"
echo "1. 左侧文本框输入诊疗思路，500ms后自动保存到数据库"
echo "2. 保存后自动更新右侧画布显示"
echo "3. 右侧画布修改节点，500ms后自动保存到数据库"
echo "4. 点击"生成特色诊疗方案"按钮，AI自动生成并同步左右两侧"
echo "5. 右上角显示实时保存状态指示器"
echo ""
