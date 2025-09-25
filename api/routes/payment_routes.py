"""
支付相关API路由
"""
from fastapi import APIRouter, HTTPException, Request, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sqlite3
import uuid
from datetime import datetime
import json

from core.payment_integration.payment_manager import payment_manager

router = APIRouter(prefix="/api/payment", tags=["支付"])

class CreateOrderRequest(BaseModel):
    """创建支付订单请求"""
    prescription_id: int
    payment_method: str  # alipay 或 wechat
    decoction_required: bool = False
    shipping_name: Optional[str] = None
    shipping_phone: Optional[str] = None
    shipping_address: Optional[str] = None
    notes: Optional[str] = None

class CreatePaymentRequest(BaseModel):
    """创建支付请求（前端调用）"""
    prescription_id: int
    amount: float
    payment_method: str

class OrderStatusResponse(BaseModel):
    """订单状态响应"""
    success: bool
    order: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

def calculate_prescription_amount(prescription_id: int) -> float:
    """计算处方费用（简化版本）"""
    # 这里可以根据具体的处方内容计算费用
    # 暂时返回固定金额
    base_amount = 88.0  # 基础诊疗费
    herb_amount = 120.0  # 药材费用
    
    # 如果需要代煎，增加代煎费
    decoction_fee = 30.0
    
    return base_amount + herb_amount

@router.post("/alipay/create")
async def create_alipay_payment(request: CreatePaymentRequest):
    """创建支付宝支付订单"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查处方是否存在
        cursor.execute("SELECT * FROM prescriptions WHERE id = ?", (request.prescription_id,))
        prescription = cursor.fetchone()
        if not prescription:
            raise HTTPException(status_code=404, detail="处方不存在")
        
        prescription_dict = dict(prescription)
        
        # 生成订单号
        order_no = f"TCM{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:8]}"
        
        # 创建数据库订单记录
        cursor.execute("""
            INSERT INTO orders (
                order_no, prescription_id, patient_id, amount, payment_method,
                decoction_required, payment_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            order_no, request.prescription_id, prescription_dict['patient_id'],
            request.amount, 'alipay', 0, 'pending'
        ))
        
        conn.commit()
        
        # 模拟支付数据（开发环境）
        payment_url = f"https://openapi.alipay.com/gateway.do?out_trade_no={order_no}"
        
        return {
            "success": True,
            "data": {
                "payment_id": order_no,
                "payment_url": payment_url,
                "order_no": order_no,
                "amount": request.amount
            },
            "message": "支付宝支付订单创建成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"创建支付宝支付失败: {e}")
    finally:
        conn.close()

@router.post("/wechat/create") 
async def create_wechat_payment(request: CreatePaymentRequest):
    """创建微信支付订单"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查处方是否存在
        cursor.execute("SELECT * FROM prescriptions WHERE id = ?", (request.prescription_id,))
        prescription = cursor.fetchone()
        if not prescription:
            raise HTTPException(status_code=404, detail="处方不存在")
        
        prescription_dict = dict(prescription)
        
        # 生成订单号
        order_no = f"TCM{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:8]}"
        
        # 创建数据库订单记录
        cursor.execute("""
            INSERT INTO orders (
                order_no, prescription_id, patient_id, amount, payment_method,
                decoction_required, payment_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            order_no, request.prescription_id, prescription_dict['patient_id'],
            request.amount, 'wechat', 0, 'pending'
        ))
        
        conn.commit()
        
        # 模拟二维码数据（开发环境）
        qr_code = f"weixin://wxpay/bizpayurl?pr={order_no}"
        
        return {
            "success": True,
            "data": {
                "payment_id": order_no,
                "qr_code": qr_code,
                "order_no": order_no,
                "amount": request.amount
            },
            "message": "微信支付订单创建成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"创建微信支付失败: {e}")
    finally:
        conn.close()

@router.post("/create-order")
async def create_payment_order(request: CreateOrderRequest):
    """创建支付订单"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查处方是否存在且已获得患者确认
        cursor.execute("""
            SELECT * FROM prescriptions 
            WHERE id = ? AND status = 'patient_confirmed'
        """, (request.prescription_id,))
        
        prescription = cursor.fetchone()
        if not prescription:
            raise HTTPException(
                status_code=404, 
                detail="处方不存在或未获得患者确认"
            )
        
        # 计算订单金额
        base_amount = calculate_prescription_amount(request.prescription_id)
        decoction_fee = 30.0 if request.decoction_required else 0.0
        total_amount = base_amount + decoction_fee
        
        # 生成订单号
        order_no = f"TCM{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:8]}"
        
        # 创建订单记录
        cursor.execute("""
            INSERT INTO orders (
                order_no, prescription_id, patient_id, amount, payment_method,
                decoction_required, shipping_name, shipping_phone, 
                shipping_address, notes, payment_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_no, request.prescription_id, prescription['patient_id'],
            total_amount, request.payment_method, 
            1 if request.decoction_required else 0,
            request.shipping_name, request.shipping_phone,
            request.shipping_address, request.notes, 'pending'
        ))
        
        order_id = cursor.lastrowid
        conn.commit()
        
        # 调用支付接口创建支付订单
        payment_data = {
            'order_no': order_no,
            'amount': total_amount,
            'subject': f'中医处方费用 - 订单{order_no}',
            'body': f'处方ID: {request.prescription_id}'
        }
        
        payment_result = payment_manager.create_payment_order(
            request.payment_method, payment_data
        )
        
        if payment_result['success']:
            return {
                "success": True,
                "order_id": order_id,
                "order_no": order_no,
                "amount": total_amount,
                "payment_method": request.payment_method,
                "payment_data": payment_result
            }
        else:
            # 支付订单创建失败，删除数据库订单
            cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
            conn.commit()
            
            raise HTTPException(
                status_code=500,
                detail=f"创建支付订单失败: {payment_result.get('error', '未知错误')}"
            )
            
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"创建订单失败: {e}")
    finally:
        conn.close()

@router.get("/status/{payment_id}")
async def get_payment_status(payment_id: str):
    """查询支付状态（基于数据库真实状态）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询订单状态 (payment_id实际上是order_no)
        cursor.execute("""
            SELECT o.payment_status, o.prescription_id, o.amount, o.payment_method
            FROM orders o
            WHERE o.order_no = ?
        """, (payment_id,))
        
        order = cursor.fetchone()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        order_dict = dict(order)
        status = "paid" if order_dict['payment_status'] == 'paid' else "pending"
        message = "支付成功" if status == "paid" else "等待支付"
        
        return {
            "success": True,
            "data": {
                "payment_id": payment_id,
                "status": status,
                "message": message,
                "prescription_id": order_dict['prescription_id'],
                "amount": order_dict['amount'],
                "payment_method": order_dict['payment_method']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询支付状态失败: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

@router.post("/wechat/test-success")
async def test_wechat_payment_success(order_no: str):
    """测试微信支付成功（开发测试用）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查找订单
        cursor.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,))
        order = cursor.fetchone()
        
        if not order:
            return {
                "success": False,
                "message": "订单不存在，请重新创建订单后再试",
                "error_code": "ORDER_NOT_FOUND"
            }
        
        order_dict = dict(order)
        
        # 更新订单状态 (如果尚未支付)
        cursor.execute("""
            UPDATE orders 
            SET payment_status = 'paid', 
                payment_time = datetime('now'),
                payment_transaction_id = ?
            WHERE order_no = ? AND payment_status = 'pending'
        """, (f"TEST_{order_no}", order_no))
        
        # 检查订单是否已经支付或刚刚更新成功
        if cursor.rowcount > 0 or order_dict['payment_status'] == 'paid':
            # 更新处方状态为pending（进入医生审核流程）
            cursor.execute("""
                UPDATE prescriptions 
                SET status = 'pending', payment_status = 'paid'
                WHERE id = ?
            """, (order_dict['prescription_id'],))
            
            conn.commit()
            
            return {
                "success": True,
                "message": "测试支付成功，处方已进入医生审核流程",
                "order_no": order_no,
                "prescription_id": order_dict['prescription_id']
            }
        else:
            return {
                "success": True,
                "message": f"订单已处理完成（当前状态：{order_dict['payment_status']}）",
                "order_no": order_no,
                "prescription_id": order_dict['prescription_id']
            }
            
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"测试支付失败: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

@router.post("/alipay/test-success")
async def test_alipay_payment_success(order_no: str):
    """测试支付宝支付成功（开发测试用）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查找订单
        cursor.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,))
        order = cursor.fetchone()
        
        if not order:
            return {
                "success": False,
                "message": "订单不存在，请重新创建订单后再试",
                "error_code": "ORDER_NOT_FOUND"
            }
        
        order_dict = dict(order)
        
        # 更新订单状态 (如果尚未支付)
        cursor.execute("""
            UPDATE orders 
            SET payment_status = 'paid', 
                payment_time = datetime('now'),
                payment_transaction_id = ?
            WHERE order_no = ? AND payment_status = 'pending'
        """, (f"TEST_ALIPAY_{order_no}", order_no))
        
        # 检查订单是否已经支付或刚刚更新成功
        if cursor.rowcount > 0 or order_dict['payment_status'] == 'paid':
            # 更新处方状态为pending（进入医生审核流程）
            cursor.execute("""
                UPDATE prescriptions 
                SET status = 'pending', payment_status = 'paid'
                WHERE id = ?
            """, (order_dict['prescription_id'],))
            
            conn.commit()
            
            return {
                "success": True,
                "message": "测试支付成功，处方已进入医生审核流程",
                "order_no": order_no,
                "prescription_id": order_dict['prescription_id']
            }
        else:
            return {
                "success": True,
                "message": f"订单已处理完成（当前状态：{order_dict['payment_status']}）",
                "order_no": order_no,
                "prescription_id": order_dict['prescription_id']
            }
            
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"测试支付失败: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

@router.get("/order/{order_id}/status")
async def get_order_status(order_id: int):
    """查询订单状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT o.*, p.ai_prescription, p.doctor_prescription
            FROM orders o
            LEFT JOIN prescriptions p ON o.prescription_id = p.id
            WHERE o.id = ?
        """, (order_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        order = dict(row)
        
        return {
            "success": True,
            "order": order
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询订单状态失败: {e}")
    finally:
        conn.close()

@router.post("/alipay/notify")
async def alipay_notify_handler(request: Request):
    """支付宝支付回调处理"""
    try:
        # 获取回调参数
        form_data = await request.form()
        params = dict(form_data)
        
        # 验证支付宝签名
        if not payment_manager.verify_payment_notify('alipay', params.copy()):
            return {"success": False, "message": "签名验证失败"}
        
        # 提取关键信息
        out_trade_no = params.get('out_trade_no')  # 商户订单号
        trade_status = params.get('trade_status')  # 交易状态
        total_amount = params.get('total_amount')  # 支付金额
        trade_no = params.get('trade_no')  # 支付宝交易号
        
        # 只有支付成功的回调才处理
        if trade_status in ['TRADE_SUCCESS', 'TRADE_FINISHED']:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                # 更新订单状态
                cursor.execute("""
                    UPDATE orders 
                    SET payment_status = 'paid', 
                        payment_time = datetime('now'),
                        payment_transaction_id = ?
                    WHERE order_no = ? AND payment_status = 'pending'
                """, (trade_no, out_trade_no))
                
                if cursor.rowcount > 0:
                    # 获取订单信息
                    cursor.execute("""
                        SELECT prescription_id FROM orders WHERE order_no = ?
                    """, (out_trade_no,))
                    
                    row = cursor.fetchone()
                    if row:
                        prescription_id = row['prescription_id']
                        
                        # 更新处方状态为pending（进入医生审核流程）
                        cursor.execute("""
                            UPDATE prescriptions 
                            SET status = 'pending', payment_status = 'paid'
                            WHERE id = ?
                        """, (prescription_id,))
                
                conn.commit()
                
            except Exception as e:
                conn.rollback()
                print(f"处理支付宝回调失败: {e}")
            finally:
                conn.close()
        
        return "success"  # 支付宝要求返回success
        
    except Exception as e:
        print(f"支付宝回调处理异常: {e}")
        return {"success": False, "message": "处理失败"}

@router.post("/wechat/notify")
async def wechat_notify_handler(request: Request):
    """微信支付回调处理"""
    try:
        # 获取XML数据
        xml_data = await request.body()
        
        # 解析XML（简化版本）
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_data.decode('utf-8'))
        params = {child.tag: child.text for child in root}
        
        # 验证微信签名
        if not payment_manager.verify_payment_notify('wechat', params.copy()):
            return {
                'return_code': 'FAIL',
                'return_msg': '签名验证失败'
            }
        
        # 检查支付结果
        if params.get('return_code') == 'SUCCESS' and params.get('result_code') == 'SUCCESS':
            out_trade_no = params.get('out_trade_no')  # 商户订单号
            transaction_id = params.get('transaction_id')  # 微信交易号
            total_fee = params.get('total_fee')  # 支付金额（分）
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                # 更新订单状态
                cursor.execute("""
                    UPDATE orders 
                    SET payment_status = 'paid', 
                        payment_time = datetime('now'),
                        payment_transaction_id = ?
                    WHERE order_no = ? AND payment_status = 'pending'
                """, (transaction_id, out_trade_no))
                
                if cursor.rowcount > 0:
                    # 获取订单信息并更新处方状态
                    cursor.execute("""
                        SELECT prescription_id FROM orders WHERE order_no = ?
                    """, (out_trade_no,))
                    
                    row = cursor.fetchone()
                    if row:
                        prescription_id = row['prescription_id']
                        
                        # 更新处方状态为pending（进入医生审核流程）
                        cursor.execute("""
                            UPDATE prescriptions 
                            SET status = 'pending', payment_status = 'paid'
                            WHERE id = ?
                        """, (prescription_id,))
                
                conn.commit()
                
            except Exception as e:
                conn.rollback()
                print(f"处理微信支付回调失败: {e}")
            finally:
                conn.close()
        
        # 微信要求返回XML格式
        return """<xml>
    <return_code><![CDATA[SUCCESS]]></return_code>
    <return_msg><![CDATA[OK]]></return_msg>
</xml>"""
        
    except Exception as e:
        print(f"微信支付回调处理异常: {e}")
        return """<xml>
    <return_code><![CDATA[FAIL]]></return_code>
    <return_msg><![CDATA[处理失败]]></return_msg>
</xml>"""

@router.get("/order/{order_no}/qrcode")
async def get_payment_qrcode(order_no: str):
    """获取支付二维码（用于微信支付）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM orders WHERE order_no = ? AND payment_status = 'pending'
        """, (order_no,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="订单不存在或已支付")
        
        order = dict(row)
        
        if order['payment_method'] == 'wechat':
            # 重新生成微信支付二维码
            payment_data = {
                'order_no': order_no,
                'amount': order['amount'],
                'subject': f'中医处方费用 - 订单{order_no}',
                'body': f'处方ID: {order["prescription_id"]}'
            }
            
            payment_result = payment_manager.create_payment_order('wechat', payment_data)
            
            if payment_result['success']:
                return {
                    "success": True,
                    "qr_code_url": payment_result['code_url'],
                    "order_no": order_no,
                    "amount": order['amount']
                }
            else:
                raise HTTPException(status_code=500, detail="生成二维码失败")
        else:
            raise HTTPException(status_code=400, detail="该支付方式不支持二维码")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取支付二维码失败: {e}")
    finally:
        conn.close()

@router.get("/statistics")
async def get_payment_statistics():
    """获取支付统计信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 总体统计
        cursor.execute("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(CASE WHEN payment_status = 'paid' THEN 1 ELSE 0 END) as paid_orders,
                SUM(CASE WHEN payment_status = 'paid' THEN amount ELSE 0 END) as total_revenue,
                SUM(CASE WHEN payment_status = 'pending' THEN 1 ELSE 0 END) as pending_orders
            FROM orders
        """)
        
        stats = cursor.fetchone()
        
        # 今日统计
        cursor.execute("""
            SELECT 
                COUNT(*) as today_orders,
                SUM(CASE WHEN payment_status = 'paid' THEN amount ELSE 0 END) as today_revenue
            FROM orders 
            WHERE DATE(created_at) = DATE('now')
        """)
        
        today_stats = cursor.fetchone()
        
        # 支付方式统计
        cursor.execute("""
            SELECT 
                payment_method,
                COUNT(*) as count,
                SUM(CASE WHEN payment_status = 'paid' THEN amount ELSE 0 END) as revenue
            FROM orders 
            WHERE payment_status = 'paid'
            GROUP BY payment_method
        """)
        
        payment_method_stats = [dict(row) for row in cursor.fetchall()]
        
        return {
            "success": True,
            "statistics": {
                "total_orders": stats['total_orders'] if stats else 0,
                "paid_orders": stats['paid_orders'] if stats else 0,
                "total_revenue": float(stats['total_revenue'] or 0),
                "pending_orders": stats['pending_orders'] if stats else 0,
                "today_orders": today_stats['today_orders'] if today_stats else 0,
                "today_revenue": float(today_stats['today_revenue'] or 0),
                "payment_methods": payment_method_stats
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取支付统计失败: {e}")
    finally:
        conn.close()