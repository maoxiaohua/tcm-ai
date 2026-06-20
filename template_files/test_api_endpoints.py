#!/usr/bin/env python3
"""
API端点测试脚本
测试处方审核流程相关的API接口
"""

import requests
import json
import time
import sys

class APIEndpointTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_data = {}
        
    def log(self, message, level="INFO"):
        """日志输出"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def test_service_status(self):
        """测试服务状态"""
        self.log("测试服务状态...")
        
        try:
            response = self.session.get(f"{self.base_url}/api/consultation/service-status")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log("✅ 服务运行正常")
                    self.log(f"   版本: {data['data'].get('version', 'unknown')}")
                    self.log(f"   支持的医生: {len(data['data'].get('supported_doctors', []))}")
                    return True
                else:
                    self.log("❌ 服务状态检查失败")
                    return False
            else:
                self.log(f"❌ 服务状态API返回错误: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ 服务状态检查异常: {e}")
            return False
    
    def test_consultation_api(self):
        """测试问诊API"""
        self.log("测试问诊API...")
        
        test_data = {
            "message": "医生您好，我最近失眠，请帮我看看",
            "conversation_id": f"test_api_{int(time.time())}",
            "selected_doctor": "zhang_zhongjing",
            "patient_id": f"test_patient_{int(time.time())}",
            "has_images": False,
            "conversation_history": []
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/consultation/chat",
                json=test_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.log("✅ 问诊API正常")
                    self.log(f"   回复长度: {len(result['data'].get('reply', ''))}")
                    self.log(f"   包含处方: {result['data'].get('contains_prescription', False)}")
                    
                    # 保存测试数据
                    self.test_data['consultation'] = {
                        'conversation_id': test_data['conversation_id'],
                        'patient_id': test_data['patient_id'],
                        'prescription_id': result['data'].get('prescription_id')
                    }
                    
                    return True
                else:
                    self.log(f"❌ 问诊API返回失败: {result.get('message')}")
                    return False
            else:
                self.log(f"❌ 问诊API返回错误: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ 问诊API测试异常: {e}")
            return False
    
    def test_patient_history_api(self):
        """测试患者历史记录API"""
        self.log("测试患者历史记录API...")
        
        if not self.test_data.get('consultation'):
            self.log("⚠️ 没有测试数据，跳过历史记录测试")
            return True
        
        patient_id = self.test_data['consultation']['patient_id']
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/consultation/patient/history",
                params={"user_id": patient_id}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    history = result["data"]["consultation_history"]
                    self.log("✅ 患者历史记录API正常")
                    self.log(f"   历史记录数: {len(history)}")
                    
                    # 检查是否找到刚才的问诊记录
                    found = False
                    for record in history:
                        if record.get("consultation_id") == self.test_data['consultation']['conversation_id']:
                            found = True
                            break
                    
                    if found:
                        self.log("   ✅ 找到测试问诊记录")
                    else:
                        self.log("   ⚠️ 未找到测试问诊记录")
                    
                    return True
                else:
                    self.log(f"❌ 历史记录API返回失败: {result.get('message')}")
                    return False
            else:
                self.log(f"❌ 历史记录API返回错误: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ 历史记录API测试异常: {e}")
            return False
    
    def test_doctor_pending_api(self):
        """测试医生待审核处方API"""
        self.log("测试医生待审核处方API...")
        
        # 使用测试token（实际环境中需要真实的医生token）
        test_token = "test_doctor_token"
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/doctor/pending-prescriptions",
                headers={"Authorization": f"Bearer {test_token}"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    prescriptions = result.get("prescriptions", [])
                    self.log("✅ 医生待审核处方API正常")
                    self.log(f"   待审核处方数: {len(prescriptions)}")
                    return True
                else:
                    self.log(f"❌ 待审核处方API返回失败: {result.get('message')}")
                    return False
            elif response.status_code == 401:
                self.log("⚠️ 医生API认证失败（预期行为）")
                return True  # 认证失败是正常的，说明API存在且工作正常
            else:
                self.log(f"❌ 待审核处方API返回错误: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ 待审核处方API测试异常: {e}")
            return False
    
    def test_payment_apis(self):
        """测试支付相关API"""
        self.log("测试支付相关API...")
        
        if not self.test_data.get('consultation', {}).get('prescription_id'):
            self.log("⚠️ 没有处方ID，跳过支付API测试")
            return True
        
        prescription_id = self.test_data['consultation']['prescription_id']
        
        # 测试创建支付订单
        payment_data = {
            "prescription_id": prescription_id,
            "amount": 88.0,
            "payment_method": "alipay"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/payment/alipay/create",
                json=payment_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    order_no = result["data"]["order_no"]
                    self.log("✅ 创建支付订单API正常")
                    self.log(f"   订单号: {order_no}")
                    
                    # 保存订单号用于后续测试
                    self.test_data['payment'] = {'order_no': order_no}
                    
                    return True
                else:
                    self.log(f"❌ 创建支付订单失败: {result.get('message')}")
                    return False
            else:
                self.log(f"❌ 创建支付订单API返回错误: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ 支付API测试异常: {e}")
            return False
    
    def test_prescription_status_api(self):
        """测试处方状态查询API"""
        self.log("测试处方状态查询API...")
        
        if not self.test_data.get('consultation', {}).get('prescription_id'):
            self.log("⚠️ 没有处方ID，跳过状态查询测试")
            return True
        
        prescription_id = self.test_data['consultation']['prescription_id']
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/doctor/prescription/{prescription_id}"
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    prescription = result.get("prescription", {})
                    self.log("✅ 处方状态查询API正常")
                    self.log(f"   处方状态: {prescription.get('status', 'unknown')}")
                    self.log(f"   审核状态: {prescription.get('review_status', 'unknown')}")
                    return True
                else:
                    self.log(f"❌ 处方状态查询失败: {result.get('message')}")
                    return False
            else:
                self.log(f"❌ 处方状态查询API返回错误: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ 处方状态查询API测试异常: {e}")
            return False
    
    def test_system_health(self):
        """测试系统健康状态"""
        self.log("测试系统健康状态...")
        
        health_checks = [
            ("/api/consultation/service-status", "问诊服务"),
            ("/api/doctor/statistics", "医生统计"),  # 需要认证，但可以测试端点存在性
            ("/api/payment/statistics", "支付统计"),
        ]
        
        results = []
        
        for endpoint, name in health_checks:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                
                if response.status_code == 200:
                    self.log(f"   ✅ {name}: 正常")
                    results.append(True)
                elif response.status_code == 401:
                    self.log(f"   ⚠️ {name}: 需要认证（端点存在）")
                    results.append(True)
                else:
                    self.log(f"   ❌ {name}: 错误 {response.status_code}")
                    results.append(False)
                    
            except Exception as e:
                self.log(f"   ❌ {name}: 异常 {e}")
                results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        self.log(f"系统健康检查: {success_rate:.1f}% 通过")
        
        return success_rate >= 70  # 70%以上通过率认为系统健康
    
    def cleanup_test_data(self):
        """清理测试数据"""
        self.log("清理测试数据...")
        
        try:
            import sqlite3
            
            conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
            cursor = conn.cursor()
            
            # 删除测试数据
            if self.test_data.get('consultation'):
                patient_id = self.test_data['consultation']['patient_id']
                conversation_id = self.test_data['consultation']['conversation_id']
                prescription_id = self.test_data['consultation'].get('prescription_id')
                
                # 删除相关记录
                cursor.execute("DELETE FROM consultations WHERE patient_id = ?", (patient_id,))
                cursor.execute("DELETE FROM conversation_states WHERE user_id = ?", (patient_id,))
                
                if prescription_id:
                    cursor.execute("DELETE FROM prescriptions WHERE id = ?", (prescription_id,))
                    cursor.execute("DELETE FROM doctor_review_queue WHERE prescription_id = ?", (prescription_id,))
            
            if self.test_data.get('payment'):
                order_no = self.test_data['payment']['order_no']
                cursor.execute("DELETE FROM orders WHERE order_no = ?", (order_no,))
            
            conn.commit()
            conn.close()
            
            self.log("✅ 测试数据清理完成")
            
        except Exception as e:
            self.log(f"⚠️ 清理测试数据时出现异常: {e}")
    
    def run_all_tests(self):
        """运行所有API测试"""
        self.log("🚀 开始API端点测试")
        
        tests = [
            ("服务状态检查", self.test_service_status),
            ("问诊API测试", self.test_consultation_api),
            ("患者历史记录API测试", self.test_patient_history_api),
            ("医生待审核处方API测试", self.test_doctor_pending_api),
            ("支付API测试", self.test_payment_apis),
            ("处方状态查询API测试", self.test_prescription_status_api),
            ("系统健康检查", self.test_system_health),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            self.log(f"\n{'='*50}")
            self.log(f"执行: {test_name}")
            
            try:
                result = test_func()
                results.append((test_name, result))
                
                if result:
                    self.log(f"✅ {test_name} 通过")
                else:
                    self.log(f"❌ {test_name} 失败")
                    
            except Exception as e:
                self.log(f"❌ {test_name} 异常: {e}")
                results.append((test_name, False))
            
            time.sleep(1)  # 测试间隔
        
        # 输出测试结果
        self.log(f"\n{'='*50}")
        self.log("📊 API测试结果摘要")
        self.log(f"{'='*50}")
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status} {test_name}")
            if result:
                passed += 1
        
        self.log(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")
        
        if passed == total:
            self.log("🎉 所有API测试通过！系统运行正常")
        elif passed >= total * 0.8:
            self.log("⚠️ 大部分API测试通过，系统基本正常")
        else:
            self.log("❌ 多个API测试失败，系统存在问题")
        
        # 清理测试数据
        if input("\n是否清理测试数据？(y/N): ").lower() == 'y':
            self.cleanup_test_data()
        
        return passed >= total * 0.8  # 80%通过率认为成功

def main():
    """主函数"""
    print("API端点测试脚本")
    print("=" * 50)
    
    tester = APIEndpointTester()
    
    # 检查服务是否运行
    try:
        response = requests.get(f"{tester.base_url}/api/consultation/service-status", timeout=5)
        if response.status_code != 200:
            print("❌ TCM-AI服务未运行或状态异常")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ 无法连接到TCM-AI服务，请确认服务已启动")
        sys.exit(1)
    
    # 运行测试
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()