"""
处方格式强制执行器
确保AI生成的处方包含具体剂量信息
v1.0 - 2025-09-25
"""

import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class PrescriptionFormatEnforcer:
    """处方格式强制执行器"""
    
    def __init__(self):
        # 常用中药默认剂量（克）
        self.default_dosages = {
            # 补气药
            '人参': 10, '党参': 15, '黄芪': 20, '白术': 12, '茯苓': 15, '甘草': 6,
            '山药': 15, '大枣': 10, '蜂蜜': 30,
            
            # 补血药
            '当归': 10, '熟地': 15, '白芍': 12, '川芎': 6, '阿胶': 10,
            
            # 补阴药
            '生地': 15, '麦冬': 12, '天冬': 10, '玄参': 12, '石斛': 12,
            '枸杞子': 12, '女贞子': 12, '旱莲草': 10,
            
            # 补阳药
            '附子': 6, '肉桂': 3, '干姜': 6, '淫羊藿': 12, '巴戟天': 10,
            '杜仲': 12, '续断': 12, '骨碎补': 15,
            
            # 解表药
            '麻黄': 6, '桂枝': 6, '紫苏叶': 10, '生姜': 6, '薄荷': 6,
            '柴胡': 10, '升麻': 6, '葛根': 15,
            
            # 清热药
            '石膏': 30, '知母': 12, '黄连': 6, '黄芩': 10, '黄柏': 10,
            '栀子': 10, '连翘': 12, '金银花': 15, '板蓝根': 15,
            
            # 泻下药
            '大黄': 6, '芒硝': 10, '火麻仁': 15,
            
            # 祛湿药
            '苍术': 10, '厚朴': 10, '陈皮': 9, '半夏': 9, '茯苓': 15,
            '泽泻': 12, '车前子': 12, '薏苡仁': 20,
            
            # 理气药
            '木香': 6, '枳实': 10, '枳壳': 10, '香附': 10, '佛手': 10,
            
            # 活血药
            '红花': 6, '桃仁': 10, '川芎': 6, '赤芍': 12, '丹参': 15,
            
            # 安神药
            '酸枣仁': 15, '远志': 6, '龙骨': 20, '牡蛎': 20, '朱砂': 1,
            
            # 其他常用药
            '桔梗': 6, '杏仁': 10, '枇杷叶': 10, '川贝母': 10, '百合': 20,
            '五味子': 6, '山茱萸': 12, '牡丹皮': 10, '地骨皮': 12,
        }
        
        logger.info("处方格式强制执行器初始化完成")
    
    def enforce_prescription_format(self, ai_response: str) -> str:
        """
        强制执行处方格式，确保包含具体剂量
        
        Args:
            ai_response: AI原始回复
            
        Returns:
            str: 格式化后的回复（包含具体剂量）
        """
        if not self._contains_prescription(ai_response):
            return ai_response
        
        logger.info("检测到处方内容，开始格式强制执行")
        
        # 查找并修复缺少剂量的药材
        fixed_response = self._fix_missing_dosages(ai_response)
        
        # 验证修复结果
        herb_count_before = len(self._extract_incomplete_herbs(ai_response))
        herb_count_after = len(self._extract_incomplete_herbs(fixed_response))
        
        logger.info(f"处方格式修复完成: 修复前{herb_count_before}个缺少剂量的药材，修复后{herb_count_after}个")
        
        return fixed_response
    
    def _contains_prescription(self, text: str) -> bool:
        """检查是否包含处方"""
        prescription_keywords = [
            '处方如下', '方剂组成', '药物组成', '具体方药', '处方建议', '处方组成',
            '君药', '臣药', '佐药', '使药', '方解', '治疗方案', '用药方案'
        ]
        
        # 也检查是否有列表格式的药材（作为处方的强指示器）
        herb_list_pattern = r'[-•*]\s*[一-龟\u4e00-\u9fff]{2,6}'
        herb_matches = re.findall(herb_list_pattern, text)
        confirmed_herbs = [match.strip('- •*') for match in herb_matches 
                          if match.strip('- •*') in self.default_dosages]
        
        # 如果有确认的药材列表，也认为包含处方
        return any(keyword in text for keyword in prescription_keywords) or len(confirmed_herbs) >= 3
    
    def _extract_incomplete_herbs(self, text: str) -> List[str]:
        """提取缺少剂量的药材"""
        incomplete_herbs = []
        
        # 匹配 "药材名 g" 或 "药材名g" 格式（没有具体数字）- 改进避免误匹配
        pattern = r'([一-龟\u4e00-\u9fff]{2,6})\s*[gG克](?!\d)(?![\u4e00-\u9fff])'
        matches = re.findall(pattern, text)
        # 只保留确认的药材名
        confirmed_matches = [match for match in matches if match in self.default_dosages]
        incomplete_herbs.extend(confirmed_matches)
        
        # 匹配 "- 药材名" 格式（列表中没有剂量的药材）- 只匹配确认的药材
        pattern2 = r'[-•*]\s*([一-龟\u4e00-\u9fff]{2,6})(?!\s*[\d克gG])(?=\s|$|\n)'
        matches2 = re.findall(pattern2, text)
        confirmed_matches2 = [match for match in matches2 if match in self.default_dosages]
        incomplete_herbs.extend(confirmed_matches2)
        
        return list(set(incomplete_herbs))  # 去重
    
    def _fix_missing_dosages(self, text: str) -> str:
        """修复缺少剂量的药材"""
        fixed_text = text
        
        # 修复 "药材名 g" 格式
        def replace_herb_g(match):
            herb_name = match.group(1)
            dosage = self.default_dosages.get(herb_name, 12)  # 默认12g
            return f"{herb_name} {dosage}g"
        
        # 修复 "药材名g" 格式 - 改进正则表达式，避免误匹配
        pattern1 = r'([一-龟\u4e00-\u9fff]{2,6})\s*[gG克](?!\d)(?![\u4e00-\u9fff])'
        fixed_text = re.sub(pattern1, replace_herb_g, fixed_text)
        
        # 修复列表格式 "- 药材名" - 确保药材名后面没有数字或单位
        def replace_list_herb(match):
            prefix = match.group(1)  # "- " 或 "* "
            herb_name = match.group(2)
            # 检查是否在默认药材列表中
            if herb_name in self.default_dosages:
                dosage = self.default_dosages.get(herb_name, 12)
                return f"{prefix}{herb_name} {dosage}g"
            else:
                # 如果不在药材列表中，可能不是药材，不修改
                return match.group(0)
        
        # 匹配列表格式，包括行结尾的情况
        pattern2 = r'([-•*]\s*)([一-龟\u4e00-\u9fff]{2,6})(?!\s*[\d克gG])(?=\s|$|\n)'
        fixed_text = re.sub(pattern2, replace_list_herb, fixed_text)
        
        # 修复纯药材名（在换行符后，可能是处方列表）
        def replace_pure_herb(match):
            herb_name = match.group(1)
            # 只修复确认的药材名
            if herb_name in self.default_dosages:
                dosage = self.default_dosages.get(herb_name, 12)
                return f"{herb_name} {dosage}g"
            else:
                return match.group(0)
        
        # 匹配换行符后的纯药材名（2-6个汉字，后面是换行符或结尾）
        pattern3 = r'\n([一-龟\u4e00-\u9fff]{2,6})(?=\n|$)'
        fixed_text = re.sub(pattern3, lambda m: f"\n{replace_pure_herb(m).strip()}", fixed_text)
        
        return fixed_text
    
    def _fix_other_formats(self, text: str) -> str:
        """修复其他格式的药材剂量缺失"""
        # 可以根据需要添加更多格式的处理
        return text
    
    def add_prescription_format_prompt(self) -> str:
        """生成处方格式提示词"""
        return '''
**🔥 重要：处方格式强制要求 🔥**

当您需要给出处方时，必须严格按照以下格式：

【处方建议】
人参 10克
黄芪 20克  
白术 12克
茯苓 15克
甘草 6克
...

**强制要求：**
1. 每个药材必须包含具体剂量数字，如"人参 10克"
2. 绝对禁止只写"人参 克"或"人参 g"
3. 剂量范围：一般3-30克，石膏等可用30-60克
4. 单位统一使用"克"或"g"

**错误示例❌：**
- 人参 g
- 黄芪 克  
- 白术

**正确示例✅：**
- 人参 10克
- 黄芪 20克
- 白术 12克

请确保您的每个处方都包含具体的药材剂量！
'''

# 全局实例
_prescription_enforcer = None

def get_prescription_enforcer() -> PrescriptionFormatEnforcer:
    """获取处方格式强制执行器实例"""
    global _prescription_enforcer
    if _prescription_enforcer is None:
        _prescription_enforcer = PrescriptionFormatEnforcer()
    return _prescription_enforcer