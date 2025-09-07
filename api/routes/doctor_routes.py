"""
医生相关API路由
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3

from core.doctor_management.doctor_auth import doctor_auth_manager
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
    
    # 首先尝试使用session_manager验证 (统一认证系统)
    try:
        from core.security.rbac_system import session_manager
        session = session_manager.get_session(token)
        if session and session.role.value == "doctor":
            # 根据user_id映射到doctors表的ID - 匹配主页面医生清单
            user_id_to_doctor_id = {
                "zhangzhongjing_001": 1,  # 张仲景
                "yetianshi_001": 2,       # 叶天士  
                "lidongyuan_001": 3,      # 李东垣
                "liuduzhou_001": 5,       # 刘渡舟
                "zhengqinan_001": 6,      # 郑钦安
                "zhudanxi_001": 7,        # 朱丹溪
            }
            
            doctor_id = user_id_to_doctor_id.get(session.user_id)
            if doctor_id is None:
                raise HTTPException(status_code=403, detail=f"未找到对应的医生信息: {session.user_id}")
            
            # 从doctors表获取详细信息
            import sqlite3
            conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,))
                row = cursor.fetchone()
                if row:
                    return Doctor(
                        id=row[0],                    # 使用doctors表的ID
                        name=row[1],                  # 医生姓名
                        license_no=row[2],            # 执业证号
                        phone=row[3],                 # 电话
                        email=row[4],                 # 邮箱
                        speciality=row[5],            # 专科
                        hospital=row[6]               # 医院
                    )
            finally:
                conn.close()
                
            # 如果找不到医生信息，使用默认值
            return Doctor(
                id=doctor_id,
                name=session.user_id,
                license_no="system_auth",
                email="",
                phone="",
                speciality="",
                hospital=""
            )
    except Exception as e:
        print(f"Session auth failed: {e}")
    
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

@router.get("/pending-prescriptions")
async def get_pending_prescriptions(current_doctor: Doctor = Depends(get_current_doctor)):
    """获取待审查处方列表"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT p.*, 
                   CASE WHEN p.doctor_id = ? THEN 1 ELSE 0 END as is_assigned_to_me
            FROM prescriptions p 
            WHERE p.status IN ('pending', 'doctor_reviewing')
            ORDER BY p.created_at ASC
        """, (current_doctor.id,))
        
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
            SELECT * FROM prescriptions WHERE id = ? AND status IN ('pending', 'doctor_reviewing')
        """, (prescription_id,))
        
        prescription = cursor.fetchone()
        if not prescription:
            raise HTTPException(status_code=404, detail="处方不存在或已审查")
        
        # 根据操作类型更新处方状态
        if request.action == "approve":
            new_status = "approved"
            doctor_prescription = request.doctor_prescription or prescription[7]  # ai_prescription
        elif request.action == "reject":
            new_status = "rejected"
            doctor_prescription = None
        elif request.action == "modify":
            new_status = "approved"
            doctor_prescription = request.doctor_prescription
        else:
            raise HTTPException(status_code=400, detail="无效的操作类型")
        
        # 更新处方
        cursor.execute("""
            UPDATE prescriptions 
            SET status = ?, doctor_id = ?, doctor_prescription = ?, doctor_notes = ?, 
                reviewed_at = datetime('now'), version = version + 1
            WHERE id = ?
        """, (new_status, current_doctor.id, doctor_prescription, request.doctor_notes, prescription_id))
        
        # 记录变更历史（如果需要的话）
        if request.action == "modify":
            cursor.execute("""
                INSERT INTO prescription_changes 
                (prescription_id, changed_by, change_type, original_prescription, new_prescription, change_reason)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (prescription_id, current_doctor.id, "modified", 
                  prescription[7], doctor_prescription, request.doctor_notes))
        
        conn.commit()
        
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
        "doctor": {
            "id": current_doctor.id,
            "name": current_doctor.name,
            "license_no": current_doctor.license_no,
            "speciality": current_doctor.speciality,
            "hospital": current_doctor.hospital
        }
    }

@router.get("/statistics")
async def get_doctor_statistics(current_doctor: Doctor = Depends(get_current_doctor)):
    """获取医生工作统计"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    cursor = conn.cursor()
    
    try:
        # 统计各种状态的处方数量
        cursor.execute("""
            SELECT 
                COUNT(*) as total_reviewed,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                COUNT(DISTINCT DATE(reviewed_at)) as active_days
            FROM prescriptions 
            WHERE doctor_id = ? AND reviewed_at IS NOT NULL
        """, (current_doctor.id,))
        
        stats = cursor.fetchone()
        
        # 今日审查数量
        cursor.execute("""
            SELECT COUNT(*) FROM prescriptions 
            WHERE doctor_id = ? AND DATE(reviewed_at) = DATE('now')
        """, (current_doctor.id,))
        
        today_count = cursor.fetchone()[0]
        
        return {
            "success": True,
            "statistics": {
                "total_reviewed": stats[0] if stats[0] else 0,
                "approved": stats[1] if stats[1] else 0,
                "rejected": stats[2] if stats[2] else 0,
                "today_reviewed": today_count,
                "active_days": stats[3] if stats[3] else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {e}")
    finally:
        conn.close()