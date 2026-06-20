#!/usr/bin/env python3
"""
君臣佐使分析防回归测试
确保药材功效不会回到"调理脏腑功能"的错误状态

创建时间: 2025-08-22
目的: 防止君臣佐使分析中药材功效显示错误的bug回归
"""

import sys
import os
sys.path.append('/opt/tcm-ai')

import pytest
from core.prescription.tcm_formula_analyzer import TCMFormulaAnalyzer, analyze_formula_with_ai
from services.multimodal_processor import MultiModalPrescriptionProcessor


class TestHerbFunctionRegression:
    """药材功效防回归测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.analyzer = TCMFormulaAnalyzer()
        self.processor = MultiModalPrescriptionProcessor()
        
    def test_no_generic_fallback_in_analysis(self):
        """测试君臣佐使分析中不应出现通用fallback"""
        # 测试处方
        test_herbs = [
            {'name': '黄芪', 'dosage': 15, 'unit': 'g'},
            {'name': '白术', 'dosage': 12, 'unit': 'g'},
            {'name': '甘草', 'dosage': 6, 'unit': 'g'},
            {'name': '当归', 'dosage': 10, 'unit': 'g'}
        ]
        
        result = analyze_formula_with_ai(test_herbs)
        
        # 检查所有药材的reason不包含"调理脏腑功能"
        for role, herbs in result['roles'].items():
            for herb in herbs:
                assert '调理脏腑功能' not in herb['reason'], \
                    f"药材{herb['name']}的功效描述包含错误的fallback: {herb['reason']}"
    
    def test_known_herbs_have_specific_functions(self):
        """测试已知药材应有具体功效，而非通用描述"""
        known_herbs = ['黄芪', '白术', '甘草', '当归', '人参', '党参', '茯苓', '川芎', '白芍']
        
        for herb_name in known_herbs:
            function = self.analyzer._get_herb_function(herb_name)
            
            # 这些已知药材不应该返回通用描述
            assert function != '调理脏腑功能', \
                f"已知药材{herb_name}返回了通用fallback: {function}"
            assert function != '辅助调理、协同治疗', \
                f"已知药材{herb_name}返回了智能fallback，应该有具体功效: {function}"
            assert len(function) > 4, \
                f"已知药材{herb_name}的功效描述太简短: {function}"
    
    def test_processed_herb_names(self):
        """测试炮制药材名称应正确识别"""
        processed_herbs = [
            '炙甘草', '炒白术', '制附子', '生地黄', '炙黄芪', 
            '蜜枇杷叶', '酒当归', '盐杜仲'
        ]
        
        for herb_name in processed_herbs:
            function = self.analyzer._get_herb_function(herb_name)
            
            # 炮制药材不应返回通用描述
            assert function != '调理脏腑功能', \
                f"炮制药材{herb_name}返回了错误的fallback: {function}"
            assert '、' in function or len(function) > 6, \
                f"炮制药材{herb_name}的功效描述不够详细: {function}"
    
    def test_multimodal_processor_enhancement(self):
        """测试多模态处理器的药材功效增强功能"""
        test_herbs = [
            {'name': '炙黄芪', 'dosage': 15, 'unit': 'g'},
            {'name': '炒白术', 'dosage': 12, 'unit': 'g'},
            {'name': '制附子', 'dosage': 9, 'unit': 'g'}
        ]
        
        enhanced_herbs = self.processor._enhance_herb_info(test_herbs)
        
        for herb in enhanced_herbs:
            function = herb.get('function', '')
            
            # 增强后的药材不应有通用描述
            assert function != '调理脏腑功能', \
                f"增强功能返回了错误的fallback for {herb['name']}: {function}"
            assert len(function) > 4, \
                f"增强功能返回的描述太简短 for {herb['name']}: {function}"
    
    def test_unknown_herbs_intelligent_fallback(self):
        """测试未知药材应使用智能fallback而非通用描述"""
        # 使用不包含特殊字符的药材名测试最终fallback
        pure_unknown_herbs = ['测试药材', '虚构物质', 'ABC', 'XYZ123']
        
        for herb_name in pure_unknown_herbs:
            function = self.analyzer._get_herb_function(herb_name)
            
            # 未知药材不应返回"调理脏腑功能"
            assert function != '调理脏腑功能', \
                f"未知药材{herb_name}返回了错误的通用fallback: {function}"
            
            # 这些药材应该返回最终的智能fallback或基于字符的智能推断
            assert function in ['辅助调理、协同治疗'], \
                f"未知药材{herb_name}应返回智能fallback，实际: {function}"
                
        # 测试包含特殊字符的药材会触发智能推断
        pattern_herbs = ['虚构草药', '假想参', '测试芪']
        expected_patterns = ['清热解毒、调和诸药', '补气健脾、扶正固本', '补气升阳、固表止汗']
        
        for herb_name, expected in zip(pattern_herbs, expected_patterns):
            function = self.analyzer._get_herb_function(herb_name)
            assert function == expected, \
                f"含特殊字符的药材{herb_name}智能推断错误，期望: {expected}，实际: {function}"
    
    def test_herb_name_patterns_fallback(self):
        """测试基于名称模式的智能fallback"""
        pattern_tests = [
            ('测试参', '补气健脾、扶正固本'),
            ('虚构芪', '补气升阳、固表止汗'),
            ('假归', '补血活血、调经止痛'),
            ('试验草', '清热解毒、调和诸药'),
            ('白某术', '健脾燥湿、补气利水'),
            ('红苓', '利水渗湿、健脾宁心')
        ]
        
        for herb_name, expected_pattern in pattern_tests:
            function = self.analyzer._get_herb_function(herb_name)
            assert function == expected_pattern, \
                f"药材{herb_name}的智能fallback错误，期望: {expected_pattern}，实际: {function}"
    
    def test_formula_analysis_no_generic_fallback(self):
        """测试方剂分析中所有环节都不使用通用fallback"""
        # 包含已知和未知药材的混合处方
        mixed_herbs = [
            {'name': '黄芪', 'dosage': 15, 'unit': 'g'},     # 已知
            {'name': '炙甘草', 'dosage': 6, 'unit': 'g'},    # 炮制名
            {'name': '虚构参', 'dosage': 12, 'unit': 'g'},   # 未知但有模式匹配
            {'name': 'XYZ', 'dosage': 8, 'unit': 'g'}       # 完全未知
        ]
        
        result = analyze_formula_with_ai(mixed_herbs)
        
        # 验证所有药材都有合理的功效描述
        all_herbs_analyzed = []
        for role, herbs in result['roles'].items():
            all_herbs_analyzed.extend(herbs)
        
        assert len(all_herbs_analyzed) == len(mixed_herbs), \
            "分析结果中的药材数量不匹配"
        
        for herb in all_herbs_analyzed:
            reason = herb['reason']
            assert '调理脏腑功能' not in reason, \
                f"君臣佐使分析中{herb['name']}包含错误fallback: {reason}"
            assert len(reason) > 10, \
                f"君臣佐使分析中{herb['name']}的描述太简短: {reason}"

    def test_pc_text_api_regression(self):
        """测试PC端文本处方API的防回归"""
        import requests
        import json
        
        # 测试PC端文本处方检查API
        url = 'http://localhost:8000/api/prescription/check'
        data = {
            'prescription_text': '''炙黄芪 15g
炒白术 12g
茯苓 10g
炙甘草 6g'''
        }
        
        try:
            response = requests.post(url, data=data, timeout=30)
            assert response.status_code == 200, f"API调用失败: {response.status_code}"
            
            result = response.json()
            assert result.get('success') == True, "API返回失败状态"
            assert 'data' in result, "响应中缺少data字段"
            assert 'formula_analysis' in result['data'], "响应中缺少formula_analysis字段"
            
            formula_analysis = result['data']['formula_analysis']
            assert 'roles' in formula_analysis, "formula_analysis中缺少roles字段"
            
            # 检查所有药材的reason不包含"调理脏腑功能"
            for role, herbs in formula_analysis['roles'].items():
                for herb in herbs:
                    reason = herb.get('reason', '')
                    assert '调理脏腑功能' not in reason, \
                        f"PC端文本API中{herb.get('name')}仍显示调理脏腑功能: {reason}"
                    
        except requests.exceptions.RequestException:
            # 如果服务未启动，跳过此测试
            import pytest
            pytest.skip("服务未启动，跳过PC端API测试")


def test_regression_prevention():
    """主要的防回归测试函数"""
    test_instance = TestHerbFunctionRegression()
    test_instance.setup_method()
    
    # 运行关键测试
    test_instance.test_no_generic_fallback_in_analysis()
    test_instance.test_known_herbs_have_specific_functions()
    test_instance.test_processed_herb_names()
    test_instance.test_multimodal_processor_enhancement()
    test_instance.test_unknown_herbs_intelligent_fallback()
    test_instance.test_herb_name_patterns_fallback()
    test_instance.test_formula_analysis_no_generic_fallback()
    
    print("✅ 所有防回归测试通过！")
    return True


if __name__ == "__main__":
    print("🧪 开始运行君臣佐使分析防回归测试...")
    try:
        test_regression_prevention()
        print("🎉 防回归测试完成，未发现问题！")
    except AssertionError as e:
        print(f"❌ 发现回归问题: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"💥 测试过程中出现异常: {e}")
        sys.exit(1)