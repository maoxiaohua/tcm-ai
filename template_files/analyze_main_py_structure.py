#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py文件结构分析工具
分析代码结构、重复函数、模块化重构机会
"""

import ast
import re
import sys
from typing import Dict, List, Tuple, Set
from collections import defaultdict, Counter

class MainPyAnalyzer:
    """main.py文件分析器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.content = ""
        self.lines = []
        self.functions = {}
        self.classes = {}
        self.imports = []
        self.duplicates = []
        self.code_blocks = {}
        
    def load_file(self):
        """加载文件内容"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            self.content = f.read()
            self.lines = self.content.split('\n')
        print(f"📄 文件加载完成: {len(self.lines)}行代码")
    
    def analyze_structure(self):
        """分析文件结构"""
        print("\n🔍 分析文件结构")
        print("=" * 50)
        
        # 统计基本信息
        total_lines = len(self.lines)
        empty_lines = sum(1 for line in self.lines if not line.strip())
        comment_lines = sum(1 for line in self.lines if line.strip().startswith('#'))
        code_lines = total_lines - empty_lines - comment_lines
        
        print(f"📊 基本统计:")
        print(f"   总行数: {total_lines}")
        print(f"   代码行: {code_lines}")
        print(f"   注释行: {comment_lines}")
        print(f"   空行: {empty_lines}")
        print(f"   代码密度: {code_lines/total_lines:.1%}")
        
        # 分析AST
        try:
            tree = ast.parse(self.content)
            self._analyze_ast(tree)
        except SyntaxError as e:
            print(f"❌ AST解析失败: {e}")
    
    def _analyze_ast(self, tree):
        """分析AST结构"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = {
                    'name': node.name,
                    'line': node.lineno,
                    'lines': node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 'unknown',
                    'args': len(node.args.args),
                    'docstring': ast.get_docstring(node),
                    'is_async': False
                }
                self.functions[node.name] = func_info
                
            elif isinstance(node, ast.AsyncFunctionDef):
                func_info = {
                    'name': node.name,
                    'line': node.lineno,
                    'lines': node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 'unknown',
                    'args': len(node.args.args),
                    'docstring': ast.get_docstring(node),
                    'is_async': True
                }
                self.functions[node.name] = func_info
                
            elif isinstance(node, ast.ClassDef):
                class_info = {
                    'name': node.name,
                    'line': node.lineno,
                    'lines': node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 'unknown',
                    'methods': [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                }
                self.classes[node.name] = class_info
                
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports.append(('import', alias.name, node.lineno))
                    
            elif isinstance(node, ast.ImportFrom):
                module = node.module if node.module else ''
                for alias in node.names:
                    self.imports.append(('from', f"{module}.{alias.name}", node.lineno))
    
    def analyze_functions(self):
        """分析函数详情"""
        print(f"\n🔧 函数分析 (共{len(self.functions)}个函数)")
        print("=" * 50)
        
        # 按行数排序
        sorted_functions = sorted(self.functions.items(), key=lambda x: x[1].get('lines', 0), reverse=True)
        
        print("📋 最大的函数 (Top 10):")
        for i, (name, info) in enumerate(sorted_functions[:10], 1):
            lines = info.get('lines', 'unknown')
            line_no = info['line']
            is_async = " (async)" if info['is_async'] else ""
            print(f"   {i:2d}. {name}{is_async}: {lines}行 (第{line_no}行)")
        
        # 统计函数类型
        sync_funcs = sum(1 for f in self.functions.values() if not f['is_async'])
        async_funcs = sum(1 for f in self.functions.values() if f['is_async'])
        
        print(f"\n📊 函数类型分布:")
        print(f"   同步函数: {sync_funcs}")
        print(f"   异步函数: {async_funcs}")
        
        # 分析函数职责
        self._analyze_function_responsibilities()
    
    def _analyze_function_responsibilities(self):
        """分析函数职责"""
        print(f"\n🎯 函数职责分析:")
        
        categories = {
            'API端点': [],
            '数据处理': [],
            '工具函数': [],
            '安全检查': [],
            '图像处理': [],
            '数据库操作': [],
            'AI调用': [],
            '其他': []
        }
        
        for name, info in self.functions.items():
            if name.startswith('get_') or name.startswith('post_') or 'endpoint' in name.lower():
                categories['API端点'].append(name)
            elif 'extract' in name or 'parse' in name or 'process' in name:
                categories['数据处理'].append(name)
            elif 'check' in name or 'validate' in name or 'sanitize' in name or 'safety' in name:
                categories['安全检查'].append(name)
            elif 'image' in name or 'picture' in name or 'multimodal' in name:
                categories['图像处理'].append(name)
            elif 'database' in name or 'db_' in name or 'search' in name:
                categories['数据库操作'].append(name)
            elif 'llm' in name or 'ai_' in name or 'model' in name:
                categories['AI调用'].append(name)
            elif len(name) < 15 and not name.startswith('_'):
                categories['工具函数'].append(name)
            else:
                categories['其他'].append(name)
        
        for category, functions in categories.items():
            if functions:
                print(f"   {category}: {len(functions)}个")
                for func in functions[:3]:  # 只显示前3个
                    print(f"      • {func}")
                if len(functions) > 3:
                    print(f"      ... 还有{len(functions)-3}个")
    
    def find_duplicate_code(self):
        """查找重复代码"""
        print(f"\n🔄 重复代码分析")
        print("=" * 50)
        
        # 查找重复的函数名模式
        self._find_similar_function_names()
        
        # 查找重复的代码块
        self._find_duplicate_blocks()
        
        # 查找重复的导入
        self._find_duplicate_imports()
    
    def _find_similar_function_names(self):
        """查找相似的函数名"""
        print("🔍 相似函数名分析:")
        
        # 按功能分组
        groups = defaultdict(list)
        for name in self.functions.keys():
            if 'extract' in name:
                groups['extract'].append(name)
            elif 'check' in name or 'validate' in name:
                groups['validation'].append(name)
            elif 'sanitize' in name or 'clean' in name:
                groups['sanitization'].append(name)
            elif 'get_' in name:
                groups['getters'].append(name)
            elif 'process' in name:
                groups['processing'].append(name)
        
        for group_name, functions in groups.items():
            if len(functions) > 1:
                print(f"   {group_name.upper()}类函数: {len(functions)}个")
                for func in functions:
                    print(f"      • {func}")
    
    def _find_duplicate_blocks(self):
        """查找重复代码块"""
        print(f"\n🔄 代码块重复分析:")
        
        # 简单的重复模式检测
        patterns = {
            'try-except-logger': 0,
            'if-not-available': 0,
            'response-status-check': 0,
            'temp-file-creation': 0,
            'ai-response-validation': 0
        }
        
        content_lower = self.content.lower()
        
        patterns['try-except-logger'] = content_lower.count('try:') + content_lower.count('except') + content_lower.count('logger.')
        patterns['temp-file-creation'] = content_lower.count('tempfile') + content_lower.count('tmp_file')
        patterns['response-status-check'] = content_lower.count('status_code') + content_lower.count('response.')
        patterns['ai-response-validation'] = content_lower.count('ai_response') + content_lower.count('validate')
        
        print("   常见代码模式出现频率:")
        for pattern, count in patterns.items():
            if count > 5:  # 只显示频繁出现的模式
                print(f"      {pattern}: {count}次")
    
    def _find_duplicate_imports(self):
        """查找重复导入"""
        print(f"\n📦 导入分析 (共{len(self.imports)}个导入):")
        
        # 统计导入类型
        import_types = Counter()
        modules = Counter()
        
        for import_type, module, line in self.imports:
            import_types[import_type] += 1
            base_module = module.split('.')[0]
            modules[base_module] += 1
        
        print("   导入类型分布:")
        for import_type, count in import_types.most_common():
            print(f"      {import_type}: {count}次")
        
        print("   主要模块:")
        for module, count in modules.most_common(10):
            print(f"      {module}: {count}次")
    
    def suggest_refactoring(self):
        """生成重构建议"""
        print(f"\n💡 重构建议")
        print("=" * 50)
        
        suggestions = []
        
        # 基于文件大小的建议
        if len(self.lines) > 3000:
            suggestions.append("🔥 文件过大 (>3000行)，强烈建议拆分")
        elif len(self.lines) > 1500:
            suggestions.append("⚠️ 文件较大 (>1500行)，建议考虑拆分")
        
        # 基于函数数量的建议
        if len(self.functions) > 50:
            suggestions.append("🔧 函数过多，建议按功能分组到不同模块")
        
        # 基于大函数的建议
        large_functions = [name for name, info in self.functions.items() 
                          if isinstance(info.get('lines'), int) and info['lines'] > 100]
        if large_functions:
            suggestions.append(f"📏 发现{len(large_functions)}个大函数 (>100行)，建议拆分")
        
        # 基于职责的建议
        api_funcs = [name for name in self.functions.keys() if 'get_' in name or 'post_' in name]
        if len(api_funcs) > 10:
            suggestions.append("🌐 API端点过多，建议使用路由分离")
        
        # 生成具体的重构计划
        refactor_plan = self._generate_refactor_plan()
        
        print("📋 重构优先级:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"   {i}. {suggestion}")
        
        if refactor_plan:
            print(f"\n🗺️ 建议的模块拆分方案:")
            for module_name, functions in refactor_plan.items():
                print(f"   📦 {module_name}: {len(functions)}个函数")
                for func in functions[:3]:
                    print(f"      • {func}")
                if len(functions) > 3:
                    print(f"      ... 还有{len(functions)-3}个")
    
    def _generate_refactor_plan(self):
        """生成重构计划"""
        plan = {
            'api_routes.py': [],
            'data_processors.py': [],
            'security_validators.py': [],
            'multimodal_handlers.py': [],
            'database_operations.py': [],
            'ai_integrations.py': [],
            'utils.py': []
        }
        
        for name, info in self.functions.items():
            if any(keyword in name.lower() for keyword in ['get_', 'post_', 'endpoint']):
                plan['api_routes.py'].append(name)
            elif any(keyword in name.lower() for keyword in ['extract', 'parse', 'process']):
                plan['data_processors.py'].append(name)
            elif any(keyword in name.lower() for keyword in ['check', 'validate', 'sanitize', 'safety']):
                plan['security_validators.py'].append(name)
            elif any(keyword in name.lower() for keyword in ['image', 'multimodal', 'picture']):
                plan['multimodal_handlers.py'].append(name)
            elif any(keyword in name.lower() for keyword in ['search', 'database', 'db_']):
                plan['database_operations.py'].append(name)
            elif any(keyword in name.lower() for keyword in ['llm', 'ai_', 'model']):
                plan['ai_integrations.py'].append(name)
            else:
                plan['utils.py'].append(name)
        
        # 移除空模块
        return {k: v for k, v in plan.items() if v}
    
    def generate_report(self):
        """生成分析报告"""
        report = {
            'file_info': {
                'path': self.file_path,
                'total_lines': len(self.lines),
                'functions_count': len(self.functions),
                'classes_count': len(self.classes),
                'imports_count': len(self.imports)
            },
            'functions': dict(self.functions),
            'classes': dict(self.classes),
            'refactor_suggestions': self._generate_refactor_plan(),
            'analysis_timestamp': '2025-08-19T15:50:00'
        }
        
        # 保存报告
        import json
        with open('/opt/tcm-ai/template_files/main_py_analysis_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细报告已保存至: /opt/tcm-ai/template_files/main_py_analysis_report.json")
        return report
    
    def run_analysis(self):
        """运行完整分析"""
        print("🚀 开始main.py文件结构分析")
        print("=" * 80)
        
        self.load_file()
        self.analyze_structure() 
        self.analyze_functions()
        self.find_duplicate_code()
        self.suggest_refactoring()
        
        return self.generate_report()

def main():
    analyzer = MainPyAnalyzer('/opt/tcm-ai/api/main.py')
    report = analyzer.run_analysis()
    
    print(f"\n🎯 分析总结:")
    print(f"   文件大小: {report['file_info']['total_lines']}行")
    print(f"   函数数量: {report['file_info']['functions_count']}个")
    print(f"   建议拆分: {len(report['refactor_suggestions'])}个模块")
    print(f"\n✅ 分析完成，可以开始重构规划")

if __name__ == "__main__":
    main()