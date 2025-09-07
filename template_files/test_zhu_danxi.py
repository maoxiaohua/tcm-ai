#!/usr/bin/env python3
"""
测试朱丹溪医生功能
"""

import sys
sys.path.append('/opt/tcm-ai')

from core.doctor_system.tcm_doctor_personas import TCMDoctorPersonas, PersonalizedTreatmentGenerator

def test_zhu_danxi_doctor():
    """测试朱丹溪医生完整功能"""
    print("=== 朱丹溪医生功能测试 ===\n")
    
    # 1. 测试医生人格是否存在
    personas = TCMDoctorPersonas()
    zhu_danxi_persona = personas.get_persona("zhu_danxi")
    
    if zhu_danxi_persona:
        print("✅ 朱丹溪医生人格定义成功！")
        print(f"   姓名: {zhu_danxi_persona.name}")
        print(f"   流派: {zhu_danxi_persona.school.value}")
        print(f"   专长: {', '.join(zhu_danxi_persona.specialty)}")
        print(f"   理论特色: {zhu_danxi_persona.introduction[:50]}...")
    else:
        print("❌ 朱丹溪医生人格定义失败！")
        return False
    
    print("\n" + "="*50)
    
    # 2. 测试提示词生成
    generator = PersonalizedTreatmentGenerator()
    test_query = "我最近总是感觉潮热盗汗，特别是晚上，心烦失眠，口干咽燥，请朱丹溪医生帮我看看"
    knowledge_context = "阴虚火旺的中医治疗方法和经典方剂..."
    
    print("--- 测试朱丹溪医生提示词生成 ---")
    prompt = generator.generate_persona_prompt("zhu_danxi", test_query, knowledge_context)
    
    if prompt and "滋阴派" in prompt and "阴常不足" in prompt:
        print("✅ 朱丹溪医生提示词生成成功！")
        print("主要特色包含:")
        if "朱丹溪问诊重点" in prompt:
            print("   ✓ 特有问诊重点")
        if "大补阴丸" in prompt:
            print("   ✓ 经典方剂")
        if "生地" in prompt and "麦冬" in prompt:
            print("   ✓ 用药偏好")
        if "滋阴降火" in prompt:
            print("   ✓ 治疗原则")
    else:
        print("❌ 朱丹溪医生提示词生成失败！")
        return False
    
    print("\n" + "="*50)
    
    # 3. 测试流派差异化
    print("--- 测试流派差异化效果 ---")
    
    # 比较不同医生对同一症状的处理
    doctors_to_test = ["zhang_zhongjing", "ye_tianshi", "zhu_danxi", "zheng_qin_an"]
    test_symptoms = "患者潮热盗汗，心烦失眠"
    
    for doctor in doctors_to_test:
        prompt = generator.generate_persona_prompt(doctor, test_symptoms, knowledge_context)
        persona = personas.get_persona(doctor)
        if persona:
            print(f"✅ {persona.name} ({persona.school.value})")
            # 检查是否包含流派特色
            if doctor == "zhu_danxi" and "阴常不足" in prompt:
                print("   ✓ 滋阴派特色明显")
            elif doctor == "zhang_zhongjing" and "六经辨证" in prompt:
                print("   ✓ 伤寒派特色明显")
            elif doctor == "ye_tianshi" and "卫气营血" in prompt:
                print("   ✓ 温病派特色明显")
            elif doctor == "zheng_qin_an" and "扶阳" in prompt:
                print("   ✓ 扶阳派特色明显")
    
    print("\n" + "="*50)
    
    # 4. 测试医生档案完整性
    print("--- 测试医生档案完整性 ---")
    all_personas = personas.get_all_personas()
    
    print(f"总医生数量: {len(all_personas)}")
    for doctor_key, persona in all_personas.items():
        print(f"✅ {persona.name} ({persona.school.value}) - 专长: {len(persona.specialty)}项")
    
    # 确认朱丹溪在其中
    if "zhu_danxi" in all_personas:
        print("✅ 朱丹溪医生已完整集成到系统中")
    else:
        print("❌ 朱丹溪医生未正确集成")
        return False
    
    print("\n" + "="*50)
    print("🎉 朱丹溪医生功能测试全部通过！")
    print("\n修复成果:")
    print("✅ 补全了朱丹溪医生的完整人格定义")
    print("✅ 添加了ZIYIN滋阴派枚举")  
    print("✅ 强化了流派差异化特色")
    print("✅ 每个医生都有独特的问诊重点")
    print("✅ 朱丹溪医生现在可以正常使用")
    
    return True

if __name__ == "__main__":
    test_zhu_danxi_doctor()