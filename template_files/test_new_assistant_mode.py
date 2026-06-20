#!/usr/bin/env python3
"""
测试新的诊疗助手模式
"""

import requests
import json
import time

def test_medical_assistant_mode():
    """测试诊疗助手模式效果"""
    
    print("🩺 测试诊疗助手模式")
    print("="*60)
    
    # 模拟医生的具体诊疗思路
    doctor_thinking = """
    患者，男，45岁，腰痛3个月。
    
    我的诊疗分析：
    1. 主症：腰部冷痛，遇寒加重，喜温喜按
    2. 兼症：畏寒肢冷，夜尿频多，精神疲倦
    3. 舌象：舌质淡胖，苔白润
    4. 脉象：脉沉细无力
    
    我的证型判断：肾阳虚证
    我的治法：温补肾阳，强腰止痛
    我的处方：右归丸加减
    - 熟地黄20g（君药，补肾填精）
    - 肉桂6g（臣药，温肾助阳）
    - 附子10g（佐药，回阳救逆）
    - 山药15g（补脾肾）
    - 杜仲15g（强腰膝）
    - 当归12g（补血活血）
    
    希望AI助手帮我验证这个诊疗思路的完整性和合理性。
    """
    
    request_data = {
        "disease_name": "腰痛",
        "thinking_process": doctor_thinking,
        "use_ai": True,
        "include_tcm_analysis": True,
        "complexity_level": "standard"
    }
    
    print("📝 医生诊疗思路：")
    print("- 证型：肾阳虚证")  
    print("- 治法：温补肾阳")
    print("- 方剂：右归丸加减")
    print("- 君药：熟地黄20g")
    print("- 臣药：肉桂6g")
    print("- 佐药：附子10g")
    
    start_time = time.time()
    
    response = requests.post(
        "http://localhost:8000/api/generate_visual_decision_tree",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )
    
    end_time = time.time()
    
    if response.status_code != 200:
        print(f"❌ API调用失败: {response.status_code}")
        return False
    
    result = response.json()
    print(f"⏱️ 响应时间: {end_time - start_time:.1f}秒")
    
    if not result.get('success'):
        print(f"❌ 请求失败: {result.get('message')}")
        return False
    
    data = result.get('data', {})
    paths = data.get('paths', [])
    
    if not paths:
        print("❌ 没有生成辅助决策树")
        return False
    
    path = paths[0]
    print(f"\n📋 AI助手生成的决策辅助树:")
    print(f"标题: {path.get('title', 'N/A')}")
    
    steps = path.get('steps', [])
    print(f"\n🔍 辅助验证步骤 ({len(steps)}步):")
    
    for i, step in enumerate(steps, 1):
        step_type = step.get('type', 'unknown')
        content = step.get('content', 'N/A')
        
        print(f"  {i}. [{step_type}] {content}")
        if step.get('options'):
            print(f"     选项: {step.get('options')}")
    
    # 检查是否体现医生个性化思路
    doctor_insights = path.get('doctor_insights', '')
    improvement_suggestions = path.get('improvement_suggestions', '')
    
    print(f"\n💡 医生思路特色识别:")
    print(f"   {doctor_insights}")
    
    print(f"\n📈 优化建议:")
    print(f"   {improvement_suggestions}")
    
    # 检查关键信息是否被正确识别
    full_content = json.dumps(path, ensure_ascii=False)
    key_points = ['肾阳虚', '右归丸', '熟地黄', '肉桂', '附子', '温补肾阳']
    found_points = [point for point in key_points if point in full_content]
    
    print(f"\n🎯 医生思路识别度:")
    print(f"   识别到的关键点: {found_points}")
    print(f"   识别率: {len(found_points)}/{len(key_points)} = {len(found_points)/len(key_points)*100:.1f}%")
    
    # 检查是否是辅助验证模式而非替代模式
    is_assistant_mode = any(
        '验证' in content or '确认' in content or '审核' in content or '核实' in content
        for step in steps
        for content in [step.get('content', '')]
    )
    
    print(f"\n✅ 模式检验:")
    print(f"   辅助验证模式: {'是' if is_assistant_mode else '否'}")
    print(f"   数据源: {data.get('source', 'unknown')}")
    print(f"   AI生成: {data.get('ai_generated', False)}")
    
    success = (
        len(found_points) >= 4 and  # 识别到医生的主要思路
        is_assistant_mode and       # 是辅助模式而非替代模式
        len(steps) >= 5             # 有完整的验证流程
    )
    
    print(f"\n🎯 测试结果: {'✅ 成功' if success else '❌ 需优化'}")
    
    if success:
        print("🎉 AI现在作为诊疗助手，帮助医生验证和优化诊疗思路！")
        print("🎉 体现了'一人一诊，一人一方'的个性化特色！")
    else:
        print("⚠️ AI助手模式需要进一步调优")
    
    return success

if __name__ == "__main__":
    time.sleep(8)  # 等待服务器启动
    test_medical_assistant_mode()