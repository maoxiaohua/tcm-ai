"""
代煎服务相关API路由
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
from datetime import datetime

from core.decoction_service.decoction_providers import (
    decoction_service_manager, 
    DecoctionOrderStatus
)

router = APIRouter(prefix="/api/decoction", tags=["代煎服务"])

class CreateDecoctionOrderRequest(BaseModel):
    """创建代煎订单请求"""
    order_id: int
    provider_id: str = "default"
    notes: Optional[str] = None

class UpdateOrderStatusRequest(BaseModel):
    """更新代煎订单状态请求"""
    status: str
    tracking_no: Optional[str] = None
    provider_notes: Optional[str] = None

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

@router.post("/create-order")
async def create_decoction_order(request: CreateDecoctionOrderRequest):
    """创建代煎订单"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取支付订单信息
        cursor.execute("""
            SELECT o.*, p.ai_prescription, p.doctor_prescription, p.patient_id
            FROM orders o
            JOIN prescriptions p ON o.prescription_id = p.id
            WHERE o.id = ? AND o.payment_status = 'paid' AND o.decoction_required = 1
        """, (request.order_id,))
        
        order = cursor.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在或不符合代煎条件")
        
        # 检查是否已经创建过代煎订单
        cursor.execute("""
            SELECT id FROM decoction_orders WHERE order_id = ?
        """, (request.order_id,))
        
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="该订单已创建代煎订单")
        
        # 准备提交给代煎服务商的数据
        prescription_content = order['doctor_prescription'] or order['ai_prescription']
        
        prescription_data = {
            'prescription_id': order['prescription_id'],
            'prescription_content': prescription_content,
            'patient_info': {
                'name': order['shipping_name'],
                'phone': order['shipping_phone']
            },
            'shipping_info': {
                'name': order['shipping_name'],
                'phone': order['shipping_phone'],
                'address': order['shipping_address']
            }
        }
        
        # 提交到代煎服务商
        result = await decoction_service_manager.submit_prescription(
            prescription_data, 
            request.provider_id
        )
        
        if result['success']:
            # 在数据库中创建代煎订单记录
            cursor.execute("""
                INSERT INTO decoction_orders (
                    order_id, provider_id, provider_name, decoction_order_no,
                    status, estimated_delivery, provider_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                request.order_id,
                request.provider_id,
                result.get('provider_name', ''),
                result.get('order_no', ''),
                DecoctionOrderStatus.SUBMITTED,
                result.get('estimated_delivery'),
                request.notes
            ))
            
            decoction_order_id = cursor.lastrowid
            
            # 更新处方状态为已提交代煎
            cursor.execute("""
                UPDATE prescriptions 
                SET status = 'decoction_submitted'
                WHERE id = ?
            """, (order['prescription_id'],))
            
            conn.commit()
            
            return {
                "success": True,
                "message": "代煎订单创建成功",
                "decoction_order_id": decoction_order_id,
                "decoction_order_no": result.get('order_no'),
                "estimated_delivery": result.get('estimated_delivery'),
                "provider_name": result.get('provider_name')
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"代煎服务提交失败: {result.get('message', '未知错误')}"
            )
            
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"创建代煎订单失败: {e}")
    finally:
        conn.close()

@router.get("/order/{decoction_order_id}")
async def get_decoction_order(decoction_order_id: int):
    """获取代煎订单详情"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT d.*, o.order_no as payment_order_no, o.shipping_name, 
                   o.shipping_phone, o.shipping_address,
                   p.ai_prescription, p.doctor_prescription
            FROM decoction_orders d
            JOIN orders o ON d.order_id = o.id
            JOIN prescriptions p ON o.prescription_id = p.id
            WHERE d.id = ?
        """, (decoction_order_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="代煎订单不存在")
        
        order = dict(row)
        
        # 如果有代煎订单号，查询最新状态
        if order['decoction_order_no'] and order['provider_id']:
            status_result = await decoction_service_manager.query_order_status(
                order['decoction_order_no'], 
                order['provider_id']
            )
            
            if status_result['success']:
                order['latest_status'] = status_result.get('order', {})
        
        return {
            "success": True,
            "decoction_order": order
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取代煎订单详情失败: {e}")
    finally:
        conn.close()

@router.get("/order/{decoction_order_id}/tracking")
async def get_decoction_tracking(decoction_order_id: int):
    """获取代煎订单物流信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM decoction_orders WHERE id = ?
        """, (decoction_order_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="代煎订单不存在")
        
        order = dict(row)
        
        if not order['tracking_no']:
            return {
                "success": True,
                "message": "暂无物流信息",
                "tracking_info": None
            }
        
        # 查询物流信息
        tracking_result = await decoction_service_manager.get_tracking_info(
            order['tracking_no'], 
            order['provider_id']
        )
        
        return {
            "success": True,
            "tracking_info": tracking_result.get('tracking_info') if tracking_result['success'] else None,
            "message": tracking_result.get('message', '')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取物流信息失败: {e}")
    finally:
        conn.close()

@router.put("/order/{decoction_order_id}/status")
async def update_decoction_order_status(
    decoction_order_id: int, 
    request: UpdateOrderStatusRequest
):
    """更新代煎订单状态（通常由代煎公司回调使用）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查订单是否存在
        cursor.execute("""
            SELECT * FROM decoction_orders WHERE id = ?
        """, (decoction_order_id,))
        
        order = cursor.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="代煎订单不存在")
        
        # 更新订单状态
        update_fields = ["status = ?", "updated_at = datetime('now')"]
        update_values = [request.status]
        
        if request.tracking_no:
            update_fields.append("tracking_no = ?")
            update_values.append(request.tracking_no)
        
        if request.provider_notes:
            update_fields.append("provider_notes = ?")
            update_values.append(request.provider_notes)
        
        # 根据状态设置相应的时间字段
        if request.status == DecoctionOrderStatus.DELIVERED:
            update_fields.append("actual_delivery_date = datetime('now')")
        
        update_sql = f"UPDATE decoction_orders SET {', '.join(update_fields)} WHERE id = ?"
        update_values.append(decoction_order_id)
        
        cursor.execute(update_sql, update_values)
        
        # 如果代煎订单已送达，更新处方状态为已完成
        if request.status == DecoctionOrderStatus.DELIVERED:
            cursor.execute("""
                UPDATE prescriptions 
                SET status = 'completed'
                WHERE id = (
                    SELECT p.id FROM prescriptions p
                    JOIN orders o ON p.id = o.prescription_id
                    WHERE o.id = ?
                )
            """, (order['order_id'],))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "代煎订单状态更新成功"
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"更新代煎订单状态失败: {e}")
    finally:
        conn.close()

@router.post("/webhook")
async def decoction_webhook_handler(request_data: Dict[str, Any]):
    """代煎公司状态回调处理"""
    try:
        # 验证回调来源（实际项目中需要验证签名）
        provider_id = request_data.get('provider_id')
        order_no = request_data.get('order_no')
        status = request_data.get('status')
        tracking_no = request_data.get('tracking_no')
        
        if not all([provider_id, order_no, status]):
            raise HTTPException(status_code=400, detail="缺少必要参数")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 根据代煎订单号查找订单
            cursor.execute("""
                SELECT id FROM decoction_orders 
                WHERE decoction_order_no = ? AND provider_id = ?
            """, (order_no, provider_id))
            
            row = cursor.fetchone()
            if not row:
                return {
                    "success": False,
                    "message": "代煎订单不存在"
                }
            
            decoction_order_id = row['id']
            
            # 更新订单状态
            await update_decoction_order_status(
                decoction_order_id,
                UpdateOrderStatusRequest(
                    status=status,
                    tracking_no=tracking_no,
                    provider_notes=request_data.get('notes')
                )
            )
            
            return {
                "success": True,
                "message": "状态更新成功"
            }
            
        finally:
            conn.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理回调失败: {e}")

@router.get("/providers")
async def list_decoction_providers():
    """获取所有可用的代煎服务提供商"""
    try:
        providers = decoction_service_manager.list_providers()
        
        return {
            "success": True,
            "providers": providers
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取代煎服务商列表失败: {e}")

@router.get("/statistics")
async def get_decoction_statistics():
    """获取代煎服务统计信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 总体统计
        cursor.execute("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) as delivered_orders,
                SUM(CASE WHEN status IN ('processing', 'shipped') THEN 1 ELSE 0 END) as processing_orders,
                COUNT(DISTINCT provider_id) as active_providers
            FROM decoction_orders
        """)
        
        stats = cursor.fetchone()
        
        # 按服务商统计
        cursor.execute("""
            SELECT 
                provider_name,
                COUNT(*) as order_count,
                SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) as completed_count
            FROM decoction_orders 
            GROUP BY provider_id, provider_name
        """)
        
        provider_stats = [dict(row) for row in cursor.fetchall()]
        
        # 今日统计
        cursor.execute("""
            SELECT COUNT(*) as today_orders
            FROM decoction_orders 
            WHERE DATE(created_at) = DATE('now')
        """)
        
        today_stats = cursor.fetchone()
        
        return {
            "success": True,
            "statistics": {
                "total_orders": stats['total_orders'] if stats else 0,
                "delivered_orders": stats['delivered_orders'] if stats else 0,
                "processing_orders": stats['processing_orders'] if stats else 0,
                "active_providers": stats['active_providers'] if stats else 0,
                "today_orders": today_stats['today_orders'] if today_stats else 0,
                "provider_stats": provider_stats
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取代煎统计失败: {e}")
    finally:
        conn.close()

@router.post("/auto-process")
async def auto_process_paid_orders(background_tasks: BackgroundTasks):
    """自动处理已支付且需要代煎的订单"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查找已支付且需要代煎但未提交的订单
        cursor.execute("""
            SELECT o.id, o.prescription_id, o.decoction_required
            FROM orders o
            JOIN prescriptions p ON o.prescription_id = p.id
            WHERE o.payment_status = 'paid' 
              AND o.decoction_required = 1
              AND p.status = 'paid'
              AND NOT EXISTS (
                  SELECT 1 FROM decoction_orders d WHERE d.order_id = o.id
              )
        """)
        
        orders = cursor.fetchall()
        processed_count = 0
        
        for order in orders:
            try:
                # 创建代煎订单
                await create_decoction_order(
                    CreateDecoctionOrderRequest(
                        order_id=order['id'],
                        provider_id='default',
                        notes='自动批量处理'
                    )
                )
                processed_count += 1
                
            except Exception as e:
                print(f"自动处理订单 {order['id']} 失败: {e}")
                continue
        
        return {
            "success": True,
            "message": f"自动处理完成，成功处理 {processed_count} 个订单",
            "processed_count": processed_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"自动处理失败: {e}")
    finally:
        conn.close()