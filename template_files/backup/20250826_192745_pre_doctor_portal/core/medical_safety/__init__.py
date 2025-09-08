"""
医疗安全模块 - Medical Safety Module
负责检测和防止AI编造医疗信息
"""

from .safety_validator import check_symptom_fabrication, sanitize_ai_response

__all__ = ['check_symptom_fabrication', 'sanitize_ai_response']