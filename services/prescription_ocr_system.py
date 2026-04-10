#!/usr/bin/env python3
"""
中医处方OCR识别系统 - Prescription OCR Recognition System
功能：图片/PDF识别、医学文本纠错、与现有处方检查系统集成
作者：TCM AI System
"""

import re
import json
import base64
import requests
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageFilter
from typing import Dict, List, Optional, Any, Tuple
from io import BytesIO
import logging
from dataclasses import dataclass
from datetime import datetime

from app.core.settings import AI_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class OCRResult:
    """OCR识别结果结构"""
    text: str  # 识别的文本
    confidence: float  # 识别置信度
    corrected_text: Optional[str] = None  # 医学纠错后的文本
    words_info: Optional[List[Dict]] = None  # 词汇位置信息
    processing_time: Optional[float] = None  # 处理时间

class PrescriptionImageProcessor:
    """处方图像预处理系统"""
    
    def __init__(self):
        """初始化图像处理器"""
        self.supported_formats = ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'pdf']
        self.max_size = (1600, 1600)  # 百度OCR超严格限制: 更保守的尺寸
        self.max_file_size = 500 * 1024  # 500KB文件大小限制 (超保守)
        self.max_base64_size = int(700 * 1024)  # 700KB base64限制 (超保守)
        self.min_size = (15, 15)  # 百度OCR最小限制: 最短边大于10px
        
    def preprocess_image(self, image_data: bytes, format_hint: str = None) -> bytes:
        """图像预处理：智能压缩、去噪、矫正、对比度增强"""
        try:
            # 检查文件大小
            file_size = len(image_data)
            logger.info(f"原始图片大小: {file_size / 1024 / 1024:.2f} MB")
            
            # 打开图像
            image = Image.open(BytesIO(image_data))
            original_size = image.size
            logger.info(f"原始图片尺寸: {original_size}")
            
            # 检查尺寸限制
            if (original_size[0] < self.min_size[0] or original_size[1] < self.min_size[1]):
                logger.warning(f"图片尺寸太小: {original_size}, 最小要求: {self.min_size}")
                # 不抛出异常，而是放大图片到最小尺寸
                scale_factor = max(self.min_size[0] / original_size[0], self.min_size[1] / original_size[1])
                new_size = (int(original_size[0] * scale_factor), int(original_size[1] * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"图片已放大到: {image.size}")
            
            # 转换为RGB模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 1. 智能尺寸调整
            needs_resize = False
            if image.size[0] > self.max_size[0] or image.size[1] > self.max_size[1]:
                needs_resize = True
                logger.info(f"图片尺寸超限，需要压缩: {image.size} -> {self.max_size}")
                image.thumbnail(self.max_size, Image.Resampling.LANCZOS)
                logger.info(f"压缩后尺寸: {image.size}")
            
            # 2. 对比度增强（处方单通常对比度不够）
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.3)
            
            # 3. 锐化处理（提升字符清晰度）
            image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
            
            # 4. 亮度调整
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.1)
            
            # 转换回字节流，智能质量控制
            output = BytesIO()
            
            # 根据文件大小智能调整质量 - 超激进的压缩策略
            if file_size > self.max_file_size:
                # 大文件使用超低质量
                quality = 50
                logger.info("大文件，使用质量50%压缩")
            elif needs_resize:
                # 尺寸调整过的文件使用低质量
                quality = 60
                logger.info("尺寸调整，使用质量60%")
            else:
                # 正常文件使用中低质量
                quality = 65
                logger.info("正常文件，使用质量65%")
            
            image.save(output, format='JPEG', quality=quality, optimize=True)
            processed_data = output.getvalue()
            
            processed_size = len(processed_data)
            logger.info(f"处理后图片大小: {processed_size / 1024 / 1024:.2f} MB")
            
            # 最终检查文件大小
            if processed_size > self.max_file_size:
                logger.warning("处理后文件仍然过大，进行进一步压缩")
                output = BytesIO()
                image.save(output, format='JPEG', quality=75, optimize=True)
                processed_data = output.getvalue()
                logger.info(f"最终图片大小: {len(processed_data) / 1024 / 1024:.2f} MB")
            
            # 检查base64编码后的大小 (重要!)
            import base64
            base64_size = len(base64.b64encode(processed_data))
            logger.info(f"base64编码大小: {base64_size / 1024 / 1024:.2f} MB")
            
            if base64_size > self.max_base64_size:
                logger.warning("base64编码过大，进行激进压缩")
                # 激进压缩模式 - 更严格的策略
                quality = 50  # 从更低质量开始
                while base64_size > self.max_base64_size and quality >= 20:
                    output = BytesIO()
                    image.save(output, format='JPEG', quality=quality, optimize=True)
                    processed_data = output.getvalue()
                    base64_size = len(base64.b64encode(processed_data))
                    logger.info(f"激进压缩-质量{quality}%: 文件{len(processed_data)/1024/1024:.2f}MB, base64:{base64_size/1024/1024:.2f}MB")
                    quality -= 5  # 更小的步长
                
                # 如果还是太大，尝试进一步缩小尺寸
                if base64_size > self.max_base64_size:
                    logger.warning("继续缩小图片尺寸")
                    scale_factor = 0.8
                    while base64_size > self.max_base64_size and scale_factor >= 0.5:
                        new_size = (int(image.size[0] * scale_factor), int(image.size[1] * scale_factor))
                        resized_image = image.resize(new_size, Image.Resampling.LANCZOS)
                        output = BytesIO()
                        resized_image.save(output, format='JPEG', quality=60, optimize=True)
                        processed_data = output.getvalue()
                        base64_size = len(base64.b64encode(processed_data))
                        logger.info(f"尺寸缩放{scale_factor:.1f}: 尺寸{new_size}, 文件{len(processed_data)/1024/1024:.2f}MB, base64:{base64_size/1024/1024:.2f}MB")
                        scale_factor -= 0.1
                
                if base64_size > self.max_base64_size:
                    logger.error(f"无法将图片压缩到合适大小，当前base64: {base64_size/1024/1024:.2f}MB")
                    raise ValueError("图片过大，无法压缩到百度OCR要求的大小")
            
            return processed_data
            
        except Exception as e:
            logger.error(f"图像预处理失败: {e}")
            return image_data  # 返回原始数据
    
    def extract_pdf_images(self, pdf_data: bytes) -> List[bytes]:
        """从PDF提取图像页面"""
        try:
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            images = []
            
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                
                # 将页面渲染为图像
                mat = fitz.Matrix(2.0, 2.0)  # 提升分辨率
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("jpeg")
                images.append(img_data)
            
            doc.close()
            return images
            
        except Exception as e:
            logger.error(f"PDF图像提取失败: {e}")
            return []

class MedicalTextCorrector:
    """医学文本智能纠错系统"""
    
    def __init__(self):
        """初始化医学文本纠错器"""
        # 常见OCR错误映射（基于实际使用经验）
        self.common_ocr_errors = {
            # 中药名称常见错误
            "当归": ["当归", "当归", "当帰", "当归"],
            "黄芪": ["黄芪", "黄芪", "黄芩", "黄蓍"],
            "人参": ["人参", "人参", "人蔘", "人森"],
            "白术": ["白术", "白术", "白术", "白朮"],
            "茯苓": ["茯苓", "茯苓", "茯灵", "伏苓"],
            "甘草": ["甘草", "甘草", "甘早", "甘萆"],
            "川芎": ["川芎", "川芎", "川弓", "川穹"],
            "当归": ["当归", "当帰", "當歸"],
            "红花": ["红花", "红花", "紅花", "红华"],
            "桃仁": ["桃仁", "桃仁", "桃人", "挑仁"],
            
            # 剂量单位常见错误
            "克": ["克", "g", "兟", "窩"],
            "毫升": ["毫升", "ml", "豪升", "毫开"],
            "片": ["片", "片", "斤", "斤"],
            "粒": ["粒", "粒", "粒", "立"],
            
            # 用法用量
            "水煎服": ["水煎服", "水前服", "水箭服", "水剑服"],
            "每日": ["每日", "每目", "每曰", "每々"],
            "分服": ["分服", "分服", "份服", "分腹"],
            "温服": ["温服", "溫服", "温腹", "湿服"],
            
            # 医学术语
            "证候": ["证候", "症候", "征候", "証候"],
            "方剂": ["方剂", "方剂", "方齐", "芳剂"],
            "配伍": ["配伍", "配伍", "配午", "配五"],
        }
        
        # 构建反向映射表
        self.correction_map = {}
        for correct, errors in self.common_ocr_errors.items():
            for error in errors:
                if error != correct:  # 排除正确的写法
                    self.correction_map[error] = correct
    
    def correct_medical_text(self, text: str) -> Tuple[str, List[str]]:
        """医学文本智能纠错"""
        try:
            corrected_text = text
            corrections = []
            
            # 1. 基于字典的纠错
            for error, correct in self.correction_map.items():
                if error in corrected_text:
                    corrected_text = corrected_text.replace(error, correct)
                    corrections.append(f"{error} → {correct}")
            
            # 2. 剂量格式标准化
            # 匹配各种剂量格式: 10g, 10 g, 10克, 十克等
            dose_patterns = [
                (r'(\d+)\s*克', r'\1g'),
                (r'(\d+)\s*毫升', r'\1ml'),
                (r'(\d+)\s*钱', r'\1g'),  # 1钱约等于3g，这里简化处理
                (r'([一二三四五六七八九十]+)克', self._chinese_num_to_g),
                (r'(\d+)-(\d+)\s*g', r'\1-\2g'),  # 规范化范围表示
            ]
            
            for pattern, replacement in dose_patterns:
                if callable(replacement):
                    corrected_text = re.sub(pattern, replacement, corrected_text)
                else:
                    old_text = corrected_text
                    corrected_text = re.sub(pattern, replacement, corrected_text)
                    if old_text != corrected_text:
                        corrections.append("剂量格式标准化")
            
            # 3. 中药名称完整性检查
            corrected_text = self._fix_incomplete_herb_names(corrected_text, corrections)
            
            return corrected_text, corrections
            
        except Exception as e:
            logger.error(f"医学文本纠错失败: {e}")
            return text, []
    
    def _chinese_num_to_g(self, match) -> str:
        """中文数字转换为阿拉伯数字+g"""
        chinese_nums = {
            '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
            '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'
        }
        chinese_num = match.group(1)
        arabic_num = chinese_nums.get(chinese_num, chinese_num)
        return f"{arabic_num}g"
    
    def _fix_incomplete_herb_names(self, text: str, corrections: List[str]) -> str:
        """修复不完整的药名识别"""
        # 常见的不完整药名模式
        incomplete_patterns = {
            r'当\s*归': '当归',
            r'黄\s*芪': '黄芪',
            r'人\s*参': '人参',
            r'白\s*术': '白术',
            r'茯\s*苓': '茯苓',
            r'川\s*芎': '川芎',
            r'红\s*花': '红花',
            r'桃\s*仁': '桃仁',
        }
        
        for pattern, replacement in incomplete_patterns.items():
            old_text = text
            text = re.sub(pattern, replacement, text)
            if old_text != text:
                corrections.append(f"修复药名: {replacement}")
        
        return text

class BaiduOCRService:
    """百度OCR服务接口"""
    
    def __init__(self):
        """初始化百度OCR服务"""
        # 密钥统一从 config/settings.py 读取（已兼容 BAIDU_* 历史变量）
        self.api_key = AI_CONFIG.get("baidu_ocr_api_key", "")
        self.secret_key = AI_CONFIG.get("baidu_ocr_secret_key", "")
        
        # 如果没有设置，使用测试密钥（实际生产中应该设置真实密钥）
        if not self.api_key or not self.secret_key:
            logger.warning("百度OCR密钥未设置，使用测试模式")
            self.api_key = "your_baidu_api_key"
            self.secret_key = "your_baidu_secret_key"
        
        self.access_token = None
        self.token_expires_at = 0
    
    def get_access_token(self) -> Optional[str]:
        """获取百度API访问令牌"""
        try:
            current_time = datetime.now().timestamp()
            
            # 如果token还有效，直接返回
            if self.access_token and current_time < self.token_expires_at:
                return self.access_token
            
            # 获取新的access_token
            url = "https://aip.baidubce.com/oauth/2.0/token"
            params = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key
            }
            
            response = requests.post(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                self.token_expires_at = current_time + expires_in - 300  # 提前5分钟过期
                return self.access_token
            else:
                logger.error(f"获取百度access_token失败: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"获取百度access_token异常: {e}")
            return None
    
    def recognize_text(self, image_data: bytes) -> OCRResult:
        """使用百度OCR识别图片文字"""
        try:
            start_time = datetime.now()
            
            # 获取访问令牌
            access_token = self.get_access_token()
            if not access_token:
                return OCRResult(text="", confidence=0.0)
            
            # 准备请求 - 使用高精度版本
            url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={access_token}"
            
            # 图片转base64并记录信息
            image_b64 = base64.b64encode(image_data).decode()
            
            # 记录图片信息用于调试
            file_size = len(image_data)
            base64_size = len(image_b64)
            logger.info(f"百度OCR请求: 文件{file_size/1024:.1f}KB, base64:{base64_size/1024:.1f}KB")
            
            # 检查是否有明显问题
            if file_size < 1000:  # 小于1KB
                logger.warning(f"图片文件过小 ({file_size} bytes)，可能导致识别失败")
            elif base64_size > 5 * 1024 * 1024:  # 大于5MB base64
                logger.warning(f"base64编码过大 ({base64_size/1024/1024:.1f}MB)，可能导致识别失败")
            
            data = {
                "image": image_b64,
                "detect_direction": "false",     # 关闭朝向检测(高精度版推荐)
                "vertexes_location": "true",     # 返回文字位置信息
                "paragraph": "false",            # 不合并段落
                "probability": "true",           # 返回置信度
                "char_probability": "false",     # 不返回单字置信度
                "multidirectional_recognize": "false"  # 关闭多方向识别
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # 发送请求
            response = requests.post(url, data=data, headers=headers, timeout=30)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if response.status_code == 200:
                result = response.json()
                
                # 记录API响应详情用于调试
                logger.info(f"百度OCR API响应: {result}")
                
                if "words_result" in result:
                    # 提取识别的文字
                    text_lines = []
                    total_confidence = 0
                    word_count = 0
                    words_info = []
                    
                    for item in result["words_result"]:
                        words = item.get("words", "")
                        if words.strip():
                            text_lines.append(words.strip())
                            
                            # 收集置信度信息
                            if "probability" in item:
                                confidence_info = item["probability"]
                                avg_confidence = confidence_info.get("average", 0)
                                total_confidence += avg_confidence
                                word_count += 1
                                
                                words_info.append({
                                    "text": words,
                                    "confidence": avg_confidence
                                })
                    
                    full_text = "\n".join(text_lines)
                    avg_confidence = total_confidence / word_count if word_count > 0 else 0
                    
                    return OCRResult(
                        text=full_text,
                        confidence=avg_confidence / 100.0,  # 转换为0-1范围
                        words_info=words_info,
                        processing_time=processing_time
                    )
                else:
                    error_msg = result.get("error_msg", "未知错误")
                    logger.error(f"百度OCR识别失败: {error_msg}")
                    return OCRResult(text="", confidence=0.0, processing_time=processing_time)
            
            else:
                logger.error(f"百度OCR API请求失败: {response.status_code}, {response.text}")
                return OCRResult(text="", confidence=0.0, processing_time=processing_time)
                
        except Exception as e:
            logger.error(f"百度OCR识别异常: {e}")
            return OCRResult(text="", confidence=0.0)

class PrescriptionOCRSystem:
    """处方OCR识别主系统 - 支持多OCR服务商"""
    
    def __init__(self, primary_service='baidu'):
        """初始化OCR系统"""
        self.image_processor = PrescriptionImageProcessor()
        self.text_corrector = MedicalTextCorrector()
        
        # 支持多个OCR服务商
        self.ocr_services = {
            'baidu': BaiduOCRService(),
            # 'tencent': TencentOCRService(),  # 待扩展
            # 'ali': AliOCRService(),          # 待扩展  
        }
        self.primary_service = primary_service
        self.fallback_services = [s for s in self.ocr_services.keys() if s != primary_service]
        
        # 统计信息
        self.stats = {
            "total_processed": 0,
            "success_count": 0,
            "average_confidence": 0.0,
            "average_processing_time": 0.0
        }
    
    def process_image(self, image_data: bytes, filename: str = None) -> Dict[str, Any]:
        """处理单张图片的OCR识别"""
        try:
            start_time = datetime.now()
            
            # 1. 增强图像预处理
            try:
                from enhanced_image_preprocessor import get_enhanced_image_preprocessor
                enhanced_processor = get_enhanced_image_preprocessor()
                processed_image = enhanced_processor.process_prescription_image(image_data)
                logger.info("使用增强图像预处理器")
            except ImportError:
                # 回退到原始预处理器
                processed_image = self.image_processor.preprocess_image(image_data)
                logger.info("使用原始图像预处理器")
            
            # 2. OCR文字识别 (支持服务降级)
            ocr_result = self._recognize_with_fallback(processed_image)
            
            if not ocr_result.text.strip():
                return {
                    "success": False,
                    "error": "无法从图片中识别到文字",
                    "confidence": 0.0
                }
            
            # 3. 医学文本纠错
            corrected_text, corrections = self.text_corrector.correct_medical_text(ocr_result.text)
            ocr_result.corrected_text = corrected_text
            
            # 4. 更新统计信息
            self._update_stats(ocr_result)
            
            total_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "original_text": ocr_result.text,
                "corrected_text": ocr_result.corrected_text,
                "confidence": round(ocr_result.confidence, 3),
                "corrections_made": corrections,
                "words_info": ocr_result.words_info,
                "processing_time": round(total_time, 2),
                "filename": filename or "uploaded_image"
            }
            
        except Exception as e:
            logger.error(f"图片OCR处理失败: {e}")
            return {
                "success": False,
                "error": f"图片处理失败: {str(e)}",
                "confidence": 0.0
            }
    
    def process_pdf(self, pdf_data: bytes, filename: str = None) -> Dict[str, Any]:
        """处理PDF文档的OCR识别"""
        try:
            # 1. 从PDF提取图像
            images = self.image_processor.extract_pdf_images(pdf_data)
            
            if not images:
                return {
                    "success": False,
                    "error": "无法从PDF中提取图像",
                    "pages": 0
                }
            
            # 2. 处理每一页
            pages_result = []
            combined_text = []
            total_confidence = 0
            
            for i, image_data in enumerate(images):
                page_result = self.process_image(image_data, f"{filename}_page_{i+1}")
                pages_result.append({
                    "page": i + 1,
                    "result": page_result
                })
                
                if page_result["success"]:
                    combined_text.append(f"=== 第{i+1}页 ===")
                    combined_text.append(page_result["corrected_text"])
                    total_confidence += page_result["confidence"]
            
            success_pages = len([r for r in pages_result if r["result"]["success"]])
            avg_confidence = total_confidence / success_pages if success_pages > 0 else 0
            
            return {
                "success": success_pages > 0,
                "total_pages": len(images),
                "success_pages": success_pages,
                "combined_text": "\n\n".join(combined_text),
                "pages_detail": pages_result,
                "average_confidence": round(avg_confidence, 3),
                "filename": filename or "uploaded_pdf"
            }
            
        except Exception as e:
            logger.error(f"PDF OCR处理失败: {e}")
            return {
                "success": False,
                "error": f"PDF处理失败: {str(e)}",
                "pages": 0
            }
    
    def _update_stats(self, ocr_result: OCRResult):
        """更新系统统计信息"""
        self.stats["total_processed"] += 1
        if ocr_result.text.strip():
            self.stats["success_count"] += 1
        
        # 更新平均置信度
        total_confidence = self.stats["average_confidence"] * (self.stats["total_processed"] - 1)
        total_confidence += ocr_result.confidence
        self.stats["average_confidence"] = total_confidence / self.stats["total_processed"]
        
        # 更新平均处理时间
        if ocr_result.processing_time:
            total_time = self.stats["average_processing_time"] * (self.stats["total_processed"] - 1)
            total_time += ocr_result.processing_time
            self.stats["average_processing_time"] = total_time / self.stats["total_processed"]
    
    def _recognize_with_fallback(self, image_data: bytes) -> OCRResult:
        """带降级的OCR识别"""
        services_to_try = [self.primary_service] + self.fallback_services
        
        for service_name in services_to_try:
            try:
                if service_name in self.ocr_services:
                    service = self.ocr_services[service_name]
                    result = service.recognize_text(image_data)
                    
                    # 如果置信度足够高，直接返回
                    if result.confidence > 0.01:
                        logger.info(f"OCR识别成功，使用服务: {service_name}")
                        return result
                    
                    # 置信度较低但有结果，继续尝试其他服务
                    if result.text.strip():
                        logger.info(f"{service_name} OCR置信度: {result.confidence} (内容长度: {len(result.text)})")
                        return result  # 目前只有百度服务，直接返回
                        
            except Exception as e:
                logger.warning(f"{service_name} OCR识别失败: {e}")
                continue
        
        # 所有服务都失败，返回空结果
        logger.error("所有OCR服务都失败")
        return OCRResult(text="", confidence=0.0)
    

    def _assess_content_quality(self, text: str) -> float:
        """评估OCR识别内容的质量"""
        if not text.strip():
            return 0.0
        
        quality_score = 0.0
        
        # 1. 中文字符比例
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        if len(text) > 0:
            chinese_ratio = chinese_chars / len(text)
            quality_score += chinese_ratio * 0.3
        
        # 2. 医学相关关键词
        medical_keywords = ['克', 'g', '净', '帖', '剂', '服', '方', '药', '治', '症']
        keyword_count = sum(1 for kw in medical_keywords if kw in text)
        quality_score += min(keyword_count / 5, 1.0) * 0.3
        
        # 3. 数字和剂量信息
        if re.search(r'\d+(?:\.\d+)?\s*[克g]', text):
            quality_score += 0.2
        
        # 4. 中药名称模式
        herb_patterns = [
            r'[一-龯]{2,4}（净）',  # 如：桔梗（净）
            r'[一-龯]{2,4}\s*\d+[克g]',  # 如：甘草 6克
            r'炒[一-龯]{2,4}',  # 如：炒莱菔子
        ]
        for pattern in herb_patterns:
            if re.search(pattern, text):
                quality_score += 0.1
        
        # 5. 文本长度合理性
        if 50 <= len(text) <= 2000:
            quality_score += 0.1
        
        return min(quality_score, 1.0)
    def switch_primary_service(self, service_name: str):
        """切换主要OCR服务"""
        if service_name in self.ocr_services:
            self.primary_service = service_name
            self.fallback_services = [s for s in self.ocr_services.keys() if s != service_name]
            logger.info(f"主OCR服务已切换至: {service_name}")
            return True
        return False

    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return {
            "total_processed": self.stats["total_processed"],
            "success_count": self.stats["success_count"],
            "success_rate": round(self.stats["success_count"] / max(1, self.stats["total_processed"]), 3),
            "average_confidence": round(self.stats["average_confidence"], 3),
            "average_processing_time": round(self.stats["average_processing_time"], 2),
            "primary_service": self.primary_service,
            "available_services": list(self.ocr_services.keys())
        }

# 全局OCR系统实例
ocr_system = None

def get_ocr_system():
    """获取全局OCR系统实例"""
    global ocr_system
    if ocr_system is None:
        ocr_system = PrescriptionOCRSystem()
    return ocr_system

# 测试函数
def test_ocr_system():
    """测试OCR系统功能"""
    print("=== 测试处方OCR识别系统 ===")
    
    ocr = get_ocr_system()
    
    # 测试图像预处理
    processor = PrescriptionImageProcessor()
    print(f"✅ 图像处理器初始化成功")
    print(f"   支持格式: {processor.supported_formats}")
    print(f"   最大尺寸: {processor.max_size}")
    
    # 测试医学文本纠错
    corrector = MedicalTextCorrector()
    test_text = "當帰 12兟，黄芪 15克，人蔘 9g，白朮 10g，水前服"
    corrected, corrections = corrector.correct_medical_text(test_text)
    print(f"\n✅ 医学文本纠错测试:")
    print(f"   原文: {test_text}")
    print(f"   纠错: {corrected}")
    print(f"   修正: {corrections}")
    
    # 显示系统统计
    stats = ocr.get_system_stats()
    print(f"\n📊 系统统计: {stats}")
    
    print("\n🚀 OCR系统初始化完成，等待API集成...")

if __name__ == "__main__":
    test_ocr_system()
