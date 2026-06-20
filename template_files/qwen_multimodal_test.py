#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QWEN多模态大模型集成验证测试
检查舌象分析功能是否正常工作
"""

import sys
import os
import json
import asyncio
import tempfile
import logging
from typing import Dict, Any

# 添加项目路径
sys.path.insert(0, '/opt/tcm-ai')

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QWENMultimodalTester:
    """QWEN多模态功能测试器"""
    
    def __init__(self):
        self.test_results = {
            'api_config': {},
            'multimodal_processor': {},
            'tongue_analysis': {},
            'prescription_analysis': {},
            'integration_status': {},
            'errors': []
        }
    
    def test_api_configuration(self):
        """测试API配置"""
        print("🔍 测试1: API配置检查")
        print("=" * 60)
        
        try:
            from config.settings import AI_CONFIG
            
            # 检查API密钥配置
            api_key = AI_CONFIG.get('dashscope_api_key', '')
            if api_key:
                # 隐藏大部分API密钥，只显示前后几位
                masked_key = f"{api_key[:8]}...{api_key[-8:]}" if len(api_key) > 16 else "****"
                self.test_results['api_config']['dashscope_key'] = {
                    'status': 'SUCCESS',
                    'masked_key': masked_key,
                    'length': len(api_key)
                }
                print(f"✅ DashScope API密钥: 已配置 ({masked_key})")
            else:
                self.test_results['api_config']['dashscope_key'] = {
                    'status': 'FAILED',
                    'error': 'API密钥未配置'
                }
                print("❌ DashScope API密钥: 未配置")
                self.test_results['errors'].append("DashScope API密钥未配置")
            
            # 检查超时配置
            timeout = AI_CONFIG.get('model_timeout', 0)
            self.test_results['api_config']['timeout'] = {
                'status': 'SUCCESS' if timeout > 0 else 'WARNING',
                'value': timeout
            }
            print(f"✅ 模型超时设置: {timeout}秒")
            
        except Exception as e:
            self.test_results['api_config']['import_error'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"❌ API配置导入失败: {e}")
            self.test_results['errors'].append(f"API配置导入失败: {e}")
    
    def test_dashscope_import(self):
        """测试DashScope库导入"""
        print("\n🔍 测试2: DashScope库导入")
        print("=" * 60)
        
        try:
            import dashscope
            from dashscope import MultiModalConversation
            
            self.test_results['multimodal_processor']['dashscope_import'] = {
                'status': 'SUCCESS',
                'version': getattr(dashscope, '__version__', 'unknown')
            }
            print("✅ DashScope库导入成功")
            
            # 检查MultiModalConversation API
            if hasattr(MultiModalConversation, 'call'):
                print("✅ MultiModalConversation.call方法可用")
                self.test_results['multimodal_processor']['api_method'] = {
                    'status': 'SUCCESS'
                }
            else:
                print("❌ MultiModalConversation.call方法不可用")
                self.test_results['multimodal_processor']['api_method'] = {
                    'status': 'FAILED'
                }
                
        except ImportError as e:
            self.test_results['multimodal_processor']['dashscope_import'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"❌ DashScope库导入失败: {e}")
            self.test_results['errors'].append(f"DashScope库导入失败: {e}")
    
    def test_tongue_analysis_function(self):
        """测试舌象分析函数"""
        print("\n🔍 测试3: 舌象分析函数")
        print("=" * 60)
        
        try:
            from api.main import extract_features_from_image
            
            self.test_results['tongue_analysis']['function_import'] = {
                'status': 'SUCCESS'
            }
            print("✅ extract_features_from_image函数导入成功")
            
            # 测试函数调用（使用虚拟数据）
            try:
                # 创建一个最小的JPEG头部来测试函数
                fake_image_bytes = b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'\x00' * 100
                result = extract_features_from_image(fake_image_bytes, "测试图像")
                
                self.test_results['tongue_analysis']['function_call'] = {
                    'status': 'SUCCESS',
                    'result_length': len(result) if result else 0,
                    'contains_error': '失败' in result or '错误' in result
                }
                print(f"✅ 函数调用成功 - 返回长度: {len(result)}字符")
                if '失败' in result or '错误' in result:
                    print(f"⚠️ 返回内容包含错误信息: {result[:100]}...")
                
            except Exception as func_error:
                self.test_results['tongue_analysis']['function_call'] = {
                    'status': 'FAILED',
                    'error': str(func_error)
                }
                print(f"❌ 函数调用失败: {func_error}")
                
        except ImportError as e:
            self.test_results['tongue_analysis']['function_import'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"❌ 舌象分析函数导入失败: {e}")
            self.test_results['errors'].append(f"舌象分析函数导入失败: {e}")
    
    def test_prescription_processor(self):
        """测试处方处理器"""
        print("\n🔍 测试4: 处方处理器")
        print("=" * 60)
        
        try:
            from services.multimodal_processor import MultiModalPrescriptionProcessor
            
            processor = MultiModalPrescriptionProcessor()
            
            self.test_results['prescription_analysis']['processor_init'] = {
                'status': 'SUCCESS',
                'model': processor.model,
                'timeout': processor.timeout
            }
            print(f"✅ 处方处理器初始化成功")
            print(f"   模型: {processor.model}")
            print(f"   超时: {processor.timeout}秒")
            
        except Exception as e:
            self.test_results['prescription_analysis']['processor_init'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"❌ 处方处理器初始化失败: {e}")
            self.test_results['errors'].append(f"处方处理器初始化失败: {e}")
    
    def test_api_connectivity(self):
        """测试API连接性（如果配置了密钥）"""
        print("\n🔍 测试5: API连接性测试")
        print("=" * 60)
        
        try:
            from config.settings import AI_CONFIG
            api_key = AI_CONFIG.get('dashscope_api_key', '')
            
            if not api_key:
                print("⚠️ 跳过API连接测试 - 未配置API密钥")
                self.test_results['integration_status']['api_connectivity'] = {
                    'status': 'SKIPPED',
                    'reason': 'No API key configured'
                }
                return
            
            import dashscope
            from dashscope import MultiModalConversation
            
            # 设置API密钥
            dashscope.api_key = api_key
            
            # 创建一个简单的测试图片（1x1像素的JPEG）
            test_image_bytes = bytes([
                0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46,
                0x00, 0x01, 0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00,
                0xFF, 0xDB, 0x00, 0x43, 0x00, 0x08, 0x06, 0x06, 0x07, 0x06,
                0x05, 0x08, 0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C,
                0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12, 0x13, 0x0F,
                0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
                0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28,
                0x37, 0x29, 0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
                0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF,
                0xC0, 0x00, 0x11, 0x08, 0x00, 0x01, 0x00, 0x01, 0x01, 0x01,
                0x11, 0x00, 0x02, 0x11, 0x01, 0x03, 0x11, 0x01, 0xFF, 0xC4,
                0x00, 0x1F, 0x00, 0x00, 0x01, 0x05, 0x01, 0x01, 0x01, 0x01,
                0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A,
                0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
                0x00, 0xD2, 0xFF, 0xD9
            ])
            
            # 保存为临时文件
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                tmp_file.write(test_image_bytes)
                tmp_file_path = tmp_file.name
            
            try:
                # 测试API调用
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"image": f"file://{tmp_file_path}"},
                            {"text": "这是一个API连接测试，请简单描述您看到的内容。"}
                        ]
                    }
                ]
                
                print("🔄 正在测试API连接...")
                response = MultiModalConversation.call(
                    model="qwen-vl-plus",
                    messages=messages,
                    timeout=15
                )
                
                if hasattr(response, 'status_code') and response.status_code == 200:
                    self.test_results['integration_status']['api_connectivity'] = {
                        'status': 'SUCCESS',
                        'model': 'qwen-vl-plus'
                    }
                    print("✅ API连接测试成功")
                else:
                    error_msg = getattr(response, 'message', 'Unknown error')
                    self.test_results['integration_status']['api_connectivity'] = {
                        'status': 'FAILED',
                        'error': f"Status: {getattr(response, 'status_code', 'unknown')}, Message: {error_msg}"
                    }
                    print(f"❌ API连接失败: {error_msg}")
                    self.test_results['errors'].append(f"API连接失败: {error_msg}")
                    
            finally:
                # 清理临时文件
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
                    
        except Exception as e:
            self.test_results['integration_status']['api_connectivity'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"❌ API连接测试失败: {e}")
            self.test_results['errors'].append(f"API连接测试失败: {e}")
    
    def compare_implementations(self):
        """对比处方和舌象分析的实现差异"""
        print("\n🔍 测试6: 实现差异对比")
        print("=" * 60)
        
        try:
            # 检查处方处理器配置
            from services.multimodal_processor import MultiModalPrescriptionProcessor
            prescription_processor = MultiModalPrescriptionProcessor()
            
            # 检查舌象分析配置
            from api.main import extract_features_from_image
            
            print("📊 实现对比:")
            print(f"   处方分析模型: {prescription_processor.model}")
            print(f"   处方分析超时: {prescription_processor.timeout}秒")
            print("   舌象分析模型: qwen-vl-plus (硬编码)")
            print("   舌象分析超时: 30秒 (硬编码)")
            
            # 分析差异
            differences = []
            if prescription_processor.model != "qwen-vl-plus":
                differences.append(f"模型版本不同: 处方({prescription_processor.model}) vs 舌象(qwen-vl-plus)")
            
            if prescription_processor.timeout != 30:
                differences.append(f"超时设置不同: 处方({prescription_processor.timeout}s) vs 舌象(30s)")
            
            self.test_results['integration_status']['implementation_comparison'] = {
                'status': 'SUCCESS',
                'differences': differences,
                'prescription_model': prescription_processor.model,
                'tongue_model': 'qwen-vl-plus',
                'prescription_timeout': prescription_processor.timeout,
                'tongue_timeout': 30
            }
            
            if differences:
                print("⚠️ 发现实现差异:")
                for diff in differences:
                    print(f"   • {diff}")
            else:
                print("✅ 实现配置一致")
                
        except Exception as e:
            self.test_results['integration_status']['implementation_comparison'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"❌ 实现对比失败: {e}")
    
    def generate_report(self):
        """生成测试报告"""
        print("\n🔍 测试完成 - 生成报告")
        print("=" * 60)
        
        # 统计结果
        total_tests = 0
        successful_tests = 0
        failed_tests = 0
        warning_tests = 0
        
        for category, tests in self.test_results.items():
            if category != 'errors' and isinstance(tests, dict):
                for test_name, test_result in tests.items():
                    if isinstance(test_result, dict) and 'status' in test_result:
                        total_tests += 1
                        if test_result['status'] == 'SUCCESS':
                            successful_tests += 1
                        elif test_result['status'] == 'FAILED':
                            failed_tests += 1
                        else:
                            warning_tests += 1
        
        # 生成详细报告
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'failed_tests': failed_tests,
                'warning_tests': warning_tests,
                'success_rate': round((successful_tests / total_tests) * 100, 2) if total_tests > 0 else 0
            },
            'critical_issues': self.test_results['errors'],
            'detailed_results': self.test_results,
            'diagnosis_and_recommendations': self.generate_diagnosis()
        }
        
        # 保存报告
        report_file = '/opt/tcm-ai/template_files/qwen_multimodal_test_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 打印摘要
        print(f"\n📊 测试摘要:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功: {successful_tests} (✅)")
        print(f"   失败: {failed_tests} (❌)")
        print(f"   警告: {warning_tests} (⚠️)")
        print(f"   成功率: {report['test_summary']['success_rate']}%")
        
        if self.test_results['errors']:
            print(f"\n🚨 关键问题 ({len(self.test_results['errors'])}个):")
            for error in self.test_results['errors']:
                print(f"   • {error}")
        
        print(f"\n📄 详细报告已保存至: {report_file}")
        return report
    
    def generate_diagnosis(self):
        """生成诊断和建议"""
        diagnosis = {
            'overall_status': 'unknown',
            'primary_issues': [],
            'recommendations': []
        }
        
        # 分析主要问题
        if not self.test_results.get('api_config', {}).get('dashscope_key', {}).get('status') == 'SUCCESS':
            diagnosis['primary_issues'].append('API密钥配置问题')
            diagnosis['recommendations'].append('配置正确的DashScope API密钥')
        
        if not self.test_results.get('multimodal_processor', {}).get('dashscope_import', {}).get('status') == 'SUCCESS':
            diagnosis['primary_issues'].append('DashScope库导入问题')
            diagnosis['recommendations'].append('检查DashScope库安装：pip install dashscope')
        
        api_connectivity = self.test_results.get('integration_status', {}).get('api_connectivity', {})
        if api_connectivity.get('status') == 'FAILED':
            diagnosis['primary_issues'].append('API连接失败')
            diagnosis['recommendations'].append('检查网络连接和API密钥有效性')
        
        # 特定问题诊断
        differences = self.test_results.get('integration_status', {}).get('implementation_comparison', {}).get('differences', [])
        if differences:
            diagnosis['primary_issues'].append('处方和舌象分析实现不一致')
            diagnosis['recommendations'].append('统一多模态模型配置，使用相同的模型版本和参数')
        
        # 确定总体状态
        if len(diagnosis['primary_issues']) == 0:
            diagnosis['overall_status'] = 'healthy'
        elif len(diagnosis['primary_issues']) <= 2:
            diagnosis['overall_status'] = 'needs_attention'
        else:
            diagnosis['overall_status'] = 'critical'
        
        return diagnosis
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始QWEN多模态大模型集成验证测试")
        print("📋 测试目标: 验证舌象分析和处方分析的多模态功能")
        print("=" * 80)
        
        try:
            self.test_api_configuration()
            self.test_dashscope_import()
            self.test_tongue_analysis_function()
            self.test_prescription_processor()
            self.test_api_connectivity()
            self.compare_implementations()
            
            return self.generate_report()
            
        except Exception as e:
            logger.error(f"测试执行过程中发生严重错误: {e}")
            self.test_results['errors'].append(f"测试执行严重错误: {e}")
            return self.generate_report()

def main():
    """主函数"""
    tester = QWENMultimodalTester()
    report = tester.run_all_tests()
    
    # 根据测试结果返回适当的退出码
    if report['test_summary']['failed_tests'] == 0 and len(report['critical_issues']) == 0:
        print("\n🎉 所有测试通过！QWEN多模态功能正常。")
        return 0
    elif report['test_summary']['failed_tests'] > 0:
        print(f"\n⚠️ 存在 {report['test_summary']['failed_tests']} 个失败测试，需要修复。")
        return 1
    else:
        print(f"\n🚨 存在 {len(report['critical_issues'])} 个关键问题，需要立即处理。")
        return 2

if __name__ == "__main__":
    sys.exit(main())