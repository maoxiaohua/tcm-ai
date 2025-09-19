#!/usr/bin/env python
"""测试决策树生成功能"""

import asyncio
import json
from services.famous_doctor_learning_system import FamousDoctorLearningSystem

async def test_decision_tree_generation():
    """测试AI决策树生成"""
    
    # 初始化学习系统
    learning_system = FamousDoctorLearningSystem()
    
    # 测试用例：胃痛的诊疗思路
    disease_name = "胃痛"
    thinking_process = """
    胃脘疼痛反复发作半年，得温则舒，按之痛减，泛吐清水，纳呆乏力。
    症见：胃脘隐痛，绵绵不休，喜温喜按，空腹痛甚，得食稍缓，泛吐清水，
    神疲乏力，手足不温，大便溏薄，舌淡苔白，脉沉迟无力。
    证属：脾胃虚寒，中阳不足。
    治法：温中健脾，和胃止痛。
    方用：理中汤合良附丸加减。
    药物：党参15g、白术12g、干姜10g、炙甘草6g、高良姜10g、香附12g、陈皮10g、半夏9g。
    """
    
    print(f"测试疾病：{disease_name}")
    print(f"诊疗思路：{thinking_process}")
    print("="*60)
    
    try:
        # 生成决策路径
        result = await learning_system.generate_decision_paths(
            disease_name=disease_name,
            thinking_process=thinking_process,
            complexity_level="detailed"
        )
        
        # 从返回的字典中提取paths
        paths = result.get('paths', [])
        
        print(f"生成的决策路径数量：{len(paths)}")
        print(f"决策路径内容：")
        print(json.dumps(paths, ensure_ascii=False, indent=2))
        
        # 验证生成的内容
        if paths:
            first_path = paths[0]
            print(f"\n第一条路径分析：")
            print(f"- ID: {first_path.get('id')}")
            print(f"- 标题: {first_path.get('title')}")
            print(f"- 步骤数: {len(first_path.get('steps', []))}")
            
            print("\n步骤详情：")
            for step in first_path.get('steps', []):
                print(f"  - 类型: {step.get('type')}, 内容: {step.get('content')}")
        
    except Exception as e:
        print(f"错误：{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_decision_tree_generation())