#!/bin/bash
###############################################################################
# TCM-AI 部署前检查脚本
#
# 用途：在修改代码后、重启服务前，自动检查关键功能是否完整
#
# 使用方法：
#   bash scripts/pre_deploy_check.sh
#   或在git commit前运行
#
# 退出码：
#   0 = 所有检查通过
#   1 = 发现问题
###############################################################################

set -e

echo "🔍 TCM-AI 部署前检查"
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

FAILED=0

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check() {
    local test_name="$1"
    local test_command="$2"

    echo -n "  检查: $test_name ... "

    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# 检查带输出的函数
check_with_output() {
    local test_name="$1"
    local test_command="$2"
    local expected="$3"

    echo -n "  检查: $test_name ... "

    local output=$(eval "$test_command" 2>&1)

    if echo "$output" | grep -q "$expected"; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        echo "    预期包含: $expected"
        echo "    实际输出: $output"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo ""
echo "📁 1. 文件完整性检查"
check "主HTML文件存在" "[ -f static/index_smart_workflow.html ]"
check "处方管理器JS存在" "[ -f static/js/simple_prescription_manager.js ]"
check "认证管理器JS存在" "[ -f static/js/auth_manager.js ]"
check "主API文件存在" "[ -f api/main.py ]"

echo ""
echo "📜 2. 脚本加载检查"
check "处方管理器已加载" "grep -q 'simple_prescription_manager.js' static/index_smart_workflow.html"
check "处方管理器script标签未被注释" "! grep 'simple_prescription_manager.js' static/index_smart_workflow.html | grep -q '<!--.*<script'"
check "认证管理器已加载" "grep -q 'auth_manager.js\|authManager' static/index_smart_workflow.html"

echo ""
echo "🔧 3. 关键函数检查"
check "处方管理器类存在" "grep -q 'class SimplePrescriptionManager\|SimplePrescriptionManager' static/js/simple_prescription_manager.js"
check "主API文件可访问" "test -r api/main.py"

echo ""
echo "🎯 4. 处方管理器功能检查"
check "处方渲染方法存在" "grep -q 'renderContent\|renderApprovedContent' static/js/simple_prescription_manager.js"
check "处方状态检查方法" "grep -q 'checkPrescriptionStatus' static/js/simple_prescription_manager.js"

echo ""
echo "🔌 5. 核心API端点检查"
check "问诊API配置正确" "grep -rq '/api/consultation/chat\|/api/chat_with_ai' static/js/ static/index_smart_workflow.html"
check "处方API配置正确" "grep -rq '/api/prescription' static/js/ static/index_smart_workflow.html"

echo ""
echo "🛡️ 6. 基础完整性检查"
# 简化检查 - 只确保关键文件存在且不为空
check "HTML文件非空" "test -s static/index_smart_workflow.html"
check "处方管理器JS非空" "test -s static/js/simple_prescription_manager.js"

echo ""
echo "=========================================="

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ 所有检查通过！可以安全部署${NC}"
    exit 0
else
    echo -e "${RED}❌ 发现 $FAILED 个问题，请修复后再部署${NC}"
    exit 1
fi
