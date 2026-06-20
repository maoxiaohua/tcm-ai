"""
决策树数据服务单元测试

测试数据转换和同步功能
"""

import pytest
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.decision_tree_data_service import DecisionTreeDataService


@pytest.fixture
def service():
    """创建服务实例"""
    return DecisionTreeDataService()


@pytest.fixture
def sample_text():
    """示例文本数据"""
    return """【疾病】风寒感冒
【主症】恶寒发热（重）、头痛（中）、身痛（中）
【兼症】鼻塞、流清涕、咳嗽
【舌象】舌淡红，苔薄白
【脉象】脉浮紧
【证候】风寒表证
【处方】麻黄汤
【方剂】麻黄9克(君药) + 桂枝6克(臣药) + 杏仁6克(佐药) + 甘草3克(使药)"""


@pytest.fixture
def sample_structured():
    """示例结构化数据"""
    return {
        "disease": {
            "id": "disease_001",
            "name": "风寒感冒",
            "category": "外感病",
            "description": "感受风寒之邪，导致肺卫失宣"
        },
        "diagnosis": {
            "main_symptoms": [
                {"id": "symptom_001", "name": "恶寒发热", "category": "主症", "severity": "重"},
                {"id": "symptom_002", "name": "头痛", "category": "主症", "severity": "中"},
                {"id": "symptom_003", "name": "身痛", "category": "主症", "severity": "中"}
            ],
            "secondary_symptoms": [
                {"id": "symptom_004", "name": "鼻塞", "category": "兼症", "severity": "中"},
                {"id": "symptom_005", "name": "流涕", "category": "兼症", "severity": "清涕"},
                {"id": "symptom_006", "name": "咳嗽", "category": "兼症", "severity": "中"}
            ],
            "tongue": {
                "body": "淡红",
                "coating": "薄白"
            },
            "pulse": {
                "type": "浮紧",
                "description": "浮紧"
            }
        },
        "syndrome": {
            "id": "syndrome_001",
            "name": "风寒表证",
            "type": "实证"
        },
        "prescriptions": [{
            "id": "prescription_001",
            "name": "麻黄汤",
            "source": "《伤寒论》",
            "category": "解表剂",
            "effects": "发汗解表，宣肺平喘",
            "indications": "外感风寒表实证",
            "composition": [
                {"herb_id": "herb_001", "name": "麻黄", "dosage": 9, "unit": "克", "role": "君药", "effect": "发汗解表，宣肺平喘"},
                {"herb_id": "herb_002", "name": "桂枝", "dosage": 6, "unit": "克", "role": "臣药", "effect": "解肌发表，温通经脉"},
                {"herb_id": "herb_003", "name": "杏仁", "dosage": 6, "unit": "克", "role": "佐药", "effect": "止咳平喘"},
                {"herb_id": "herb_004", "name": "甘草", "dosage": 3, "unit": "克", "role": "使药", "effect": "调和诸药"}
            ]
        }],
        "decision_flow": {
            "nodes": [],
            "connections": []
        },
        "metadata": {
            "created_at": "2025-10-31T10:00:00",
            "created_by": "zhang_zhongjing",
            "version": "1.0"
        }
    }


@pytest.fixture
def sample_tree():
    """示例树形结构数据"""
    return {
        "nodes": [
            {"id": "node_1", "type": "disease", "label": "风寒感冒", "x": 400, "y": 50,
             "data": {"id": "disease_001", "name": "风寒感冒", "category": "外感病"}},
            {"id": "node_2", "type": "symptoms", "label": "恶寒发热、头痛、身痛", "x": 400, "y": 150,
             "data": {"symptoms": [
                 {"id": "symptom_001", "name": "恶寒发热", "category": "主症", "severity": "重"},
                 {"id": "symptom_002", "name": "头痛", "category": "主症", "severity": "中"},
                 {"id": "symptom_003", "name": "身痛", "category": "主症", "severity": "中"}
             ]}},
            {"id": "node_3", "type": "examination", "label": "舌淡红，苔薄白、脉浮紧", "x": 400, "y": 250,
             "data": {"tongue": {"body": "淡红", "coating": "薄白"}, "pulse": {"type": "浮紧"}}},
            {"id": "node_4", "type": "syndrome", "label": "风寒表证", "x": 400, "y": 350,
             "data": {"id": "syndrome_001", "name": "风寒表证", "type": "实证"}},
            {"id": "node_5", "type": "prescription", "label": "麻黄汤", "x": 400, "y": 450,
             "data": {"id": "prescription_001", "name": "麻黄汤"}}
        ],
        "connections": [
            {"from": "node_1", "to": "node_2", "type": "diagnosis"},
            {"from": "node_2", "to": "node_3", "type": "examination"},
            {"from": "node_3", "to": "node_4", "type": "pattern_identification"},
            {"from": "node_4", "to": "node_5", "type": "treatment"}
        ]
    }


class TestTextToStructured:
    """测试文本转结构化数据"""

    def test_basic_parsing(self, service, sample_text):
        """测试基本解析"""
        result = service.text_to_structured(sample_text, "zhang_zhongjing")

        assert result["disease"]["name"] == "风寒感冒"
        assert len(result["diagnosis"]["main_symptoms"]) == 3
        assert len(result["diagnosis"]["secondary_symptoms"]) == 3
        assert result["diagnosis"]["tongue"]["body"] == "淡红"
        assert result["diagnosis"]["pulse"]["type"] == "浮紧"
        assert result["syndrome"]["name"] == "风寒表证"
        assert len(result["prescriptions"]) == 1
        assert result["prescriptions"][0]["name"] == "麻黄汤"

    def test_symptom_severity_parsing(self, service):
        """测试症状严重程度解析"""
        text = "【主症】恶寒发热（重）、头痛（中）、身痛（轻）"
        result = service.text_to_structured(text, "zhang_zhongjing")

        symptoms = result["diagnosis"]["main_symptoms"]
        assert symptoms[0]["severity"] == "重"
        assert symptoms[1]["severity"] == "中"
        assert symptoms[2]["severity"] == "轻"

    def test_formula_parsing(self, service):
        """测试方剂解析"""
        text = "【处方】麻黄汤\n【方剂】麻黄9克(君药) + 桂枝6克(臣药) + 杏仁6克(佐药) + 甘草3克(使药)"
        result = service.text_to_structured(text, "zhang_zhongjing")

        composition = result["prescriptions"][0]["composition"]
        assert len(composition) == 4
        assert composition[0]["name"] == "麻黄"
        assert composition[0]["dosage"] == 9
        assert composition[0]["unit"] == "克"
        assert composition[0]["role"] == "君药"

    def test_standard_library_lookup(self, service):
        """测试标准库查询（麻黄汤应该在标准库中）"""
        text = "【处方】麻黄汤"
        result = service.text_to_structured(text, "zhang_zhongjing")

        prescription = result["prescriptions"][0]
        assert prescription["id"] == "prescription_001"
        assert prescription["source"] == "《伤寒论》"
        assert "发汗解表" in prescription["effects"]


class TestStructuredToText:
    """测试结构化数据转文本"""

    def test_basic_formatting(self, service, sample_structured):
        """测试基本格式化"""
        result = service.structured_to_text(sample_structured)

        assert "【疾病】风寒感冒" in result
        assert "【主症】" in result
        assert "恶寒发热" in result
        assert "【证候】风寒表证" in result
        assert "【处方】麻黄汤" in result

    def test_symptom_formatting(self, service, sample_structured):
        """测试症状格式化"""
        result = service.structured_to_text(sample_structured)

        # 重症应该有括号标注
        assert "恶寒发热（重）" in result
        # 中症可能没有括号（根据实现决定）
        assert "头痛" in result

    def test_tongue_pulse_formatting(self, service, sample_structured):
        """测试舌脉格式化"""
        result = service.structured_to_text(sample_structured)

        assert "【舌象】" in result
        assert "舌淡红" in result
        assert "苔薄白" in result
        assert "【脉象】" in result
        assert "脉浮紧" in result

    def test_prescription_details(self, service, sample_structured):
        """测试处方详细信息"""
        result = service.structured_to_text(sample_structured)

        assert "【处方】麻黄汤" in result
        assert "【出处】《伤寒论》" in result
        assert "【功效】发汗解表，宣肺平喘" in result
        assert "【方剂】" in result
        assert "麻黄9克(君药)" in result


class TestStructuredToTree:
    """测试结构化数据转树形结构"""

    def test_node_generation(self, service, sample_structured):
        """测试节点生成"""
        result = service.structured_to_tree(sample_structured)

        assert "nodes" in result
        assert "connections" in result
        assert len(result["nodes"]) >= 5  # 至少有疾病、症状、舌脉、证候、处方

    def test_node_types(self, service, sample_structured):
        """测试节点类型"""
        result = service.structured_to_tree(sample_structured)

        node_types = [node["type"] for node in result["nodes"]]
        assert "disease" in node_types
        assert "symptoms" in node_types
        assert "syndrome" in node_types
        assert "prescription" in node_types

    def test_connections(self, service, sample_structured):
        """测试连接关系"""
        result = service.structured_to_tree(sample_structured)

        assert len(result["connections"]) >= 4
        # 验证连接的from和to都指向有效节点
        node_ids = [node["id"] for node in result["nodes"]]
        for conn in result["connections"]:
            assert conn["from"] in node_ids
            assert conn["to"] in node_ids


class TestTreeToStructured:
    """测试树形结构转结构化数据"""

    def test_basic_extraction(self, service, sample_tree):
        """测试基本提取"""
        result = service.tree_to_structured(sample_tree, "zhang_zhongjing")

        assert result["disease"]["name"] == "风寒感冒"
        assert result["syndrome"]["name"] == "风寒表证"

    def test_symptom_extraction(self, service, sample_tree):
        """测试症状提取"""
        result = service.tree_to_structured(sample_tree, "zhang_zhongjing")

        # 症状应该被正确分类为主症和兼症
        all_symptoms = (
            result["diagnosis"]["main_symptoms"] +
            result["diagnosis"]["secondary_symptoms"]
        )
        assert len(all_symptoms) > 0

    def test_decision_flow_preservation(self, service, sample_tree):
        """测试决策流程保留"""
        result = service.tree_to_structured(sample_tree, "zhang_zhongjing")

        assert result["decision_flow"] == sample_tree


class TestRoundTrip:
    """测试往返转换"""

    def test_text_roundtrip(self, service, sample_text):
        """测试文本往返转换"""
        # text → structured → text
        structured = service.text_to_structured(sample_text, "zhang_zhongjing")
        text_back = service.structured_to_text(structured)

        # 关键信息应该保留
        assert "风寒感冒" in text_back
        assert "恶寒发热" in text_back
        assert "麻黄汤" in text_back

    def test_tree_roundtrip(self, service, sample_structured):
        """测试树形结构往返转换"""
        # structured → tree → structured
        tree = service.structured_to_tree(sample_structured)
        structured_back = service.tree_to_structured(tree, "zhang_zhongjing")

        # 关键信息应该保留
        assert structured_back["disease"]["name"] == sample_structured["disease"]["name"]
        assert structured_back["syndrome"]["name"] == sample_structured["syndrome"]["name"]

    def test_full_cycle(self, service, sample_text):
        """测试完整循环转换"""
        # text → structured → tree → structured → text
        structured1 = service.text_to_structured(sample_text, "zhang_zhongjing")
        tree = service.structured_to_tree(structured1)
        structured2 = service.tree_to_structured(tree, "zhang_zhongjing")
        text_back = service.structured_to_text(structured2)

        # 核心信息应该保持
        assert "风寒感冒" in text_back
        assert "麻黄汤" in text_back


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_text(self, service):
        """测试空文本"""
        # 空文本应该返回基本结构，不抛出异常
        result = service.text_to_structured("", "zhang_zhongjing")
        assert "disease" in result
        assert "diagnosis" in result

    def test_malformed_text(self, service):
        """测试格式错误的文本"""
        text = "这是一段没有格式的文本"
        # 应该能处理但返回基本结构
        result = service.text_to_structured(text, "zhang_zhongjing")
        assert "disease" in result
        assert "diagnosis" in result

    def test_minimal_data(self, service):
        """测试最小数据集"""
        minimal = {
            "disease": {"name": "测试疾病"},
            "diagnosis": {"main_symptoms": [], "secondary_symptoms": [], "tongue": {}, "pulse": {}},
            "syndrome": {},
            "prescriptions": [],
            "decision_flow": {"nodes": [], "connections": []}
        }

        # 应该能转换为文本
        text = service.structured_to_text(minimal)
        assert "【疾病】测试疾病" in text

    def test_unicode_handling(self, service):
        """测试Unicode字符处理"""
        text = "【疾病】风寒感冒\n【主症】恶寒发热（重）、头痛（中）"
        result = service.text_to_structured(text, "zhang_zhongjing")
        assert result["disease"]["name"] == "风寒感冒"


class TestHelperMethods:
    """测试辅助方法"""

    def test_symptom_formatting(self, service):
        """测试症状格式化"""
        symptoms = [
            {"name": "恶寒发热", "severity": "重"},
            {"name": "头痛", "severity": "中"},
            {"name": "身痛", "severity": "轻"}
        ]
        result = service._format_symptoms(symptoms)
        assert "恶寒发热（重）" in result
        assert "头痛" in result

    def test_tongue_parsing(self, service):
        """测试舌象解析"""
        result = service._parse_tongue("舌淡红，苔薄白")
        assert result["body"] == "淡红"
        assert result["coating"] == "薄白"

    def test_pulse_parsing(self, service):
        """测试脉象解析"""
        result = service._parse_pulse("脉浮紧")
        assert result["type"] == "浮紧"

    def test_syndrome_type_inference(self, service):
        """测试证候类型推断"""
        assert service._infer_syndrome_type("脾气虚证") == "虚证"
        assert service._infer_syndrome_type("风寒表证") == "实证"
        assert service._infer_syndrome_type("气阴两虚证") == "虚证"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
