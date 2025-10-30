#!/bin/bash
###############################################################################
# 一致性检查报告查看工具
# 快速查看检查结果的摘要和详细信息
###############################################################################

REPORT_FILE="template_files/consistency_check_report.json"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          TCM-AI 代码一致性检查报告查看器                      ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查报告文件是否存在
if [ ! -f "$REPORT_FILE" ]; then
    echo -e "${RED}❌ 报告文件不存在！${NC}"
    echo "   请先运行: python3 scripts/consistency_checker.py"
    exit 1
fi

# 解析JSON并显示摘要
echo -e "${BLUE}📊 统计摘要${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────${NC}"

BACKEND_APIS=$(cat $REPORT_FILE | python3 -c "import sys, json; print(json.load(sys.stdin)['statistics']['backend_apis'])")
FRONTEND_APIS=$(cat $REPORT_FILE | python3 -c "import sys, json; print(json.load(sys.stdin)['statistics']['frontend_apis'])")
DB_TABLES=$(cat $REPORT_FILE | python3 -c "import sys, json; print(json.load(sys.stdin)['statistics']['database_tables'])")

echo -e "  后端API端点:    ${GREEN}${BACKEND_APIS}${NC} 个"
echo -e "  前端API调用:    ${GREEN}${FRONTEND_APIS}${NC} 个"
echo -e "  数据库表:       ${GREEN}${DB_TABLES}${NC} 张"

echo ""
echo -e "${BLUE}🔍 问题统计${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────${NC}"

ERRORS=$(cat $REPORT_FILE | python3 -c "import sys, json; print(json.load(sys.stdin)['summary']['errors'])")
WARNINGS=$(cat $REPORT_FILE | python3 -c "import sys, json; print(json.load(sys.stdin)['summary']['warnings'])")
INFO=$(cat $REPORT_FILE | python3 -c "import sys, json; print(json.load(sys.stdin)['summary']['info'])")

echo -e "  ${RED}错误:${NC}          ${RED}${ERRORS}${NC} 个  ${RED}(必须修复)${NC}"
echo -e "  ${YELLOW}警告:${NC}          ${YELLOW}${WARNINGS}${NC} 个  ${YELLOW}(建议修复)${NC}"
echo -e "  ${GREEN}信息:${NC}          ${GREEN}${INFO}${NC} 个  ${GREEN}(仅供参考)${NC}"

echo ""

# 计算总体健康度
TOTAL_ISSUES=$((ERRORS + WARNINGS))
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    HEALTH="优秀"
    HEALTH_COLOR=$GREEN
    HEALTH_ICON="✅"
elif [ $ERRORS -eq 0 ] && [ $WARNINGS -lt 10 ]; then
    HEALTH="良好"
    HEALTH_COLOR=$GREEN
    HEALTH_ICON="👍"
elif [ $ERRORS -lt 5 ]; then
    HEALTH="一般"
    HEALTH_COLOR=$YELLOW
    HEALTH_ICON="⚠️"
else
    HEALTH="较差"
    HEALTH_COLOR=$RED
    HEALTH_ICON="❌"
fi

echo -e "${BLUE}💯 代码健康度${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────${NC}"
echo -e "  ${HEALTH_ICON}  ${HEALTH_COLOR}${HEALTH}${NC}  (总问题数: ${TOTAL_ISSUES})"

echo ""

# 提供快速操作选项
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}快速操作:${NC}"
echo ""
echo "  1️⃣  查看所有错误详情"
echo "  2️⃣  查看所有警告详情"
echo "  3️⃣  查看完整JSON报告"
echo "  4️⃣  导出错误到文件"
echo "  5️⃣  重新运行检查"
echo "  0️⃣  退出"
echo ""
echo -ne "${CYAN}请选择操作 (0-5): ${NC}"

read -r choice

case $choice in
    1)
        echo ""
        echo -e "${RED}╔════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║                    错误详情列表                                ║${NC}"
        echo -e "${RED}╚════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        cat $REPORT_FILE | python3 -c "
import sys, json
data = json.load(sys.stdin)
errors = data['details']['errors']
for i, err in enumerate(errors, 1):
    print(f'\033[0;31m[{i}] [{err[\"category\"]}] {err[\"message\"]}\033[0m')
    if err['details']:
        print(f'    {err[\"details\"]}')
    print()
"
        ;;
    2)
        echo ""
        echo -e "${YELLOW}╔════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║                    警告详情列表                                ║${NC}"
        echo -e "${YELLOW}╚════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        cat $REPORT_FILE | python3 -c "
import sys, json
data = json.load(sys.stdin)
warnings = data['details']['warnings']
for i, warn in enumerate(warnings, 1):
    print(f'\033[1;33m[{i}] [{warn[\"category\"]}] {warn[\"message\"]}\033[0m')
    if warn['details']:
        print(f'    {warn[\"details\"]}')
    print()
"
        ;;
    3)
        echo ""
        echo -e "${BLUE}完整JSON报告:${NC}"
        echo ""
        cat $REPORT_FILE | python3 -m json.tool | less
        ;;
    4)
        OUTPUT_FILE="template_files/consistency_errors_$(date +%Y%m%d_%H%M%S).txt"
        cat $REPORT_FILE | python3 -c "
import sys, json
data = json.load(sys.stdin)
errors = data['details']['errors']
for i, err in enumerate(errors, 1):
    print(f'[{i}] [{err[\"category\"]}] {err[\"message\"]}')
    if err['details']:
        print(f'    {err[\"details\"]}')
    print()
" > "$OUTPUT_FILE"
        echo -e "${GREEN}✓ 错误已导出到: ${OUTPUT_FILE}${NC}"
        ;;
    5)
        echo ""
        echo -e "${BLUE}重新运行检查...${NC}"
        echo ""
        python3 scripts/consistency_checker.py
        echo ""
        echo -e "${GREEN}✓ 检查完成，重新启动查看器...${NC}"
        echo ""
        bash scripts/view_consistency_report.sh
        ;;
    0)
        echo ""
        echo -e "${GREEN}再见！${NC}"
        ;;
    *)
        echo ""
        echo -e "${YELLOW}无效选择${NC}"
        ;;
esac

echo ""
