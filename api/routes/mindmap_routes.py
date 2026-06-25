#!/usr/bin/env python3
"""
思维导图API路由
提供思维导图的生成、保存、加载功能
"""

import logging
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import datetime
import sqlite3

from core.mindmap import mindmap_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mindmap", tags=["mindmap"])


# 请求/响应模型
class GenerateMindMapRequest(BaseModel):
    """生成思维导图请求"""
    topic: str = Field(..., min_length=2, max_length=100, description="主题标题")
    description: str = Field(..., min_length=5, max_length=1000, description="详细描述")
    domain: str = Field(default="general", description="应用领域: medical/technical/business/general")
    max_levels: int = Field(default=4, ge=2, le=6, description="最大层级数")
    max_children: int = Field(default=5, ge=2, le=10, description="每节点最大子节点数")


class SaveMindMapRequest(BaseModel):
    """保存思维导图请求"""
    mindmap_id: str
    title: str
    description: str
    domain: str
    data: Dict[str, Any]
    user_id: Optional[str] = None


class MindMapResponse(BaseModel):
    """思维导图响应"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# 数据库路径
DB_PATH = "/home/ute/tcm-ai/data/user_history.sqlite"


def init_mindmap_table():
    """初始化思维导图数据表"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mindmaps (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                domain TEXT DEFAULT 'general',
                data TEXT NOT NULL,
                user_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()
        logger.info("✅ 思维导图数据表初始化成功")

    except Exception as e:
        logger.error(f"❌ 初始化数据表失败: {str(e)}")


# 启动时初始化表
init_mindmap_table()


@router.post("/generate", response_model=MindMapResponse)
async def generate_mindmap(request: GenerateMindMapRequest):
    """
    生成思维导图

    使用AI自动分析主题，生成结构化的思维导图
    """
    try:
        logger.info(f"📝 收到思维导图生成请求: {request.topic}")

        # 调用生成器
        mindmap = mindmap_generator.generate_mindmap(
            topic=request.topic,
            description=request.description,
            domain=request.domain,
            max_levels=request.max_levels,
            max_children=request.max_children
        )

        # 转换为字典
        mindmap_dict = mindmap_generator.export_to_dict(mindmap)

        # 转换为ECharts格式
        echarts_data = mindmap_generator.export_to_echarts_format(mindmap)

        return MindMapResponse(
            success=True,
            message="思维导图生成成功",
            data={
                "mindmap": mindmap_dict,
                "echarts": echarts_data
            }
        )

    except Exception as e:
        logger.error(f"❌ 生成思维导图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/save", response_model=MindMapResponse)
async def save_mindmap(request: SaveMindMapRequest):
    """
    保存思维导图

    将思维导图保存到数据库
    """
    try:
        logger.info(f"💾 保存思维导图: {request.mindmap_id}")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        # 检查是否已存在
        cursor.execute(
            "SELECT id FROM mindmaps WHERE id = ?",
            (request.mindmap_id,)
        )
        existing = cursor.fetchone()

        data_json = json.dumps(request.data, ensure_ascii=False)

        if existing:
            # 更新
            cursor.execute("""
                UPDATE mindmaps
                SET title = ?, description = ?, domain = ?, data = ?, updated_at = ?
                WHERE id = ?
            """, (
                request.title,
                request.description,
                request.domain,
                data_json,
                now,
                request.mindmap_id
            ))
            message = "思维导图更新成功"
        else:
            # 插入
            cursor.execute("""
                INSERT INTO mindmaps (id, title, description, domain, data, user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.mindmap_id,
                request.title,
                request.description,
                request.domain,
                data_json,
                request.user_id,
                now,
                now
            ))
            message = "思维导图保存成功"

        conn.commit()
        conn.close()

        return MindMapResponse(
            success=True,
            message=message,
            data={"mindmap_id": request.mindmap_id}
        )

    except Exception as e:
        logger.error(f"❌ 保存思维导图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@router.get("/load/{mindmap_id}", response_model=MindMapResponse)
async def load_mindmap(mindmap_id: str):
    """
    加载思维导图

    从数据库加载指定ID的思维导图
    """
    try:
        logger.info(f"📂 加载思维导图: {mindmap_id}")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, description, domain, data, created_at, updated_at
            FROM mindmaps
            WHERE id = ?
        """, (mindmap_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="思维导图不存在")

        mindmap_data = {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "domain": row[3],
            "data": json.loads(row[4]),
            "created_at": row[5],
            "updated_at": row[6]
        }

        return MindMapResponse(
            success=True,
            message="加载成功",
            data=mindmap_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 加载思维导图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"加载失败: {str(e)}")


@router.get("/list", response_model=MindMapResponse)
async def list_mindmaps(user_id: Optional[str] = None, limit: int = 20):
    """
    获取思维导图列表

    返回所有或指定用户的思维导图列表
    """
    try:
        logger.info(f"📋 获取思维导图列表 (user_id: {user_id})")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if user_id:
            cursor.execute("""
                SELECT id, title, description, domain, created_at, updated_at
                FROM mindmaps
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (user_id, limit))
        else:
            cursor.execute("""
                SELECT id, title, description, domain, created_at, updated_at
                FROM mindmaps
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        mindmaps = [
            {
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "domain": row[3],
                "created_at": row[4],
                "updated_at": row[5]
            }
            for row in rows
        ]

        return MindMapResponse(
            success=True,
            message=f"找到 {len(mindmaps)} 个思维导图",
            data={"mindmaps": mindmaps}
        )

    except Exception as e:
        logger.error(f"❌ 获取列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.delete("/delete/{mindmap_id}", response_model=MindMapResponse)
async def delete_mindmap(mindmap_id: str):
    """
    删除思维导图

    从数据库删除指定ID的思维导图
    """
    try:
        logger.info(f"🗑️ 删除思维导图: {mindmap_id}")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM mindmaps WHERE id = ?", (mindmap_id,))
        deleted = cursor.rowcount

        conn.commit()
        conn.close()

        if deleted == 0:
            raise HTTPException(status_code=404, detail="思维导图不存在")

        return MindMapResponse(
            success=True,
            message="删除成功",
            data={"mindmap_id": mindmap_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
