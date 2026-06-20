"""
支付集成管理模块
支持支付宝和微信支付
"""
import json
import hashlib
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import requests
from urllib.parse import urlencode
import hmac
import base64

class PaymentConfig:
    """支付配置"""
    
    # 支付宝配置
    ALIPAY_CONFIG = {
        'app_id': '2021000000000000',  # 替换为实际的app_id
        'merchant_private_key': """-----BEGIN RSA PRIVATE KEY-----
your_private_key_here
-----END RSA PRIVATE KEY-----""",  # 替换为实际私钥
        'alipay_public_key': """-----BEGIN PUBLIC KEY-----
alipay_public_key_here
-----END PUBLIC KEY-----""",  # 替换为支付宝公钥
        'sign_type': 'RSA2',
        'charset': 'utf-8',
        'version': '1.0',
        'gateway_url': 'https://openapi.alipay.com/gateway.do',  # 生产环境
        # 'gateway_url': 'https://openapi.alipaydev.com/gateway.do',  # 沙箱环境
        'notify_url': 'https://mxh0510.cn/api/payment/alipay/notify',
        'return_url': 'https://mxh0510.cn/payment/success'
    }
    
    # 微信支付配置
    WECHAT_CONFIG = {
        'app_id': 'your_app_id',  # 替换为实际的app_id
        'mch_id': 'your_merchant_id',  # 替换为实际商户号
        'api_key': 'your_api_key',  # 替换为实际API密钥
        'notify_url': 'https://mxh0510.cn/api/payment/wechat/notify',
        'trade_type': 'NATIVE',  # 扫码支付
        'api_url': 'https://api.mch.weixin.qq.com/pay/unifiedorder',
        'query_url': 'https://api.mch.weixin.qq.com/pay/orderquery'
    }

class AlipayManager:
    """支付宝支付管理器"""
    
    def __init__(self, config: dict = None):
        self.config = config or PaymentConfig.ALIPAY_CONFIG
    
    def _generate_sign(self, params: dict) -> str:
        """生成签名"""
        # 排序参数
        sorted_params = sorted([f"{k}={v}" for k, v in params.items() if v])
        sign_string = "&".join(sorted_params)
        
        # 这里应该使用RSA私钥签名，简化演示
        # 实际项目中需要使用 Crypto 库进行RSA签名
        import hashlib
        return hashlib.md5(sign_string.encode()).hexdigest()
    
    def create_order(self, order_data: dict) -> dict:
        """创建支付宝订单"""
        try:
            biz_content = {
                'out_trade_no': order_data['order_no'],
                'total_amount': str(order_data['amount']),
                'subject': order_data.get('subject', '中医处方药费'),
                'body': order_data.get('body', ''),
                'product_code': 'FAST_INSTANT_TRADE_PAY'
            }
            
            params = {
                'app_id': self.config['app_id'],
                'method': 'alipay.trade.page.pay',
                'charset': self.config['charset'],
                'sign_type': self.config['sign_type'],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'version': self.config['version'],
                'notify_url': self.config['notify_url'],
                'return_url': self.config['return_url'],
                'biz_content': json.dumps(biz_content, separators=(',', ':'))
            }
            
            # 生成签名
            sign = self._generate_sign(params)
            params['sign'] = sign
            
            # 构建支付URL
            payment_url = f"{self.config['gateway_url']}?{urlencode(params)}"
            
            return {
                'success': True,
                'payment_url': payment_url,
                'order_no': order_data['order_no']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_notify(self, params: dict) -> bool:
        """验证支付宝回调"""
        try:
            # 提取签名
            sign = params.pop('sign', '')
            sign_type = params.pop('sign_type', '')
            
            # 验证签名（简化版本）
            # 实际项目中需要使用支付宝公钥验证RSA签名
            expected_sign = self._generate_sign(params)
            return sign == expected_sign
            
        except Exception as e:
            print(f"支付宝回调验证失败: {e}")
            return False

class WechatPayManager:
    """微信支付管理器"""
    
    def __init__(self, config: dict = None):
        self.config = config or PaymentConfig.WECHAT_CONFIG
    
    def _generate_sign(self, params: dict) -> str:
        """生成微信支付签名"""
        # 排序参数
        sorted_params = sorted([f"{k}={v}" for k, v in params.items() if v])
        sign_string = "&".join(sorted_params) + f"&key={self.config['api_key']}"
        
        return hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()
    
    def _dict_to_xml(self, params: dict) -> str:
        """字典转XML"""
        xml_parts = ['<xml>']
        for k, v in params.items():
            xml_parts.append(f'<{k}><![CDATA[{v}]]></{k}>')
        xml_parts.append('</xml>')
        return ''.join(xml_parts)
    
    def _xml_to_dict(self, xml_string: str) -> dict:
        """XML转字典（简化版本）"""
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_string)
        return {child.tag: child.text for child in root}
    
    def create_order(self, order_data: dict) -> dict:
        """创建微信支付订单"""
        try:
            params = {
                'appid': self.config['app_id'],
                'mch_id': self.config['mch_id'],
                'nonce_str': str(uuid.uuid4()).replace('-', ''),
                'body': order_data.get('body', '中医处方药费'),
                'out_trade_no': order_data['order_no'],
                'total_fee': str(int(float(order_data['amount']) * 100)),  # 分为单位
                'spbill_create_ip': '127.0.0.1',
                'notify_url': self.config['notify_url'],
                'trade_type': self.config['trade_type']
            }
            
            # 生成签名
            params['sign'] = self._generate_sign(params)
            
            # 发送请求
            xml_data = self._dict_to_xml(params)
            response = requests.post(self.config['api_url'], data=xml_data)
            
            if response.status_code == 200:
                result = self._xml_to_dict(response.text)
                
                if result.get('return_code') == 'SUCCESS' and result.get('result_code') == 'SUCCESS':
                    return {
                        'success': True,
                        'code_url': result.get('code_url'),  # 二维码URL
                        'prepay_id': result.get('prepay_id'),
                        'order_no': order_data['order_no']
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('return_msg', '创建订单失败')
                    }
            else:
                return {
                    'success': False,
                    'error': '网络请求失败'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_notify(self, params: dict) -> bool:
        """验证微信支付回调"""
        try:
            # 提取签名
            sign = params.pop('sign', '')
            
            # 验证签名
            expected_sign = self._generate_sign(params)
            return sign == expected_sign
            
        except Exception as e:
            print(f"微信支付回调验证失败: {e}")
            return False

class PaymentManager:
    """统一支付管理器"""
    
    def __init__(self):
        self.alipay = AlipayManager()
        self.wechat = WechatPayManager()
    
    def create_payment_order(self, payment_method: str, order_data: dict) -> dict:
        """创建支付订单"""
        if payment_method == 'alipay':
            return self.alipay.create_order(order_data)
        elif payment_method == 'wechat':
            return self.wechat.create_order(order_data)
        else:
            return {
                'success': False,
                'error': '不支持的支付方式'
            }
    
    def verify_payment_notify(self, payment_method: str, params: dict) -> bool:
        """验证支付回调"""
        if payment_method == 'alipay':
            return self.alipay.verify_notify(params)
        elif payment_method == 'wechat':
            return self.wechat.verify_notify(params)
        else:
            return False

# 全局支付管理器实例
payment_manager = PaymentManager()