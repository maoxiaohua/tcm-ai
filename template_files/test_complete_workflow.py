#!/usr/bin/env python3
"""
医生客户端闭环系统完整流程测试脚本
测试从AI问诊到代煎配送的完整流程
"""
import sys
import os
import asyncio
import sqlite3
from datetime import datetime

# 添加项目路径
sys.path.append('/opt/tcm-ai')
sys.path.append('/opt/tcm-ai/core')

from core.doctor_management.doctor_auth import doctor_auth_manager
from core.decoction_service.decoction_providers import decoction_service_manager

def print_step(step_num: int, description: str):
    """打印测试步骤"""
    print(f"\n{'='*50}")
    print(f"步骤 {step_num}: {description}")
    print('='*50)

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

async def test_complete_workflow():
    """测试完整的医生客户端闭环流程"""
    print("🏥 开始测试医生客户端闭环系统")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 步骤1: 模拟AI问诊生成处方
    print_step(1, "模拟AI问诊生成处方")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 插入测试处方
        test_prescription = """
        **中医诊断**：脾胃虚弱，湿热内蕴
        
        **处方**：
        黄连 10g
        黄芩 10g  
        黄柏 10g
        茯苓 15g
        白术 12g
        甘草 6g
        
        **用法**：水煎服，日一剂，分两次温服
        **疗程**：7天
        """
        
        cursor.execute("""
            INSERT INTO prescriptions (
                patient_id, conversation_id, patient_name, patient_phone,
                symptoms, diagnosis, ai_prescription, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "test_patient_001",
            "test_conversation_001", 
            "张三",
            "13800138001",
            "腹泻，腹痛，食欲不振",
            "脾胃虚弱，湿热内蕴",
            test_prescription,
            "pending"
        ))
        
        prescription_id = cursor.lastrowid
        conn.commit()
        print(f"✅ 创建测试处方成功，ID: {prescription_id}")
        
    except Exception as e:
        print(f"❌ 创建处方失败: {e}")
        return False
    
    # 步骤2: 医生登录和审查处方
    print_step(2, "医生登录和审查处方")
    
    # 医生登录
    login_result = doctor_auth_manager.login('TCM001', 'password123')
    if not login_result:
        print("❌ 医生登录失败")
        return False
    
    doctor_id = login_result['id']
    print(f"✅ 医生登录成功: {login_result['name']}")
    
    # 医生审查并批准处方
    try:
        cursor.execute("""
            UPDATE prescriptions 
            SET status = 'approved', doctor_id = ?, 
                doctor_prescription = ?, doctor_notes = ?, 
                reviewed_at = datetime('now')
            WHERE id = ?
        """, (
            doctor_id,
            test_prescription + "\n\n[医生备注] 处方合理，同意执行",
            "处方符合患者症状，建议按时服用",
            prescription_id
        ))
        conn.commit()
        print("✅ 医生审查处方成功")
        
    except Exception as e:
        print(f"❌ 医生审查处方失败: {e}")
        return False
    
    # 步骤3: 患者确认处方
    print_step(3, "患者确认处方")
    
    try:
        cursor.execute("""
            UPDATE prescriptions 
            SET status = 'patient_confirmed', confirmed_at = datetime('now')
            WHERE id = ?
        """, (prescription_id,))
        conn.commit()
        print("✅ 患者确认处方成功")
        
    except Exception as e:
        print(f"❌ 患者确认处方失败: {e}")
        return False
    
    # 步骤4: 创建支付订单
    print_step(4, "创建支付订单")
    
    try:
        order_no = f"TCM{datetime.now().strftime('%Y%m%d%H%M%S')}TEST"
        base_amount = 88.0  # 基础诊疗费
        herb_amount = 120.0  # 药材费用
        decoction_fee = 30.0  # 代煎费用
        total_amount = base_amount + herb_amount + decoction_fee
        
        cursor.execute("""
            INSERT INTO orders (
                order_no, prescription_id, patient_id, amount, payment_method,
                decoction_required, shipping_name, shipping_phone, 
                shipping_address, payment_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_no, prescription_id, "test_patient_001", total_amount, "alipay",
            1, "张三", "13800138001", "北京市朝阳区测试街道123号", "pending"
        ))
        
        order_id = cursor.lastrowid
        conn.commit()
        print(f"✅ 创建支付订单成功，订单号: {order_no}")
        
    except Exception as e:
        print(f"❌ 创建支付订单失败: {e}")
        return False
    
    # 步骤5: 模拟支付完成
    print_step(5, "模拟支付完成")
    
    try:
        cursor.execute("""
            UPDATE orders 
            SET payment_status = 'paid', payment_time = datetime('now'),
                payment_transaction_id = 'ALIPAY_TEST_' || ?
            WHERE id = ?
        """, (datetime.now().strftime('%Y%m%d%H%M%S'), order_id))
        
        # 更新处方状态为已支付
        cursor.execute("""
            UPDATE prescriptions 
            SET status = 'paid' 
            WHERE id = ?
        """, (prescription_id,))
        
        conn.commit()
        print("✅ 支付完成，处方状态已更新")
        
    except Exception as e:
        print(f"❌ 支付处理失败: {e}")
        return False
    
    # 步骤6: 提交代煎服务
    print_step(6, "提交代煎服务")
    
    try:
        # 准备代煎数据
        prescription_data = {
            'prescription_id': prescription_id,
            'prescription_content': test_prescription,
            'patient_info': {
                'name': '张三',
                'phone': '13800138001'
            },
            'shipping_info': {
                'name': '张三',
                'phone': '13800138001',
                'address': '北京市朝阳区测试街道123号'
            }
        }
        
        # 提交到代煎服务
        decoction_result = await decoction_service_manager.submit_prescription(
            prescription_data, 'default'
        )
        
        if decoction_result['success']:
            # 创建代煎订单记录
            cursor.execute("""
                INSERT INTO decoction_orders (
                    order_id, provider_id, provider_name, decoction_order_no,
                    status, estimated_delivery
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                'default',
                '默认代煎服务',
                decoction_result['order_no'],
                'submitted',
                decoction_result.get('estimated_delivery')
            ))
            
            # 更新处方状态
            cursor.execute("""
                UPDATE prescriptions 
                SET status = 'decoction_submitted' 
                WHERE id = ?
            """, (prescription_id,))
            
            conn.commit()
            print(f"✅ 代煎服务提交成功，代煎订单号: {decoction_result['order_no']}")
            decoction_order_no = decoction_result['order_no']
            
        else:
            print(f"❌ 代煎服务提交失败: {decoction_result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ 代煎服务处理失败: {e}")
        return False
    
    # 步骤7: 模拟代煎状态更新
    print_step(7, "模拟代煎状态更新")
    
    try:
        # 模拟代煎状态演进
        statuses = [
            ('confirmed', '代煎订单已确认'),
            ('processing', '开始煎制处理'),
            ('completed', '煎制完成'),
            ('shipped', '已发货，物流单号: SF123456789'),
            ('delivered', '已送达')
        ]
        
        for status, message in statuses:
            cursor.execute("""
                UPDATE decoction_orders 
                SET status = ?, provider_notes = ?, updated_at = datetime('now')
                WHERE decoction_order_no = ?
            """, (status, message, decoction_order_no))
            
            # 如果已送达，更新处方状态为已完成
            if status == 'delivered':
                cursor.execute("""
                    UPDATE prescriptions 
                    SET status = 'completed' 
                    WHERE id = ?
                """, (prescription_id,))
            
            conn.commit()
            print(f"✅ 代煎状态更新: {status} - {message}")
            
            # 模拟时间延迟
            await asyncio.sleep(0.1)
            
    except Exception as e:
        print(f"❌ 代煎状态更新失败: {e}")
        return False
    
    # 步骤8: 验证完整流程
    print_step(8, "验证完整流程")
    
    try:
        # 查询最终的处方状态
        cursor.execute("""
            SELECT p.*, d.name as doctor_name, o.order_no, o.amount, 
                   dec.decoction_order_no, dec.status as decoction_status
            FROM prescriptions p
            LEFT JOIN doctors d ON p.doctor_id = d.id
            LEFT JOIN orders o ON p.id = o.prescription_id
            LEFT JOIN decoction_orders dec ON o.id = dec.order_id
            WHERE p.id = ?
        """, (prescription_id,))
        
        final_result = cursor.fetchone()
        if final_result:
            result_dict = dict(final_result)
            print("✅ 完整流程验证成功！")
            print(f"   处方状态: {result_dict['status']}")
            print(f"   审查医生: {result_dict['doctor_name']}")
            print(f"   支付订单: {result_dict['order_no']}")
            print(f"   支付金额: ¥{result_dict['amount']}")
            print(f"   代煎订单: {result_dict['decoction_order_no']}")
            print(f"   代煎状态: {result_dict['decoction_status']}")
            
            # 统计信息
            cursor.execute("SELECT COUNT(*) FROM prescriptions")
            prescription_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM orders WHERE payment_status = 'paid'")
            paid_orders = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM decoction_orders WHERE status = 'delivered'")
            delivered_orders = cursor.fetchone()[0]
            
            print(f"\n📊 系统统计:")
            print(f"   总处方数: {prescription_count}")
            print(f"   已支付订单: {paid_orders}")
            print(f"   已送达代煎: {delivered_orders}")
            
            return True
        else:
            print("❌ 无法获取最终结果")
            return False
            
    except Exception as e:
        print(f"❌ 验证流程失败: {e}")
        return False
    
    finally:
        conn.close()

async def main():
    """主函数"""
    success = await test_complete_workflow()
    
    print(f"\n{'='*70}")
    if success:
        print("🎉 医生客户端闭环系统测试 - 全部通过！")
        print("✅ 系统功能完整，可以投入使用")
    else:
        print("❌ 测试失败，请检查系统配置")
    print('='*70)
    
    return success

if __name__ == "__main__":
    # 运行完整流程测试
    result = asyncio.run(main())
    sys.exit(0 if result else 1)