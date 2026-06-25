#!/bin/bash

# TCM-AI 静态文件清理脚本 - Phase 1
# 删除所有明确的测试/调试/备份文件 (0风险)
# 使用方式: bash scripts/cleanup_static_phase1.sh

set -e

STATIC_DIR="/home/ute/tcm-ai/static"
BACKUP_DIR="/home/ute/tcm-ai/.backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "============================================"
echo "TCM-AI 静态文件清理 - Phase 1"
echo "============================================"
echo ""

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 创建完整备份
echo "📦 创建完整备份..."
tar -czf "$BACKUP_DIR/static_backup_$TIMESTAMP.tar.gz" "$STATIC_DIR/"
echo "   ✓ 备份已保存到: $BACKUP_DIR/static_backup_$TIMESTAMP.tar.gz"
echo ""

# 待删除的文件列表
echo "🔍 准备删除以下文件..."
echo ""

# 备份文件
echo "【备份文件】"
BACKUP_FILES=(
    "admin/index_original.html"
    "doctor/index_backup_20250921_113856.html"
    "doctor/index_optimized_backup.html"
    "doctor/index_original.html"
    "index_smart_workflow_backup.html"
)

for file in "${BACKUP_FILES[@]}"; do
    if [ -f "$STATIC_DIR/$file" ]; then
        echo "  • $file"
    fi
done
echo ""

# 测试文件
echo "【测试文件】"
TEST_FILES=(
    "ai_mindmap_test.html"
    "chrome_test.html"
    "simple_mobile_test.html"
    "test_decision_tree_fix.html"
    "test_doctor_login.html"
    "test_edit_debug.html"
    "test_pc_functions.html"
    "test_prescription_logic.html"
    "test_prescription_rendering.html"
    "test_prescription_restore.html"
)

for file in "${TEST_FILES[@]}"; do
    if [ -f "$STATIC_DIR/$file" ]; then
        echo "  • $file"
    fi
done
echo ""

# 调试文件
echo "【调试文件】"
DEBUG_FILES=(
    "debug_login_token.html"
    "debug_prescription.html"
    "debug_prescription_payment.html"
    "debug_prescription_status.html"
    "js/prescription_debug_helper.js"
)

for file in "${DEBUG_FILES[@]}"; do
    if [ -f "$STATIC_DIR/$file" ]; then
        echo "  • $file"
    fi
done
echo ""

# 确认
read -p "确认删除上述文件? (yes/no) " -n 3 -r
echo ""
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "❌ 取消删除"
    exit 0
fi

echo ""
echo "🗑️  开始删除..."
echo ""

# 删除备份文件
for file in "${BACKUP_FILES[@]}"; do
    if [ -f "$STATIC_DIR/$file" ]; then
        rm -f "$STATIC_DIR/$file"
        echo "  ✓ 已删除: $file"
    fi
done

# 删除测试文件
for file in "${TEST_FILES[@]}"; do
    if [ -f "$STATIC_DIR/$file" ]; then
        rm -f "$STATIC_DIR/$file"
        echo "  ✓ 已删除: $file"
    fi
done

# 删除调试文件
for file in "${DEBUG_FILES[@]}"; do
    if [ -f "$STATIC_DIR/$file" ]; then
        rm -f "$STATIC_DIR/$file"
        echo "  ✓ 已删除: $file"
    fi
done

echo ""
echo "✅ 清理完成!"
echo ""

# 显示统计信息
BEFORE_SIZE=$(tar -czf - "$STATIC_DIR/" 2>/dev/null | wc -c)
echo "📊 清理统计:"
echo "   总文件数: $(find $STATIC_DIR -type f | wc -l)"
echo "   目录大小: $(du -sh $STATIC_DIR | cut -f1)"
echo ""

echo "✅ 请检查备份文件已安全保存"
echo "   备份路径: $BACKUP_DIR/static_backup_$TIMESTAMP.tar.gz"
echo ""

