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
sys.path.append('/opt/tcm-ai')
from core.prescription.tcm_formula_analyzer import analyze_formula_with_ai

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
        self.model = 'qwen-vl-max'  # 使用最强版本
        self.timeout = 80  # API调用超时时间 (多模态LLM需要更长时间)
        
        # 专业的系统提示词模板
        self.system_prompt_template = """你是资深的中医药专家和处方分析师，具有30年临床经验。请仔细分析上传的医疗文档图片，提取完整的结构化信息。

核心要求：
1. 准确识别文档类型（处方单/病历/检查报告/结算单等）
2. 完整提取所有中药材信息（名称、剂量、炮制方法）
3. 识别患者基本信息和医疗机构信息
4. **重点**: 智能提取诊断信息，根据不同文档类型采用不同策略
5. 提供专业的用药安全分析和建议
6. 以标准JSON格式返回，确保格式正确

## 诊断信息提取策略：

### 1. 处方单/病历：
- 直接查找诊断、病名、证型等明确标注

### 2. 医疗结算单/费用清单：
- 虽然主要是费用信息，但要智能分析药材配伍推断治疗方向
- 查找"中医辨证论治"、"中医内科"等科室信息
- 根据药物组合智能推测病症类型，不要简单标注"无法识别"

### 3. 智能推理示例：
如果看到以下药物组合：
- 桔梗、荆芥、百部、浙贝母 → 止咳化痰，推测诊断：咳嗽
- 甘草、茯苓、陈皮、半夏 → 健脾化痰，推测诊断：脾虚痰湿
- 炒莱菔子、炒紫苏子 → 消食降气，推测诊断：食积咳嗽

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

重要说明：
- **对于诊断信息**：如果无直接标注，请基于药物配伍进行专业推断，不要简单标注"无法识别"
- **推断原则**：结合中医理论、药物功效、临床经验进行合理推测
- 确保所有药材信息的准确性，药名必须是标准中药名称
- 剂量必须是具体数字，不要范围值
- 炮制方法要准确（如：净、生、炒、蜜炙、酒制等）
- 安全分析要基于实际中医药学知识
- JSON格式必须完整正确，不能有语法错误

请仔细观察图片，如实提取所有可见信息，对于诊断信息要发挥专业判断能力，确保分析的准确性和专业性。"""

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
            return self._fallback_text_processing(result_text)
    
    def _extract_json_from_text(self, text: str) -> str:
        """从文本中提取JSON内容"""
        
        # 查找JSON代码块
        if '```json' in text:
            json_start = text.find('```json') + 7
            json_end = text.find('```', json_start)
            if json_end > json_start:
                return text[json_start:json_end].strip()
        
        # 查找花括号包围的内容
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return text[start_idx:end_idx + 1]
        
        # 如果都找不到，返回原文本
        return text
    
    def _fallback_text_processing(self, text: str) -> Dict[str, Any]:
        """降级文本处理 - 当JSON解析失败时"""
        
        logger.info("使用降级文本处理模式")
        
        return {
            "success": True,
            "document_analysis": {
                "type": "文本识别结果",
                "confidence": 0.7,
                "quality": "API响应处理中",
                "notes": "使用降级处理模式"
            },
            "raw_text": text,
            "prescription": {
                "herbs": [],
                "total_herbs": 0
            },
            "processing_note": "AI返回格式异常，已使用降级处理，建议人工核实"
        }
    
    def _enhance_analysis_result(self, result: Dict[str, Any], image_path: str) -> Dict[str, Any]:
        """增强和验证分析结果"""
        
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
            
            # 处理炮制名称，提取纯药材名
            clean_name = herb_name.replace('炒', '').replace('姜', '').replace('蜜', '').replace('酒', '')
            
            # 从数据库获取功效信息
            herb_data = analyzer.herb_database.get(clean_name, {})
            functions = herb_data.get('functions', [])
            
            if functions:
                enhanced_herb['function'] = '、'.join(functions)
                enhanced_herb['properties'] = herb_data.get('properties', {})
                enhanced_herb['category'] = herb_data.get('category', '未分类')
            else:
                enhanced_herb['function'] = '调理脏腑功能'
                enhanced_herb['properties'] = {}
                enhanced_herb['category'] = '未分类'
            
            enhanced_herbs.append(enhanced_herb)
        
        return enhanced_herbs
    
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