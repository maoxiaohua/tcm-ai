#!/usr/bin/env python3
"""
TCM AI 系统启动脚本
解决路径问题，确保服务正常启动
"""
import sys
import os

# 设置工作目录
os.chdir('/home/ute/tcm-ai/api')

# 设置Python路径 (顺序很重要!)
sys.path.insert(0, '/home/ute/tcm-ai/database')
sys.path.insert(0, '/home/ute/tcm-ai/services')
sys.path.insert(0, '/home/ute/tcm-ai/core')
sys.path.insert(0, '/home/ute/tcm-ai')

# 设置环境变量
os.environ['PYTHONPATH'] = '/home/ute/tcm-ai:/home/ute/tcm-ai/core:/home/ute/tcm-ai/services:/home/ute/tcm-ai/database'
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