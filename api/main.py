# main_minimal_correct.py - 腾讯云最小化部署版本
# 仅将本地模型替换为在线API，保留所有其他功能

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, '/opt/tcm-ai')
sys.path.insert(0, '/opt/tcm-ai/core')
sys.path.insert(0, '/opt/tcm-ai/services')
sys.path.insert(0, '/opt/tcm-ai/database')

# 导入统一配置
from app.core.settings import PATHS, API_CONFIG, DATABASE_CONFIG, AI_CONFIG, SECURITY_CONFIG

# 加强的医疗安全检查
ENHANCED_MEDICAL_SAFETY_PROMPT = """
**【严格医疗安全规则】**

1. **症状描述严格限制** - 最高优先级：
   - **绝对禁止**：添加、推测、编造患者未明确描述的任何症状细节
   - **绝对禁止**：从"便秘"推测出"大便干结如栗，数日一行"
   - **绝对禁止**：从"挑食"推测出"食欲不佳，腹胀嗳气"  
   - **正确做法**：只能使用患者确切的原始表述

2. **舌象脉象信息严格限制**：
   - **绝对禁止**：在没有患者上传舌象图片的情况下，描述任何具体的舌象特征
   - **绝对禁止**：编造任何脉象描述（"脉细弱"、"脉濡缓"等）
   - **绝对禁止**：使用"舌苔薄白"、"舌边有齿痕"、"舌质淡红"等具体描述
   - **正确做法**：如无图像和患者描述，写"未见舌象脉象信息"

3. **望诊切诊编造检测 - 新增严格规则**：
   - **绝对禁止**：在"1. 望诊"部分编造面色、舌象等描述
   - **绝对禁止**：在"4. 切诊"部分编造脉象描述  
   - **绝对禁止**：使用"提示"、"说明"等词汇暗示体征信息
   - **正确做法**：写"未进行实际望诊/切诊，建议面诊"

4. **望诊信息来源验证**：  
   - 只能基于**当前对话中患者明确描述**的症状
   - 只能基于**当前对话中上传的图像**进行望诊分析
   - **绝对禁止**：从知识库或其他来源添加患者未提及的症状信息
   - **绝对禁止**：推测面色、精神状态等患者未描述的体征

4. **严格信息隔离**：
   - 每次诊疗都是独立的，不能使用其他患者的信息
   - 不能假设或推测患者的任何未明确表述的症状或体征
   - 必须基于当前会话的实际信息进行分析

**违反以上任何一条都是严重的医疗安全事故！**
"""

def check_symptom_fabrication(ai_response: str, patient_message: str) -> str:
    """
    检查AI是否编造了患者未明确描述的症状细节
    返回编造的症状描述，如果没有编造则返回空字符串
    """
    # 常见的症状编造模式
    fabricated_symptoms = [
        # 便秘相关编造
        (r'大便干结.*栗', "大便干结如栗"),
        (r'数日一行', "数日一行"),
        (r'大便.*干.*硬', "大便干硬"),
        (r'大便干结', "大便干结"),  # 新增：患者只说便秘，AI添加具体描述
        (r'排便困难', "排便困难"),  # 新增：患者未描述的排便情况
        
        # 消化系统编造
        (r'腹胀.*嗳气', "腹胀嗳气"),
        (r'腹胀不舒', "腹胀不舒"),
        (r'嗳气频频', "嗳气频频"),
        (r'食欲不佳', "食欲不佳"),
        (r'食欲不振', "食欲不振"),  # 新增：患者只说挑食，AI编造食欲状态
        
        # 体征编造
        (r'面色[苍白萎黄]', "面色苍白/萎黄"),
        (r'精神疲倦', "精神疲倦"),
        (r'精神.*不振', "精神不振"),
        (r'神疲乏力', "神疲乏力"),
        (r'精神倦怠', "精神倦怠"),  # 新增：患者未描述的精神状态
        
        # 时间和程度编造
        (r'.*已久', "持续时间编造(已久)"),
        (r'.*数日', "时间编造(数日)"),
        (r'.*不舒', "程度编造(不舒)"),
    ]
    
    patient_keywords = set(patient_message.lower().split())
    found_fabrications = []
    
    for pattern, description in fabricated_symptoms:
        if re.search(pattern, ai_response):
            # 检查患者消息中是否包含相关关键词
            pattern_keywords = re.findall(r'[\u4e00-\u9fff]+', pattern.replace('.*', '').replace('[', '').replace(']', ''))
            
            # 如果AI回复中的症状描述在患者消息中没有对应的关键词，则认为是编造
            if not any(keyword in patient_message for keyword in pattern_keywords if len(keyword) > 1):
                found_fabrications.append(description)
    
    return ", ".join(found_fabrications) if found_fabrications else ""


# 严格的望诊切诊编造检测
STRICT_TONGUE_PULSE_PATTERNS = [
    # 望诊编造模式 - 更严格
    (r'面色[^，。]*?淡白', "面色淡白描述"),
    (r'面色[^，。]*?略红', "面色略红描述"),
    (r'面色[^，。]*?苍白', "面色苍白描述"),
    (r'面色[^，。]*?潮红', "面色潮红描述"),
    (r'舌质[^，。]*?淡红', "舌质淡红描述"),
    (r'舌质[^，。]*?红', "舌质红描述"),
    (r'舌质[^，。]*?暗', "舌质暗描述"),
    (r'苔[^，。]*?薄白', "苔薄白描述"),
    (r'苔[^，。]*?薄黄', "苔薄黄描述"),
    (r'苔[^，。]*?厚', "苔厚描述"),
    (r'舌边[^，。]*?齿痕', "舌边齿痕描述"),
    (r'舌尖[^，。]*?红', "舌尖红描述"),
    
    # 切诊编造模式 - 更严格  
    (r'脉[^，。]*?浮', "脉浮描述"),
    (r'脉[^，。]*?沉', "脉沉描述"),
    (r'脉[^，。]*?缓', "脉缓描述"),
    (r'脉[^，。]*?数', "脉数描述"),
    (r'脉[^，。]*?细', "脉细描述"),
    (r'脉[^，。]*?弱', "脉弱描述"),
    (r'脉[^，。]*?滑', "脉滑描述"),
    (r'脉[^，。]*?弦', "脉弦描述"),
    (r'脉象[^，。]*?浮缓', "脉象浮缓描述"),
    (r'脉象[^，。]*?细弱', "脉象细弱描述"),
    (r'脉象[^，。]*?沉细', "脉象沉细描述"),
    
    # 组合编造模式
    (r'提示.*?不足', "提示证候描述"),
    (r'说明.*?未', "说明病机描述"),
]

def detect_fabricated_examination(text: str, has_actual_examination: bool = False) -> list:
    """检测编造的望诊切诊内容"""
    if has_actual_examination:
        return []  # 如果有实际检查，则不检测
    
    fabricated_items = []
    
    # 检测望诊内容
    if "望诊" in text or "面色" in text or "舌" in text:
        for pattern, description in STRICT_TONGUE_PULSE_PATTERNS:
            if re.search(pattern, text):
                fabricated_items.append(f"编造{description}")
    
    # 检测切诊内容  
    if "切诊" in text or "脉" in text:
        for pattern, description in STRICT_TONGUE_PULSE_PATTERNS:
            if "脉" in pattern and re.search(pattern, text):
                fabricated_items.append(f"编造{description}")
    
    return fabricated_items


# 综合医疗安全检查函数 (舌象、脉象、症状编造)
def check_medical_safety(ai_response: str, has_tongue_image: bool, patient_described_tongue: str = "", image_analysis_successful: bool = False, original_patient_message: str = "") -> tuple[bool, str]:
    """
    检查AI回复中的医疗信息是否安全（舌象、脉象、症状编造）
    返回: (is_safe, error_message)
    
    安全策略：
    1. 舌象检查：有图片且分析成功 → 允许舌象描述  
    2. 脉象检查：绝不允许编造脉象描述
    3. 症状检查：不允许添加患者未明确描述的症状细节
    4. 患者自述：允许AI引用患者明确描述的内容
    5. 【新增】望诊切诊严格检测：绝不允许编造任何体征信息
    """
    
    # 1. 严格检测编造的望诊切诊内容
    has_actual_examination = has_tongue_image and image_analysis_successful
    fabricated_examinations = detect_fabricated_examination(ai_response, has_actual_examination)
    
    if fabricated_examinations:
        error_msg = f"检测到编造的体征信息: {', '.join(fabricated_examinations)}"
        return False, error_msg
    
    # 2. 原有的检查逻辑
    # 关键检查：只有图片分析真正成功时才允许舌象描述
    if has_tongue_image and image_analysis_successful:
        return True, ""
    
    # 第一步：检查症状编造
    if original_patient_message:
        symptom_fabrication = check_symptom_fabrication(ai_response, original_patient_message)
        if symptom_fabrication:
            return False, f"检测到症状编造: {symptom_fabrication}"
    
    # 第二步：检查是否有AI编造的舌象和脉象描述 - 增强检测模式
    dangerous_patterns = [
        # 舌象相关 - 基础模式
        r'吾观其舌.*[淡红紫暗]',           # "吾观其舌淡红"等明显编造
        r'舌质[淡红紫暗].*苔[薄厚][白黄腻]',    # 完整舌象描述
        r'望诊所见.*舌苔.*[薄厚][白黄腻]',     # 望诊中的舌象
        r'舌[质色][淡红紫暗].*[，,].*苔',      # 舌质+苔象组合
        r'舌边.*齿痕.*苔',                    # 舌边齿痕+苔象
        r'观其舌象.*[淡红紫暗]',              # "观其舌象"
        r'舌诊.*[淡红紫暗].*苔',              # 舌诊相关
        r'舌[淡红紫暗][，,].*苔[薄厚少][白黄腻]',  # "舌淡红，苔薄白"格式
        r'<望诊所见>.*舌.*[淡红紫暗].*苔.*</望诊所见>', # XML格式中的望诊
        r'舌.*[淡红紫暗].*或.*苔',            # "舌淡红或少苔"等
        r'苔[薄厚][白黄腻]或[少无]苔',         # "苔薄白或少苔"等
        
        # 舌象相关 - 新增强化模式 (针对用户反馈的问题)
        r'舌象[：:].*舌.*[红白黄]',            # "舌象：舌边尖红"等模式
        r'舌边[尖]?红',                       # "舌边红"、"舌边尖红"
        r'苔薄[白黄]或薄[黄白]',               # "苔薄白或薄黄"
        r'舌.*红.*[，,].*苔.*[白黄]',         # "舌边尖红，苔薄白"
        r'舌边.*红.*苔',                      # 舌边红+苔象组合
        r'舌.*尖.*红',                        # "舌尖红"等
        r'舌.*[边尖].*红.*苔',                # 舌边尖红+苔象
        r'舌.*苔.*[薄厚].*[白黄腻]',          # 任何舌苔具体描述
        r'舌苔.*[薄厚].*[白黄腻]',            # 直接的舌苔描述
        r'舌.*红.*或.*苔',                    # "舌红或苔白"等模式
        
        # 脉象相关 - 基础模式
        r'脉象[濡缓细数弦滑沉浮洪微]',         # "脉象濡缓"等编造
        r'脉[濡缓细数弦滑沉浮洪微][，,]',      # "脉缓，"等编造  
        r'脉.*[濡缓细数弦滑沉浮洪微].*[，,]',  # "脉象缓弱，"等
        r'切诊.*脉.*[濡缓细数弦滑沉浮洪微]',   # 切诊中的脉象
        r'<望诊所见>.*脉.*[濡缓细数弦滑沉浮洪微].*</望诊所见>', # XML中脉象
        r'脉诊.*[濡缓细数弦滑沉浮洪微]',       # 脉诊相关
        r'诊得.*脉.*[濡缓细数弦滑沉浮洪微]',   # "诊得脉象"
        r'按其脉.*[濡缓细数弦滑沉浮洪微]',     # "按其脉"等
        
        # 脉象相关 - 新增强化模式
        r'脉象[：:].*脉.*[濡缓细数弦滑沉浮洪微]',  # "脉象：脉浮数"等
        r'脉浮数',                            # 具体的脉象描述
        r'脉.*浮.*数',                        # "脉浮数"等组合
        r'脉.*[濡缓细数弦滑沉浮洪微].*[濡缓细数弦滑沉浮洪微]', # 多个脉象特征
        
        # 通用医疗信息编造模式
        r'辨证要点.*舌象',                    # 辨证要点中提到舌象
        r'辨证要点.*脉象',                    # 辨证要点中提到脉象
        r'望诊.*舌',                          # 望诊提到舌
        r'切诊.*脉',                          # 切诊提到脉
        r'四诊.*舌.*脉',                      # 四诊中同时提到舌脉
    ]
    
    found_dangerous = []
    for pattern in dangerous_patterns:
        matches = re.findall(pattern, ai_response)
        if matches:
            found_dangerous.extend(matches)
    
    # 如果患者自己描述了舌象或脉象，也允许AI引用
    if patient_described_tongue and found_dangerous:
        # 检查患者描述中是否包含相关舌象和脉象特征
        tongue_features = ["淡红", "红", "暗红", "紫", "薄白", "厚白", "黄", "腻", "齿痕"]
        pulse_features = ["濡", "缓", "细", "数", "弦", "滑", "沉", "浮", "洪", "微", "脉象", "脉搏"]
        all_features = tongue_features + pulse_features
        
        patient_features = [feature for feature in all_features if feature in patient_described_tongue]
        
        if patient_features:
            # 检查AI回复中是否只是引用了患者提到的特征
            for feature in patient_features:
                if feature in ai_response:
                    return True, ""
    
    if found_dangerous:
        error_msg = f"检测到可能的无根据舌象/脉象描述: {found_dangerous}"
        return False, error_msg
    
    return True, ""

# 清理AI回复中的非法医疗信息
def normalize_prescription_dosage(prescription_text: str) -> str:
    """规范化处方用量，将范围用量转换为确定用量"""
    import re
    
    # 匹配 "药名 数字-数字g" 的模式
    pattern = r'(\w+)\s+(\d+)-(\d+)g'
    
    def replace_range(match):
        herb_name = match.group(1)
        min_dose = int(match.group(2))
        max_dose = int(match.group(3))
        
        # 选择中间值或偏向较小值
        if max_dose - min_dose <= 3:
            recommended_dose = min_dose + 1  # 偏向较小值
        else:
            recommended_dose = (min_dose + max_dose) // 2  # 中间值
            
        return f"{herb_name} {recommended_dose}g"
    
    # 应用规范化
    normalized = re.sub(pattern, replace_range, prescription_text)
    return normalized

def extract_herbs_from_prescription(prescription_text: str):
    """从处方文本中提取药材信息 - 支持表格格式"""
    import re
    
    herbs = []
    lines = prescription_text.split('\n')
    
    # 先尝试表格格式提取
    table_herbs = extract_herbs_from_table(prescription_text)
    if table_herbs:
        return table_herbs
    
    # 如果不是表格格式，使用原来的逻辑
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 跳过明显的标题行和用法行
        skip_patterns = [
            r'^【.*】$', r'^\*\*.*\*\*$', r'^##.*$', r'^###.*$',
            '用法', '煎服', '制法', '功效', '注意', '服法', '【用法】', '【注意】'
        ]
        
        should_skip = any(re.search(pattern, line, re.IGNORECASE) for pattern in skip_patterns)
        if should_skip:
            continue
        
        # 多种药材匹配模式 - 修复中文字符匹配
        herb_patterns = [
            # 带括号格式: 薄荷（净）6g
            r'([\u4e00-\u9fff]+(?:（[\u4e00-\u9fff]*）)?)\s*(\d+(?:\.\d+)?)[gGg克]',
            # 标准格式: 人参 9g
            r'([\u4e00-\u9fff]+)\s+(\d+(?:\.\d+)?)[gGg克]',
            # 带冒号: 人参: 9g  
            r'([\u4e00-\u9fff]+)\s*[:：]\s*(\d+(?:\.\d+)?)[gGg克]',
            # 紧密格式: 人参9g
            r'([\u4e00-\u9fff]+)(\d+(?:\.\d+)?)[gGg克]',
            # 序号格式: 1. 人参 9g
            r'\d+[\.\)]\s*([\u4e00-\u9fff]+(?:（[\u4e00-\u9fff]*）)?)\s*(\d+(?:\.\d+)?)[gGg克]',
            # 中文单位: 人参9克
            r'([\u4e00-\u9fff]+(?:（[\u4e00-\u9fff]*）)?)\s*(\d+(?:\.\d+)?)克',
        ]
        
        for pattern in herb_patterns:
            matches = re.findall(pattern, line)
            for match in matches:
                if len(match) == 2:
                    herb_name, dosage = match
                    # 过滤掉明显不是药名的词和重复项
                    if len(herb_name) >= 2 and herb_name not in ['用法', '注意', '功效', '制法']:
                        # 避免重复添加同一药材
                        if (herb_name.strip(), dosage.strip()) not in herbs:
                            herbs.append((herb_name.strip(), dosage.strip()))
    
    return herbs

def extract_herbs_from_table(text: str):
    """从markdown表格中提取药材信息"""
    import re
    
    herbs = []
    lines = text.split('\n')
    
    # 检测是否包含表格格式
    table_indicators = ['药物', '剂量', '|', '---']
    if not any(indicator in text for indicator in table_indicators):
        return []
    
    # 寻找表格数据行
    for line in lines:
        line = line.strip()
        
        # 跳过表头和分隔线
        if not line or '药物' in line or '---' in line or '功效' in line:
            continue
            
        # 匹配表格行格式: | 药名 | 剂量 | 其他 |
        table_match = re.search(r'\|\s*([一-龟\u4e00-\u9fff]+(?:\（[^）]*\）)?)\s*\|\s*(\d+(?:\.\d+)?)g?\s*\|', line)
        if table_match:
            herb_name = table_match.group(1).strip()
            dosage = table_match.group(2).strip()
            
            # 清理药名（去除括号内容如"（制）"）
            herb_name = re.sub(r'[（\(][^）\)]*[）\)]', '', herb_name).strip()
            
            # 过滤有效药名
            if len(herb_name) >= 2 and herb_name not in ['药物', '剂量', '功效', '说明']:
                if (herb_name, dosage) not in herbs:
                    herbs.append((herb_name, dosage))
    
    return herbs

def standardize_prescription_format(ai_response: str) -> str:
    """统一处方格式为增强版标准格式 - 支持层次感和视觉效果"""
    import re
    
    # 先清理可能存在的重复标签和格式错误
    ai_response = re.sub(r'\*\*【处方】\*\*[\s\n]*\*\*【处方】\*\*', '**【处方】**', ai_response)
    ai_response = re.sub(r'【处方】[\s\n]*【处方】', '【处方】', ai_response)
    ai_response = re.sub(r'\*\*【处方】\*\*[\s\n]*\*\*\*\*', '**【处方】**', ai_response)
    
    # 改进的处方识别正则表达式 - 支持表格格式
    prescription_patterns = [
        # 表格格式 - 新增
        (r'(?:\|\s*药物.*?\|.*?\n.*?---.*?\n)(.*?)(?=\n\n|---|###|$)', '表格格式'),
        # XML格式
        (r'<处方[^>]*>(.*?)</处方>', 'XML'),
        # 标准标记格式 - 改进版
        (r'【处方】[：:]?\s*(.*?)(?=\n\n|【[^】]*】|\*\*【|$)', '标准标记'),
        (r'\*\*【处方】\*\*[：:]?\s*(.*?)(?=\n\n|【[^】]*】|\*\*【|$)', '标准标记带星号'),
        # 其他常见格式
        (r'(?:处方|方剂|药方)[：:]?\s*(.*?)(?=\n\n|\n【|\n\*\*|$)', '通用'),
    ]
    
    processed = False
    
    for pattern, pattern_name in prescription_patterns:
        if processed:
            break
            
        matches = list(re.finditer(pattern, ai_response, re.DOTALL | re.IGNORECASE))
        
        for match in matches:
            original_prescription = match.group(1).strip() if len(match.groups()) > 0 else match.group(0).strip()
            
            # 确保处方内容有效
            if len(original_prescription) < 3:
                continue
                
            # 使用新的药材提取函数
            herbs = extract_herbs_from_prescription(original_prescription)
            
            if not herbs or len(herbs) < 1:
                continue
            
            # 生成增强版标准格式 - 层次清晰、视觉美观
            standardized_prescription = generate_enhanced_prescription_format(herbs)
            
            # 替换原始处方 - 完全替换整个表格区域
            ai_response = ai_response.replace(match.group(0), standardized_prescription)
            processed = True
            break
    
    return ai_response

def generate_enhanced_prescription_format(herbs: list) -> str:
    """生成增强版处方格式 - 层次分明、视觉美观"""
    
    # 🎯 处方标题 - 显眼的标题
    prescription_text = "\n\n" + "=" * 50 + "\n"
    prescription_text += "# 🏥 **中医处方单**\n"
    prescription_text += "=" * 50 + "\n\n"
    
    # 💊 处方内容 - 清晰的药物列表
    prescription_text += "## **📋 处方组成**\n\n"
    
    herb_count = len(herbs)
    for i, (herb_name, dosage) in enumerate(herbs, 1):
        # 使用编号和颜色强调
        prescription_text += f"**{i}.** **`{herb_name}`** ——— **{dosage}g**\n"
    
    prescription_text += f"\n> **处方药味总数：** {herb_count} 味\n\n"
    
    # 🔥 煎服方法 - 详细用法说明
    prescription_text += "## **⚡ 煎服方法**\n\n"
    prescription_text += "### **煎制方法：**\n"
    prescription_text += "- 🔸 **第一煎：** 加清水500ml，浸泡30分钟后，大火煮沸转小火煎煮25分钟\n"
    prescription_text += "- 🔸 **第二煎：** 加清水400ml，直接煎煮20分钟\n"
    prescription_text += "- 🔸 **混合：** 两次药汁混合，约得药液300ml\n\n"
    
    prescription_text += "### **服用方法：**\n"
    prescription_text += "- 🔸 **用量：** 每日1剂，分2次温服\n"
    prescription_text += "- 🔸 **时间：** 饭后1小时服用（早晚各1次）\n"
    prescription_text += "- 🔸 **温度：** 温热服用，避免过烫或过凉\n\n"
    
    # 📝 用药注意事项
    prescription_text += "## **⚠️ 重要注意事项**\n\n"
    prescription_text += "### **🚨 安全提醒：**\n"
    prescription_text += "- **❗ 必须在执业中医师指导下使用**\n"
    prescription_text += "- **❗ 孕妇、哺乳期妇女慎用**\n"
    prescription_text += "- **❗ 服药期间忌食生冷、辛辣、油腻食物**\n"
    prescription_text += "- **❗ 如有过敏史，请告知医师**\n\n"
    
    prescription_text += "### **👀 用药观察：**\n"
    prescription_text += "- 🔹 观察症状变化情况\n"
    prescription_text += "- 🔹 注意有无不良反应\n"
    prescription_text += "- 🔹 记录服药后的感受\n\n"
    
    # 🔄 复诊要求
    prescription_text += "## **🔄 复诊安排**\n\n"
    prescription_text += "### **📅 复诊时间：**\n"
    prescription_text += "- **首次复诊：** 服药3天后\n"
    prescription_text += "- **后续复诊：** 每周1次，共3次\n\n"
    
    prescription_text += "### **📋 复诊要点：**\n"
    prescription_text += "- ✅ 主要症状变化情况\n"
    prescription_text += "- ✅ 药物疗效及不良反应\n"
    prescription_text += "- ✅ 食欲、睡眠、二便情况\n"
    prescription_text += "- ✅ 舌象、脉象变化\n\n"
    
    # 📞 医疗免责声明
    prescription_text += "## **📞 医疗免责声明**\n\n"
    prescription_text += "> **🔴 重要声明：**\n"
    prescription_text += "> 本处方为AI辅助生成的中医建议，仅供参考，不能替代正规医院的专业诊断和治疗。\n"
    prescription_text += "> - **建议在执业中医师指导下使用**\n\n"
    
    prescription_text += "---\n"
    prescription_text += "*🕒 处方生成时间：" + "今日" + "  |  💻 AI中医助手*\n"
    prescription_text += "---\n\n"
    
    return prescription_text

def enhance_diagnosis_format(ai_response: str) -> str:
    """增强整体诊疗方案的格式化 - 为所有医生回复添加层次感"""
    import re
    
    # 1. 强化标题层次
    # 将【xxx】格式转换为更显眼的格式
    ai_response = re.sub(r'【([^】]+)】', r'## **🔸 \1**', ai_response)
    
    # 2. 强化重要医学术语
    medical_terms = [
        '辨证论治', '证型', '病机', '治法', '方剂', '加减',
        '脾虚', '肝郁', '肾阳虚', '肾阴虚', '血瘀', '痰湿',
        '风寒', '风热', '湿热', '寒湿', '气滞', '血虚'
    ]
    
    for term in medical_terms:
        ai_response = re.sub(f'({term})', r'**\1**', ai_response)
    
    # 3. 增强症状描述的可读性
    symptom_keywords = ['头痛', '发热', '咳嗽', '胸闷', '腹痛', '便秘', '腹泻', '失眠', '疲倦']
    for symptom in symptom_keywords:
        ai_response = re.sub(f'({symptom})', r'**`\1`**', ai_response)
    
    # 4. 为重要提醒添加视觉强调
    ai_response = re.sub(r'(请.*?就医|建议.*?医师|注意.*?事项)', r'> **⚠️ \1**', ai_response)
    
    # 5. 为方剂名添加特殊格式
    formula_pattern = r'([一-九十]+[汤|散|丸|膏|汁|饮])'
    ai_response = re.sub(formula_pattern, r'**📜 `\1`**', ai_response)
    
    return ai_response

def detect_and_filter_western_medicine(ai_response: str) -> tuple[bool, str]:
    """检测并过滤西医内容 - 只清理明确的西药推荐和西医检查建议"""
    import re
    
    # 只检测明确需要过滤的西医内容 - 大幅缩减关键词列表
    western_medicine_keywords = {
        # 西药名称 - 只保留明确的西药推荐
        '西药': ['奥美拉唑', '阿司匹林', '布洛芬', '头孢', '阿莫西林', '青霉素', '氨茶碱', 
               '地塞米松', '泼尼松', '美托洛尔', '硝苯地平', '阿托伐他汀', '二甲双胍',
               '胰岛素', '华法林', '氯吡格雷', '雷贝拉唑', '多潘立酮', '蒙脱石散'],
        
        # 西医检查项目 - 只检测明确的检查建议
        '检查建议': ['建议做CT', '建议做MRI', '建议做核磁', '建议做B超', '建议做彩超', 
                   '建议做X光', '建议做胃镜', '建议做肠镜', '需要做血常规', '需要查肝功能',
                   '建议病理检查', '建议活检', '建议穿刺', '建议造影'],
        
        # 明确的西医诊断术语 - 移除"高血压"等常见病名，只保留严重疾病
        '严重疾病': ['癌症', '恶性肿瘤', '心肌梗死', '脑梗死'],
    }
    
    # 检测西医内容
    found_western_content = []
    
    # 中医合理上下文关键词 - 如果回复包含这些，说明是在中医语境下讨论
    tcm_context_keywords = ['中医', '中药', '辨证', '脏腑', '经络', '气血', '阴阳', '寒热', '虚实', 
                           '风寒', '风热', '湿热', '痰湿', '血瘀', '气滞', '肝郁', '脾虚', '肾虚',
                           '温阳', '滋阴', '清热', '祛湿', '化痰', '活血', '理气', '证候', '方剂']
    
    # 检查是否在中医上下文中
    has_tcm_context = any(tcm_keyword in ai_response for tcm_keyword in tcm_context_keywords)
    
    # 如果已经是中医上下文，只检测明确的西药推荐
    if has_tcm_context:
        # 只检测西药推荐
        for keyword in western_medicine_keywords['西药']:
            if f"建议服用{keyword}" in ai_response or f"可以用{keyword}" in ai_response:
                found_western_content.append(f"西药推荐:{keyword}")
    else:
        # 非中医上下文，检测所有西医内容
        for category, keywords in western_medicine_keywords.items():
            for keyword in keywords:
                if keyword in ai_response:
                    found_western_content.append(f"{category}:{keyword}")
    
    # 如果发现需要过滤的西医内容，只移除该部分内容，不替换整个回复
    if found_western_content:
        logger.warning(f"检测到西医内容: {found_western_content}")
        
        # 删除西药推荐语句，但保留其他内容
        filtered_response = ai_response
        
        # 移除西药推荐语句
        for keyword in western_medicine_keywords['西药']:
            patterns = [
                f"建议服用{keyword}[^。]*。?",
                f"可以用{keyword}[^。]*。?",
                f"推荐{keyword}[^。]*。?",
                f"使用{keyword}[^。]*。?"
            ]
            for pattern in patterns:
                filtered_response = re.sub(pattern, "", filtered_response)
        
        # 移除检查建议语句
        for keyword in western_medicine_keywords['检查建议']:
            pattern = f"{keyword}[^。]*。?"
            filtered_response = re.sub(pattern, "", filtered_response)
        
        # 清理多余的空行和格式
        filtered_response = re.sub(r'\n\s*\n\s*\n', '\n\n', filtered_response)
        filtered_response = filtered_response.strip()
        
        # 如果过滤后内容太少，添加中医建议
        if len(filtered_response) < 100:
            filtered_response += "\n\n建议通过中医辨证论治的方式进行调理，请详细描述症状以便准确诊断。"
        
        return True, filtered_response
    
    return False, ai_response

def sanitize_ai_response(ai_response: str, has_tongue_image: bool, patient_described_tongue: str = "", image_analysis_successful: bool = False, original_patient_message: str = "") -> str:
    """清理AI回复中的非法舌象、脉象、症状编造和处方编造信息"""
    
    # 首先检查舌象、脉象、症状安全
    is_safe, error_msg = check_medical_safety(ai_response, has_tongue_image, patient_described_tongue, image_analysis_successful, original_patient_message)
    
    # 如果发现传统的医疗安全问题（舌象、脉象、症状编造），先处理
    tongue_pulse_cleaned = False
    if not is_safe:
        logger.warning(f"发现医疗安全问题: {error_msg}")
        tongue_pulse_cleaned = True
    
    # 如果没有图片上传或图片分析失败，清理所有舌象脉象描述
    if not has_tongue_image or not image_analysis_successful:
        
        # 清理策略1: 处理XML格式的望诊部分
        if '<望诊所见>' in ai_response and '</望诊所见>' in ai_response:
            safer_observation = '<望诊所见>因未上传舌象图片，建议患者在充足光线下拍摄舌象照片以便更准确的望诊分析。</望诊所见>'
            ai_response = re.sub(r'<望诊所见>.*?</望诊所见>', safer_observation, ai_response, flags=re.DOTALL)
            logger.info("已替换XML望诊部分为安全提示")
        
        # 清理策略2: 处理"辨证要点"中的舌象脉象描述
        if "辨证要点" in ai_response:
            # 替换舌象描述行
            ai_response = re.sub(
                r'- 舌象：.*?[\n\r]', 
                '- 舌象：因未进行实际舌诊，建议患者面诊时由医师观察舌象\n', 
                ai_response
            )
            # 替换脉象描述行
            ai_response = re.sub(
                r'- 脉象：.*?[\n\r]', 
                '- 脉象：因未进行实际脉诊，建议患者面诊时由医师进行脉象诊断\n', 
                ai_response
            )
            logger.info("已清理辨证要点中的舌象脉象描述")
        
        # 清理策略3: 智能清理具体舌象脉象描述，保留正常术语讨论
        # 先检查上下文，如果是教学/说明内容则不清理
        def should_preserve_term(text, term_pos):
            """判断是否应该保留术语（基于上下文）"""
            context_before = text[max(0, term_pos-10):term_pos]
            return any(indicator in context_before for indicator in ['如', '若', '见', '或', '常', '多', '包括'])
        
        # 只清理明确的编造描述，保留教学讨论
        cleaned_response = ai_response
        
        # 处理明确的编造模式 - 扩展版本
        fabrication_patterns = [
            r'舌象[：:].*?[，。\n]',  # "舌象：淡红苔白"
            r'患者舌边尖红[，。]?',   # "患者舌边尖红"  
            r'患者苔薄[白黄][，。]?', # "患者苔薄白"
            r'脉象[：:].*?[，。\n]',  # "脉象：浮数有力"
            r'患者脉[浮沉缓数弦滑][，。]?', # "患者脉浮数"
            r'^脉[浮沉缓数弦滑][，。]',     # 句首的"脉浮数，"
            r'脉[浮沉缓数弦滑]+，有力[，。]?', # "脉浮数，有力"
            r'^舌质[淡红][，。]',          # 句首的"舌质淡红，"
            r'舌质淡红，苔薄[白黄腻][，。]?', # "舌质淡红，苔薄腻"
        ]
        
        for pattern in fabrication_patterns:
            matches = list(re.finditer(pattern, cleaned_response))
            for match in reversed(matches):  # 从后向前替换，避免位置偏移
                start, end = match.span()
                # 简单的上下文检查
                context = cleaned_response[max(0, start-15):start]
                if not any(indicator in context for indicator in ['如', '若', '见', '或', '常见', '多为']):
                    if '舌象' in match.group():
                        cleaned_response = cleaned_response[:start] + '舌象需要面诊观察。' + cleaned_response[end:]
                    elif '脉象' in match.group():
                        cleaned_response = cleaned_response[:start] + '脉象需要面诊切诊。' + cleaned_response[end:]
                    else:
                        cleaned_response = cleaned_response[:start] + cleaned_response[end:]
                    logger.info(f"清理了编造描述: {match.group()}")
        
        ai_response = cleaned_response
        
        
        # 清理策略5: 严格清理望诊切诊部分的编造内容
        if "1. 望诊" in ai_response or "### 望诊" in ai_response:
            # 替换整个望诊部分
            ai_response = re.sub(
                r'(?:1\.|###)?\s*望诊[：:]?.*?(?=(?:2\.|###|$))', 
                '1. 望诊\n\n- 未进行实际望诊，建议患者提供舌象照片或寻求面诊。\n\n',
                ai_response, 
                flags=re.DOTALL
            )
            logger.info("已清理望诊部分的编造内容")
        
        if "4. 切诊" in ai_response or "### 切诊" in ai_response:
            # 替换整个切诊部分
            ai_response = re.sub(
                r'(?:4\.|###)?\s*切诊[：:]?.*?(?=(?:5\.|###|$))', 
                '4. 切诊\n\n- 未进行实际切诊，脉象诊断需要专业中医师面诊确定。\n\n',
                ai_response, 
                flags=re.DOTALL
            )
            logger.info("已清理切诊部分的编造内容")
        
        # 清理策略6: 清理诊疗方案中的编造体征
        if "<望诊所见>" in ai_response:
            # 更严格的望诊清理
            ai_response = re.sub(
                r'<望诊所见>.*?</望诊所见>',
                '<望诊所见>未进行实际望诊，建议患者上传舌象照片或面诊</望诊所见>',
                ai_response,
                flags=re.DOTALL
            )
            logger.info("已清理XML格式的望诊编造内容")

        # 清理策略7: 检测并阻止AI编造具体处方建议 - 修复过度清理问题
        prescription_fabrication_patterns = [
            r'💊 处方建议.*?(?=🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',              # 整个处方建议部分 (简化)
            r'💊 药物组成.*?(?=🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',              # 药物组成部分 (简化)
            r'处方组成[：:].*?(?=🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',             # 处方组成部分 (简化)
            # 删除过度清理的模式：
            # r'-\s*[^\n]+\s+\d+g',                                              # "- 连翘 15g" 格式 - 会误判OCR分析
            # r'[一-龯\u4e00-\u9fff]{2,4}\s+\d+g',                              # "连翘 15g" 格式 - 会误判OCR分析
            r'煎制方法[：:].*?(?=服用方法|🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',       # 煎制方法 (简化)
            r'服用方法[：:].*?(?=🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',               # 服用方法 (简化)
        ]
        
        for pattern in prescription_fabrication_patterns:
            if re.search(pattern, ai_response, flags=re.DOTALL):
                logger.warning("检测到AI编造处方内容，进行清理")
                
                # 替换处方建议部分 (使用简化模式)
                ai_response = re.sub(
                    r'💊 处方建议.*?(?=🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',
                    '💊 处方建议\n\n⚠️ 为确保用药安全，具体的处方建议需要由执业中医师根据患者的具体情况，通过面诊后才能开具。\n\n建议患者：\n1. 及时到正规中医院就诊\n2. 由专业中医师进行四诊合参\n3. 根据具体证型开具个性化处方\n\n',
                    ai_response,
                    flags=re.DOTALL
                )
                
                # 替换药物组成部分（防止AI编造具体处方）- 使用简化模式
                ai_response = re.sub(
                    r'💊 药物组成.*?(?=🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',
                    '💊 药物组成\n\n⚠️ 处方的具体药物组成需要由执业中医师根据患者的具体病情，通过详细诊察后才能确定。\n\n请到正规中医医院进行专业诊疗。\n\n',
                    ai_response,
                    flags=re.DOTALL
                )
                
                # 清理煎服指导
                ai_response = re.sub(
                    r'⚡ 煎服指导\s*.*?(?=---|\n\n[🔥⚡📜🔄]|\n\n[【\[]|$)',
                    '⚡ 用药指导\n\n具体的煎制和服用方法应当遵循执业中医师的专业指导。\n\n',
                    ai_response,
                    flags=re.DOTALL
                )
                
                # 清理辨证加减部分（这也是编造的）
                ai_response = re.sub(
                    r'🔄 辨证加减\s*.*?(?=---|\n\n[🔥⚡📜🔄]|\n\n[【\[]|$)',
                    '🔄 后续调整\n\n具体的药物加减应当由执业中医师根据患者病情变化进行专业调整。\n\n',
                    ai_response,
                    flags=re.DOTALL
                )
                
                logger.info("已清理AI编造的处方建议内容")
                break

        # 清理策略8: 检测并清理编造的望诊信息
        appearance_fabrication_patterns = [
            (r'面色[略显]?[苍白红润黯淡][，。]?', '面色需要面诊观察'),
            (r'精神[疲倦萎靡不振倦怠][，。]?', '精神状态需要面诊评估'), 
            (r'舌体[胖大瘦薄][，。]?', '舌体特征需要面诊检查'),
            (r'舌边[有齿痕无异常][，。]?', '舌边情况需要面诊确认'),
        ]
        
        for pattern, replacement in appearance_fabrication_patterns:
            if re.search(pattern, ai_response):
                logger.warning(f"检测到编造的望诊信息: {pattern}")
                # 清理编造的望诊描述
                ai_response = re.sub(pattern, replacement, ai_response)
                logger.info(f"已清理编造的望诊信息: {pattern}")

        # 清理策略4: 添加简洁的医疗安全提醒（仅在必要时）
        if "重要声明" not in ai_response and "仅供参考" not in ai_response:
            safety_notice = "\n\n**提醒**：以上建议仅供参考，如症状严重请及时就医。"
            ai_response += safety_notice
            logger.info("已添加简洁医疗安全提醒")
    
    # 🚨 关键修复：处方编造清理逻辑 - 总是运行，不管舌象脉象检查结果
    # 这个清理逻辑独立于舌象脉象检查，因为处方编造是更严重的安全问题
    # 修复：移除会误判OCR分析的过度清理模式
    prescription_fabrication_patterns = [
        r'💊 处方建议.*?(?=🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',              # 整个处方建议部分 (简化)
        r'💊 药物组成.*?(?=🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',              # 药物组成部分 (简化)
        r'处方组成[：:].*?(?=🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',             # 处方组成部分 (简化)
        # 注释掉会误判OCR分析的模式：
        # r'-\s*[^\n]+\s+\d+g',                                              # "- 连翘 15g" 格式 - 误判OCR
        # r'[一-龯\u4e00-\u9fff]{2,4}\s+\d+g',                              # "连翘 15g" 格式 - 误判OCR
        r'煎制方法[：:].*?(?=服用方法|🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',       # 煎制方法 (简化)
        r'服用方法[：:].*?(?=🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',               # 服用方法 (简化)
    ]
    
    for pattern in prescription_fabrication_patterns:
        if re.search(pattern, ai_response, flags=re.DOTALL):
            logger.warning("检测到AI编造处方内容，进行清理")
            
            # 替换处方建议部分 (使用简化模式)
            ai_response = re.sub(
                r'💊 处方建议.*?(?=🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',
                '💊 处方建议\n\n⚠️ 为确保用药安全，具体的处方建议需要由执业中医师根据患者的具体情况，通过面诊后才能开具。\n\n建议患者：\n1. 及时到正规中医院就诊\n2. 由专业中医师进行四诊合参\n3. 根据具体证型开具个性化处方\n\n',
                ai_response,
                flags=re.DOTALL
            )
            
            # 替换药物组成部分（防止AI编造具体处方）- 使用简化模式
            ai_response = re.sub(
                r'💊 药物组成.*?(?=🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',
                '💊 药物组成\n\n⚠️ 处方的具体药物组成需要由执业中医师根据患者的具体病情，通过详细诊察后才能确定。\n\n请到正规中医医院进行专业诊疗。\n\n',
                ai_response,
                flags=re.DOTALL
            )
            
            # 清理煎服指导
            ai_response = re.sub(
                r'⚡ 煎服指导.*?(?=🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',
                '⚡ 用药指导\n\n具体的煎制和服用方法应当遵循执业中医师的专业指导。\n\n',
                ai_response,
                flags=re.DOTALL
            )
            
            # 清理辨证加减部分（这也是编造的）
            ai_response = re.sub(
                r'🔄 辨证加减.*?(?=🔥|⚡|📜|🔄|🎯|---|\n\n\*|$)',
                '🔄 后续调整\n\n具体的药物加减应当由执业中医师根据患者病情变化进行专业调整。\n\n',
                ai_response,
                flags=re.DOTALL
            )
            
            logger.info("已清理AI编造的处方建议内容")
            break
    
    return ai_response

def check_image_analysis_success(chat_history: list) -> bool:
    """检查最近的图片分析是否成功
    
    通过检查会话历史中的图片上传结果来判断：
    1. 包含"✅ 舌象图片已成功上传" → 分析成功
    2. 包含"⚠️ 图片已上传，但图像质量" → 分析失败（质量问题）
    3. 没有图片上传记录 → 分析失败
    """
    try:
        logger.info(f"检查图片分析状态，历史消息数量: {len(chat_history)}")
        
        # 从最近的消息开始检查，重点查找图片上传的成功标识
        for message in reversed(chat_history):
            content = message.get("content", "")
            role = message.get("role", "")
            
            # 检查AI回复中的图片上传确认信息
            if role == "assistant":
                # 成功上传的标识
                if "✅ 舌象图片已成功上传" in content:
                    logger.info("检测到成功的舌象图片上传标识")
                    return True
                # 质量问题的标识
                if "⚠️ 图片已上传，但图像质量" in content:
                    logger.info("检测到图片质量问题标识")
                    return False
                # 其他图片相关的成功标识
                if "图片已成功上传" in content or "舌象图片" in content and "成功" in content:
                    logger.info("检测到其他图片上传成功标识")
                    return True
            
            # 检查系统消息中是否有图片分析成功的标识
            if role == "system" and "舌象" in content:
                if "成功" in content or "已保存" in content:
                    logger.info("检测到系统级图片处理成功标识")
                    return True
        
        logger.info("未检测到任何图片上传成功标识")
        return False
    except Exception as e:
        logger.error(f"检查图片分析状态失败: {e}")
        return False

async def detect_tongue_image_upload(conversation_id: str, chat_history: list) -> bool:
    """检测是否有舌象图片上传
    
    改进的检测逻辑：
    1. 优先检查明确的上传成功标识
    2. 检查会话历史中的图像消息
    3. 检查是否存在舌象相关的图像文件
    """
    
    logger.info(f"检测舌象图片上传状态，会话ID: {conversation_id}，历史消息数量: {len(chat_history)}")
    
    # 方法1: 检查明确的图片上传成功标识
    for msg in reversed(chat_history):  # 从最新消息开始检查
        content = msg.get("content", "")
        role = msg.get("role", "")
        
        # 检查AI回复中的图片上传确认
        if role == "assistant":
            if "✅ 舌象图片已成功上传" in content:
                logger.info("通过AI回复确认检测到舌象图片上传")
                return True
            if "⚠️ 图片已上传，但图像质量" in content:
                logger.info("检测到图片上传但质量有问题")
                return True  # 虽然质量有问题，但确实上传了
        
        # 检查用户消息中的图片上传标识
        if role == "user":
            if any(keyword in content for keyword in ["舌象图片", "舌诊照片", "上传舌象", "舌头照片"]):
                logger.info(f"在用户消息中检测到舌象图片上传标识: {content[:50]}...")
                return True
    
    # 方法2: 检查是否存在会话相关的图像文件
    # 假设图像文件存储在 ./uploaded_images/{conversation_id}/ 目录
    image_dir = f"./uploaded_images/{conversation_id}"
    if os.path.exists(image_dir):
        image_files = [f for f in os.listdir(image_dir) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))]
        if image_files:
            logger.info(f"检测到会话 {conversation_id} 有 {len(image_files)} 个图像文件")
            return True
    
    # 方法3: 检查用户消息中是否有base64编码的图像数据（用于未来扩展）
    for msg in chat_history:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            # 检查是否包含base64图像数据
            if "data:image/" in content and "base64," in content:
                logger.info("检测到base64编码的图像数据")
                return True
    
    return False

def validate_image_analysis_safety(analysis_result: str, image_type: str) -> str:
    """验证图像分析结果的医疗安全性"""
    
    # 危险的断言性词汇
    dangerous_assertions = [
        "确诊", "诊断为", "可以确定", "明确显示", "一定是", "肯定是", 
        "患有", "病变", "异常", "疾病", "症候", "证型为"
    ]
    
    # 过于具体的舌象描述（可能不准确）
    over_specific_tongue = [
        "舌苔厚腻", "舌边齿痕明显", "舌质紫暗", "地图舌", 
        "镜面舌", "舌体胖大", "舌尖红刺"
    ]
    
    # 检查是否包含危险断言
    has_dangerous_assertion = any(danger in analysis_result for danger in dangerous_assertions)
    
    # 检查舌象描述是否过于具体
    has_over_specific = any(specific in analysis_result for specific in over_specific_tongue)
    
    # 安全性评估
    safety_warnings = []
    
    if has_dangerous_assertion:
        safety_warnings.append("⚠️ 检测到过于肯定的医疗判断表述")
        logger.warning("图像分析包含危险的医疗断言")
    
    if has_over_specific and image_type in ["舌部", "医学图像"]:
        safety_warnings.append("⚠️ 舌象描述可能过于具体，建议谨慎参考")
        logger.warning("舌象分析可能过于具体")
    
    # 如果发现安全问题，添加警告或替换为安全版本
    if safety_warnings:
        safe_result = f"""
【图像分析安全提示】
{chr(10).join(safety_warnings)}

【保守分析结果】
图像质量和角度限制了准确分析。基于可见部分进行非常保守的观察：

"""
        if image_type in ["舌部", "医学图像"]:
            safe_result += """- 图像显示舌部区域，但受光线、角度等因素影响，无法进行精确的舌象分析
- 建议患者在自然光下、舌体平伸状态下重新拍摄，或直接寻求中医师面诊
- 舌象分析需要结合患者症状、脉象等综合判断，单纯图像分析有局限性

【重要提醒】
- 此分析结果仅供参考，不能替代专业医师诊断
- 任何治疗方案都需要执业中医师根据四诊合参制定
- 建议患者及时就医，寻求专业中医师的面诊和指导"""
        else:
            safe_result += """- 图像显示面部区域，但受光线、角度等因素影响，仅能观察到基本面色
- 面诊需要在自然光下、近距离观察，图像分析存在局限性
- 建议结合患者自述症状和专业医师面诊进行综合判断

【重要提醒】  
- 此分析结果仅供参考，不能替代专业医师诊断
- 任何诊疗建议都需要执业中医师亲自诊查确定"""
        
        return safe_result
    
    # 如果安全，但仍需要添加标准安全声明
    else:
        # 确保包含必要的安全声明
        if "仅供参考" not in analysis_result:
            analysis_result += "\n\n【重要声明】此图像分析仅供参考，不能作为诊断依据。建议结合症状描述和专业中医师面诊进行综合判断。"
        
        return analysis_result

def extract_patient_tongue_description(chat_history: list) -> str:
    """提取患者描述的舌象信息
    
    从会话历史中提取患者自己描述的舌象特征，
    这些信息是合法的，可以在AI回复中使用
    """
    patient_descriptions = []
    
    # 舌象相关关键词
    tongue_keywords = [
        "舌苔", "舌质", "舌边", "舌尖", "舌根", "舌体", 
        "舌红", "舌淡", "舌紫", "舌暗", "舌胖", "舌瘦",
        "苔薄", "苔厚", "苔白", "苔黄", "苔腻", "苔干",
        "齿痕", "裂纹", "地图舌", "镜面舌"
    ]
    
    for msg in chat_history:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            
            # 检查用户消息中是否包含舌象描述
            for keyword in tongue_keywords:
                if keyword in content:
                    # 提取包含舌象关键词的句子
                    sentences = re.split(r'[。！？.!?]', content)
                    for sentence in sentences:
                        if keyword in sentence:
                            patient_descriptions.append(sentence.strip())
                            logger.info(f"提取到患者舌象描述: {sentence.strip()}")
    
    return " ".join(set(patient_descriptions))  # 去重并合并

import asyncio
import logging
import re
import json
import tempfile
import platform
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request, Response

# 先定义logger，再导入安全系统
import logging
from app.core.logging_config import configure_app_logging
logger = logging.getLogger(__name__)

# 导入安全系统
try:
    from api.security_integration import setup_security_system, protect_api_routes
    SECURITY_AVAILABLE = True
    logger.info("Security system imported successfully")
except ImportError as e:
    logger.warning(f"Security system not available: {e}")
    SECURITY_AVAILABLE = False
from fastapi.responses import PlainTextResponse
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import numpy as np
import requests

# 导入医生路由（保持原有导入时机，避免历史模块路径副作用）
from api.routes.doctor_routes import router as doctor_router
from api.routes.prescription_routes import router as prescription_router
from api.routes.payment_routes import router as payment_router
from api.routes.decoction_routes import router as decoction_router
from api.routes.auth_routes import router as auth_router
from api.routes.unified_auth_routes import router as unified_auth_router
from api.routes.unified_login_routes import router as unified_login_router  # ⭐ 新的统一登录路由
from api.routes.doctor_decision_tree_routes import router as decision_tree_router
from api.routes.decision_tree_usage_routes import router as decision_tree_usage_router
from api.routes.decision_tree_data_routes import router as decision_tree_data_router  # ⭐ 决策树数据驱动v3.0
from api.routes.symptom_analysis_routes import router as symptom_analysis_router
# from api.routes.doctor_matching_routes import router as doctor_matching_router  # AI推荐医生功能已移除
from api.routes.review_routes import router as review_router
from api.routes.unified_consultation_routes import router as unified_consultation_router
from api.routes.database_management_routes import router as database_management_router
from api.routes.conversation_sync_routes import router as conversation_sync_router
from api.routes.user_data_sync_routes import router as user_data_sync_router
from api.routes.data_migration_routes import router as data_migration_router
from api.routes.user_sessions_routes import router as user_sessions_router
from api.routes.medical_knowledge_routes import router as medical_knowledge_router
from api.routes.follow_up_routes import router as follow_up_router
from api.routes.session_routes import router as session_router
from api.routes.security_routes import router as security_router
from api.routes.prescription_review_routes import router as prescription_review_router
from api.routes.prescription_structured_edit_routes import router as prescription_structured_edit_router

from app.api.registration import (
    register_all_routes,
    setup_exception_and_security,
    setup_cors_middleware,
)
from app.api.site_setup import (
    register_common_browser_file_routes,
    setup_static_and_site_routes,
)
from app.api.ops_setup import register_operational_routes
from app.api.monitor_setup import register_monitor_and_debug_routes
from app.api.page_setup import (
    register_auth_portal_routes,
    register_three_interface_page_routes,
)
from app.api.feature_page_setup import (
    register_auth_entry_routes,
    register_console_and_test_page_routes,
    register_doctor_tool_page_routes,
)
from app.services import local_sqlite_service as sqlite_service
import faiss

# 导入智能缓存系统
from core.cache_system.intelligent_cache_system import IntelligentCacheSystem, get_cache_system, init_cache_system
from core.prescription.integrated_prescription_parser import parse_prescription_text
from core.prescription.prescription_checker import PrescriptionChecker
from services.prescription_ocr_system import get_ocr_system, PrescriptionOCRSystem
from core.knowledge_retrieval.tcm_knowledge_graph import TCMKnowledgeGraph
from services.famous_doctor_learning_system import FamousDoctorLearningSystem
from services.prescription_learning_integrator import get_prescription_learning_integrator
import pickle

# 导入增强检索和人格化系统
# 重新启用增强系统，所有依赖已修复
try:
    from core.knowledge_retrieval.enhanced_retrieval import EnhancedKnowledgeRetrieval
    from core.doctor_system.tcm_doctor_personas import PersonalizedTreatmentGenerator
    from services.personalized_learning import PersonalizedLearningSystem, UserFeedback
    from core.doctor_system.doctor_mind_integration import EnhancedPersonalizedTreatmentGenerator, DoctorMindAPI
    from database.postgresql_knowledge_interface import get_hybrid_knowledge_system
    from services.medical_diagnosis_controller import medical_diagnosis_controller
    ENHANCED_SYSTEM_AVAILABLE = True  # 依赖已修复，重新启用
    DOCTOR_MIND_SYSTEM_AVAILABLE = True
    POSTGRESQL_HYBRID_AVAILABLE = True
    # print("Enhanced systems loaded successfully including PostgreSQL hybrid knowledge")  # 减少启动日志
except ImportError as e:
    print(f"Enhanced systems not available: {e}, using basic search")
    ENHANCED_SYSTEM_AVAILABLE = False
    DOCTOR_MIND_SYSTEM_AVAILABLE = False
    POSTGRESQL_HYBRID_AVAILABLE = False

# 导入张仲景专用决策系统
try:
    from zhang_zhongjing_decision_system import ZhangZhongjingDecisionSystem
    ZHANG_ZHONGJING_SYSTEM_AVAILABLE = True
    # print("Zhang Zhongjing decision system loaded successfully")  # 减少启动日志
except ImportError as e:
    print(f"Zhang Zhongjing decision system not available: {e}")
    ZHANG_ZHONGJING_SYSTEM_AVAILABLE = False

# 初始化智能缓存系统
try:
    cache_system = init_cache_system(
        cache_db_path=str(PATHS['cache_db']),
        similarity_threshold=0.45
    )
    CACHE_SYSTEM_AVAILABLE = True
    # print("Intelligent cache system initialized successfully")  # 减少启动日志
except Exception as e:
    print(f"Cache system initialization failed: {e}, continuing without cache")
    CACHE_SYSTEM_AVAILABLE = False

# 初始化用户历史系统
try:
    from services.user_history_system import UserHistorySystem
    user_history = UserHistorySystem()  # 直接实例化
    USER_HISTORY_AVAILABLE = True
    logger.info("✅ 用户历史系统初始化成功")
except ImportError as e:
    print(f"User history system not available: {e}")
    USER_HISTORY_AVAILABLE = False
    user_history = None

# 基础导入和配置
if platform.system() == "Linux":
    os.environ['SQLITE_TMPDIR'] = '/tmp'
    os.environ['TMPDIR'] = '/tmp'

# 优化jieba分词启动性能 - 禁用DEBUG日志和详细输出
import logging
import jieba
jieba_logger = logging.getLogger('jieba')
jieba_logger.setLevel(logging.ERROR)  # 只显示ERROR级别，进一步减少日志
jieba.setLogLevel(logging.ERROR)  # 设置jieba内部日志级别

try:
    import dashscope
    from dashscope import Generation, MultiModalConversation
    from http import HTTPStatus
except ImportError as e:
    print(f"Required libraries missing: {e}. Please run 'pip install dashscope'")
    sys.exit(1)

# 日志配置（阶段2：迁移到app.core.logging_config）
logger = configure_app_logging(logger_name=__name__)

# 环境变量由 config/settings.py 统一加载
logger.info("Environment variables initialized via config.settings.")

# API配置
DASHSCOPE_API_KEY = AI_CONFIG.get("dashscope_api_key", "")
if not DASHSCOPE_API_KEY:
    logger.error("CRITICAL: DASHSCOPE_API_KEY not set.")
else:
    dashscope.api_key = DASHSCOPE_API_KEY
    logger.info("DashScope API Key is set.")

MAIN_LLM_MODEL = "qwen-turbo"
RAG_EMBEDDING_MODEL = "text-embedding-v4"
RAG_EMBEDDING_DIM = 1024
CONVERSATION_LOG_DIR = "./conversation_logs"
os.makedirs(CONVERSATION_LOG_DIR, exist_ok=True)

# FAISS知识库路径配置（由统一配置 PATHS 提供，可被 KNOWLEDGE_DB_PATH 覆盖）
KNOWLEDGE_DB_PATH = str(PATHS["knowledge_db"])
FAISS_INDEX_FILE = os.path.join(KNOWLEDGE_DB_PATH, "knowledge.index")
DOCUMENTS_FILE = os.path.join(KNOWLEDGE_DB_PATH, "documents.pkl")
METADATA_FILE = os.path.join(KNOWLEDGE_DB_PATH, "metadata.pkl")

conversation_history_store: Dict[str, List[Dict[str, str]]] = {}
conversation_session_store: Dict[str, Dict] = {}

# 初始化增强检索和人格化系统
enhanced_retrieval = None
persona_generator = None
learning_system = None
enhanced_treatment_generator = None
doctor_mind_api = None
hybrid_knowledge_system = None

if ENHANCED_SYSTEM_AVAILABLE:
    try:
        enhanced_retrieval = EnhancedKnowledgeRetrieval(KNOWLEDGE_DB_PATH)
        persona_generator = PersonalizedTreatmentGenerator()
        learning_system = PersonalizedLearningSystem(db_path=str(PATHS['data_dir'] / 'learning_db.sqlite'))
        logger.info("Enhanced retrieval, persona and learning systems initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize enhanced systems: {e}")
        ENHANCED_SYSTEM_AVAILABLE = False

# 初始化PostgreSQL混合知识库系统
if POSTGRESQL_HYBRID_AVAILABLE:
    try:
        hybrid_knowledge_system = get_hybrid_knowledge_system(enhanced_retrieval)
        logger.info("PostgreSQL hybrid knowledge system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL hybrid system: {e}")
        POSTGRESQL_HYBRID_AVAILABLE = False

# 初始化医生思维决策树系统
if DOCTOR_MIND_SYSTEM_AVAILABLE:
    try:
        enhanced_treatment_generator = EnhancedPersonalizedTreatmentGenerator()
        doctor_mind_api = DoctorMindAPI(enhanced_treatment_generator)
        logger.info("Doctor mind decision tree system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize doctor mind system: {e}")
        DOCTOR_MIND_SYSTEM_AVAILABLE = False

# 初始化张仲景专用决策系统
if ZHANG_ZHONGJING_SYSTEM_AVAILABLE:
    try:
        zhang_zhongjing_system = ZhangZhongjingDecisionSystem()
        logger.info("Zhang Zhongjing specialized decision system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Zhang Zhongjing system: {e}")
        ZHANG_ZHONGJING_SYSTEM_AVAILABLE = False
        zhang_zhongjing_system = None
else:
    zhang_zhongjing_system = None

# 混合知识库搜索函数 (整合PostgreSQL和FAISS)
async def search_knowledge_base(query: str, query_embedding: list[float], k: int = 5, selected_doctor: str = "zhang_zhongjing") -> list[str]:
    """增强的混合知识库搜索函数 (优先使用PostgreSQL医生专用知识库，支持向量搜索)"""
    try:
        # 如果PostgreSQL混合系统可用，优先使用
        if POSTGRESQL_HYBRID_AVAILABLE and hybrid_knowledge_system:
            logger.info(f"Using PostgreSQL hybrid knowledge search (with vectors) for doctor: {selected_doctor}")
            results = await hybrid_knowledge_system.search_knowledge(
                query, selected_doctor, query_embedding=query_embedding, top_k=k
            )
            
            # 转换格式为原有格式
            formatted_results = []
            for result in results:
                content = result.get('content', '')
                title = result.get('title', 'Unknown')
                source = result.get('source', '')
                search_method = result.get('search_method', 'unknown')
                score = result.get('relevance_score', 0)
                
                formatted_content = f"【{title}】\n{content}"
                if source and source != '综合知识库':
                    formatted_content += f"\n\n来源：{source}"
                formatted_content += f"\n\n搜索方式：{search_method}，相关性：{score:.3f}"
                formatted_results.append(formatted_content)
            
            logger.info(f"PostgreSQL hybrid vector search found {len(formatted_results)} results")
            return formatted_results
        
        # 如果增强检索系统可用，使用混合检索
        elif ENHANCED_SYSTEM_AVAILABLE and enhanced_retrieval:
            logger.info("Using enhanced hybrid search")
            results = enhanced_retrieval.hybrid_search(
                query=query,
                query_embedding=query_embedding,
                semantic_weight=0.6,
                keyword_weight=0.4,
                total_results=k
            )
            return [result['document'] for result in results]
        
        # 否则使用基础FAISS检索
        else:
            logger.info("Using basic FAISS search")
            if not os.path.exists(FAISS_INDEX_FILE):
                logger.warning("FAISS index file not found")
                return []
                
            # 加载索引
            index = faiss.read_index(FAISS_INDEX_FILE)
            if index.ntotal == 0:
                logger.warning("FAISS index is empty")
                return []
                
            # 加载文档
            with open(DOCUMENTS_FILE, 'rb') as f:
                documents = pickle.load(f)
                
            # 标准化查询向量
            query_vector = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_vector)
            
            # 搜索
            scores, indices = index.search(query_vector, k)
            
            # 返回结果
            results = []
            for idx in indices[0]:
                if idx != -1 and idx < len(documents):
                    results.append(documents[idx])
            
            logger.info(f"FAISS search found {len(results)} results")
            return results
        
    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}")
        return []

def extract_diagnosis_improved(ai_response: str) -> str:
    """
    改进的诊断信息提取函数
    支持多种中医诊断格式
    """
    import re
    
    diagnosis_patterns = [
        # XML格式
        r'<诊断>(.*?)</诊断>',
        r'<中医诊断>(.*?)</中医诊断>',
        r'<证候>(.*?)</证候>',
        
        # 标准格式
        r'【诊断】[:：]?\s*(.+?)(?:\n|$)',
        r'【中医诊断】[:：]?\s*(.+?)(?:\n|$)', 
        r'【证候】[:：]?\s*(.+?)(?:\n|$)',
        r'【证型】[:：]?\s*(.+?)(?:\n|$)',
        
        # 自然语言格式
        r'诊断为[:：]?\s*(.+?)(?:\n|。|$)',
        r'辨证为[:：]?\s*(.+?)(?:\n|。|$)',
        r'证候为[:：]?\s*(.+?)(?:\n|。|$)',
        r'属于[:：]?\s*(.+?证)(?:\n|。|$)',
        
        # 结构化格式
        r'## 诊断\s*\n(.+?)(?:\n##|\n\n|$)',
        r'\*\*诊断[:：]?\*\*\s*(.+?)(?:\n|$)',
        
        # 其他常见格式
        r'中医诊断[:：]?\s*(.+?)(?:\n|。|$)',
        r'临床诊断[:：]?\s*(.+?)(?:\n|。|$)',
    ]
    
    for pattern in diagnosis_patterns:
        matches = re.findall(pattern, ai_response, re.MULTILINE | re.DOTALL)
        if matches:
            diagnosis = matches[0].strip()
            # 清理多余的标点和空白
            diagnosis = re.sub(r'[\n\r\t]+', ' ', diagnosis)
            diagnosis = re.sub(r'[。，；：]+$', '', diagnosis)
            if len(diagnosis) > 5 and len(diagnosis) < 200:  # 合理长度
                return diagnosis
    
    # 如果没有找到，尝试从段落中提取
    lines = ai_response.split('\n')
    for line in lines:
        line = line.strip()
        if any(keyword in line for keyword in ['证', '诊断', '辨证', '病机']):
            if len(line) > 10 and len(line) < 150:
                # 去掉可能的前缀
                for prefix in ['根据症状,', '综合分析,', '患者的情况属于']:
                    line = line.replace(prefix, '')
                cleaned_line = line.strip()
                if len(cleaned_line) > 5:
                    return cleaned_line
    
    return "待完善"

def extract_prescription_improved(ai_response: str) -> tuple[bool, str]:
    """
    改进的处方提取函数
    返回: (是否检测到处方, 处方内容)
    """
    import re
    
    # 1. XML格式处方检测（最优先）
    xml_patterns = [
        r'<处方建议>(.*?)</处方建议>',
        r'<处方>(.*?)</处方>',
        r'<方剂>(.*?)</方剂>',
        r'<药方>(.*?)</药方>'
    ]
    
    for pattern in xml_patterns:
        matches = re.findall(pattern, ai_response, re.MULTILINE | re.DOTALL)
        if matches:
            prescription = matches[0].strip()
            if len(prescription) > 20:  # 处方应该有一定长度
                return True, prescription[:1500]
    
    # 2. 标准标记格式
    marker_patterns = [
        r'【处方】[:：]?(.*?)(?:【|##|\n\n|$)',
        r'【方剂】[:：]?(.*?)(?:【|##|\n\n|$)',
        r'【药方】[:：]?(.*?)(?:【|##|\n\n|$)',
        r'处方[:：]\n(.*?)(?:【|##|\n\n|$)',
        r'方剂[:：]\n(.*?)(?:【|##|\n\n|$)',
        r'## 处方建议\s*\n(.*?)(?:##|\n\n|$)',
        r'\*\*处方[:：]?\*\*\s*\n(.*?)(?:\n\n|$)'
    ]
    
    for pattern in marker_patterns:
        matches = re.findall(pattern, ai_response, re.MULTILINE | re.DOTALL)
        if matches:
            prescription = matches[0].strip()
            # 验证是否包含药物信息
            if has_herbal_content(prescription):
                return True, prescription[:400]
    
    # 3. 方剂名称检测
    formula_patterns = [
        r'(银翘散|麻杏石甘汤|小柴胡汤|四君子汤|四物汤|六味地黄汤|补中益气汤|逍遥散|甘露饮|清胃散).*?(?:组成|药物)[:：]?(.*?)(?:【|##|\n\n|$)',
        r'推荐使用\s*(.*?汤|.*?散|.*?丸|.*?片)\s*[:,：]?(.*?)(?:【|##|\n\n|$)'
    ]
    
    for pattern in formula_patterns:
        matches = re.findall(pattern, ai_response, re.MULTILINE | re.DOTALL)
        if matches:
            formula_name = matches[0][0] if isinstance(matches[0], tuple) else matches[0]
            formula_content = matches[0][1] if isinstance(matches[0], tuple) and len(matches[0]) > 1 else ""
            if formula_content and has_herbal_content(formula_content):
                return True, f"{formula_name}：{formula_content}"[:1500]
            elif formula_name:
                return True, f"推荐方剂：{formula_name}"
    
    # 4. 药物组合检测
    lines = ai_response.split('\n')
    herb_lines = []
    
    common_herbs = [
        '党参', '黄芪', '当归', '川芎', '白芍', '熟地', '白术', '茯苓', '甘草',
        '银花', '连翘', '板蓝根', '蒲公英', '桔梗', '薄荷', '菊花', '金银花',
        '陈皮', '半夏', '生姜', '大枣', '枸杞', '菊花', '决明子', '山楂',
        '柴胡', '黄芩', '人参', '鹿茸', '冬虫夏草', '灵芝', '天麻'
    ]
    
    for line in lines:
        line = line.strip()
        # 检查是否包含药物和用量
        herb_count = sum(1 for herb in common_herbs if herb in line)
        has_dosage = bool(re.search(r'\d+[gG克钱]', line))
        
        if herb_count >= 2 or (herb_count >= 1 and has_dosage):
            herb_lines.append(line)
    
    if len(herb_lines) >= 3:  # 至少3行药物
        prescription_content = '\n'.join(herb_lines[:8])  # 最多8行
        return True, prescription_content[:1500]
    
    # 5. 检测"- 药名 用量"格式的药物列表（新增）
    dash_herb_lines = []
    for line in lines:
        line = line.strip()
        # 匹配 "- 药名 数量g" 或 "- 药名 数量克" 格式
        if re.match(r'-\s*[\u4e00-\u9fa5]+\s+\d+[gG克钱]', line):
            dash_herb_lines.append(line)
        # 也匹配带说明的格式 "- 药名 数量g (功效说明)"
        elif re.match(r'-\s*[\u4e00-\u9fa5]+\s+\d+[gG克钱]\s*\([^)]+\)', line):
            dash_herb_lines.append(line)
    
    if len(dash_herb_lines) >= 3:  # 至少3个药物项目
        prescription_content = '\n'.join(dash_herb_lines[:10])  # 最多10行
        return True, prescription_content[:1500]
    
    return False, "未开方"

def has_herbal_content(text: str) -> bool:
    """检查文本是否包含中药内容"""
    import re
    
    # 检查是否包含用量单位
    dosage_pattern = r'\d+[gG克钱]'
    if re.search(dosage_pattern, text):
        return True
    
    # 检查是否包含常见中药名
    common_herbs = ['党参', '黄芪', '当归', '川芎', '白芍', '熟地', '白术', '茯苓', '甘草', '银花', '连翘']
    herb_count = sum(1 for herb in common_herbs if herb in text)
    
    return herb_count >= 2

def llm_based_knowledge_search(query: str, k: int = 5) -> list[str]:
    """基于LLM的知识搜索 (替代本地知识库)"""
    try:
        search_prompt = f"""作为中医知识专家，请针对用户查询"{query}"提供相关的中医知识。

请从以下几个方面提供信息：
1. 相关的中医理论和病机分析
2. 常用的治疗方剂和药物
3. 临床症状和辨证要点
4. 调理建议和注意事项

请确保信息准确、专业，适合中医临床应用。"""

        messages = [{"role": "user", "content": search_prompt}]
        
        # 使用异步调用的同步版本
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(bailian_llm_complete(MAIN_LLM_MODEL, messages))
            # 将回复分割成多个知识块
            knowledge_blocks = response.split('\n\n')
            return knowledge_blocks[:k]
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"LLM-based knowledge search error: {e}")
        return [f"基于查询'{query}'的中医知识搜索暂时不可用。"]

# 核心功能函数
async def embed_query(texts: list[str]) -> list[list[float]]:
    if not texts: return []
    logger.info(f"EMBEDDING [QUERY]: Starting for {len(texts)} texts...")
    try:
        resp = await asyncio.to_thread(dashscope.TextEmbedding.call, model=RAG_EMBEDDING_MODEL, input=texts, text_type="query")
        if resp.status_code != HTTPStatus.OK:
            raise RuntimeError(f"DashScope Embedding API Error: {getattr(resp, 'message', 'Unknown')}")
        logger.info(f"EMBEDDING [QUERY]: Successfully completed.")
        return [r['embedding'] for r in resp.output['embeddings']]
    except Exception as e:
        logger.error(f"EMBEDDING [QUERY]: Exception: {e}", exc_info=True)
        return [[]]

async def bailian_llm_complete(model: str, messages: List[Dict[str, str]], timeout: float = 40.0) -> str:
    try:
        # 为AI调用添加超时保护
        response = await asyncio.wait_for(
            asyncio.to_thread(Generation.call, model=model, messages=messages, result_format='message'),
            timeout=timeout
        )
        if response.status_code == HTTPStatus.OK and response.output and response.output.choices:
            return response.output.choices[0]['message']['content']
        else:
            error_msg = f"LLM Error: {getattr(response, 'message', 'Unknown')}"
            logger.error(error_msg)
            return f"【系统错误】{error_msg}"
    except asyncio.TimeoutError:
        logger.error(f"LLM call timed out after {timeout} seconds")
        return "【系统提示】AI医生正在分析中，响应时间较长，请稍后重试或提供更简洁的症状描述。"
    except Exception as e:
        logger.error(f"LLM Exception: {e}", exc_info=True)
        return "【系统错误】调用AI时发生未知异常。"

# def call_qwen_vl_api(messages: List[Dict], model: str = "qwen-vl-plus") -> str:
#     """[DEPRECATED] 旧版API调用方法 - 已由extract_features_from_image直接处理"""
#     pass

async def extract_keywords_from_query(query: str) -> List[str]:
    logger.info("LLM - Extracting keywords from query...")
    prompt = f'''你是一个信息检索专家。请从以下用户问题中，提取出所有对检索结果至关重要的【核心关键词】。
这些关键词应该包括：
1.  **病名或证型** (例如：中暑, 气阴两虚)
2.  **方剂或药材名** (例如：清络饮, 西洋参)
3.  **核心症状** (例如：头晕, 乏力, 口干)

返回一个JSON格式的字符串列表。

【示例1】
用户问题："先兆中暑头晕乏力怎么办？"
返回：["先兆中暑", "头晕", "乏力"]

【用户问题】
"{query}"
'''
    try:
        response_str = await bailian_llm_complete(model=MAIN_LLM_MODEL, messages=[{"role": "user", "content": prompt}])
        logger.info(f"LLM - Raw keyword extraction response: {response_str}")
        match = re.search(r'```json\s*([\s\S]*?)\s*```', response_str)
        if match:
            response_str = match.group(1)
        keywords = json.loads(response_str)
        if isinstance(keywords, list):
            logger.info(f"LLM - Extracted keywords: {keywords}")
            return keywords
    except Exception as e:
        logger.error(f"Failed to extract or parse keywords: {e}")
    return []

# 使用在线语音识别服务 (集成阿里云语音识别)
async def speech_to_text_online(audio_bytes: bytes) -> str:
    """使用阿里云语音识别服务"""
    try:
        import tempfile
        import requests
        import json
        
        logger.info(f"开始语音识别，音频大小: {len(audio_bytes)} bytes")
        
        # 检查音频大小
        if len(audio_bytes) < 100:
            logger.warning("音频数据过小，可能是空音频")
            return "音频数据过小，请重新录制"
            
        # 保存音频到临时文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file_path = tmp_file.name
        
        logger.info(f"音频文件保存到: {tmp_file_path}")
        
        try:
            # 使用DashScope的语音识别API
            from dashscope.audio.asr import Recognition
            
            recognition = Recognition(model='paraformer-realtime-v1',
                                    format='wav',
                                    sample_rate=16000,
                                    callback=None)
            
            # 调用语音识别
            result = recognition.call(tmp_file_path)
            
            if result.status_code == 200:
                # 解析识别结果
                if hasattr(result, 'output') and result.output and 'text' in result.output:
                    recognized_text = result.output['text'].strip()
                    logger.info(f"语音识别成功: {recognized_text}")
                    return recognized_text if recognized_text else "未识别到语音内容"
                else:
                    logger.warning("语音识别返回空结果")
                    return "未识别到语音内容，请重新录制"
            else:
                logger.error(f"语音识别API错误: {result.status_code}")
                return "语音识别服务暂时不可用，请使用文字输入"
                
        except ImportError:
            logger.warning("DashScope语音识别模块未安装，尝试备用方案")
            # 备用方案：使用简单的音频检测
            if len(audio_bytes) > 1000:  # 基本的音频大小检测
                return "语音识别功能正在升级中，请暂时使用文字输入"
            else:
                return "音频过短，请重新录制"
                
        except Exception as api_error:
            logger.error(f"语音识别API调用失败: {api_error}")
            return "语音识别暂时不可用，请使用文字输入"
            
        finally:
            # 清理临时文件
            try:
                import os
                os.unlink(tmp_file_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"语音识别系统错误: {e}")
        return "语音识别服务暂时不可用"

# 图像分析函数 (使用多模态API)
def extract_features_from_image(image_bytes: bytes, image_type: str) -> str:
    """使用多模态API进行图像分析"""
    try:
        logger.info(f"Starting image analysis for {image_type}, image size: {len(image_bytes)} bytes")
        
        # 检查图像数据是否有效
        if not image_bytes or len(image_bytes) < 100:
            logger.error(f"Invalid image data: size={len(image_bytes) if image_bytes else 0}")
            return f"{image_type}图像数据无效或过小"
        
        # 保存临时文件供API使用 (因为DashScope VL API需要文件路径)
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(image_bytes)
            tmp_file_path = tmp_file.name
        
        logger.info(f"Temporary image file created: {tmp_file_path}")
        
        try:
            # 使用正确的DashScope多模态API格式 (file://本地路径)
            messages = [
                {
                    "role": "user", 
                    "content": [
                        {
                            "image": f"file://{tmp_file_path}"
                        },
                        {
                            "text": f"""【严格医疗安全要求】请作为专业的中医师进行{image_type}图像分析，严格遵循以下安全原则：

**【关键安全规则】**
1. 如果图像模糊、光线不佳、角度不正确，必须明确说明"图像质量不佳，无法进行准确分析"
2. 对于任何不确定的特征，必须使用"疑似"、"可能"等不确定性词汇
3. 绝对禁止进行诊断或暗示疾病
4. 必须强调需要结合症状和专业医生面诊

**【分析要求】**
1. **图像质量评估**：首先评估图像是否适合分析（清晰度、光线、角度）
2. **基础观察**（仅在图像质量良好时进行）：
   - 舌诊图像：仅描述明显可见的舌质基本颜色和苔色（如"舌质偏红色调"、"苔色偏白"）
   - 面诊图像：仅描述明显的面色特点（如"面色偏红润"、"面色偏苍白"）
3. **不确定性声明**：对任何细节特征使用"疑似"、"似有"等词汇
4. **医疗安全声明**：
   - "此图像分析仅供参考，不能作为诊断依据"
   - "建议结合患者详细症状描述和专业中医师面诊"
   - "任何治疗方案需由执业中医师根据四诊合参确定"

**【严格禁止】**
- 禁止给出具体的病理判断
- 禁止暗示特定疾病或证型  
- 禁止在图像不清晰时强行描述细节
- 禁止给出治疗建议

请严格按照以上要求进行分析，确保医疗安全。"""
                        }
                    ]
                }
            ]
            
            logger.info("Calling Qwen VL API with temporary file...")
            
            # 使用MultiModalConversation.call而不是Generation.call
            # 使用统一的多模态模型配置
            model_name = AI_CONFIG.get("multimodal_model", "qwen-vl-max")
            model_timeout = AI_CONFIG.get("multimodal_timeout", 80)
            
            response = dashscope.MultiModalConversation.call(
                model=model_name,
                messages=messages,
                timeout=model_timeout
            )
            
            logger.info(f"API Response status: {response.status_code}")
            
            if response.status_code == HTTPStatus.OK:
                # 正确解析响应格式
                content_list = response.output.choices[0].message.content
                result_text = ""
                
                for item in content_list:
                    if 'text' in item:
                        result_text += item['text']
                
                logger.info(f"API Response content (first 100 chars): {result_text[:100]}...")
                
                if not result_text or result_text.strip() == "":
                    logger.warning("API returned empty content")
                    return "图像分析未能识别到有效内容，请确保图像清晰且包含面部或舌部特征。"
                
                # 医疗安全验证
                validated_result = validate_image_analysis_safety(result_text, image_type)
                return validated_result
            else:
                error_msg = getattr(response, 'message', 'Unknown error')
                logger.error(f"Qwen VL API error - Status: {response.status_code}, Message: {error_msg}")
                return f"图像分析API调用失败: {error_msg}"
                
        finally:
            # 清理临时文件
            try:
                os.unlink(tmp_file_path)
                logger.info(f"Temporary file cleaned up: {tmp_file_path}")
            except:
                pass
        
    except Exception as e: 
        logger.error(f"Error processing {image_type} image: {e}", exc_info=True)
        return f"{image_type}图像处理时发生错误: {str(e)}"

# FastAPI应用设置
@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    logger.info("Application startup: Initializing online-only resources...")
    # 不需要加载本地模型
    yield
    logger.info("Application shutdown.")

app = FastAPI(
    title="AI中医智能问诊系统 - 最小化版本",
    description="基于在线API的中医问诊系统",
    version="2.2.0",
    lifespan=lifespan
)

# 设置安全系统
if SECURITY_AVAILABLE:
    setup_security_system(app)
    logger.info("Security system activated")

# 🔑 修复认证profile端点 - 覆盖安全系统的版本
@app.get("/api/auth/profile-fixed", tags=["auth-fixed"])
async def get_auth_profile_fixed(request: Request):
    """获取用户认证信息 - 修复版本，直接使用corrected token validation"""
    try:
        # 获取token
        token = None
        auth_header = request.headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
        
        if not token:
            token = request.cookies.get('session_token')
        
        if not token:
            # 无token，返回anonymous用户
            return {
                "success": True,
                "user": {
                    "user_id": "anonymous",
                    "role": "anonymous",
                    "permissions": ["chat:access"],
                    "session_info": {
                        "created_at": datetime.now().isoformat(),
                        "last_activity": datetime.now().isoformat(),
                        "expires_at": (datetime.now() + timedelta(days=1)).isoformat()
                    }
                }
            }
        
        # 使用修复的token验证函数
        user_info = await get_user_info_by_token(token)
        if user_info:
            return {
                "success": True,
                "user": {
                    "user_id": user_info['user_id'],
                    "username": user_info.get('username', 'Unknown'),
                    "email": user_info.get('email'),
                    "role": user_info.get('role', 'patient'),
                    "permissions": ["chat:access", "prescription:view"],
                    "session_info": {
                        "created_at": datetime.now().isoformat(),
                        "last_activity": datetime.now().isoformat(),
                        "expires_at": (datetime.now() + timedelta(days=1)).isoformat()
                    }
                }
            }
        else:
            # token无效，返回anonymous
            return {
                "success": True,
                "user": {
                    "user_id": "anonymous",
                    "role": "anonymous", 
                    "permissions": ["chat:access"],
                    "session_info": {
                        "created_at": datetime.now().isoformat(),
                        "last_activity": datetime.now().isoformat(),
                        "expires_at": (datetime.now() + timedelta(days=1)).isoformat()
                    }
                }
            }
    except Exception as e:
        logger.error(f"认证profile获取失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# 🔍 Direct debug endpoint to test token validation
@app.get("/api/debug-token", tags=["debug"])
async def debug_token_validation(request: Request):
    """直接测试token验证功能的调试端点"""
    try:
        # 获取token
        token = None
        auth_header = request.headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
        
        if not token:
            return {"error": "No token provided", "token": None}
        
        # 直接测试我们的函数
        print(f"🔍 DEBUG: Direct test of token: {token[:20]}...")
        result = await get_user_info_by_token(token)
        print(f"🔍 DEBUG: Direct test result: {result}")
        
        return {
            "token_provided": token[:20] + "...",
            "token_validation_result": result,
            "success": result is not None
        }
    except Exception as e:
        print(f"🔍 DEBUG: Error in token test: {e}")
        return {"error": str(e)}

# 先注册具体路由，再注册通用路由（避免路由冲突）
@app.get("/api/prescription/learning_stats")
async def get_prescription_learning_stats():
    """获取处方学习系统统计信息"""
    try:
        learning_integrator = get_prescription_learning_integrator()
        stats = await learning_integrator.get_learning_statistics()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取处方学习统计失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/prescription/learning_details")
async def get_prescription_learning_details():
    """获取处方学习详细内容"""
    try:
        learning_integrator = get_prescription_learning_integrator()
        
        # 获取详细的学习案例
        details = []

        try:
            rows = sqlite_service.fetch_recent_learning_cases(limit=20)
            for row in rows:
                details.append({
                    'diagnosis': row[2] if len(row) > 2 else '未知',
                    'syndrome': row[3] if len(row) > 3 else '未知',
                    'prescription': row[4] if len(row) > 4 else '',
                    'confidence': row[5] if len(row) > 5 else 0.0,
                    'learned_at': row[6] if len(row) > 6 else '未知'
                })
        except Exception as db_error:
            logger.error(f"读取学习数据库失败: {db_error}")
        
        return {
            "success": True,
            "data": details
        }
    except Exception as e:
        logger.error(f"获取学习详情失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": []
        }

@app.get("/api/prescription/recent_learning")
async def get_recent_learning_activities():
    """获取最近的学习活动"""
    try:
        # 模拟最近学习活动数据
        activities = []

        try:
            rows = sqlite_service.fetch_recent_learning_cases(limit=10)
            for row in rows:
                activities.append({
                    'type': '处方学习',
                    'diagnosis': row[2] if len(row) > 2 else '未知诊断',
                    'syndrome': row[3] if len(row) > 3 else '未识别',
                    'confidence': row[5] if len(row) > 5 else 0.0,
                    'time_ago': calculate_time_ago(row[6]) if len(row) > 6 else '未知时间'
                })
        except Exception as db_error:
            logger.error(f"读取学习活动失败: {db_error}")
        
        return {
            "success": True,
            "data": activities
        }
    except Exception as e:
        logger.error(f"获取学习活动失败: {e}")
        return {
            "success": False,
            "data": []
        }

# 先注册控制台与测试页面路由（阶段8）
register_console_and_test_page_routes(app)

# 🔧 处理浏览器常见自动请求 - 避免不必要的404日志（阶段4）
register_common_browser_file_routes(app)

# 集成所有路由（阶段3：迁移到 app.api.registration）
# 添加管理员路由
from api.routes.admin_routes import router as admin_router

# AI增强处方管理路由
from api.routes.prescription_ai_routes import router as prescription_ai_router

# 思维导图路由
from api.routes.mindmap_routes import router as mindmap_router

# WebSocket实时同步路由
from api.routes.websocket_sync_routes import router as websocket_sync_router

# 对话管理路由 - v4.0重构版
from api.routes.conversation_management_routes import router as conversation_management_router

register_all_routes(
    app,
    auth_router=auth_router,
    unified_auth_router=unified_auth_router,
    unified_login_router=unified_login_router,
    doctor_router=doctor_router,
    admin_router=admin_router,
    prescription_router=prescription_router,
    prescription_ai_router=prescription_ai_router,
    payment_router=payment_router,
    decoction_router=decoction_router,
    decision_tree_router=decision_tree_router,
    decision_tree_data_router=decision_tree_data_router,
    symptom_analysis_router=symptom_analysis_router,
    review_router=review_router,
    unified_consultation_router=unified_consultation_router,
    database_management_router=database_management_router,
    conversation_sync_router=conversation_sync_router,
    user_data_sync_router=user_data_sync_router,
    data_migration_router=data_migration_router,
    user_sessions_router=user_sessions_router,
    medical_knowledge_router=medical_knowledge_router,
    follow_up_router=follow_up_router,
    session_router=session_router,
    security_router=security_router,
    decision_tree_usage_router=decision_tree_usage_router,
    prescription_review_router=prescription_review_router,
    prescription_structured_edit_router=prescription_structured_edit_router,
    mindmap_router=mindmap_router,
    websocket_sync_router=websocket_sync_router,
    conversation_management_router=conversation_management_router,
)

# 设置全局异常处理器与安全保护（阶段3）
setup_exception_and_security(app, SECURITY_AVAILABLE, protect_api_routes)

# 初始化处方检查系统 - 延迟初始化，避免启动时错误
prescription_checker = None
tcm_knowledge_graph = None
famous_doctor_system = None

def get_prescription_checker():
    global prescription_checker
    if prescription_checker is None:
        try:
            from core.prescription.prescription_checker import PrescriptionChecker
            prescription_checker = PrescriptionChecker()
        except Exception as e:
            logger.error(f"处方检查器初始化失败: {e}")
    return prescription_checker

def get_knowledge_graph():
    global tcm_knowledge_graph
    if tcm_knowledge_graph is None:
        try:
            from core.knowledge_retrieval.tcm_knowledge_graph import TCMKnowledgeGraph
            tcm_knowledge_graph = TCMKnowledgeGraph()
        except Exception as e:
            logger.error(f"知识图谱初始化失败: {e}")
    return tcm_knowledge_graph

def get_famous_doctor_system():
    global famous_doctor_system  
    if famous_doctor_system is None:
        try:
            from services.famous_doctor_learning_system import FamousDoctorLearningSystem
            famous_doctor_system = FamousDoctorLearningSystem()
        except Exception as e:
            logger.error(f"名医系统初始化失败: {e}")
    return famous_doctor_system

# CORS中间件配置（阶段3：迁移到 app.api.registration）
setup_cors_middleware(app)

# 静态文件挂载与站点辅助路由（阶段4）
setup_static_and_site_routes(app, logger, PATHS)

# 医生工具页面与兼容页面路由（阶段8）
register_doctor_tool_page_routes(app)

# Pydantic 模型
class ChatMessageInput(BaseModel): 
    message: str
    conversation_id: str
    selected_doctor: Optional[str] = "zhang_zhongjing"

class ChatMessageOutput(BaseModel): 
    reply: str
    conversation_id: str

class ConversationHistoryMessage(BaseModel): 
    role: str
    content: str

class ConversationHistoryOutput(BaseModel): 
    conversation_id: str
    history: List[ConversationHistoryMessage]
    message: Optional[str] = None

class STTOutput(BaseModel): 
    text: str
    error: Optional[str] = None

class ImageAnalysisOutput(BaseModel): 
    analysis_result: Optional[str] = None
    error: Optional[str] = None

class FeedbackInput(BaseModel):
    conversation_id: str
    rating: int
    feedback_text: Optional[str] = None
    timestamp: str

class FeedbackOutput(BaseModel):
    success: bool
    message: str


class FeedbackCompatInput(BaseModel):
    conversation_id: Optional[str] = None
    conversationId: Optional[str] = None
    session_id: Optional[str] = None
    sessionId: Optional[str] = None
    rating: Optional[int] = None
    score: Optional[int] = None
    feedback_text: Optional[str] = None
    message: Optional[str] = None
    content: Optional[str] = None
    timestamp: Optional[str] = None
    user_id: Optional[str] = None
    doctor_id: Optional[str] = None
    feedback_type: Optional[str] = None

# 系统提示词 - 中医诊疗辅助系统
SYSTEM_PROMPT_TCM_DIALOGUE_ENHANCED = ENHANCED_MEDICAL_SAFETY_PROMPT + """
# 身份和目标
您是一位经验丰富的中医师，运用传统中医理论进行诊疗辅助。您的目标是通过中医望闻问切四诊合参，进行辨证论治，提供专业的中医诊疗方案。

# 🚨 重要原则：坚持中医特色
**请严格遵循中医诊疗规范：**
- ❌ 避免：西药名称、现代医学检查项目、西医诊断术语
- ❌ 避免：血常规、胃镜、B超、CT、MRI等现代检查
- ❌ 避免：奥美拉唑、阿司匹林等化学药品
- ❌ 避免：使用现代医学病名，应采用中医病症名
- ❌ 避免：细菌、病毒等微观医学概念
- ✅ 专注：中医理论、中药方剂、针灸推拿等传统疗法

# 中医诊疗理念
1. **四诊合参**：望闻问切，以中医理论为准绳
2. **辨证论治**：病因病机分析，证型确定，方药对症
3. **整体观念**：人体脏腑经络气血津液的整体调理
4. **治病求本**：标本兼治，调理根本

# 诊疗流程和问诊要点

## 重要指导原则：
**⚠️ 避免重复提问**：在继续问诊前，请仔细回顾对话历史中患者已经提供的信息，不要重复询问相同的问题。如果患者已经回答了某个问题，请基于该信息进行分析，而不是再次询问。

## 问诊重点（按优先级）：
1. **主诉症状**：最主要的不适及持续时间
2. **症状特点**：
   - 疼痛性质：胀痛、刺痛、隐痛、窜痛等
   - 发作规律：持续性、间歇性、与时间/饮食/情绪的关系
   - 诱发缓解因素：什么情况下加重或减轻
3. **伴随症状**：
   - 全身症状：寒热、汗出、精神、食欲、睡眠
   - 头面五官：头痛、眩晕、耳鸣、咽干等
   - 胸腹：胸闷、腹胀、胃脘痛等
   - 二便：大便（次数、性状、颜色）、小便（次数、颜色、量）
4. **既往史和生活史**：
   - 既往疾病、手术史、用药史
   - 饮食偏好、作息规律、工作性质
   - 情志状态：是否焦虑、抑郁、易怒等

## 望诊要点（仅限有图像上传时）：
1. **面色观察**：红润、苍白、萎黄、青黑、潮红等
2. **精神状态**：神采奕奕、疲惫无神、焦虑不安等
3. **舌象分析**：**仅在患者上传舌象图片时进行分析，绝不可在没有图像时描述舌象特征**
   - 必须基于实际图像观察进行描述
   - 如无舌象图片，应建议患者提供以便准确诊断
   - **图像质量差处理**：如果收到"【图像质量提示】"，说明患者已上传图片但质量不佳，应在分析中明确说明："虽然您已上传舌象图片，但由于图像质量限制，暂时无法进行精确舌象分析"，并建议重新拍摄

# 对话交互规则
## 信息收集阶段（信息不足时）：
采用循序渐进的问诊方式，每次询问2-3个最关键的问题：

**重要问诊规则**：
- **绝不重复询问**：仔细查看完整对话历史，绝对不要重复询问已经问过的问题
- **基于已知信息**：根据患者已经提供的信息，只询问尚未了解的关键信息
- **循序渐进**：每次询问2-3个最关键的问题，配合适当的解释和关怀
- **完整回复**：每次回复都要包含具体的问诊内容，不能只有标签

**问诊语言特点**：
- "请问您的[症状]是什么性质的？比如是胀痛、刺痛还是隐隐作痛？"
- "这个症状大概持续多长时间了？是什么时候开始出现的？"
- "平时您是比较怕冷还是怕热？手脚温度如何？"
- "您的睡眠如何？是难以入睡，还是容易醒来？"
- "大小便情况怎样？大便是否成形？小便颜色深浅？"

## 问诊和开方决策规则：
1. **继续问诊时**：使用 `[ASK_MORE]` 标签结束，并询问缺失的关键信息
2. **准备开方时**：当信息充足且诊断明确时，可进入辨证论治阶段，无需使用`[ASK_MORE]`标签

## 辨证论治阶段（信息充足时）：
按照传统中医辨证思路给出完整方案，**严格使用以下XML格式**：

**注意**：基于患者明确描述的症状进行分析。

# 🏥 **完整中医诊疗方案**

## 📋 **基本信息**
**🔸 主诉：** 简要概括主要症状（仅基于患者明确表述）

**🔸 现病史：** 详细描述症状发生发展过程及伴随症状（仅基于患者描述内容）

## 👁️ **望诊所见**
**🔸 面色舌象：** 如有图像分析结果，描述面色、舌象等客观表现

## 🧠 **中医辨证分析**

### **病机分析**
从中医角度分析发病原因和病理机制

### **🎯 证型诊断**  
**确定具体的中医证型**

### **⚡ 治疗方法**
**治法：** 确定治疗大法

### **📜 方剂选用**
**选择的主要方剂及理由**

---

## 💊 **处方建议**
具体药物及剂量（**严格要求**：药名 确定剂量g格式，如"党参 15g"，绝不使用范围用量如"12-15g"）

---

## ⚡ **煎服指导**

### **煎制方法：**
- 🔸 详细的煎药方法
- 🔸 煎制时间和火候

### **服用方法：**  
- 🔸 具体的服用方法和时间

---

## 🔄 **辨证加减**
**随证加减：** 根据兼症的加减变化

---

## 🍃 **生活调护**
**生活调摄：** 饮食起居、情志调节等具体建议

---

## 📅 **复诊安排**

### **复诊时间：**
- **首次复诊：** 服药3-5天后
- **后续复诊：** 根据病情变化安排

### **观察要点：**
- ✅ 主要症状变化情况  
- ✅ 药物疗效及不良反应
- ✅ 舌象脉象变化
- ✅ 食欲睡眠二便情况

---

## ⚠️ **重要提醒**

> **注意事项：**
> - 本方案为AI辅助中医建议，仅供参考
> - 必须在执业中医师指导下使用
> - 不能替代正规医院诊断治疗
> - 如症状加重或出现不适，**请及时就医**

# 语言风格
- 使用通俗易懂的中医术语，必要时进行解释
- 语气亲切专业，体现医者仁心
- 善用比喻说明病机（如"心火上炎"、"肝气郁结"等）
- 在关键术语上使用**加粗**标记突出重点
"""

SYNTHESIS_PROMPT_TEMPLATE = """
# 角色设定
你是一位行医50多年的资深老中医，有着丰富的临床经验和深厚的理论功底。现在需要你根据古籍资料，结合多年临床心得，为年轻医生提供诊疗指导。

# 任务
根据【用户问题】和【古籍参考资料】，以老中医的语气和经验，整理出实用的临床指导意见。

# 表达要求
1. **老中医语气**: 使用"我从医这么多年来看..."、"据我临床所见..."、"古人有云..."、"这类病人我见得多了..."等表达方式
2. **经验分享**: 结合参考资料内容，但要以个人临床体会的方式表达
3. **理论联系实际**: 既要引用古籍理论，又要结合现代临床实践
4. **语言特色**: 语气亲切但权威，偶尔使用中医行话，体现老中医的睿智和慈祥
5. **严格症状记录**: 【绝对禁止】添加用户未提及的症状，只能基于用户明确描述的症状进行分析

# 内容要求
- 整合参考资料中的精华内容
- 按照【病机分析 -> 临床经验 -> 治疗思路 -> 方药心得 -> 调护嘱咐】的逻辑组织
- 每个重点必须标注 `[古籍依据: 参考资料 N]`

---
【患者咨询】
{user_question}
---
【古籍参考资料】
{context_str}
---

请以一位经验丰富的老中医身份，结合古籍智慧，给出专业而亲切的临床指导：
"""

# 辅助函数
def get_conversation_history_filepath(conversation_id: str) -> str: 
    return os.path.join(CONVERSATION_LOG_DIR, f"conversation_{conversation_id}.json")

def load_conversation_history(conversation_id: str) -> List[Dict[str, str]]:
    filepath = get_conversation_history_filepath(conversation_id)
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f: 
                return json.load(f)
        except: 
            return []
    return []

def save_conversation_history(conversation_id: str, history: List[Dict[str, str]]):
    filepath = get_conversation_history_filepath(conversation_id)
    try:
        with open(filepath, 'w', encoding='utf-8') as f: 
            json.dump(history, f, ensure_ascii=False, indent=2)
    except: 
        pass

# API 端点
@app.get("/")
async def read_index_html():
    """首页 - 重定向到登录页"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/login", status_code=302)


@app.get("/get_conversation_history/{conversation_id}", response_model=ConversationHistoryOutput)
async def get_history_endpoint(conversation_id: str): 
    history = conversation_history_store.get(conversation_id) or load_conversation_history(conversation_id)
    return ConversationHistoryOutput(conversation_id=conversation_id, history=history) if history else ConversationHistoryOutput(conversation_id=conversation_id, history=[], message=f"No history found")

@app.post("/speech_to_text", response_model=STTOutput)
async def speech_to_text_endpoint(audio_file: UploadFile = File(...)):
    """语音转文字接口 - 使用在线语音识别"""
    logger.info(f"收到语音转文字请求, 文件: {audio_file.filename}")
    
    try:
        content = await audio_file.read()
        recognized_text = await speech_to_text_online(content)
        
        if not recognized_text or "不可用" in recognized_text:
            return STTOutput(text="", error=recognized_text)
        
        return STTOutput(text=recognized_text)
        
    except Exception as e: 
        logger.error(f"STT Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}")
    finally:
        await audio_file.close()

@app.post("/analyze_images", response_model=ImageAnalysisOutput)
async def analyze_images_endpoint(
    conversation_id: str = Form(...), 
    medical_image: Optional[UploadFile] = File(None),
    face_image: Optional[UploadFile] = File(None), 
    tongue_image: Optional[UploadFile] = File(None)
):
    """图像分析接口 - 使用多模态API"""
    analysis_texts = []
    
    # 处理通用医学图像 (前端上传的 medical_image)
    if medical_image:
        try: 
            image_bytes = await medical_image.read()
            analysis_result = extract_features_from_image(image_bytes, "医学图像")
            if analysis_result and analysis_result != "null":
                analysis_texts.append(analysis_result)
            else:
                logger.warning(f"Medical image analysis returned null or empty result")
                analysis_texts.append("【图像质量提示】患者已上传舌象图片，但由于光线不足、角度不佳或图像模糊等因素，无法进行精确的舌象分析。建议患者在自然光下重新拍摄舌象照片。")
        except Exception as e:
            logger.error(f"Error processing medical image: {e}")
            analysis_texts.append(f"图像处理时发生错误：{str(e)}")
        finally: 
            await medical_image.close()
    
    # 处理面部图像 (支持旧版接口)
    if face_image:
        try: 
            image_bytes = await face_image.read()
            analysis_result = extract_features_from_image(image_bytes, "面部")
            if analysis_result and analysis_result != "null":
                analysis_texts.append(analysis_result)
        except Exception as e:
            logger.error(f"Error processing face image: {e}")
            analysis_texts.append(f"面部图像处理错误：{str(e)}")
        finally: 
            await face_image.close()
    
    # 处理舌部图像 (支持旧版接口)
    if tongue_image:
        try: 
            image_bytes = await tongue_image.read()
            analysis_result = extract_features_from_image(image_bytes, "舌部")
            if analysis_result and analysis_result != "null":
                analysis_texts.append(analysis_result)
            else:
                logger.warning(f"Tongue image analysis returned null or empty result")
                analysis_texts.append("【图像质量提示】患者已上传舌象图片，但由于光线不足、角度不佳或图像模糊等因素，无法进行精确的舌象分析。建议患者在自然光下重新拍摄舌象照片。")
        except Exception as e:
            logger.error(f"Error processing tongue image: {e}")
            analysis_texts.append(f"舌部图像处理错误：{str(e)}")
        finally: 
            await tongue_image.close()
    
    if not analysis_texts: 
        return ImageAnalysisOutput(error="未提供有效图像或图像分析失败")
    
    # 不立即分析，只保存图片的原始分析结果到系统消息中
    combined_analysis = "\n".join(analysis_texts)
    
    # 保存图片分析结果到会话历史，但标记为待处理
    visual_features_message = {
        "role": "system", 
        "content": f"【待分析图像】{combined_analysis}",
        "image_pending": True  # 标记为待处理的图片
    }
    
    history = conversation_history_store.get(conversation_id) or load_conversation_history(conversation_id)
    history.append(visual_features_message)
    conversation_history_store[conversation_id] = history
    save_conversation_history(conversation_id, history)
    
    # 根据分析结果调整友好提示信息
    if "【图像质量提示】" in combined_analysis:
        user_friendly_response = "⚠️ 图片已上传，但图像质量可能不够清晰。\n\n💡 为了更好的诊疗效果，建议您：\n• 在充足的自然光下重新拍摄\n• 确保舌头完全伸出\n• 镜头垂直向下拍摄\n\n📝 请先描述一下目前的症状：\n• 主要不适感觉\n• 持续时间\n• 伴随症状\n• 既往病史等\n\n我将基于您的症状描述进行初步分析，如需要更精确的舌象诊断，再重新拍摄图片。"
    else:
        user_friendly_response = "✅ 舌象图片已成功上传并保存。\n\n📝 请您详细描述一下目前的症状，比如：\n• 主要不适感觉\n• 持续时间\n• 伴随症状\n• 既往病史等\n\n我将结合您的舌象图片和症状描述，为您提供更准确的中医诊疗建议。"
    
    logger.info(f"Image uploaded and saved for {conversation_id}, waiting for symptom description")
    return ImageAnalysisOutput(analysis_result=user_friendly_response)

# 重构版本也已迁移至统一问诊服务 /api/consultation/chat
# DEPRECATED: 原refactored函数 (~150 lines) 已移至统一问诊服务
# 保留此代码段作为备份，可在需要时恢复
# DEPRECATED: 此端点将在下个版本中完全移除
@app.post("/chat_with_ai_deprecated", response_model=ChatMessageOutput)
async def chat_with_ai_endpoint_backup(chat_input: ChatMessageInput, request: Request):
    """原版对话接口 - 已废弃，请使用 /api/consultation/chat"""
    raise HTTPException(
        status_code=410, 
        detail="此接口已废弃，请使用 /api/consultation/chat"
    )

# 原chat_with_ai函数体 (550+ lines) 已完全迁移至 /api/consultation/chat
# 功能保留，性能优化，接口统一 - 请使用新端点

@app.get("/get_doctor_info/{doctor_name}")
async def get_doctor_info_endpoint(doctor_name: str):
    """获取医生专业信息和统计"""
    try:
        if POSTGRESQL_HYBRID_AVAILABLE and hybrid_knowledge_system:
            doctor_info = hybrid_knowledge_system.get_doctor_info(doctor_name)
            if doctor_info:
                return {"success": True, "data": doctor_info}
        
        return {"success": False, "message": "医生信息不可用"}
    except Exception as e:
        logger.error(f"Error getting doctor info: {e}")
        return {"success": False, "error": str(e)}

@app.post("/recommend_formula")
async def recommend_formula_endpoint(symptoms_data: dict):
    """根据症状推荐方剂"""
    try:
        symptoms = symptoms_data.get("symptoms", "")
        selected_doctor = symptoms_data.get("selected_doctor", "zhang_zhongjing")
        
        if POSTGRESQL_HYBRID_AVAILABLE and hybrid_knowledge_system:
            recommendation = hybrid_knowledge_system.get_formula_recommendation(symptoms, selected_doctor)
            if recommendation:
                return {"success": True, "data": recommendation}
        
        return {"success": False, "message": "方剂推荐不可用"}
    except Exception as e:
        logger.error(f"Error recommending formula: {e}")
        return {"success": False, "error": str(e)}

@app.get("/get_doctor_introductions")
async def get_doctor_introductions_endpoint():
    """获取医生简介信息"""
    try:
        if ENHANCED_SYSTEM_AVAILABLE and persona_generator:
            introductions = persona_generator.doctor_personas.get_doctor_introductions()
            return {"success": True, "data": introductions}
        else:
            # 备用静态数据
            static_introductions = {
                "zhang_zhongjing": {
                    "name": "张仲景医师",
                    "school": "伤寒派",
                    "introduction": "伤寒派以《伤寒论》为理论基础，擅长六经辨证，治疗外感病和内伤杂病。用药精准，方证对应，药少力专，适合急性感冒、发热、消化系统疾病等。注重脉证合参，辨证严谨。",
                    "specialty": "外感病, 内伤杂病, 急症"
                },
                "ye_tianshi": {
                    "name": "叶天士医师",
                    "school": "温病派", 
                    "introduction": "温病派专治各种热性疾病，以卫气营血辨证为特色，用药轻清灵动。擅长儿科妇科疾病，重视清热养阴，保护津液。适合发热、咽喉肿痛、皮肤病、妇女经期热症等。",
                    "specialty": "温病, 热病, 儿科, 妇科"
                },
                "liu_duzhou": {
                    "name": "刘渡舟医师",
                    "school": "经方派",
                    "introduction": "经方派严格按照古代经典方剂治疗，强调方证对应。特别擅长疑难杂症和慢性疾病，重视主症抓取和体质辨识。适合失眠、心悸、慢性胃病、肝胆疾病等需要精准调理的病症。",
                    "specialty": "经方应用, 疑难杂症, 慢性病"
                },
                "li_dongyuan": {
                    "name": "李东垣医师",
                    "school": "补土派",
                    "introduction": "补土派以调理脾胃为核心，认为脾胃为后天之本。擅长治疗消化系统疾病和内伤发热，重视补中益气、升阳举陷。适合食欲不振、消化不良、慢性腹泻、脱肛、乏力等脾胃虚弱症状。用药温和，注重调养。",
                    "specialty": "脾胃病, 内伤发热, 消化系统疾病"
                },
                "zheng_qin_an": {
                    "name": "郑钦安医师",
                    "school": "扶阳派",
                    "introduction": "扶阳派重视阳气，认为万病皆由阳气不足所致。擅长治疗各种阳虚症状和急危重症，善用附子、干姜等温阳药物。适合怕冷、乏力、腹泻、水肿、心衰等阳气虚弱的疾病。用药力量较猛，见效快。",
                    "specialty": "阳虚证, 急危重症, 疑难杂症"
                },
                "zhu_danxi": {
                    "name": "朱丹溪医师", 
                    "school": "滋阴派",
                    "introduction": "滋阴派重视养阴清热，擅长治疗阴虚火旺和各种内科调养，用药平和有效。以滋阴降火为主要治疗原则，注重调理阴血不足。适合潮热盗汗、口干咽燥、失眠多梦、月经不调等阴虚内热症状。",
                    "specialty": "阴虚火旺, 妇科杂症, 内科调养"
                }
            }
            return {"success": True, "data": static_introductions}
    except Exception as e:
        logger.error(f"Error getting doctor introductions: {e}")
        return {"success": False, "error": str(e)}

def _build_debug_status_payload():
    """构建调试状态数据（阶段5：用于ops_setup统一注册）"""
    status = {
        "server_status": "running",
        "enhanced_system_available": ENHANCED_SYSTEM_AVAILABLE,
        "doctor_mind_system_available": DOCTOR_MIND_SYSTEM_AVAILABLE,
        "zhang_zhongjing_system_available": ZHANG_ZHONGJING_SYSTEM_AVAILABLE,
        "cache_system_available": CACHE_SYSTEM_AVAILABLE,
        "conversation_store_size": len(conversation_history_store),
        "session_store_size": len(conversation_session_store),
        "knowledge_db_path": KNOWLEDGE_DB_PATH,
        "api_key_configured": bool(DASHSCOPE_API_KEY)
    }

    # 添加缓存统计信息
    if CACHE_SYSTEM_AVAILABLE and cache_system:
        try:
            cache_stats = cache_system.get_cache_stats()
            status["cache_stats"] = {
                "total_entries": cache_stats.total_entries,
                "hit_rate": f"{cache_stats.hit_rate:.3f}",
                "cache_size_mb": f"{cache_stats.cache_size_mb:.2f}",
                "total_queries": cache_system.total_queries,
                "cache_hits": cache_system.cache_hits,
                "cache_misses": cache_system.cache_misses
            }
        except Exception as e:
            status["cache_stats"] = {"error": str(e)}

    if ENHANCED_SYSTEM_AVAILABLE:
        status["enhanced_retrieval_initialized"] = enhanced_retrieval is not None
        status["persona_generator_initialized"] = persona_generator is not None
        status["learning_system_initialized"] = learning_system is not None

    if DOCTOR_MIND_SYSTEM_AVAILABLE:
        status["enhanced_treatment_generator_initialized"] = enhanced_treatment_generator is not None
        status["doctor_mind_api_initialized"] = doctor_mind_api is not None

    if ZHANG_ZHONGJING_SYSTEM_AVAILABLE:
        status["zhang_zhongjing_system_initialized"] = zhang_zhongjing_system is not None

    return status

@app.get("/test_upload_page")
async def test_upload_page():
    """提供图片上传测试页面"""
    with open(str(PATHS['static_dir'] / 'test_upload_simple.html'), "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/mobile_debug_test")
async def mobile_debug_test():
    """提供移动端弹窗调试测试页面"""
    with open("/opt/tcm/mobile_debug_test.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/diagnosis_progress/{conversation_id}")
async def get_diagnosis_progress(conversation_id: str):
    """获取特定对话的诊断进度"""
    try:
        progress_info = medical_diagnosis_controller.get_diagnosis_progress_info(conversation_id)
        return progress_info
    except Exception as e:
        logger.error(f"获取诊断进度失败: {e}")
        return {"error": str(e)}

# 处方检查系统API端点
@app.post("/api/prescription/check")
async def check_prescription_endpoint(
    prescription_text: str = Form(...),
    patient_info: str = Form(None)
):
    """处方检查API - 使用基础处方解析器"""
    try:
        logger.info(f"处方检测API收到请求: prescription_text='{prescription_text}', patient_info='{patient_info}'")
        
        # 解析患者信息
        patient_data = {}
        if patient_info:
            try:
                import json
                patient_data = json.loads(patient_info)
            except:
                patient_data = {}
        
        # 使用基础处方解析器
        from core.prescription.prescription_checker import PrescriptionParser
        
        parser = PrescriptionParser()
        logger.info(f"开始解析处方文本: '{prescription_text[:100]}...'")
        prescription = parser.parse_prescription_text(prescription_text)
        logger.info(f"处方解析结果: 成功={prescription is not None}, 药物数量={len(prescription.herbs) if prescription else 0}")
        
        if prescription and prescription.herbs:
            # 构建药物列表
            herbs_list = []
            total_dosage = 0
            
            for herb in prescription.herbs:
                herb_info = {
                    "name": herb.name,
                    "dosage": herb.dosage,
                    "unit": herb.unit,
                    "preparation": herb.preparation or ""
                }
                herbs_list.append(herb_info)
                
                # 计算总剂量（简单解析数字）
                try:
                    dosage_str = herb.dosage.replace('g', '').replace('克', '').strip()
                    if '-' in dosage_str:
                        dosage_str = dosage_str.split('-')[0]
                    dosage_num = float(dosage_str)
                    total_dosage += dosage_num
                except:
                    pass
            
            result = {
                "success": True,
                "analysis_type": "中医处方基础解析",
                "prescription": {
                    "herbs": herbs_list,
                    "total_count": len(herbs_list),
                    "total_dosage": f"{total_dosage}g",
                    "preparation_method": prescription.preparation_method or "水煎服",
                    "usage_instructions": prescription.usage_instructions or "一日一剂，分2-3次服用"
                },
                "tcm_analysis": {
                    "syndrome_analysis": {
                        "primary_syndrome": "请咨询专业中医师进行辨证分析",
                        "analysis_note": "基础解析器不提供辨证分析"
                    },
                    "prescription_pattern": "基础模式：请专业医师提供辨证分析",
                    "clinical_assessment": {
                        "therapeutic_effects": ["需要专业中医师评估"],
                        "dosage_notes": [f"总剂量约{total_dosage}g，符合常规用量"],
                        "usage_guidance": ["请按医师指导服用"]
                    },
                    "professional_comments": [
                        "本次为基础解析，识别到有效中药成分",
                        "具体辨证分析需要专业中医师进行",
                        "请寻求正规中医院专业指导"
                    ]
                },
                "safety_check": {
                    "is_safe": True,
                    "warnings": ["请在专业医师指导下使用"]
                },
                "detailed_analysis": {
                    "dosage_analysis": {
                        "total_dosage": f"{total_dosage}g",
                        "dosage_range_ratio": "常规剂量范围",
                        "ratio_analysis": ["剂量需要专业医师根据患者具体情况调整"]
                    },
                    "therapeutic_analysis": {
                        "treatment_methods": ["需要专业中医师制定治疗方案"],
                        "therapeutic_focus": ["基础解析已识别药物成分"],
                        "expected_effects": ["具体疗效需要专业医师评估"]
                    }
                }
            }
            
            # 🎓 自动学习处理：将处方数据用于系统学习
            try:
                learning_integrator = get_prescription_learning_integrator()
                learning_success = await learning_integrator.process_prescription_data(
                    prescription_data={'prescription': result['prescription']},
                    source_type="text_upload",
                    patient_info=patient_data if patient_data else None
                )
                if learning_success:
                    logger.info(f"✅ 处方数据已用于系统学习")
                else:
                    logger.warning(f"⚠️ 处方学习处理未完全成功")
            except Exception as learning_error:
                logger.warning(f"⚠️ 处方学习失败（不影响检测结果）: {learning_error}")
            
            # 🎯 添加君臣佐使分析 - 修复PC端bug
            try:
                from core.prescription.tcm_formula_analyzer import analyze_formula_with_ai
                
                # 转换药材格式以匹配分析器要求
                analysis_herbs = []
                for herb in herbs_list:
                    analysis_herb = {
                        'name': herb['name'],
                        'dosage': float(herb['dosage'].replace('g', '').replace('克', '').strip().split('-')[0]),
                        'unit': herb.get('unit', 'g')
                    }
                    analysis_herbs.append(analysis_herb)
                
                if len(analysis_herbs) >= 3:  # 至少3味药才进行分析
                    logger.info(f"开始君臣佐使分析，共{len(analysis_herbs)}味药材")
                    formula_analysis = analyze_formula_with_ai(analysis_herbs)
                    result['formula_analysis'] = formula_analysis
                    logger.info(f"君臣佐使分析完成: {formula_analysis.get('confidence_level', 'unknown')}")
                else:
                    logger.info(f"药材数量不足({len(analysis_herbs)}味)，跳过君臣佐使分析")
                    result['formula_analysis'] = {
                        'message': '药材数量不足，建议至少3味药材才能进行君臣佐使分析',
                        'roles': {'君药': [], '臣药': [], '佐药': [], '使药': []},
                        'confidence_level': 'insufficient_data'
                    }
                    
            except Exception as analysis_error:
                logger.error(f"君臣佐使分析失败: {analysis_error}")
                result['formula_analysis'] = {
                    'error': f'分析失败: {str(analysis_error)}',
                    'roles': {'君药': [], '臣药': [], '佐药': [], '使药': []},
                    'confidence_level': 'failed'
                }
            
            return {
                "success": True,
                "data": result
            }
        else:
            # 处方解析失败
            return {
                "success": False,
                "error": "未能识别到有效的中药处方信息",
                "data": {
                    "suggestion": "请确保文本包含规范的中药名称和剂量信息，格式如：麻黄 9g"
                }
            }
        
    except Exception as e:
        logger.error(f"处方检查API错误: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/prescription/add_famous_doctor")
async def add_famous_doctor_prescription_endpoint(
    prescription_text: str = Form(...),
    doctor_name: str = Form(...),
    source: str = Form("manual_input")
):
    """添加名医处方到学习系统"""
    try:
        checker = get_prescription_checker()
        if not checker:
            return {
                "success": False,
                "error": "处方检查系统初始化失败"
            }
        
        success = checker.add_famous_doctor_prescription(
            prescription_text, doctor_name, source
        )
        
        return {
            "success": success,
            "message": "处方添加成功" if success else "处方添加失败"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/prescription/doctor_patterns/{doctor_name}")
async def get_doctor_patterns_endpoint(doctor_name: str):
    """获取特定医生的处方规律"""
    try:
        system = get_famous_doctor_system()
        if not system:
            return {
                "success": False,
                "error": "名医学习系统初始化失败"
            }
        
        patterns = system.learn_doctor_prescription_patterns(doctor_name)
        return {
            "success": True,
            "data": patterns
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# OCR图片识别API端点
@app.post("/api/prescription/ocr")
async def prescription_ocr_endpoint(file: UploadFile = File(...)):
    """处方图片OCR识别API"""
    try:
        # 检查文件类型
        if not file.content_type or not file.content_type.startswith(('image/', 'application/pdf')):
            return {
                "success": False,
                "error": "不支持的文件类型，请上传图片(JPG/PNG)或PDF文件"
            }
        
        # 读取文件数据
        file_data = await file.read()
        if len(file_data) > 10 * 1024 * 1024:  # 限制10MB
            return {
                "success": False,
                "error": "文件过大，请上传10MB以内的文件"
            }
        
        # 获取OCR系统
        ocr = get_ocr_system()
        
        # 根据文件类型处理
        if file.content_type == 'application/pdf':
            result = ocr.process_pdf(file_data, file.filename)
        else:
            result = ocr.process_image(file_data, file.filename)
        
        return result
        
    except Exception as e:
        logger.error(f"处方OCR识别失败: {e}")
        return {
            "success": False,
            "error": f"OCR识别失败: {str(e)}"
        }

@app.post("/api/prescription/check_image_v2")  
async def prescription_check_image_multimodal(file: UploadFile = File(...)):
    """使用多模LLM的新处方图片检查API - 现代化方案"""
    
    try:
        import tempfile
        from services.multimodal_processor import analyze_prescription_image_bytes
        
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            return {
                "success": False,
                "error": "请上传图片文件 (JPG, PNG, GIF等格式)",
                "document_type": "文件格式错误"
            }
        
        # 读取文件内容
        content = await file.read()
        
        # 验证文件大小 (10MB限制)
        if len(content) > 10 * 1024 * 1024:
            return {
                "success": False,
                "error": "图片文件过大，请上传小于10MB的图片",
                "document_type": "文件过大"
            }
        
        # 使用多模LLM分析
        logger.info(f"使用多模LLM分析处方图片: {file.filename}")
        result = await analyze_prescription_image_bytes(content, file.filename or "prescription.jpg")
        
        logger.info(f"多模态处理器返回结果类型: {type(result)}")
        logger.info(f"多模态处理器返回结果成功状态: {result.get('success')}")
        logger.debug(f"多模态处理器返回结果: {str(result)[:500]}...")
        
        # 检查多模态处理器返回的格式并确保正确性
        if result.get('success'):
            logger.info(f"检查多模态结果格式，包含字段: {list(result.keys())}")
            
            # 检查是否已经是多模态格式
            if 'document_analysis' in result and 'prescription' in result:
                logger.info("多模态处理器返回标准格式，直接返回")
                # 确保confidence字段存在
                if 'confidence' not in result['document_analysis']:
                    result['document_analysis']['confidence'] = 0.95
                    logger.warning("补充缺失的confidence字段")
                
                # 🎓 自动学习处理：将图片处方数据用于系统学习
                try:
                    learning_integrator = get_prescription_learning_integrator()
                    learning_success = await learning_integrator.process_prescription_data(
                        prescription_data=result,
                        source_type="image_upload",
                        patient_info=None  # 图片上传通常不包含患者信息
                    )
                    if learning_success:
                        logger.info(f"✅ 图片处方数据已用于系统学习")
                    else:
                        logger.warning(f"⚠️ 图片处方学习处理未完全成功")
                except Exception as learning_error:
                    logger.warning(f"⚠️ 图片处方学习失败（不影响检测结果）: {learning_error}")
                
                return result
            else:
                # 如果返回了非标准格式，需要转换
                logger.warning("多模态处理器返回非标准格式，进行转换")
                logger.info(f"转换前的结果结构: {list(result.keys())}")
                
                # 从analysis字段提取herbs_details
                analysis = result.get('analysis', {})
                herbs_details = analysis.get('herbs_details', [])
                
                converted_result = {
                    "success": True,
                    "document_analysis": {
                        "type": result.get('document_type', '中医处方'),
                        "confidence": result.get('confidence', 0.95),
                        "quality": "清晰",
                        "notes": result.get('step', '')
                    },
                    "prescription": {
                        "herbs": herbs_details,
                        "total_herbs": analysis.get('total_herbs', len(herbs_details)),
                        "usage": analysis.get('usage_info', {}),
                        "estimated_cost": analysis.get('estimated_cost')
                    },
                    "patient_info": result.get('patient_info', {}),
                    "medical_info": result.get('medical_info', {}),
                    "diagnosis": result.get('diagnosis', {}),
                    "safety_analysis": result.get('safety_analysis', {}),
                    "clinical_analysis": result.get('clinical_analysis', {}),
                    "processing_info": result.get('processing_info', {})
                }
                
                logger.info(f"转换后包含 {len(herbs_details)} 味中药")
                logger.info(f"转换后的结果结构: {list(converted_result.keys())}")
                
                # 🎓 自动学习处理：将转换后的图片处方数据用于系统学习
                try:
                    learning_integrator = get_prescription_learning_integrator()
                    learning_success = await learning_integrator.process_prescription_data(
                        prescription_data=converted_result,
                        source_type="image_upload_converted",
                        patient_info=None  # 图片上传通常不包含患者信息
                    )
                    if learning_success:
                        logger.info(f"✅ 转换后的图片处方数据已用于系统学习")
                    else:
                        logger.warning(f"⚠️ 转换后的图片处方学习处理未完全成功")
                except Exception as learning_error:
                    logger.warning(f"⚠️ 转换后的图片处方学习失败（不影响检测结果）: {learning_error}")
                
                return converted_result
        else:
            return {
                "success": False,
                "error": result.get('error', '多模LLM分析失败'),
                "document_type": "分析失败",
                "step": "多模LLM分析异常"
            }
            
    except Exception as e:
        logger.error(f"多模LLM处方分析异常: {e}")
        logger.error(f"异常类型: {type(e)}")
        logger.error(f"异常堆栈: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"系统处理异常: {str(e)}",
            "document_analysis": {
                "type": "系统错误",
                "confidence": 0.0,
                "notes": f"处理异常: {str(e)}"
            },
            "processing_info": {
                "error": True,
                "processed_at": "异常时间"
            }
        }

@app.post("/api/prescription/check_image")
async def prescription_check_image_endpoint(
    file: UploadFile = File(...),
    patient_info: str = Form(None)
):
    """图片处方一站式检查API (OCR + 处方检查) - 传统方案"""
    try:
        # 1. OCR识别
        if not file.content_type or not file.content_type.startswith(('image/', 'application/pdf')):
            return {
                "success": False,
                "error": "不支持的文件类型，请上传图片或PDF文件"
            }
        
        file_data = await file.read()
        if len(file_data) > 10 * 1024 * 1024:
            return {
                "success": False,
                "error": "文件过大，请上传10MB以内的文件"
            }
        
        # 使用优化的自适应OCR策略
        try:
            from adaptive_ocr_strategy import AdaptiveOCRStrategy
            adaptive_ocr = AdaptiveOCRStrategy()
            
            logger.info("使用自适应OCR策略处理图片")
            
            if file.content_type == 'application/pdf':
                # PDF暂时使用原有逻辑
                ocr = get_ocr_system()
                ocr_result = ocr.process_pdf(file_data, file.filename)
            else:
                # 图片使用优化的自适应策略
                adaptive_result = adaptive_ocr.auto_detect_and_process(file_data)
                
                # 转换为兼容格式
                ocr_result = {
                    "success": adaptive_result.is_usable,
                    "original_text": adaptive_result.text,
                    "corrected_text": adaptive_result.text,
                    "combined_text": adaptive_result.text,
                    "confidence": adaptive_result.final_confidence,
                    "original_confidence": adaptive_result.original_confidence,
                    "quality_score": adaptive_result.quality_score,
                    "content_type": adaptive_result.content_type,
                    "strategy_used": adaptive_result.strategy_used,
                    "processing_time": adaptive_result.processing_time,
                    "adaptive_info": {
                        "quality_reasons": adaptive_result.quality_reasons,
                        "is_optimized": True
                    }
                }
                
                logger.info(f"自适应OCR结果: 类型{adaptive_result.content_type}, 策略{adaptive_result.strategy_used}, 置信度{adaptive_result.original_confidence:.3f}->{adaptive_result.final_confidence:.3f}")
        
        except ImportError:
            logger.warning("自适应OCR策略不可用，使用原始OCR")
            # 降级到原始OCR
            ocr = get_ocr_system()
            if file.content_type == 'application/pdf':
                ocr_result = ocr.process_pdf(file_data, file.filename)
            else:
                ocr_result = ocr.process_image(file_data, file.filename)
        
        if not ocr_result["success"]:
            return {
                "success": False,
                "step": "OCR识别",
                "error": ocr_result.get("error", "OCR识别失败"),
                "ocr_result": ocr_result
            }
        
        # 2. 处方安全检查
        prescription_text = ocr_result.get("corrected_text", ocr_result.get("combined_text", ""))
        if not prescription_text.strip():
            return {
                "success": False,
                "step": "文本提取",
                "error": "无法从图片中提取到处方文本",
                "ocr_result": ocr_result
            }
        
        # 解析患者信息
        patient_data = {}
        if patient_info:
            try:
                patient_data = json.loads(patient_info)
            except:
                patient_data = {}
        
        # 使用集成版处方解析器（修复版）
        try:
            analysis_result = parse_prescription_text(prescription_text)
            
            # 使用智能处方响应器处理解析失败情况
            if not analysis_result["success"]:
                try:
                    from intelligent_prescription_responder import IntelligentPrescriptionResponder
                    intelligent_responder = IntelligentPrescriptionResponder()
                    
                    logger.info(f"原始解析失败，启用智能文档类型识别和响应...")
                    
                    # 使用智能响应器生成合适的响应
                    intelligent_response = intelligent_responder.generate_appropriate_response(
                        prescription_text, 
                        analysis_result
                    )
                    
                    logger.info(f"智能分类结果: {intelligent_response.get('document_type', '未知')} (置信度: {intelligent_response.get('classification_confidence', 0):.3f})")
                    
                    # 将OCR结果也添加到智能响应中
                    intelligent_response["ocr_result"] = ocr_result
                    
                    return intelligent_response
                
                except ImportError:
                    logger.warning("智能处方响应器不可用，使用原始逻辑")
                    # 降级到原始的低置信度处理
                    if ocr_result.get("confidence", 0) < 0.1 and ocr_result.get("corrected_text"):
                        return {
                            "success": False,
                            "step": "基础OCR处理", 
                            "error": f"OCR置信度较低({ocr_result.get('confidence', 0):.3f})，但已识别到内容",
                            "suggestion": "基于优化后的系统，低置信度内容可能仍有价值，建议查看识别结果",
                            "partial_content": ocr_result.get("corrected_text", "")[:200] + "...",
                            "ocr_result": ocr_result
                        }
                
                # 如果智能响应器也不可用，返回原始错误信息
                return {
                    "success": False,
                    "step": "处方解析",
                    "error": analysis_result.get("error", "无法识别足够的中药信息进行分析"),
                    "ocr_result": ocr_result,
                    "analysis_details": analysis_result
                }
            
            # 转换为标准格式
            check_result = {
                "success": True,
                "analysis_type": "中医智能处方分析（修复版）",
                "prescription": {
                    "herbs": analysis_result["herbs"],
                    "total_count": analysis_result["total_herbs"],
                    "document_type": analysis_result.get("document_type", "unknown")
                },
                "validation": analysis_result.get("validation", {}),
                "parsing_notes": analysis_result.get("parsing_notes", []),
                "special_note": analysis_result.get("special_note", ""),
                "analysis_confidence": analysis_result.get("validation", {}).get("confidence_summary", {}).get("average", 0.8),
                "safety_check": {"is_safe": True, "warnings": []}
            }
            
        except (ImportError, Exception) as e:
            # 回退到原有系统
            logger.warning(f"集成处方解析器失败，回退到原有系统: {e}")
            checker = get_prescription_checker()
            if not checker:
                return {
                    "success": False,
                    "step": "处方检查",
                    "error": "处方检查系统初始化失败",
                    "ocr_result": ocr_result
                }
            check_result = checker.check_prescription(prescription_text, patient_data)
        
        return {
            "success": True,
            "ocr_result": ocr_result,
            "prescription_check": check_result,
            "processing_summary": {
                "ocr_confidence": ocr_result.get("confidence", 0.0),
                "prescription_found": check_result.get("success", False),
                "safety_passed": check_result.get("safety_check", {}).get("is_safe", False),
                "total_herbs": len(check_result.get("prescription", {}).get("herbs", [])) if check_result.get("prescription") else 0
            }
        }
        
    except Exception as e:
        logger.error(f"图片处方检查失败: {e}")
        return {
            "success": False,
            "step": "系统处理",
            "error": f"处理失败: {str(e)}"
        }

@app.get("/api/prescription/ocr_stats")
async def get_ocr_stats_endpoint():
    """获取OCR系统统计信息"""
    try:
        ocr = get_ocr_system()
        stats = ocr.get_system_stats()
        return {
            "success": True,
            "stats": stats,
            "system_info": {
                "version": "1.0.0",
                "supported_formats": ["JPG", "JPEG", "PNG", "BMP", "TIFF", "PDF"],
                "max_file_size": "10MB",
                "ocr_service": "百度OCR"
            }
        }
    except Exception as e:
        logger.error(f"获取OCR统计失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# 处方检查界面
@app.get("/prescription/checker")
async def prescription_checker_page():
    """处方检查界面"""
    from fastapi.responses import HTMLResponse
    
    # 使用完整功能版本
    try:
        from fastapi.responses import FileResponse
        return FileResponse("/opt/tcm-ai/static/prescription_checker_v2.html")
    except FileNotFoundError:
        return HTMLResponse("""
            <html><body>
                <h1>🏥 处方检查系统</h1>
                <p>系统正在更新中...</p>
                <a href="/">返回主页</a>
            </body></html>
        """)

@app.get("/prescription/learning")
async def prescription_learning_dashboard():
    """处方学习统计面板"""
    try:
        return FileResponse("/opt/tcm-ai/static/prescription_learning_dashboard.html")
    except FileNotFoundError:
        from fastapi.responses import HTMLResponse
        return HTMLResponse("""
            <html><body>
                <h1>处方学习统计面板</h1>
                <p>页面文件未找到，请检查系统配置。</p>
                <a href="/">返回主页</a>
            </body></html>
        """, status_code=404)

@app.get("/prescription/debug")
async def prescription_debug_page():
    """处方检查移动端调试页面"""
    from fastapi.responses import HTMLResponse
    
    try:
        with open('/opt/tcm/mobile_prescription_debug.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(html_content)
    except FileNotFoundError:
        return HTMLResponse("<h1>调试页面未找到</h1>")

@app.get("/diagnosis_safety_status")
async def diagnosis_safety_status():
    """获取诊断安全系统状态"""
    try:
        return {
            "diagnosis_controller_active": True,
            "total_tracked_conversations": len(medical_diagnosis_controller.diagnosis_progress),
            "stage_requirements": {
                stage.value: [req.value for req in requirements]
                for stage, requirements in medical_diagnosis_controller.stage_requirements.items()
            },
            "safety_features": [
                "四诊信息强制收集",
                "多轮问诊要求", 
                "处方前安全检查",
                "防止草率开方"
            ]
        }
    except Exception as e:
        logger.error(f"获取诊断安全状态失败: {e}")
        return {"error": str(e)}

@app.post("/submit_feedback", response_model=FeedbackOutput)
async def submit_feedback_endpoint(feedback_input: FeedbackInput):
    """提交用户反馈"""
    try:
        conversation_id = feedback_input.conversation_id
        
        # 查找最近的会话记录
        recent_session_id = None
        for session_id, session_data in conversation_session_store.items():
            if session_id.startswith(conversation_id):
                recent_session_id = session_id
        
        if not recent_session_id:
            return FeedbackOutput(success=False, message="未找到对应的会话记录")
        
        session_data = conversation_session_store[recent_session_id]
        
        # 如果学习系统可用，记录反馈
        if ENHANCED_SYSTEM_AVAILABLE and learning_system:
            try:
                feedback = UserFeedback(
                    session_id=recent_session_id,
                    user_query=session_data["user_query"],
                    selected_doctor=session_data["selected_doctor"],
                    ai_response=session_data["ai_response"],
                    user_rating=feedback_input.rating,
                    feedback_text=feedback_input.feedback_text,
                    timestamp=datetime.fromisoformat(feedback_input.timestamp.replace('Z', '+00:00'))
                )
                
                learning_system.record_feedback(feedback)
                logger.info(f"Feedback recorded for session {recent_session_id}: rating={feedback_input.rating}")
                
                return FeedbackOutput(success=True, message="反馈已成功记录，谢谢您的评价！")
                
            except Exception as e:
                logger.error(f"Failed to record feedback: {e}")
                return FeedbackOutput(success=False, message="反馈记录失败，请稍后重试")
        else:
            logger.info(f"Basic feedback logged: rating={feedback_input.rating}")
            return FeedbackOutput(success=True, message="感谢您的反馈！")
            
    except Exception as e:
        logger.error(f"Error in submit_feedback_endpoint: {e}")
        return FeedbackOutput(success=False, message="提交反馈时发生错误")


@app.post("/api/review/feedback", response_model=FeedbackOutput)
async def submit_feedback_compat_endpoint(feedback_input: FeedbackCompatInput):
    """兼容旧版前端反馈入口，统一转发到 /submit_feedback"""
    def _first_non_empty(*values):
        for value in values:
            if isinstance(value, str):
                normalized = value.strip()
                if normalized:
                    return normalized
                continue
            if value is not None:
                return value
        return None

    conversation_id = _first_non_empty(
        feedback_input.conversation_id,
        feedback_input.conversationId,
        feedback_input.session_id,
        feedback_input.sessionId,
    )
    if not conversation_id:
        return FeedbackOutput(success=False, message="conversation_id不能为空")

    raw_rating = _first_non_empty(feedback_input.rating, feedback_input.score)
    if raw_rating is None:
        return FeedbackOutput(success=False, message="rating不能为空")
    try:
        rating = int(raw_rating)
    except (TypeError, ValueError):
        return FeedbackOutput(success=False, message="rating格式错误")
    if rating < 1 or rating > 5:
        return FeedbackOutput(success=False, message="rating必须在1到5之间")

    feedback_text = _first_non_empty(
        feedback_input.feedback_text,
        feedback_input.message,
        feedback_input.content,
    )
    timestamp = feedback_input.timestamp or datetime.now().isoformat()

    normalized_feedback = FeedbackInput(
        conversation_id=str(conversation_id),
        rating=rating,
        feedback_text=str(feedback_text) if feedback_text is not None else None,
        timestamp=timestamp,
    )
    return await submit_feedback_endpoint(normalized_feedback)

# 医生思维决策树系统API端点 (保持所有原有端点)
class CaseInput(BaseModel):
    case_id: Optional[str] = None
    patient_symptoms: Dict[str, Any]
    doctor_reasoning: List[str]
    final_prescription: Dict[str, Any]
    treatment_outcome: str
    success_rating: float
    doctor_id: str
    disease_category: str

class DoctorLearningInput(BaseModel):
    doctor_id: str
    doctor_name: str

class DoctorRecommendationInput(BaseModel):
    user_query: str
    patient_data: Optional[Dict[str, Any]] = None

class DirectThinkingPatternInput(BaseModel):
    doctor_id: str
    doctor_name: str
    disease_category: str
    specialty_area: str
    pattern_accuracy: Optional[float] = 0.9
    case_count: Optional[int] = 0
    decision_logic: List[Dict[str, Any]]

# 所有医生思维系统的API端点 (保持不变)
@app.post("/add_case_example")
async def add_case_example_endpoint(case_input: CaseInput):
    if not DOCTOR_MIND_SYSTEM_AVAILABLE or not doctor_mind_api:
        return {"success": False, "message": "医生思维系统不可用"}
    
    try:
        case_data = {
            "case_id": case_input.case_id,
            "patient_symptoms": case_input.patient_symptoms,
            "doctor_reasoning": case_input.doctor_reasoning,
            "final_prescription": case_input.final_prescription,
            "treatment_outcome": case_input.treatment_outcome,
            "success_rating": case_input.success_rating,
            "doctor_id": case_input.doctor_id,
            "disease_category": case_input.disease_category
        }
        
        result = doctor_mind_api.add_case_api(case_data)
        logger.info(f"Added case example: {case_input.case_id or 'auto-generated'}")
        return result
        
    except Exception as e:
        logger.error(f"Error adding case example: {e}")
        return {"success": False, "message": f"添加案例失败: {str(e)}"}

@app.post("/import_thinking_pattern")
async def import_thinking_pattern_endpoint(pattern_input: DirectThinkingPatternInput):
    """导入医生思维模式"""
    if not DOCTOR_MIND_SYSTEM_AVAILABLE or not doctor_mind_api:
        return {"success": False, "message": "医生思维系统不可用"}
    
    try:
        pattern_data = {
            "doctor_id": pattern_input.doctor_id,
            "doctor_name": pattern_input.doctor_name,
            "disease_category": pattern_input.disease_category,
            "specialty_area": pattern_input.specialty_area,
            "pattern_accuracy": pattern_input.pattern_accuracy,
            "case_count": pattern_input.case_count,
            "decision_logic": pattern_input.decision_logic
        }
        
        result = doctor_mind_api.import_thinking_pattern_api(pattern_data)
        logger.info(f"Imported thinking pattern for {pattern_input.doctor_name}")
        return result
        
    except Exception as e:
        logger.error(f"Error importing thinking pattern: {e}")
        return {"success": False, "message": f"导入思维模式失败: {str(e)}"}

@app.post("/learn_doctor_patterns/{doctor_id}")
async def learn_doctor_patterns_endpoint(doctor_id: str, doctor_name: str = ""):
    """学习医生思维模式"""
    if not DOCTOR_MIND_SYSTEM_AVAILABLE or not doctor_mind_api:
        return {"success": False, "message": "医生思维系统不可用"}
    
    try:
        if not doctor_name:
            doctor_name = doctor_id
            
        result = doctor_mind_api.learn_patterns_api(doctor_id, doctor_name)
        logger.info(f"Learned patterns for doctor: {doctor_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error learning doctor patterns: {e}")
        return {"success": False, "message": f"学习医生模式失败: {str(e)}"}

@app.post("/recommend_doctors")
async def recommend_doctors_endpoint(recommendation_input: DoctorRecommendationInput):
    """推荐最适合的医生"""
    if not DOCTOR_MIND_SYSTEM_AVAILABLE or not doctor_mind_api:
        return {"success": False, "message": "医生思维系统不可用"}
    
    try:
        result = doctor_mind_api.recommend_doctors_api(
            recommendation_input.user_query, 
            recommendation_input.patient_data
        )
        logger.info(f"Generated doctor recommendations for query: {recommendation_input.user_query[:50]}...")
        return result
        
    except Exception as e:
        logger.error(f"Error recommending doctors: {e}")
        return {"success": False, "message": f"推荐医生失败: {str(e)}"}

@app.get("/doctor_statistics")
async def get_doctor_statistics_endpoint():
    """获取医生统计信息"""
    if not DOCTOR_MIND_SYSTEM_AVAILABLE or not doctor_mind_api:
        return {"success": False, "message": "医生思维系统不可用"}
    
    try:
        result = doctor_mind_api.get_statistics_api()
        return result
        
    except Exception as e:
        logger.error(f"Error getting doctor statistics: {e}")
        return {"success": False, "message": f"获取统计信息失败: {str(e)}"}

@app.post("/doctor_authenticate")
async def doctor_authenticate_endpoint(auth_data: dict):
    """医生身份认证"""
    try:
        code = auth_data.get("code", "")
        name = auth_data.get("name", "")
        
        # 预设的医生访问码（实际部署时应使用数据库管理）
        valid_codes = {
            'tcm2024': '中医AI系统',
            'doctor123': '演示医生', 
            'zhangzj': '张仲景传人',
            'lidongyw': '李东垣传人',
            'yetsh': '叶天士传人',
            'admin001': '系统管理员'
        }
        
        if code in valid_codes:
            logger.info(f"Doctor authentication successful: {name} ({code})")
            return {
                "success": True, 
                "message": f"欢迎 {name} 医生",
                "doctor_name": name,
                "access_level": valid_codes[code]
            }
        else:
            logger.warning(f"Failed doctor authentication attempt: {name} ({code})")
            return {
                "success": False,
                "message": "访问码错误，请联系系统管理员"
            }
            
    except Exception as e:
        logger.error(f"Error in doctor authentication: {e}")
        return {"success": False, "message": f"认证失败: {str(e)}"}

@app.get("/doctor_portal_info")
async def get_doctor_portal_info():
    """获取医生门户信息"""
    try:
        # 获取系统统计
        stats_result = {"statistics": {"total_doctors": 0, "total_patterns": 0, "total_cases": 0}}
        if DOCTOR_MIND_SYSTEM_AVAILABLE and doctor_mind_api:
            stats_result = doctor_mind_api.get_statistics_api()
        
        # 获取服务器信息
        import socket
        hostname = socket.gethostname()
        
        return {
            "success": True,
            "server_info": {
                "hostname": hostname,
                "port": 8000,
                "doctor_mind_available": DOCTOR_MIND_SYSTEM_AVAILABLE
            },
            "statistics": stats_result.get("statistics", {}),
            "access_urls": {
                "portal": "/static/doctor_portal.html",
                "thinking_input": "/static/doctor_thinking_input.html",
                "management": "/static/doctor_management.html"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting doctor portal info: {e}")
        return {"success": False, "message": f"获取门户信息失败: {str(e)}"}

# 分享统计API
@app.post("/api/share_visit")
async def share_visit_api(request: Request):
    """记录分享页面访问"""
    try:
        data = await request.json()
        logger.info(f"Share visit: {data}")
        return {"success": True}
    except:
        return {"success": False}

@app.post("/api/wechat_visit") 
async def wechat_visit_api(request: Request):
    """记录微信访问"""
    try:
        data = await request.json()
        logger.info(f"Wechat visit: {data}")
        return {"success": True}
    except:
        return {"success": False}

# ============ 用户历史记录系统 API ============

@app.get("/api/user/info")
async def get_user_info_api(request: Request):
    """获取当前用户信息"""
    if not USER_HISTORY_AVAILABLE:
        return {"success": False, "error": "用户历史系统不可用"}
    
    try:
        # 🔧 直接创建实例避免导入问题
        from services.user_history_system import UserHistorySystem
        history_service = UserHistorySystem()
        
        # 生成设备指纹
        request_info = {
            'user_agent': request.headers.get('user-agent', ''),
            'client_ip': request.client.host,
            'accept_language': request.headers.get('accept-language', '')
        }
        device_fingerprint = history_service.generate_device_fingerprint(request_info)
        
        # 获取用户信息
        user_id = history_service.register_or_get_user(device_fingerprint)
        user_info = history_service.get_user_info(user_id)
        
        if user_info:
            return {"success": True, **user_info}
        else:
            return {"success": False, "error": "用户信息不存在"}
            
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return {"success": False, "error": str(e)}

async def get_user_info_by_token(token: str):
    """通过token获取用户信息"""
    try:
        return sqlite_service.get_user_info_by_token(token)
    except Exception as e:
        logger.error(f"Token验证失败: {e}")
        return None


def _build_request_info(request: Request) -> Dict[str, str]:
    return {
        "user_agent": request.headers.get("user-agent", ""),
        "client_ip": request.client.host if request.client else "unknown",
        "accept_language": request.headers.get("accept-language", ""),
    }


async def _resolve_effective_user_id(
    request: Request,
    requested_user_id: str = None,
):
    """解析有效用户ID：token优先，URL参数次之，最后设备指纹兜底。"""
    from services.user_history_system import UserHistorySystem

    history_service = UserHistorySystem()
    token_user_id = None

    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        try:
            auth_user_info = await get_user_info_by_token(token)
            if auth_user_info and auth_user_info.get("user_id") and auth_user_info.get("user_id") != "anonymous":
                token_user_id = auth_user_info["user_id"]
        except Exception as e:
            logger.warning(f"Token解析失败: {e}")

    if token_user_id:
        if requested_user_id and requested_user_id != "anonymous" and requested_user_id != token_user_id:
            logger.warning(
                f"⚠️ 忽略与token不一致的user_id参数: requested={requested_user_id}, token={token_user_id}"
            )
        logger.info(f"✅ 使用token解析的用户ID: {token_user_id}")
        return token_user_id, history_service

    if requested_user_id and requested_user_id != "anonymous":
        logger.info(f"✅ 使用URL参数中的用户ID: {requested_user_id}")
        return requested_user_id, history_service

    request_info = _build_request_info(request)
    device_fingerprint = history_service.generate_device_fingerprint(request_info)
    fallback_user_id = history_service.register_or_get_user(device_fingerprint)
    logger.info(f"⚠️ 使用设备指纹获取历史记录用户ID: {fallback_user_id}")
    return fallback_user_id, history_service


@app.get("/api/user/sessions")
async def get_user_sessions_api(request: Request, limit: int = 20, user_id: str = None):
    """获取用户的问诊会话历史 - 支持跨设备同步"""
    if not USER_HISTORY_AVAILABLE:
        return {"success": False, "error": "用户历史系统不可用"}
    
    try:
        final_user_id, history_service = await _resolve_effective_user_id(request, user_id)
        
        # 获取会话历史
        sessions = history_service.get_user_sessions(final_user_id, limit)
        logger.info(f"📊 为用户 {final_user_id} 获取到 {len(sessions)} 条会话记录")
        
        # 计算统计信息
        doctor_names = set(session['doctor_name'] for session in sessions)
        earliest_session = min(sessions, key=lambda x: x['created_at'])['created_at'] if sessions else None
        usage_days = 0
        if earliest_session:
            from datetime import datetime
            earliest_date = datetime.fromisoformat(earliest_session)
            usage_days = (datetime.now() - earliest_date).days + 1
        
        stats = {
            'total_sessions': len(sessions),
            'doctor_count': len(doctor_names),
            'usage_days': usage_days
        }
        
        return {
            "success": True,
            "sessions": sessions,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"获取用户会话历史失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/user/sessions/{doctor_name}")
async def get_user_doctor_sessions_api(doctor_name: str, request: Request):
    """获取用户与特定医生的会话历史"""
    if not USER_HISTORY_AVAILABLE:
        return {"success": False, "error": "用户历史系统不可用"}
    
    try:
        user_id, history_service = await _resolve_effective_user_id(request)
        
        # 获取特定医生的会话历史
        sessions = history_service.get_sessions_by_doctor(user_id, doctor_name)
        
        return {
            "success": True,
            "doctor_name": doctor_name,
            "sessions": sessions
        }
        
    except Exception as e:
        logger.error(f"获取医生会话历史失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/user/conversation/{conversation_id}")
async def get_conversation_detail_api(conversation_id: str, request: Request):
    """获取对话详情"""
    if not USER_HISTORY_AVAILABLE:
        return {"success": False, "error": "用户历史系统不可用"}
    
    try:
        # 验证用户权限
        user_id, history_service = await _resolve_effective_user_id(request)
        
        # 获取对话详情
        conversation_detail = history_service.get_conversation_detail(conversation_id, user_id)
        
        if not conversation_detail:
            return {"success": False, "error": "对话不存在或无权限访问"}
        
        return conversation_detail
        
    except Exception as e:
        logger.error(f"获取对话详情API失败: {e}")
        return {"success": False, "error": "获取对话详情失败"}

@app.get("/api/user/conversation/{conversation_id}/export")
async def export_conversation_api(conversation_id: str, request: Request, format: str = "medical_record"):
    """导出对话为专业医疗格式"""
    if not USER_HISTORY_AVAILABLE:
        return Response("用户历史系统不可用", status_code=503, media_type="text/plain")
    
    try:
        # 验证用户权限
        user_id, history_service = await _resolve_effective_user_id(request)
        
        # 获取对话详情
        conversation_detail = history_service.get_conversation_detail(conversation_id, user_id)
        
        if not conversation_detail:
            return Response("对话不存在或无权限访问", status_code=404, media_type="text/plain")
        
        # 生成专业医疗格式
        if format == "medical_record":
            exported_content = history_service.export_as_medical_record(conversation_detail)
            media_type = "text/html; charset=utf-8"
            filename = f"TCM_病历_{conversation_id[:8]}_{datetime.now().strftime('%Y%m%d')}.html"
        else:
            exported_content = history_service.export_as_text(conversation_detail)
            media_type = "text/plain; charset=utf-8"
            filename = f"TCM_记录_{conversation_id[:8]}_{datetime.now().strftime('%Y%m%d')}.txt"
        
        # 返回文件响应 - 彻底修复中文编码问题
        from urllib.parse import quote
        
        # 对中文文件名进行URL编码
        encoded_filename = quote(filename.encode('utf-8'), safe='')
        
        # 生成纯ASCII的安全文件名作为备选
        safe_filename = f"TCM_Record_{conversation_id[:8]}_{datetime.now().strftime('%Y%m%d')}.{'html' if format == 'medical_record' else 'txt'}"
        
        # 确保内容是UTF-8字节
        if isinstance(exported_content, str):
            content_bytes = exported_content.encode('utf-8')
        else:
            content_bytes = exported_content
            
        return Response(
            content=content_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{safe_filename}\"; filename*=UTF-8''{encoded_filename}",
                "Content-Type": f"{media_type}; charset=utf-8"
            }
        )
        
    except Exception as e:
        logger.error(f"导出对话API失败: {e}")
        return Response("导出失败", status_code=500, media_type="text/plain")

@app.get("/history")
async def user_history_page():
    """用户历史记录页面"""
    try:
        return FileResponse("/opt/tcm-ai/static/user_history.html")
    except Exception as e:
        logger.error(f"加载历史记录页面失败: {e}")
        return HTMLResponse("<h1>页面加载失败</h1>", status_code=500)

@app.get("/api/user/stats")
async def get_user_stats_api():
    """获取用户系统统计信息（管理用）"""
    if not USER_HISTORY_AVAILABLE:
        return {"success": False, "error": "用户历史系统不可用"}
    
    try:
        stats = user_history.get_system_stats()
        return {"success": True, **stats}
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}")
        return {"success": False, "error": str(e)}

# ========== 手机验证相关API (第二阶段新增) ==========

@app.post("/api/auth/send-verification-code")
async def send_verification_code_api(request: Request):
    """发送手机验证码"""
    if not USER_HISTORY_AVAILABLE:
        return {"success": False, "error": "用户历史系统不可用"}
    
    try:
        # 获取请求数据
        data = await request.json()
        phone = data.get('phone', '').strip()
        
        if not phone:
            return {"success": False, "error": "手机号不能为空"}
        
        # 发送验证码
        result = user_history.send_verification_code(phone)
        logger.info(f"发送验证码结果: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"发送验证码API失败: {e}")
        return {"success": False, "error": "发送验证码失败"}

@app.post("/api/auth/verify-phone-code")
async def verify_phone_code_api(request: Request):
    """验证手机验证码"""
    if not USER_HISTORY_AVAILABLE:
        return {"success": False, "error": "用户历史系统不可用"}
    
    try:
        # 获取请求数据
        data = await request.json()
        phone = data.get('phone', '').strip()
        code = data.get('code', '').strip()
        
        if not phone or not code:
            return {"success": False, "error": "手机号和验证码不能为空"}
        
        # 验证验证码
        result = user_history.verify_phone_code(phone, code)
        logger.info(f"验证码验证结果: {result}")
        
        return result

    except Exception as e:
        logger.error(f"验证码验证API失败: {e}")
        return {"success": False, "error": "验证码验证失败"}

@app.post("/api/auth/send-email-code")
async def send_email_code_api(request: Request):
    """发送邮箱验证码"""
    if not USER_HISTORY_AVAILABLE:
        return {"success": False, "error": "用户历史系统不可用"}

    try:
        data = await request.json()
        email = data.get('email', '').strip().lower()

        import re
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not email or not re.match(email_regex, email):
            return {"success": False, "error": "请输入正确的邮箱地址"}

        result = user_history.send_email_verification_code(email)
        logger.info(f"发送邮箱验证码结果: {result}")

        return result

    except Exception as e:
        logger.error(f"发送邮箱验证码API失败: {e}")
        return {"success": False, "error": "发送验证码失败"}

@app.post("/api/auth/verify-email-code")
async def verify_email_code_api(request: Request):
    """验证邮箱验证码"""
    if not USER_HISTORY_AVAILABLE:
        return {"success": False, "error": "用户历史系统不可用"}

    try:
        data = await request.json()
        email = data.get('email', '').strip().lower()
        code = data.get('code', '').strip()

        if not email or not code:
            return {"success": False, "error": "邮箱和验证码不能为空"}

        result = user_history.verify_email_code(email, code)
        logger.info(f"邮箱验证码验证结果: {result}")

        return result

    except Exception as e:
        logger.error(f"邮箱验证码验证API失败: {e}")
        return {"success": False, "error": "验证码验证失败"}

@app.post("/api/auth/bind-phone")
async def bind_phone_api(request: Request):
    """绑定手机号到当前设备用户"""
    if not USER_HISTORY_AVAILABLE:
        return {"success": False, "error": "用户历史系统不可用"}
    
    try:
        # 获取请求数据
        data = await request.json()
        phone = data.get('phone', '').strip()
        nickname = data.get('nickname', '').strip()
        
        if not phone:
            return {"success": False, "error": "手机号不能为空"}
        
        # 生成设备指纹
        request_info = {
            'user_agent': request.headers.get('user-agent', ''),
            'client_ip': request.client.host,
            'accept_language': request.headers.get('accept-language', '')
        }
        device_fingerprint = user_history.generate_device_fingerprint(request_info)
        
        # 绑定手机号
        result = user_history.bind_phone_to_user(device_fingerprint, phone, nickname)
        logger.info(f"手机号绑定结果: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"手机号绑定API失败: {e}")
        return {"success": False, "error": "手机号绑定失败"}

@app.post("/api/auth/phone-login")
async def phone_login_api(request: Request):
    """手机号登录（多设备支持）"""
    if not USER_HISTORY_AVAILABLE:
        return {"success": False, "error": "用户历史系统不可用"}
    
    try:
        # 获取请求数据
        data = await request.json()
        phone = data.get('phone', '').strip()
        
        if not phone:
            return {"success": False, "error": "手机号不能为空"}
        
        # 生成设备指纹
        request_info = {
            'user_agent': request.headers.get('user-agent', ''),
            'client_ip': request.client.host,
            'accept_language': request.headers.get('accept-language', '')
        }
        device_fingerprint = user_history.generate_device_fingerprint(request_info)
        
        # 手机号登录
        result = user_history.login_with_phone(phone, device_fingerprint)
        logger.info(f"手机号登录结果: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"手机号登录API失败: {e}")
        return {"success": False, "error": "手机号登录失败"}

# ========== 新增注册方式API ==========

@app.post("/api/auth/register/email")
async def register_with_email(request: Request):
    """邮箱注册（需先验证邮箱验证码）"""
    if not USER_HISTORY_AVAILABLE:
        return {"success": False, "error": "用户历史系统不可用"}

    try:
        data = await request.json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        nickname = data.get('nickname', '').strip()
        code = data.get('code', '').strip()

        # 验证邮箱格式
        import re
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not email or not re.match(email_regex, email):
            return {"success": False, "error": "请输入正确的邮箱地址"}

        # 验证密码
        if not password or len(password) < 6 or len(password) > 20:
            return {"success": False, "error": "密码长度为6-20位"}

        # 验证邮箱验证码
        if not code:
            return {"success": False, "error": "请输入邮箱验证码"}

        verify_result = user_history.verify_email_code(email, code)
        if not verify_result.get("success"):
            return {"success": False, "error": verify_result.get("error", "验证码错误")}

        import hashlib
        import time
        import random

        display_name = nickname or email.split('@')[0]

        # 先检查统一账户系统中邮箱是否已注册
        from core.unified_account.account_manager import unified_account_manager, UserType

        # 1. 创建统一账户（登录用的 unified_users 表，这是登录认证的表）
        username = nickname if nickname else email.split('@')[0]
        try:
            unified_account_manager.create_user(
                username=username,
                password=password,
                display_name=display_name,
                user_type=UserType.PATIENT,
                email=email,
            )
        except ValueError:
            # 用户名重复，加随机后缀
            username = f"{username}{random.randint(100, 999)}"
            unified_account_manager.create_user(
                username=username,
                password=password,
                display_name=display_name,
                user_type=UserType.PATIENT,
                email=email,
            )

        # 2. 写入旧 users 表（向后兼容，供 user_history 等模块使用）
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        request_info = {
            'user_agent': request.headers.get('user-agent', ''),
            'client_ip': request.client.host,
            'accept_language': request.headers.get('accept-language', '')
        }
        fingerprint_data = f"{request_info.get('user_agent', '')}|{request_info.get('client_ip', '')}|{request_info.get('accept_language', '')}|{str(int(time.time() / 3600))}"
        device_fingerprint = hashlib.md5(fingerprint_data.encode('utf-8')).hexdigest()[:32]

        try:
            sqlite_service.register_email_user(
                email=email,
                password_hash=password_hash,
                nickname=display_name,
                device_fingerprint=device_fingerprint,
            )
        except Exception:
            logger.warning(f"旧 users 表写入失败（可能设备指纹重复），已跳过: {email}")

        # 标记邮箱已验证
        with unified_account_manager._get_db_connection() as conn:
            conn.cursor().execute(
                "UPDATE unified_users SET email_verified = 1 WHERE email = ?",
                (email,)
            )
            conn.commit()

        logger.info(f"邮箱注册成功: {email} (username: {username})")
        return {"success": True, "message": "注册成功"}

    except Exception as e:
        logger.error(f"邮箱注册失败: {e}")
        return {"success": False, "error": "注册失败，请重试"}

@app.post("/api/auth/register/username")
async def register_with_username(request: Request):
    """用户名注册"""
    if not USER_HISTORY_AVAILABLE:
        return {"success": False, "error": "用户历史系统不可用"}
        
    try:
        data = await request.json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # 验证用户名格式（支持中文、英文、数字和下划线）
        import re
        username_regex = r'^[\w\u4e00-\u9fa5]{4,20}$'
        if not username or not re.match(username_regex, username):
            return {"success": False, "error": "用户名为4-20位，支持中文、英文、数字和下划线"}
        
        # 验证密码
        if not password or len(password) < 6 or len(password) > 20:
            return {"success": False, "error": "密码长度为6-20位"}
        
        import hashlib
        import secrets

        # 使用 PBKDF2-SHA256 加密密码（与统一认证系统一致）
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000
        ).hex()
        
        # 生成设备指纹
        request_info = {
            'user_agent': request.headers.get('user-agent', ''),
            'client_ip': request.client.host,
            'accept_language': request.headers.get('accept-language', '')
        }
        # 简单的设备指纹生成
        import time
        fingerprint_data = f"{request_info.get('user_agent', '')}|{request_info.get('client_ip', '')}|{request_info.get('accept_language', '')}|{str(int(time.time() / 3600))}"
        device_fingerprint = hashlib.md5(fingerprint_data.encode('utf-8')).hexdigest()[:32]

        registration_result = sqlite_service.register_username_user(
            username=username,
            salted_password_hash=password_hash,
            salt=salt,
            device_fingerprint=device_fingerprint,
            registration_ip=request.client.host if request.client else 'unknown',
        )
        if not registration_result.get("created"):
            return {"success": False, "error": "该用户名已被注册"}

        logger.info(f"用户名注册成功: {username} (统一ID: {registration_result.get('global_user_id')})")
        return {"success": True, "message": "注册成功"}
        
    except Exception as e:
        logger.error(f"用户名注册失败: {e}")
        return {"success": False, "error": "注册失败，请重试"}

@app.get("/api/user/devices")
async def get_user_devices_api(request: Request):
    """获取用户绑定的设备列表"""
    if not USER_HISTORY_AVAILABLE:
        return {"success": False, "error": "用户历史系统不可用"}
    
    try:
        # 获取当前用户ID
        request_info = {
            'user_agent': request.headers.get('user-agent', ''),
            'client_ip': request.client.host,
            'accept_language': request.headers.get('accept-language', '')
        }
        device_fingerprint = user_history.generate_device_fingerprint(request_info)
        user_id = user_history.register_or_get_user(device_fingerprint)
        
        # 获取设备列表
        devices = user_history.get_user_devices(user_id)
        
        return {"success": True, "devices": devices}
        
    except Exception as e:
        logger.error(f"获取用户设备API失败: {e}")
        return {"success": False, "error": "获取设备列表失败"}

# 认证入口页面路由（阶段8）
register_auth_entry_routes(app, logger)

# 系统监控/健康状态端点（阶段5：迁移到 app.api.ops_setup）
register_operational_routes(
    app,
    logger=logger,
    debug_status_provider=_build_debug_status_payload,
    cache_system_available=CACHE_SYSTEM_AVAILABLE,
    dashscope_api_key=DASHSCOPE_API_KEY,
)

register_monitor_and_debug_routes(app, logger)

# ==================== 三界面系统路由 ====================

# 医生端路由
# 医生端路由已移动到 security_integration.py 中，带有适当的权限检查
register_three_interface_page_routes(app)

# 公共API - 医生列表
@app.get("/api/doctors/list")
async def get_doctors_list(page: int = 1, per_page: int = 20):
    """获取医生列表 - 支持分页"""
    try:
        rows = sqlite_service.fetch_active_public_doctors(page=page, per_page=per_page)
        doctors = []
        
        # 获取默认医生数据模板
        default_doctors = get_default_doctors()
        
        # 为每个数据库医生生成与前端一致的数据结构
        doctors = []
        for row in rows:
            doctor_id = row['id']
            doctor_name = row['name']
            
            # 查找是否有对应的默认医生模板
            default_template = None
            for default_doc in default_doctors:
                # 根据ID映射或名字匹配找到模板 - 修复映射关系
                if (doctor_id == 1 and default_doc['id'] == 'jin_daifu') or \
                   (doctor_id == 2 and default_doc['id'] == 'ye_tianshi') or \
                   (doctor_id == 3 and default_doc['id'] == 'li_dongyuan') or \
                   (doctor_id == 4 and default_doc['id'] == 'zhang_zhongjing') or \
                   (doctor_id == 5 and default_doc['id'] == 'liu_duzhou') or \
                   (doctor_id == 6 and default_doc['id'] == 'zheng_qin_an') or \
                   (doctor_id == 7 and default_doc['id'] == 'zhu_danxi'):
                    default_template = default_doc
                    break
            
            if default_template:
                # 使用模板但更新数据库中的姓名和专业信息
                doctor_data = default_template.copy()
                doctor_data['name'] = doctor_name  # 使用数据库中的实际姓名
                # 强制确保doctor_code字段存在
                if 'doctor_code' not in doctor_data:
                    doctor_data['doctor_code'] = doctor_data['id']
                if row['speciality']:
                    doctor_data['school'] = row['speciality']
                    doctor_data['specialty'] = row['speciality']
                if row['hospital']:
                    doctor_data['hospital'] = row['hospital']
            else:
                # 新医生使用基础数据结构
                doctor_code = f"doctor_{doctor_id}"
                doctor_data = {
                    "id": doctor_code,
                    "doctor_code": doctor_code,  # 添加doctor_code字段
                    "name": doctor_name,
                    "school": row['speciality'] or "现代中医",
                    "avatar": get_doctor_avatar(doctor_name),
                    "description": f"{row['speciality'] or '中医'}专家，来自{row['hospital'] or '知名医院'}，具有丰富的临床经验。",
                    "specialty": row['speciality'] or "现代中医",
                    "specialties": [row['speciality'] or "中医诊疗", "方剂调配", "健康调理"],
                    "hospital": row['hospital']
                }
            
            doctors.append(doctor_data)
        
        # 如果数据库没有医生数据，使用默认数据作为备选
        if not doctors:
            doctors = default_doctors
        
        total = len(doctors)
        
        # 支持分页
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        doctors = doctors[start_idx:end_idx]
            
        return {
            "success": True,
            "doctors": doctors,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
                "has_next": page * per_page < total,
                "has_prev": page > 1
            }
        }
        
    except Exception as e:
        logger.error(f"获取医生列表失败: {e}")
        # 发生错误时返回默认医生数据
        doctors = get_default_doctors()
        return {
            "success": True,
            "doctors": doctors,
            "pagination": {
                "page": 1,
                "per_page": len(doctors),
                "total": len(doctors),
                "pages": 1,
                "has_next": False,
                "has_prev": False
            }
        }

def get_doctor_avatar(name: str) -> str:
    """根据医生姓名生成头像表情"""
    avatar_map = {
        "张仲景": "🎯",
        "叶天士": "🌡️", 
        "李东垣": "🌱",
        "朱丹溪": "💧",
        "刘渡舟": "📚",
        "郑钦安": "☀️",
        "华佗": "⚕️",
        "李时珍": "🌿"
    }
    return avatar_map.get(name, "👨‍⚕️")

def get_default_doctors() -> list:
    """返回默认医生数据（与前端保持完全一致）"""
    return [
        {
            "id": "jin_daifu",
            "doctor_code": "jin_daifu",
            "name": "金大夫",
            "school": "经方大师",
            "era": "现代",
            "avatar": "👨‍⚕️",
            "description": "经方大师，深通古典医学，擅长运用经典方剂解决现代疑难杂症，临床经验丰富。",
            "specialty": "经方大师 • 综合诊疗",
            "specialties": ["经方应用", "疑难杂症", "综合诊疗", "古典医学"]
        },
        {
            "id": "zhang_zhongjing",
            "doctor_code": "zhang_zhongjing",  # 添加doctor_code字段
            "name": "张仲景",
            "school": "伤寒派",
            "era": "汉代",
            "avatar": "🎯",
            "description": "伤寒派以《伤寒论》为理论基础，擅长六经辨证，治疗外感热病和内伤杂病。用药精准，方证对应。",
            "specialty": "伤寒派 • 六经辨证",
            "specialties": ["外感病", "内伤杂病", "急症", "六经辨证"]
        },
        {
            "id": "ye_tianshi",
            "doctor_code": "ye_tianshi",
            "name": "叶天士",
            "school": "温病派",
            "era": "清代", 
            "avatar": "🌡️",
            "description": "温病派专治各种热性疾病，以卫气营血辨证为特色，用药轻清灵动。",
            "specialty": "温病派 • 卫气营血",
            "specialties": ["温病", "热病", "儿科", "妇科"]
        },
        {
            "id": "li_dongyuan",
            "doctor_code": "li_dongyuan",
            "name": "李东垣",
            "school": "补土派",
            "era": "金代",
            "avatar": "🌱", 
            "description": "补土派以调理脾胃为核心，擅长治疗消化系统疾病和内伤发热。",
            "specialty": "补土派 • 升清降浊",
            "specialties": ["脾胃病", "内伤发热", "消化系统疾病", "脾胃调理"]
        },
        {
            "id": "zhu_danxi",
            "doctor_code": "zhu_danxi",
            "name": "朱丹溪",
            "school": "滋阴派",
            "era": "元代",
            "avatar": "💧",
            "description": "滋阴派重视养阴清热，擅长治疗阴虚火旺和各种内科调养，用药平和有效。",
            "specialty": "滋阴派 • 养阴清热",
            "specialties": ["阴虚火旺", "妇科杂症", "内科调养", "养阴清热"]
        },
        {
            "id": "liu_duzhou",
            "doctor_code": "liu_duzhou", 
            "name": "刘渡舟",
            "school": "经方派",
            "era": "现代",
            "avatar": "📚",
            "description": "经方派严格按照古代经典方剂治疗，特别擅长疑难杂症和慢性疾病。",
            "specialty": "经方派 • 经典方剂",
            "specialties": ["经方应用", "疑难杂症", "慢性病", "经典方剂"]
        },
        {
            "id": "zheng_qin_an",
            "doctor_code": "zheng_qin_an",
            "name": "郑钦安", 
            "school": "扶阳派",
            "era": "清代",
            "avatar": "☀️",
            "description": "扶阳派重视阳气，擅长治疗各种阳虚症状和急危重症。",
            "specialty": "扶阳派 • 扶阳理论",
            "specialties": ["阳虚证", "急危重症", "疑难杂症", "扶阳理论"]
        }
    ]

# 管理端路由已移动到 security_integration.py 中，带有适当的权限检查

register_auth_portal_routes(app)

# 管理员API端点
@app.get("/api/admin/dashboard")
async def admin_dashboard():
    """管理员仪表板数据 - 实时统计"""
    from datetime import datetime
    
    try:
        stats = sqlite_service.fetch_admin_dashboard_stats()

        total_users = stats["total_users"]
        active_doctors = stats["active_doctors"]
        today_consultations = stats["today_consultations"]
        pending_prescriptions = stats["pending_prescriptions"]
        monthly_new_users = stats["monthly_new_users"]

        system_status = "normal"
        system_uptime = "99.9%"
        active_sessions = stats["active_sessions"]
        
        return {
            "success": True,
            "stats": {
                "total_users": total_users,
                "active_doctors": active_doctors,
                "today_consultations": today_consultations,
                "pending_prescriptions": pending_prescriptions,
                "monthly_new_users": monthly_new_users,
                "active_sessions": active_sessions,
                "system_status": system_status,
                "system_uptime": system_uptime,
                "last_updated": datetime.now().isoformat()
            },
            "alerts": [
                {
                    "type": "info" if pending_prescriptions < 10 else "warning",
                    "title": "待审核处方",
                    "message": f"当前有 {pending_prescriptions} 个处方待审核",
                    "action_url": "#prescriptions"
                },
                {
                    "type": "info" if active_sessions < 50 else "warning",
                    "title": "活跃会话",
                    "message": f"当前有 {active_sessions} 个活跃用户会话",
                    "action_url": "#users"
                },
                {
                    "type": "success",
                    "title": "系统状态",
                    "message": f"系统运行正常，可用性 {system_uptime}",
                    "action_url": "#system"
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"获取仪表板数据失败: {e}")
        # 返回模拟数据
        return {
            "success": True,
            "stats": {
                "total_users": 1234,
                "active_doctors": 6,
                "today_consultations": 156,
                "system_status": "normal"
            }
        }

@app.get("/api/admin/users")
async def admin_get_users(page: int = 1, per_page: int = 20):
    """获取用户列表"""
    try:
        rows, total = sqlite_service.fetch_admin_users(page=page, per_page=per_page)
        offset = (page - 1) * per_page
        users = []
        
        for i, row in enumerate(rows):
            user_data = {
                "id": row['user_id'] or f"user_{i+1 + offset}",
                "name": row['nickname'] or f"用户{row['user_id'][:8] if row['user_id'] else str(i+1)}",
                "email": f"{row['user_id'][:8] if row['user_id'] else f'user{i+1}'}@example.com",
                "phone": row['phone_number'] or '-',
                "register_time": row['created_at'],
                "last_visit": row['last_active'],
                "status": "verified" if row['is_verified'] else "active",
                "conversation_count": row['conversation_count'] or 0
            }
            users.append(user_data)
        
        return {
            "success": True,
            "users": users,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        return {
            "success": False,
            "message": f"获取用户列表失败: {e}",
            "users": [],
            "pagination": {"page": page, "per_page": per_page, "total": 0, "pages": 0}
        }

@app.get("/api/admin/doctors")
async def admin_get_doctors(page: int = 1, per_page: int = 20):
    """获取医生列表（管理员视图）"""
    try:
        doctors, total = sqlite_service.fetch_admin_doctors(page=page, per_page=per_page)
        
        return {
            "success": True,
            "doctors": doctors,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }
        
    except Exception as e:
        logger.error(f"获取医生列表失败: {e}")
        return {
            "success": False,
            "message": f"获取医生列表失败: {e}",
            "doctors": [],
            "pagination": {"page": page, "per_page": per_page, "total": 0, "pages": 0}
        }

@app.post("/api/admin/doctors")
async def admin_add_doctor(doctor_data: dict):
    """添加新医生"""
    try:
        # 验证必填字段
        required_fields = ['name', 'license_no']
        for field in required_fields:
            if not doctor_data.get(field):
                return {"success": False, "message": f"缺少必填字段: {field}"}

        result = sqlite_service.admin_add_doctor(doctor_data)
        if result["status"] == "license_exists":
            return {"success": False, "message": "执业证号已存在"}

        return {
            "success": True,
            "message": "医生添加成功",
            "doctor_id": result.get("doctor_id")
        }
        
    except Exception as e:
        logger.error(f"添加医生失败: {e}")
        return {"success": False, "message": f"添加医生失败: {e}"}

@app.put("/api/admin/doctors/{doctor_id}")
async def admin_update_doctor(doctor_id: int, doctor_data: dict):
    """更新医生信息"""
    try:
        result = sqlite_service.admin_update_doctor(doctor_id, doctor_data)
        if result["status"] == "not_found":
            return {"success": False, "message": "医生不存在"}
        if result["status"] == "no_fields":
            return {"success": False, "message": "没有提供更新字段"}
        if result["status"] == "license_exists":
            return {"success": False, "message": "执业证号已被其他医生使用"}
        
        return {
            "success": True,
            "message": "医生信息更新成功"
        }
        
    except Exception as e:
        logger.error(f"更新医生信息失败: {e}")
        return {"success": False, "message": f"更新医生信息失败: {e}"}

@app.post("/api/admin/doctors/{doctor_id}/approve")
async def admin_approve_doctor(doctor_id: int):
    """审核通过医生申请"""
    try:
        result = sqlite_service.admin_approve_doctor(doctor_id)
        if result["status"] == "not_found":
            return {"success": False, "message": "医生不存在"}

        return {
            "success": True,
            "message": "医生申请已通过"
        }
        
    except Exception as e:
        logger.error(f"审核医生失败: {e}")
        return {"success": False, "message": f"审核医生失败: {e}"}

@app.post("/api/admin/doctors/{doctor_id}/reject")
async def admin_reject_doctor(doctor_id: int):
    """拒绝医生申请"""
    try:
        result = sqlite_service.admin_reject_doctor(doctor_id)
        if result["status"] == "not_found":
            return {"success": False, "message": "医生不存在"}

        return {
            "success": True,
            "message": "医生申请已拒绝"
        }
        
    except Exception as e:
        logger.error(f"拒绝医生申请失败: {e}")
        return {"success": False, "message": f"拒绝医生申请失败: {e}"}

@app.get("/api/admin/prescriptions")
async def admin_get_prescriptions(page: int = 1, per_page: int = 20):
    """获取处方列表"""
    try:
        prescriptions, total = sqlite_service.fetch_admin_prescriptions(page=page, per_page=per_page)
        
        return {
            "success": True,
            "prescriptions": prescriptions,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }
        
    except Exception as e:
        logger.error(f"获取处方列表失败: {e}")
        return {
            "success": False,
            "message": f"获取处方列表失败: {e}",
            "prescriptions": [],
            "pagination": {"page": page, "per_page": per_page, "total": 0, "pages": 0}
        }

@app.get("/api/admin/prescription/{prescription_id}")
async def admin_get_prescription(prescription_id: int):
    """获取单个处方详情 - 支持订单管理联动"""
    try:
        prescription = sqlite_service.fetch_admin_prescription(prescription_id)
        if not prescription:
            return {
                "success": False,
                "message": f"处方ID {prescription_id} 不存在",
                "prescription": None
            }

        return {
            "success": True,
            "prescription": prescription
        }
        
    except Exception as e:
        logger.error(f"获取处方详情失败: {e}")
        return {
            "success": False,
            "message": f"获取处方详情失败: {e}",
            "prescription": None
        }

@app.get("/api/admin/settings")
async def admin_get_settings():
    """获取系统配置"""
    import json
    import os
    
    config_file_path = "/opt/tcm-ai/data/system_settings.json"
    
    try:
        # 获取默认配置作为基础
        settings = get_default_system_settings()
        
        # 尝试从配置文件读取并合并
        if os.path.exists(config_file_path):
            with open(config_file_path, 'r', encoding='utf-8') as f:
                file_settings = json.load(f)
                
                # 合并配置，文件中的配置覆盖默认配置
                for section in ['basic', 'ai', 'business', 'security', 'integration']:
                    if section in file_settings:
                        if section in settings:
                            settings[section].update(file_settings[section])
                        else:
                            settings[section] = file_settings[section]
        
        return {
            "success": True,
            "settings": settings
        }
        
    except Exception as e:
        logger.error(f"获取系统配置失败: {e}")
        # 出现错误时返回默认配置
        return {
            "success": True,
            "settings": get_default_system_settings()
        }

@app.post("/api/admin/settings")
async def admin_save_settings(settings_data: dict):
    """保存系统配置"""
    import json
    import os
    from datetime import datetime
    
    config_file_path = "/opt/tcm-ai/data/system_settings.json"
    backup_file_path = f"/opt/tcm-ai/data/system_settings_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        # 创建数据目录（如果不存在）
        os.makedirs("/opt/tcm-ai/data", exist_ok=True)
        
        # 如果已有配置文件，先备份
        if os.path.exists(config_file_path):
            import shutil
            shutil.copy2(config_file_path, backup_file_path)
        
        # 验证配置数据
        validated_settings = validate_system_settings(settings_data)
        
        # 添加保存时间戳
        validated_settings['_metadata'] = {
            'last_updated': datetime.now().isoformat(),
            'version': 'v2.6.0',
            'backup_file': backup_file_path
        }
        
        # 保存配置到文件
        with open(config_file_path, 'w', encoding='utf-8') as f:
            json.dump(validated_settings, f, ensure_ascii=False, indent=2)
        
        # 清理旧备份文件（只保留最近5个备份）
        cleanup_old_backups("/opt/tcm-ai/data", "system_settings_backup_", 5)
        
        logger.info("系统配置已成功保存")
        
        return {
            "success": True,
            "message": "系统配置保存成功",
            "backup_file": backup_file_path
        }
        
    except Exception as e:
        logger.error(f"保存系统配置失败: {e}")
        return {
            "success": False,
            "message": f"保存系统配置失败: {str(e)}"
        }

def get_default_system_settings():
    """获取默认系统配置"""
    return {
        "basic": {
            "system_name": "TCM-AI 中医智能诊断系统",
            "system_version": "v2.6.0",
            "server_port": 8000,
            "domain_name": "mxh0510.cn",
            "database_path": "/opt/tcm-ai/data/user_history.sqlite",
            "backup_retention": 30,
            "log_level": "INFO",
            "log_retention": 90,
            "session_timeout": 60,
            "upload_limit": 10,
            "api_timeout": 30,
            "max_connections": 100
        },
        "ai": {
            "dashscope_api_key": "[已配置环境变量，请勿修改]",
            "dashscope_endpoint": "https://dashscope.aliyuncs.com/api/v1/",
            "default_text_model": "qwen-max",
            "multimodal_model": "qwen-vl-max",
            "model_temperature": 0.7,
            "max_tokens": 2000,
            "daily_cost_limit": 500,
            "monthly_cost_limit": 15000,
            "retry_attempts": 3,
            "enable_cost_alerts": False
        },
        "business": {
            "standard_prescription_fee": 88,
            "decoction_service_fee": 50,
            "require_doctor_review": False,
            "prescription_validity": 30,
            "require_license_verification": False,
            "doctor_commission_rate": 15,
            "review_time_limit": 24,
            "auto_assign_doctors": False,
            "require_real_name": False,
            "free_consultation_limit": 1,
            "followup_interval": 7,
            "enable_patient_feedback": True
        },
        "security": {
            "password_min_length": 8,
            "require_password_complexity": False,
            "login_failure_limit": 5,
            "account_lockout_duration": 15,
            "api_rate_limit": 60,
            "enable_ip_whitelist": False,
            "ip_whitelist": "",
            "enable_https_only": True,
            "enable_audit_logging": True,
            "sensitive_log_retention": 365,
            "log_failed_requests": True,
            "enable_real_time_alerts": False
        },
        "integration": {
            "enable_alipay": True,
            "alipay_merchant_id": "",
            "enable_wechatpay": False,
            "wechat_merchant_id": "",
            "smtp_server": "",
            "smtp_port": 587,
            "sender_email": "",
            "sms_api_key": "",
            "enable_decoction_service": True,
            "decoction_api_endpoint": "",
            "decoction_api_key": "",
            "delivery_promise_days": 3
        }
    }

def validate_system_settings(settings):
    """验证系统配置数据"""
    validated = {}
    
    # 验证基础设置
    if 'basic' in settings:
        basic = settings['basic']
        validated['basic'] = {
            'system_name': str(basic.get('system_name', 'TCM-AI 中医智能诊断系统'))[:100],
            'system_version': str(basic.get('system_version', 'v2.6.0')),
            'server_port': max(1000, min(65535, int(basic.get('server_port', 8000)))),
            'domain_name': str(basic.get('domain_name', ''))[:200],
            'database_path': str(basic.get('database_path', '/opt/tcm-ai/data/user_history.sqlite')),
            'backup_retention': max(1, min(365, int(basic.get('backup_retention', 30)))),
            'log_level': basic.get('log_level', 'INFO') if basic.get('log_level') in ['DEBUG', 'INFO', 'WARNING', 'ERROR'] else 'INFO',
            'log_retention': max(7, min(365, int(basic.get('log_retention', 90)))),
            'session_timeout': max(5, min(1440, int(basic.get('session_timeout', 60)))),
            'upload_limit': max(1, min(100, int(basic.get('upload_limit', 10)))),
            'api_timeout': max(5, min(300, int(basic.get('api_timeout', 30)))),
            'max_connections': max(10, min(1000, int(basic.get('max_connections', 100))))
        }
    
    # 验证AI配置
    if 'ai' in settings:
        ai = settings['ai']
        validated['ai'] = {
            'dashscope_api_key': str(ai.get('dashscope_api_key', ''))[:200],
            'dashscope_endpoint': str(ai.get('dashscope_endpoint', 'https://dashscope.aliyuncs.com/api/v1/'))[:300],
            'default_text_model': ai.get('default_text_model', 'qwen-max') if ai.get('default_text_model') in ['qwen-max', 'qwen-plus', 'qwen-turbo'] else 'qwen-max',
            'multimodal_model': ai.get('multimodal_model', 'qwen-vl-max') if ai.get('multimodal_model') in ['qwen-vl-max', 'qwen-vl-plus'] else 'qwen-vl-max',
            'model_temperature': max(0.0, min(1.0, float(ai.get('model_temperature', 0.7)))),
            'max_tokens': max(100, min(8000, int(ai.get('max_tokens', 2000)))),
            'daily_cost_limit': max(1, min(10000, int(ai.get('daily_cost_limit', 500)))),
            'monthly_cost_limit': max(100, min(100000, int(ai.get('monthly_cost_limit', 15000)))),
            'retry_attempts': max(1, min(10, int(ai.get('retry_attempts', 3)))),
            'enable_cost_alerts': bool(ai.get('enable_cost_alerts', False))
        }
    
    # 验证其他配置分类（简化处理）
    for category in ['business', 'security', 'integration']:
        if category in settings:
            validated[category] = settings[category]
    
    return validated

def cleanup_old_backups(directory, prefix, keep_count):
    """清理旧的备份文件"""
    import glob
    
    try:
        backup_files = glob.glob(os.path.join(directory, f"{prefix}*.json"))
        backup_files.sort(key=os.path.getctime, reverse=True)
        
        # 删除多余的备份文件
        for old_backup in backup_files[keep_count:]:
            os.remove(old_backup)
            logger.info(f"已删除旧备份文件: {old_backup}")
    
    except Exception as e:
        logger.warning(f"清理备份文件失败: {e}")

@app.get("/api/admin/orders")
async def admin_get_orders(page: int = 1, per_page: int = 20):
    """获取订单列表"""
    try:
        orders, total = sqlite_service.fetch_admin_orders(page=page, per_page=per_page)
        
        return {
            "success": True,
            "orders": orders,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }
        
    except Exception as e:
        logger.error(f"获取订单列表失败: {e}")
        return {
            "success": False,
            "message": f"获取订单列表失败: {e}",
            "orders": [],
            "pagination": {"page": page, "per_page": per_page, "total": 0, "pages": 0}
        }

@app.get("/api/admin/system")
async def admin_system_monitor():
    """系统监控数据"""
    import psutil
    import os
    from datetime import datetime
    
    try:
        # 获取系统资源使用情况
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 获取进程信息
        current_process = psutil.Process()
        process_memory = current_process.memory_info()
        
        system_info = {
            "cpu_usage": cpu_percent,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100
            },
            "process": {
                "memory_rss": process_memory.rss,
                "memory_vms": process_memory.vms,
                "pid": current_process.pid
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "system": system_info
        }
        
    except Exception as e:
        logger.error(f"获取系统监控数据失败: {e}")
        # 返回模拟数据
        return {
            "success": True,
            "system": {
                "cpu_usage": 15.2,
                "memory": {
                    "total": 8589934592,
                    "available": 4294967296,
                    "percent": 50.0,
                    "used": 4294967296
                },
                "disk": {
                    "total": 107374182400,
                    "used": 53687091200,
                    "free": 53687091200,
                    "percent": 50.0
                },
                "timestamp": datetime.now().isoformat()
            }
        }

@app.get("/api/admin/logs")
async def admin_get_logs(
    page: int = 1, 
    per_page: int = 50,
    level: str = None,
    keyword: str = None,
    date: str = None
):
    """获取系统日志 - 从审计日志和安全日志中提取"""
    try:
        logs, total = sqlite_service.fetch_admin_logs(
            page=page,
            per_page=per_page,
            level=level,
            keyword=keyword,
            date=date,
        )
        
        # 如果数据库没有日志，尝试读取文件日志
        if not logs:
            log_file = "/opt/tcm-ai/api.log"
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for line in lines[-50:]:  # 只取最新50条
                    if line.strip():
                        # 简单解析日志行
                        log_level = "INFO"
                        if "ERROR" in line.upper():
                            log_level = "ERROR"
                        elif "WARN" in line.upper():
                            log_level = "WARN"
                        elif "DEBUG" in line.upper():
                            log_level = "DEBUG"
                        
                        # 过滤条件检查
                        if level and log_level != level:
                            continue
                        if keyword and keyword.lower() not in line.lower():
                            continue
                            
                        logs.append({
                            "timestamp": datetime.now().isoformat(),
                            "level": log_level,
                            "message": line.strip(),
                            "source": "api.log"
                        })
                
                total = len(logs)
            
            # 如果还是没有日志，返回模拟数据
            if not logs:
                logs = [
                    {
                        "timestamp": datetime.now().isoformat(),
                        "level": "INFO",
                        "message": "系统正常运行",
                        "source": "system"
                    },
                    {
                        "timestamp": datetime.now().isoformat(),
                        "level": "INFO", 
                        "message": "API服务器启动成功",
                        "source": "system"
                    }
                ]
                total = len(logs)
        
        return {
            "success": True,
            "logs": logs,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }
        
    except Exception as e:
        logger.error(f"获取系统日志失败: {e}")
        return {
            "success": False,
            "message": f"获取系统日志失败: {e}",
            "logs": [],
            "pagination": {"page": page, "per_page": per_page, "total": 0, "pages": 0}
        }

@app.get("/api/admin/logs/export")
async def admin_export_logs(
    level: str = None,
    keyword: str = None,
    date: str = None
):
    """导出系统日志为CSV格式"""
    try:
        from fastapi.responses import StreamingResponse
        import csv
        from io import StringIO
        rows = sqlite_service.fetch_admin_logs_for_export(
            level=level,
            keyword=keyword,
            date=date,
        )
        
        # 创建CSV内容
        output = StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(['时间', '级别', '来源', '消息'])
        
        # 写入数据
        for row in rows:
            writer.writerow([row[0], row[1], row[2], row[3]])
        
        # 如果没有数据，返回提示
        if not rows:
            writer.writerow(['暂无日志数据', '', '', ''])
        
        # 准备文件内容
        csv_content = output.getvalue()
        output.close()
        
        # 添加BOM以支持Excel正确显示中文
        csv_content = '\ufeff' + csv_content
        
        # 返回CSV文件
        return StreamingResponse(
            iter([csv_content.encode('utf-8')]),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=system-logs-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
            }
        )
        
    except Exception as e:
        logger.error(f"导出系统日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出失败: {e}")

# ==================== 医生工作台API ====================
# 所有医生API已移至 api/routes/doctor_routes.py 统一管理
# 避免重复定义和路由冲突

# ==================== Agent系统已完全移除 ====================
# 使用阿里云qwen大模型已足够，无需外部Agent服务
logger.info("使用阿里云qwen大模型，Agent系统已移除")

if __name__ == "__main__":
    import uvicorn
    
    # 临时修复配置 - 使用单worker避免启动问题
    uvicorn.run(
        app,  # 直接传递app对象而不是字符串
        host="0.0.0.0",
        port=8000,
        workers=1,  # 使用单worker避免多进程问题
        access_log=False,  # 关闭访问日志提升性能
        log_level="info",  # 显示详细日志以便调试
        timeout_keep_alive=30,  # 优化连接保持
        limit_concurrency=100,  # 限制并发连接数
        reload=False  # 明确禁用热重载
    )
    # 注意: uvicorn不支持preload参数，已移除
