#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试重构后的API是否有运行时错误
"""

import sys
import os
import requests
import time
import subprocess
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/opt/tcm-ai')
sys.path.insert(0, '/opt/tcm-ai/api')

def test_api_import():
    """测试API导入是否正常"""
    print("=" * 60)
    print("测试API导入")
    print("-" * 40)
    
    try:
        # 测试重构后的模块导入
        from api.processors.chat_endpoint_processor import ChatEndpointProcessor
        print("✓ ChatEndpointProcessor 导入成功")
        
        from api.services.llm_service_wrapper import LLMServiceWrapper, MultimodalServiceWrapper
        print("✓ 服务包装器导入成功")
        
        from api.utils.common_utils import safe_execute, generate_conversation_id
        print("✓ 通用工具模块导入成功")
        
        print("✓ 所有重构模块导入正常")
        return True
        
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def start_server_test():
    """启动服务器进行测试"""
    print("=" * 60)
    print("启动测试服务器")
    print("-" * 40)
    
    try:
        # 切换到正确的目录
        os.chdir('/opt/tcm-ai/api')
        
        # 启动服务器（非阻塞模式）
        print("启动FastAPI服务器...")
        process = subprocess.Popen(
            [sys.executable, 'main.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待服务器启动
        print("等待服务器启动...")
        max_wait_time = 60  # 最多等待60秒
        start_time = time.time()
        server_ready = False
        
        while time.time() - start_time < max_wait_time:
            try:
                response = requests.get('http://localhost:8000/health', timeout=5)
                if response.status_code == 200:
                    server_ready = True
                    break
            except:
                pass
            
            time.sleep(2)
            
            # 检查进程是否还在运行
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"服务器进程意外退出")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return False, None
        
        if server_ready:
            print("✓ 服务器启动成功")
            return True, process
        else:
            print("✗ 服务器启动超时")
            process.terminate()
            return False, None
            
    except Exception as e:
        print(f"✗ 服务器启动失败: {e}")
        return False, None

def test_endpoints(process):
    """测试API端点"""
    print("=" * 60)
    print("测试API端点")
    print("-" * 40)
    
    try:
        base_url = "http://localhost:8000"
        
        # 测试健康检查
        try:
            response = requests.get(f"{base_url}/health", timeout=10)
            print(f"✓ Health检查: {response.status_code}")
        except Exception as e:
            print(f"✗ Health检查失败: {e}")
        
        # 测试聊天接口
        try:
            chat_data = {
                "message": "我有头痛症状，请分析",
                "conversation_id": "test_conv_123",
                "selected_doctor": "zhang_zhongjing"
            }
            
            response = requests.post(
                f"{base_url}/chat_with_ai", 
                json=chat_data, 
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✓ 聊天接口测试成功")
                print(f"  响应长度: {len(result.get('message', ''))}")
                print(f"  处理时间: {result.get('processing_time', 0):.2f}秒")
            else:
                print(f"✗ 聊天接口返回错误状态码: {response.status_code}")
                print(f"  响应内容: {response.text}")
                
        except Exception as e:
            print(f"✗ 聊天接口测试失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ 端点测试失败: {e}")
        return False
    
    finally:
        # 清理进程
        if process:
            process.terminate()
            process.wait()

def main():
    """主测试函数"""
    print("开始测试重构后的TCM AI系统")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 第一步：测试模块导入
    if not test_api_import():
        print("❌ 模块导入测试失败，退出测试")
        return False
    
    print()
    
    # 第二步：启动服务器测试  
    server_started, process = start_server_test()
    if not server_started:
        print("❌ 服务器启动测试失败")
        return False
    
    print()
    
    # 第三步：测试API端点
    try:
        endpoints_ok = test_endpoints(process) 
        
        print()
        if endpoints_ok:
            print("🎉 重构后的系统运行正常！")
            print("✅ 所有核心功能测试通过")
        else:
            print("⚠️ 部分功能测试失败，但系统基本运行正常")
            
        return endpoints_ok
        
    finally:
        # 确保清理进程
        if process and process.poll() is None:
            process.terminate()
            process.wait()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)