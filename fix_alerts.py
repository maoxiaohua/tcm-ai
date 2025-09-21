#!/usr/bin/env python3
import re

# 读取文件
with open('/opt/tcm-ai/static/doctor/index_optimized.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复所有多行alert语句
fixes = [
    # 本周工作总结
    (r"alert\(['\"]本周工作总结功能开发中[^)]*\);", 
     'alert("本周工作总结功能开发中...\\n\\n预计包含：\\n- 详细审查统计\\n- 效率对比分析\\n- 改进建议");'),
    
    # AI批量检查
    (r"alert\(`AI批量检查功能正在开发中[^)]*\);",
     'alert("AI批量检查功能正在开发中...\\n\\n将为 " + selectedPrescriptions.size + " 个处方进行：\\n- 药物相互作用检查\\n- 剂量安全评估\\n- 配伍禁忌分析\\n- 中医理论符合性验证");'),
    
    # 添加新患者
    (r"alert\(['\"]添加新患者功能正在开发中[^)]*\);",
     'alert("添加新患者功能正在开发中，将包括：\\n\\n📝 基本信息登记\\n📅 初诊预约\\n📊 病史记录\\n🗃️ 联系方式管理\\n\\n敬请期待！");'),
    
    # 患者详情 - 使用模板字符串修复
    (r"alert\(['\"]患者详情[^)]*档案功能正在开发中\.\.\.[^)]*\);",
     'alert("患者详情\\n\\n详细患者档案功能正在开发中...");'),
    
    # 预约随访
    (r"alert\(['\"]为[^)]*敬请期待！[^)]*\);",
     'alert("预约随访功能正在开发中，将包括：\\n\\n📅 灵活时间选择\\n🔔 随访提醒\\n📝 随访计划\\n📊 疗效评估\\n\\n敬请期待！");'),
    
    # 就诊历史
    (r"alert\([^)]*就诊历史功能正在开发中[^)]*\);",
     'alert("就诊历史功能正在开发中，将包括：\\n\\n📈 病情变化趋势\\n💊 用药历史记录\\n📝 诊断及处方历史\\n🗺️ 时间线视图\\n\\n敬请期待！");'),
]

# 应用修复
for pattern, replacement in fixes:
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# 特殊处理：学习中心函数已经修复，跳过

# 写回文件
with open('/opt/tcm-ai/static/doctor/index_optimized.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Alert statements fixed!")