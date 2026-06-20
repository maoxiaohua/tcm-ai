#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控无效HTTP请求，分析来源
"""

import subprocess
import re
import time
from collections import defaultdict
from datetime import datetime

def monitor_invalid_requests():
    """监控无效HTTP请求"""
    print("开始监控无效HTTP请求...")
    print("时间: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print("-" * 60)
    
    # 监控日志
    cmd = ["sudo", "journalctl", "-u", "tcm-ai.service", "-f", "--no-pager"]
    
    request_count = defaultdict(int)
    start_time = time.time()
    
    try:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        print("正在监控... (按Ctrl+C停止)")
        
        for line in iter(process.stdout.readline, ''):
            if "Invalid HTTP request received" in line:
                timestamp = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if timestamp:
                    ts = timestamp.group(1)
                    request_count[ts] += 1
                    print(f"❌ {ts}: 检测到无效HTTP请求 (累计: {sum(request_count.values())})")
            
            elif "INFO" in line and ("GET" in line or "POST" in line):
                timestamp = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if timestamp:
                    ts = timestamp.group(1)
                    print(f"✅ {ts}: 正常HTTP请求")
            
            # 每30秒汇总一次
            if time.time() - start_time > 30:
                total_invalid = sum(request_count.values())
                if total_invalid > 0:
                    print(f"\n📊 过去30秒统计: {total_invalid} 次无效请求")
                    request_count.clear()
                start_time = time.time()
                
    except KeyboardInterrupt:
        print("\n监控已停止")
        total_invalid = sum(request_count.values())
        if total_invalid > 0:
            print(f"📊 总计发现 {total_invalid} 次无效HTTP请求")
        
    finally:
        if process:
            process.terminate()

if __name__ == "__main__":
    monitor_invalid_requests()