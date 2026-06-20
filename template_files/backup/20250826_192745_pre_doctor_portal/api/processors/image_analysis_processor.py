#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像分析处理模块
从chat_with_ai_endpoint函数中提取的图像分析相关功能
"""

import logging
import base64
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from ..utils.common_utils import safe_execute, create_temp_file, safe_remove_file
from ..utils.text_utils import clean_ai_response_text, has_medical_keywords

logger = logging.getLogger(__name__)

class ImageAnalysisProcessor:
    """图像分析处理器"""
    
    def __init__(self, multimodal_service, config_manager):
        self.multimodal_service = multimodal_service
        self.config = config_manager.get_ai_config()
        
        # 支持的图像类型
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        self.max_image_size = 10 * 1024 * 1024  # 10MB
        
        # 预设的分析类型
        self.analysis_types = {
            'tongue': {
                'name': '舌象分析',
                'prompt_template': self._get_tongue_analysis_prompt(),
                'required_features': ['舌质', '舌苔', '舌形', '舌色']
            },
            'pulse': {
                'name': '脉象分析', 
                'prompt_template': self._get_pulse_analysis_prompt(),
                'required_features': ['脉位', '脉率', '脉力', '脉形']
            },
            'skin': {
                'name': '皮肤症状分析',
                'prompt_template': self._get_skin_analysis_prompt(),
                'required_features': ['颜色', '形状', '分布', '质地']
            },
            'general': {
                'name': '一般医疗图像分析',
                'prompt_template': self._get_general_analysis_prompt(),
                'required_features': ['外观', '颜色', '形状', '异常表现']
            }
        }
    
    def analyze_medical_image(self, image_data: bytes, image_type: str, 
                             analysis_type: str = 'general', 
                             additional_context: str = '') -> Dict[str, Any]:
        """分析医疗图像"""
        result = {
            'success': False,
            'analysis_type': analysis_type,
            'features_extracted': {},
            'diagnosis_suggestions': [],
            'confidence_score': 0.0,
            'raw_analysis': '',
            'error_message': ''
        }
        
        try:
            # 验证图像数据
            validation_result = self._validate_image_data(image_data, image_type)
            if not validation_result['valid']:
                result['error_message'] = validation_result['error']
                return result
            
            # 创建临时文件
            temp_file_path = create_temp_file(image_data, suffix=f'.{image_type.lower()}')
            if not temp_file_path:
                result['error_message'] = "创建临时文件失败"
                return result
            
            try:
                # 获取分析提示词
                analysis_config = self.analysis_types.get(analysis_type, self.analysis_types['general'])
                prompt = self._build_analysis_prompt(analysis_config, additional_context)
                
                # 调用多模态分析
                analysis_response = self._call_multimodal_analysis(temp_file_path, prompt)
                
                if analysis_response['success']:
                    # 解析分析结果
                    parsed_result = self._parse_analysis_response(
                        analysis_response['response'], 
                        analysis_config
                    )
                    
                    result.update(parsed_result)
                    result['success'] = True
                    
                else:
                    result['error_message'] = analysis_response.get('error', '图像分析失败')
                
            finally:
                # 清理临时文件
                safe_remove_file(temp_file_path)
                
        except Exception as e:
            logger.error(f"医疗图像分析失败: {e}")
            result['error_message'] = f"分析过程出错: {str(e)}"
        
        return result
    
    def _validate_image_data(self, image_data: bytes, image_type: str) -> Dict[str, Any]:
        """验证图像数据"""
        if not image_data:
            return {'valid': False, 'error': '图像数据为空'}
        
        if len(image_data) > self.max_image_size:
            return {'valid': False, 'error': f'图像大小超过限制({self.max_image_size // 1024 // 1024}MB)'}
        
        if f'.{image_type.lower()}' not in self.supported_formats:
            return {'valid': False, 'error': f'不支持的图像格式: {image_type}'}
        
        return {'valid': True, 'error': ''}
    
    def _call_multimodal_analysis(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """调用多模态分析服务"""
        try:
            # 使用配置中的多模态设置
            model = self.config.get('multimodal_model', 'qwen-vl-max')
            timeout = self.config.get('multimodal_timeout', 80)
            
            response = self.multimodal_service.analyze_image(
                image_path=image_path,
                prompt=prompt,
                model=model,
                timeout=timeout
            )
            
            return response
            
        except Exception as e:
            logger.error(f"多模态分析调用失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _build_analysis_prompt(self, analysis_config: Dict[str, Any], 
                              additional_context: str = '') -> str:
        """构建分析提示词"""
        base_prompt = analysis_config['prompt_template']
        
        if additional_context:
            context_addition = f"\n\n补充信息：{additional_context}"
            base_prompt += context_addition
        
        # 添加输出格式要求
        format_requirement = """

请按照以下JSON格式返回分析结果：
{
    "features": {
        "主要特征1": "描述1",
        "主要特征2": "描述2"
    },
    "diagnosis_suggestions": [
        "可能诊断1",
        "可能诊断2"
    ],
    "confidence_score": 0.8,
    "detailed_analysis": "详细分析说明"
}
"""
        
        return base_prompt + format_requirement
    
    def _parse_analysis_response(self, response_text: str, 
                               analysis_config: Dict[str, Any]) -> Dict[str, Any]:
        """解析分析响应"""
        result = {
            'features_extracted': {},
            'diagnosis_suggestions': [],
            'confidence_score': 0.0,
            'raw_analysis': clean_ai_response_text(response_text)
        }
        
        try:
            # 尝试解析JSON格式的响应
            import json
            import re
            
            # 查找JSON块
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_matches = re.findall(json_pattern, response_text, re.DOTALL)
            
            parsed_data = None
            for json_str in json_matches:
                try:
                    parsed_data = json.loads(json_str)
                    break
                except:
                    continue
            
            if parsed_data:
                # 提取结构化数据
                result['features_extracted'] = parsed_data.get('features', {})
                result['diagnosis_suggestions'] = parsed_data.get('diagnosis_suggestions', [])
                result['confidence_score'] = parsed_data.get('confidence_score', 0.0)
                
                # 验证必需特征
                required_features = analysis_config.get('required_features', [])
                for feature in required_features:
                    if feature not in result['features_extracted']:
                        result['features_extracted'][feature] = "未明确观察到"
            
            else:
                # 如果无法解析JSON，则使用文本解析
                result = self._parse_text_response(response_text, analysis_config)
                
        except Exception as e:
            logger.error(f"解析分析响应失败: {e}")
            # 返回原始文本分析
            result['raw_analysis'] = response_text
            result['confidence_score'] = 0.5
        
        return result
    
    def _parse_text_response(self, response_text: str, 
                           analysis_config: Dict[str, Any]) -> Dict[str, Any]:
        """解析文本格式的响应"""
        result = {
            'features_extracted': {},
            'diagnosis_suggestions': [],
            'confidence_score': 0.5,
            'raw_analysis': clean_ai_response_text(response_text)
        }
        
        try:
            # 简单的关键词提取
            required_features = analysis_config.get('required_features', [])
            
            for feature in required_features:
                # 查找特征相关描述
                feature_pattern = rf'{feature}[：:](.*?)(?=\n|$|。|，)'
                matches = re.findall(feature_pattern, response_text)
                if matches:
                    result['features_extracted'][feature] = matches[0].strip()
                else:
                    result['features_extracted'][feature] = "未明确描述"
            
            # 提取可能的诊断建议
            diagnosis_keywords = ['诊断', '可能', '建议', '考虑', '倾向']
            lines = response_text.split('\n')
            
            for line in lines:
                if any(keyword in line for keyword in diagnosis_keywords):
                    cleaned_line = line.strip().rstrip('。，')
                    if len(cleaned_line) > 5 and len(cleaned_line) < 50:
                        result['diagnosis_suggestions'].append(cleaned_line)
            
            # 限制建议数量
            result['diagnosis_suggestions'] = result['diagnosis_suggestions'][:3]
            
        except Exception as e:
            logger.error(f"文本响应解析失败: {e}")
        
        return result
    
    def batch_analyze_images(self, images: List[Tuple[bytes, str, str]], 
                           analysis_type: str = 'general') -> List[Dict[str, Any]]:
        """批量分析图像"""
        results = []
        
        for i, (image_data, image_type, context) in enumerate(images):
            logger.info(f"分析第{i+1}/{len(images)}张图像")
            
            result = self.analyze_medical_image(
                image_data=image_data,
                image_type=image_type,
                analysis_type=analysis_type,
                additional_context=context
            )
            
            result['image_index'] = i
            results.append(result)
        
        return results
    
    def extract_features_from_image(self, image_path: str) -> Dict[str, Any]:
        """从图像路径提取特征（兼容原有接口）"""
        try:
            # 读取图像文件
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # 获取文件扩展名
            file_ext = Path(image_path).suffix.lstrip('.')
            
            # 调用分析
            result = self.analyze_medical_image(
                image_data=image_data,
                image_type=file_ext,
                analysis_type='general'
            )
            
            # 转换为原有格式
            if result['success']:
                return {
                    'success': True,
                    'features': result['features_extracted'],
                    'analysis': result['raw_analysis'],
                    'confidence': result['confidence_score']
                }
            else:
                return {
                    'success': False,
                    'error': result['error_message']
                }
                
        except Exception as e:
            logger.error(f"图像特征提取失败: {e}")
            return {
                'success': False,
                'error': f"特征提取错误: {str(e)}"
            }
    
    # 预设提示词模板
    def _get_tongue_analysis_prompt(self) -> str:
        return """请作为一名中医专家，详细分析这张舌象图片。请从以下方面进行观察和分析：

1. 舌质：观察舌体的颜色、形状、大小、质地
2. 舌苔：观察苔质的厚薄、润燥、颜色、分布
3. 舌形：观察舌体是否肿大、瘦小、有齿痕等
4. 舌色：观察舌质的具体颜色变化
5. 舌下络脉：如果能观察到，请描述络脉情况

请根据观察到的舌象特征，结合中医理论，给出可能的证型判断和健康状况分析。"""
    
    def _get_pulse_analysis_prompt(self) -> str:
        return """请作为一名中医专家，分析这张脉象相关图片。请从以下方面进行分析：

1. 脉位：观察脉搏的深浅位置
2. 脉率：分析脉搏的快慢节律
3. 脉力：评估脉搏的强弱力度
4. 脉形：描述脉象的具体形态特征

请结合观察到的脉象特征，给出相应的中医诊断建议。"""
    
    def _get_skin_analysis_prompt(self) -> str:
        return """请作为一名医学专家，分析这张皮肤症状图片。请从以下方面进行观察：

1. 颜色：描述皮肤的颜色变化
2. 形状：观察皮损的形态特征
3. 分布：分析症状的分布模式
4. 质地：评估皮肤的质地变化
5. 边界：观察病变的边界情况

请根据观察结果，提供可能的诊断方向和建议。"""
    
    def _get_general_analysis_prompt(self) -> str:
        return """请作为一名医学专家，仔细观察和分析这张医疗相关图片。请从以下方面进行详细分析：

1. 外观特征：描述图像中的主要视觉特征
2. 颜色变化：观察是否有异常的颜色表现
3. 形状结构：分析相关解剖结构或病变形态
4. 异常表现：识别可能的异常或病理表现

请基于专业医学知识，提供客观的观察结果和可能的医学解释。"""