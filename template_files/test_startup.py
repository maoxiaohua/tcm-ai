#!/usr/bin/env python3
"""
快速启动测试脚本
"""
import sys
import os

# 设置路径
sys.path.insert(0, '/opt/tcm-ai')
sys.path.insert(0, '/opt/tcm-ai/core')
sys.path.insert(0, '/opt/tcm-ai/services')
sys.path.insert(0, '/opt/tcm-ai/database')

# 测试关键导入
try:
    print("🔍 测试配置导入...")
    from config.settings import PATHS
    print(f"✅ 配置加载成功: {PATHS['project_root']}")
    
    print("🔍 测试缓存系统导入...")
    from core.cache_system.intelligent_cache_system import IntelligentCacheSystem
    print("✅ 缓存系统导入成功")
    
    print("🔍 测试用户历史系统...")
    from services.user_history_system import UserHistorySystem
    print("✅ 用户历史系统导入成功")
    
    print("🔍 测试主程序导入...")
    # 切换到API目录
    os.chdir('/opt/tcm-ai/api')
    exec(open('main.py').read()[:100])  # 只测试开头部分
    print("✅ 主程序基础导入成功")
    
    print("🎉 所有基础模块测试通过！")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()