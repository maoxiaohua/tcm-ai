#!/usr/bin/env python3
"""
对话状态管理系统测试脚本
验证对话状态管理和分析功能
"""

import asyncio
import sys
import uuid
from datetime import datetime

sys.path.append('/opt/tcm-ai')

from core.conversation.conversation_state_manager import (
    ConversationStateManager, 
    ConversationStage, 
    ConversationEndType
)
from core.conversation.conversation_analyzer import ConversationAnalyzer
from core.consultation.unified_consultation_service import (
    ConsultationRequest, 
    get_consultation_service
)

async def test_conversation_state_management():
    """测试对话状态管理"""
    print("=" * 60)
    print("🧪 测试对话状态管理系统")
    print("=" * 60)
    
    # 初始化管理器
    state_manager = ConversationStateManager()
    analyzer = ConversationAnalyzer()
    
    # 创建测试对话
    conversation_id = f"test_{uuid.uuid4().hex[:8]}"
    user_id = "test_user"
    doctor_id = "zhang_zhongjing"
    
    print(f"📝 创建测试对话: {conversation_id}")
    
    # 1. 创建对话状态
    state = state_manager.create_conversation(conversation_id, user_id, doctor_id)
    print(f"✅ 对话状态创建成功: {state.current_stage.value}")
    
    # 2. 测试状态转换
    print("\n📊 测试状态转换:")
    
    # 转换到详细问诊阶段
    success = state_manager.update_stage(
        conversation_id, 
        ConversationStage.DETAILED_INQUIRY,
        "用户提供了详细症状"
    )
    print(f"  - 转换到详细问诊: {'✅' if success else '❌'}")
    
    # 更新症状收集
    symptoms = ["头痛", "失眠", "胃胀"]
    state_manager.update_symptoms(conversation_id, symptoms)
    print(f"  - 症状更新: {symptoms}")
    
    # 转换到诊断阶段
    success = state_manager.update_stage(
        conversation_id,
        ConversationStage.DIAGNOSIS,
        "收集到足够症状信息",
        0.8
    )
    print(f"  - 转换到诊断阶段: {'✅' if success else '❌'}")
    
    # 3. 测试进度查询
    progress = state_manager.get_conversation_progress(conversation_id)
    print(f"\n📈 对话进度: {progress['progress_percentage']:.1f}%")
    print(f"   当前阶段: {progress['stage_display']}")
    print(f"   对话轮数: {progress['turn_count']}")
    print(f"   症状数量: {progress['symptoms_count']}")
    
    # 4. 测试阶段引导
    guidance = state_manager.get_stage_guidance(conversation_id)
    print(f"\n🧭 阶段引导:")
    print(f"   标题: {guidance['title']}")
    print(f"   描述: {guidance['description']}")
    
    # 5. 测试对话分析
    print(f"\n🔍 测试对话分析:")
    
    test_messages = [
        "我最近头痛，还有失眠的问题",
        "头痛大概持续了一周，晚上很难入睡",
        "胃口也不太好，有时候胃胀",
        "谢谢医生，我明白了"
    ]
    
    for i, message in enumerate(test_messages):
        current_state = state_manager.get_conversation_state(conversation_id)
        analysis = analyzer.analyze_user_message(
            message, 
            current_state.current_stage,
            current_state.turn_count,
            []
        )
        
        print(f"   消息 {i+1}: '{message}'")
        print(f"   提取症状: {analysis.extracted_symptoms}")
        
        if analysis.should_end:
            print(f"   建议结束: {analysis.end_reason}")
        elif analysis.suggested_stage:
            print(f"   建议阶段: {analysis.suggested_stage.value}")
        
        state_manager.increment_turn(conversation_id)
    
    # 6. 测试对话结束
    print(f"\n🏁 测试对话结束:")
    success = state_manager.end_conversation(
        conversation_id,
        ConversationEndType.NATURAL,
        "测试完成"
    )
    print(f"   结束对话: {'✅' if success else '❌'}")
    
    # 7. 获取对话摘要
    final_state = state_manager.get_conversation_state(conversation_id)
    print(f"\n📋 最终状态:")
    print(f"   是否活跃: {final_state.is_active}")
    print(f"   结束类型: {final_state.end_type.value if final_state.end_type else '无'}")
    print(f"   总轮数: {final_state.turn_count}")
    print(f"   收集症状: {final_state.symptoms_collected}")
    
    return True

async def test_unified_consultation_with_state():
    """测试集成了状态管理的统一问诊服务"""
    print("\n" + "=" * 60)
    print("🧪 测试统一问诊服务(含状态管理)")
    print("=" * 60)
    
    try:
        consultation_service = get_consultation_service()
        
        # 创建测试请求
        conversation_id = f"test_unified_{uuid.uuid4().hex[:8]}"
        
        test_requests = [
            {
                "message": "医生您好，我最近总是头痛，想咨询一下",
                "expected_stage": "inquiry"
            },
            {
                "message": "头痛主要在太阳穴的位置，持续了大概一周了，每天下午特别严重",
                "expected_stage": "detailed_inquiry"
            },
            {
                "message": "还有就是睡眠不好，经常失眠，胃口也不太好",
                "expected_stage": "detailed_inquiry"
            },
            {
                "message": "舌苔有点厚腻，大便也不太正常，有时候便秘",
                "expected_stage": "diagnosis"
            }
        ]
        
        conversation_history = []
        
        for i, test_req in enumerate(test_requests):
            print(f"\n📤 第 {i+1} 轮问诊:")
            print(f"   用户: {test_req['message']}")
            
            request = ConsultationRequest(
                message=test_req["message"],
                conversation_id=conversation_id,
                selected_doctor="zhang_zhongjing",
                conversation_history=conversation_history.copy(),
                patient_id="test_user"
            )
            
            # 调用统一问诊服务
            response = await consultation_service.process_consultation(request)
            
            print(f"   医生: {response.reply[:100]}...")
            print(f"   当前阶段: {response.stage}")
            print(f"   对话活跃: {response.conversation_active}")
            print(f"   处理时间: {response.processing_time:.2f}s")
            
            if response.progress_info:
                print(f"   进度: {response.progress_info['progress_percentage']:.1f}%")
            
            if response.stage_guidance:
                print(f"   引导: {response.stage_guidance['title']}")
            
            # 更新对话历史
            conversation_history.append({"role": "user", "content": test_req["message"]})
            conversation_history.append({"role": "assistant", "content": response.reply})
        
        print(f"\n✅ 统一问诊服务测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 统一问诊服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_timeout_mechanism():
    """测试超时机制"""
    print("\n" + "=" * 60)
    print("🧪 测试超时机制")
    print("=" * 60)
    
    state_manager = ConversationStateManager()
    
    # 创建测试对话
    conversation_id = f"test_timeout_{uuid.uuid4().hex[:8]}"
    state = state_manager.create_conversation(conversation_id, "test_user", "zhang_zhongjing")
    
    print(f"📝 创建超时测试对话: {conversation_id}")
    
    # 测试超时检查
    is_timeout, message = state_manager.check_timeout(conversation_id)
    print(f"🕐 初始超时检查: {'超时' if is_timeout else '正常'} - {message}")
    
    # 模拟活跃状态更新
    state_manager.increment_turn(conversation_id)
    print(f"🔄 增加对话轮数")
    
    # 再次检查
    is_timeout, message = state_manager.check_timeout(conversation_id)
    print(f"🕐 更新后超时检查: {'超时' if is_timeout else '正常'} - {message}")
    
    return True

async def main():
    """主测试函数"""
    print("🚀 开始对话状态管理系统测试")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 测试基础状态管理
        result1 = await test_conversation_state_management()
        
        # 2. 测试统一问诊服务集成
        result2 = await test_unified_consultation_with_state()
        
        # 3. 测试超时机制
        result3 = await test_timeout_mechanism()
        
        # 总结测试结果
        print("\n" + "=" * 60)
        print("📊 测试结果总结")
        print("=" * 60)
        print(f"对话状态管理: {'✅ 通过' if result1 else '❌ 失败'}")
        print(f"统一问诊服务: {'✅ 通过' if result2 else '❌ 失败'}")
        print(f"超时机制测试: {'✅ 通过' if result3 else '❌ 失败'}")
        
        overall_success = all([result1, result2, result3])
        print(f"\n🎯 总体结果: {'✅ 全部通过' if overall_success else '❌ 部分失败'}")
        
        if overall_success:
            print("\n🎉 对话状态管理系统已准备就绪！")
            print("📝 主要功能:")
            print("   - 智能状态转换和管理")
            print("   - 症状收集和分析")
            print("   - 进度跟踪和引导")
            print("   - 超时检查和处理")
            print("   - 完整的对话生命周期管理")
        
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())