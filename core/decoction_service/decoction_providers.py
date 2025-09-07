"""
代煎服务提供商抽象接口和具体实现
支持多家代煎公司的接入
"""
import json
import uuid
import hashlib
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import requests

class DecoctionOrderStatus:
    """代煎订单状态常量"""
    SUBMITTED = "submitted"      # 已提交
    CONFIRMED = "confirmed"      # 已确认
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 煎制完成
    SHIPPED = "shipped"          # 已发货
    DELIVERED = "delivered"      # 已送达

class DecoctionProvider(ABC):
    """代煎服务提供商抽象基类"""
    
    def __init__(self, provider_id: str, provider_name: str, config: Dict[str, Any]):
        self.provider_id = provider_id
        self.provider_name = provider_name
        self.config = config
    
    @abstractmethod
    async def submit_prescription(self, prescription_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        提交处方到代煎公司
        
        Args:
            prescription_data: 处方数据，包含：
                - prescription_id: 处方ID
                - prescription_content: 处方内容
                - patient_info: 患者信息
                - shipping_info: 配送信息
        
        Returns:
            处理结果，包含：
                - success: 是否成功
                - order_no: 代煎订单号
                - estimated_delivery: 预计送达时间
                - message: 返回消息
        """
        pass
    
    @abstractmethod
    async def query_order_status(self, order_no: str) -> Dict[str, Any]:
        """
        查询代煎订单状态
        
        Args:
            order_no: 代煎订单号
            
        Returns:
            订单状态信息
        """
        pass
    
    @abstractmethod
    async def get_tracking_info(self, tracking_no: str) -> Dict[str, Any]:
        """
        获取物流跟踪信息
        
        Args:
            tracking_no: 物流单号
            
        Returns:
            物流信息
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_no: str, reason: str) -> Dict[str, Any]:
        """
        取消代煎订单
        
        Args:
            order_no: 代煎订单号
            reason: 取消原因
            
        Returns:
            取消结果
        """
        pass

class DefaultDecoctionProvider(DecoctionProvider):
    """默认代煎服务提供商（模拟实现）"""
    
    def __init__(self):
        super().__init__(
            provider_id="default",
            provider_name="默认代煎服务",
            config={}
        )
        # 模拟订单存储
        self._orders = {}
    
    async def submit_prescription(self, prescription_data: Dict[str, Any]) -> Dict[str, Any]:
        """提交处方（模拟实现）"""
        try:
            # 生成代煎订单号
            order_no = f"DC{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:6]}"
            
            # 模拟处理延迟
            import asyncio
            await asyncio.sleep(0.1)
            
            # 预计1-2天送达
            estimated_delivery = datetime.now() + timedelta(days=2)
            
            # 存储订单信息
            self._orders[order_no] = {
                'order_no': order_no,
                'prescription_id': prescription_data.get('prescription_id'),
                'prescription_content': prescription_data.get('prescription_content'),
                'patient_info': prescription_data.get('patient_info', {}),
                'shipping_info': prescription_data.get('shipping_info', {}),
                'status': DecoctionOrderStatus.SUBMITTED,
                'created_at': datetime.now().isoformat(),
                'estimated_delivery': estimated_delivery.isoformat(),
                'tracking_no': None
            }
            
            return {
                'success': True,
                'order_no': order_no,
                'estimated_delivery': estimated_delivery.isoformat(),
                'message': '处方提交成功，预计2天内完成煎制并发货'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': '提交处方失败'
            }
    
    async def query_order_status(self, order_no: str) -> Dict[str, Any]:
        """查询订单状态（模拟实现）"""
        try:
            order = self._orders.get(order_no)
            if not order:
                return {
                    'success': False,
                    'error': 'Order not found',
                    'message': '订单不存在'
                }
            
            # 模拟状态演进
            created_time = datetime.fromisoformat(order['created_at'])
            now = datetime.now()
            hours_passed = (now - created_time).total_seconds() / 3600
            
            if hours_passed > 48:  # 48小时后
                order['status'] = DecoctionOrderStatus.DELIVERED
                order['actual_delivery'] = now.isoformat()
            elif hours_passed > 24:  # 24小时后
                order['status'] = DecoctionOrderStatus.SHIPPED
                order['tracking_no'] = f"SF{str(uuid.uuid4())[:10]}"
            elif hours_passed > 4:  # 4小时后
                order['status'] = DecoctionOrderStatus.PROCESSING
            elif hours_passed > 1:  # 1小时后
                order['status'] = DecoctionOrderStatus.CONFIRMED
            
            return {
                'success': True,
                'order': order
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': '查询订单状态失败'
            }
    
    async def get_tracking_info(self, tracking_no: str) -> Dict[str, Any]:
        """获取物流信息（模拟实现）"""
        try:
            # 模拟物流信息
            tracking_info = {
                'tracking_no': tracking_no,
                'status': '运输中',
                'current_location': '北京分拣中心',
                'traces': [
                    {
                        'time': '2024-08-26 14:00:00',
                        'location': '北京代煎中心',
                        'description': '代煎完成，准备发货'
                    },
                    {
                        'time': '2024-08-26 16:30:00',
                        'location': '北京转运中心',
                        'description': '快件已发出'
                    },
                    {
                        'time': '2024-08-27 08:00:00',
                        'location': '目标城市分拣中心',
                        'description': '快件到达处理中心'
                    }
                ]
            }
            
            return {
                'success': True,
                'tracking_info': tracking_info
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': '获取物流信息失败'
            }
    
    async def cancel_order(self, order_no: str, reason: str) -> Dict[str, Any]:
        """取消订单（模拟实现）"""
        try:
            order = self._orders.get(order_no)
            if not order:
                return {
                    'success': False,
                    'error': 'Order not found',
                    'message': '订单不存在'
                }
            
            # 只有未开始处理的订单才能取消
            if order['status'] in [DecoctionOrderStatus.PROCESSING, DecoctionOrderStatus.COMPLETED, DecoctionOrderStatus.SHIPPED]:
                return {
                    'success': False,
                    'error': 'Cannot cancel',
                    'message': '订单已开始处理，无法取消'
                }
            
            order['status'] = 'cancelled'
            order['cancel_reason'] = reason
            order['cancelled_at'] = datetime.now().isoformat()
            
            return {
                'success': True,
                'message': '订单取消成功'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': '取消订单失败'
            }

class KangmeiDecoctionProvider(DecoctionProvider):
    """康美药业代煎服务提供商（接口示例）"""
    
    def __init__(self):
        super().__init__(
            provider_id="kangmei",
            provider_name="康美药业代煎",
            config={
                'api_url': 'https://api.kangmei.com/decoction',
                'app_key': 'your_app_key',
                'app_secret': 'your_app_secret',
                'timeout': 30
            }
        )
    
    def _generate_signature(self, params: Dict[str, Any], timestamp: str) -> str:
        """生成API签名"""
        sorted_params = sorted(params.items())
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
        sign_string = f"{query_string}&timestamp={timestamp}&key={self.config['app_secret']}"
        return hashlib.md5(sign_string.encode()).hexdigest().upper()
    
    async def submit_prescription(self, prescription_data: Dict[str, Any]) -> Dict[str, Any]:
        """提交处方到康美药业（示例实现）"""
        try:
            timestamp = str(int(time.time()))
            
            api_params = {
                'app_key': self.config['app_key'],
                'method': 'prescription.submit',
                'prescription_id': prescription_data.get('prescription_id'),
                'prescription_content': prescription_data.get('prescription_content'),
                'patient_name': prescription_data.get('patient_info', {}).get('name'),
                'patient_phone': prescription_data.get('patient_info', {}).get('phone'),
                'shipping_address': prescription_data.get('shipping_info', {}).get('address')
            }
            
            signature = self._generate_signature(api_params, timestamp)
            
            request_data = {
                **api_params,
                'timestamp': timestamp,
                'sign': signature
            }
            
            # 实际项目中这里会调用康美药业的API
            # response = requests.post(self.config['api_url'], json=request_data, timeout=self.config['timeout'])
            
            # 模拟返回结果
            return {
                'success': True,
                'order_no': f"KM{int(time.time())}{str(uuid.uuid4())[:6]}",
                'estimated_delivery': (datetime.now() + timedelta(days=1)).isoformat(),
                'message': '处方已提交康美药业，预计1天内完成煎制'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': '康美药业API调用失败'
            }
    
    async def query_order_status(self, order_no: str) -> Dict[str, Any]:
        """查询康美药业订单状态"""
        # 实际实现会调用康美药业的查询接口
        return await DefaultDecoctionProvider().query_order_status(order_no)
    
    async def get_tracking_info(self, tracking_no: str) -> Dict[str, Any]:
        """获取康美药业物流信息"""
        # 实际实现会调用康美药业的物流接口
        return await DefaultDecoctionProvider().get_tracking_info(tracking_no)
    
    async def cancel_order(self, order_no: str, reason: str) -> Dict[str, Any]:
        """取消康美药业订单"""
        # 实际实现会调用康美药业的取消接口
        return await DefaultDecoctionProvider().cancel_order(order_no, reason)

class TongrentangDecoctionProvider(DecoctionProvider):
    """同仁堂代煎服务提供商（接口示例）"""
    
    def __init__(self):
        super().__init__(
            provider_id="tongrentang",
            provider_name="同仁堂代煎",
            config={
                'api_url': 'https://api.tongrentang.com/decoction',
                'merchant_id': 'your_merchant_id',
                'api_key': 'your_api_key',
                'timeout': 30
            }
        )
    
    async def submit_prescription(self, prescription_data: Dict[str, Any]) -> Dict[str, Any]:
        """提交处方到同仁堂（示例实现）"""
        # 类似康美药业的实现，调用同仁堂的API
        return {
            'success': True,
            'order_no': f"TRT{int(time.time())}{str(uuid.uuid4())[:6]}",
            'estimated_delivery': (datetime.now() + timedelta(days=2)).isoformat(),
            'message': '处方已提交同仁堂，预计2天内完成煎制'
        }
    
    async def query_order_status(self, order_no: str) -> Dict[str, Any]:
        return await DefaultDecoctionProvider().query_order_status(order_no)
    
    async def get_tracking_info(self, tracking_no: str) -> Dict[str, Any]:
        return await DefaultDecoctionProvider().get_tracking_info(tracking_no)
    
    async def cancel_order(self, order_no: str, reason: str) -> Dict[str, Any]:
        return await DefaultDecoctionProvider().cancel_order(order_no, reason)

class DecoctionServiceManager:
    """代煎服务管理器"""
    
    def __init__(self):
        self.providers = {}
        self._register_providers()
    
    def _register_providers(self):
        """注册所有可用的代煎服务提供商"""
        self.providers['default'] = DefaultDecoctionProvider()
        self.providers['kangmei'] = KangmeiDecoctionProvider()
        self.providers['tongrentang'] = TongrentangDecoctionProvider()
    
    def get_provider(self, provider_id: str = 'default') -> DecoctionProvider:
        """获取指定的代煎服务提供商"""
        return self.providers.get(provider_id, self.providers['default'])
    
    def list_providers(self) -> List[Dict[str, str]]:
        """列出所有可用的代煎服务提供商"""
        return [
            {
                'provider_id': provider.provider_id,
                'provider_name': provider.provider_name
            }
            for provider in self.providers.values()
        ]
    
    async def submit_prescription(self, prescription_data: Dict[str, Any], 
                                provider_id: str = 'default') -> Dict[str, Any]:
        """提交处方到指定的代煎服务商"""
        provider = self.get_provider(provider_id)
        result = await provider.submit_prescription(prescription_data)
        
        # 在结果中添加提供商信息
        if result.get('success'):
            result['provider_id'] = provider_id
            result['provider_name'] = provider.provider_name
        
        return result
    
    async def query_order_status(self, order_no: str, provider_id: str = 'default') -> Dict[str, Any]:
        """查询代煎订单状态"""
        provider = self.get_provider(provider_id)
        return await provider.query_order_status(order_no)
    
    async def get_tracking_info(self, tracking_no: str, provider_id: str = 'default') -> Dict[str, Any]:
        """获取物流跟踪信息"""
        provider = self.get_provider(provider_id)
        return await provider.get_tracking_info(tracking_no)
    
    async def cancel_order(self, order_no: str, reason: str, provider_id: str = 'default') -> Dict[str, Any]:
        """取消代煎订单"""
        provider = self.get_provider(provider_id)
        return await provider.cancel_order(order_no, reason)

# 全局代煎服务管理器实例
decoction_service_manager = DecoctionServiceManager()