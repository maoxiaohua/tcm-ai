#!/usr/bin/env python3
"""
TCM AI 系统启动脚本
解决路径问题，确保服务正常启动
"""
import sys
import os

# 设置工作目录
os.chdir('/opt/tcm-ai/api')

# 设置Python路径 (顺序很重要!)
sys.path.insert(0, '/opt/tcm-ai/database')
sys.path.insert(0, '/opt/tcm-ai/services')
sys.path.insert(0, '/opt/tcm-ai/core')
sys.path.insert(0, '/opt/tcm-ai')

# 设置环境变量
os.environ['PYTHONPATH'] = '/opt/tcm-ai:/opt/tcm-ai/core:/opt/tcm-ai/services:/opt/tcm-ai/database'
os.environ['PYTHONUNBUFFERED'] = '1'

if __name__ == "__main__":
    try:
        print("🚀 启动TCM AI系统...")
        print(f"工作目录: {os.getcwd()}")
        print(f"Python路径: {sys.path[:4]}")
        
        # 执行主程序
        exec(open('main.py').read())
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)