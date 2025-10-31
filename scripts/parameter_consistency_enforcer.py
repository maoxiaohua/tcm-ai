#!/usr/bin/env python3
"""
参数一致性强制检查器
专门检查和修复ID不匹配、参数名称不一致的问题
这是对 consistency_checker.py 的增强版本，更加严格和主动
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent

# 颜色定义
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    BOLD = '\033[1m'
    NC = '\033[0m'


class ParameterConsistencyEnforcer:
    """参数一致性强制检查器"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.suggestions = []

        # 标准参数映射表（权威版本）
        self.STANDARD_PARAMS = {
            # 用户/患者ID
            'user_id': {
                'standard': 'user_id',
                'aliases': ['userId', 'patient_id', 'patientId', 'uid'],
                'description': '用户/患者唯一标识',
                'type': 'string',
                'example': 'user_12345'
            },
            # 医生ID
            'doctor_id': {
                'standard': 'doctor_id',
                'aliases': ['doctorId', 'selected_doctor', 'doctor_name', 'doctor_code'],
                'description': '医生唯一标识',
                'type': 'string',
                'example': 'zhang_zhongjing',
                'format': 'pinyin_name (不是数字！)'
            },
            # 会话/对话ID
            'conversation_id': {
                'standard': 'conversation_id',
                'aliases': ['conversationId', 'session_id', 'sessionId', 'chat_id'],
                'description': '对话会话唯一标识',
                'type': 'string',
                'example': 'conv_12345'
            },
            # 处方ID
            'prescription_id': {
                'standard': 'prescription_id',
                'aliases': ['prescriptionId', 'rx_id', 'formula_id'],
                'description': '处方唯一标识',
                'type': 'string',
                'example': 'prescription_12345'
            },
            # 消息内容
            'message': {
                'standard': 'message',
                'aliases': ['content', 'msg', 'text', 'body'],
                'description': '消息内容',
                'type': 'string',
                'example': '我头痛三天了'
            }
        }

        # 常见错误模式
        self.ERROR_PATTERNS = {
            'doctor_id_as_number': {
                'pattern': r'(?:doctor_id|selected_doctor|doctorId)\s*[:=]\s*["\']?\d+["\']?',
                'message': '医生ID使用了数字格式，应该使用名称格式（如 zhang_zhongjing）',
                'severity': 'error',
                'fix_example': 'doctor_id: "zhang_zhongjing"  // 不是 "1"'
            },
            'mixed_id_format': {
                'pattern': r'(user_id|userId|patient_id|patientId)',
                'message': 'ID参数命名不统一，建议统一使用 user_id',
                'severity': 'warning',
                'fix_example': 'user_id: currentUser.id  // 统一使用 user_id'
            },
            'response_data_inconsistent': {
                'pattern': r'(?<!result\.)(?<!data\.)reply\b',
                'message': '直接访问 .reply 可能失败，应该检查嵌套结构',
                'severity': 'warning',
                'fix_example': 'const reply = result.data?.reply || result.reply || "默认值"'
            }
        }

    def print_header(self, text: str):
        """打印标题"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 80}{Colors.NC}")
        print(f"{Colors.CYAN}{Colors.BOLD}{text}{Colors.NC}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 80}{Colors.NC}\n")

    def print_section(self, text: str):
        """打印小节"""
        print(f"\n{Colors.BLUE}{Colors.BOLD}▶ {text}{Colors.NC}")
        print(f"{Colors.BLUE}{'─' * 70}{Colors.NC}")

    # ===== 1. 扫描前端文件中的参数使用 =====
    def scan_frontend_parameters(self) -> Dict:
        """扫描前端代码中的参数使用情况"""
        self.print_section("扫描前端参数使用")

        param_usage = defaultdict(lambda: defaultdict(list))

        static_dir = PROJECT_ROOT / "static"
        files = list(static_dir.glob("**/*.html")) + list(static_dir.glob("**/*.js"))

        for file_path in files:
            try:
                content = file_path.read_text(encoding='utf-8')
                relative_path = str(file_path.relative_to(static_dir))

                # 检查每个标准参数的使用
                for standard, config in self.STANDARD_PARAMS.items():
                    all_variants = [standard] + config['aliases']

                    for variant in all_variants:
                        # 匹配模式：参数名: 值 或 参数名 = 值
                        patterns = [
                            rf'\b{variant}\s*[:=]\s*([^,\}}]+)',
                            rf'["\']?{variant}["\']?\s*:\s*([^,\}}]+)',
                            rf'\.{variant}\b'
                        ]

                        for pattern in patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            if matches:
                                param_usage[standard][variant].append({
                                    'file': relative_path,
                                    'matches': len(matches)
                                })

            except Exception as e:
                # 忽略读取错误
                pass

        print(f"✓ 扫描了 {len(files)} 个前端文件")
        return dict(param_usage)

    # ===== 2. 检查参数命名不一致 =====
    def check_parameter_naming(self, param_usage: Dict):
        """检查参数命名一致性"""
        self.print_section("检查参数命名一致性")

        inconsistencies = 0

        for standard, variants_usage in param_usage.items():
            if len(variants_usage) > 1:  # 使用了多种变体
                inconsistencies += 1

                # 统计每种变体的使用次数
                variant_counts = {}
                files_by_variant = {}

                for variant, files in variants_usage.items():
                    total_matches = sum(f['matches'] for f in files)
                    variant_counts[variant] = total_matches
                    files_by_variant[variant] = [f['file'] for f in files]

                # 找出最常用的变体
                most_used = max(variant_counts, key=variant_counts.get)

                # 生成错误报告
                config = self.STANDARD_PARAMS[standard]

                error_msg = f"参数 '{standard}' 使用了 {len(variants_usage)} 种不同的命名"
                details = f"标准名称: {config['standard']}\n"
                details += f"描述: {config['description']}\n"
                details += f"当前使用情况:\n"

                for variant, count in sorted(variant_counts.items(), key=lambda x: x[1], reverse=True):
                    is_standard = "✓ 标准" if variant == config['standard'] else "✗ 别名"
                    details += f"  - {variant}: {count} 次使用 {is_standard}\n"
                    details += f"    文件: {', '.join(files_by_variant[variant][:3])}\n"

                details += f"\n建议: 统一使用 '{config['standard']}'"

                self.errors.append({
                    'category': '参数命名不一致',
                    'message': error_msg,
                    'details': details,
                    'standard': config['standard'],
                    'variants': list(variants_usage.keys()),
                    'fix_suggestion': self._generate_fix_suggestion(standard, config)
                })

        if inconsistencies == 0:
            print(f"{Colors.GREEN}✓ 所有参数命名一致{Colors.NC}")
        else:
            print(f"{Colors.RED}✗ 发现 {inconsistencies} 个参数命名不一致{Colors.NC}")

    def _generate_fix_suggestion(self, standard: str, config: Dict) -> str:
        """生成修复建议"""
        suggestion = f"# 修复建议：统一使用 {config['standard']}\n\n"
        suggestion += "# 前端代码示例:\n"
        suggestion += f"// ❌ 错误用法\n"

        for alias in config['aliases'][:2]:
            suggestion += f"{{  {alias}: value  }}  // 使用了别名\n"

        suggestion += f"\n// ✅ 正确用法\n"
        suggestion += f"{{  {config['standard']}: value  }}  // 使用标准名称\n"

        if 'format' in config:
            suggestion += f"\n// 注意: {config['format']}\n"
            suggestion += f"// 示例: {config['example']}\n"

        return suggestion

    # ===== 3. 检查医生ID格式错误 =====
    def check_doctor_id_format(self):
        """专门检查医生ID是否使用了错误的数字格式"""
        self.print_section("检查医生ID格式")

        static_dir = PROJECT_ROOT / "static"
        files = list(static_dir.glob("**/*.html")) + list(static_dir.glob("**/*.js"))

        errors_found = 0

        for file_path in files:
            try:
                content = file_path.read_text(encoding='utf-8')
                relative_path = str(file_path.relative_to(static_dir))

                # 检查医生ID是否使用数字
                patterns = [
                    (r'(?:doctor_id|selected_doctor|doctorId)\s*[:=]\s*["\']?\d+["\']?', '赋值语句'),
                    (r'doctorIdMapping\s*=\s*\{[^}]*["\']?\d+["\']?\s*:', '映射表定义'),
                ]

                for pattern, context in patterns:
                    matches = list(re.finditer(pattern, content))
                    if matches:
                        errors_found += len(matches)

                        # 提取代码片段
                        for match in matches:
                            start = max(0, match.start() - 50)
                            end = min(len(content), match.end() + 50)
                            snippet = content[start:end].replace('\n', ' ')

                            self.errors.append({
                                'category': '医生ID格式错误',
                                'message': f'文件 {relative_path} 使用了数字格式的医生ID',
                                'details': f"上下文: ...{snippet}...\n"
                                          f"\n正确格式: doctor_id: 'zhang_zhongjing'  // 使用拼音名称\n"
                                          f"错误格式: doctor_id: '1'  // 不要使用数字！\n"
                                          f"\n可用医生ID:\n"
                                          f"  - zhang_zhongjing (张仲景)\n"
                                          f"  - ye_tianshi (叶天士)\n"
                                          f"  - li_dongyuan (李东垣)\n"
                                          f"  - zheng_qinan (郑钦安)\n"
                                          f"  - liu_duzhou (刘渡舟)",
                                'severity': 'high',
                                'fix_suggestion': self._generate_doctor_id_fix(relative_path)
                            })

            except Exception as e:
                pass

        if errors_found == 0:
            print(f"{Colors.GREEN}✓ 所有医生ID格式正确{Colors.NC}")
        else:
            print(f"{Colors.RED}✗ 发现 {errors_found} 个医生ID格式错误{Colors.NC}")

    def _generate_doctor_id_fix(self, file_path: str) -> str:
        """生成医生ID修复建议"""
        fix = f"# 修复文件: {file_path}\n\n"
        fix += "# 步骤1: 定义医生ID映射表（如果还没有）\n"
        fix += """
const DOCTOR_ID_MAP = {
  '1': 'zhang_zhongjing',
  '2': 'ye_tianshi',
  '3': 'li_dongyuan',
  '4': 'zheng_qinan',
  '5': 'liu_duzhou'
};

# 步骤2: 在发送API请求前转换
const requestData = {
  message: userMessage,
  user_id: currentUser.id,
  conversation_id: conversationId,
  doctor_id: DOCTOR_ID_MAP[selectedDoctorId] || 'zhang_zhongjing'  // 转换为名称
};

# 步骤3: 后端API统一使用名称格式
# 后端不应该接受数字格式的医生ID
"""
        return fix

    # ===== 4. 检查响应数据访问一致性 =====
    def check_response_data_access(self):
        """检查前端访问响应数据的方式是否一致"""
        self.print_section("检查响应数据访问")

        static_dir = PROJECT_ROOT / "static"
        files = list(static_dir.glob("**/*.html")) + list(static_dir.glob("**/*.js"))

        access_patterns = defaultdict(list)

        for file_path in files:
            try:
                content = file_path.read_text(encoding='utf-8')
                relative_path = str(file_path.relative_to(static_dir))

                # 检测不同的访问模式
                patterns = {
                    'direct': r'\.reply\b(?!\s*\|\|)',  # 直接访问 .reply
                    'safe_data': r'\.data\.reply',  # 安全访问 .data.reply
                    'safe_result': r'result\.data\.reply',  # 更安全 result.data.reply
                    'optional_chaining': r'\?\.reply',  # 可选链 ?.reply
                }

                for pattern_name, pattern in patterns.items():
                    matches = re.findall(pattern, content)
                    if matches:
                        access_patterns[pattern_name].append({
                            'file': relative_path,
                            'count': len(matches)
                        })

            except Exception:
                pass

        # 分析访问模式
        if 'direct' in access_patterns and len(access_patterns['direct']) > 0:
            files_list = [f['file'] for f in access_patterns['direct'][:5]]

            self.warnings.append({
                'category': '响应数据访问不安全',
                'message': f'发现 {len(access_patterns["direct"])} 个文件直接访问 .reply',
                'details': f"文件: {', '.join(files_list)}\n\n"
                          f"问题: 直接访问可能因为响应格式不同而失败\n\n"
                          f"推荐方案:\n"
                          f"  ✅ 使用可选链: result?.data?.reply\n"
                          f"  ✅ 使用兼容判断: result.data?.reply || result.reply\n"
                          f"  ✅ 统一响应格式处理函数",
                'fix_suggestion': self._generate_response_access_fix()
            })

        print(f"✓ 检查了 {len(files)} 个文件的响应访问模式")

    def _generate_response_access_fix(self) -> str:
        """生成响应访问修复建议"""
        return """
# 推荐方案: 创建统一的响应处理函数

// 定义统一的响应处理器
function extractReply(response) {
  // 处理新API格式 (统一问诊服务)
  if (response.success && response.data) {
    return response.data.reply || response.data.message;
  }

  // 处理旧API格式
  if (response.reply) {
    return response.reply;
  }

  // 处理直接返回
  if (typeof response === 'string') {
    return response;
  }

  // 默认值
  return '系统暂时无法响应，请稍后重试';
}

// 使用示例
const response = await fetch('/api/consultation/chat', {...});
const result = await response.json();
const reply = extractReply(result);  // 统一提取
addMessage('ai', reply);
"""

    # ===== 5. 生成修复脚本 =====
    def generate_fix_script(self):
        """生成自动修复脚本"""
        self.print_section("生成修复建议")

        if not self.errors and not self.warnings:
            print(f"{Colors.GREEN}✓ 没有发现需要修复的问题{Colors.NC}")
            return

        # 生成修复脚本文件
        fix_script_path = PROJECT_ROOT / "template_files" / "parameter_fix_suggestions.md"

        fix_content = "# 参数一致性修复建议\n\n"
        fix_content += f"**生成时间**: {self._get_timestamp()}\n\n"
        fix_content += "---\n\n"

        # 错误修复
        if self.errors:
            fix_content += f"## 🔴 错误修复 (共 {len(self.errors)} 个)\n\n"

            for i, error in enumerate(self.errors, 1):
                fix_content += f"### 错误 {i}: {error['message']}\n\n"
                fix_content += f"**类别**: {error['category']}\n\n"
                fix_content += f"**详情**:\n```\n{error['details']}\n```\n\n"

                if 'fix_suggestion' in error:
                    fix_content += f"**修复建议**:\n```javascript\n{error['fix_suggestion']}\n```\n\n"

                fix_content += "---\n\n"

        # 警告修复
        if self.warnings:
            fix_content += f"## 🟡 警告修复 (共 {len(self.warnings)} 个)\n\n"

            for i, warning in enumerate(self.warnings, 1):
                fix_content += f"### 警告 {i}: {warning['message']}\n\n"
                fix_content += f"**类别**: {warning['category']}\n\n"
                fix_content += f"**详情**:\n```\n{warning['details']}\n```\n\n"

                if 'fix_suggestion' in warning:
                    fix_content += f"**修复建议**:\n```javascript\n{warning['fix_suggestion']}\n```\n\n"

                fix_content += "---\n\n"

        # 通用修复指南
        fix_content += self._generate_general_fix_guide()

        fix_script_path.write_text(fix_content, encoding='utf-8')

        print(f"{Colors.GREEN}✓ 修复建议已保存: {fix_script_path}{Colors.NC}")

    def _generate_general_fix_guide(self) -> str:
        """生成通用修复指南"""
        guide = "## 📚 通用修复指南\n\n"
        guide += "### 参数命名标准\n\n"
        guide += "| 标准名称 | 类型 | 格式 | 示例 |\n"
        guide += "|---------|------|------|------|\n"

        for standard, config in self.STANDARD_PARAMS.items():
            format_info = config.get('format', config['type'])
            guide += f"| `{config['standard']}` | {config['type']} | {format_info} | `{config['example']}` |\n"

        guide += "\n### 常见错误及修复\n\n"
        guide += "#### 1. 医生ID格式错误\n\n"
        guide += "```javascript\n"
        guide += "// ❌ 错误\n"
        guide += "{ doctor_id: '1' }  // 数字格式\n\n"
        guide += "// ✅ 正确\n"
        guide += "{ doctor_id: 'zhang_zhongjing' }  // 名称格式\n"
        guide += "```\n\n"

        guide += "#### 2. 参数名称不统一\n\n"
        guide += "```javascript\n"
        guide += "// ❌ 错误 - 混用多种名称\n"
        guide += "{ patient_id: user.id }  // 某些地方\n"
        guide += "{ userId: user.id }      // 另一些地方\n\n"
        guide += "// ✅ 正确 - 统一使用\n"
        guide += "{ user_id: user.id }     // 所有地方都用 user_id\n"
        guide += "```\n\n"

        guide += "#### 3. 响应数据访问不安全\n\n"
        guide += "```javascript\n"
        guide += "// ❌ 错误\n"
        guide += "const reply = data.reply;  // 可能不存在\n\n"
        guide += "// ✅ 正确\n"
        guide += "const reply = data?.reply || result?.data?.reply || '默认值';\n"
        guide += "```\n\n"

        return guide

    def _get_timestamp(self):
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ===== 主运行流程 =====
    def run(self):
        """运行所有检查"""
        self.print_header("🔍 参数一致性强制检查")

        # 1. 扫描参数使用
        param_usage = self.scan_frontend_parameters()

        # 2. 检查参数命名
        self.check_parameter_naming(param_usage)

        # 3. 检查医生ID格式
        self.check_doctor_id_format()

        # 4. 检查响应访问
        self.check_response_data_access()

        # 5. 生成修复建议
        self.generate_fix_script()

        # 6. 生成报告
        return self.generate_report()

    def generate_report(self):
        """生成检查报告"""
        self.print_header("📊 检查报告")

        print(f"\n{Colors.CYAN}问题汇总:{Colors.NC}")
        print(f"  {Colors.RED}错误: {len(self.errors)} 个{Colors.NC}")
        print(f"  {Colors.YELLOW}警告: {len(self.warnings)} 个{Colors.NC}")

        # 显示错误
        if self.errors:
            print(f"\n{Colors.RED}{'=' * 80}{Colors.NC}")
            print(f"{Colors.RED}错误详情:{Colors.NC}")
            print(f"{Colors.RED}{'=' * 80}{Colors.NC}")

            for i, error in enumerate(self.errors, 1):
                print(f"\n{Colors.RED}[{i}] {error['message']}{Colors.NC}")
                if 'details' in error:
                    print(f"{error['details'][:500]}...")

        # 显示警告
        if self.warnings:
            print(f"\n{Colors.YELLOW}{'=' * 80}{Colors.NC}")
            print(f"{Colors.YELLOW}警告详情:{Colors.NC}")
            print(f"{Colors.YELLOW}{'=' * 80}{Colors.NC}")

            for i, warning in enumerate(self.warnings, 1):
                print(f"\n{Colors.YELLOW}[{i}] {warning['message']}{Colors.NC}")

        print(f"\n{Colors.GREEN}✓ 详细修复建议已保存: template_files/parameter_fix_suggestions.md{Colors.NC}")

        # 返回状态码
        return 1 if self.errors else 0


def main():
    enforcer = ParameterConsistencyEnforcer()
    exit_code = enforcer.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
