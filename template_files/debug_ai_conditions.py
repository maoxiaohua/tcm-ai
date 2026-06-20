#!/usr/bin/env python3
"""
调试AI调用条件
"""

import sys
sys.path.insert(0, '/opt/tcm-ai')

from services.famous_doctor_learning_system import FamousDoctorLearningSystem
import asyncio

async def debug_ai_conditions():
    """调试AI调用条件检查"""
    
    system = FamousDoctorLearningSystem()
    
    print("🔍 AI条件调试")
    print("="*40)
    
    # 参数
    disease_name = "腰痛"
    thinking_process = "患者腰痛，肾阳虚证。右归丸加减：熟地黄20g，肉桂6g，附子10g。温补肾阳。"
    use_ai = True
    
    print(f"输入参数:")
    print(f"  disease_name: '{disease_name}'")
    print(f"  thinking_process: '{thinking_process}'")
    print(f"  use_ai: {use_ai}")
    print(f"  thinking_process长度: {len(thinking_process)}")
    
    print(f"\nAI系统状态:")
    print(f"  system.ai_enabled: {system.ai_enabled}")
    print(f"  type: {type(system.ai_enabled)}")
    
    print(f"\n条件检查:")
    print(f"  use_ai: {use_ai} (类型: {type(use_ai)})")
    print(f"  system.ai_enabled: {system.ai_enabled} (类型: {type(system.ai_enabled)})")
    print(f"  thinking_process.strip(): '{thinking_process.strip()}'")
    print(f"  bool(thinking_process.strip()): {bool(thinking_process.strip())}")
    print(f"  综合条件: {use_ai and system.ai_enabled and thinking_process.strip()}")
    
    # 测试调用generate_decision_paths
    try:
        print(f"\n🚀 调用generate_decision_paths...")
        result = await system.generate_decision_paths(
            disease_name=disease_name,
            thinking_process=thinking_process,
            use_ai=use_ai,
            include_tcm_analysis=True,
            complexity_level="standard"
        )
        
        print(f"✅ 调用成功")
        print(f"  source: {result.get('source')}")
        print(f"  ai_generated: {result.get('ai_generated')}")
        print(f"  paths数量: {len(result.get('paths', []))}")
        
        if result.get('error_message'):
            print(f"  错误信息: {result.get('error_message')}")
            
    except Exception as e:
        print(f"❌ 调用失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_ai_conditions())