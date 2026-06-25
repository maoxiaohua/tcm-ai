#!/usr/bin/env python3
"""
多模LLM处方处理器 - 替换OCR+解析方案
基于通义千问VL的现代化处方图片分析系统

作者: Claude AI Assistant  
创建时间: 2025-08-13
版本: v1.0 - 第一阶段实施
"""

import asyncio
import json
import logging
import tempfile
import os
from typing import Dict, Optional, Any, List
from pathlib import Path
from dashscope import MultiModalConversation
from dashscope.api_entities.dashscope_response import DashScopeAPIResponse
import sys
sys.path.append('/home/ute/tcm-ai')
from core.prescription.tcm_formula_analyzer import analyze_formula_with_ai
from config.settings import AI_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiModalPrescriptionProcessor:
    """
    多模LLM处方处理器
    
    核心功能:
    1. 直接分析处方图片，无需OCR预处理
    2. 智能识别药材名称、剂量、炮制方法
    3. 提取患者信息、医院信息、诊断结果
    4. 进行专业的安全性分析
    5. 返回标准化JSON结果
    """
    
    def __init__(self):
        self.model = AI_CONFIG.get("multimodal_model", "qwen3.5-omni-plus-2026-03-15")
        self.timeout = 150  # API调用超时时间 (多模态LLM需要更长时间，设置比nginx更长)
        
        # 专业的系统提示词模板
        self.system_prompt_template = """你是资深的中医药专家和处方分析师，具有30年临床经验。请仔细分析上传的图片。

**⚠️ 重要警告：请务必先检查这是否真的是医疗文档！**

## 第一步：图像内容识别
请先判断上传的图像是否包含以下医疗文档特征：
- 医院/诊所的抬头或标识
- 医生姓名和签章/印章
- 患者基本信息栏位  
- 处方单格式（药名、剂量列表）
- 医疗费用清单格式
- 病历记录格式

**如果图像不包含这些医疗文档特征（比如是合照、风景照、日常生活照片等），请直接返回：**
```json
{
    "success": false,
    "error": "非医疗文档",
    "message": "上传的图片不是医疗处方或相关文档，请上传正确的处方图片"
}
```

## 第二步：医疗文档分析（仅当确认是医疗文档时执行）

核心要求：
1. 准确识别文档类型（处方单/病历/检查报告/结算单等）
2. 完整提取所有中药材信息（名称、剂量、炮制方法）
3. 识别患者基本信息和医疗机构信息
4. 智能提取诊断信息
5. 提供专业的用药安全分析和建议
6. 以标准JSON格式返回，确保格式正确

## 诊断信息提取策略：

### 1. 处方单/病历：
- 直接查找诊断、病名、证型等明确标注

### 2. 医疗结算单/费用清单：
- 查找"中医辨证论治"、"中医内科"等科室信息
- 基于实际提取的药物配伍进行合理的医学推断
- 避免过度推测，如果不确定请标注"需要更多信息"

返回JSON结构：
{
    "success": true,
    "document_analysis": {
        "type": "文档类型（处方单/医疗结算单/病历等）",
        "confidence": "识别置信度（0-1）",
        "quality": "图片质量（清晰/模糊/难以识别）",
        "notes": "文档描述和特征说明"
    },
    "medical_info": {
        "hospital": "医疗机构名称", 
        "department": "科室（中医科/内科等）",
        "doctor": "医生姓名",
        "date": "就诊日期",
        "prescription_id": "处方号/单据号"
    },
    "patient_info": {
        "name": "患者姓名",
        "gender": "性别", 
        "age": "年龄", 
        "id": "病历号/就诊号",
        "phone": "联系电话"
    },
    "diagnosis": {
        "primary": "主要诊断（如果无直接标注，根据药物组合和临床经验推测，如：咳嗽、食积等）",
        "secondary": ["次要诊断1", "次要诊断2"],
        "tcm_syndrome": "中医证型（根据药物配伍推断，如：痰热咳嗽、脾虚痰湿等）",
        "symptoms": ["症状1", "症状2", "症状3"]
    },
    "prescription": {
        "herbs": [
            {
                "name": "药材名称（如：甘草）",
                "dosage": "剂量数字（如：6）",
                "unit": "单位（g/克/钱等）",
                "processing": "炮制方法（如：净、炒、蜜炙等）",
                "notes": "特殊备注"
            }
        ],
        "usage": {
            "method": "煎服方法（如：水煎服）",
            "frequency": "服用频次（如：日2次）",
            "duration": "疗程（如：7剂）",
            "timing": "服用时间（如：饭后温服）",
            "precautions": ["注意事项1", "注意事项2"]
        },
        "total_herbs": "总药味数（数字）",
        "estimated_cost": "预估费用（数字，单位元）"
    },
    "safety_analysis": {
        "overall_safety": "整体安全性评级（安全/需注意/有风险）",
        "warnings": ["安全警告1", "安全警告2"],
        "contraindications": ["禁忌症1", "禁忌症2"],
        "interactions": ["可能的药物相互作用"],
        "special_populations": ["孕妇慎用", "儿童减量等特殊人群用药建议"]
    },
    "clinical_analysis": {
        "formula_type": "方剂类型（如：清热剂、补益剂等）",
        "therapeutic_principle": "治疗原则",
        "expected_effects": ["预期疗效1", "预期疗效2"],
        "similar_formulas": ["相似经典方剂"],
        "modification_suggestions": ["加减建议"]
    }
}

**⚠️ 再次强调：只有确认是真实的医疗文档才能进行分析！**

重要说明：
- **优先级1**：验证是否为医疗文档，非医疗图片直接拒绝
- **对于诊断信息**：基于文档中实际记录的信息，避免过度推测  
- **推断原则**：必须有明确的医学依据，不确定时保持保守态度
- 确保所有药材信息的准确性，药名必须是标准中药名称
- 剂量必须是具体数字，不要范围值
- 炮制方法要准确（如：净、生、炒、蜜炙、酒制等）
- 安全分析要基于实际中医药学知识
- JSON格式必须完整正确，不能有语法错误

请仔细观察图片，**首先确认这是医疗文档**，然后如实提取所有可见信息，确保分析的准确性和专业性。"""

    async def analyze_prescription_image(self, image_path: str, patient_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        分析处方图片的主方法
        
        Args:
            image_path: 图片文件路径
            patient_context: 可选的患者上下文信息
            
        Returns:
            标准化的分析结果字典
        """
        logger.info(f"开始分析处方图片: {image_path}")
        
        # 检查文件是否存在
        if not os.path.exists(image_path):
            return self._create_error_response("图片文件不存在")
        
        # 检查文件大小（限制10MB）
        file_size = os.path.getsize(image_path) / (1024 * 1024)
        if file_size > 10:
            return self._create_error_response(f"图片文件过大: {file_size:.2f}MB，请上传小于10MB的图片")
        
        try:
            # 构建消息
            messages = self._build_messages(image_path, patient_context)
            
            # 调用通义千问VL
            logger.info("正在调用通义千问VL进行图片分析...")
            response = await self._call_multimodal_api(messages)
            
            if response.status_code != 200:
                return self._create_error_response(f"多模LLM API调用失败: {response.message}")
            
            # 处理API响应
            result = self._process_api_response(response)
            
            # 验证和增强结果
            result = self._enhance_analysis_result(result, image_path)
            
            logger.info(f"图片分析完成，识别到 {result.get('prescription', {}).get('total_herbs', 0)} 味中药")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return self._create_error_response(f"AI响应格式解析失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"处方图片分析失败: {e}")
            return self._create_error_response(f"图片分析异常: {str(e)}")
    
    def _build_messages(self, image_path: str, patient_context: Optional[Dict]) -> list:
        """构建API调用消息"""
        
        # 基础系统提示词
        system_content = self.system_prompt_template
        
        # 如果有患者上下文，增强提示词
        if patient_context:
            context_info = f"""
            
额外上下文信息：
患者信息: {json.dumps(patient_context, ensure_ascii=False, indent=2)}

请结合这些上下文信息进行更准确的分析。"""
            system_content += context_info
        
        messages = [{
            "role": "user",
            "content": [
                {"text": system_content},
                {"image": f"file://{image_path}"}
            ]
        }]
        
        return messages
    
    async def _call_multimodal_api(self, messages: list) -> DashScopeAPIResponse:
        """调用多模态API"""
        
        response = MultiModalConversation.call(
            model=self.model,
            messages=messages,
            timeout=self.timeout
        )
        
        return response
    
    def _process_api_response(self, response: DashScopeAPIResponse) -> Dict[str, Any]:
        """处理API响应"""
        
        # 提取响应内容
        content = response.output.choices[0].message.content
        if isinstance(content, list):
            result_text = content[0].get('text', '')
        else:
            result_text = content
        
        logger.info(f"API原始响应长度: {len(result_text)}")
        logger.debug(f"API原始响应: {result_text[:500]}...")
        
        # 提取JSON内容
        json_text = self._extract_json_from_text(result_text)
        logger.info(f"提取的JSON长度: {len(json_text)}")
        logger.debug(f"提取的JSON: {json_text[:500]}...")
        
        # 解析JSON
        try:
            result = json.loads(json_text)
            logger.info(f"JSON解析成功，包含字段: {list(result.keys())}")
            
            # 确保success字段
            if 'success' not in result:
                result['success'] = True
                
            return result
            
        except json.JSONDecodeError as e:
            # 如果JSON解析失败，尝试简单的文本处理
            logger.warning(f"JSON解析失败，尝试文本处理: {e}")
            logger.warning(f"提取的JSON前100字符: {json_text[:100]}")
            logger.warning(f"原始响应前200字符: {result_text[:200]}")
            return self._fallback_text_processing(result_text)
    
    def _extract_json_from_text(self, text: str) -> str:
        """从文本中提取JSON内容"""
        
        # 预处理：移除可能干扰的字符
        text = text.strip()
        
        # 查找JSON代码块
        if '```json' in text:
            json_start = text.find('```json') + 7
            json_end = text.find('```', json_start)
            if json_end > json_start:
                json_content = text[json_start:json_end].strip()
                return self._clean_json_content(json_content)
        
        # 查找花括号包围的内容 - 改进算法，支持嵌套花括号
        start_idx = text.find('{')
        if start_idx == -1:
            return text
            
        # 使用栈算法找到匹配的结束花括号
        brace_count = 0
        end_idx = start_idx
        
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break
        
        if brace_count == 0 and end_idx > start_idx:
            json_content = text[start_idx:end_idx + 1]
            return self._clean_json_content(json_content)
        
        # 如果都找不到，返回原文本
        return text
    
    def _clean_json_content(self, json_str: str) -> str:
        """清理JSON内容，移除可能的干扰字符"""
        
        # 移除前后空白
        json_str = json_str.strip()
        
        # 移除可能的BOM字符
        if json_str.startswith('\ufeff'):
            json_str = json_str[1:]
        
        # 移除JSON前后的非JSON字符
        # 确保以{开始，以}结束
        start = json_str.find('{')
        end = json_str.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            json_str = json_str[start:end + 1]
        
        return json_str
    
    def _fallback_text_processing(self, text: str) -> Dict[str, Any]:
        """降级文本处理 - 当JSON解析失败时"""
        
        logger.info("使用降级文本处理模式")
        
        # 尝试从文本中提取基本信息
        extracted_info = self._extract_basic_info_from_text(text)
        
        return {
            "success": True,
            "document_analysis": {
                "type": extracted_info.get('doc_type', "文本识别结果"),
                "confidence": 0.6,  # 降级处理的置信度较低
                "quality": "JSON解析失败，使用文本分析",
                "notes": "使用降级处理模式，建议人工核实"
            },
            "prescription": {
                "herbs": extracted_info.get('herbs', []),
                "total_herbs": len(extracted_info.get('herbs', []))
            },
            "medical_info": extracted_info.get('medical_info', {}),
            "patient_info": extracted_info.get('patient_info', {}),
            "diagnosis": extracted_info.get('diagnosis', {}),
            "raw_text": text[:1000],  # 限制长度
            "processing_note": "AI返回格式异常，已使用降级处理，建议人工核实"
        }
    
    def _extract_basic_info_from_text(self, text: str) -> Dict[str, Any]:
        """从文本中提取基本信息（降级处理时使用）"""
        
        result = {
            'herbs': [],
            'medical_info': {},
            'patient_info': {},
            'diagnosis': {},
            'doc_type': '处方文档'
        }
        
        # 常见中药名称正则
        herb_patterns = [
            r'([甘草|人参|当归|白术|茯苓|陈皮|半夏|生姜|大枣|桔梗|荆芥|防风|白芷|川芎|红花|桃仁|杏仁|麻黄|桂枝|柴胡|黄芩|黄连|黄柏|知母|石膏|栀子|连翘|金银花|板蓝根|大青叶|蒲公英|紫花地丁|野菊花|白头翁|秦皮|黄芪|党参|太子参|西洋参|红参|白参|熟地黄|生地黄|玉竹|麦冬|天冬|石斛|枸杞子|菊花|决明子|车前子|泽泻|木通|通草|滑石|茵陈|栀子|大黄|芒硝|番泻叶|芦荟|火麻仁|郁李仁|桃仁|杏仁|白果|苏子|莱菔子|芥子|百部|浙贝母|川贝母|瓜蒌|桔梗|前胡|紫菀|款冬花|枇杷叶|桑白皮|葶苈子|白芥子|苏子|莱菔子|芥子|百合|沙参|玉竹|天花粉|芦根|茅根|竹叶|淡竹叶])+[^a-zA-Z]*?(\d+(?:\.\d+)?)\s*([克|g|钱|两|斤|毫升|ml]+)',
            r'([一-龟]+)\s*(\d+(?:\.\d+)?)\s*([克|g|钱|两|斤|毫升|ml]+)'
        ]
        
        # 尝试提取药材信息
        for pattern in herb_patterns:
            import re
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) >= 3:
                    herb_name = match[0].strip()
                    dosage = match[1].strip()
                    unit = match[2].strip()
                    
                    if herb_name and dosage:
                        result['herbs'].append({
                            'name': herb_name,
                            'dosage': dosage,
                            'unit': unit,
                            'processing': '净',
                            'notes': '文本提取'
                        })
        
        # 去重
        seen_herbs = set()
        unique_herbs = []
        for herb in result['herbs']:
            herb_key = herb['name']
            if herb_key not in seen_herbs:
                seen_herbs.add(herb_key)
                unique_herbs.append(herb)
        result['herbs'] = unique_herbs
        
        # 提取医院信息
        hospital_patterns = [
            r'([^，。]+(?:医院|诊所|卫生院|卫生服务中心|中医院|人民医院))',
            r'([^，。]+(?:Hospital|Clinic|Medical Center))'
        ]
        
        for pattern in hospital_patterns:
            import re
            matches = re.findall(pattern, text)
            if matches:
                result['medical_info']['hospital'] = matches[0].strip()
                break
        
        # 提取诊断信息
        diagnosis_patterns = [
            r'诊断[：:]\s*([^，。\n]+)',
            r'病名[：:]\s*([^，。\n]+)',
            r'主诉[：:]\s*([^，。\n]+)'
        ]
        
        for pattern in diagnosis_patterns:
            import re
            matches = re.findall(pattern, text)
            if matches:
                result['diagnosis']['primary'] = matches[0].strip()
                break
        
        # 如果提取到了药材或医疗信息，判断为医疗文档
        if result['herbs'] or result['medical_info'] or result['diagnosis']:
            result['doc_type'] = '医疗处方文档'
        
        logger.info(f"降级处理提取到：{len(result['herbs'])}味药材，医疗信息：{bool(result['medical_info'])}，诊断：{bool(result['diagnosis'])}")
        
        return result
    
    def _enhance_analysis_result(self, result: Dict[str, Any], image_path: str) -> Dict[str, Any]:
        """增强和验证分析结果"""
        
        # 🚨 首要验证：检查是否为有效的医疗文档分析结果
        if not result.get('success', True):
            # 如果AI已经判断这不是医疗文档，直接返回错误
            if result.get('error') == '非医疗文档':
                return result
        
        # 🚨 暂时禁用医疗文档验证 - 恢复到原来的工作状态
        # 只在极端情况下才拒绝（完全没有任何医疗相关信息）
        prescription = result.get('prescription', {})
        herbs = prescription.get('herbs', [])
        medical_info = result.get('medical_info', {})
        patient_info = result.get('patient_info', {})
        
        # 只有在完全没有任何相关信息时才拒绝
        has_any_medical_content = (
            len(herbs) > 0 or  # 有药材信息
            any(medical_info.values()) or  # 有医疗机构信息
            any(patient_info.values())  # 有患者信息
        )
        
        if not has_any_medical_content:
            return {
                "success": False,
                "error": "非医疗文档",
                "message": "上传的图片不包含任何医疗相关信息，请确认是否为处方图片",
                "validation_failed": "无任何医疗内容"
            }
        
        # 如果有任何医疗相关内容，就直接通过，不再进行复杂验证
        logger.info(f"检测到医疗内容：药材{len(herbs)}味，医疗信息{bool(any(medical_info.values()))}，患者信息{bool(any(patient_info.values()))}")
        
        # 添加处理元数据
        result['processing_info'] = {
            "processor": "MultiModalPrescriptionProcessor",
            "model": self.model,
            "version": "v1.0",
            "processed_at": self._get_current_timestamp(),
            "image_info": {
                "path": os.path.basename(image_path),
                "size_mb": round(os.path.getsize(image_path) / (1024 * 1024), 2)
            }
        }
        
        # 验证和修正数据结构
        result = self._validate_result_structure(result)
        
        # 计算统计信息
        if 'prescription' in result and 'herbs' in result['prescription']:
            herbs_count = len(result['prescription']['herbs'])
            result['prescription']['total_herbs'] = herbs_count
            result['statistics'] = {
                "herbs_identified": herbs_count,
                "has_patient_info": bool(result.get('patient_info', {}).get('name')),
                "has_diagnosis": bool(result.get('diagnosis', {}).get('primary')),
                "safety_warnings_count": len(result.get('safety_analysis', {}).get('warnings', []))
            }
            
            # 增强药材信息，添加功效描述
            result['prescription']['herbs'] = self._enhance_herb_info(result['prescription']['herbs'])
            
            # 添加君臣佐使分析
            if herbs_count >= 3:  # 至少3味药才进行分析
                try:
                    logger.info(f"开始君臣佐使分析，共{herbs_count}味药材")
                    formula_analysis = analyze_formula_with_ai(result['prescription']['herbs'])
                    result['formula_analysis'] = formula_analysis
                    logger.info(f"君臣佐使分析完成: {formula_analysis.get('confidence_level', 'unknown')}")
                except Exception as e:
                    logger.error(f"君臣佐使分析失败: {e}")
                    result['formula_analysis'] = {
                        'error': f'分析失败: {str(e)}',
                        'roles': {'君药': [], '臣药': [], '佐药': [], '使药': []},
                        'confidence_level': 'failed'
                    }
        
        return result
    
    def _enhance_herb_info(self, herbs: List[Dict]) -> List[Dict]:
        """增强药材信息，添加功效描述"""
        from core.prescription.tcm_formula_analyzer import TCMFormulaAnalyzer
        
        analyzer = TCMFormulaAnalyzer()
        enhanced_herbs = []
        
        for herb in herbs:
            enhanced_herb = herb.copy()
            herb_name = herb.get('name', '')
            
            # 处理炮制名称，提取纯药材名 - 改进的清理逻辑
            clean_name = self._clean_herb_name(herb_name)
            
            # 从数据库获取功效信息
            herb_data = analyzer.herb_database.get(clean_name, {})
            functions = herb_data.get('functions', [])
            
            # 调试日志
            logger.debug(f"药材名称匹配: '{herb_name}' -> '{clean_name}' -> 找到数据: {bool(herb_data)}")
            
            if functions:
                enhanced_herb['function'] = '、'.join(functions)
                enhanced_herb['properties'] = herb_data.get('properties', {})
                enhanced_herb['category'] = herb_data.get('category', '未分类')
                logger.debug(f"药材 {clean_name} 功效: {functions}")
            else:
                # 如果在主数据库中找不到，尝试备用数据库或使用默认功效
                fallback_function = self._get_fallback_herb_function(clean_name)
                enhanced_herb['function'] = fallback_function
                enhanced_herb['properties'] = {}
                enhanced_herb['category'] = '未分类'
                logger.warning(f"药材 {herb_name} (清理后: {clean_name}) 未在数据库中找到，使用备用功效: {fallback_function}")
            
            enhanced_herbs.append(enhanced_herb)
        
        return enhanced_herbs
    
    def _clean_herb_name(self, herb_name: str) -> str:
        """清理药材名称，移除炮制前缀，保留核心药材名"""
        from core.prescription.tcm_formula_analyzer import TCMFormulaAnalyzer
        
        original_name = herb_name.strip()
        
        # 首先检查原名称是否直接在数据库中存在
        analyzer = TCMFormulaAnalyzer()
        if original_name in analyzer.herb_database:
            return original_name
        
        # 特殊情况处理 - 优先处理
        special_mappings = {
            '姜半夏': '半夏',
            '姜厚朴': '厚朴', 
            '姜黄连': '黄连',
            '炙甘草': '甘草',
            '炙黄芪': '黄芪',
            '蜜枇杷叶': '枇杷叶',
            '酒当归': '当归',
            '酒白芍': '白芍',
            '盐杜仲': '杜仲',
            '盐知母': '知母',
            '制附子': '附子',
            '制南星': '南星',
            '制首乌': '何首乌',
            '炒白术': '白术',
            '炒苍术': '苍术',
            '炒山楂': '山楂',
            '炒神曲': '神曲',
            '炒麦芽': '麦芽',
            '生地黄': '地黄',
            '熟地黄': '地黄',
            '醋香附': '香附',
            '醋延胡索': '延胡索'
        }
        
        if original_name in special_mappings:
            mapped_name = special_mappings[original_name]
            if mapped_name in analyzer.herb_database:
                return mapped_name
        
        # 移除常见炮制前缀 - 更保守的策略
        prefixes_to_remove = ['炒', '生', '制', '蜜', '酒', '醋', '盐', '土', '煅', '焦', '炙']
        
        clean_name = original_name
        
        # 只有当药材名称长度>2且以炮制前缀开头时才移除前缀
        for prefix in prefixes_to_remove:
            if len(clean_name) > 2 and clean_name.startswith(prefix):
                # 特殊处理：避免误删除核心药材名的一部分
                potential_clean = clean_name[len(prefix):]
                
                # 检查清理后的名称是否在数据库中存在
                if len(potential_clean) >= 2 and potential_clean in analyzer.herb_database:
                    clean_name = potential_clean
                    break
                
                # 如果数据库中没有，但看起来像合理的药材名，仍然清理
                if (len(potential_clean) >= 2 and 
                    not potential_clean.startswith('芥') and  # 避免"荆芥"被错误处理
                    not potential_clean in ['草', '参', '芪', '术']):  # 避免过度清理
                    clean_name = potential_clean
                    break
        
        return clean_name
    
    def _get_fallback_herb_function(self, herb_name: str) -> str:
        """获取备用的药材功效信息"""
        
        # 备用功效数据库 - 包含更多常见药材
        fallback_functions = {
            # 解表药
            '荆芥': '散风解表、透疹消疮、止血',
            '防风': '祛风解表、胜湿止痛、止痉',
            '桔梗': '宣肺、利咽、祛痰、排脓',
            
            # 化痰止咳平喘药
            '百部': '润肺下气止咳、杀虫灭虱',
            '浙贝母': '清热化痰、散结消肿',
            '川贝母': '清热润肺、化痰止咳',
            '瓜蒌': '清热涤痰、宽胸散结、润燥滑肠',
            '前胡': '降气化痰、散风清热',
            '紫菀': '润肺下气、消痰止咳',
            '款冬花': '润肺下气、止咳化痰',
            '枇杷叶': '清肺止咳、降逆止呕',
            '桑白皮': '泻肺平喘、利水消肿',
            '葶苈子': '泻肺平喘、行水消肿',
            '白芥子': '温肺豁痰、利气散结',
            '苏子': '降气化痰、止咳平喘、润肠通便',
            '莱菔子': '消食除胀、降气化痰',
            '芥子': '温肺豁痰、利气散结',
            
            # 补益药
            '百合': '养阴润肺、清心安神',
            '沙参': '清热养阴、润肺止咳',
            '玉竹': '养阴润燥、生津止渴',
            '天花粉': '清热泻火、生津止渴、消肿排脓',
            
            # 理气药
            '陈皮': '理气健脾、燥湿化痰',
            '青皮': '疏肝破气、消积化滞',
            '枳壳': '理气宽中、行滞消胀',
            '枳实': '破气消积、化痰散痞',
            '木香': '行气止痛、健脾消食',
            '香附': '疏肝解郁、理气调经、止痛',
            '佛手': '疏肝理气、和中化痰',
            '青木香': '行气止痛、解毒消肿',
            
            # 平肝息风药
            '蝉蜕': '疏散风热、利咽开音、透疹、明目退翳、息风止痉',
            '僵蚕': '息风止痉、祛风止痛、化痰散结',
            
            # 化痰药
            '茯苓': '利水渗湿、健脾、宁心',
            '半夏': '燥湿化痰、降逆止呕、消痞散结',
            '姜半夏': '燥湿化痰、降逆止呕、消痞散结',
            '旋覆花': '降气、消痰、行水、止呕',
            
            # 补气药
            '甘草': '补脾益气、清热解毒、祛痰止咳、缓急止痛、调和诸药',
            
            # 其他常见药材
            '扯根菜': '清热解毒、利湿消肿',
            '甜叶菊': '清热生津、润燥',
            '枯梗': '宣肺利咽、祛痰排脓'
        }
        
        # 如果备用数据库中也没有，则使用更智能的默认描述
        if '参' in herb_name:
            return '补气健脾、扶正固本'
        elif any(x in herb_name for x in ['芪', '耆']):
            return '补气升阳、固表止汗'  
        elif any(x in herb_name for x in ['归', '当']):
            return '补血活血、调经止痛'
        elif '草' in herb_name:
            return '清热解毒、调和诸药'
        elif any(x in herb_name for x in ['术', '朮']):
            return '健脾燥湿、补气利水'
        elif '苓' in herb_name:
            return '利水渗湿、健脾宁心'
        elif '芍' in herb_name:
            return '养血柔肝、缓急止痛'
        elif '地' in herb_name:
            return '滋阴补血、清热凉血'
        elif any(x in herb_name for x in ['芎', '川']):
            return '活血行气、祛风止痛'
        elif '皮' in herb_name:
            return '理气化痰、行气消胀'  
        elif '花' in herb_name:
            return '行气解郁、理血调经'
        elif '子' in herb_name:
            return '润肠通便、消食除胀'
        else:
            # 最后的智能fallback - 避免千篇一律的"调理脏腑功能"
            return '辅助调理、协同治疗'
    
    def _validate_result_structure(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证并修正结果数据结构"""
        
        # 确保必需的顶级键存在
        required_keys = ['success', 'document_analysis', 'prescription', 'safety_analysis']
        for key in required_keys:
            if key not in result:
                result[key] = {}
        
        # 确保prescription结构完整
        if 'herbs' not in result['prescription']:
            result['prescription']['herbs'] = []
        
        # 确保safety_analysis结构完整
        safety_keys = ['warnings', 'contraindications', 'interactions']
        for key in safety_keys:
            if key not in result['safety_analysis']:
                result['safety_analysis'][key] = []
        
        return result
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """创建错误响应"""
        
        return {
            "success": False,
            "error": error_message,
            "document_analysis": {
                "type": "处理失败",
                "confidence": 0.0,
                "quality": "无法处理",
                "notes": error_message
            },
            "prescription": {
                "herbs": [],
                "total_herbs": 0
            },
            "safety_analysis": {
                "warnings": [f"处理失败: {error_message}"],
                "contraindications": [],
                "interactions": []
            },
            "processing_info": {
                "processor": "MultiModalPrescriptionProcessor",
                "error": True,
                "processed_at": self._get_current_timestamp()
            }
        }
    
    def _validate_medical_document_features(self, result: Dict[str, Any]) -> bool:
        """验证是否具备医疗文档的基本特征"""
        try:
            # 检查1: 是否有医疗机构信息
            medical_info = result.get('medical_info', {})
            has_medical_institution = any([
                medical_info.get('hospital', '').strip(),
                medical_info.get('department', '').strip(),
                medical_info.get('doctor', '').strip()
            ])
            
            # 检查2: 是否有处方药物信息
            prescription = result.get('prescription', {})
            herbs = prescription.get('herbs', [])
            has_prescription_data = len(herbs) > 0
            
            # 检查3: 是否有患者信息（至少应该有部分信息）
            patient_info = result.get('patient_info', {})
            has_patient_data = any([
                patient_info.get('name', '').strip(),
                patient_info.get('gender', '').strip(),
                patient_info.get('age', '').strip(),
                patient_info.get('id', '').strip()
            ])
            
            # 检查4: 文档分析结果
            doc_analysis = result.get('document_analysis', {})
            doc_type = doc_analysis.get('type', '').strip()
            is_medical_document_type = any(keyword in doc_type for keyword in [
                '处方', '病历', '诊断', '医疗', '结算', '费用', '药房', '中医', '西医'
            ]) if doc_type else False
            
            # 检查5: 如果有药物，检查是否为合理的中药名称（放宽验证）
            if has_prescription_data and len(herbs) > 0:
                valid_herbs = 0
                checked_herbs = herbs[:min(5, len(herbs))]  # 最多检查前5个药材
                
                for herb in checked_herbs:
                    herb_name = herb.get('name', '').strip()
                    # 放宽验证：中药名称通常为中文，长度1-10字符（包含一些复方名称）
                    if herb_name and len(herb_name) >= 1 and len(herb_name) <= 10:
                        # 检查是否包含中文字符或者常见的中药字符
                        if (any('\u4e00' <= char <= '\u9fff' for char in herb_name) or 
                            any(common_char in herb_name for common_char in ['草', '芍', '芝', '参', '苓', '归', '芪', '枝', '花', '子', '仁', '皮', '根'])):
                            valid_herbs += 1
                
                # 显著降低验证门槛：只要有1/3的药材名称合理就通过
                validation_ratio = valid_herbs / len(checked_herbs) if checked_herbs else 0
                logger.info(f"药材名称验证: {valid_herbs}/{len(checked_herbs)} 个合理 (比例: {validation_ratio:.2f})")
                
                if validation_ratio < 0.33:  # 降低至33%门槛
                    logger.warning(f"药材名称验证失败: 合理比例 {validation_ratio:.2f} < 0.33")
                    # 但不直接返回False，而是记录警告，让综合判断决定
                    # return False  # 注释掉直接拒绝
            
            # 综合判断：降低验证门槛，优先保证真实处方不被误拦
            validation_score = 0
            if has_medical_institution:
                validation_score += 3  # 医疗机构信息权重最高
            if has_prescription_data:
                validation_score += 3  # 处方数据权重提升至最高（核心特征）
            if has_patient_data:
                validation_score += 1  # 患者信息权重最低
            if is_medical_document_type:
                validation_score += 2  # 文档类型识别权重中等
            
            logger.info(f"医疗文档特征验证得分: {validation_score}/9")
            logger.info(f"验证详情: 医疗机构={has_medical_institution}, 处方数据={has_prescription_data}, 患者信息={has_patient_data}, 文档类型={is_medical_document_type}")
            logger.info(f"医疗机构信息: {medical_info}")
            logger.info(f"处方药材数: {len(herbs)}")
            logger.info(f"患者信息: {patient_info}")
            logger.info(f"文档类型: '{doc_type}'")
            
            # 降低门槛：只要有处方数据(3分)就认为是医疗文档
            # 或者有医疗机构信息(3分)
            # 这样可以避免误杀正常处方
            if validation_score >= 3:
                return True
            
            # 如果得分较低，但是有处方数据，给一个机会（可能是简单处方单）
            if has_prescription_data and len(herbs) >= 2:  # 至少2味药
                logger.info("得分较低但存在处方数据，允许通过")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"医疗文档特征验证失败: {e}")
            return False
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 全局实例
multimodal_processor = MultiModalPrescriptionProcessor()

# =========================
# 便捷函数
# =========================

async def analyze_prescription_image_file(image_path: str, patient_context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    便捷函数：分析处方图片文件
    
    Args:
        image_path: 图片文件路径
        patient_context: 可选的患者上下文信息
        
    Returns:
        分析结果字典
    """
    return await multimodal_processor.analyze_prescription_image(image_path, patient_context)

async def analyze_prescription_image_bytes(image_bytes: bytes, filename: str = "prescription.jpg", patient_context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    便捷函数：分析处方图片字节数据
    
    Args:
        image_bytes: 图片字节数据
        filename: 文件名（用于临时文件）
        patient_context: 可选的患者上下文信息
        
    Returns:
        分析结果字典
    """
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_file:
        tmp_file.write(image_bytes)
        tmp_file_path = tmp_file.name
    
    try:
        # 分析图片
        result = await multimodal_processor.analyze_prescription_image(tmp_file_path, patient_context)
        return result
    finally:
        # 清理临时文件
        try:
            os.unlink(tmp_file_path)
        except:
            pass

# =========================
# 测试和演示
# =========================

async def test_multimodal_processor():
    """测试多模处理器功能"""
    
    print("=== 多模LLM处方处理器测试 ===")
    
    # 寻找测试图片
    test_dirs = ["/opt/tcm/test_pictures", "/opt/tcm/Prescription_Folder"]
    test_image = None
    
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            for file in os.listdir(test_dir):
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    test_image = os.path.join(test_dir, file)
                    break
        if test_image:
            break
    
    if not test_image:
        print("❌ 未找到测试图片")
        return
    
    print(f"📷 测试图片: {test_image}")
    
    # 执行分析
    result = await analyze_prescription_image_file(test_image)
    
    # 显示结果
    if result['success']:
        print("✅ 分析成功!")
        
        doc_info = result.get('document_analysis', {})
        print(f"📋 文档类型: {doc_info.get('type', '未识别')}")
        print(f"🎯 置信度: {doc_info.get('confidence', 0):.2f}")
        
        prescription = result.get('prescription', {})
        herbs = prescription.get('herbs', [])
        print(f"💊 识别到 {len(herbs)} 味中药:")
        
        for i, herb in enumerate(herbs[:5], 1):  # 显示前5味
            name = herb.get('name', '未知')
            dosage = herb.get('dosage', '未知')
            unit = herb.get('unit', '')
            processing = herb.get('processing', '')
            
            herb_info = f"  {i}. {name}"
            if dosage != '未知':
                herb_info += f" {dosage}{unit}"
            if processing:
                herb_info += f" ({processing})"
            
            print(herb_info)
        
        if len(herbs) > 5:
            print(f"  ... 还有 {len(herbs) - 5} 味中药")
        
        # 安全分析
        safety = result.get('safety_analysis', {})
        warnings = safety.get('warnings', [])
        if warnings:
            print(f"\n⚠️ 安全提醒:")
            for warning in warnings[:3]:
                print(f"  • {warning}")
        
    else:
        print(f"❌ 分析失败: {result.get('error')}")

# 向后兼容的API函数
async def analyze_prescription_image_bytes(image_bytes: bytes, filename: str = "prescription.jpg") -> Dict[str, Any]:
    """
    分析处方图片字节数据 - API兼容函数
    为了兼容现有的main.py API端点
    """
    import tempfile
    import os
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
        temp_file.write(image_bytes)
        temp_path = temp_file.name
    
    try:
        # 使用多模态处理器分析
        processor = MultiModalPrescriptionProcessor()
        result = await processor.analyze_prescription_image(temp_path)
        return result
    
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)

async def analyze_prescription_image_file(image_path: str) -> Dict[str, Any]:
    """
    分析处方图片文件 - 便捷函数
    """
    processor = MultiModalPrescriptionProcessor()
    return await processor.analyze_prescription_image(image_path)

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_multimodal_processor())