#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中医诊断流程控制器
确保AI严格按照中医诊断流程进行，防止草率开具处方
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DiagnosisStage(Enum):
    """诊断阶段枚举"""
    INITIAL_INQUIRY = "initial_inquiry"      # 初步问诊
    DETAILED_SYMPTOMS = "detailed_symptoms"   # 详细症状收集
    TONGUE_EXAMINATION = "tongue_exam"        # 舌诊
    PULSE_EXAMINATION = "pulse_exam"          # 脉诊
    ADDITIONAL_INQUIRY = "additional_inquiry" # 补充问诊
    SYNDROME_ANALYSIS = "syndrome_analysis"   # 证候分析
    PRESCRIPTION_READY = "prescription_ready" # 可以开具处方

class DiagnosisRequirement(Enum):
    """诊断要求枚举"""
    MAIN_COMPLAINT = "main_complaint"         # 主诉
    PRESENT_ILLNESS = "present_illness"       # 现病史
    SYSTEM_REVIEW = "system_review"           # 系统回顾
    TONGUE_DESCRIPTION = "tongue_description" # 舌象描述
    PULSE_DESCRIPTION = "pulse_description"   # 脉象描述
    SLEEP_APPETITE = "sleep_appetite"         # 睡眠食欲
    BOWEL_URINATION = "bowel_urination"       # 二便情况
    EMOTIONAL_STATE = "emotional_state"       # 情志状态

@dataclass
class DiagnosisProgress:
    """诊断进度跟踪"""
    stage: DiagnosisStage
    completed_requirements: Set[DiagnosisRequirement]
    missing_requirements: Set[DiagnosisRequirement]
    conversation_count: int
    last_updated: datetime
    patient_data: Dict[str, Any]

class MedicalDiagnosisController:
    """中医诊断流程控制器"""
    
    def __init__(self):
        # 每个阶段的必需要求
        self.stage_requirements = {
            DiagnosisStage.INITIAL_INQUIRY: {
                DiagnosisRequirement.MAIN_COMPLAINT
            },
            DiagnosisStage.DETAILED_SYMPTOMS: {
                DiagnosisRequirement.MAIN_COMPLAINT,
                DiagnosisRequirement.PRESENT_ILLNESS,
                DiagnosisRequirement.SYSTEM_REVIEW
            },
            DiagnosisStage.TONGUE_EXAMINATION: {
                DiagnosisRequirement.MAIN_COMPLAINT,
                DiagnosisRequirement.PRESENT_ILLNESS,
                DiagnosisRequirement.TONGUE_DESCRIPTION
            },
            DiagnosisStage.PULSE_EXAMINATION: {
                DiagnosisRequirement.MAIN_COMPLAINT,
                DiagnosisRequirement.PRESENT_ILLNESS,
                DiagnosisRequirement.TONGUE_DESCRIPTION,
                DiagnosisRequirement.PULSE_DESCRIPTION
            },
            DiagnosisStage.ADDITIONAL_INQUIRY: {
                DiagnosisRequirement.MAIN_COMPLAINT,
                DiagnosisRequirement.PRESENT_ILLNESS,
                DiagnosisRequirement.TONGUE_DESCRIPTION,
                DiagnosisRequirement.PULSE_DESCRIPTION,
                DiagnosisRequirement.SLEEP_APPETITE,
                DiagnosisRequirement.BOWEL_URINATION
            },
            DiagnosisStage.SYNDROME_ANALYSIS: {
                DiagnosisRequirement.MAIN_COMPLAINT,
                DiagnosisRequirement.PRESENT_ILLNESS,
                DiagnosisRequirement.TONGUE_DESCRIPTION,
                DiagnosisRequirement.PULSE_DESCRIPTION,
                DiagnosisRequirement.SLEEP_APPETITE,
                DiagnosisRequirement.BOWEL_URINATION,
                DiagnosisRequirement.EMOTIONAL_STATE
            },
            DiagnosisStage.PRESCRIPTION_READY: {
                DiagnosisRequirement.MAIN_COMPLAINT,
                DiagnosisRequirement.PRESENT_ILLNESS,
                DiagnosisRequirement.TONGUE_DESCRIPTION,
                DiagnosisRequirement.PULSE_DESCRIPTION,
                DiagnosisRequirement.SLEEP_APPETITE,
                DiagnosisRequirement.BOWEL_URINATION,
                DiagnosisRequirement.EMOTIONAL_STATE
            }
        }
        
        # 用于检测已收集信息的关键词模式
        self.requirement_patterns = {
            DiagnosisRequirement.MAIN_COMPLAINT: [
                r'主要问题|主诉|主要症状|主要不适',
                r'感到|出现了|症状|不舒服'
            ],
            DiagnosisRequirement.PRESENT_ILLNESS: [
                r'什么时候开始|多久了|持续时间|发病时间',
                r'加重|缓解|诱因|性质|程度'
            ],
            DiagnosisRequirement.SYSTEM_REVIEW: [
                r'还有其他|伴随症状|同时出现|另外',
                r'头痛|头晕|胸闷|腰酸|乏力'
            ],
            DiagnosisRequirement.TONGUE_DESCRIPTION: [
                r'舌质|舌苔|舌体|舌边|舌尖',
                r'红|淡|暗|胖|瘦|厚|薄|白|黄|腻'
            ],
            DiagnosisRequirement.PULSE_DESCRIPTION: [
                r'脉象|脉搏|脉|跳动',
                r'浮|沉|迟|数|细|洪|弦|滑|涩|结|代'
            ],
            DiagnosisRequirement.SLEEP_APPETITE: [
                r'睡眠|入睡|失眠|多梦|早醒',
                r'食欲|胃口|吃饭|饮食|食量'
            ],
            DiagnosisRequirement.BOWEL_URINATION: [
                r'大便|小便|排便|排尿|二便',
                r'便秘|腹泻|尿频|尿急|尿痛'
            ],
            DiagnosisRequirement.EMOTIONAL_STATE: [
                r'情绪|心情|精神|情志|焦虑|抑郁',
                r'烦躁|易怒|担心|紧张|压力'
            ]
        }
        
        # 处方相关关键词检测
        self.prescription_keywords = [
            '处方', '方剂', '开药', '药方', '治疗方案', '用药',
            '中药', '汤剂', '开方', '配方', '药物', '开点药'
        ]
        
        # 诊断进度存储
        self.diagnosis_progress: Dict[str, DiagnosisProgress] = {}

    def analyze_conversation_requirements(self, conversation_history: List[Dict[str, str]]) -> Set[DiagnosisRequirement]:
        """分析对话历史，识别已满足的诊断要求"""
        completed_requirements = set()
        
        # 合并所有对话内容
        full_conversation = "\n".join([
            msg.get("content", "") for msg in conversation_history
        ])
        
        # 检查每个要求是否已满足
        for requirement, patterns in self.requirement_patterns.items():
            for pattern in patterns:
                if re.search(pattern, full_conversation, re.IGNORECASE):
                    completed_requirements.add(requirement)
                    break
        
        return completed_requirements

    def get_diagnosis_stage(self, conversation_id: str, conversation_history: List[Dict[str, str]]) -> DiagnosisStage:
        """根据对话历史确定当前诊断阶段"""
        completed_requirements = self.analyze_conversation_requirements(conversation_history)
        conversation_count = len(conversation_history)
        
        # 更新或创建诊断进度
        if conversation_id not in self.diagnosis_progress:
            self.diagnosis_progress[conversation_id] = DiagnosisProgress(
                stage=DiagnosisStage.INITIAL_INQUIRY,
                completed_requirements=completed_requirements,
                missing_requirements=set(),
                conversation_count=conversation_count,
                last_updated=datetime.now(),
                patient_data={}
            )
        else:
            self.diagnosis_progress[conversation_id].completed_requirements = completed_requirements
            self.diagnosis_progress[conversation_id].conversation_count = conversation_count
            self.diagnosis_progress[conversation_id].last_updated = datetime.now()
        
        # 根据已完成的要求确定阶段
        progress = self.diagnosis_progress[conversation_id]
        
        # 逐级检查是否满足各阶段要求
        for stage, required_set in self.stage_requirements.items():
            if required_set.issubset(completed_requirements):
                progress.stage = stage
            else:
                # 找到第一个不满足的阶段，就是当前应该处于的阶段
                progress.missing_requirements = required_set - completed_requirements
                break
        
        return progress.stage

    def can_prescribe(self, conversation_id: str, conversation_history: List[Dict[str, str]], user_message: str) -> tuple[bool, str]:
        """检查是否可以开具处方 - 张仲景风格的合理严谨模式"""
        
        # 基本轮数检查 - 至少需要2轮对话了解病情
        if len(conversation_history) < 2:
            return False, f"需要进一步了解病情（当前{len(conversation_history)}轮对话）"
        
        # 检查用户是否明确要求处方
        requesting_prescription = any(keyword in user_message for keyword in self.prescription_keywords)
        
        # 合并所有对话内容分析
        full_conversation = "\n".join([
            msg.get("content", "") for msg in conversation_history
        ])
        
        # 检查基本症状信息
        has_symptoms = any(pattern in full_conversation for pattern in [
            '疼', '痛', '胀', '酸', '麻', '热', '冷', '咳', '喘', '泻', '便秘', 
            '头晕', '乏力', '失眠', '焦虑', '抑郁', '发烧', '咽痛', '流鼻涕',
            '恶心', '呕吐', '腹泻', '食欲', '出汗', '怕冷', '怕热'
        ])
        
        # 检查症状描述的基本完整性
        symptom_completeness = 0
        
        # 有明确的症状位置和性质
        if any(pattern in full_conversation for pattern in ['头', '胃', '腹', '胸', '腰', '背', '四肢', '身体', '全身']):
            symptom_completeness += 1
            
        # 有时间相关信息    
        if any(pattern in full_conversation for pattern in ['天', '周', '月', '最近', '今天', '昨天', '一直', '经常', '总是']):
            symptom_completeness += 1
            
        # 有诱因或伴随情况
        if any(pattern in full_conversation for pattern in ['吃', '喝', '累', '压力', '情绪', '天气', '还有', '同时', '伴有']):
            symptom_completeness += 1
            
        # 有具体症状描述（新增）
        if any(pattern in full_conversation for pattern in ['疲劳', '乏力', '无力', '困倦', '精神', '状态', '感觉']):
            symptom_completeness += 1
            
        # 检查是否有舌象信息（图片或描述）
        full_conversation_lower = full_conversation.lower()
        has_tongue_info = any(pattern in full_conversation_lower for pattern in [
            '舌象', '舌苔', '舌质', '舌边', '舌尖', '苔薄', '苔厚', '苔白', '苔黄', '苔红',
            '齿痕', '舌体', '胖大', '【图像分析结果】', '【已分析图像】', '上传', '图片', '照片',
            '舌', '苔', '舌头', '舌质淡红', '苔白厚腻'  # 增加更多匹配模式
        ])
        
        # 有舌象或体征描述（新增）
        if has_tongue_info:
            symptom_completeness += 1
        
        # 处方决策 - 中医辨证论治原则：严谨且科学
        if requesting_prescription:
            # 用户明确要求处方时的判断
            if not has_symptoms:
                return False, "请先详细描述您的不适症状"
            
                # 基于中医辨证论治的开方标准
            tcm_info = self._check_tcm_diagnostic_info(full_conversation)
            info_score, missing_items = self._evaluate_tcm_completeness(tcm_info)
            
            # 开方决策：基于中医辨证所需信息完整度
            if info_score >= 5:  # 7项信息中有5项或以上
                return True, "中医辨证信息充分，可以开具处方"
            elif info_score >= 4 and tcm_info['tongue']:
                return True, "关键辨证信息完整，舌象清晰，可以开方"
            elif info_score >= 3:
                missing_str = "、".join(missing_items[:2])  # 显示缺失的前2项
                return False, f"辨证信息还需完善，建议补充：{missing_str}等情况"
            else:
                return False, "信息不足以进行准确的中医辨证，请详细描述症状、食欲、睡眠、二便等情况"
        
        # 未明确要求处方时，主动建议获取更多信息
        if len(conversation_history) >= 2 and has_symptoms:
            if has_tongue_info and symptom_completeness >= 3:
                return True, "信息较完整，如需要可以开具处方"
            else:
                return False, "信息收集中，继续问诊了解病情"
        elif len(conversation_history) >= 3 and has_symptoms and symptom_completeness >= 2:
            # 条件足够时，可以主动建议处方
            return True, "症状了解较为清楚，可根据需要开具处方"
        
        # 未明确要求处方时，基于信息完整度评估
        tcm_info = self._check_tcm_diagnostic_info(full_conversation)
        info_score = sum(tcm_info.values())
        
        if info_score >= 5:
            return True, "辨证信息较为完整，可根据需要开具处方"
        elif info_score >= 4:
            return True, "信息基本充分，如需处方可以开具"
        else:
            return False, "正在问诊中，需要进一步了解症状详情"

    def get_next_inquiry_prompt(self, conversation_id: str, conversation_history: List[Dict[str, str]]) -> str:
        """获取下一步问诊提示"""
        current_stage = self.get_diagnosis_stage(conversation_id, conversation_history)
        progress = self.diagnosis_progress.get(conversation_id)
        
        stage_prompts = {
            DiagnosisStage.INITIAL_INQUIRY: "请详细描述您的主要症状和不适感受。",
            DiagnosisStage.DETAILED_SYMPTOMS: "请描述症状的具体情况：什么时候开始的？什么情况下加重或缓解？还有其他伴随症状吗？",
            DiagnosisStage.TONGUE_EXAMINATION: "为了更好地诊断，我需要了解您的舌象。请观察您的舌质颜色、舌苔厚薄和颜色等情况。",
            DiagnosisStage.PULSE_EXAMINATION: "请让我了解您的脉象情况，如脉搏跳动的快慢、强弱等特点。",
            DiagnosisStage.ADDITIONAL_INQUIRY: "还需要了解您的睡眠质量、食欲情况、大小便等基本生活状况。",
            DiagnosisStage.SYNDROME_ANALYSIS: "最后请告诉我您最近的情绪状态和精神状况。",
            DiagnosisStage.PRESCRIPTION_READY: "诊断信息已收集完整，如果您需要治疗方案或处方，请明确提出。"
        }
        
        base_prompt = stage_prompts.get(current_stage, "请提供更多症状信息。")
        
        # 添加具体缺失信息的提示
        if progress and progress.missing_requirements:
            missing_details = {
                DiagnosisRequirement.MAIN_COMPLAINT: "具体的主要症状",
                DiagnosisRequirement.PRESENT_ILLNESS: "症状的详细发展过程",
                DiagnosisRequirement.TONGUE_DESCRIPTION: "舌质和舌苔的具体描述",
                DiagnosisRequirement.PULSE_DESCRIPTION: "脉象的具体特征",
                DiagnosisRequirement.SLEEP_APPETITE: "睡眠和食欲状况",
                DiagnosisRequirement.BOWEL_URINATION: "大小便情况",
                DiagnosisRequirement.EMOTIONAL_STATE: "情绪和精神状态"
            }
            
            missing_list = [missing_details.get(req, str(req)) for req in progress.missing_requirements]
            base_prompt += f"\n\n特别需要了解：{', '.join(missing_list)}"
        
        return base_prompt

    def check_prescription_safety(self, user_message: str, conversation_history: List[Dict[str, str]]) -> tuple[bool, str]:
        """检查处方安全性 - 防止AI草率开方"""
        
        # 检查是否有处方相关请求
        has_prescription_request = any(keyword in user_message for keyword in self.prescription_keywords)
        
        if not has_prescription_request:
            return True, "无处方请求"
        
        # 检查对话是否过于简短
        if len(conversation_history) < 6:  # 至少需要3轮对话（6条消息）
            return False, "对话轮次不足，无法确保充分了解病情"
        
        # 检查是否收集了足够的四诊信息
        full_conversation = "\n".join([msg.get("content", "") for msg in conversation_history])
        
        # 必须包含的信息类型
        required_info_checks = {
            "症状描述": [r'症状|不适|疼痛|发热|咳嗽|头痛|腹痛'],
            "舌象信息": [r'舌质|舌苔|舌.*红|舌.*淡|苔.*白|苔.*黄'],
            "脉象信息": [r'脉象|脉.*浮|脉.*沉|脉.*细|脉.*数|脉.*迟'],
            "生活状况": [r'睡眠|食欲|大便|小便|二便']
        }
        
        missing_info = []
        for info_type, patterns in required_info_checks.items():
            found = False
            for pattern in patterns:
                if re.search(pattern, full_conversation, re.IGNORECASE):
                    found = True
                    break
            if not found:
                missing_info.append(info_type)
        
        if missing_info:
            return False, f"诊断信息不完整，缺少：{', '.join(missing_info)}"
        
        return True, "诊断信息充分，可以开具处方"

    def generate_safety_prompt(self, conversation_id: str, user_message: str, conversation_history: List[Dict[str, str]]) -> str:
        """生成安全的系统提示，防止草率开方"""
        
        can_prescribe, reason = self.can_prescribe(conversation_id, conversation_history, user_message)
        
        if can_prescribe:
            return """
            **诊断已充分，可以开具处方**
            
            请严格按照中医诊断流程，基于已收集的完整四诊信息进行：
            1. 证候分析和辨证论治
            2. 选择适当的治法和方剂
            3. 开具详细的处方和用药指导
            
            注意：必须基于患者实际描述的症状，不得编造任何未经患者确认的舌象、脉象或其他体征信息。
            """
        else:
            next_inquiry = self.get_next_inquiry_prompt(conversation_id, conversation_history)
            return f"""
            **诊断流程控制 - 暂不开具处方**
            
            原因：{reason}
            
            请继续问诊收集必要信息：
            {next_inquiry}
            
            **严禁事项**：
            - 不得基于不完整信息开具处方
            - 不得编造患者未描述的舌象、脉象信息
            - 不得跳过必要的诊断步骤
            
            只有在收集完整的四诊信息后，才能进行证候分析和开具处方。
            """

    def get_diagnosis_progress_info(self, conversation_id: str) -> Dict[str, Any]:
        """获取诊断进度信息"""
        if conversation_id not in self.diagnosis_progress:
            return {"error": "未找到诊断进度信息"}
        
        progress = self.diagnosis_progress[conversation_id]
        
        return {
            "conversation_id": conversation_id,
            "current_stage": progress.stage.value,
            "completed_requirements": [req.value for req in progress.completed_requirements],
            "missing_requirements": [req.value for req in progress.missing_requirements],
            "conversation_count": progress.conversation_count,
            "can_prescribe": progress.stage == DiagnosisStage.PRESCRIPTION_READY,
            "last_updated": progress.last_updated.isoformat()
        }

    def _check_tcm_diagnostic_info(self, conversation_text: str) -> dict:
        """检查中医辨证所需的核心信息"""
        return {
            # 1. 主要症状（必需）
            'main_symptoms': self._check_main_symptoms_detailed(conversation_text),
            
            # 2. 口干口苦情况 (津液状态)
            'thirst_taste': any(pattern in conversation_text for pattern in [
                '口干', '口苦', '口渴', '口淡', '口甜', '口腻', '口臭', '不渴',
                '喜热饮', '喜冷饮', '饮水', '口中', '口味'
            ]),
            
            # 3. 食欲消化情况 (脾胃功能)
            'appetite': any(pattern in conversation_text for pattern in [
                '食欲', '胃口', '食量', '想吃', '不想吃', '吃不下', '消化', 
                '腹胀', '腹痛', '胃痛', '胃胀', '恶心', '呕吐', '反酸', '烧心'
            ]),
            
            # 4. 睡眠情况 (心肾阴阳)
            'sleep': any(pattern in conversation_text for pattern in [
                '睡眠', '失眠', '入睡', '易醒', '多梦', '早醒', '睡不着', 
                '睡得', '困倦', '瞌睡', '精神状态'
            ]),
            
            # 5. 大小便情况 (脏腑功能)
            'bowel_urination': any(pattern in conversation_text for pattern in [
                '大便', '小便', '便秘', '腹泻', '溏便', '干燥', '尿频', '尿急',
                '尿少', '尿多', '排便', '排尿', '二便', '上厕所', '拉肚子'
            ]),
            
            # 6. 出汗情况 (营卫状态)
            'sweating': any(pattern in conversation_text for pattern in [
                '出汗', '汗出', '多汗', '少汗', '无汗', '盗汗', '自汗', 
                '容易出汗', '不出汗', '汗液', '发汗'
            ]),
            
            # 7. 舌象情况 (内脏反映)
            'tongue': any(pattern in conversation_text for pattern in [
                '舌象', '舌苔', '舌质', '舌边', '舌尖', '苔薄', '苔厚', '苔白', 
                '苔黄', '苔腻', '齿痕', '舌体', '舌头', '舌', '苔'
            ]),
        }
    
    def _check_main_symptoms_detailed(self, conversation_text: str) -> bool:
        """检查主要症状是否有详细描述"""
        # 基础症状关键词
        basic_symptoms = [
            '疼', '痛', '胀', '闷', '酸', '麻', '咳嗽', '发热', '头晕', '乏力', 
            '疲劳', '失眠', '便秘', '腹泻', '不适', '难受'
        ]
        
        # 症状部位或性质描述
        detail_keywords = [
            '头', '胃', '腹', '胸', '腰', '背', '四肢', '全身',  # 部位
            '持续', '间歇', '加重', '缓解', '最近', '一直', '总是'  # 性质和时间
        ]
        
        has_basic = any(symptom in conversation_text for symptom in basic_symptoms)
        has_detail = any(detail in conversation_text for detail in detail_keywords)
        
        return has_basic and has_detail
    
    def _evaluate_tcm_completeness(self, tcm_info: dict) -> tuple[int, list]:
        """评估中医信息完整度，返回得分和缺失项目"""
        
        info_mapping = {
            'main_symptoms': '主要症状详情',
            'thirst_taste': '口干口苦情况', 
            'appetite': '食欲胃口情况',
            'sleep': '睡眠情况',
            'bowel_urination': '大小便情况',
            'sweating': '出汗情况',
            'tongue': '舌苔舌象'
        }
        
        score = sum(tcm_info.values())
        missing_items = [info_mapping[key] for key, value in tcm_info.items() if not value]
        
        return score, missing_items

# 全局实例
medical_diagnosis_controller = MedicalDiagnosisController()

def test_diagnosis_controller():
    """测试诊断控制器功能"""
    controller = MedicalDiagnosisController()
    
    # 模拟对话历史
    test_conversations = [
        {"role": "user", "content": "我最近头痛"},
        {"role": "assistant", "content": "请详细描述您的头痛症状"},
        {"role": "user", "content": "头痛已经持续3天了，在太阳穴位置，还有点恶心"},
        {"role": "assistant", "content": "需要了解您的舌象"},
        {"role": "user", "content": "舌质红，苔薄白"},
        {"role": "assistant", "content": "脉象如何？"},
        {"role": "user", "content": "脉象浮数"},
        {"role": "assistant", "content": "睡眠和食欲怎么样？"},
        {"role": "user", "content": "睡眠不好，食欲一般，大便正常，小便黄"},
        {"role": "assistant", "content": "情绪状态如何？"},
        {"role": "user", "content": "最近工作压力大，有些焦虑"},
        {"role": "user", "content": "请开个处方"}
    ]
    
    conversation_id = "test_123"
    
    # 测试各阶段诊断能力
    for i in range(2, len(test_conversations), 2):
        current_history = test_conversations[:i]
        stage = controller.get_diagnosis_stage(conversation_id, current_history)
        can_prescribe, reason = controller.can_prescribe(conversation_id, current_history, "请开处方")
        
        print(f"对话轮次: {i//2}")
        print(f"当前阶段: {stage.value}")
        print(f"可以开方: {can_prescribe}")
        print(f"原因: {reason}")
        print("-" * 50)


if __name__ == "__main__":
    test_diagnosis_controller()