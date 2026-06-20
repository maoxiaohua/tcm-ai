#!/usr/bin/env python3
"""
调试AI响应 - 查看原始返回内容
"""

import requests
import json
import time

def debug_ai_raw_response():
    """直接调用AI API查看原始响应"""
    
    # 模拟系统内部的AI调用
    import sys
    sys.path.insert(0, '/opt/tcm-ai')
    
    from services.famous_doctor_learning_system import FamousDoctorLearningSystem
    import asyncio
    
    async def test_ai():
        system = FamousDoctorLearningSystem()
        
        try:
            result = await system._generate_ai_decision_paths(
                disease_name="腰痛",
                thinking_process="患者腰痛，辨证为肾阳虚证。方药：右归丸加减。熟地黄20g，山药15g，肉桂6g，附子10g。",
                complexity_level="intermediate"
            )
            print("=== AI直接调用成功 ===")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        except Exception as e:
            print(f"❌ AI直接调用失败: {e}")
            
            # 查看是否是JSON解析问题
            print("\n=== 尝试查看原始响应 ===")
            
    # 运行测试
    asyncio.run(test_ai())

if __name__ == "__main__":
    debug_ai_raw_response()