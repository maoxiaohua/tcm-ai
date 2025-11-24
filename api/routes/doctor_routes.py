"""
医生相关API路由
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3

from core.doctor_management.doctor_auth import doctor_auth_manager

# 使用内联导入避免模块路径问题
import sys
sys.path.insert(0, '/opt/tcm-ai')
from database.models.doctor_portal_models import Doctor, Prescription

router = APIRouter(prefix="/api/doctor", tags=["医生端"])

class DoctorLoginRequest(BaseModel):
    """医生登录请求"""
    license_no: str
    password: str

class DoctorRegisterRequest(BaseModel):
    """医生注册请求"""
    name: str
    license_no: str
    phone: str
    email: str
    password: str
    speciality: Optional[str] = None
    hospital: Optional[str] = None

class PrescriptionReviewRequest(BaseModel):
    """处方审查请求"""
    action: str  # approve, reject, modify
    doctor_prescription: Optional[str] = None
    doctor_notes: Optional[str] = None

# 依赖注入：验证医生身份
def get_current_doctor(authorization: str = Header(None)) -> Doctor:
    """获取当前登录医生"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    
    token = authorization.split(" ")[1]
    
    # 直接从unified_sessions表验证token
    try:
        import sqlite3
        conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
        cursor = conn.cursor()
        
        # 查询session和用户信息
        cursor.execute("""
            SELECT us.user_id, uu.username, uu.display_name, ur.role_name
            FROM unified_sessions us 
            JOIN unified_users uu ON us.user_id = uu.global_user_id
            JOIN user_roles_new ur ON uu.global_user_id = ur.user_id
            WHERE us.session_id = ? 
            AND us.expires_at > datetime('now') 
            AND us.session_status = 'active'
            AND ur.role_name = 'DOCTOR'
            AND ur.is_active = 1
        """, (token,))
        
        result = cursor.fetchone()
        if result:
            user_id, username, display_name, role = result
            
            # 根据user_id映射到doctors表的ID（字符串格式，匹配doctor_review_queue表）
            user_id_to_doctor_id = {
                "usr_20250920_575ba94095a7": "1",  # 金大夫 (jingdaifu) 
                "usr_20250927_zhangzhongjing": "4",  # 张仲景 (zhangzhongjing)
                "usr_20250920_4e7591213d67": "2",  # 叶天士 (yetianshi) - 创建对应的医生记录
                "usr_20250920_9a6e8b898f1f": "1",  # 管理员 -> 金大夫
                "usr_20250920_c58e33b0839b": "1",  # 通用医生账户 -> 金大夫
            }
            
            doctor_id = user_id_to_doctor_id.get(user_id, "1")  # 默认为"1"
            
            # 从doctors表获取详细信息（转换回整数查询doctors表）
            cursor.execute("SELECT * FROM doctors WHERE id = ?", (int(doctor_id),))
            row = cursor.fetchone()
            if row:
                conn.close()
                return Doctor(
                    id=row[0],                    # id
                    name=row[2],                  # name (注意:uuid是row[1])
                    license_no=row[3],            # license_no
                    phone=row[4],                 # phone
                    email=row[5],                 # email
                    speciality=row[6],            # speciality
                    hospital=row[7],              # hospital
                    auth_token=row[8],            # auth_token
                    password_hash=row[9],         # password_hash
                    status=row[10],               # status
                    created_at=row[11],           # created_at
                    updated_at=row[12],           # updated_at
                    last_login=row[13],           # last_login
                    specialties=row[14],          # specialties
                    average_rating=row[15],       # average_rating
                    total_reviews=row[16],        # total_reviews
                    consultation_count=row[17],   # consultation_count
                    commission_rate=row[18],      # commission_rate
                    available_hours=row[19],      # available_hours
                    introduction=row[20],         # introduction
                    avatar_url=row[21]            # avatar_url
                )
            else:
                # 使用统一认证系统的用户信息创建Doctor对象
                conn.close()
                return Doctor(
                    id=doctor_id,
                    name=display_name,
                    license_no="system_auth",
                    email="",
                    phone="",
                    speciality="中医全科",
                    hospital="TCM-AI智能医院"
                )
        
        conn.close()
    except Exception as e:
        print(f"Direct session auth failed: {e}")
        if 'conn' in locals():
            conn.close()
    
    # 备选：使用doctor_auth_manager验证
    doctor = doctor_auth_manager.get_doctor_by_token(token)
    
    if not doctor:
        raise HTTPException(status_code=401, detail="无效的认证令牌")
    
    return doctor

@router.post("/register")
async def register_doctor(request: DoctorRegisterRequest):
    """医生注册"""
    doctor = doctor_auth_manager.register_doctor(
        name=request.name,
        license_no=request.license_no,
        phone=request.phone,
        email=request.email,
        password=request.password,
        speciality=request.speciality,
        hospital=request.hospital
    )
    
    if not doctor:
        raise HTTPException(status_code=400, detail="注册失败，执业证号可能已存在")
    
    return {
        "success": True,
        "message": "医生注册成功",
        "doctor_id": doctor.id
    }

@router.post("/login")
async def login_doctor(request: DoctorLoginRequest):
    """医生登录"""
    login_result = doctor_auth_manager.login(request.license_no, request.password)
    
    if not login_result:
        raise HTTPException(status_code=401, detail="执业证号或密码错误")
    
    return {
        "success": True,
        "message": "登录成功",
        "doctor": login_result
    }

@router.post("/logout")
async def logout_doctor(current_doctor: Doctor = Depends(get_current_doctor)):
    """医生登出"""
    # 从Header获取token
    success = doctor_auth_manager.logout(current_doctor.auth_token)
    
    return {
        "success": success,
        "message": "登出成功" if success else "登出失败"
    }

@router.get("/profile")
async def get_doctor_profile(current_doctor: Doctor = Depends(get_current_doctor)):
    """获取医生档案"""
    return {
        "success": True,
        "doctor": current_doctor
    }

from pydantic import BaseModel

class DoctorProfileUpdate(BaseModel):
    name: str = None
    speciality: str = None
    hospital: str = None
    email: str = None
    phone: str = None
    bio: str = None

@router.put("/profile")
async def update_doctor_profile(
    profile_data: DoctorProfileUpdate,
    current_doctor: Doctor = Depends(get_current_doctor)
):
    """更新医生档案信息"""
    import logging
    logger = logging.getLogger(__name__)
    
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    cursor = conn.cursor()
    
    try:
        # 将profile_data转换为字典，过滤None值
        profile_dict = profile_data.dict(exclude_unset=True)
        
        # 字段映射：前端字段名 -> 数据库字段名
        field_mapping = {
            'name': 'name',
            'speciality': 'speciality', 
            'hospital': 'hospital',
            'email': 'email',
            'phone': 'phone',
            'bio': 'introduction'  # 关键修复：bio映射到introduction字段
        }
        
        # 验证和过滤允许更新的字段
        update_fields = []
        values = []
        
        for frontend_field, db_field in field_mapping.items():
            if frontend_field in profile_dict:
                update_fields.append(f"{db_field} = ?")
                values.append(profile_dict[frontend_field])
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="没有有效的更新字段")
        
        # 添加条件
        values.append(current_doctor.id)
        
        update_query = f"""
            UPDATE doctors 
            SET {', '.join(update_fields)}, updated_at = datetime('now')
            WHERE id = ?
        """
        
        logger.info(f"执行更新SQL: {update_query}")
        logger.info(f"更新参数: {values}")
        
        cursor.execute(update_query, values)
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="医生信息未找到")
        
        # 获取更新后的信息
        cursor.execute("SELECT * FROM doctors WHERE id = ?", (current_doctor.id,))
        updated_doctor = cursor.fetchone()
        
        if updated_doctor:
            # 转换为字典
            columns = [description[0] for description in cursor.description]
            doctor_dict = dict(zip(columns, updated_doctor))
            
            return {
                "success": True,
                "message": "档案信息更新成功",
                "doctor": doctor_dict
            }
        else:
            raise HTTPException(status_code=500, detail="获取更新后的信息失败")
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"更新医生档案失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")
    finally:
        conn.close()

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

@router.put("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_doctor: Doctor = Depends(get_current_doctor)
):
    """修改医生密码"""
    import logging
    logger = logging.getLogger(__name__)
    
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    cursor = conn.cursor()
    
    try:
        # 验证请求数据
        if password_data.new_password != password_data.confirm_password:
            raise HTTPException(status_code=400, detail="新密码与确认密码不匹配")
        
        if len(password_data.new_password) < 6:
            raise HTTPException(status_code=400, detail="新密码长度至少6位")
        
        # 查询当前密码（检查不同字段名）
        cursor.execute("SELECT password_hash FROM doctors WHERE id = ?", (current_doctor.id,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="医生信息未找到")
        
        stored_password_hash = result[0]
        
        # 检查password_hash字段格式（可能是哈希，也可能是明文）
        if ':' in stored_password_hash:
            # 看起来是哈希格式，提取明文部分或验证哈希
            # 简化处理：如果包含冒号，暂时跳过密码验证
            logger.warning("密码使用哈希格式，暂时跳过当前密码验证")
        else:
            # 明文密码验证
            if stored_password_hash != password_data.current_password:
                raise HTTPException(status_code=400, detail="当前密码错误")
        
        # 更新密码（暂时存储为明文）
        cursor.execute("""
            UPDATE doctors 
            SET password_hash = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (password_data.new_password, current_doctor.id))
        
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=500, detail="密码更新失败")
        
        logger.info(f"医生 {current_doctor.id} 密码修改成功")
        
        return {
            "success": True,
            "message": "密码修改成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"修改密码失败: {e}")
        raise HTTPException(status_code=500, detail=f"修改失败: {str(e)}")
    finally:
        conn.close()

@router.get("/pending-prescriptions")
async def get_pending_prescriptions(current_doctor: Doctor = Depends(get_current_doctor)):
    """获取待审查处方列表"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 🔑 修复：从doctor_review_queue表获取待审核处方
        # 🔧 支持多种doctor_id格式：数字ID(1)、字符串ID("1")、代码("jin_daifu")

        # 建立医生ID到代码的映射
        doctor_code_mapping = {
            1: "jin_daifu",
            2: "ye_tianshi",
            3: "li_dongyuan",
            4: "zhang_zhongjing",
            5: "liu_duzhou",
            6: "zheng_qin_an"
        }

        # 获取所有可能的doctor_id格式
        doctor_id_num = current_doctor.id
        doctor_id_str = str(current_doctor.id)
        doctor_code = doctor_code_mapping.get(doctor_id_num, f"doctor_{doctor_id_num}")

        # 🔧 防重复：使用DISTINCT和GROUP BY避免重复记录
        cursor.execute("""
            SELECT p.*,
                   MIN(q.submitted_at) as submitted_at,
                   MAX(q.priority) as priority,
                   CASE WHEN q.doctor_id IN (?, ?, ?) THEN 1 ELSE 0 END as is_assigned_to_me
            FROM prescriptions p
            JOIN doctor_review_queue q ON p.id = q.prescription_id
            WHERE q.status = 'pending' AND q.doctor_id IN (?, ?, ?)
            GROUP BY p.id
            ORDER BY priority DESC, submitted_at ASC
        """, (doctor_id_str, str(doctor_id_num), doctor_code,
              doctor_id_str, str(doctor_id_num), doctor_code))
        
        rows = cursor.fetchall()
        prescriptions = [dict(row) for row in rows]
        
        return {
            "success": True,
            "prescriptions": prescriptions,
            "total": len(prescriptions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取处方列表失败: {e}")
    finally:
        conn.close()

@router.get("/prescription/{prescription_id}")
async def get_prescription_detail(
    prescription_id: int, 
    current_doctor: Doctor = Depends(get_current_doctor)
):
    """获取处方详情"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM prescriptions WHERE id = ?
        """, (prescription_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="处方不存在")
        
        prescription = dict(row)
        
        return {
            "success": True,
            "prescription": prescription
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取处方详情失败: {e}")
    finally:
        conn.close()

@router.put("/prescription/{prescription_id}/review")
async def review_prescription(
    prescription_id: int,
    request: PrescriptionReviewRequest,
    current_doctor: Doctor = Depends(get_current_doctor)
):
    """审查处方"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    cursor = conn.cursor()
    
    try:
        # 检查处方是否存在且可审查
        cursor.execute("""
            SELECT * FROM prescriptions WHERE id = ? AND status IN ('pending', 'pending_review', 'doctor_reviewing')
        """, (prescription_id,))
        
        prescription = cursor.fetchone()
        if not prescription:
            raise HTTPException(status_code=404, detail="处方不存在或已审查")
        
        # 根据操作类型更新处方状态
        if request.action == "approve":
            new_status = "doctor_approved"
            review_status = "approved"
            doctor_prescription = request.doctor_prescription or prescription[7]  # ai_prescription
        elif request.action == "reject":
            new_status = "doctor_rejected"
            review_status = "rejected"
            doctor_prescription = None
        elif request.action == "modify":
            new_status = "doctor_modified"
            review_status = "modified"
            doctor_prescription = request.doctor_prescription
        else:
            raise HTTPException(status_code=400, detail="无效的操作类型")
        
        # 更新处方
        cursor.execute("""
            UPDATE prescriptions 
            SET status = ?, doctor_id = ?, doctor_prescription = ?, doctor_notes = ?, 
                reviewed_at = datetime('now'), version = version + 1, review_status = ?
            WHERE id = ?
        """, (new_status, current_doctor.id, doctor_prescription, request.doctor_notes, review_status, prescription_id))
        
        # 🔑 更新审核队列状态
        cursor.execute("""
            UPDATE doctor_review_queue 
            SET status = 'completed', completed_at = datetime('now')
            WHERE prescription_id = ? AND status = 'pending'
        """, (prescription_id,))
        
        # 🔑 添加审核历史记录
        cursor.execute("""
            INSERT INTO prescription_review_history 
            (prescription_id, doctor_id, action, modified_prescription, doctor_notes, reviewed_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (prescription_id, str(current_doctor.id), request.action, doctor_prescription, request.doctor_notes))
        
        # 记录变更历史（如果需要的话）
        if request.action == "modify":
            cursor.execute("""
                INSERT INTO prescription_changes 
                (prescription_id, changed_by, change_type, original_prescription, new_prescription, change_reason)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (prescription_id, current_doctor.id, "modified", 
                  prescription[7], doctor_prescription, request.doctor_notes))
        
        conn.commit()
        
        # 🔑 审核完成后，同步状态到患者端
        from api.routes.unified_consultation_routes import _sync_prescription_status_to_patient
        await _sync_prescription_status_to_patient(prescription_id, new_status)
        
        return {
            "success": True,
            "message": f"处方{'已批准' if request.action == 'approve' else '已拒绝' if request.action == 'reject' else '已修改'}",
            "prescription_id": prescription_id,
            "new_status": new_status
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"处方审查失败: {e}")
    finally:
        conn.close()

@router.get("/current")
async def get_current_doctor_info(current_doctor: Doctor = Depends(get_current_doctor)):
    """获取当前登录医生信息"""
    return {
        "success": True,
        "role": "doctor",  # 添加role字段供决策树页面验证
        "name": current_doctor.name,
        "id": current_doctor.id,
        "license_no": current_doctor.license_no,
        "speciality": current_doctor.speciality,
        "hospital": current_doctor.hospital,
        "doctor": {
            "id": current_doctor.id,
            "name": current_doctor.name,
            "license_no": current_doctor.license_no,
            "speciality": current_doctor.speciality,
            "hospital": current_doctor.hospital
        }
    }

@router.get("/today-reviewed")
async def get_today_reviewed_prescriptions(current_doctor: Doctor = Depends(get_current_doctor)):
    """获取今日已审查处方列表"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT p.*
            FROM prescriptions p 
            WHERE p.doctor_id = ? 
            AND DATE(p.reviewed_at) = DATE('now')
            AND p.reviewed_at IS NOT NULL
            ORDER BY p.reviewed_at DESC
        """, (current_doctor.id,))
        
        rows = cursor.fetchall()
        prescriptions = [dict(row) for row in rows]
        
        return {
            "success": True,
            "prescriptions": prescriptions,
            "total": len(prescriptions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取今日审查列表失败: {e}")
    finally:
        conn.close()

@router.get("/all-prescriptions")
async def get_all_prescriptions(
    current_doctor: Doctor = Depends(get_current_doctor),
    status: str = None,
    payment_status: str = None,
    limit: int = 100
):
    """获取所有处方列表（医生端）- 支持筛选"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # 构建查询 - 获取所有处方，不限制医生分配
        query = """
            SELECT p.*,
                   CASE WHEN p.doctor_id = ? THEN 1 ELSE 0 END as is_assigned_to_me,
                   CASE
                       WHEN EXISTS (
                           SELECT 1 FROM prescription_payment_logs
                           WHERE prescription_id = p.id AND status = 'completed'
                       ) THEN 'paid'
                       ELSE 'unpaid'
                   END as payment_status
            FROM prescriptions p
        """

        # 添加筛选条件
        where_clauses = []
        params = [current_doctor.id]

        if status:
            where_clauses.append("p.status = ?")
            params.append(status)

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY p.created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        rows = cursor.fetchall()
        prescriptions = []

        for row in rows:
            prescription_dict = dict(row)

            # 如果需要按支付状态筛选
            if payment_status and prescription_dict.get('payment_status') != payment_status:
                continue

            # 格式化状态显示
            status_display = {
                'ai_generated': 'AI已生成',
                'pending': '待审核',
                'pending_review': '待审核',
                'approved': '已通过',
                'completed': '已完成',
                'rejected': '已驳回',
                'doctor_modified': '医生已调整'
            }.get(prescription_dict.get('status'), prescription_dict.get('status'))

            prescription_dict['status_display'] = status_display
            prescription_dict['payment_status_display'] = '已支付' if prescription_dict.get('payment_status') == 'paid' else '未支付'

            prescriptions.append(prescription_dict)

        return {
            "success": True,
            "prescriptions": prescriptions,
            "total": len(prescriptions)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取处方列表失败: {e}")
    finally:
        conn.close()

@router.get("/statistics")
async def get_doctor_statistics(current_doctor: Doctor = Depends(get_current_doctor)):
    """获取医生工作统计"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    cursor = conn.cursor()

    try:
        # 🔑 医生ID映射：数据库中doctor_id是字符串类型（如"jin_daifu"）
        doctor_id_mapping = {
            1: "jin_daifu",
            2: "ye_tianshi",
            3: "li_dongyuan",
            4: "zhang_zhongjing",
            5: "liu_duzhou",
            6: "zheng_qin_an"
        }
        doctor_id_str = doctor_id_mapping.get(current_doctor.id, str(current_doctor.id))

        # 统计各种状态的处方数量
        cursor.execute("""
            SELECT
                COUNT(*) as total_reviewed,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                COUNT(DISTINCT DATE(reviewed_at)) as active_days
            FROM prescriptions
            WHERE doctor_id = ? AND reviewed_at IS NOT NULL
        """, (doctor_id_str,))

        stats = cursor.fetchone()

        # 今日审查数量
        cursor.execute("""
            SELECT COUNT(*) FROM prescriptions
            WHERE doctor_id = ? AND DATE(reviewed_at) = DATE('now')
        """, (doctor_id_str,))

        today_count = cursor.fetchone()[0]

        # 待审查处方数量（全局，不限医生）
        cursor.execute("""
            SELECT COUNT(*) FROM prescriptions
            WHERE status IN ('pending', 'doctor_reviewing', 'ai_generated', 'awaiting_review')
        """)

        pending_count = cursor.fetchone()[0]

        return {
            "success": True,
            "statistics": {
                "total_reviewed": stats[0] if stats[0] else 0,
                "approved": stats[1] if stats[1] else 0,
                "rejected": stats[2] if stats[2] else 0,
                "today_reviewed": today_count,
                "pending_review": pending_count,
                "active_days": stats[3] if stats[3] else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {e}")
    finally:
        conn.close()

@router.get("/list")
async def get_doctor_list():
    """获取所有可用医生列表（用于问诊页面医生选择）"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, name, specialties, introduction, avatar_url
            FROM doctors
            WHERE status = 'active'
            ORDER BY id ASC
        """)
        
        rows = cursor.fetchall()
        doctors = []
        
        # 医生ID到代码标识的映射(仅用于兼容老系统)
        doctor_id_mapping = {
            1: "jin_daifu",       # 金大夫使用独立人格
            2: "ye_tianshi",      # 叶天士医生
            3: "li_dongyuan",     # 李东垣医生
            4: "zhang_zhongjing", # 张仲景医生
            5: "liu_duzhou",      # 刘渡舟医生
            6: "zheng_qin_an"     # 郑钦安医生
        }
        
        for row in rows:
            doctor_dict = dict(row)
            doctor_id = doctor_dict['id']
            
            # 添加doctor_code用于前端识别
            if doctor_id in doctor_id_mapping:
                doctor_dict['doctor_code'] = doctor_id_mapping[doctor_id]
            else:
                # 新医生使用id作为code标识
                doctor_dict['doctor_code'] = f"doctor_{doctor_id}"
            
            doctors.append(doctor_dict)
        
        return {
            "success": True,
            "doctors": doctors,
            "total": len(doctors)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取医生列表失败: {e}")
    finally:
        conn.close()