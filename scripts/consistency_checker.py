#!/usr/bin/env python3
"""
TCM-AI 代码一致性检查工具
用于检查API接口、数据库接口、前后端关联关系的一致性
防止"修A坏B"问题的发生
"""

import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 颜色定义
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

class ConsistencyChecker:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

        # 后端API路由
        self.backend_apis = {}
        # 前端API调用
        self.frontend_apis = {}
        # 数据库表和字段
        self.database_schema = {}

    def print_header(self, text: str):
        """打印章节标题"""
        print(f"\n{Colors.CYAN}{'=' * 80}{Colors.NC}")
        print(f"{Colors.CYAN}{text}{Colors.NC}")
        print(f"{Colors.CYAN}{'=' * 80}{Colors.NC}\n")

    def print_section(self, text: str):
        """打印小节标题"""
        print(f"\n{Colors.BLUE}{'▶ ' + text}{Colors.NC}")
        print(f"{Colors.BLUE}{'-' * 60}{Colors.NC}")

    def add_error(self, category: str, message: str, details: str = ""):
        """添加错误"""
        self.errors.append({
            'category': category,
            'message': message,
            'details': details
        })

    def add_warning(self, category: str, message: str, details: str = ""):
        """添加警告"""
        self.warnings.append({
            'category': category,
            'message': message,
            'details': details
        })

    def add_info(self, category: str, message: str):
        """添加信息"""
        self.info.append({
            'category': category,
            'message': message
        })

    # ===== 1. 扫描后端API定义 =====
    def scan_backend_apis(self):
        """扫描后端所有API路由定义"""
        self.print_section("扫描后端API路由")

        routes_dir = PROJECT_ROOT / "api" / "routes"
        if not routes_dir.exists():
            self.add_error("Backend", "API路由目录不存在", str(routes_dir))
            return

        for py_file in routes_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            content = py_file.read_text(encoding='utf-8')

            # 匹配路由装饰器：@router.post("/path")
            pattern = r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']\)'
            matches = re.findall(pattern, content)

            for method, path in matches:
                # 提取完整路径（包含路由前缀）
                prefix_match = re.search(r'router\s*=\s*APIRouter\([^)]*prefix=["\']([^"\']+)["\']', content)
                prefix = prefix_match.group(1) if prefix_match else ""

                full_path = f"{prefix}{path}"

                if full_path not in self.backend_apis:
                    self.backend_apis[full_path] = {
                        'methods': [],
                        'file': py_file.name,
                        'params': self._extract_params(content, path)
                    }

                self.backend_apis[full_path]['methods'].append(method.upper())

        print(f"✓ 发现 {len(self.backend_apis)} 个后端API端点")
        self.add_info("Backend", f"扫描到 {len(self.backend_apis)} 个API端点")

    def _extract_params(self, content: str, path: str) -> List[str]:
        """从函数签名提取参数"""
        params = []

        # 查找路由函数
        pattern = rf'async def.*?\(([^)]+)\):'
        matches = re.findall(pattern, content)

        for match in matches:
            # 提取Pydantic模型参数
            if ':' in match:
                param_parts = match.split(',')
                for part in param_parts:
                    if ':' in part:
                        param_name = part.split(':')[0].strip()
                        if param_name not in ['request', 'db', 'current_user']:
                            params.append(param_name)

        return params

    # ===== 2. 扫描前端API调用 =====
    def scan_frontend_apis(self):
        """扫描前端所有API调用"""
        self.print_section("扫描前端API调用")

        static_dir = PROJECT_ROOT / "static"
        if not static_dir.exists():
            self.add_error("Frontend", "静态文件目录不存在", str(static_dir))
            return

        # 扫描HTML和JS文件
        files_to_scan = list(static_dir.glob("**/*.html")) + list(static_dir.glob("**/*.js"))

        for file_path in files_to_scan:
            try:
                content = file_path.read_text(encoding='utf-8')

                # 匹配fetch调用：fetch('/api/...'
                pattern = r'fetch\s*\(\s*["\']([^"\']+)["\']'
                matches = re.findall(pattern, content)

                for api_path in matches:
                    # 过滤非API调用
                    if not api_path.startswith('/api/') and not api_path.startswith('/'):
                        continue

                    # 标准化路径
                    if not api_path.startswith('/api/'):
                        api_path = f"/api/{api_path.lstrip('/')}"

                    if api_path not in self.frontend_apis:
                        self.frontend_apis[api_path] = {
                            'files': [],
                            'params_sent': self._extract_fetch_params(content, api_path)
                        }

                    relative_path = file_path.relative_to(static_dir)
                    if str(relative_path) not in self.frontend_apis[api_path]['files']:
                        self.frontend_apis[api_path]['files'].append(str(relative_path))

            except Exception as e:
                self.add_warning("Frontend", f"读取文件失败: {file_path.name}", str(e))

        print(f"✓ 发现 {len(self.frontend_apis)} 个前端API调用")
        self.add_info("Frontend", f"扫描到 {len(self.frontend_apis)} 个API调用")

    def _extract_fetch_params(self, content: str, api_path: str) -> Set[str]:
        """从fetch调用提取发送的参数"""
        params = set()

        # 查找fetch调用的body参数
        escaped_path = re.escape(api_path)
        pattern = rf'fetch\s*\(\s*["\']' + escaped_path + r'["\'][^)]*body:\s*JSON\.stringify\s*\(\s*\{([^}]+)\}'

        matches = re.findall(pattern, content, re.DOTALL)
        for match in matches:
            # 提取参数名
            param_names = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:', match)
            params.update(param_names)

        return params

    # ===== 3. 扫描数据库schema =====
    def scan_database_schema(self):
        """扫描数据库表结构"""
        self.print_section("扫描数据库结构")

        db_paths = [
            PROJECT_ROOT / "data" / "user_history.sqlite",
            PROJECT_ROOT / "data" / "famous_doctors.sqlite"
        ]

        for db_path in db_paths:
            if not db_path.exists():
                self.add_warning("Database", f"数据库不存在: {db_path.name}")
                continue

            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # 获取所有表名
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                for (table_name,) in tables:
                    # 获取表结构
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()

                    self.database_schema[table_name] = {
                        'database': db_path.name,
                        'columns': {}
                    }

                    for col_info in columns:
                        col_name = col_info[1]
                        col_type = col_info[2]
                        self.database_schema[table_name]['columns'][col_name] = col_type

                conn.close()
                print(f"✓ 扫描数据库 {db_path.name}: {len(tables)} 张表")

            except Exception as e:
                self.add_error("Database", f"扫描数据库失败: {db_path.name}", str(e))

        self.add_info("Database", f"扫描到 {len(self.database_schema)} 张表")

    # ===== 4. API一致性检查 =====
    def check_api_consistency(self):
        """检查前后端API一致性"""
        self.print_section("检查前后端API一致性")

        # 检查1: 前端调用的API是否在后端定义
        for fe_api in self.frontend_apis:
            # 尝试精确匹配
            if fe_api not in self.backend_apis:
                # 尝试模糊匹配（路径参数）
                matched = False
                for be_api in self.backend_apis:
                    if self._path_matches(fe_api, be_api):
                        matched = True
                        break

                if not matched:
                    files = ', '.join(self.frontend_apis[fe_api]['files'][:3])
                    self.add_error(
                        "API一致性",
                        f"前端调用的API不存在于后端: {fe_api}",
                        f"调用文件: {files}"
                    )

        # 检查2: 后端定义的API是否被前端使用
        unused_apis = []
        for be_api in self.backend_apis:
            used = False
            for fe_api in self.frontend_apis:
                if self._path_matches(fe_api, be_api):
                    used = True
                    break

            if not used:
                # 排除一些系统API
                if not any(x in be_api for x in ['/health', '/docs', '/openapi']):
                    unused_apis.append(be_api)

        if unused_apis:
            self.add_warning(
                "API一致性",
                f"发现 {len(unused_apis)} 个未被使用的后端API",
                '\n'.join(unused_apis[:10])
            )

        # 统计
        matched_count = len(self.backend_apis) - len(unused_apis)
        print(f"✓ API匹配率: {matched_count}/{len(self.backend_apis)} ({matched_count*100//len(self.backend_apis)}%)")

    def _path_matches(self, path1: str, path2: str) -> bool:
        """路径匹配（支持路径参数）"""
        # 精确匹配
        if path1 == path2:
            return True

        # 路径参数匹配: /api/user/123 匹配 /api/user/{user_id}
        parts1 = path1.split('/')
        parts2 = path2.split('/')

        if len(parts1) != len(parts2):
            return False

        for p1, p2 in zip(parts1, parts2):
            if p1 != p2 and not (p2.startswith('{') and p2.endswith('}')):
                return False

        return True

    # ===== 5. 参数命名一致性检查 =====
    def check_parameter_consistency(self):
        """检查参数命名一致性"""
        self.print_section("检查参数命名一致性")

        # 常见参数别名问题
        param_aliases = {
            'user_id': ['userId', 'patient_id', 'patientId'],
            'doctor_id': ['doctorId', 'selected_doctor', 'doctor_name'],
            'conversation_id': ['conversationId', 'session_id', 'sessionId'],
            'message': ['content', 'msg', 'text']
        }

        inconsistencies = defaultdict(list)

        for fe_api, fe_data in self.frontend_apis.items():
            params_sent = fe_data.get('params_sent', set())

            # 检查是否使用了别名
            for standard_name, aliases in param_aliases.items():
                for alias in aliases:
                    if alias in params_sent and standard_name not in params_sent:
                        inconsistencies[fe_api].append({
                            'param': alias,
                            'suggested': standard_name
                        })

        if inconsistencies:
            for api, issues in list(inconsistencies.items())[:5]:
                details = '\n'.join([f"  - 使用 '{i['param']}', 建议 '{i['suggested']}'" for i in issues])
                self.add_warning(
                    "参数命名",
                    f"API参数命名不一致: {api}",
                    details
                )

        print(f"✓ 发现 {len(inconsistencies)} 个参数命名不一致问题")

    # ===== 6. 数据库字段引用检查 =====
    def check_database_field_references(self):
        """检查代码中的数据库字段引用"""
        self.print_section("检查数据库字段引用")

        # 扫描Python代码中的SQL查询
        api_dir = PROJECT_ROOT / "api"
        py_files = list(api_dir.glob("**/*.py"))

        field_errors = []

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding='utf-8')

                # 查找SQL查询中的字段名
                sql_patterns = [
                    r'SELECT\s+([^FROM]+)\s+FROM\s+(\w+)',
                    r'WHERE\s+(\w+)\s*=',
                    r'ORDER BY\s+(\w+)',
                ]

                for pattern in sql_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            if len(match) == 2:  # SELECT ... FROM table
                                fields, table = match
                                if table in self.database_schema:
                                    field_list = [f.strip() for f in fields.split(',') if f.strip() != '*']
                                    for field in field_list:
                                        if field and field not in self.database_schema[table]['columns']:
                                            field_errors.append({
                                                'file': py_file.name,
                                                'table': table,
                                                'field': field
                                            })

            except Exception as e:
                pass  # 忽略读取错误

        if field_errors:
            for error in field_errors[:10]:
                self.add_error(
                    "数据库字段",
                    f"字段不存在: {error['table']}.{error['field']}",
                    f"文件: {error['file']}"
                )

        print(f"✓ 检查完成，发现 {len(field_errors)} 个字段引用问题")

    # ===== 7. 常见错误模式检查 =====
    def check_common_error_patterns(self):
        """检查文档中列出的常见错误模式"""
        self.print_section("检查常见错误模式")

        static_dir = PROJECT_ROOT / "static"
        files_to_scan = list(static_dir.glob("**/*.html")) + list(static_dir.glob("**/*.js"))

        error_patterns = [
            {
                'name': '错误的API端点',
                'pattern': r'fetch\s*\(\s*["\']/(chat|doctor/list)["\']',
                'message': '使用了错误的API端点，应使用完整路径如 /api/consultation/chat'
            },
            {
                'name': '医生ID格式错误',
                'pattern': r'selected_doctor\s*:\s*["\']?\d+["\']?',
                'message': '医生ID应使用名称格式(zhang_zhongjing)而非数字'
            },
            {
                'name': '响应数据结构不一致',
                'pattern': r'\.reply(?!\s*\|\|)',
                'message': '直接访问.reply可能失败，应检查data.reply或result.data.reply'
            },
            {
                'name': 'try-catch不匹配',
                'pattern': r'try\s*\{[^}]*$',
                'message': 'try块可能缺少对应的catch'
            }
        ]

        for file_path in files_to_scan:
            try:
                content = file_path.read_text(encoding='utf-8')

                for error_pattern in error_patterns:
                    matches = re.findall(error_pattern['pattern'], content)
                    if matches:
                        relative_path = file_path.relative_to(static_dir)
                        self.add_warning(
                            "常见错误",
                            f"{error_pattern['name']}: {relative_path}",
                            error_pattern['message']
                        )

            except Exception:
                pass

        print(f"✓ 常见错误模式检查完成")

    # ===== 8. 生成报告 =====
    def generate_report(self):
        """生成检查报告"""
        self.print_header("📊 一致性检查报告")

        # 统计信息
        print(f"\n{Colors.CYAN}统计信息:{Colors.NC}")
        print(f"  后端API: {len(self.backend_apis)} 个")
        print(f"  前端API调用: {len(self.frontend_apis)} 个")
        print(f"  数据库表: {len(self.database_schema)} 张")

        # 问题汇总
        print(f"\n{Colors.CYAN}问题汇总:{Colors.NC}")
        print(f"  {Colors.RED}错误: {len(self.errors)} 个{Colors.NC}")
        print(f"  {Colors.YELLOW}警告: {len(self.warnings)} 个{Colors.NC}")
        print(f"  {Colors.GREEN}信息: {len(self.info)} 个{Colors.NC}")

        # 详细错误
        if self.errors:
            print(f"\n{Colors.RED}{'=' * 80}{Colors.NC}")
            print(f"{Colors.RED}错误详情 (共 {len(self.errors)} 个):{Colors.NC}")
            print(f"{Colors.RED}{'=' * 80}{Colors.NC}")

            for i, error in enumerate(self.errors, 1):
                print(f"\n{Colors.RED}[{i}] [{error['category']}] {error['message']}{Colors.NC}")
                if error['details']:
                    print(f"    {error['details']}")

        # 详细警告
        if self.warnings:
            print(f"\n{Colors.YELLOW}{'=' * 80}{Colors.NC}")
            print(f"{Colors.YELLOW}警告详情 (共 {len(self.warnings)} 个):{Colors.NC}")
            print(f"{Colors.YELLOW}{'=' * 80}{Colors.NC}")

            for i, warning in enumerate(self.warnings, 1):
                print(f"\n{Colors.YELLOW}[{i}] [{warning['category']}] {warning['message']}{Colors.NC}")
                if warning['details']:
                    print(f"    {warning['details']}")

        # 保存JSON报告
        from datetime import datetime
        report = {
            'timestamp': datetime.now().isoformat(),
            'statistics': {
                'backend_apis': len(self.backend_apis),
                'frontend_apis': len(self.frontend_apis),
                'database_tables': len(self.database_schema)
            },
            'summary': {
                'errors': len(self.errors),
                'warnings': len(self.warnings),
                'info': len(self.info)
            },
            'details': {
                'errors': self.errors,
                'warnings': self.warnings,
                'info': self.info
            }
        }

        report_path = PROJECT_ROOT / "template_files" / "consistency_check_report.json"
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

        print(f"\n{Colors.GREEN}✓ 详细报告已保存: {report_path}{Colors.NC}")

        # 返回状态码
        return 1 if self.errors else 0

    def run(self):
        """运行所有检查"""
        self.print_header("🔍 TCM-AI 代码一致性检查")

        # 执行所有检查
        self.scan_backend_apis()
        self.scan_frontend_apis()
        self.scan_database_schema()

        self.check_api_consistency()
        self.check_parameter_consistency()
        self.check_database_field_references()
        self.check_common_error_patterns()

        # 生成报告
        return self.generate_report()


def main():
    checker = ConsistencyChecker()
    exit_code = checker.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
