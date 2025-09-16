#!/usr/bin/env python3
"""
TCM-AI 模板化AI回复系统
从源头控制AI回复格式，确保质量一致性和医疗安全
"""

from .template_engine import (
    ResponseStage,
    TemplateContext, 
    TCMResponseTemplateEngine,
    get_template_engine
)

from .template_prompt_generator_simple import (
    SimpleTemplateContext,
    SimpleTemplatePromptGenerator,
    get_simple_prompt_generator
)

__all__ = [
    'ResponseStage',
    'TemplateContext',
    'TCMResponseTemplateEngine', 
    'get_template_engine',
    'PromptType',
    'TemplatePromptContext',
    'TemplatePromptGenerator',
    'get_prompt_generator'
]