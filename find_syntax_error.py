#!/usr/bin/env python3

import re

def find_unmatched_try_blocks(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    stack = []  # Stack to track open try blocks
    unmatched = []
    
    for i, line in enumerate(lines):
        line_num = i + 1
        
        # Look for try blocks
        if re.search(r'try\s*{', line):
            stack.append(line_num)
            print(f"Found try at line {line_num}: {line.strip()}")
        
        # Look for catch blocks
        elif re.search(r'catch\s*\(', line):
            if stack:
                matched_try = stack.pop()
                print(f"Found catch at line {line_num} for try at line {matched_try}")
            else:
                print(f"Found unmatched catch at line {line_num}: {line.strip()}")
    
    # Any remaining items in stack are unmatched try blocks
    for try_line in stack:
        print(f"❌ Unmatched try block at line {try_line}")
        unmatched.append(try_line)
    
    return unmatched

if __name__ == "__main__":
    unmatched = find_unmatched_try_blocks('/opt/tcm-ai/static/index_smart_workflow.html')
    print(f"\n总结: 发现 {len(unmatched)} 个未匹配的try块")
    for line_num in unmatched:
        print(f"未匹配的try块在第 {line_num} 行")