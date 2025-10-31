"""
决策树数据驱动服务
提供数据格式转换和同步功能

核心功能:
1. text_to_structured(): 文本 → JSON结构化数据
2. structured_to_text(): JSON结构化数据 → 格式化文本
3. structured_to_tree(): JSON结构化数据 → 树形结构
4. tree_to_structured(): 树形结构 → JSON结构化数据
5. save_and_sync(): 保存并同步三种格式

版本: v3.0
日期: 2025-10-31
"""

import json
import re
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path


class DecisionTreeDataService:
    """决策树数据转换和同步服务"""

    def __init__(self, db_path: str = "/opt/tcm-ai/data/user_history.sqlite"):
        """初始化服务

        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path

    def _get_db_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ============================================
    # 核心转换方法
    # ============================================

    def text_to_structured(self, text: str, doctor_id: str) -> Dict[str, Any]:
        """将文本格式转换为JSON结构化数据

        文本格式示例:
        【疾病】风寒感冒
        【主症】恶寒发热（重）、头痛（中）
        【兼症】鼻塞、流清涕
        【舌象】舌淡红，苔薄白
        【脉象】脉浮紧
        【证候】风寒表证
        【处方】麻黄汤
        【方剂】麻黄9克(君药)、桂枝6克(臣药)、杏仁6克(佐药)、甘草3克(使药)

        Args:
            text: 格式化文本
            doctor_id: 医生ID

        Returns:
            JSON结构化数据
        """
        try:
            # 初始化结构
            structured_data = {
                "disease": {},
                "diagnosis": {
                    "main_symptoms": [],
                    "secondary_symptoms": [],
                    "tongue": {},
                    "pulse": {}
                },
                "syndrome": {},
                "prescriptions": [],
                "decision_flow": {
                    "nodes": [],
                    "connections": []
                },
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "created_by": doctor_id,
                    "version": "1.0"
                }
            }

            # 解析疾病
            disease_match = re.search(r'【疾病】(.+?)(?=\n|【|$)', text)
            if disease_match:
                disease_name = disease_match.group(1).strip()
                # 从标准库查询疾病信息
                disease_info = self._get_disease_from_standard(disease_name)
                if disease_info:
                    structured_data["disease"] = {
                        "id": disease_info["id"],
                        "name": disease_info["name"],
                        "category": disease_info["category"],
                        "description": disease_info.get("description", "")
                    }
                else:
                    structured_data["disease"] = {
                        "id": f"disease_{uuid.uuid4().hex[:8]}",
                        "name": disease_name,
                        "category": "未分类",
                        "description": ""
                    }

            # 解析主症
            main_symptoms_match = re.search(r'【主症】(.+?)(?=\n|【|$)', text)
            if main_symptoms_match:
                symptoms_text = main_symptoms_match.group(1).strip()
                structured_data["diagnosis"]["main_symptoms"] = self._parse_symptoms(symptoms_text, "主症")

            # 解析兼症
            secondary_symptoms_match = re.search(r'【兼症】(.+?)(?=\n|【|$)', text)
            if secondary_symptoms_match:
                symptoms_text = secondary_symptoms_match.group(1).strip()
                structured_data["diagnosis"]["secondary_symptoms"] = self._parse_symptoms(symptoms_text, "兼症")

            # 解析舌象
            tongue_match = re.search(r'【舌象】(.+?)(?=\n|【|$)', text)
            if tongue_match:
                tongue_text = tongue_match.group(1).strip()
                structured_data["diagnosis"]["tongue"] = self._parse_tongue(tongue_text)

            # 解析脉象
            pulse_match = re.search(r'【脉象】(.+?)(?=\n|【|$)', text)
            if pulse_match:
                pulse_text = pulse_match.group(1).strip()
                structured_data["diagnosis"]["pulse"] = self._parse_pulse(pulse_text)

            # 解析证候
            syndrome_match = re.search(r'【证候】(.+?)(?=\n|【|$)', text)
            if syndrome_match:
                syndrome_name = syndrome_match.group(1).strip()
                structured_data["syndrome"] = {
                    "id": f"syndrome_{uuid.uuid4().hex[:8]}",
                    "name": syndrome_name,
                    "type": self._infer_syndrome_type(syndrome_name)
                }

            # 解析处方
            prescription_match = re.search(r'【处方】(.+?)(?=\n|【|$)', text)
            formula_match = re.search(r'【方剂】(.+?)(?=\n|【|$)', text)

            if prescription_match:
                prescription_name = prescription_match.group(1).strip()
                formula_text = formula_match.group(1).strip() if formula_match else ""

                # 从标准库查询处方信息
                prescription_info = self._get_prescription_from_standard(prescription_name)

                if prescription_info:
                    # 使用标准库信息
                    prescription = {
                        "id": prescription_info["id"],
                        "name": prescription_info["name"],
                        "source": prescription_info.get("source", ""),
                        "category": prescription_info.get("category", ""),
                        "effects": prescription_info.get("effects", ""),
                        "indications": prescription_info.get("indications", ""),
                        "composition": json.loads(prescription_info.get("composition", "[]"))
                    }
                else:
                    # 手动解析方剂组成
                    composition = self._parse_formula(formula_text) if formula_text else []
                    prescription = {
                        "id": f"prescription_{uuid.uuid4().hex[:8]}",
                        "name": prescription_name,
                        "source": "",
                        "category": "",
                        "effects": "",
                        "indications": "",
                        "composition": composition
                    }

                structured_data["prescriptions"].append(prescription)

            return structured_data

        except Exception as e:
            raise ValueError(f"文本解析失败: {str(e)}")

    def structured_to_text(self, data: Dict[str, Any]) -> str:
        """将JSON结构化数据转换为格式化文本

        Args:
            data: JSON结构化数据

        Returns:
            格式化文本
        """
        try:
            lines = []

            # 疾病
            if data.get("disease") and data["disease"].get("name"):
                lines.append(f"【疾病】{data['disease']['name']}")
                if data["disease"].get("category"):
                    lines.append(f"【分类】{data['disease']['category']}")

            # 主症
            diagnosis = data.get("diagnosis", {})
            if diagnosis.get("main_symptoms"):
                symptoms_text = self._format_symptoms(diagnosis["main_symptoms"])
                lines.append(f"【主症】{symptoms_text}")

            # 兼症
            if diagnosis.get("secondary_symptoms"):
                symptoms_text = self._format_symptoms(diagnosis["secondary_symptoms"])
                lines.append(f"【兼症】{symptoms_text}")

            # 舌象
            if diagnosis.get("tongue"):
                tongue_text = self._format_tongue(diagnosis["tongue"])
                if tongue_text:
                    lines.append(f"【舌象】{tongue_text}")

            # 脉象
            if diagnosis.get("pulse"):
                pulse_text = self._format_pulse(diagnosis["pulse"])
                if pulse_text:
                    lines.append(f"【脉象】{pulse_text}")

            # 证候
            if data.get("syndrome") and data["syndrome"].get("name"):
                syndrome_name = data["syndrome"]["name"]
                syndrome_type = data["syndrome"].get("type", "")
                if syndrome_type:
                    lines.append(f"【证候】{syndrome_name}（{syndrome_type}）")
                else:
                    lines.append(f"【证候】{syndrome_name}")

            # 处方
            if data.get("prescriptions"):
                for prescription in data["prescriptions"]:
                    lines.append(f"【处方】{prescription['name']}")

                    # 出处
                    if prescription.get("source"):
                        lines.append(f"【出处】{prescription['source']}")

                    # 功效
                    if prescription.get("effects"):
                        lines.append(f"【功效】{prescription['effects']}")

                    # 主治
                    if prescription.get("indications"):
                        lines.append(f"【主治】{prescription['indications']}")

                    # 方剂组成
                    if prescription.get("composition"):
                        formula_parts = []
                        for herb in prescription["composition"]:
                            herb_text = f"{herb['name']}{herb['dosage']}{herb.get('unit', '克')}"
                            if herb.get("role"):
                                herb_text += f"({herb['role']})"
                            formula_parts.append(herb_text)
                        lines.append(f"【方剂】{' + '.join(formula_parts)}")

            return '\n'.join(lines)

        except Exception as e:
            raise ValueError(f"结构化数据转文本失败: {str(e)}")

    def structured_to_tree(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """将JSON结构化数据转换为树形结构

        Args:
            data: JSON结构化数据

        Returns:
            树形结构 {nodes: [], connections: []}
        """
        try:
            nodes = []
            connections = []
            node_id_counter = 1

            # 创建疾病根节点
            disease_node_id = f"node_{node_id_counter}"
            node_id_counter += 1

            disease_name = data.get("disease", {}).get("name", "未知疾病")
            nodes.append({
                "id": disease_node_id,
                "type": "disease",
                "label": disease_name,
                "data": data.get("disease", {}),
                "x": 400,
                "y": 50
            })

            last_node_id = disease_node_id
            current_y = 150

            # 创建诊断节点（主症+兼症）
            diagnosis = data.get("diagnosis", {})
            all_symptoms = diagnosis.get("main_symptoms", []) + diagnosis.get("secondary_symptoms", [])

            if all_symptoms:
                symptoms_node_id = f"node_{node_id_counter}"
                node_id_counter += 1

                symptoms_text = "、".join([s["name"] for s in all_symptoms[:5]])  # 最多显示5个
                if len(all_symptoms) > 5:
                    symptoms_text += f"等{len(all_symptoms)}个症状"

                nodes.append({
                    "id": symptoms_node_id,
                    "type": "symptoms",
                    "label": symptoms_text,
                    "data": {"symptoms": all_symptoms},
                    "x": 400,
                    "y": current_y
                })

                connections.append({
                    "from": last_node_id,
                    "to": symptoms_node_id,
                    "type": "diagnosis"
                })

                last_node_id = symptoms_node_id
                current_y += 100

            # 创建舌脉节点
            tongue = diagnosis.get("tongue", {})
            pulse = diagnosis.get("pulse", {})

            if tongue or pulse:
                tongue_pulse_node_id = f"node_{node_id_counter}"
                node_id_counter += 1

                tongue_pulse_text = []
                if tongue:
                    tongue_text = self._format_tongue(tongue)
                    if tongue_text:
                        tongue_pulse_text.append(tongue_text)
                if pulse:
                    pulse_text = self._format_pulse(pulse)
                    if pulse_text:
                        tongue_pulse_text.append(pulse_text)

                nodes.append({
                    "id": tongue_pulse_node_id,
                    "type": "examination",
                    "label": "、".join(tongue_pulse_text),
                    "data": {"tongue": tongue, "pulse": pulse},
                    "x": 400,
                    "y": current_y
                })

                connections.append({
                    "from": last_node_id,
                    "to": tongue_pulse_node_id,
                    "type": "examination"
                })

                last_node_id = tongue_pulse_node_id
                current_y += 100

            # 创建证候节点
            syndrome = data.get("syndrome", {})
            if syndrome.get("name"):
                syndrome_node_id = f"node_{node_id_counter}"
                node_id_counter += 1

                nodes.append({
                    "id": syndrome_node_id,
                    "type": "syndrome",
                    "label": syndrome["name"],
                    "data": syndrome,
                    "x": 400,
                    "y": current_y
                })

                connections.append({
                    "from": last_node_id,
                    "to": syndrome_node_id,
                    "type": "pattern_identification"
                })

                last_node_id = syndrome_node_id
                current_y += 100

            # 创建处方节点
            prescriptions = data.get("prescriptions", [])
            for prescription in prescriptions:
                prescription_node_id = f"node_{node_id_counter}"
                node_id_counter += 1

                nodes.append({
                    "id": prescription_node_id,
                    "type": "prescription",
                    "label": prescription["name"],
                    "data": prescription,
                    "x": 400,
                    "y": current_y
                })

                connections.append({
                    "from": last_node_id,
                    "to": prescription_node_id,
                    "type": "treatment"
                })

                last_node_id = prescription_node_id
                current_y += 100

            return {
                "nodes": nodes,
                "connections": connections
            }

        except Exception as e:
            raise ValueError(f"结构化数据转树形结构失败: {str(e)}")

    def tree_to_structured(self, tree: Dict[str, Any], doctor_id: str) -> Dict[str, Any]:
        """将树形结构转换为JSON结构化数据

        Args:
            tree: 树形结构 {nodes: [], connections: []}
            doctor_id: 医生ID

        Returns:
            JSON结构化数据
        """
        try:
            # 初始化结构
            structured_data = {
                "disease": {},
                "diagnosis": {
                    "main_symptoms": [],
                    "secondary_symptoms": [],
                    "tongue": {},
                    "pulse": {}
                },
                "syndrome": {},
                "prescriptions": [],
                "decision_flow": tree,
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "created_by": doctor_id,
                    "version": "1.0"
                }
            }

            nodes = tree.get("nodes", [])

            # 按类型提取节点数据
            for node in nodes:
                node_type = node.get("type")
                node_data = node.get("data", {})

                if node_type == "disease":
                    structured_data["disease"] = node_data

                elif node_type == "symptoms":
                    symptoms = node_data.get("symptoms", [])
                    # 简单分类：前面的是主症，后面的是兼症
                    if len(symptoms) > 0:
                        structured_data["diagnosis"]["main_symptoms"] = symptoms[:3]
                        structured_data["diagnosis"]["secondary_symptoms"] = symptoms[3:]

                elif node_type == "examination":
                    if "tongue" in node_data:
                        structured_data["diagnosis"]["tongue"] = node_data["tongue"]
                    if "pulse" in node_data:
                        structured_data["diagnosis"]["pulse"] = node_data["pulse"]

                elif node_type == "syndrome":
                    structured_data["syndrome"] = node_data

                elif node_type == "prescription":
                    structured_data["prescriptions"].append(node_data)

            return structured_data

        except Exception as e:
            raise ValueError(f"树形结构转结构化数据失败: {str(e)}")

    # ============================================
    # 数据保存和同步
    # ============================================

    def save_and_sync(
        self,
        doctor_id: str,
        content: Any,
        source: str,
        decision_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """保存并同步数据

        核心同步逻辑:
        1. 接收来自'text'或'canvas'的输入
        2. 转换为structured_content（JSON）
        3. 生成另外两种格式
        4. 保存三种格式到数据库
        5. 返回完整数据供UI刷新

        Args:
            doctor_id: 医生ID
            content: 输入内容（文本或树形结构）
            source: 数据来源 ('text' 或 'canvas')
            decision_id: 决策记录ID（新建时为None）

        Returns:
            (成功标志, 消息, 完整数据)
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # 步骤1: 根据来源转换为structured_content
            if source == "text":
                structured_content = self.text_to_structured(content, doctor_id)
            elif source == "canvas":
                structured_content = self.tree_to_structured(content, doctor_id)
            else:
                return False, f"不支持的数据来源: {source}", None

            # 步骤2: 生成另外两种格式
            text_format = self.structured_to_text(structured_content)
            tree_structure = self.structured_to_tree(structured_content)

            # 步骤3: 提取疾病信息
            disease_name = structured_content.get("disease", {}).get("name", "未知疾病")
            disease_id = structured_content.get("disease", {}).get("id")

            # 步骤4: 保存到数据库
            if decision_id is None:
                # 新建记录
                decision_id = f"decision_{uuid.uuid4().hex}"

                cursor.execute("""
                    INSERT INTO clinical_decision_data (
                        id, doctor_id, disease_id, disease_name,
                        structured_content, text_format, tree_structure,
                        last_modified_from, version, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1)
                """, (
                    decision_id,
                    doctor_id,
                    disease_id,
                    disease_name,
                    json.dumps(structured_content, ensure_ascii=False),
                    text_format,
                    json.dumps(tree_structure, ensure_ascii=False),
                    source
                ))

                message = "新建决策记录成功"

            else:
                # 更新现有记录
                cursor.execute("""
                    UPDATE clinical_decision_data
                    SET structured_content = ?,
                        text_format = ?,
                        tree_structure = ?,
                        disease_id = ?,
                        disease_name = ?,
                        last_modified_from = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND doctor_id = ?
                """, (
                    json.dumps(structured_content, ensure_ascii=False),
                    text_format,
                    json.dumps(tree_structure, ensure_ascii=False),
                    disease_id,
                    disease_name,
                    source,
                    decision_id,
                    doctor_id
                ))

                if cursor.rowcount == 0:
                    conn.close()
                    return False, "记录不存在或无权限", None

                message = "更新决策记录成功"

            # 步骤5: 保存历史版本
            cursor.execute("""
                INSERT INTO clinical_decision_history (
                    decision_id, version, structured_content, text_format, tree_structure, modified_from
                ) SELECT id, version, structured_content, text_format, tree_structure, ?
                FROM clinical_decision_data WHERE id = ?
            """, (source, decision_id))

            conn.commit()
            conn.close()

            # 步骤6: 返回完整数据
            complete_data = {
                "id": decision_id,
                "structured_content": structured_content,
                "text_format": text_format,
                "tree_structure": tree_structure,
                "disease_name": disease_name
            }

            return True, message, complete_data

        except Exception as e:
            if conn:
                conn.rollback()
                conn.close()
            return False, f"保存失败: {str(e)}", None

    def get_decision_data(
        self,
        decision_id: str,
        doctor_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取决策数据

        Args:
            decision_id: 决策记录ID
            doctor_id: 医生ID

        Returns:
            完整数据或None
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, doctor_id, disease_id, disease_name,
                       structured_content, text_format, tree_structure,
                       version, last_modified_from, created_at, updated_at
                FROM clinical_decision_data
                WHERE id = ? AND doctor_id = ? AND is_active = 1
            """, (decision_id, doctor_id))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return {
                "id": row["id"],
                "doctor_id": row["doctor_id"],
                "disease_id": row["disease_id"],
                "disease_name": row["disease_name"],
                "structured_content": json.loads(row["structured_content"]),
                "text_format": row["text_format"],
                "tree_structure": json.loads(row["tree_structure"]),
                "version": row["version"],
                "last_modified_from": row["last_modified_from"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }

        except Exception as e:
            return None

    # ============================================
    # 辅助解析方法
    # ============================================

    def _parse_symptoms(self, symptoms_text: str, category: str) -> List[Dict[str, Any]]:
        """解析症状文本"""
        symptoms = []
        # 按顿号、逗号或空格分割
        parts = re.split(r'[、，,\s]+', symptoms_text)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # 提取严重程度
            severity_match = re.search(r'[（(](.+?)[）)]', part)
            severity = severity_match.group(1) if severity_match else "中"
            symptom_name = re.sub(r'[（(].+?[）)]', '', part).strip()

            # 从标准库查询症状
            symptom_info = self._get_symptom_from_standard(symptom_name)

            if symptom_info:
                symptoms.append({
                    "id": symptom_info["id"],
                    "name": symptom_info["name"],
                    "category": category,
                    "severity": severity
                })
            else:
                symptoms.append({
                    "id": f"symptom_{uuid.uuid4().hex[:8]}",
                    "name": symptom_name,
                    "category": category,
                    "severity": severity
                })

        return symptoms

    def _parse_tongue(self, tongue_text: str) -> Dict[str, str]:
        """解析舌象"""
        tongue = {}

        # 尝试解析舌质和舌苔
        if "舌" in tongue_text:
            parts = tongue_text.split("，")
            for part in parts:
                if "舌" in part and "苔" not in part:
                    tongue["body"] = part.replace("舌", "").strip()
                elif "苔" in part:
                    tongue["coating"] = part.replace("苔", "").strip()
        else:
            tongue["description"] = tongue_text

        return tongue

    def _parse_pulse(self, pulse_text: str) -> Dict[str, str]:
        """解析脉象"""
        pulse_text = pulse_text.replace("脉", "").strip()
        return {
            "type": pulse_text,
            "description": pulse_text
        }

    def _parse_formula(self, formula_text: str) -> List[Dict[str, Any]]:
        """解析方剂组成"""
        composition = []
        # 按顿号、加号或空格分割
        parts = re.split(r'[、+\s]+', formula_text)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # 提取药名、剂量、单位、角色
            # 格式: 麻黄9克(君药) 或 麻黄9克
            role_match = re.search(r'[（(](.+?)[）)]', part)
            role = role_match.group(1) if role_match else ""

            part_without_role = re.sub(r'[（(].+?[）)]', '', part).strip()

            # 提取剂量和单位
            dosage_match = re.search(r'(\d+(?:\.\d+)?)(克|g|枚|片|钱)?', part_without_role)

            if dosage_match:
                dosage = float(dosage_match.group(1))
                unit = dosage_match.group(2) or "克"
                herb_name = part_without_role[:dosage_match.start()].strip()
            else:
                dosage = 0
                unit = "克"
                herb_name = part_without_role

            # 从标准库查询药材
            herb_info = self._get_herb_from_standard(herb_name)

            composition.append({
                "herb_id": herb_info["id"] if herb_info else f"herb_{uuid.uuid4().hex[:8]}",
                "name": herb_name,
                "dosage": dosage,
                "unit": unit,
                "role": role,
                "effect": herb_info.get("effects", "") if herb_info else ""
            })

        return composition

    def _format_symptoms(self, symptoms: List[Dict[str, Any]]) -> str:
        """格式化症状列表为文本"""
        parts = []
        for symptom in symptoms:
            name = symptom["name"]
            severity = symptom.get("severity", "")
            if severity and severity != "中":
                parts.append(f"{name}（{severity}）")
            else:
                parts.append(name)
        return "、".join(parts)

    def _format_tongue(self, tongue: Dict[str, str]) -> str:
        """格式化舌象为文本"""
        parts = []
        if tongue.get("body"):
            parts.append(f"舌{tongue['body']}")
        if tongue.get("coating"):
            parts.append(f"苔{tongue['coating']}")
        if not parts and tongue.get("description"):
            return tongue["description"]
        return "，".join(parts)

    def _format_pulse(self, pulse: Dict[str, str]) -> str:
        """格式化脉象为文本"""
        pulse_type = pulse.get("type", "")
        if pulse_type:
            return f"脉{pulse_type}"
        return pulse.get("description", "")

    def _infer_syndrome_type(self, syndrome_name: str) -> str:
        """推断证候类型"""
        if "虚" in syndrome_name:
            return "虚证"
        elif "实" in syndrome_name or "表" in syndrome_name or "热" in syndrome_name or "寒" in syndrome_name:
            return "实证"
        else:
            return "虚实夹杂"

    # ============================================
    # 数据库标准库查询
    # ============================================

    def _get_disease_from_standard(self, disease_name: str) -> Optional[Dict[str, Any]]:
        """从标准库查询疾病"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, category, description
                FROM tcm_diseases_standard
                WHERE name = ? OR alias LIKE ?
            """, (disease_name, f'%{disease_name}%'))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def _get_symptom_from_standard(self, symptom_name: str) -> Optional[Dict[str, Any]]:
        """从标准库查询症状"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, category
                FROM tcm_symptoms_standard
                WHERE name = ?
            """, (symptom_name,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def _get_prescription_from_standard(self, prescription_name: str) -> Optional[Dict[str, Any]]:
        """从标准库查询处方"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, source, category, composition, effects, indications
                FROM tcm_prescriptions_standard
                WHERE name = ? OR alias LIKE ?
            """, (prescription_name, f'%{prescription_name}%'))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def _get_herb_from_standard(self, herb_name: str) -> Optional[Dict[str, Any]]:
        """从标准库查询中药"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, effects
                FROM tcm_herbs_standard
                WHERE name = ? OR alias LIKE ?
            """, (herb_name, f'%{herb_name}%'))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None
