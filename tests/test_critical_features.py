#!/usr/bin/env python3
"""
关键功能自动化测试
防止代码修改破坏核心功能

测试范围：
1. 用户认证系统（登录、注册、退出）
2. 医生列表显示
3. 历史记录功能
4. 新对话功能
5. 处方渲染系统

运行方式：
    pytest tests/test_critical_features.py -v
    或
    python tests/test_critical_features.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import re
from pathlib import Path

# 主HTML文件路径
MAIN_HTML = Path(__file__).parent.parent / 'static' / 'index_smart_workflow.html'
SIMPLE_MANAGER_JS = Path(__file__).parent.parent / 'static' / 'js' / 'simple_prescription_manager.js'

class TestCriticalFeatures:
    """关键功能测试套件"""

    def test_html_file_exists(self):
        """测试：主HTML文件存在"""
        assert MAIN_HTML.exists(), f"主HTML文件不存在: {MAIN_HTML}"

    def test_prescription_manager_exists(self):
        """测试：处方管理器文件存在"""
        assert SIMPLE_MANAGER_JS.exists(), f"处方管理器不存在: {SIMPLE_MANAGER_JS}"

    def test_prescription_manager_loaded(self):
        """测试：处方管理器被正确加载"""
        html_content = MAIN_HTML.read_text(encoding='utf-8')

        # 检查simple_prescription_manager.js被加载且未注释
        assert 'simple_prescription_manager.js' in html_content, \
            "simple_prescription_manager.js未被引用"

        # 确保不是注释状态
        script_line_pattern = r'<script[^>]*src="[^"]*simple_prescription_manager\.js[^"]*"[^>]*>'
        matches = re.findall(script_line_pattern, html_content)
        assert len(matches) > 0, "simple_prescription_manager.js的script标签未找到"

        # 确保script标签前面没有<!--
        for match in matches:
            # 找到这一行在文件中的位置
            index = html_content.find(match)
            # 检查前100个字符是否有注释开始标记
            preceding = html_content[max(0, index-100):index]
            assert '<!--' not in preceding or '-->' in preceding, \
                "simple_prescription_manager.js被注释了！"

    def test_compatibility_layer_exists(self):
        """测试：兼容性适配器存在"""
        js_content = SIMPLE_MANAGER_JS.read_text(encoding='utf-8')

        assert 'window.prescriptionContentRenderer' in js_content, \
            "兼容性适配器 prescriptionContentRenderer 不存在"

        assert 'renderContent:' in js_content or 'renderContent =' in js_content, \
            "renderContent方法不存在"

        assert 'containsPrescription:' in js_content or 'containsPrescription =' in js_content, \
            "containsPrescription方法不存在"

    def test_auth_manager_loaded(self):
        """测试：认证管理器被加载"""
        html_content = MAIN_HTML.read_text(encoding='utf-8')

        assert 'auth_manager.js' in html_content or 'authManager' in html_content, \
            "认证管理器未加载"

    def test_login_function_exists(self):
        """测试：登录函数存在"""
        html_content = MAIN_HTML.read_text(encoding='utf-8')

        # 检查关键登录函数
        assert 'function performLogin' in html_content or 'async function performLogin' in html_content, \
            "performLogin函数不存在"

        assert 'showLoginModal' in html_content, \
            "showLoginModal函数不存在"

    def test_doctor_list_function_exists(self):
        """测试：医生列表函数存在"""
        html_content = MAIN_HTML.read_text(encoding='utf-8')

        # 检查医生列表相关函数
        assert 'loadDoctors' in html_content or 'fetchDoctors' in html_content, \
            "医生列表加载函数不存在"

        # 检查医生API端点
        assert '/api/doctor' in html_content or '/api/doctors' in html_content, \
            "医生API端点未配置"

    def test_history_function_exists(self):
        """测试：历史记录函数存在"""
        html_content = MAIN_HTML.read_text(encoding='utf-8')

        assert 'loadDoctorHistory' in html_content, \
            "loadDoctorHistory函数不存在"

        assert 'openHistoryPage' in html_content, \
            "openHistoryPage函数不存在"

    def test_new_conversation_function_exists(self):
        """测试：新对话函数存在"""
        html_content = MAIN_HTML.read_text(encoding='utf-8')

        assert 'startNewConversation' in html_content or 'newConversation' in html_content, \
            "新对话函数不存在"

    def test_mobile_message_is_async(self):
        """测试：移动端消息函数是async"""
        html_content = MAIN_HTML.read_text(encoding='utf-8')

        # 查找addMobileMessage函数定义
        pattern = r'(async\s+)?function\s+addMobileMessage\s*\('
        matches = re.findall(pattern, html_content)

        assert len(matches) > 0, "addMobileMessage函数不存在"
        assert matches[0].strip() == 'async', \
            "addMobileMessage函数不是async的！这会导致处方渲染失败"

    def test_pc_message_is_async(self):
        """测试：PC端消息函数是async"""
        html_content = MAIN_HTML.read_text(encoding='utf-8')

        # 查找addMessage函数定义（PC端）
        pattern = r'(async\s+)?function\s+addMessage\s*\('
        matches = re.findall(pattern, html_content)

        assert len(matches) > 0, "addMessage函数不存在"
        assert matches[0].strip() == 'async', \
            "addMessage函数不是async的！"

    def test_await_in_prescription_rendering(self):
        """测试：处方渲染调用使用了await"""
        html_content = MAIN_HTML.read_text(encoding='utf-8')

        # 检查关键的await调用
        critical_awaits = [
            'await addMobileMessage',
            'await window.simplePrescriptionManager.processContent',
            'await window.prescriptionContentRenderer.renderContent'
        ]

        for await_call in critical_awaits:
            assert await_call in html_content, \
                f"缺少关键的await调用: {await_call}"

    def test_no_syntax_errors_in_try_catch(self):
        """测试：try-catch块没有语法错误"""
        html_content = MAIN_HTML.read_text(encoding='utf-8')

        # 简单检查：每个try都有对应的catch
        try_count = html_content.count('try {')
        catch_count = html_content.count('} catch')

        assert try_count == catch_count, \
            f"try-catch不匹配！try:{try_count}, catch:{catch_count}"

    def test_critical_divs_exist(self):
        """测试：关键DOM元素存在"""
        html_content = MAIN_HTML.read_text(encoding='utf-8')

        critical_ids = [
            'mobileMessagesContainer',  # 移动端消息容器
            'messagesContainer',         # PC端消息容器
            'loginModal',                # 登录模态框
            'doctorList',                # 医生列表容器
            'mobileSendBtn',             # 移动端发送按钮
        ]

        for div_id in critical_ids:
            assert f'id="{div_id}"' in html_content or f"id='{div_id}'" in html_content, \
                f"关键DOM元素缺失: {div_id}"

    def test_strip_prescription_content_method_exists(self):
        """测试：stripPrescriptionContent方法存在"""
        js_content = SIMPLE_MANAGER_JS.read_text(encoding='utf-8')

        assert 'stripPrescriptionContent' in js_content, \
            "stripPrescriptionContent方法不存在，这会导致运行时错误"

    def test_api_endpoints_configured(self):
        """测试：关键API端点已配置"""
        html_content = MAIN_HTML.read_text(encoding='utf-8')

        critical_apis = [
            '/api/consultation/chat',      # 统一问诊
            '/api/auth/login',              # 登录
            '/api/doctor',                  # 医生信息
            '/api/prescription/create',     # 创建处方
        ]

        for api in critical_apis:
            assert api in html_content, \
                f"关键API端点未配置: {api}"


def run_tests():
    """直接运行测试"""
    print("🧪 开始运行关键功能测试...")
    print("=" * 60)

    test_class = TestCriticalFeatures()
    test_methods = [method for method in dir(test_class) if method.startswith('test_')]

    passed = 0
    failed = 0
    errors = []

    for method_name in test_methods:
        method = getattr(test_class, method_name)
        try:
            method()
            print(f"✅ {method_name}")
            passed += 1
        except AssertionError as e:
            print(f"❌ {method_name}")
            print(f"   错误: {e}")
            failed += 1
            errors.append((method_name, str(e)))
        except Exception as e:
            print(f"💥 {method_name}")
            print(f"   异常: {e}")
            failed += 1
            errors.append((method_name, str(e)))

    print("=" * 60)
    print(f"\n📊 测试结果:")
    print(f"   通过: {passed}")
    print(f"   失败: {failed}")
    print(f"   总计: {passed + failed}")

    if failed > 0:
        print("\n❌ 测试失败详情:")
        for test_name, error in errors:
            print(f"\n{test_name}:")
            print(f"  {error}")
        return 1
    else:
        print("\n✅ 所有测试通过！")
        return 0


if __name__ == '__main__':
    exit(run_tests())
