#!/usr/bin/env python3
"""
调试验证过程
"""

import sys
sys.path.insert(0, '/opt/tcm-ai')

from services.famous_doctor_learning_system import FamousDoctorLearningSystem
import asyncio
import json

async def debug_validation():
    """调试验证过程"""
    
    system = FamousDoctorLearningSystem()
    
    print("🔍 调试AI路径验证过程...")
    
    try:
        # 直接调用AI生成方法
        paths = await system._generate_ai_decision_paths(
            disease_name="腰痛",
            thinking_process="患者腰痛，肾阳虚证。右归丸加减：熟地黄20g，肉桂6g，附子10g。",
            complexity_level="simple"
        )
        
        print(f"✅ AI生成了 {len(paths)} 条路径")
        
        for i, path in enumerate(paths):
            print(f"\n路径 {i+1}:")
            print(f"  ID: {path.get('id', 'MISSING')}")
            print(f"  标题: {path.get('title', 'MISSING')}")
            print(f"  步骤数: {len(path.get('steps', []))}")
            print(f"  关键词: {path.get('keywords', 'MISSING')}")
            
            # 检查验证状态
            is_valid = system._validate_ai_path(path, "腰痛")
            print(f"  验证通过: {is_valid}")
            
            # 显示完整内容
            print("  完整内容:")
            print(json.dumps(path, ensure_ascii=False, indent=4))
            
            # 检查关键信息
            path_str = json.dumps(path, ensure_ascii=False)
            keywords_found = []
            test_keywords = ['右归丸', '熟地黄', '肉桂', '附子', '肾阳虚', '温补肾阳']
            
            for keyword in test_keywords:
                if keyword in path_str:
                    keywords_found.append(keyword)
            
            print(f"  找到的关键词: {keywords_found}")
            
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_validation())