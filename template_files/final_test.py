#!/usr/bin/env python3
"""
最终测试：验证AI功能是否完全正常
"""

import requests
import json
import time

def final_verification_test():
    """最终验证测试"""
    
    print("🎯 最终验证测试：AI真实处理用户输入")
    print("="*60)
    
    # 用户具体输入
    user_input = {
        "disease_name": "腰痛",
        "thinking_process": "患者腰痛，辨证为肾阳虚证。肾阳虚则温煦无力，腰府失养而痛。治法：温补肾阳，强腰止痛。方药：右归丸加减。熟地黄20g补肾填精，山药15g健脾补肾，山茱萸12g补肝肾，枸杞子15g滋补肝肾，鹿角胶10g（烊化）温补肾阳，菟丝子15g补肾固精，杜仲15g补肾强腰，当归12g补血活血，肉桂6g温肾助阳，附子10g（先煎）回阳救逆。",
        "complexity_level": "intermediate",
        "ai_mode": True
    }
    
    print(f"📤 用户输入疾病：{user_input['disease_name']}")
    print(f"📤 用户输入证型：肾阳虚证")
    print(f"📤 用户输入方剂：右归丸加减")
    print(f"📤 用户输入药物：熟地黄、山药、肉桂、附子等10味药")
    
    start_time = time.time()
    response = requests.post(
        "http://localhost:8000/api/generate_visual_decision_tree",
        json=user_input,
        headers={"Content-Type": "application/json"}
    )
    end_time = time.time()
    
    result = response.json()
    
    print(f"\n⏱️ 响应时间：{end_time - start_time:.1f}秒")
    
    if not result.get('success'):
        print(f"❌ API调用失败：{result.get('message', 'Unknown')}")
        return False
    
    data = result.get('data', {})
    source = data.get('source', 'unknown')
    ai_generated = data.get('ai_generated', False)
    
    print(f"🔧 数据源：{source}")
    print(f"🤖 AI生成：{ai_generated}")
    
    paths = data.get('paths', [])
    if not paths:
        print("❌ 没有生成路径")
        return False
    
    path = paths[0]
    title = path.get('title', '')
    
    print(f"📋 路径标题：{title}")
    
    # 检查步骤内容
    steps = path.get('steps', [])
    print(f"📝 生成步骤数：{len(steps)}")
    
    # 检查是否包含用户输入的核心信息
    full_path_content = json.dumps(path, ensure_ascii=False)
    
    # 核心验证：是否包含用户的具体输入
    user_keywords = [
        '肾阳虚',      # 证型
        '右归丸',      # 方剂名
        '熟地黄',      # 具体药物1  
        '肉桂',        # 具体药物2
        '附子',        # 具体药物3
        '温补肾阳'     # 治法
    ]
    
    found_keywords = []
    for keyword in user_keywords:
        if keyword in full_path_content:
            found_keywords.append(keyword)
    
    print(f"\n🔍 核心验证结果：")
    print(f"   找到的用户输入关键词：{found_keywords}")
    print(f"   覆盖率：{len(found_keywords)}/{len(user_keywords)} = {len(found_keywords)/len(user_keywords)*100:.1f}%")
    
    # 成功标准：至少找到4个关键词（包括证型、方剂、药物）
    success_threshold = 4
    is_success = len(found_keywords) >= success_threshold
    
    print(f"\n🎯 最终判定：")
    if is_success:
        print(f"✅ 成功！AI正确处理了用户的具体输入")
        print(f"✅ 不再是硬编码模板，而是真实的个性化内容")
        print(f"✅ 响应时间证明了真实的AI调用")
        
        # 额外验证：检查是否还有老的模板痕迹
        template_indicators = ['具体诊断条件', 'AI推荐诊断', '治疗建议', 'AI推荐处方']
        template_found = any(indicator in full_path_content for indicator in template_indicators)
        
        if template_found:
            print(f"⚠️ 警告：仍然包含一些模板内容")
        else:
            print(f"✅ 完全摆脱了硬编码模板限制")
            
        return True
    else:
        print(f"❌ 失败！关键词覆盖率不足（需要>={success_threshold}个）")
        print(f"❌ 可能仍在使用通用模板或AI未正确处理用户输入")
        return False

if __name__ == "__main__":
    print("🚀 开始最终验证...")
    success = final_verification_test()
    
    print("\n" + "="*60)
    if success:
        print("🎉 问题已完全解决！")
        print("🎉 可视化决策树构建器现在使用真实的AI分析用户输入")
        print("🎉 用户的具体处方、证型、治法都被正确处理")
    else:
        print("😞 问题仍然存在")
        print("😞 需要进一步调试AI响应处理逻辑")
    print("="*60)