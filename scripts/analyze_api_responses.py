#!/usr/bin/env python3
"""
API响应格式分析工具
分析现有API的响应格式不一致问题
"""

import os
import re
from typing import Dict, List, Set
import json

def analyze_api_responses():
    """分析API响应格式"""
    print("🔍 分析API响应格式")
    print("=" * 50)
    
    api_patterns = {
        'success_true': re.compile(r'"success":\s*True'),
        'success_false': re.compile(r'"success":\s*False'),
        'success_literal': re.compile(r'["\'"]success["\'"]:\s*(True|False)'),
        'http_exception': re.compile(r'HTTPException\s*\('),
        'json_response': re.compile(r'JSONResponse\s*\('),
        'return_dict': re.compile(r'return\s*\{[^}]*"success"'),
        'error_detail': re.compile(r'"detail":\s*'),
        'error_message': re.compile(r'"message":\s*'),
        'data_field': re.compile(r'"data":\s*'),
    }
    
    response_formats = {
        'success_message_format': 0,  # {"success": bool, "message": str}
        'success_data_format': 0,     # {"success": bool, "data": any}
        'success_detail_format': 0,   # {"success": bool, "detail": str}
        'http_exception_format': 0,   # HTTPException
        'mixed_format': 0,           # {"success": bool, "message": str, "data": any}
    }
    
    files_analyzed = 0
    inconsistencies = []
    
    # 扫描API文件
    api_dirs = ['/opt/tcm-ai/api/routes/', '/opt/tcm-ai/api/']
    
    for api_dir in api_dirs:
        if not os.path.exists(api_dir):
            continue
            
        for filename in os.listdir(api_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                file_path = os.path.join(api_dir, filename)
                analyze_file(file_path, api_patterns, response_formats, inconsistencies)
                files_analyzed += 1
    
    # 报告结果
    print(f"\n📊 分析结果 (扫描 {files_analyzed} 个文件)")
    print("-" * 40)
    
    print("📋 响应格式分布:")
    for format_type, count in response_formats.items():
        if count > 0:
            print(f"  - {format_type}: {count} 处")
    
    print(f"\n❌ 发现 {len(inconsistencies)} 处格式不一致:")
    
    format_groups = {}
    for file_path, line_no, pattern, content in inconsistencies:
        key = os.path.basename(file_path)
        if key not in format_groups:
            format_groups[key] = []
        format_groups[key].append((line_no, pattern, content[:80] + "..."))
    
    for filename, issues in format_groups.items():
        print(f"\n  📁 {filename}:")
        for line_no, pattern, content in issues[:3]:  # 限制显示前3个
            print(f"    L{line_no}: {pattern} - {content}")
        if len(issues) > 3:
            print(f"    ... 还有 {len(issues)-3} 个问题")
    
    return response_formats, inconsistencies

def analyze_file(file_path: str, patterns: Dict, formats: Dict, inconsistencies: List):
    """分析单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line_no, line in enumerate(lines, 1):
            line = line.strip()
            
            # 检查各种格式模式
            if patterns['success_literal'].search(line):
                if patterns['error_message'].search(line):
                    if patterns['data_field'].search(line):
                        formats['mixed_format'] += 1
                    else:
                        formats['success_message_format'] += 1
                elif patterns['data_field'].search(line):
                    formats['success_data_format'] += 1
                elif patterns['error_detail'].search(line):
                    formats['success_detail_format'] += 1
            
            elif patterns['http_exception'].search(line):
                formats['http_exception_format'] += 1
                inconsistencies.append((file_path, line_no, "HTTPException", line))
            
            # 检查不一致的模式
            if '"detail":' in line and '"success":' in line:
                inconsistencies.append((file_path, line_no, "success+detail", line))
            
            if 'HTTPException' in line and 'detail=' in line:
                inconsistencies.append((file_path, line_no, "HTTPException+detail", line))
                
    except Exception as e:
        print(f"❌ 读取文件失败 {file_path}: {e}")

def propose_standard_format():
    """提出标准格式建议"""
    print("\n🎯 推荐的统一API响应标准")
    print("-" * 40)
    
    standard = {
        "success_response": {
            "success": True,
            "data": "any",
            "message": "操作成功信息 (可选)",
            "timestamp": "2025-09-12T14:30:00Z (可选)"
        },
        "error_response": {
            "success": False,
            "error": {
                "code": "ERROR_CODE",
                "message": "用户友好的错误信息",
                "details": "详细错误信息 (可选)"
            },
            "timestamp": "2025-09-12T14:30:00Z (可选)"
        }
    }
    
    print("✅ 成功响应格式:")
    print(json.dumps(standard["success_response"], indent=2, ensure_ascii=False))
    
    print("\n❌ 错误响应格式:")
    print(json.dumps(standard["error_response"], indent=2, ensure_ascii=False))
    
    print(f"\n💡 统一原则:")
    print("  1. 所有响应都包含 success 字段")
    print("  2. 成功响应使用 data 字段承载数据")
    print("  3. 错误响应使用 error 对象包含错误信息")
    print("  4. 避免使用 HTTPException，使用统一错误格式")
    print("  5. 可选添加 timestamp 用于调试")

def generate_response_helper():
    """生成响应辅助函数"""
    print(f"\n🛠️ 生成统一响应辅助函数")
    print("-" * 40)
    
    helper_code = '''
from typing import Any, Optional
from datetime import datetime
from fastapi.responses import JSONResponse

class APIResponse:
    """统一API响应格式辅助类"""
    
    @staticmethod
    def success(data: Any = None, message: str = "", status_code: int = 200) -> JSONResponse:
        """成功响应"""
        response_data = {
            "success": True,
            "data": data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        if message:
            response_data["message"] = message
            
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
    
    @staticmethod
    def error(code: str, message: str, details: str = "", status_code: int = 400) -> JSONResponse:
        """错误响应"""
        response_data = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        if details:
            response_data["error"]["details"] = details
            
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
    
    @staticmethod
    def not_found(resource: str = "资源") -> JSONResponse:
        """404 响应"""
        return APIResponse.error(
            code="NOT_FOUND",
            message=f"{resource}不存在",
            status_code=404
        )
    
    @staticmethod
    def unauthorized(message: str = "未授权访问") -> JSONResponse:
        """401 响应"""
        return APIResponse.error(
            code="UNAUTHORIZED", 
            message=message,
            status_code=401
        )
    
    @staticmethod
    def forbidden(message: str = "权限不足") -> JSONResponse:
        """403 响应"""
        return APIResponse.error(
            code="FORBIDDEN",
            message=message, 
            status_code=403
        )
'''
    
    return helper_code

def main():
    """主函数"""
    print("🚀 TCM-AI API响应格式标准化分析")
    print("=" * 50)
    
    # 分析现有格式
    formats, inconsistencies = analyze_api_responses()
    
    # 提出标准
    propose_standard_format()
    
    # 生成辅助代码
    helper_code = generate_response_helper()
    
    # 保存辅助代码
    helper_file = "/opt/tcm-ai/api/utils/api_response.py"
    os.makedirs(os.path.dirname(helper_file), exist_ok=True)
    
    with open(helper_file, 'w', encoding='utf-8') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write('"""\nAPI响应格式统一辅助类\n"""\n')
        f.write(helper_code)
    
    print(f"💾 辅助代码已保存到: {helper_file}")
    
    print(f"\n✅ API标准化分析完成!")
    print(f"📋 发现 {sum(formats.values())} 处API响应")
    print(f"⚠️ 需要修复 {len(inconsistencies)} 处不一致")

if __name__ == "__main__":
    main()