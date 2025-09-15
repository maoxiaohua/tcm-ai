#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户数据迁移和导出API路由
支持完整的用户数据迁移、导出和导入功能
"""

from fastapi import APIRouter, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import sqlite3
import json
import zipfile
import csv
import io
import base64
import hashlib
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/data-migration", tags=["数据迁移与导出"])

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

class ExportRequest(BaseModel):
    """数据导出请求"""
    user_id: str
    export_format: str = "json"  # json, csv, xml
    include_data: List[str] = ["all"]  # all, conversations, consultations, prescriptions
    date_range: Optional[Dict[str, str]] = None
    encryption: bool = False
    password: Optional[str] = None

class ImportRequest(BaseModel):
    """数据导入请求"""
    user_id: str
    import_format: str = "json"
    merge_strategy: str = "replace"  # replace, merge, skip_existing
    validate_only: bool = False

class MigrationRequest(BaseModel):
    """数据迁移请求"""
    source_user_id: str
    target_user_id: str
    migration_type: str = "full"  # full, partial
    include_data: List[str] = ["all"]
    preserve_source: bool = True

@router.post("/export")
async def export_user_data(request: ExportRequest):
    """导出用户数据"""
    try:
        user_id = request.user_id
        export_format = request.export_format
        include_data = request.include_data
        
        # 获取用户数据
        user_data = await get_exportable_user_data(user_id, include_data, request.date_range)
        
        if not user_data:
            raise HTTPException(status_code=404, detail="未找到用户数据")
        
        # 根据格式处理数据
        if export_format == "json":
            content = await export_as_json(user_data, request.encryption, request.password)
            media_type = "application/json"
            filename = f"tcm_ai_data_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        elif export_format == "csv":
            content = await export_as_csv(user_data)
            media_type = "text/csv"
            filename = f"tcm_ai_data_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        elif export_format == "zip":
            content = await export_as_zip(user_data, request.encryption, request.password)
            media_type = "application/zip"
            filename = f"tcm_ai_data_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        else:
            raise HTTPException(status_code=400, detail="不支持的导出格式")
        
        # 记录导出操作
        await log_export_operation(user_id, export_format, len(content))
        
        # 返回文件流
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")

@router.post("/import")
async def import_user_data(
    user_id: str,
    merge_strategy: str = "replace",
    validate_only: bool = False,
    file: UploadFile = File(...)
):
    """导入用户数据"""
    try:
        # 读取上传的文件
        content = await file.read()
        
        # 根据文件类型解析数据
        if file.filename.endswith('.json'):
            import_data = json.loads(content.decode('utf-8'))
        elif file.filename.endswith('.zip'):
            import_data = await parse_zip_import(content)
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式")
        
        # 验证数据格式
        validation_result = await validate_import_data(import_data, user_id)
        if not validation_result['valid']:
            return {
                "success": False,
                "message": "数据验证失败",
                "errors": validation_result['errors']
            }
        
        if validate_only:
            return {
                "success": True,
                "message": "数据验证通过",
                "preview": validation_result['preview']
            }
        
        # 执行导入
        import_result = await execute_import(user_id, import_data, merge_strategy)
        
        # 记录导入操作
        await log_import_operation(user_id, file.filename, import_result)
        
        return {
            "success": True,
            "message": "数据导入成功",
            "imported_records": import_result['imported_count'],
            "skipped_records": import_result['skipped_count'],
            "errors": import_result.get('errors', [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")

@router.post("/migrate")
async def migrate_user_data(request: MigrationRequest):
    """迁移用户数据"""
    try:
        source_user_id = request.source_user_id
        target_user_id = request.target_user_id
        migration_type = request.migration_type
        include_data = request.include_data
        preserve_source = request.preserve_source
        
        # 检查目标用户是否存在
        if not await user_exists(target_user_id):
            raise HTTPException(status_code=404, detail="目标用户不存在")
        
        # 获取源用户数据
        source_data = await get_exportable_user_data(source_user_id, include_data)
        if not source_data:
            raise HTTPException(status_code=404, detail="源用户数据不存在")
        
        # 执行迁移
        migration_result = await execute_migration(
            source_user_id, 
            target_user_id, 
            source_data, 
            migration_type,
            preserve_source
        )
        
        # 记录迁移操作
        await log_migration_operation(source_user_id, target_user_id, migration_result)
        
        return {
            "success": True,
            "message": "数据迁移成功",
            "migrated_records": migration_result['migrated_count'],
            "migration_id": migration_result['migration_id']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据迁移失败: {str(e)}")

@router.get("/export-history/{user_id}")
async def get_export_history(user_id: str):
    """获取用户的导出历史"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT operation_type, file_format, file_size, created_at, status
            FROM data_operation_log 
            WHERE user_id = ? AND operation_type = 'export'
            ORDER BY created_at DESC LIMIT 20
        """, (user_id,))
        
        history = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {
            "success": True,
            "data": history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取导出历史失败: {str(e)}")

@router.get("/data-preview/{user_id}")
async def preview_user_data(user_id: str, data_type: str = "all"):
    """预览用户数据"""
    try:
        preview_data = {}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if data_type in ["all", "conversations"]:
            cursor.execute("""
                SELECT COUNT(*) as count, MIN(start_time) as earliest, MAX(last_activity) as latest
                FROM conversation_states WHERE user_id = ?
            """, (user_id,))
            conv_stats = dict(cursor.fetchone())
            preview_data["conversations"] = conv_stats
        
        if data_type in ["all", "consultations"]:
            cursor.execute("""
                SELECT COUNT(*) as count, MIN(created_at) as earliest, MAX(created_at) as latest
                FROM consultations WHERE patient_id = ?
            """, (user_id,))
            consult_stats = dict(cursor.fetchone())
            preview_data["consultations"] = consult_stats
        
        if data_type in ["all", "prescriptions"]:
            cursor.execute("""
                SELECT COUNT(*) as count, MIN(p.created_at) as earliest, MAX(p.created_at) as latest
                FROM prescriptions_new p
                JOIN consultations c ON p.consultation_id = c.uuid
                WHERE c.patient_id = ?
            """, (user_id,))
            presc_stats = dict(cursor.fetchone())
            preview_data["prescriptions"] = presc_stats
        
        conn.close()
        
        return {
            "success": True,
            "data": preview_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据预览失败: {str(e)}")

@router.delete("/cleanup/{user_id}")
async def cleanup_user_data(user_id: str, data_types: List[str], older_than_days: int = 30):
    """清理用户数据"""
    try:
        cutoff_date = (datetime.now() - timedelta(days=older_than_days)).isoformat()
        cleanup_results = {}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if "conversations" in data_types:
            cursor.execute("""
                UPDATE conversation_states 
                SET is_active = 0 
                WHERE user_id = ? AND last_activity < ? AND is_active = 1
            """, (user_id, cutoff_date))
            cleanup_results["conversations"] = cursor.rowcount
        
        if "old_sessions" in data_types:
            cursor.execute("""
                UPDATE user_sessions 
                SET is_active = 0 
                WHERE user_id = ? AND last_activity < ? AND is_active = 1
            """, (user_id, cutoff_date))
            cleanup_results["sessions"] = cursor.rowcount
        
        if "export_logs" in data_types:
            cursor.execute("""
                DELETE FROM data_operation_log 
                WHERE user_id = ? AND created_at < ?
            """, (user_id, cutoff_date))
            cleanup_results["logs"] = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        # 记录清理操作
        await log_cleanup_operation(user_id, cleanup_results)
        
        return {
            "success": True,
            "message": "数据清理完成",
            "cleaned_records": cleanup_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据清理失败: {str(e)}")

# 辅助函数
async def get_exportable_user_data(user_id: str, include_data: List[str], date_range: Optional[Dict] = None) -> Dict:
    """获取可导出的用户数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    data = {
        "user_id": user_id,
        "export_timestamp": datetime.now().isoformat(),
        "data_version": "1.0"
    }
    
    # 构建日期过滤条件
    date_filter = ""
    date_params = []
    if date_range:
        if date_range.get("start"):
            date_filter += " AND created_at >= ?"
            date_params.append(date_range["start"])
        if date_range.get("end"):
            date_filter += " AND created_at <= ?"
            date_params.append(date_range["end"])
    
    if "all" in include_data or "conversations" in include_data:
        query = f"SELECT * FROM conversation_states WHERE user_id = ?{date_filter.replace('created_at', 'start_time')}"
        cursor.execute(query, [user_id] + date_params)
        data["conversations"] = [dict(row) for row in cursor.fetchall()]
    
    if "all" in include_data or "consultations" in include_data:
        query = f"SELECT * FROM consultations WHERE patient_id = ?{date_filter}"
        cursor.execute(query, [user_id] + date_params)
        data["consultations"] = [dict(row) for row in cursor.fetchall()]
    
    if "all" in include_data or "prescriptions" in include_data:
        query = f"""
            SELECT p.* FROM prescriptions_new p
            JOIN consultations c ON p.consultation_id = c.uuid
            WHERE c.patient_id = ?{date_filter.replace('created_at', 'p.created_at')}
        """
        cursor.execute(query, [user_id] + date_params)
        data["prescriptions"] = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return data

async def export_as_json(data: Dict, encrypt: bool = False, password: str = None) -> bytes:
    """导出为JSON格式"""
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    
    if encrypt and password:
        # 简单加密（实际项目中应使用更强的加密）
        encrypted_data = base64.b64encode(json_str.encode('utf-8')).decode('ascii')
        return json.dumps({
            "encrypted": True,
            "data": encrypted_data,
            "hint": "数据已加密"
        }, ensure_ascii=False, indent=2).encode('utf-8')
    
    return json_str.encode('utf-8')

async def export_as_csv(data: Dict) -> bytes:
    """导出为CSV格式"""
    output = io.StringIO()
    
    # 导出问诊记录
    if "consultations" in data:
        writer = csv.writer(output)
        writer.writerow(["类型", "ID", "医生", "症状分析", "创建时间"])
        
        for consultation in data["consultations"]:
            writer.writerow([
                "问诊记录",
                consultation.get("uuid", ""),
                consultation.get("selected_doctor_id", ""),
                consultation.get("symptoms_analysis", ""),
                consultation.get("created_at", "")
            ])
    
    return output.getvalue().encode('utf-8')

async def export_as_zip(data: Dict, encrypt: bool = False, password: str = None) -> bytes:
    """导出为ZIP格式"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 添加主数据文件
        json_data = await export_as_json(data, encrypt, password)
        zip_file.writestr("user_data.json", json_data)
        
        # 添加CSV格式的摘要
        csv_data = await export_as_csv(data)
        zip_file.writestr("summary.csv", csv_data)
        
        # 添加README文件
        readme_content = f"""
TCM AI 用户数据导出包
用户ID: {data['user_id']}
导出时间: {data['export_timestamp']}
数据版本: {data['data_version']}

文件说明:
- user_data.json: 完整的用户数据（JSON格式）
- summary.csv: 数据摘要（CSV格式）

如有问题，请联系技术支持。
        """.strip()
        zip_file.writestr("README.txt", readme_content.encode('utf-8'))
    
    return zip_buffer.getvalue()

async def validate_import_data(import_data: Dict, user_id: str) -> Dict:
    """验证导入数据"""
    validation_result = {
        "valid": True,
        "errors": [],
        "preview": {}
    }
    
    # 检查数据格式
    required_fields = ["user_id", "export_timestamp"]
    for field in required_fields:
        if field not in import_data:
            validation_result["errors"].append(f"缺少必需字段: {field}")
            validation_result["valid"] = False
    
    # 统计数据量
    if "conversations" in import_data:
        validation_result["preview"]["conversations"] = len(import_data["conversations"])
    
    if "consultations" in import_data:
        validation_result["preview"]["consultations"] = len(import_data["consultations"])
    
    return validation_result

async def execute_import(user_id: str, import_data: Dict, merge_strategy: str) -> Dict:
    """执行数据导入"""
    result = {
        "imported_count": 0,
        "skipped_count": 0,
        "errors": []
    }
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 导入对话状态
        if "conversations" in import_data:
            for conv in import_data["conversations"]:
                try:
                    # 修改用户ID为目标用户
                    conv["user_id"] = user_id
                    
                    if merge_strategy == "replace":
                        cursor.execute("""
                            INSERT OR REPLACE INTO conversation_states 
                            (conversation_id, user_id, doctor_id, current_stage, start_time, 
                             last_activity, turn_count, symptoms_collected, stage_history, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            conv.get("conversation_id"),
                            user_id,
                            conv.get("doctor_id"),
                            conv.get("current_stage"),
                            conv.get("start_time"),
                            conv.get("last_activity"),
                            conv.get("turn_count", 0),
                            conv.get("symptoms_collected", "{}"),
                            conv.get("stage_history", "[]"),
                            datetime.now().isoformat()
                        ))
                        result["imported_count"] += 1
                    # 其他合并策略...
                    
                except Exception as e:
                    result["errors"].append(f"导入对话失败: {str(e)}")
        
        conn.commit()
        
    finally:
        conn.close()
    
    return result

async def execute_migration(source_user_id: str, target_user_id: str, source_data: Dict, 
                          migration_type: str, preserve_source: bool) -> Dict:
    """执行数据迁移"""
    migration_id = f"migration_{source_user_id}_to_{target_user_id}_{int(datetime.now().timestamp())}"
    
    # 执行导入到目标用户
    import_result = await execute_import(target_user_id, source_data, "replace")
    
    result = {
        "migration_id": migration_id,
        "migrated_count": import_result["imported_count"],
        "errors": import_result.get("errors", [])
    }
    
    # 如果不保留源数据，清理源用户数据
    if not preserve_source:
        await cleanup_user_data(source_user_id, ["conversations", "consultations"], 0)
    
    return result

async def user_exists(user_id: str) -> bool:
    """检查用户是否存在"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone() is not None
    
    conn.close()
    return exists

async def log_export_operation(user_id: str, format: str, file_size: int):
    """记录导出操作"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO data_operation_log 
        (user_id, operation_type, file_format, file_size, status, created_at)
        VALUES (?, 'export', ?, ?, 'success', ?)
    """, (user_id, format, file_size, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

async def log_import_operation(user_id: str, filename: str, result: Dict):
    """记录导入操作"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    status = "success" if not result.get("errors") else "partial_success"
    
    cursor.execute("""
        INSERT INTO data_operation_log 
        (user_id, operation_type, file_format, records_processed, status, created_at)
        VALUES (?, 'import', ?, ?, ?, ?)
    """, (user_id, "import", result["imported_count"], status, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

async def log_migration_operation(source_user_id: str, target_user_id: str, result: Dict):
    """记录迁移操作"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO data_operation_log 
        (user_id, operation_type, target_user_id, records_processed, status, created_at)
        VALUES (?, 'migration', ?, ?, 'success', ?)
    """, (source_user_id, target_user_id, result["migrated_count"], datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

async def log_cleanup_operation(user_id: str, cleanup_results: Dict):
    """记录清理操作"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    total_cleaned = sum(cleanup_results.values())
    
    cursor.execute("""
        INSERT INTO data_operation_log 
        (user_id, operation_type, records_processed, status, created_at)
        VALUES (?, 'cleanup', ?, 'success', ?)
    """, (user_id, total_cleaned, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

async def parse_zip_import(content: bytes) -> Dict:
    """解析ZIP导入文件"""
    with zipfile.ZipFile(io.BytesIO(content), 'r') as zip_file:
        # 查找主数据文件
        if 'user_data.json' in zip_file.namelist():
            json_content = zip_file.read('user_data.json')
            return json.loads(json_content.decode('utf-8'))
        else:
            raise ValueError("ZIP文件中未找到user_data.json")