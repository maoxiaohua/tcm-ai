#!/bin/bash
# AI智能思维导图系统 - 功能测试脚本

echo "======================================"
echo "  AI智能思维导图系统 - 功能测试"
echo "======================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000"

# 测试计数
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试函数
test_case() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    local test_name="$1"
    local result="$2"

    if [ "$result" == "PASS" ]; then
        echo -e "${GREEN}✓ PASS${NC} - $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ FAIL${NC} - $test_name"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

echo "【1】测试页面访问"
echo "------------------------------"

# 测试1: 主页面访问
response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/mindmap")
if [ "$response" == "200" ]; then
    test_case "访问思维导图主页 (/mindmap)" "PASS"
else
    test_case "访问思维导图主页 (/mindmap) - HTTP $response" "FAIL"
fi

echo ""
echo "【2】测试API接口"
echo "------------------------------"

# 测试2: 生成思维导图 - 技术领域
echo -n "生成思维导图(技术领域)... "
response=$(curl -s -X POST "$BASE_URL/api/mindmap/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "数据库性能优化",
    "description": "系统性分析数据库性能问题，提供优化方案",
    "domain": "technical",
    "max_levels": 3,
    "max_children": 4
  }')

if echo "$response" | grep -q '"success":true'; then
    mindmap_id=$(echo "$response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    test_case "生成思维导图(技术领域) - ID: $mindmap_id" "PASS"
else
    test_case "生成思维导图(技术领域)" "FAIL"
    mindmap_id=""
fi

# 测试3: 生成思维导图 - 医疗领域
echo -n "生成思维导图(医疗领域)... "
response=$(curl -s -X POST "$BASE_URL/api/mindmap/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "糖尿病中医诊疗",
    "description": "从中医角度分析糖尿病的病因病机和治疗方案",
    "domain": "medical",
    "max_levels": 4,
    "max_children": 5
  }')

if echo "$response" | grep -q '"success":true'; then
    medical_mindmap_id=$(echo "$response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    test_case "生成思维导图(医疗领域) - ID: $medical_mindmap_id" "PASS"
else
    test_case "生成思维导图(医疗领域)" "FAIL"
    medical_mindmap_id=""
fi

# 测试4: 保存思维导图
if [ -n "$mindmap_id" ]; then
    echo -n "保存思维导图... "
    save_response=$(curl -s -X POST "$BASE_URL/api/mindmap/save" \
      -H "Content-Type: application/json" \
      -d "{
        \"mindmap_id\": \"$mindmap_id\",
        \"title\": \"数据库性能优化\",
        \"description\": \"测试保存功能\",
        \"domain\": \"technical\",
        \"data\": {}
      }")

    if echo "$save_response" | grep -q '"success":true'; then
        test_case "保存思维导图 - ID: $mindmap_id" "PASS"
    else
        test_case "保存思维导图" "FAIL"
    fi
fi

# 测试5: 加载思维导图
if [ -n "$mindmap_id" ]; then
    echo -n "加载思维导图... "
    load_response=$(curl -s -X GET "$BASE_URL/api/mindmap/load/$mindmap_id")

    if echo "$load_response" | grep -q '"success":true'; then
        test_case "加载思维导图 - ID: $mindmap_id" "PASS"
    else
        test_case "加载思维导图" "FAIL"
    fi
fi

# 测试6: 获取思维导图列表
echo -n "获取思维导图列表... "
list_response=$(curl -s -X GET "$BASE_URL/api/mindmap/list?limit=10")

if echo "$list_response" | grep -q '"success":true'; then
    count=$(echo "$list_response" | grep -o '"mindmaps":\[' | wc -l)
    test_case "获取思维导图列表" "PASS"
else
    test_case "获取思维导图列表" "FAIL"
fi

# 测试7: 生成思维导图 - 商业领域
echo -n "生成思维导图(商业领域)... "
response=$(curl -s -X POST "$BASE_URL/api/mindmap/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "市场营销策略",
    "description": "分析市场营销的策略制定和执行过程",
    "domain": "business",
    "max_levels": 3,
    "max_children": 4
  }')

if echo "$response" | grep -q '"success":true'; then
    test_case "生成思维导图(商业领域)" "PASS"
else
    test_case "生成思维导图(商业领域)" "FAIL"
fi

echo ""
echo "【3】测试数据库"
echo "------------------------------"

# 测试8: 检查数据库表
echo -n "检查mindmaps表... "
table_exists=$(sqlite3 /home/ute/tcm-ai/data/user_history.sqlite "SELECT name FROM sqlite_master WHERE type='table' AND name='mindmaps';" 2>/dev/null)

if [ "$table_exists" == "mindmaps" ]; then
    test_case "数据库表存在" "PASS"
else
    test_case "数据库表存在" "FAIL"
fi

# 测试9: 统计记录数
echo -n "统计思维导图记录... "
count=$(sqlite3 /home/ute/tcm-ai/data/user_history.sqlite "SELECT COUNT(*) FROM mindmaps;" 2>/dev/null)

if [ -n "$count" ]; then
    test_case "数据库记录统计 - 共 $count 条记录" "PASS"
else
    test_case "数据库记录统计" "FAIL"
fi

echo ""
echo "【4】测试文件完整性"
echo "------------------------------"

# 测试10: 检查核心文件
files=(
    "/home/ute/tcm-ai/core/mindmap/ai_mindmap_generator.py"
    "/home/ute/tcm-ai/core/mindmap/__init__.py"
    "/home/ute/tcm-ai/api/routes/mindmap_routes.py"
    "/home/ute/tcm-ai/static/mindmap/index.html"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        test_case "文件存在: $file" "PASS"
    else
        test_case "文件存在: $file" "FAIL"
    fi
done

echo ""
echo "======================================"
echo "           测试结果汇总"
echo "======================================"
echo -e "总测试数: ${YELLOW}$TOTAL_TESTS${NC}"
echo -e "通过: ${GREEN}$PASSED_TESTS${NC}"
echo -e "失败: ${RED}$FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 所有测试通过！系统运行正常${NC}"
    exit 0
else
    echo -e "${RED}⚠️  有 $FAILED_TESTS 个测试失败，请检查系统配置${NC}"
    exit 1
fi
