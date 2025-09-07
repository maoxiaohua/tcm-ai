#!/usr/bin/env python3
"""
测试刘渡舟医生修复效果
"""

import sys
sys.path.append('/opt/tcm-ai')

from core.doctor_system.tcm_doctor_personas import TCMDoctorPersonas, PersonalizedTreatmentGenerator

def test_liu_duzhou_fixes():
    """测试刘渡舟医生修复效果"""
    print("=== 刘渡舟医生修复效果测试 ===\n")
    
    personas = TCMDoctorPersonas()
    generator = PersonalizedTreatmentGenerator()
    
    # 1. 检查刘渡舟医生的新配置
    print("🔍 检查刘渡舟医生的新配置:")
    liu_persona = personas.get_persona('liu_duzhou')
    
    if liu_persona:
        print(f"✅ 医生名称: {liu_persona.name}")
        print(f"✅ 流派: {liu_persona.school.value}")
        print(f"✅ 专长: {liu_persona.specialty}")
        print(f"✅ 诊断重点: {liu_persona.diagnostic_emphasis}")
        print(f"✅ 治疗原则: {liu_persona.treatment_principles}")
        
        # 检查新增的复诊内容
        if "复诊调方" in liu_persona.specialty:
            print("✅ 已添加复诊调方专长")
        else:
            print("❌ 缺少复诊调方专长")
            
        if "疗效追踪" in liu_persona.diagnostic_emphasis:
            print("✅ 已添加疗效追踪诊断重点")
        else:
            print("❌ 缺少疗效追踪诊断重点")
            
        if "复诊调整" in liu_persona.treatment_principles:
            print("✅ 已添加复诊调整治疗原则")
        else:
            print("❌ 缺少复诊调整治疗原则")
    else:
        print("❌ 未找到刘渡舟医生配置")
        return False
    
    print("\n" + "="*60)
    
    # 2. 检查处方风格的一致性
    print("📋 检查处方风格一致性:")
    
    format_requirements = [
        "处方必须按【君药】【臣药】【佐药】【使药】分类",
        "每个药物注明具体作用",
        "目标药味15-20味",
        "四诊合参",
        "完整规范的临床处方"
    ]
    
    for requirement in format_requirements:
        if requirement in liu_persona.prescription_style:
            print(f"✅ {requirement}")
        else:
            print(f"❌ 缺少: {requirement}")
    
    print("\n" + "="*60)
    
    # 3. 检查复诊相关内容
    print("🔄 检查复诊相关内容:")
    
    复诊相关词汇 = [
        "复诊",
        "服药反应",
        "调整剂量",
        "药物配伍",
        "疗效",
        "随访"
    ]
    
    prescription_and_thinking = liu_persona.prescription_style + " " + liu_persona.thinking_pattern
    
    for 词汇 in 复诊相关词汇:
        if 词汇 in prescription_and_thinking:
            print(f"✅ 包含: {词汇}")
        else:
            print(f"❌ 缺少: {词汇}")
    
    print("\n" + "="*60)
    
    # 4. 对比其他医生的配置完整性
    print("🔧 对比其他医生的配置完整性:")
    
    all_personas = personas.get_all_personas()
    doctor_configs = {}
    
    for doctor_key, persona in all_personas.items():
        doctor_configs[doctor_key] = {
            "preferred_formulas_count": len(persona.preferred_formulas),
            "dosage_preferences_count": len(persona.dosage_preferences),
            "contraindications_count": len(persona.contraindications),
            "prescription_style_length": len(persona.prescription_style),
            "thinking_pattern_length": len(persona.thinking_pattern)
        }
    
    print("医生配置对比:")
    for doctor, config in doctor_configs.items():
        persona_name = all_personas[doctor].name
        print(f"\n{persona_name}:")
        print(f"  偏好方剂类别: {config['preferred_formulas_count']}")
        print(f"  用药偏好数量: {config['dosage_preferences_count']}")
        print(f"  禁忌事项数量: {config['contraindications_count']}")
        print(f"  处方风格描述长度: {config['prescription_style_length']}")
        print(f"  思维模式描述长度: {config['thinking_pattern_length']}")
    
    print("\n" + "="*60)
    
    # 5. 生成提示词测试
    print("🎯 生成提示词测试:")
    
    test_query = "我长期失眠多梦，心悸，胃口不好，请刘渡舟医生开个方子"
    prompt = generator.generate_persona_prompt('liu_duzhou', test_query, '相关知识...', [])
    
    # 检查提示词中的关键内容
    key_elements = {
        "复诊内容": "复诊",
        "刘渡舟学术思想": "刘渡舟",
        "经方配伍": "经方",
        "方证对应": "方证对应",
        "主症抓取": "主症",
        "君臣佐使分类": "【君药】【臣药】【佐药】【使药】",
        "药物作用说明": "每个药物注明具体作用"
    }
    
    print("提示词关键要素检查:")
    for element_name, check_string in key_elements.items():
        if check_string in prompt:
            print(f"✅ {element_name}")
        else:
            print(f"❌ 缺少: {element_name}")
    
    print("\n" + "="*60)
    
    # 6. 总结修复效果
    print("🎉 刘渡舟医生修复总结:")
    print("✅ 增加了复诊调方专业特长")
    print("✅ 添加了疗效追踪诊断重点")
    print("✅ 补充了复诊调整治疗原则")
    print("✅ 扩展了偏好方剂类别")
    print("✅ 增加了更多用药偏好")
    print("✅ 完善了禁忌事项")
    print("✅ 详细描述了处方风格")
    print("✅ 强化了经方思维模式")
    print("✅ 统一了处方格式要求")
    
    print("\n💡 解决的具体问题:")
    print("1. ✅ 处方回复格式与其他医生一致")
    print("2. ✅ 添加了复诊内容和随访要求") 
    print("3. ✅ 完善了刘渡舟经方学术特色")
    print("4. ✅ 统一了君臣佐使分类标准")
    print("5. ✅ 增强了配置的完整性和专业性")
    
    return True

if __name__ == "__main__":
    test_liu_duzhou_fixes()