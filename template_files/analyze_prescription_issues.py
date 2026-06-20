#!/usr/bin/env python3
"""
分析处方问题
"""

import sys
sys.path.append('/opt/tcm-ai')

from core.doctor_system.tcm_doctor_personas import TCMDoctorPersonas, PersonalizedTreatmentGenerator

def analyze_prescription_issues():
    """分析处方数量和朱丹溪医生回复问题"""
    print("=== 处方问题分析 ===\n")
    
    personas = TCMDoctorPersonas()
    generator = PersonalizedTreatmentGenerator()
    
    # 1. 分析所有医生的药味数量配置
    print("🔍 当前医生药味数量配置:")
    all_personas = personas.get_all_personas()
    
    for doctor_key, persona in all_personas.items():
        prescription_style = persona.prescription_style
        
        # 提取目标药味数量
        import re
        match = re.search(r'目标药味(\d+)-(\d+)味', prescription_style)
        if match:
            min_herbs = int(match.group(1))
            max_herbs = int(match.group(2))
            print(f"  {persona.name}: {min_herbs}-{max_herbs}味")
            
            if max_herbs < 15:
                print(f"    ⚠️  数量偏少，现实中医生通常开15+味")
        else:
            print(f"  {persona.name}: 未找到药味数量配置")
    
    print("\n" + "="*50)
    
    # 2. 分析现实中医处方的典型特点
    print("📊 现实中医处方分析:")
    print("✅ 现实中医生处方特点:")
    print("  - 药味数量: 通常15-25味")
    print("  - 基础方剂: 5-8味经典方")
    print("  - 症状加减: 3-6味针对性药物")
    print("  - 体质调理: 2-4味体质药")
    print("  - 现代适应: 2-3味现代病症药")
    print("  - 引经佐使: 1-2味")
    
    print("\n⚠️  当前系统问题:")
    print("  - 药味数量偏少: 10-16味 vs 现实15-25味")
    print("  - 可能导致处方不够全面和实用")
    
    print("\n" + "="*50)
    
    # 3. 测试朱丹溪医生的回复倾向
    print("🔍 测试朱丹溪医生回复:")
    test_cases = [
        "我最近总是感觉潮热盗汗，特别是晚上，心烦失眠，口干咽燥，请开个方子",
        "阴虚火旺的症状，希望得到具体的中药处方",
        "更年期症状，潮热严重，能否给个滋阴的方子"
    ]
    
    for i, test_query in enumerate(test_cases, 1):
        print(f"\n测试案例 {i}: {test_query[:30]}...")
        prompt = generator.generate_persona_prompt('zhu_danxi', test_query, '相关知识...', [])
        
        # 检查是否包含鼓励开方的内容
        encouraging_phrases = [
            "给出具体的方剂和用药指导",
            "应给出具体的治疗方案和处方指导",
            "积极治疗"
        ]
        
        discouraging_phrases = [
            "建议面诊",
            "到医院就诊", 
            "线下就医",
            "不能替代医生诊断"
        ]
        
        encourages_prescription = any(phrase in prompt for phrase in encouraging_phrases)
        discourages_prescription = any(phrase in prompt for phrase in discouraging_phrases)
        
        print(f"  鼓励开方: {'✅' if encourages_prescription else '❌'}")
        print(f"  劝导面诊: {'⚠️' if discourages_prescription else '✅'}")
    
    print("\n" + "="*50)
    
    # 4. 分析系统定位和目标
    print("🎯 系统定位分析:")
    print("✅ 正确定位 - AI预诊系统:")
    print("  - 门诊前预先收集病史")
    print("  - 协助医生快速了解患者")
    print("  - 提供符合医生思维的初步处方")
    print("  - 减少医生问诊时间")
    print("  - 提高诊疗效率")
    
    print("\n❌ 当前可能存在的问题:")
    print("  - 处方药味数量不够现实")
    print("  - 可能过于保守，不敢开方")
    print("  - 没有充分体现预诊系统的价值")
    
    print("\n" + "="*50)
    
    # 5. 提出优化建议
    print("💡 优化建议:")
    print("📋 处方数量优化:")
    print("  - 调整目标药味: 15-25味")
    print("  - 张仲景: 15-20味 (经方+现代加减)")
    print("  - 叶天士: 18-25味 (温病方+清热养阴)")
    print("  - 李东垣: 16-22味 (补土方+脾胃调理)")
    print("  - 朱丹溪: 17-23味 (滋阴方+清热降火)")
    print("  - 刘渡舟: 15-20味 (经方+灵活加减)")
    print("  - 郑钦安: 16-21味 (扶阳方+安全配伍)")
    
    print("\n🎭 角色定位优化:")
    print("  - 强调预诊辅助价值")
    print("  - 提供实用的初步处方")
    print("  - 明确说明医生会最终确认")
    print("  - 减少过度保守的表述")
    
    return True

if __name__ == "__main__":
    analyze_prescription_issues()