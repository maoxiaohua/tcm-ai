#!/usr/bin/env python3
"""
对话状态管理模块
提供对话状态管理、分析和流程控制功能
"""

from .conversation_state_manager import (
    ConversationStateManager,
    ConversationState,
    ConversationStage,
    ConversationEndType,
    conversation_state_manager
)

from .conversation_analyzer import (
    ConversationAnalyzer,
    AnalysisResult
)

__all__ = [
    'ConversationStateManager',
    'ConversationState', 
    'ConversationStage',
    'ConversationEndType',
    'conversation_state_manager',
    'ConversationAnalyzer',
    'AnalysisResult'
]