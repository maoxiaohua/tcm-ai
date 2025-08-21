"""
医生个性化回复集成测试
验证不同医生对相同症状的回复差异
"""
import pytest
import time
from difflib import SequenceMatcher

class TestDoctorPersonalization:
    """医生个性化测试类"""
    
    def test_doctor_responses_are_unique(self, api_client, test_doctors, test_symptoms):
        """测试医生回复的独特性"""
        
        for symptom in test_symptoms[:2]:  # 测试前2个症状以节省时间
            print(f"\n📋 测试症状: {symptom[:30]}...")
            
            responses = {}
            
            # 获取所有医生的回复
            for doctor in test_doctors:
                print(f"⏳ 获取 {doctor} 的回复...")
                
                response = api_client.chat(symptom, doctor)
                assert response.status_code == 200, f"API请求失败: {response.status_code}"
                
                result = response.json()
                ai_response = result.get("reply", "")
                
                # 验证不是空回复
                assert len(ai_response) > 50, f"{doctor} 回复内容太短"
                
                # 验证不是模板回复
                assert "🌿 **中医诊疗建议**" not in ai_response, f"{doctor} 返回了模板回复"
                
                responses[doctor] = ai_response
                time.sleep(2)  # 避免请求过快
            
            # 分析回复独特性
            uniqueness_score = self._calculate_response_uniqueness(responses)
            print(f"📊 回复独特性分数: {uniqueness_score:.2f}")
            
            # 验证独特性（要求至少70%不同）
            assert uniqueness_score >= 0.7, f"医生回复独特性不足: {uniqueness_score:.2f}"
    
    def test_no_template_responses_for_medical_terms(self, api_client, test_doctors):
        """测试包含医学术语的症状不返回模板回复"""
        
        medical_terms_symptoms = [
            "我有高血压，头晕",
            "糖尿病患者，口干",
            "肾功能不好，腰痛"
        ]
        
        for symptom in medical_terms_symptoms:
            # 随机选择一个医生测试
            doctor = test_doctors[0]
            
            response = api_client.chat(symptom, doctor)
            assert response.status_code == 200
            
            result = response.json()
            ai_response = result.get("reply", "")
            
            # 验证不是模板回复
            assert "🌿 **中医诊疗建议**" not in ai_response, \
                f"包含'{symptom}'的症状返回了模板回复"
            
            # 验证包含医生特色内容
            assert len(ai_response) > 100, "回复内容太简短"
            
            time.sleep(1)
    
    def test_doctor_specific_characteristics(self, api_client):
        """测试医生特定特征"""
        
        symptom = "我经常头痛，请帮我分析"
        
        # 测试张仲景的回复特征
        zhang_response = api_client.chat(symptom, "zhang_zhongjing")
        assert zhang_response.status_code == 200
        zhang_content = zhang_response.json().get("reply", "")
        
        # 张仲景应该体现伤寒论特色
        zhang_keywords = ["辨证", "四诊", "方剂"]
        assert any(keyword in zhang_content for keyword in zhang_keywords), \
            "张仲景回复未体现伤寒派特色"
        
        time.sleep(2)
        
        # 测试李东垣的回复特征
        li_response = api_client.chat(symptom, "li_dongyuan")
        assert li_response.status_code == 200
        li_content = li_response.json().get("reply", "")
        
        # 李东垣应该体现补土派特色
        li_keywords = ["脾胃", "后天之本", "清阳"]
        assert any(keyword in li_content for keyword in li_keywords), \
            "李东垣回复未体现补土派特色"
    
    def test_response_consistency_across_platforms(self, api_client):
        """测试跨平台回复一致性（模拟移动端和PC端）"""
        
        symptom = "失眠多梦，心烦意乱"
        doctor = "ye_tianshi"
        
        # 发送两次相同请求（模拟不同平台）
        response1 = api_client.chat(symptom, doctor, "mobile_test_123")
        response2 = api_client.chat(symptom, doctor, "desktop_test_456")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        content1 = response1.json().get("reply", "")
        content2 = response2.json().get("reply", "")
        
        # 核心内容应该相似（允许一些随机性）
        similarity = self._calculate_similarity(content1, content2)
        assert similarity >= 0.7, f"跨平台回复一致性不足: {similarity:.2f}"
    
    def _calculate_response_uniqueness(self, responses):
        """计算回复独特性分数"""
        if len(responses) < 2:
            return 1.0
        
        doctors = list(responses.keys())
        similarities = []
        
        # 计算两两相似度
        for i in range(len(doctors)):
            for j in range(i + 1, len(doctors)):
                similarity = self._calculate_similarity(
                    responses[doctors[i]], 
                    responses[doctors[j]]
                )
                similarities.append(similarity)
        
        # 独特性 = 1 - 平均相似度
        avg_similarity = sum(similarities) / len(similarities)
        return 1.0 - avg_similarity
    
    def _calculate_similarity(self, text1, text2):
        """计算两个文本的相似度"""
        return SequenceMatcher(None, text1, text2).ratio()

class TestSystemHealth:
    """系统健康测试"""
    
    def test_api_health_check(self, api_client):
        """测试API健康检查"""
        response = api_client.health_check()
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("server_status") == "running"
        assert data.get("api_key_configured") is True
    
    def test_all_doctors_available(self, api_client, test_doctors):
        """测试所有医生都可用"""
        test_message = "头痛"
        
        for doctor in test_doctors:
            response = api_client.chat(test_message, doctor)
            assert response.status_code == 200, f"医生 {doctor} 不可用"
            
            result = response.json()
            assert "reply" in result, f"医生 {doctor} 未返回回复"
            assert len(result["reply"]) > 10, f"医生 {doctor} 回复过短"
            
            time.sleep(1)  # 避免请求过快