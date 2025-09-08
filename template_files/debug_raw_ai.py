#!/usr/bin/env python3
"""
调试AI原始响应内容
"""

import sys
sys.path.insert(0, '/opt/tcm-ai')

import dashscope
from config.settings import AI_CONFIG
import asyncio
import json

# 设置API密钥
dashscope.api_key = AI_CONFIG.get("dashscope_api_key")

async def debug_raw_ai():
    """直接调用Dashscope查看原始返回"""
    
    prompt = """
作为中医专家，根据以下信息生成完整的诊疗决策树：

疾病名称：腰痛
医生诊疗思路：患者腰痛，辨证为肾阳虚证。方药：右归丸加减。熟地黄20g，肉桂6g，附子10g。温补肾阳。
复杂度要求：simple

返回JSON格式：
{
    "paths": [
        {
            "id": "path1",
            "title": "腰痛-肾阳虚证",
            "steps": [
                {"type": "symptom", "content": "腰痛症状"},
                {"type": "diagnosis", "content": "肾阳虚证"},
                {"type": "formula", "content": "右归丸加减"}
            ],
            "keywords": ["腰痛", "肾阳虚"],
            "tcm_theory": "理论说明"
        }
    ]
}
"""
    
    print("🔍 直接调用Dashscope API...")
    
    try:
        response = await asyncio.to_thread(
            dashscope.Generation.call,
            model="qwen-max",
            prompt=prompt,
            result_format='message'
        )
        
        if response.status_code == 200:
            content = response.output.choices[0]['message']['content']
            
            print("="*60)
            print("AI原始返回内容:")
            print("="*60)
            print(content)
            print("="*60)
            
            # 尝试解析JSON
            print("\n🧪 尝试JSON解析...")
            try:
                result = json.loads(content)
                print("✅ JSON解析成功！")
                print(json.dumps(result, ensure_ascii=False, indent=2))
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                
                # 尝试查找JSON内容
                import re
                json_matches = re.findall(r'```json\s*(.*?)\s*```', content, re.DOTALL | re.IGNORECASE)
                
                if json_matches:
                    print("\n🔧 找到markdown代码块，尝试提取...")
                    json_content = json_matches[0].strip()
                    print("提取的JSON:")
                    print(json_content)
                    
                    try:
                        result = json.loads(json_content)
                        print("✅ markdown JSON解析成功！")
                        print(json.dumps(result, ensure_ascii=False, indent=2))
                    except json.JSONDecodeError as e2:
                        print(f"❌ markdown JSON也解析失败: {e2}")
                else:
                    print("❌ 未找到JSON内容")
        else:
            print(f"❌ AI调用失败: {response.message}")
            
    except Exception as e:
        print(f"❌ 异常: {e}")

if __name__ == "__main__":
    asyncio.run(debug_raw_ai())