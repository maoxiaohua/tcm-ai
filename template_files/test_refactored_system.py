#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构后系统功能测试
验证模块化重构是否成功，所有功能是否正常
"""

import sys
import os
import asyncio
import json
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, '/opt/tcm-ai')
sys.path.insert(0, '/opt/tcm-ai/api')

def test_module_imports():
    """测试模块导入"""
    print("=" * 60)
    print("1. 测试模块导入")
    print("-" * 40)
    
    try:
        # 测试工具模块导入
        from api.utils.common_utils import (
            safe_execute, generate_conversation_id, 
            create_success_response, create_error_response
        )
        print("✓ 通用工具模块导入成功")
        
        from api.utils.text_utils import (
            clean_medical_text, has_medical_keywords,
            extract_keywords_from_query, validate_prescription_format
        )
        print("✓ 文本处理模块导入成功")
        
        # 测试处理器模块导入
        from api.processors.user_history_processor import UserHistoryProcessor
        print("✓ 用户历史处理器导入成功")
        
        from api.processors.image_analysis_processor import ImageAnalysisProcessor
        print("✓ 图像分析处理器导入成功")
        
        from api.processors.knowledge_retrieval_processor import KnowledgeRetrievalProcessor
        print("✓ 知识检索处理器导入成功")
        
        from api.processors.llm_integration_processor import LLMIntegrationProcessor
        print("✓ LLM集成处理器导入成功")
        
        from api.processors.medical_safety_processor import MedicalSafetyProcessor
        print("✓ 医疗安全处理器导入成功")
        
        from api.processors.chat_endpoint_processor import ChatEndpointProcessor
        print("✓ 聊天端点处理器导入成功")
        
        # 测试服务包装器导入
        from api.services.llm_service_wrapper import LLMServiceWrapper, MultimodalServiceWrapper
        print("✓ 服务包装器导入成功")
        
        return True, "所有模块导入成功"
        
    except Exception as e:
        return False, f"模块导入失败: {e}"

def test_utility_functions():
    """测试工具函数"""
    print("=" * 60)
    print("2. 测试工具函数")
    print("-" * 40)
    
    try:
        from api.utils.common_utils import (
            safe_execute, generate_conversation_id,
            get_current_timestamp_iso, clean_text
        )
        from api.utils.text_utils import (
            clean_medical_text, extract_keywords_from_query,
            normalize_prescription_dosage, validate_prescription_format
        )
        
        # 测试ID生成
        conv_id = generate_conversation_id()
        assert len(conv_id) > 10, "对话ID生成失败"
        print(f"✓ 对话ID生成: {conv_id[:8]}...")
        
        # 测试时间戳生成
        timestamp = get_current_timestamp_iso()
        assert datetime.fromisoformat(timestamp.replace('Z', '+00:00')), "时间戳格式错误"
        print(f"✓ 时间戳生成: {timestamp}")
        
        # 测试文本处理
        test_text = "患者有头痛、咳嗽症状，需要中医诊疗"
        cleaned_text = clean_medical_text(test_text)
        assert len(cleaned_text) > 0, "文本清理失败"
        print(f"✓ 文本清理: {cleaned_text[:20]}...")
        
        # 测试关键词提取
        keywords = extract_keywords_from_query(test_text)
        assert len(keywords) > 0, "关键词提取失败"
        print(f"✓ 关键词提取: {keywords}")
        
        # 测试处方格式验证
        test_prescription = """
        党参 12g
        白术 10g
        茯苓 12g
        甘草 6g
        """
        valid, message = validate_prescription_format(test_prescription)
        assert valid, f"处方验证失败: {message}"
        print(f"✓ 处方格式验证: {message}")
        
        # 测试安全执行
        def test_func():
            return "测试成功"
        
        result = safe_execute(test_func, default_return="默认值")
        assert result == "测试成功", "安全执行函数失败"
        print("✓ 安全执行函数测试通过")
        
        return True, "所有工具函数测试通过"
        
    except Exception as e:
        return False, f"工具函数测试失败: {e}"

def test_service_wrappers():
    """测试服务包装器"""
    print("=" * 60)
    print("3. 测试服务包装器")
    print("-" * 40)
    
    try:
        from api.services.llm_service_wrapper import LLMServiceWrapper, MultimodalServiceWrapper
        
        # 模拟AI配置
        mock_config = {
            'default_model': 'qwen-max',
            'multimodal_model': 'qwen-vl-max',
            'temperature': 0.7,
            'timeout': 60,
            'multimodal_timeout': 80
        }
        
        # 测试LLM服务包装器
        llm_service = LLMServiceWrapper(mock_config)
        llm_response = llm_service.generate_response("测试提示词", temperature=0.8)
        
        assert llm_response['success'], "LLM服务调用失败"
        assert len(llm_response['response']) > 0, "LLM响应为空"
        print("✓ LLM服务包装器测试通过")
        
        # 测试多模态服务包装器
        multimodal_service = MultimodalServiceWrapper(mock_config)
        
        # 创建临时图像文件进行测试
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(b'fake image data')
            temp_path = tmp_file.name
        
        try:
            multimodal_response = multimodal_service.analyze_image(
                temp_path, "分析这张舌象图片"
            )
            
            assert multimodal_response['success'], "多模态服务调用失败"
            assert len(multimodal_response['response']) > 0, "多模态响应为空"
            print("✓ 多模态服务包装器测试通过")
            
        finally:
            os.unlink(temp_path)
        
        return True, "服务包装器测试通过"
        
    except Exception as e:
        return False, f"服务包装器测试失败: {e}"

def test_processors():
    """测试处理器功能"""
    print("=" * 60)
    print("4. 测试处理器功能")
    print("-" * 40)
    
    try:
        # 模拟服务容器
        class MockDBManager:
            def execute_query(self, query, params=None):
                return {'success': True, 'data': []}
        
        class MockConfigManager:
            def get_ai_config(self):
                return {
                    'default_model': 'qwen-max',
                    'temperature': 0.7,
                    'enable_safety_check': True,
                    'enable_response_caching': True
                }
        
        services_container = {
            'db_manager': MockDBManager(),
            'vector_store_service': None,
            'faiss_service': None,
            'multimodal_service': None,
            'llm_service': None,
            'config_manager': MockConfigManager(),
            'cache_service': None
        }
        
        # 测试医疗安全处理器
        from api.processors.medical_safety_processor import MedicalSafetyProcessor
        safety_processor = MedicalSafetyProcessor(
            services_container['db_manager'],
            services_container['config_manager']
        )
        
        test_prescription = """
        党参 12g
        白术 10g
        茯苓 12g
        甘草 6g
        """
        
        safety_result = safety_processor.perform_comprehensive_safety_check(
            test_prescription, user_profile={}
        )
        
        assert 'overall_risk_level' in safety_result, "安全检查结果格式错误"
        assert safety_result['safety_passed'] is not None, "安全检查状态缺失"
        print("✓ 医疗安全处理器测试通过")
        
        # 测试LLM集成处理器（模拟）
        from api.processors.llm_integration_processor import LLMIntegrationProcessor
        from api.services.llm_service_wrapper import LLMServiceWrapper
        
        llm_service = LLMServiceWrapper(services_container['config_manager'].get_ai_config())
        llm_processor = LLMIntegrationProcessor(
            llm_service, 
            services_container['config_manager']
        )
        
        test_context = {
            'user_history': {'recent_history': []},
            'retrieved_knowledge': {'retrieved_items': []},
            'image_analysis': []
        }
        
        llm_result = llm_processor.generate_ai_response(
            "患者头痛，请分析",
            test_context,
            'tcm_diagnosis'
        )
        
        assert llm_result['success'], "LLM集成处理器测试失败"
        assert len(llm_result['response']) > 0, "LLM响应为空"
        print("✓ LLM集成处理器测试通过")
        
        return True, "处理器功能测试通过"
        
    except Exception as e:
        return False, f"处理器功能测试失败: {e}"

def test_chat_endpoint_processor():
    """测试聊天端点处理器"""
    print("=" * 60)
    print("5. 测试聊天端点处理器")
    print("-" * 40)
    
    try:
        from api.processors.chat_endpoint_processor import ChatEndpointProcessor
        from api.services.llm_service_wrapper import LLMServiceWrapper, MultimodalServiceWrapper
        
        # 模拟完整的服务容器
        class MockDBManager:
            def execute_query(self, query, params=None):
                if 'INSERT INTO conversations' in query:
                    return {'success': True}
                return {'success': True, 'data': []}
        
        class MockConfigManager:
            def get_ai_config(self):
                return {
                    'default_model': 'qwen-max',
                    'multimodal_model': 'qwen-vl-max',
                    'temperature': 0.7,
                    'enable_safety_check': True,
                    'enable_response_caching': False,  # 简化测试
                    'timeout': 60,
                    'multimodal_timeout': 80
                }
        
        config_manager = MockConfigManager()
        ai_config = config_manager.get_ai_config()
        
        services_container = {
            'db_manager': MockDBManager(),
            'vector_store_service': None,
            'faiss_service': None,
            'multimodal_service': MultimodalServiceWrapper(ai_config),
            'llm_service': LLMServiceWrapper(ai_config),
            'config_manager': config_manager,
            'cache_service': None
        }
        
        # 创建聊天端点处理器
        chat_processor = ChatEndpointProcessor(services_container)
        
        # 测试简单的聊天请求
        test_user_input = "我有头痛症状，请中医分析"
        test_user_id = "test_user_123"
        
        result = chat_processor.process_chat_request(
            user_input=test_user_input,
            user_id=test_user_id,
            images=None,
            additional_context={'conversation_id': 'test_conv_123'}
        )
        
        assert result['success'], f"聊天处理失败: {result.get('error')}"
        assert 'data' in result, "聊天结果缺少数据"
        assert 'response' in result['data'], "聊天结果缺少响应内容"
        assert len(result['data']['response']) > 0, "聊天响应为空"
        
        print(f"✓ 聊天请求处理成功")
        print(f"  - 响应长度: {len(result['data']['response'])} 字符")
        print(f"  - 处理时间: {result['data'].get('processing_time', 0):.2f} 秒")
        print(f"  - 安全检查: {'通过' if result['data'].get('safety_status', {}).get('safety_passed', True) else '不通过'}")
        
        return True, "聊天端点处理器测试通过"
        
    except Exception as e:
        return False, f"聊天端点处理器测试失败: {e}"

def test_system_integration():
    """测试系统集成"""
    print("=" * 60)
    print("6. 测试系统集成")
    print("-" * 40)
    
    try:
        # 模拟完整的API调用流程（不包括FastAPI部分）
        print("测试完整的处理流程...")
        
        # 导入主要组件
        from api.processors.chat_endpoint_processor import ChatEndpointProcessor
        from api.services.llm_service_wrapper import LLMServiceWrapper, MultimodalServiceWrapper
        from api.utils.common_utils import generate_conversation_id
        
        # 创建服务容器
        class MockServices:
            class DBManager:
                def execute_query(self, query, params=None):
                    if 'SELECT' in query and 'conversations' in query:
                        return {'success': True, 'data': []}
                    elif 'INSERT INTO conversations' in query:
                        return {'success': True}
                    return {'success': True, 'data': []}
            
            class ConfigManager:
                def get_ai_config(self):
                    return {
                        'default_model': 'qwen-max',
                        'multimodal_model': 'qwen-vl-max',
                        'temperature': 0.7,
                        'enable_safety_check': True,
                        'enable_response_caching': False,
                        'timeout': 60,
                        'max_tokens': 2000
                    }
        
        mock_services = MockServices()
        config_manager = mock_services.ConfigManager()
        ai_config = config_manager.get_ai_config()
        
        services_container = {
            'db_manager': mock_services.DBManager(),
            'vector_store_service': None,
            'faiss_service': None,
            'multimodal_service': MultimodalServiceWrapper(ai_config),
            'llm_service': LLMServiceWrapper(ai_config),
            'config_manager': config_manager,
            'cache_service': None
        }
        
        # 创建处理器
        chat_processor = ChatEndpointProcessor(services_container)
        
        # 测试多种场景
        test_scenarios = [
            {
                'name': '症状咨询',
                'input': '我最近总是头痛，还有点咳嗽，请帮我分析一下',
                'user_id': 'test_user_001'
            },
            {
                'name': '处方咨询',
                'input': '我需要一个治疗失眠的中药处方',
                'user_id': 'test_user_002'
            },
            {
                'name': '生活调理',
                'input': '如何通过饮食调理脾胃虚弱？',
                'user_id': 'test_user_003'
            }
        ]
        
        successful_tests = 0
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n测试场景 {i}: {scenario['name']}")
            
            try:
                result = chat_processor.process_chat_request(
                    user_input=scenario['input'],
                    user_id=scenario['user_id'],
                    images=None,
                    additional_context={
                        'conversation_id': generate_conversation_id(),
                        'selected_doctor': 'zhang_zhongjing'
                    }
                )
                
                if result['success']:
                    print(f"  ✓ 处理成功")
                    print(f"    响应长度: {len(result['data']['response'])} 字符")
                    print(f"    处理时间: {result['data'].get('processing_time', 0):.2f} 秒")
                    successful_tests += 1
                else:
                    print(f"  ✗ 处理失败: {result.get('error')}")
                    
            except Exception as e:
                print(f"  ✗ 异常: {e}")
        
        success_rate = successful_tests / len(test_scenarios)
        print(f"\n测试汇总:")
        print(f"  成功场景: {successful_tests}/{len(test_scenarios)}")
        print(f"  成功率: {success_rate:.1%}")
        
        if success_rate >= 0.8:
            return True, f"系统集成测试通过 (成功率: {success_rate:.1%})"
        else:
            return False, f"系统集成测试失败 (成功率: {success_rate:.1%})"
            
    except Exception as e:
        return False, f"系统集成测试失败: {e}"

def generate_test_report(test_results):
    """生成测试报告"""
    print("=" * 60)
    print("测试报告")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results if result['success'])
    failed_tests = total_tests - passed_tests
    
    print(f"总测试数: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {failed_tests}")
    print(f"通过率: {passed_tests/total_tests:.1%}")
    print()
    
    for i, result in enumerate(test_results, 1):
        status = "✓ 通过" if result['success'] else "✗ 失败"
        print(f"{i}. {result['name']}: {status}")
        if not result['success']:
            print(f"   错误: {result['message']}")
    
    print("-" * 60)
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过！重构后的系统功能正常。")
        return True
    else:
        print(f"⚠️  有 {failed_tests} 个测试失败，需要进一步调试。")
        return False

def main():
    """主测试函数"""
    print("开始测试重构后的TCM AI诊断系统")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 定义测试用例
    test_cases = [
        ("模块导入测试", test_module_imports),
        ("工具函数测试", test_utility_functions),
        ("服务包装器测试", test_service_wrappers),
        ("处理器功能测试", test_processors),
        ("聊天端点处理器测试", test_chat_endpoint_processor),
        ("系统集成测试", test_system_integration)
    ]
    
    test_results = []
    
    for test_name, test_func in test_cases:
        print(f"\n执行测试: {test_name}")
        try:
            success, message = test_func()
            test_results.append({
                'name': test_name,
                'success': success,
                'message': message
            })
            
            if success:
                print(f"✓ {test_name}: {message}")
            else:
                print(f"✗ {test_name}: {message}")
                
        except Exception as e:
            test_results.append({
                'name': test_name,
                'success': False,
                'message': f"测试异常: {str(e)}"
            })
            print(f"✗ {test_name}: 测试异常: {e}")
    
    # 生成测试报告
    print("\n")
    overall_success = generate_test_report(test_results)
    
    # 保存测试结果到文件
    report_file = '/opt/tcm-ai/template_files/refactoring_test_report.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_time': datetime.now().isoformat(),
            'overall_success': overall_success,
            'test_results': test_results,
            'summary': {
                'total_tests': len(test_results),
                'passed_tests': sum(1 for r in test_results if r['success']),
                'failed_tests': sum(1 for r in test_results if not r['success']),
                'success_rate': sum(1 for r in test_results if r['success']) / len(test_results)
            }
        }, ensure_ascii=False, indent=2)
    
    print(f"\n测试报告已保存到: {report_file}")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)