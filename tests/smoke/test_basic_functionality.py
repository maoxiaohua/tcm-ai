"""
冒烟测试 - 快速验证系统基本功能
用于部署后的快速健康检查
"""
import pytest
import requests
import time

class TestBasicFunctionality:
    """基础功能冒烟测试"""
    
    def test_api_server_running(self, api_base_url):
        """测试API服务器是否运行"""
        response = requests.get(f"{api_base_url}/debug_status", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert data["server_status"] == "running"
        print("✅ API服务器正常运行")
    
    def test_basic_chat_functionality(self, api_client):
        """测试基础聊天功能"""
        response = api_client.chat("头痛", "zhang_zhongjing")
        
        assert response.status_code == 200
        result = response.json()
        
        assert "reply" in result
        assert len(result["reply"]) > 20
        print("✅ 基础聊天功能正常")
    
    def test_no_template_response_for_common_symptoms(self, api_client):
        """测试常见症状不返回模板回复"""
        common_symptoms = ["高血压头晕", "糖尿病口干", "失眠多梦"]
        
        for symptom in common_symptoms:
            response = api_client.chat(symptom, "zhang_zhongjing")
            assert response.status_code == 200
            
            result = response.json()
            reply = result.get("reply", "")
            
            # 确保不是模板回复
            assert "🌿 **中医诊疗建议**" not in reply
            print(f"✅ {symptom} - 非模板回复")
            
            time.sleep(1)
    
    def test_different_doctors_give_different_responses(self, api_client):
        """测试不同医生给出不同回复"""
        symptom = "经常头痛"
        
        # 获取两个不同医生的回复
        zhang_response = api_client.chat(symptom, "zhang_zhongjing")
        ye_response = api_client.chat(symptom, "ye_tianshi")
        
        assert zhang_response.status_code == 200
        assert ye_response.status_code == 200
        
        zhang_reply = zhang_response.json().get("reply", "")
        ye_reply = ye_response.json().get("reply", "")
        
        # 回复不应该完全相同
        assert zhang_reply != ye_reply
        print("✅ 不同医生给出不同回复")
    
    def test_cache_system_working(self, api_base_url):
        """测试缓存系统是否工作"""
        response = requests.get(f"{api_base_url}/debug_status", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("cache_system_available") is True
        print("✅ 缓存系统可用")
    
    def test_knowledge_system_working(self, api_base_url):
        """测试知识系统是否工作"""
        response = requests.get(f"{api_base_url}/debug_status", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("enhanced_system_available") is True
        print("✅ 知识系统可用")

class TestCriticalPaths:
    """关键路径测试"""
    
    def test_medical_safety_system(self, api_client):
        """测试医疗安全系统"""
        # 测试包含西药名称的消息
        response = api_client.chat("医生建议我服用阿司匹林", "zhang_zhongjing")
        assert response.status_code == 200
        
        result = response.json()
        reply = result.get("reply", "")
        
        # 应该过滤掉西药推荐
        assert "阿司匹林" not in reply or "建议服用阿司匹林" not in reply
        print("✅ 医疗安全系统正常工作")
    
    def test_image_upload_endpoints_exist(self, api_base_url):
        """测试图片上传端点是否存在"""
        # 检查综合图像分析端点 (舌象+面相+医疗图像)
        response = requests.options(f"{api_base_url}/analyze_images", timeout=10)
        assert response.status_code in [200, 405]  # 405 Method Not Allowed也表示端点存在
        
        # 检查处方图像检查端点  
        response = requests.options(f"{api_base_url}/api/prescription/check_image", timeout=10)
        assert response.status_code in [200, 405]
        
        print("✅ 图片上传端点存在")
    
    def test_conversation_history_system(self, api_client):
        """测试对话历史系统"""
        conversation_id = f"smoke_test_{int(time.time())}"
        
        # 发送第一条消息
        response1 = api_client.chat("我头痛", "zhang_zhongjing", conversation_id)
        assert response1.status_code == 200
        
        time.sleep(1)
        
        # 发送第二条消息
        response2 = api_client.chat("还有什么需要注意的", "zhang_zhongjing", conversation_id)
        assert response2.status_code == 200
        
        # 第二次回复应该能理解上下文
        reply2 = response2.json().get("reply", "")
        assert len(reply2) > 20
        
        print("✅ 对话历史系统工作正常")

if __name__ == "__main__":
    # 独立运行冒烟测试
    pytest.main([__file__, "-v", "--tb=short"])