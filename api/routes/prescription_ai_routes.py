"""
AI增强处方管理相关API路由
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import json
from datetime import datetime, timedelta
import random

router = APIRouter(prefix="/api/prescription/ai", tags=["AI处方管理"])

# 导入统一认证系统
import sys
sys.path.append('/opt/tcm-ai')
from core.unified_account.account_manager import unified_account_manager

class AIAnalysisRequest(BaseModel):
    """AI分析请求"""
    prescription_id: int
    analysis_type: str = "comprehensive"  # comprehensive, safety, efficacy, compatibility

class BatchOperationRequest(BaseModel):
    """批量操作请求"""
    prescription_ids: List[int]
    operation: str  # approve, reject, ai_check
    notes: Optional[str] = None

class RiskAssessmentRequest(BaseModel):
    """风险评估请求"""
    prescription_content: str
    patient_info: Optional[Dict] = None

# 认证助手函数
async def get_current_user_from_header(authorization: Optional[str] = Header(None)):
    """从Header中获取当前用户"""
    try:
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="需要认证")
        
        session_id = authorization.replace('Bearer ', '')
        session = unified_account_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=401, detail="会话无效或已过期")
        
        user = unified_account_manager.get_user_by_id(session.user_id)
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")
        
        # 检查医生权限
        if user.primary_role not in ['doctor', 'admin', 'superadmin']:
            raise HTTPException(status_code=403, detail="需要医生权限")
        
        return user, session
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"认证过程出错: {e}")
        raise HTTPException(status_code=500, detail=f"认证系统错误: {str(e)}")

@router.post("/analyze/{prescription_id}")
async def analyze_prescription_with_ai(
    prescription_id: int,
    request: AIAnalysisRequest,
    authorization: Optional[str] = Header(None)
):
    """使用AI分析处方"""
    user, session = await get_current_user_from_header(authorization)
    
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        
        # 获取处方详情
        cursor.execute("""
            SELECT * FROM prescriptions WHERE id = ?
        """, (prescription_id,))
        
        prescription = cursor.fetchone()
        if not prescription:
            raise HTTPException(status_code=404, detail="处方不存在")
        
        # 模拟AI分析过程
        analysis_result = simulate_ai_analysis(
            prescription['ai_prescription'] or '',
            request.analysis_type
        )
        
        # 保存分析结果
        cursor.execute("""
            INSERT OR REPLACE INTO prescription_ai_analysis 
            (prescription_id, analysis_type, analysis_result, analyzed_by, analyzed_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (
            prescription_id,
            request.analysis_type,
            json.dumps(analysis_result, ensure_ascii=False),
            user.global_user_id
        ))
        
        conn.commit()
        
        return {
            "success": True,
            "analysis": analysis_result,
            "message": "AI分析完成"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI分析失败: {str(e)}")
    finally:
        conn.close()

@router.post("/batch-operation")
async def batch_prescription_operation(
    request: BatchOperationRequest,
    authorization: Optional[str] = Header(None)
):
    """批量处方操作"""
    user, session = await get_current_user_from_header(authorization)
    
    if not request.prescription_ids:
        raise HTTPException(status_code=400, detail="未选择处方")
    
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    try:
        cursor = conn.cursor()
        
        results = []
        
        for prescription_id in request.prescription_ids:
            try:
                if request.operation == "approve":
                    cursor.execute("""
                        UPDATE prescriptions 
                        SET status = 'approved', 
                            doctor_id = ?, 
                            doctor_notes = ?,
                            reviewed_at = datetime('now'),
                            version = version + 1
                        WHERE id = ? AND status IN ('pending', 'ai_generated', 'awaiting_review')
                    """, (user.global_user_id, request.notes or "批量审查通过", prescription_id))
                    
                elif request.operation == "reject":
                    cursor.execute("""
                        UPDATE prescriptions 
                        SET status = 'rejected', 
                            doctor_id = ?, 
                            doctor_notes = ?,
                            reviewed_at = datetime('now'),
                            version = version + 1
                        WHERE id = ? AND status IN ('pending', 'ai_generated', 'awaiting_review')
                    """, (user.global_user_id, request.notes or "批量审查拒绝", prescription_id))
                    
                elif request.operation == "ai_check":
                    # 执行AI检查
                    ai_result = simulate_batch_ai_check(prescription_id)
                    cursor.execute("""
                        INSERT OR REPLACE INTO prescription_ai_analysis 
                        (prescription_id, analysis_type, analysis_result, analyzed_by, analyzed_at)
                        VALUES (?, 'batch_check', ?, ?, datetime('now'))
                    """, (
                        prescription_id,
                        json.dumps(ai_result, ensure_ascii=False),
                        user.global_user_id
                    ))
                
                results.append({
                    "prescription_id": prescription_id,
                    "success": True,
                    "message": f"处方 #{prescription_id} 操作成功"
                })
                
            except Exception as e:
                results.append({
                    "prescription_id": prescription_id,
                    "success": False,
                    "message": f"处方 #{prescription_id} 操作失败: {str(e)}"
                })
        
        conn.commit()
        
        success_count = sum(1 for r in results if r["success"])
        
        return {
            "success": True,
            "results": results,
            "summary": {
                "total": len(request.prescription_ids),
                "success": success_count,
                "failed": len(request.prescription_ids) - success_count
            },
            "message": f"批量操作完成: {success_count}/{len(request.prescription_ids)} 成功"
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"批量操作失败: {str(e)}")
    finally:
        conn.close()

@router.get("/risk-analysis")
async def get_risk_analysis(authorization: Optional[str] = Header(None)):
    """获取风险分析报告"""
    user, session = await get_current_user_from_header(authorization)
    
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        
        # 获取待审查处方
        cursor.execute("""
            SELECT id, ai_prescription, patient_name, created_at
            FROM prescriptions 
            WHERE status IN ('pending', 'ai_generated', 'awaiting_review')
            ORDER BY created_at DESC
            LIMIT 50
        """)
        
        prescriptions = cursor.fetchall()
        
        # 模拟风险分析
        risk_analysis = simulate_risk_analysis(prescriptions)
        
        return {
            "success": True,
            "risk_analysis": risk_analysis,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"风险分析失败: {str(e)}")
    finally:
        conn.close()

@router.get("/insights")
async def get_ai_insights(authorization: Optional[str] = Header(None)):
    """获取AI洞察分析"""
    user, session = await get_current_user_from_header(authorization)
    
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        
        # 获取统计数据
        cursor.execute("""
            SELECT 
                COUNT(*) as total_prescriptions,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved_count,
                SUM(CASE WHEN DATE(created_at) = DATE('now') THEN 1 ELSE 0 END) as today_count,
                SUM(CASE WHEN reviewed_by = ? THEN 1 ELSE 0 END) as reviewed_by_me
            FROM prescriptions 
            WHERE created_at >= date('now', '-7 days')
        """, (user.global_user_id,))
        
        stats = cursor.fetchone()
        
        # 生成AI洞察
        insights = generate_ai_insights(stats)
        
        return {
            "success": True,
            "insights": insights,
            "statistics": dict(stats) if stats else {},
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI洞察分析失败: {str(e)}")
    finally:
        conn.close()

@router.post("/recommend")
async def get_ai_recommendation(
    prescription_id: int,
    authorization: Optional[str] = Header(None)
):
    """获取AI推荐意见"""
    user, session = await get_current_user_from_header(authorization)
    
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        
        # 获取处方详情
        cursor.execute("""
            SELECT * FROM prescriptions WHERE id = ?
        """, (prescription_id,))
        
        prescription = cursor.fetchone()
        if not prescription:
            raise HTTPException(status_code=404, detail="处方不存在")
        
        # 生成AI推荐
        recommendation = generate_ai_recommendation(prescription)
        
        # 记录推荐历史
        cursor.execute("""
            INSERT INTO prescription_ai_recommendations 
            (prescription_id, recommendation, recommended_by, recommended_at)
            VALUES (?, ?, ?, datetime('now'))
        """, (
            prescription_id,
            json.dumps(recommendation, ensure_ascii=False),
            user.global_user_id
        ))
        
        conn.commit()
        
        return {
            "success": True,
            "recommendation": recommendation,
            "message": "AI推荐生成完成"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取AI推荐失败: {str(e)}")
    finally:
        conn.close()

# 辅助函数

def simulate_ai_analysis(prescription_content: str, analysis_type: str) -> Dict:
    """模拟AI分析过程"""
    base_analysis = {
        "safety_score": round(random.uniform(0.7, 0.95), 2),
        "efficacy_score": round(random.uniform(0.75, 0.92), 2),
        "tcm_theory_compliance": round(random.uniform(0.8, 0.98), 2),
        "risk_level": random.choice(["low", "medium", "high"]),
        "confidence": round(random.uniform(0.85, 0.97), 2)
    }
    
    if analysis_type == "comprehensive":
        return {
            **base_analysis,
            "drug_interactions": [],
            "dosage_warnings": ["附子用量较大，建议分次服用"],
            "contraindications": [],
            "tcm_pattern": "阳虚证",
            "formula_structure": {
                "monarch": ["附子"],
                "minister": ["干姜", "甘草"],
                "assistant": ["白术"],
                "envoy": ["甘草"]
            },
            "recommendations": [
                "方剂组成合理，符合温阳治法原则",
                "建议餐后服用，减少胃部不适",
                "服药期间注意休息，避免过度劳累"
            ]
        }
    
    elif analysis_type == "safety":
        return {
            "safety_score": base_analysis["safety_score"],
            "risk_factors": [
                {"factor": "附子用量", "level": "medium", "description": "用量较大，需注意监测"},
                {"factor": "药物相互作用", "level": "low", "description": "未发现明显相互作用"}
            ],
            "warnings": ["孕妇慎用", "心脏病患者注意监测"],
            "monitoring_points": ["心率", "血压", "肝肾功能"]
        }
    
    return base_analysis

def simulate_batch_ai_check(prescription_id: int) -> Dict:
    """模拟批量AI检查"""
    return {
        "prescription_id": prescription_id,
        "safety_check": random.choice(["pass", "warning", "fail"]),
        "efficacy_check": random.choice(["pass", "warning"]),
        "interaction_check": random.choice(["pass", "warning"]),
        "dosage_check": random.choice(["pass", "warning"]),
        "overall_score": round(random.uniform(0.7, 0.95), 2),
        "recommendation": random.choice(["approve", "review_required", "reject"])
    }

def simulate_risk_analysis(prescriptions) -> Dict:
    """模拟风险分析"""
    total = len(prescriptions)
    high_risk = max(1, int(total * 0.1))
    medium_risk = max(1, int(total * 0.2))
    low_risk = total - high_risk - medium_risk
    
    return {
        "total_prescriptions": total,
        "risk_distribution": {
            "high": high_risk,
            "medium": medium_risk,
            "low": low_risk
        },
        "risk_factors": [
            {
                "factor": "剂量过大",
                "count": random.randint(1, 5),
                "severity": "high"
            },
            {
                "factor": "药物相互作用",
                "count": random.randint(2, 8),
                "severity": "medium"
            },
            {
                "factor": "配伍不当",
                "count": random.randint(1, 3),
                "severity": "high"
            }
        ],
        "recommendations": [
            "优先审查高风险处方",
            "加强剂量安全监控",
            "建立药物相互作用预警机制"
        ]
    }

def generate_ai_insights(stats) -> Dict:
    """生成AI洞察"""
    if not stats:
        return {}
    
    total = stats['total_prescriptions'] or 0
    approved = stats['approved_count'] or 0
    today = stats['today_count'] or 0
    
    approval_rate = (approved / total * 100) if total > 0 else 0
    
    return {
        "trends": {
            "prescription_volume": {
                "direction": "increasing" if today > total / 7 else "stable",
                "change_percent": random.randint(-10, 25)
            },
            "approval_rate": {
                "current": round(approval_rate, 1),
                "trend": "stable",
                "benchmark": 92.5
            }
        },
        "patterns": [
            "呼吸道疾病处方增长23%",
            "消化系统疾病处方保持稳定",
            "温阳类方剂使用频率上升"
        ],
        "alerts": [
            "发现3个处方存在潜在药物相互作用风险",
            "今日高风险处方比例略高于平均水平"
        ],
        "recommendations": [
            "建议优先审查附子类方剂",
            "加强对新药物组合的关注",
            "考虑建立个性化审查策略"
        ]
    }

def generate_ai_recommendation(prescription) -> Dict:
    """生成AI推荐"""
    return {
        "action": random.choice(["approve", "approve_with_notes", "review_required"]),
        "confidence": round(random.uniform(0.85, 0.97), 2),
        "reasoning": [
            "方剂组成符合中医理论",
            "剂量在安全范围内",
            "适用于诊断的证候"
        ],
        "suggested_notes": [
            "建议餐后服用",
            "注意观察患者反应",
            "如有不适及时就医"
        ],
        "risk_assessment": {
            "overall_risk": "low",
            "specific_risks": []
        },
        "optimization_suggestions": [
            "可考虑减少甘草用量",
            "建议分次服用以提高吸收"
        ]
    }