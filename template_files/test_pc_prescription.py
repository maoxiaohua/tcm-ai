#!/usr/bin/env python3
"""
测试PC端处方分析功能
模拟真实的PC端调用流程
"""

import requests
import json
import tempfile
import os
from PIL import Image, ImageDraw, ImageFont

def create_test_prescription_image():
    """创建一个测试用的处方图片"""
    
    # 创建一个白色背景的图片
    width, height = 800, 600
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # 模拟处方内容
    prescription_text = """
    处方单
    
    患者姓名: 张三
    年龄: 45岁
    
    药材清单:
    炙黄芪    15g
    炒白术    12g  
    茯苓      10g
    制附子     9g
    当归       8g
    炙甘草     6g
    
    医生: 李医生
    日期: 2025-08-22
    """
    
    # 在图片上绘制文字
    try:
        # 尝试使用系统字体
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    lines = prescription_text.strip().split('\n')
    y_offset = 50
    
    for line in lines:
        if line.strip():
            draw.text((50, y_offset), line.strip(), fill='black', font=font)
            y_offset += 35
    
    # 保存到临时文件
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    img.save(temp_file.name, 'PNG')
    temp_file.close()
    
    return temp_file.name

def test_prescription_analysis():
    """测试处方分析功能"""
    
    print("🧪 开始测试PC端处方分析功能...")
    
    # 创建测试图片
    test_image_path = create_test_prescription_image()
    print(f"✅ 测试图片创建成功: {test_image_path}")
    
    try:
        # 测试新的多模态API
        url = "http://localhost:8000/api/prescription/check_image_v2"
        
        with open(test_image_path, 'rb') as f:
            files = {'file': ('test_prescription.png', f, 'image/png')}
            
            print("📤 发送API请求...")
            response = requests.post(url, files=files, timeout=120)
            
            print(f"📥 API响应状态: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ API调用成功!")
                
                # 检查君臣佐使分析结果
                if 'formula_analysis' in result:
                    print("\n🔍 君臣佐使分析结果:")
                    formula_analysis = result['formula_analysis']
                    
                    if 'roles' in formula_analysis:
                        for role, herbs in formula_analysis['roles'].items():
                            if herbs:
                                print(f"\n{role}:")
                                for herb in herbs:
                                    reason = herb.get('reason', '无描述')
                                    print(f"  - {herb.get('name', '未知')}: {reason}")
                                    
                                    # 检查是否包含"调理脏腑功能"
                                    if '调理脏腑功能' in reason:
                                        print(f"    ❌ 发现bug: {herb.get('name')} 仍显示调理脏腑功能")
                                        return False
                                    else:
                                        print(f"    ✅ 功效描述正确")
                    else:
                        print("❌ 未找到roles信息")
                        return False
                else:
                    print("❌ 未找到formula_analysis")
                    return False
                    
                print("\n🎉 所有药材功效描述正确，bug已修复!")
                return True
                
            else:
                print(f"❌ API调用失败: {response.status_code}")
                print(f"错误内容: {response.text}")
                return False
                
    except Exception as e:
        print(f"💥 测试过程中出现异常: {e}")
        return False
        
    finally:
        # 清理临时文件
        try:
            os.unlink(test_image_path)
            print(f"🧹 清理临时文件: {test_image_path}")
        except:
            pass

if __name__ == "__main__":
    success = test_prescription_analysis()
    if success:
        print("\n✅ PC端处方分析功能测试通过！")
        exit(0)
    else:
        print("\n❌ PC端处方分析功能测试失败！")
        exit(1)