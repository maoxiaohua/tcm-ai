"""
决策树数据驱动API路由
提供决策树数据的CRUD和AI生成功能

版本: v3.0
日期: 2025-10-31
"""

import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.decision_tree_data_service import DecisionTreeDataService
from app.core.settings import AI_CONFIG
import dashscope


# ============================================
# 请求/响应模型
# ============================================

class GenerateFromTextRequest(BaseModel):
    """AI生成请求"""
    natural_language: str = Field(..., description="自然语言描述")
    doctor_id: str = Field(..., description="医生ID")


class SaveFromTextRequest(BaseModel):
    """从文本保存请求"""
    text_content: str = Field(..., description="文本内容")
    doctor_id: str = Field(..., description="医生ID")
    decision_id: Optional[str] = Field(None, description="决策记录ID（更新时提供）")


class SaveFromCanvasRequest(BaseModel):
    """从画布保存请求"""
    tree_structure: Dict[str, Any] = Field(..., description="树形结构")
    doctor_id: str = Field(..., description="医生ID")
    decision_id: Optional[str] = Field(None, description="决策记录ID（更新时提供）")


class ValidateRequest(BaseModel):
    """数据验证请求"""
    structured_content: Dict[str, Any] = Field(..., description="结构化内容")


class DecisionListQuery(BaseModel):
    """决策列表查询"""
    doctor_id: str = Field(..., description="医生ID")
    disease_name: Optional[str] = Field(None, description="疾病名称过滤")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


# ============================================
# 路由定义
# ============================================

router = APIRouter(prefix="/api/decision-tree-data", tags=["决策树数据"])

# 初始化服务
data_service = DecisionTreeDataService()

# 初始化dashscope
DASHSCOPE_API_KEY = AI_CONFIG.get("dashscope_api_key", "")
if DASHSCOPE_API_KEY:
    dashscope.api_key = DASHSCOPE_API_KEY


@router.post("/generate")
async def generate_from_natural_language(request: GenerateFromTextRequest):
    """
    AI生成决策树数据

    从自然语言描述生成标准格式的决策树数据
    """
    try:
        # 构建AI提示词
        prompt = f"""
你是一位资深中医专家，请根据以下自然语言描述，生成标准化的中医诊疗决策数据。

自然语言描述：
{request.natural_language}

请按照以下标准格式生成：

【疾病】疾病名称
【主症】主要症状（用"、"分隔，严重程度用括号标注，如：恶寒发热（重）、头痛（中））
【兼症】次要症状（用"、"分隔）
【舌象】舌质和舌苔描述
【脉象】脉象描述
【证候】证候名称
【处方】处方名称
【方剂】方剂组成（格式：药名+剂量+单位(角色)，用"+"分隔，如：麻黄9克(君药) + 桂枝6克(臣药)）

要求：
1. 严格按照上述格式输出
2. 症状描述准确、专业
3. 处方必须是经典方剂或临床常用方
4. 剂量符合临床常规用量
5. 只输出格式化文本，不要有其他说明

请生成：
"""

        # 调用AI生成
        try:
            response = dashscope.Generation.call(
                model='qwen-max',
                messages=[{"role": "user", "content": prompt}],
                result_format='message'
            )

            if response.status_code != 200 or not response.output:
                raise HTTPException(status_code=500, detail="AI生成失败")

            generated_text = response.output.choices[0].message.content

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI调用失败: {str(e)}")

        # 转换为结构化数据
        try:
            structured_content = data_service.text_to_structured(generated_text, request.doctor_id)
            text_format = data_service.structured_to_text(structured_content)
            tree_structure = data_service.structured_to_tree(structured_content)

            return {
                "success": True,
                "message": "AI生成成功",
                "data": {
                    "structured_content": structured_content,
                    "text_format": text_format,
                    "tree_structure": tree_structure,
                    "original_ai_output": generated_text
                }
            }

        except ValueError as e:
            # AI生成的格式不标准，返回原始文本让用户手动编辑
            return {
                "success": True,
                "message": "AI生成完成，但格式需要调整",
                "data": {
                    "structured_content": None,
                    "text_format": generated_text,
                    "tree_structure": None,
                    "original_ai_output": generated_text,
                    "parse_error": str(e)
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/save-from-text")
async def save_from_text(request: SaveFromTextRequest):
    """
    从文本格式保存并同步

    保存左侧文本编辑器的内容，自动生成右侧画布
    """
    try:
        success, message, data = data_service.save_and_sync(
            doctor_id=request.doctor_id,
            content=request.text_content,
            source="text",
            decision_id=request.decision_id
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {
            "success": True,
            "message": message,
            "data": data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@router.post("/save-from-canvas")
async def save_from_canvas(request: SaveFromCanvasRequest):
    """
    从画布格式保存并同步

    保存右侧画布的内容，自动生成左侧文本
    """
    try:
        success, message, data = data_service.save_and_sync(
            doctor_id=request.doctor_id,
            content=request.tree_structure,
            source="canvas",
            decision_id=request.decision_id
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {
            "success": True,
            "message": message,
            "data": data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@router.get("/{decision_id}")
async def get_decision_data(decision_id: str, doctor_id: str):
    """
    获取决策数据

    返回指定ID的完整决策数据（三种格式）
    """
    try:
        data = data_service.get_decision_data(decision_id, doctor_id)

        if not data:
            raise HTTPException(status_code=404, detail="决策记录不存在")

        return {
            "success": True,
            "message": "获取成功",
            "data": data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.post("/{decision_id}/validate")
async def validate_decision_data(decision_id: str, doctor_id: str, request: ValidateRequest):
    """
    验证决策数据一致性

    检查三种格式的数据是否一致
    """
    try:
        # 获取数据库中的数据
        db_data = data_service.get_decision_data(decision_id, doctor_id)
        if not db_data:
            raise HTTPException(status_code=404, detail="决策记录不存在")

        # 生成各种格式
        text_format = data_service.structured_to_text(request.structured_content)
        tree_structure = data_service.structured_to_tree(request.structured_content)

        # 比较一致性
        inconsistencies = []

        # 比较文本格式
        if text_format != db_data["text_format"]:
            inconsistencies.append({
                "field": "text_format",
                "message": "文本格式不一致",
                "expected": db_data["text_format"],
                "actual": text_format
            })

        # 比较树形结构（简化比较：节点数量）
        db_tree = db_data["tree_structure"]
        if len(tree_structure.get("nodes", [])) != len(db_tree.get("nodes", [])):
            inconsistencies.append({
                "field": "tree_structure.nodes",
                "message": "节点数量不一致",
                "expected": len(db_tree.get("nodes", [])),
                "actual": len(tree_structure.get("nodes", []))
            })

        is_consistent = len(inconsistencies) == 0

        return {
            "success": True,
            "message": "验证完成",
            "data": {
                "is_consistent": is_consistent,
                "inconsistencies": inconsistencies,
                "generated_text": text_format,
                "generated_tree": tree_structure
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证失败: {str(e)}")


@router.post("/list")
async def list_decisions(query: DecisionListQuery):
    """
    查询决策列表

    支持分页和疾病名称过滤
    """
    try:
        import sqlite3

        conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 构建查询
        where_clauses = ["doctor_id = ?", "is_active = 1"]
        params = [query.doctor_id]

        if query.disease_name:
            where_clauses.append("disease_name LIKE ?")
            params.append(f"%{query.disease_name}%")

        where_sql = " AND ".join(where_clauses)

        # 查询总数
        cursor.execute(f"""
            SELECT COUNT(*) as total
            FROM clinical_decision_data
            WHERE {where_sql}
        """, params)
        total = cursor.fetchone()["total"]

        # 查询列表
        offset = (query.page - 1) * query.page_size
        params.extend([query.page_size, offset])

        cursor.execute(f"""
            SELECT id, disease_name, version, modification_count,
                   usage_count, last_modified_from, created_at, updated_at
            FROM clinical_decision_data
            WHERE {where_sql}
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """, params)

        rows = cursor.fetchall()
        conn.close()

        items = [dict(row) for row in rows]

        return {
            "success": True,
            "message": "查询成功",
            "data": {
                "total": total,
                "page": query.page,
                "page_size": query.page_size,
                "items": items
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.delete("/{decision_id}")
async def delete_decision(decision_id: str, doctor_id: str):
    """
    删除决策记录（软删除）

    将is_active设置为0
    """
    try:
        import sqlite3

        conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE clinical_decision_data
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND doctor_id = ?
        """, (decision_id, doctor_id))

        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="决策记录不存在或无权限")

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": "删除成功",
            "data": {"id": decision_id}
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.get("/{decision_id}/history")
async def get_decision_history(decision_id: str, doctor_id: str):
    """
    获取决策历史版本

    返回所有历史版本列表
    """
    try:
        import sqlite3

        conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 验证权限
        cursor.execute("""
            SELECT id FROM clinical_decision_data
            WHERE id = ? AND doctor_id = ?
        """, (decision_id, doctor_id))

        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="决策记录不存在或无权限")

        # 查询历史
        cursor.execute("""
            SELECT id, version, modified_from, created_at, notes
            FROM clinical_decision_history
            WHERE decision_id = ?
            ORDER BY version DESC
        """, (decision_id,))

        rows = cursor.fetchall()
        conn.close()

        history = [dict(row) for row in rows]

        return {
            "success": True,
            "message": "获取历史成功",
            "data": {
                "decision_id": decision_id,
                "total_versions": len(history),
                "history": history
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.get("/{decision_id}/history/{version}")
async def get_decision_history_version(decision_id: str, version: int, doctor_id: str):
    """
    获取指定历史版本的完整数据

    用于版本回滚
    """
    try:
        import sqlite3

        conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 验证权限
        cursor.execute("""
            SELECT id FROM clinical_decision_data
            WHERE id = ? AND doctor_id = ?
        """, (decision_id, doctor_id))

        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="决策记录不存在或无权限")

        # 查询历史版本
        cursor.execute("""
            SELECT structured_content, text_format, tree_structure, modified_from, created_at
            FROM clinical_decision_history
            WHERE decision_id = ? AND version = ?
        """, (decision_id, version))

        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="历史版本不存在")

        return {
            "success": True,
            "message": "获取历史版本成功",
            "data": {
                "decision_id": decision_id,
                "version": version,
                "structured_content": json.loads(row["structured_content"]),
                "text_format": row["text_format"],
                "tree_structure": json.loads(row["tree_structure"]),
                "modified_from": row["modified_from"],
                "created_at": row["created_at"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史版本失败: {str(e)}")
