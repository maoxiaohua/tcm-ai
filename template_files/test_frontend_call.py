#!/usr/bin/env python3
"""
测试前端实际发送的请求
"""

import requests
import json

def test_frontend_request():
    """模拟前端发送的确切请求"""
    
    # 这是前端实际发送的请求格式
    frontend_request = {
        "disease_name": "腰痛",
        "thinking_process": "患者腰痛，辨证为肾阳虚证。肾阳虚则温煦无力，腰府失养而痛。治法：温补肾阳，强腰止痛。方药：右归丸加减。熟地黄20g补肾填精，山药15g健脾补肾，山茱萸12g补肝肾，枸杞子15g滋补肝肾，鹿角胶10g（烊化）温补肾阳，菟丝子15g补肾固精，杜仲15g补肾强腰，当归12g补血活血，肉桂6g温肾助阳，附子10g（先煎）回阳救逆。",
        "use_ai": True,  # 前端参数名
        "include_tcm_analysis": True,
        "complexity_level": "standard"
    }
    
    print("🔍 测试前端实际请求格式...")
    print(f"疾病: {frontend_request['disease_name']}")
    print(f"AI模式: {frontend_request['use_ai']}")
    print(f"思维过程长度: {len(frontend_request['thinking_process'])}字符")
    
    response = requests.post(
        "http://localhost:8000/api/generate_visual_decision_tree",
        json=frontend_request,
        headers={"Content-Type": "application/json"}
    )
    
    result = response.json()
    
    print(f"\n📥 前端请求响应:")
    print(f"成功: {result.get('success')}")
    print(f"消息: {result.get('message')}")
    
    data = result.get('data', {})
    print(f"数据源: {data.get('source')}")
    print(f"AI生成: {data.get('ai_generated')}")
    print(f"用户思维使用: {data.get('user_thinking_used')}")
    
    paths = data.get('paths', [])
    if paths:
        first_path = paths[0]
        print(f"\n第一条路径:")
        print(f"ID: {first_path.get('id')}")
        print(f"标题: {first_path.get('title')}")
        
        steps = first_path.get('steps', [])
        print(f"步骤数: {len(steps)}")
        for i, step in enumerate(steps):
            print(f"  步骤{i+1}: {step.get('content', 'N/A')}")
        
        # 检查关键信息
        path_str = json.dumps(first_path, ensure_ascii=False)
        keywords = ['右归丸', '熟地黄', '肉桂', '附子', '肾阳虚', '温补肾阳']
        found = [k for k in keywords if k in path_str]
        print(f"\n找到的关键词: {found}")
        
        if len(found) >= 4:
            print("✅ 前端请求成功！AI正确处理了用户输入！")
            return True
        else:
            print("❌ 前端请求返回了通用模板内容")
            return False
    else:
        print("❌ 没有路径数据")
        return False

if __name__ == "__main__":
    success = test_frontend_request()
    if not success:
        print("\n🔧 前端和后端之间存在连接问题，需要进一步调试")
    else:
        print("\n🎉 前端请求工作正常！问题可能在浏览器端的JavaScript执行")