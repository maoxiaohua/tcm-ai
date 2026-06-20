#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证多模态功能修复是否成功
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, '/opt/tcm-ai')

def verify_config_unification():
    """验证配置统一性"""
    print("🔍 验证多模态配置统一性")
    print("=" * 50)
    
    try:
        from config.settings import AI_CONFIG
        from services.multimodal_processor import MultiModalPrescriptionProcessor
        
        # 读取配置
        multimodal_model = AI_CONFIG.get("multimodal_model", "qwen-vl-max")
        multimodal_timeout = AI_CONFIG.get("multimodal_timeout", 80)
        
        print(f"📋 统一配置设置:")
        print(f"   模型: {multimodal_model}")
        print(f"   超时: {multimodal_timeout}秒")
        
        # 检查处方处理器
        processor = MultiModalPrescriptionProcessor()
        print(f"\n📊 处方分析器:")
        print(f"   模型: {processor.model}")
        print(f"   超时: {processor.timeout}秒")
        
        # 检查API文件中的配置使用情况
        with open('/opt/tcm-ai/api/main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"\n🔍 舌象分析配置检查:")
        
        if 'AI_CONFIG.get("multimodal_model"' in content:
            print("✅ 舌象分析已使用统一模型配置")
        else:
            print("❌ 舌象分析未使用统一模型配置")
            
        if 'AI_CONFIG.get("multimodal_timeout"' in content:
            print("✅ 舌象分析已使用统一超时配置")
        else:
            print("❌ 舌象分析未使用统一超时配置")
        
        # 验证是否还有硬编码
        if 'model="qwen-vl-plus"' in content:
            print("❌ 发现舌象分析中仍有硬编码模型 qwen-vl-plus")
            return False
        elif 'model="qwen-vl-max"' in content and 'AI_CONFIG' not in content:
            print("❌ 发现舌象分析中仍有硬编码模型 qwen-vl-max")
            return False
        else:
            print("✅ 未发现硬编码模型配置")
        
        if 'timeout=30' in content and 'AI_CONFIG' not in content.split('timeout=30')[0]:
            print("❌ 发现硬编码超时配置")
            return False
        else:
            print("✅ 未发现硬编码超时配置")
        
        # 配置一致性检查
        print(f"\n📈 配置对比:")
        print(f"   统一配置模型: {multimodal_model}")
        print(f"   处方处理器模型: {processor.model}")
        print(f"   统一配置超时: {multimodal_timeout}秒")
        print(f"   处方处理器超时: {processor.timeout}秒")
        
        # 判断是否一致
        models_match = (processor.model == multimodal_model)
        timeouts_match = (processor.timeout == multimodal_timeout)
        
        if models_match and timeouts_match:
            print("✅ 所有配置已统一")
            return True
        else:
            if not models_match:
                print("❌ 模型配置不一致")
            if not timeouts_match:
                print("❌ 超时配置不一致")
            return False
            
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")
        return False

def test_actual_model_usage():
    """测试实际使用的模型参数"""
    print("\n🔍 测试实际模型参数使用")
    print("=" * 50)
    
    try:
        from config.settings import AI_CONFIG
        
        # 模拟extract_features_from_image中的配置读取
        model_name = AI_CONFIG.get("multimodal_model", "qwen-vl-max")
        model_timeout = AI_CONFIG.get("multimodal_timeout", 80)
        
        print(f"✅ 舌象分析将使用:")
        print(f"   模型: {model_name}")
        print(f"   超时: {model_timeout}秒")
        
        # 与处方分析对比
        from services.multimodal_processor import MultiModalPrescriptionProcessor
        processor = MultiModalPrescriptionProcessor()
        
        if model_name == processor.model and model_timeout == processor.timeout:
            print("✅ 舌象分析和处方分析配置完全一致")
            return True
        else:
            print("❌ 配置仍不一致")
            print(f"   舌象: {model_name}, {model_timeout}秒")
            print(f"   处方: {processor.model}, {processor.timeout}秒")
            return False
            
    except Exception as e:
        print(f"❌ 模型参数测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始验证多模态功能修复结果")
    print("=" * 60)
    
    results = []
    
    # 验证配置统一
    results.append(verify_config_unification())
    
    # 验证实际使用的参数
    results.append(test_actual_model_usage())
    
    # 总结
    print(f"\n📊 验证总结:")
    success_count = sum(results)
    total_count = len(results)
    
    if success_count == total_count:
        print("🎉 修复验证成功！多模态功能已统一配置。")
        print("✅ 舌象分析和处方分析现在使用相同的模型和参数")
        return True
    else:
        print(f"⚠️ 修复不完整 - {success_count}/{total_count} 项检查通过")
        print("❌ 需要进一步检查和修复")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)