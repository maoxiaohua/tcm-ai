#!/usr/bin/env python3
"""
AI功能验证测试
验证AI是否真实调用Dashscope API并处理用户输入的右归丸加减
"""

import requests
import json
import time

def test_ai_real_functionality():
    """测试AI真实功能"""
    print("🔍 测试AI真实功能...")
    
    # 测试AI状态
    status_response = requests.get("http://localhost:8000/api/ai_status")
    print(f"AI状态: {status_response.json()}")
    
    # 用户的真实输入：右归丸加减
    test_data = {
        "disease_name": "腰痛", 
        "thinking_process": "患者腰痛，辨证为肾阳虚证。肾阳虚则温煦无力，腰府失养而痛。治法：温补肾阳，强腰止痛。方药：右归丸加减。熟地黄20g补肾填精，山药15g健脾补肾，山茱萸12g补肝肾，枸杞子15g滋补肝肾，鹿角胶10g（烊化）温补肾阳，菟丝子15g补肾固精，杜仲15g补肾强腰，当归12g补血活血，肉桂6g温肾助阳，附子10g（先煎）回阳救逆。",
        "complexity_level": "intermediate",
        "ai_mode": True
    }
    
    print("📤 发送AI请求（用户输入：右归丸加减）...")
    start_time = time.time()
    
    response = requests.post(
        "http://localhost:8000/api/generate_visual_decision_tree",
        json=test_data,
        headers={"Content-Type": "application/json"}
    )
    
    end_time = time.time()
    response_time = end_time - start_time
    
    print(f"⏱️ 响应时间: {response_time:.2f}秒")
    
    if response_time > 5:
        print("✅ 响应时间大于5秒，表明真实AI调用")
    else:
        print("⚠️ 响应时间过快，可能仍在使用模板")
    
    result = response.json()
    
    # 检查关键指标
    print(f"📊 成功: {result.get('success')}")
    print(f"🤖 AI生成: {result.get('data', {}).get('ai_generated')}")
    print(f"📝 用户思维使用: {result.get('data', {}).get('user_thinking_used')}")
    print(f"🔧 数据源: {result.get('data', {}).get('source')}")
    
    # 检查是否包含用户输入的关键内容
    tcm_theory = result.get('data', {}).get('paths', [{}])[0].get('tcm_theory', '')
    
    key_terms = ['右归丸', '熟地黄', '肉桂', '附子', '肾阳虚', '温补肾阳']
    found_terms = [term for term in key_terms if term in tcm_theory]
    
    print(f"🔍 找到的关键术语: {found_terms}")
    
    if len(found_terms) >= 3:
        print("✅ AI正确处理了用户的具体处方输入")
        print("✅ 不再是硬编码模板响应")
    else:
        print("❌ AI可能未正确处理用户输入")
    
    # 检查是否是老的硬编码模板
    old_templates = ['黄连解毒汤加减', '理中汤合四君子汤', '逍遥散加减']
    template_found = any(template in tcm_theory for template in old_templates)
    
    if template_found:
        print("❌ 仍在使用旧的硬编码模板")
    else:
        print("✅ 已摆脱硬编码模板限制")
    
    print("\n" + "="*50)
    print("AI验证结果总结:")
    print(f"- 响应时间: {response_time:.2f}秒 ({'✅真实AI' if response_time > 5 else '❌可能模板'})")
    print(f"- 用户输入处理: {'✅正确' if len(found_terms) >= 3 else '❌错误'}")
    print(f"- 模板依赖: {'❌仍有' if template_found else '✅已摆脱'}")
    
    return response_time > 5 and len(found_terms) >= 3 and not template_found

if __name__ == "__main__":
    success = test_ai_real_functionality()
    print(f"\n🎯 最终结果: {'✅ AI功能正常' if success else '❌ 仍有问题'}")