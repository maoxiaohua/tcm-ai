#!/bin/bash
###############################################################################
# 代码一致性检查系统 - 安装脚本
# 用于确保所有组件正确安装和配置
###############################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       TCM-AI 代码一致性检查系统 - 安装向导                   ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 检查函数
check_file() {
    local file="$1"
    local name="$2"

    echo -n "  检查 $name ... "

    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# 1. 检查必要文件
echo -e "${BLUE}[1/5] 检查必要文件${NC}"
echo "────────────────────────────────────────"

FILES_OK=true

check_file "scripts/consistency_checker.py" "一致性检查引擎" || FILES_OK=false
check_file "scripts/view_consistency_report.sh" "报告查看器" || FILES_OK=false
check_file ".git/hooks/pre-commit" "Git提交钩子" || FILES_OK=false

if [ "$FILES_OK" = false ]; then
    echo ""
    echo -e "${RED}错误: 缺少必要文件！${NC}"
    exit 1
fi

echo ""

# 2. 设置文件权限
echo -e "${BLUE}[2/5] 设置文件权限${NC}"
echo "────────────────────────────────────────"

chmod +x scripts/consistency_checker.py
echo -e "  ${GREEN}✓${NC} consistency_checker.py"

chmod +x scripts/view_consistency_report.sh
echo -e "  ${GREEN}✓${NC} view_consistency_report.sh"

chmod +x .git/hooks/pre-commit
echo -e "  ${GREEN}✓${NC} pre-commit hook"

echo ""

# 3. 检查Python环境
echo -e "${BLUE}[3/5] 检查Python环境${NC}"
echo "────────────────────────────────────────"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "  ${GREEN}✓${NC} Python 3 已安装: $PYTHON_VERSION"
else
    echo -e "  ${RED}✗${NC} Python 3 未安装"
    exit 1
fi

# 检查Python版本
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')

if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 7 ]; then
    echo -e "  ${GREEN}✓${NC} Python版本符合要求 (>= 3.7)"
else
    echo -e "  ${YELLOW}⚠${NC} Python版本较低 (建议 >= 3.7)"
fi

echo ""

# 4. 创建必要目录
echo -e "${BLUE}[4/5] 创建必要目录${NC}"
echo "────────────────────────────────────────"

mkdir -p template_files
echo -e "  ${GREEN}✓${NC} template_files/"

mkdir -p data
echo -e "  ${GREEN}✓${NC} data/"

echo ""

# 5. 运行测试
echo -e "${BLUE}[5/5] 运行测试${NC}"
echo "────────────────────────────────────────"

echo -e "  测试: 运行一致性检查..."

if python3 scripts/consistency_checker.py > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} 一致性检查运行成功"
else
    echo -e "  ${YELLOW}⚠${NC} 一致性检查有警告（正常）"
fi

if [ -f "template_files/consistency_check_report.json" ]; then
    echo -e "  ${GREEN}✓${NC} 报告文件已生成"
else
    echo -e "  ${RED}✗${NC} 报告文件未生成"
fi

echo ""

# 安装完成
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 安装完成！${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}📚 快速开始:${NC}"
echo ""
echo "  1️⃣  运行检查:"
echo -e "     ${YELLOW}python3 scripts/consistency_checker.py${NC}"
echo ""
echo "  2️⃣  查看报告:"
echo -e "     ${YELLOW}bash scripts/view_consistency_report.sh${NC}"
echo ""
echo "  3️⃣  Git提交（自动检查）:"
echo -e "     ${YELLOW}git add .${NC}"
echo -e "     ${YELLOW}git commit -m \"修改说明\"${NC}"
echo ""
echo -e "${CYAN}📖 文档位置:${NC}"
echo ""
echo "  • 系统README:"
echo -e "    ${YELLOW}cat template_files/代码一致性检查系统README.md | less${NC}"
echo ""
echo "  • 使用指南:"
echo -e "    ${YELLOW}cat template_files/代码一致性检查系统使用指南.md | less${NC}"
echo ""
echo "  • 快速参考:"
echo -e "    ${YELLOW}cat template_files/一致性检查快速参考卡.md | less${NC}"
echo ""
echo -e "${GREEN}💡 提示: 将快速参考卡添加到书签，开发时随时查看！${NC}"
echo ""
