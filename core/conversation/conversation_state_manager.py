#!/usr/bin/env python3
"""
对话状态管理器
管理中医问诊对话的完整生命周期和状态转换
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

class ConversationStage(Enum):
    """对话阶段枚举"""
    INQUIRY = "inquiry"                          # 初始问诊阶段
    DETAILED_INQUIRY = "detailed_inquiry"        # 详细问诊阶段  
    INTERIM_ADVICE = "interim_advice"            # 临时建议阶段
    DIAGNOSIS = "diagnosis"                      # 诊断阶段
    PRESCRIPTION = "prescription"                # 处方阶段
    PRESCRIPTION_CONFIRM = "prescription_confirm" # 处方确认阶段
    COMPLETED = "completed"                      # 对话结束阶段
    TIMEOUT = "timeout"                          # 超时状态
    EMERGENCY = "emergency"                      # 紧急状态

class ConversationEndType(Enum):
    """对话结束类型"""
    NATURAL = "natural"                          # 自然结束
    PRESCRIPTION_CONFIRMED = "prescription_confirmed"  # 处方确认结束
    USER_TERMINATED = "user_terminated"          # 用户主动结束
    TIMEOUT = "timeout"                          # 超时结束
    EMERGENCY_REFERRAL = "emergency_referral"    # 紧急转诊
    SYSTEM_LIMIT = "system_limit"                # 系统限制

@dataclass
class ConversationState:
    """对话状态数据类"""
    conversation_id: str
    user_id: str
    doctor_id: str
    current_stage: ConversationStage
    start_time: datetime
    last_activity: datetime
    turn_count: int = 0
    has_prescription: bool = False
    prescription_id: Optional[int] = None
    is_active: bool = True
    end_type: Optional[ConversationEndType] = None
    symptoms_collected: List[str] = None
    diagnosis_confidence: float = 0.0
    stage_history: List[Dict] = None
    timeout_warnings: int = 0
    
    def __post_init__(self):
        if self.symptoms_collected is None:
            self.symptoms_collected = []
        if self.stage_history is None:
            self.stage_history = []

class ConversationStateManager:
    """对话状态管理器"""
    
    # 超时配置（秒）
    RESPONSE_TIMEOUT = 300      # 5分钟响应超时
    SESSION_TIMEOUT = 1800      # 30分钟会话超时
    MAX_TURNS = 20              # 最大对话轮数
    MAX_TIMEOUT_WARNINGS = 3    # 最大超时警告次数
    
    # 状态转换规则
    VALID_TRANSITIONS = {
        ConversationStage.INQUIRY: [
            ConversationStage.DETAILED_INQUIRY,
            ConversationStage.INTERIM_ADVICE,
            ConversationStage.COMPLETED,
            ConversationStage.EMERGENCY
        ],
        ConversationStage.DETAILED_INQUIRY: [
            ConversationStage.INTERIM_ADVICE,
            ConversationStage.DIAGNOSIS,
            ConversationStage.PRESCRIPTION,
            ConversationStage.COMPLETED,
            ConversationStage.EMERGENCY
        ],
        ConversationStage.INTERIM_ADVICE: [
            ConversationStage.DETAILED_INQUIRY,
            ConversationStage.DIAGNOSIS,
            ConversationStage.PRESCRIPTION,
            ConversationStage.COMPLETED
        ],
        ConversationStage.DIAGNOSIS: [
            ConversationStage.INTERIM_ADVICE,
            ConversationStage.PRESCRIPTION,
            ConversationStage.COMPLETED,
            ConversationStage.EMERGENCY
        ],
        ConversationStage.PRESCRIPTION: [
            ConversationStage.PRESCRIPTION_CONFIRM,
            ConversationStage.DETAILED_INQUIRY,  # 可以回到问诊阶段
            ConversationStage.COMPLETED
        ],
        ConversationStage.PRESCRIPTION_CONFIRM: [
            ConversationStage.COMPLETED,
            ConversationStage.DETAILED_INQUIRY   # 患者可以选择继续问诊
        ]
    }
    
    def __init__(self, db_path: str = "/opt/tcm-ai/data/user_history.sqlite"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 创建对话状态表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_states (
                    conversation_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    doctor_id TEXT NOT NULL,
                    current_stage TEXT NOT NULL,
                    start_time DATETIME NOT NULL,
                    last_activity DATETIME NOT NULL,
                    turn_count INTEGER DEFAULT 0,
                    has_prescription BOOLEAN DEFAULT 0,
                    prescription_id INTEGER,
                    is_active BOOLEAN DEFAULT 1,
                    end_type TEXT,
                    symptoms_collected TEXT,  -- JSON格式
                    diagnosis_confidence REAL DEFAULT 0.0,
                    stage_history TEXT,       -- JSON格式
                    timeout_warnings INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建状态变更历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_stage_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    from_stage TEXT,
                    to_stage TEXT NOT NULL,
                    reason TEXT,
                    confidence_score REAL,
                    turn_number INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversation_states(conversation_id)
                )
            """)
            
            # 创建对话终结记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_endings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    end_type TEXT NOT NULL,
                    end_reason TEXT,
                    final_stage TEXT,
                    total_turns INTEGER,
                    duration_seconds INTEGER,
                    user_satisfaction REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversation_states(conversation_id)
                )
            """)
            
            conn.commit()
            logger.info("对话状态数据库初始化完成")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def create_conversation(self, conversation_id: str, user_id: str, 
                          doctor_id: str) -> ConversationState:
        """创建新对话状态"""
        now = datetime.now()
        state = ConversationState(
            conversation_id=conversation_id,
            user_id=user_id,
            doctor_id=doctor_id,
            current_stage=ConversationStage.INQUIRY,
            start_time=now,
            last_activity=now
        )
        
        # 记录初始阶段
        state.stage_history.append({
            "stage": ConversationStage.INQUIRY.value,
            "timestamp": now.isoformat(),
            "reason": "对话开始"
        })
        
        self._save_state(state)
        self._log_stage_change(conversation_id, None, ConversationStage.INQUIRY, 
                             "对话开始", 0.0, 0)
        
        logger.info(f"创建新对话状态: {conversation_id}")
        return state
    
    def get_conversation_state(self, conversation_id: str) -> Optional[ConversationState]:
        """获取对话状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM conversation_states WHERE conversation_id = ?
            """, (conversation_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            # 解析数据
            return ConversationState(
                conversation_id=row[0],
                user_id=row[1],
                doctor_id=row[2],
                current_stage=ConversationStage(row[3]),
                start_time=datetime.fromisoformat(row[4]),
                last_activity=datetime.fromisoformat(row[5]),
                turn_count=row[6],
                has_prescription=bool(row[7]),
                prescription_id=row[8],
                is_active=bool(row[9]),
                end_type=ConversationEndType(row[10]) if row[10] else None,
                symptoms_collected=json.loads(row[11] or "[]"),
                diagnosis_confidence=row[12],
                stage_history=json.loads(row[13] or "[]"),
                timeout_warnings=row[14]
            )
            
        except Exception as e:
            logger.error(f"获取对话状态失败: {e}")
            return None
        finally:
            conn.close()
    
    def update_stage(self, conversation_id: str, new_stage: ConversationStage, 
                    reason: str = "", confidence: float = 0.0) -> bool:
        """更新对话阶段"""
        state = self.get_conversation_state(conversation_id)
        if not state:
            logger.error(f"对话状态不存在: {conversation_id}")
            return False
        
        # 检查状态转换是否合法
        if not self._is_valid_transition(state.current_stage, new_stage):
            logger.warning(f"非法状态转换: {state.current_stage.value} -> {new_stage.value}")
            return False
        
        # 更新状态
        old_stage = state.current_stage
        state.current_stage = new_stage
        state.last_activity = datetime.now()
        
        # 记录阶段历史
        state.stage_history.append({
            "stage": new_stage.value,
            "timestamp": state.last_activity.isoformat(),
            "reason": reason,
            "confidence": confidence
        })
        
        # 特殊处理
        if new_stage == ConversationStage.PRESCRIPTION:
            state.has_prescription = True
        elif new_stage in [ConversationStage.COMPLETED, ConversationStage.TIMEOUT]:
            state.is_active = False
        
        # 保存状态
        self._save_state(state)
        self._log_stage_change(conversation_id, old_stage, new_stage, reason, 
                              confidence, state.turn_count)
        
        logger.info(f"对话阶段更新: {conversation_id} {old_stage.value} -> {new_stage.value}")
        return True
    
    def increment_turn(self, conversation_id: str) -> bool:
        """增加对话轮数"""
        state = self.get_conversation_state(conversation_id)
        if not state or not state.is_active:
            return False
        
        state.turn_count += 1
        state.last_activity = datetime.now()
        
        # 检查是否达到最大轮数
        if state.turn_count >= self.MAX_TURNS:
            self.end_conversation(conversation_id, ConversationEndType.SYSTEM_LIMIT,
                                "达到最大对话轮数限制")
            return False
        
        self._save_state(state)
        return True
    
    def update_symptoms(self, conversation_id: str, symptoms: List[str]) -> bool:
        """更新症状收集"""
        state = self.get_conversation_state(conversation_id)
        if not state:
            return False
        
        # 🔧 修复：确保类型安全的症状合并
        # 确保state.symptoms_collected是列表
        if not isinstance(state.symptoms_collected, list):
            logger.warning(f"症状收集数据类型错误: {type(state.symptoms_collected)}, 重置为空列表")
            state.symptoms_collected = []
            
        # 确保symptoms是列表
        if not isinstance(symptoms, list):
            logger.warning(f"传入症状参数类型错误: {type(symptoms)}, 尝试转换")
            if isinstance(symptoms, dict):
                symptoms = list(symptoms.keys()) if symptoms else []
            else:
                symptoms = []
        
        # 安全的症状合并（去重）
        try:
            all_symptoms = list(set(state.symptoms_collected + symptoms))
        except TypeError as e:
            logger.error(f"症状合并失败: {e}, 使用安全方式合并")
            # 安全备用方案
            existing_symptoms = state.symptoms_collected if isinstance(state.symptoms_collected, list) else []
            new_symptoms = symptoms if isinstance(symptoms, list) else []
            all_symptoms = list(set(existing_symptoms + new_symptoms))
        
        state.symptoms_collected = all_symptoms
        state.last_activity = datetime.now()
        
        self._save_state(state)
        logger.info(f"更新症状收集: {conversation_id}, 症状数量: {len(all_symptoms)}")
        return True
    
    def check_timeout(self, conversation_id: str) -> Tuple[bool, str]:
        """检查超时状态"""
        state = self.get_conversation_state(conversation_id)
        if not state or not state.is_active:
            return False, "对话已结束"
        
        now = datetime.now()
        time_since_activity = (now - state.last_activity).total_seconds()
        
        # 会话超时
        if time_since_activity > self.SESSION_TIMEOUT:
            self.end_conversation(conversation_id, ConversationEndType.TIMEOUT,
                                "会话超时")
            return True, "会话已超时，对话已结束"
        
        # 响应超时警告
        elif time_since_activity > self.RESPONSE_TIMEOUT:
            state.timeout_warnings += 1
            self._save_state(state)
            
            if state.timeout_warnings >= self.MAX_TIMEOUT_WARNINGS:
                self.end_conversation(conversation_id, ConversationEndType.TIMEOUT,
                                    "多次响应超时")
                return True, "多次无响应，对话已结束"
            
            return False, f"请及时回复，{self.RESPONSE_TIMEOUT//60}分钟内无响应将结束对话"
        
        return False, ""
    
    def should_end_conversation(self, conversation_id: str, message: str) -> Tuple[bool, ConversationEndType, str]:
        """判断是否应该结束对话"""
        state = self.get_conversation_state(conversation_id)
        if not state:
            return True, ConversationEndType.SYSTEM_LIMIT, "会话状态不存在"
        
        # 检查结束性话语
        end_keywords = [
            "谢谢", "感谢", "我了解了", "暂时这样", "不用了", "再见",
            "好的，知道了", "明白了", "就这样吧", "先这样", "够了"
        ]
        
        if any(keyword in message for keyword in end_keywords):
            return True, ConversationEndType.NATURAL, "用户表示结束"
        
        # 检查紧急情况关键词
        emergency_keywords = [
            "很痛", "剧痛", "无法忍受", "呼吸困难", "胸闷", "心慌",
            "昏迷", "抽搐", "大出血", "高热", "急诊"
        ]
        
        if any(keyword in message for keyword in emergency_keywords):
            return True, ConversationEndType.EMERGENCY_REFERRAL, "检测到紧急情况"
        
        return False, None, ""
    
    def end_conversation(self, conversation_id: str, end_type: ConversationEndType,
                        reason: str = "", user_satisfaction: float = None) -> bool:
        """结束对话"""
        state = self.get_conversation_state(conversation_id)
        if not state:
            return False
        
        # 更新状态
        state.is_active = False
        state.end_type = end_type
        
        # 如果当前不是完成状态，更新为完成状态
        if state.current_stage != ConversationStage.COMPLETED:
            if end_type == ConversationEndType.TIMEOUT:
                state.current_stage = ConversationStage.TIMEOUT
            elif end_type == ConversationEndType.EMERGENCY_REFERRAL:
                state.current_stage = ConversationStage.EMERGENCY
            else:
                state.current_stage = ConversationStage.COMPLETED
        
        self._save_state(state)
        
        # 记录结束信息
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            duration = (datetime.now() - state.start_time).total_seconds()
            cursor.execute("""
                INSERT INTO conversation_endings 
                (conversation_id, end_type, end_reason, final_stage, total_turns, 
                 duration_seconds, user_satisfaction)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (conversation_id, end_type.value, reason, state.current_stage.value,
                  state.turn_count, int(duration), user_satisfaction))
            
            conn.commit()
            logger.info(f"对话结束: {conversation_id}, 类型: {end_type.value}, 原因: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"记录对话结束失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_conversation_progress(self, conversation_id: str) -> Dict[str, Any]:
        """获取对话进度信息"""
        state = self.get_conversation_state(conversation_id)
        if not state:
            return {}
        
        # 计算进度百分比
        stage_weights = {
            ConversationStage.INQUIRY: 0.1,
            ConversationStage.DETAILED_INQUIRY: 0.3,
            ConversationStage.INTERIM_ADVICE: 0.5,
            ConversationStage.DIAGNOSIS: 0.7,
            ConversationStage.PRESCRIPTION: 0.9,
            ConversationStage.PRESCRIPTION_CONFIRM: 0.95,
            ConversationStage.COMPLETED: 1.0
        }
        
        progress = stage_weights.get(state.current_stage, 0.0) * 100
        
        return {
            "conversation_id": conversation_id,
            "current_stage": state.current_stage.value,
            "stage_display": self._get_stage_display_name(state.current_stage),
            "progress_percentage": progress,
            "turn_count": state.turn_count,
            "max_turns": self.MAX_TURNS,
            "symptoms_count": len(state.symptoms_collected),
            "has_prescription": state.has_prescription,
            "diagnosis_confidence": state.diagnosis_confidence,
            "duration_minutes": int((datetime.now() - state.start_time).total_seconds() / 60),
            "is_active": state.is_active
        }
    
    def get_stage_guidance(self, conversation_id: str) -> Dict[str, Any]:
        """获取阶段引导信息"""
        state = self.get_conversation_state(conversation_id)
        if not state:
            return {}
        
        guidance = {
            ConversationStage.INQUIRY: {
                "title": "症状收集",
                "description": "请详细描述您的主要不适症状",
                "suggestions": [
                    "症状具体表现如何？",
                    "什么时候开始出现的？",
                    "有什么诱发因素吗？"
                ]
            },
            ConversationStage.DETAILED_INQUIRY: {
                "title": "详细问诊",
                "description": "医生正在深入了解您的症状细节",
                "suggestions": [
                    "请如实回答医生的问题",
                    "可以补充相关的伴随症状",
                    "如有舌象图片可以上传"
                ]
            },
            ConversationStage.INTERIM_ADVICE: {
                "title": "初步建议",
                "description": "医生已给出初步建议，需要您补充更多信息",
                "suggestions": [
                    "请根据医生要求补充信息",
                    "可以询问不明白的地方",
                    "提供更多症状细节有助于准确诊断"
                ]
            },
            ConversationStage.DIAGNOSIS: {
                "title": "证候分析",
                "description": "医生正在进行中医证候分析",
                "suggestions": [
                    "医生正在分析您的证候类型",
                    "如有疑问可以继续询问",
                    "即将给出治疗方案"
                ]
            },
            ConversationStage.PRESCRIPTION: {
                "title": "治疗方案",
                "description": "医生已给出完整的治疗方案",
                "suggestions": [
                    "请仔细阅读处方内容",
                    "如有疑问请及时询问",
                    "可以选择确认处方或继续咨询"
                ]
            },
            ConversationStage.PRESCRIPTION_CONFIRM: {
                "title": "处方确认",
                "description": "请确认是否接受此处方方案",
                "suggestions": [
                    "仔细核对处方信息",
                    "确认用法用量",
                    "可以选择接受处方或继续咨询"
                ]
            }
        }
        
        current_guidance = guidance.get(state.current_stage, {
            "title": "问诊进行中",
            "description": "请继续与医生交流",
            "suggestions": []
        })
        
        current_guidance["stage"] = state.current_stage.value
        return current_guidance
    
    def _save_state(self, state: ConversationState) -> bool:
        """保存对话状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO conversation_states 
                (conversation_id, user_id, doctor_id, current_stage, start_time, 
                 last_activity, turn_count, has_prescription, prescription_id, is_active,
                 end_type, symptoms_collected, diagnosis_confidence, stage_history,
                 timeout_warnings, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                state.conversation_id,
                state.user_id,
                state.doctor_id,
                state.current_stage.value,
                state.start_time.isoformat(),
                state.last_activity.isoformat(),
                state.turn_count,
                state.has_prescription,
                state.prescription_id,
                state.is_active,
                state.end_type.value if state.end_type else None,
                json.dumps(state.symptoms_collected, ensure_ascii=False),
                state.diagnosis_confidence,
                json.dumps(state.stage_history, ensure_ascii=False),
                state.timeout_warnings
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"保存对话状态失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def _log_stage_change(self, conversation_id: str, from_stage: Optional[ConversationStage],
                         to_stage: ConversationStage, reason: str, confidence: float,
                         turn_number: int) -> bool:
        """记录阶段变更日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO conversation_stage_history
                (conversation_id, from_stage, to_stage, reason, confidence_score, turn_number)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                conversation_id,
                from_stage.value if from_stage else None,
                to_stage.value,
                reason,
                confidence,
                turn_number
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"记录阶段变更失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def _is_valid_transition(self, from_stage: ConversationStage, 
                           to_stage: ConversationStage) -> bool:
        """检查状态转换是否合法"""
        if from_stage == to_stage:
            return True  # 允许相同状态
        
        valid_targets = self.VALID_TRANSITIONS.get(from_stage, [])
        return to_stage in valid_targets
    
    def _get_stage_display_name(self, stage: ConversationStage) -> str:
        """获取阶段显示名称"""
        display_names = {
            ConversationStage.INQUIRY: "初始问诊",
            ConversationStage.DETAILED_INQUIRY: "详细问诊",
            ConversationStage.INTERIM_ADVICE: "临时建议",
            ConversationStage.DIAGNOSIS: "证候分析",
            ConversationStage.PRESCRIPTION: "处方建议",
            ConversationStage.PRESCRIPTION_CONFIRM: "处方确认",
            ConversationStage.COMPLETED: "问诊完成",
            ConversationStage.TIMEOUT: "会话超时",
            ConversationStage.EMERGENCY: "紧急转诊"
        }
        return display_names.get(stage, stage.value)
    
    def cleanup_expired_conversations(self, days_old: int = 30) -> int:
        """清理过期对话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            cursor.execute("""
                UPDATE conversation_states 
                SET is_active = 0, end_type = 'cleanup'
                WHERE last_activity < ? AND is_active = 1
            """, (cutoff_date.isoformat(),))
            
            cleaned_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"清理过期对话: {cleaned_count} 个")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理过期对话失败: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

# 全局状态管理器实例
conversation_state_manager = ConversationStateManager()