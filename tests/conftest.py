"""
pytest配置文件 - 测试框架基础配置
"""
import pytest
import os
import sys
import requests
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def api_base_url():
    """API基础URL"""
    return "http://localhost:8000"

@pytest.fixture
def test_doctors():
    """测试用医生列表"""
    return ["zhang_zhongjing", "ye_tianshi", "li_dongyuan", "zheng_qin_an", "liu_duzhou"]

@pytest.fixture
def test_symptoms():
    """测试用症状列表"""
    return [
        "我有高血压，最近血压不稳定，经常头晕头痛",
        "我患有糖尿病，最近血糖控制不好，还有口干口苦的症状", 
        "最近检查肾功能有问题，腰酸腿软，夜尿频多",
        "经常咳嗽，有痰，胸闷气短",
        "失眠多梦，心烦易怒，口苦咽干"
    ]

@pytest.fixture
def api_client():
    """API客户端"""
    class APIClient:
        def __init__(self, base_url):
            self.base_url = base_url
            
        def chat(self, message, doctor, conversation_id=None):
            """发送聊天请求"""
            if not conversation_id:
                conversation_id = f"test_{int(time.time())}"
                
            response = requests.post(
                f"{self.base_url}/chat_with_ai",
                json={
                    "message": message,
                    "selected_doctor": doctor,
                    "conversation_id": conversation_id
                },
                timeout=60
            )
            return response
            
        def health_check(self):
            """健康检查"""
            response = requests.get(f"{self.base_url}/debug_status", timeout=10)
            return response
    
    return APIClient("http://localhost:8000")

@pytest.fixture(scope="session", autouse=True)
def wait_for_service():
    """等待服务启动"""
    import time
    import requests
    
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get("http://localhost:8000/debug_status", timeout=5)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            pass
        
        if attempt == max_attempts - 1:
            pytest.fail("服务在30秒内未启动")
        
        time.sleep(1)

def pytest_configure(config):
    """pytest启动配置"""
    print("\n🔬 开始运行TCM系统测试...")
    
    # 添加自定义标记
    config.addinivalue_line("markers", "regression: 防回归测试标记")

def pytest_unconfigure(config):
    """pytest结束配置"""  
    print("\n✅ TCM系统测试完成!")

def pytest_collection_modifyitems(config, items):
    """修改测试收集项，为防回归测试添加标记"""
    for item in items:
        if "regression" in item.nodeid or "herb_function" in item.nodeid:
            item.add_marker(pytest.mark.regression)