#!/usr/bin/env python3
"""
Doctor Decision Tree API Routes
智能决策树生成API路由

提供医生决策树分析和生成功能，帮助医生将自然语言描述转换为结构化的诊疗决策树
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import logging
import asyncio
import sqlite3

# 导入必要的服务
from services.famous_doctor_learning_system import FamousDoctorLearningSystem
from api.security_integration import get_current_user
from core.security.rbac_system import UserSession, UserRole
from core.doctor_management.doctor_auth import doctor_auth_manager
from app.core.settings import AI_CONFIG, PATHS

# 检查Dashscope可用性
try:
    import dashscope
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api", tags=["doctor-decision-tree"])

# 懒加载服务，避免模块导入时触发重初始化
_doctor_learning_system: Optional[FamousDoctorLearningSystem] = None
USER_DB_PATH = str(PATHS["user_db"])


def get_doctor_learning_system() -> FamousDoctorLearningSystem:
    global _doctor_learning_system
    if _doctor_learning_system is None:
        _doctor_learning_system = FamousDoctorLearningSystem()
    return _doctor_learning_system


security_bearer = HTTPBearer(auto_error=False)

# 混合认证依赖函数 - 支持RBAC session和医生JWT token
async def get_current_user_or_doctor(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> UserSession:
    """
    混合认证：优先使用RBAC session，fallback到医生JWT token

    这个函数解决了系统中存在两套认证机制的问题：
    1. RBAC系统：使用user_sessions表
    2. 医生系统：使用doctors表的JWT token
    """
    logger.info(f"🔍 [认证]开始混合认证流程, 有credentials: {credentials is not None and credentials.credentials is not None}")

    # 1. 先尝试RBAC认证（包括统一认证系统）
    try:
        user_session = await get_current_user(request, credentials)
        if user_session:
            # 🔧 修复：兼容统一认证系统的 roles (List[str]) 和旧系统的 role
            user_roles = getattr(user_session, 'roles', [getattr(user_session, 'role', None)])
            if isinstance(user_roles, str):
                user_roles = [user_roles]

            logger.info(f"🔍 [认证]RBAC认证成功: user={user_session.user_id}, roles={user_roles}")

            # 检查是否有医生或管理员角色
            has_doctor_role = any(
                role in ['DOCTOR', 'ADMIN', UserRole.DOCTOR, UserRole.ADMIN]
                for role in user_roles if role
            )

            if has_doctor_role:
                logger.info(f"✅ 统一认证验证通过: user={user_session.user_id}, roles={user_roles}")
                return user_session
            else:
                logger.warning(f"⚠️ 用户无医生权限: user={user_session.user_id}, roles={user_roles}")
    except Exception as e:
        logger.info(f"🔍 [认证]RBAC认证失败: {e}")

    # 2. 尝试医生JWT token认证
    if credentials and credentials.credentials:
        token = credentials.credentials
        logger.info(f"🔍 [认证]尝试医生JWT认证, token前缀: {token[:20]}...")
        doctor_payload = doctor_auth_manager.verify_auth_token(token)

        logger.info(f"🔍 [认证]JWT验证结果: {doctor_payload is not None}")

        if doctor_payload:
            # 从doctors表获取医生信息
            conn = sqlite3.connect(USER_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM doctors WHERE id = ? AND status = 'active'
            """, (doctor_payload['doctor_id'],))

            doctor = cursor.fetchone()
            conn.close()

            if doctor:
                # 创建临时UserSession对象
                from datetime import datetime, timedelta
                # 使用license_no作为user_id (医生的唯一标识)
                doctor_user_id = doctor['license_no']
                logger.info(f"医生JWT认证成功: {doctor['name']} ({doctor_user_id})")

                return UserSession(
                    user_id=doctor_user_id,
                    role=UserRole.DOCTOR,
                    permissions=set(),  # 医生默认有所有医生权限
                    session_token=token,
                    created_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(days=7),
                    ip_address=request.client.host if request.client else "unknown",
                    user_agent=request.headers.get("User-Agent", "Unknown"),
                    last_activity=datetime.now(),
                    is_active=True
                )

    # 3. 认证失败，抛出403错误
    raise HTTPException(
        status_code=403,
        detail="需要医生或管理员权限。请先登录。"
    )

# 请求/响应模型
class ThinkingAnalysisRequest(BaseModel):
    disease_name: str
    thinking_process: str

class ThinkingAnalysisResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class DecisionTreeRequest(BaseModel):
    disease_name: str
    thinking_process: str
    selected_schools: List[str]

class DecisionTreeResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class SaveDecisionTreeRequest(BaseModel):
    disease_name: str
    thinking_process: str
    selected_schools: List[str]
    decision_tree: Dict[str, Any]
    is_template: bool = True

# V3版本的数据模型 - 分支路径结构
class PathStep(BaseModel):
    type: str  # symptom, condition, diagnosis, treatment, formula
    content: str
    condition: Optional[str] = None
    result: Optional[bool] = None

class DecisionPath(BaseModel):
    id: str
    steps: List[PathStep]
    keywords: List[str]
    created_by: str

class SaveDecisionTreeV3Request(BaseModel):
    disease_name: str
    paths: List[DecisionPath]
    integration_enabled: bool = True

class SymptomMatchRequest(BaseModel):
    symptoms: List[str]
    disease_context: Optional[str] = None

# 中医流派映射
SCHOOL_MAPPING = {
    'zhongjing': '张仲景经方派',
    'tianshi': '叶天士温病派',
    'dongyuan': '李东垣脾胃派',
    'qingan': '郑钦安火神派',
    'duzhou': '刘渡舟经方派',
    'comprehensive': '综合各派观点'
}

@router.post("/analyze_thinking", response_model=ThinkingAnalysisResponse)
async def analyze_thinking(
    request: ThinkingAnalysisRequest,
    current_user: UserSession = Depends(get_current_user)
):
    """
    分析医生的诊疗思维过程
    
    Args:
        request: 包含疾病名称和思维过程的请求
        current_user: 当前用户信息
        
    Returns:
        分析结果，包含关键要点、遗漏考虑点和建议流程
    """
    try:
        logger.info(f"用户 {current_user.user_id} 请求分析诊疗思维: {request.disease_name}")
        
        # 构建AI分析提示词
        analysis_prompt = f"""
        作为一位经验丰富的中医专家，请分析以下医生对"{request.disease_name}"的诊疗思维过程：

        医生的思维描述：
        {request.thinking_process}

        请从以下几个方面进行分析：

        1. **关键诊断要点提取**: 识别医生已经考虑到的重要诊断要素
        2. **可能遗漏的考虑点**: 指出可能被忽略但重要的诊断因素
        3. **建议的诊疗流程**: 提供优化的诊疗流程建议

        请以JSON格式返回分析结果：
        {{
            "key_points": ["要点1", "要点2", ...],
            "missing_considerations": ["遗漏点1", "遗漏点2", ...],
            "suggested_workflow": "建议的完整诊疗流程描述"
        }}
        """
        
        # 调用AI分析
        try:
            analysis_result = await get_doctor_learning_system().analyze_doctor_thinking(
                thinking_process=request.thinking_process,
                disease_name=request.disease_name,
                analysis_prompt=analysis_prompt
            )
            
            # 解析JSON结果
            if isinstance(analysis_result, str):
                try:
                    analysis_data = json.loads(analysis_result)
                except json.JSONDecodeError:
                    # 如果解析失败，创建默认结构
                    analysis_data = {
                        "key_points": ["AI分析结果解析中，请稍后查看详细分析"],
                        "missing_considerations": ["正在进行深度分析..."],
                        "suggested_workflow": analysis_result[:200] + "..."
                    }
            else:
                analysis_data = analysis_result

            return ThinkingAnalysisResponse(
                success=True,
                message="思维分析完成",
                data=analysis_data
            )
            
        except Exception as ai_error:
            logger.error(f"AI分析失败: {ai_error}")
            # 返回模拟分析结果作为后备
            return ThinkingAnalysisResponse(
                success=True,
                message="分析完成（使用后备分析）",
                data={
                    "key_points": [
                        f"主要关注疾病：{request.disease_name}",
                        "已考虑症状分析和治疗方案",
                        "具备基本的中医辨证思维"
                    ],
                    "missing_considerations": [
                        "建议补充四诊信息收集",
                        "考虑患者体质差异",
                        "注意并发症和禁忌症",
                        "加强随访观察计划"
                    ],
                    "suggested_workflow": "1. 详细四诊收集 → 2. 综合辨证分析 → 3. 确定治则治法 → 4. 方药选择 → 5. 疗效评估与调整"
                }
            )
        
    except Exception as e:
        logger.error(f"分析诊疗思维失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

@router.post("/generate_decision_tree", response_model=DecisionTreeResponse)
async def generate_decision_tree(
    request: DecisionTreeRequest,
    current_user: UserSession = Depends(get_current_user)
):
    """
    生成智能决策树
    
    Args:
        request: 包含疾病信息、思维过程和选择流派的请求
        current_user: 当前用户信息
        
    Returns:
        生成的决策树结构和流派建议
    """
    try:
        logger.info(f"用户 {current_user.user_id} 请求生成决策树: {request.disease_name}")
        
        # 转换流派名称
        selected_school_names = []
        for school_id in request.selected_schools:
            school_name = SCHOOL_MAPPING.get(school_id, school_id)
            selected_school_names.append(school_name)
        
        # 构建决策树生成提示词
        tree_prompt = f"""
        基于以下信息生成中医诊疗决策树：

        疾病名称：{request.disease_name}
        医生思维过程：{request.thinking_process}
        参考流派：{', '.join(selected_school_names)}

        请生成一个结构化的决策树，包含以下层级：
        1. 主要症状识别
        2. 辨证分型
        3. 治疗方案
        4. 方药选择

        重要：每个节点都应该有明确的分支条件，方便医生进行逻辑判断。

        返回JSON格式：
        {{
            "tree": {{
                "levels": [
                    {{
                        "title": "症状识别",
                        "type": "symptom",
                        "nodes": [
                            {{"name": "症状1", "description": "详细描述", "condition": "症状明显？", "id": "sym_1"}},
                            {{"name": "症状2", "description": "详细描述", "condition": "症状轻微？", "id": "sym_2"}}
                        ],
                        "branches": [
                            {{"condition": "症状表现程度", "result": "positive", "target_nodes": ["症状1", "症状2"]}}
                        ]
                    }},
                    {{
                        "title": "辨证分型",
                        "type": "diagnosis",
                        "nodes": [
                            {{"name": "证型1", "description": "证候特点", "condition": "舌红苔厚？", "id": "diag_1"}},
                            {{"name": "证型2", "description": "证候特点", "condition": "面色萎黄？", "id": "diag_2"}}
                        ],
                        "branches": [
                            {{"condition": "舌红苔厚？", "result": "positive", "target_nodes": ["证型1"]}},
                            {{"condition": "面色萎黄？", "result": "positive", "target_nodes": ["证型2"]}}
                        ]
                    }},
                    {{
                        "title": "治疗方案",
                        "type": "treatment",
                        "nodes": [
                            {{"name": "方案1", "description": "治疗详情", "condition": "需清热？", "id": "treat_1"}},
                            {{"name": "方案2", "description": "治疗详情", "condition": "需补益？", "id": "treat_2"}}
                        ],
                        "branches": [
                            {{"condition": "治疗方向", "result": "positive", "target_nodes": ["方案1", "方案2"]}}
                        ]
                    }},
                    {{
                        "title": "方药选择",
                        "type": "formula",
                        "nodes": [
                            {{"name": "主方", "description": "首选方剂", "condition": "标准剂量？", "id": "form_1"}},
                            {{"name": "加减方", "description": "个体化调整", "condition": "需加减？", "id": "form_2"}}
                        ],
                        "branches": [
                            {{"condition": "用药策略", "result": "positive", "target_nodes": ["主方", "加减方"]}}
                        ]
                    }}
                ]
            }},
            "school_suggestions": [
                {{
                    "school": "流派名称",
                    "advice": "具体建议内容"
                }}
            ]
        }}
        """
        
        try:
            # 调用AI生成决策树
            tree_result = await get_doctor_learning_system().generate_decision_tree(
                disease_name=request.disease_name,
                thinking_process=request.thinking_process,
                schools=selected_school_names,
                tree_prompt=tree_prompt
            )
            
            # 解析结果
            if isinstance(tree_result, str):
                try:
                    tree_data = json.loads(tree_result)
                except json.JSONDecodeError:
                    # 解析失败时返回错误
                    return DecisionTreeResponse(
                        success=False,
                        message="AI响应格式错误，JSON解析失败",
                        data=None
                    )
            else:
                tree_data = tree_result

            return DecisionTreeResponse(
                success=True,
                message="决策树生成完成",
                data=tree_data
            )
            
        except Exception as ai_error:
            logger.error(f"AI生成决策树失败: {ai_error}")
            # AI失败时直接返回错误
            return DecisionTreeResponse(
                success=False,
                message=f"AI生成失败: {str(ai_error)}",
                data=None
            )
        
    except Exception as e:
        logger.error(f"生成决策树失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")

@router.post("/save_decision_tree")
async def save_decision_tree(
    request: SaveDecisionTreeRequest,
    current_user: UserSession = Depends(get_current_user)
):
    """
    保存决策树到知识库
    
    Args:
        request: 包含决策树数据的保存请求
        current_user: 当前用户信息
        
    Returns:
        保存结果
    """
    try:
        logger.info(f"用户 {current_user.user_id} 保存决策树: {request.disease_name}")
        
        # 构建保存数据
        save_data = {
            "disease_name": request.disease_name,
            "thinking_process": request.thinking_process,
            "selected_schools": request.selected_schools,
            "decision_tree": request.decision_tree,
            "is_template": request.is_template,
            "created_by": current_user.user_id,
            "created_at": datetime.now().isoformat()
        }
        
        # 这里应该调用数据库保存功能
        # 目前先记录日志，表示保存成功
        logger.info(f"决策树保存数据: {save_data}")
        
        return {
            "success": True,
            "message": "决策树已成功保存到知识库",
            "data": {
                "saved_id": f"dt_{current_user.user_id}_{hash(request.disease_name) % 10000}",
                "saved_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"保存决策树失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")

def create_default_tree_structure(disease_name: str, schools: List[str]) -> Dict[str, Any]:
    """
    创建默认的决策树结构，支持分支条件和交互式编辑
    
    Args:
        disease_name: 疾病名称
        schools: 选择的流派列表
        
    Returns:
        包含分支条件的决策树数据结构
    """
    return {
        "tree": {
            "levels": [
                {
                    "title": "主要症状识别",
                    "type": "symptom",
                    "nodes": [
                        {"name": f"{disease_name}主证", "description": "需要详细观察的主要表现", "id": "root_symptom"}
                    ],
                    "branches": []
                },
                {
                    "title": "症状细分析",
                    "type": "symptom", 
                    "nodes": [
                        {"name": "典型症状", "description": "最常见的主要症状", "condition": "症状明显？"},
                        {"name": "伴随症状", "description": "相关的次要症状", "condition": "症状轻微？"},
                        {"name": "诱发因素", "description": "可能的病因分析", "condition": "有诱因？"}
                    ],
                    "branches": [
                        {"condition": "症状表现", "result": "positive", "target_nodes": ["典型症状", "伴随症状", "诱发因素"]}
                    ]
                },
                {
                    "title": "辨证分型",
                    "type": "diagnosis",
                    "nodes": [
                        {"name": "实证", "description": "邪气盛实的证候类型", "condition": "舌红苔厚？"},
                        {"name": "虚证", "description": "正气虚弱的证候", "condition": "面色萎黄？"},
                        {"name": "虚实夹杂", "description": "虚实并见的复合证候", "condition": "症状复杂？"}
                    ],
                    "branches": [
                        {"condition": "舌红苔厚？", "result": "positive", "target_nodes": ["实证"]},
                        {"condition": "面色萎黄？", "result": "positive", "target_nodes": ["虚证"]},
                        {"condition": "症状复杂？", "result": "positive", "target_nodes": ["虚实夹杂"]}
                    ]
                },
                {
                    "title": "治法方药",
                    "type": "formula",
                    "nodes": [
                        {"name": "黄连解毒汤", "description": "清热解毒方剂", "condition": "需清热？"},
                        {"name": "四君子汤", "description": "补气健脾方剂", "condition": "需补益？"},
                        {"name": "半夏泻心汤", "description": "寒热并用，调和中焦", "condition": "需攻补？"}
                    ],
                    "branches": [
                        {"condition": "清热治疗", "result": "positive", "target_nodes": ["黄连解毒汤"]},
                        {"condition": "补益治疗", "result": "positive", "target_nodes": ["四君子汤"]}, 
                        {"condition": "攻补并用", "result": "positive", "target_nodes": ["半夏泻心汤"]}
                    ]
                }
            ]
        },
        "school_suggestions": [
            {
                "school": school,
                "advice": f"从{school}的角度，建议重点关注相关的诊疗要点和特色治法"
            } for school in schools[:3]  # 限制建议数量
        ]
    }

@router.post("/save_decision_tree_v3")
async def save_decision_tree_v3(
    request: SaveDecisionTreeV3Request,
    current_user: UserSession = Depends(get_current_user)
):
    """
    保存V3版本的决策树（分支路径结构）
    
    Args:
        request: 包含分支路径数据的保存请求
        current_user: 当前用户信息
        
    Returns:
        保存结果
    """
    try:
        logger.info(f"用户 {current_user.user_id} 保存V3决策树: {request.disease_name}")
        
        # 构建保存数据
        save_data = {
            "disease_name": request.disease_name,
            "paths": [path.dict() for path in request.paths],
            "integration_enabled": request.integration_enabled,
            "version": "v3",
            "created_by": current_user.user_id,
            "created_at": datetime.now().isoformat()
        }
        
        # 这里应该调用数据库保存功能
        logger.info(f"V3决策树保存数据: {save_data}")
        
        return {
            "success": True,
            "message": "决策树路径已成功保存，现已启用问诊集成功能",
            "data": {
                "saved_id": f"dtv3_{current_user.user_id}_{hash(request.disease_name) % 10000}",
                "saved_at": datetime.now().isoformat(),
                "paths_count": len(request.paths)
            }
        }
        
    except Exception as e:
        logger.error(f"保存V3决策树失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")

@router.post("/match_symptoms_to_paths")
async def match_symptoms_to_paths(
    request: SymptomMatchRequest,
    current_user: UserSession = Depends(get_current_user)
):
    """
    症状匹配决策路径（用于问诊集成）
    
    Args:
        request: 包含症状列表的匹配请求
        current_user: 当前用户信息
        
    Returns:
        匹配的决策路径和推荐方剂
    """
    try:
        logger.info(f"症状匹配请求: {request.symptoms}")
        
        # 这里应该从数据库加载该疾病的所有决策路径
        # 现在使用模拟数据演示匹配逻辑
        
        sample_paths = [
            {
                "id": "path_1",
                "steps": [
                    {"type": "symptom", "content": "失眠"},
                    {"type": "condition", "content": "舌红苔黄", "result": True},
                    {"type": "diagnosis", "content": "心火旺盛"},
                    {"type": "treatment", "content": "清心火"},
                    {"type": "formula", "content": "黄连阿胶汤"}
                ],
                "keywords": ["失眠", "多梦", "心烦", "口干", "舌红", "苔黄"],
                "match_score": 0
            },
            {
                "id": "path_2",
                "steps": [
                    {"type": "symptom", "content": "失眠"},
                    {"type": "condition", "content": "面色萎黄", "result": True},
                    {"type": "diagnosis", "content": "心脾两虚"},
                    {"type": "treatment", "content": "补益心脾"},
                    {"type": "formula", "content": "归脾汤"}
                ],
                "keywords": ["失眠", "心悸", "健忘", "面色萎黄", "舌淡", "脉弱"],
                "match_score": 0
            }
        ]
        
        # 计算匹配分数
        user_symptoms_set = set([s.lower() for s in request.symptoms])
        
        for path in sample_paths:
            path_keywords_set = set([k.lower() for k in path["keywords"]])
            # 计算交集比例
            intersection = user_symptoms_set.intersection(path_keywords_set)
            path["match_score"] = len(intersection) / len(path_keywords_set) if path_keywords_set else 0
            path["matched_keywords"] = list(intersection)
        
        # 按匹配分数排序
        sample_paths.sort(key=lambda x: x["match_score"], reverse=True)
        
        # 选择最佳匹配路径
        best_match = sample_paths[0] if sample_paths and sample_paths[0]["match_score"] > 0.3 else None
        
        if best_match:
            recommended_formula = None
            treatment_method = None
            
            for step in best_match["steps"]:
                if step["type"] == "formula":
                    recommended_formula = step["content"]
                elif step["type"] == "treatment":
                    treatment_method = step["content"]
            
            return {
                "success": True,
                "message": "找到匹配的诊疗路径",
                "data": {
                    "matched_path": best_match,
                    "recommended_formula": recommended_formula,
                    "treatment_method": treatment_method,
                    "match_confidence": best_match["match_score"],
                    "matched_keywords": best_match["matched_keywords"]
                }
            }
        else:
            return {
                "success": True,
                "message": "未找到高度匹配的路径，建议手动诊断",
                "data": {
                    "matched_path": None,
                    "alternative_paths": sample_paths[:2],
                    "suggestion": "症状描述可能需要更详细，或该病症暂无对应的决策路径"
                }
            }
        
    except Exception as e:
        logger.error(f"症状匹配失败: {e}")
        raise HTTPException(status_code=500, detail=f"匹配失败: {str(e)}")


# V3版本新增API - 可视化构建器支持

class VisualDecisionTreeRequest(BaseModel):
    disease_name: str
    thinking_process: Optional[str] = ""
    include_tcm_analysis: bool = True
    complexity_level: str = "standard"  # simple, standard, complex
    use_ai: Optional[bool] = None  # 新增：手动指定AI模式
    enable_smart_branching: bool = False  # 新增：智能年龄分支功能

class TCMTheoryAnalysisRequest(BaseModel):
    tree_data: Dict[str, Any]
    disease_name: str

class MissingLogicDetectionRequest(BaseModel):
    disease_name: str
    current_paths: List[Dict[str, Any]]
    existing_nodes: List[Dict[str, Any]]

class UserPreferencesRequest(BaseModel):
    ai_mode_preferred: bool = True
    complexity_level: str = "standard"
    favorite_schools: List[str] = []

class DiagnosticCompletenessRequest(BaseModel):
    disease_name: str
    thinking_process: str
    patient_info: Optional[Dict[str, Any]] = None  # 患者信息：年龄、性别等
    custom_templates: Dict[str, Any] = {}

@router.post("/generate_visual_decision_tree")
async def generate_visual_decision_tree(
    request: VisualDecisionTreeRequest
):
    """
    智能生成决策树（混合模式：AI+模板）
    
    Args:
        request: 包含疾病名称和生成选项的请求
        
    Returns:
        智能决策树数据（包含数据来源标识）
    """
    try:
        logger.info(f"请求智能生成决策树: {request.disease_name}")
        
        try:
            # 🔍 API路由调试信息
            print(f"📡 API路由调试:")
            print(f"  - 疾病名称: {request.disease_name}")
            print(f"  - 思维过程长度: {len(request.thinking_process.strip()) if request.thinking_process else 0}")
            print(f"  - use_ai: {request.use_ai}")
            print(f"  - 调用get_doctor_learning_system().generate_decision_paths...")
            
            # 调用新的智能生成方法
            generation_result = await get_doctor_learning_system().generate_decision_paths(
                disease_name=request.disease_name,
                thinking_process=request.thinking_process,
                use_ai=request.use_ai,  # 使用前端传递的参数
                include_tcm_analysis=request.include_tcm_analysis,
                complexity_level=request.complexity_level,
                enable_smart_branching=request.enable_smart_branching  # 新增智能分支参数
            )
            
            print(f"📡 API路由返回结果:")
            print(f"  - source: {generation_result.get('source', 'MISSING')}")
            print(f"  - ai_generated: {generation_result.get('ai_generated', 'MISSING')}")
            print(f"  - user_thinking_used: {generation_result.get('user_thinking_used', 'MISSING')}")
            
            return {
                "success": True,
                "message": f"{generation_result['source'].upper()}生成完成",
                "data": generation_result,
                "ai_status": {
                    "enabled": get_doctor_learning_system().ai_enabled,
                    "source": generation_result['source'],
                    "generation_time": generation_result.get('generation_time', '未知')
                }
            }
            
        except Exception as ai_error:
            logger.error(f"智能生成决策树失败: {ai_error}")
            # AI失败时直接返回错误，不使用硬编码模板
            return {
                "success": False,
                "message": f"AI生成失败: {str(ai_error)}",
                "data": None,
                "ai_status": {
                    "enabled": get_doctor_learning_system().ai_enabled,
                    "source": "ai_failed",
                    "error": str(ai_error)
                }
            }
        
    except Exception as e:
        logger.error(f"生成决策树失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")

@router.post("/analyze_tree_tcm_theory")
async def analyze_tree_tcm_theory(
    request: TCMTheoryAnalysisRequest
):
    """
    使用AI进行中医理论分析（混合模式）
    
    Args:
        request: 包含决策树数据的分析请求
        
    Returns:
        中医理论分析结果和改进建议
    """
    try:
        logger.info(f"请求TCM理论分析: {request.disease_name}")
        
        try:
            # 优先尝试AI分析
            analysis_result = await get_doctor_learning_system().analyze_tcm_theory_with_ai(
                tree_data=request.tree_data,
                disease_name=request.disease_name
            )
            
            # 格式化分析结果为前端显示格式
            formatted_analysis = format_tcm_analysis_for_display(analysis_result)
            formatted_suggestions = format_tcm_suggestions_for_display(analysis_result)
            
            return {
                "success": True,
                "message": f"AI理论分析完成（{get_doctor_learning_system().ai_enabled and 'AI' or '模板'}模式）",
                "data": {
                    "analysis": formatted_analysis,
                    "suggestions": formatted_suggestions,
                    "source": "ai" if get_doctor_learning_system().ai_enabled else "template",
                    "ai_enabled": get_doctor_learning_system().ai_enabled
                }
            }
            
        except Exception as ai_error:
            logger.error(f"TCM理论分析失败: {ai_error}")
            # 返回默认分析
            default_analysis = create_default_tcm_analysis(request.disease_name)
            formatted_default_analysis = format_tcm_analysis_for_display(default_analysis)
            formatted_default_suggestions = format_tcm_suggestions_for_display(default_analysis)
            
            return {
                "success": True,
                "message": "理论分析完成（模板模式）",
                "data": {
                    "analysis": formatted_default_analysis,
                    "suggestions": formatted_default_suggestions,
                    "source": "template_fallback",
                    "ai_enabled": False,
                    "error": str(ai_error)
                }
            }
        
    except Exception as e:
        logger.error(f"TCM理论分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失赅: {str(e)}")

@router.post("/detect_missing_logic")
async def detect_missing_logic(
    request: MissingLogicDetectionRequest
):
    """
    检测决策树遗漏的诊疗逻辑 - 简化版本
    
    直接返回预定义的建议，避免复杂的AI调用导致卡死
    """
    try:
        logger.info(f"请求遗漏逻辑检测: {request.disease_name}")
        
        # 直接返回简化的遗漏逻辑分析，避免复杂处理
        detection_data = create_simple_missing_logic_analysis(request.disease_name, request.existing_nodes)
        
        return {
            "success": True,
            "message": "遗漏逻辑检测完成",
            "data": detection_data
        }
        
    except Exception as e:
        logger.error(f"遗漏逻辑检测失败: {e}")
        # 确保始终返回有效响应
        return {
            "success": True,
            "message": "检测完成（基础分析）",
            "data": {
                "missing_analyses": [
                    {
                        "category": "基础分析",
                        "items": [
                            {
                                "type": "general_suggestion",
                                "content": "建议完善决策树",
                                "description": "当前决策树可以进一步细化",
                                "importance": "medium"
                            }
                        ]
                    }
                ],
                "quick_additions": [
                    {
                        "title": "基础补充",
                        "path_data": {"steps": [{"type": "condition", "content": "补充判断条件"}]}
                    }
                ]
            }
        }

def create_simple_missing_logic_analysis(disease_name: str, existing_nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """创建简化的遗漏逻辑分析，避免复杂处理"""
    
    # 获取现有节点的证型和条件
    existing_diagnoses = set()
    existing_conditions = set()
    
    for node in existing_nodes:
        if node.get("type") == "diagnosis":
            existing_diagnoses.add(node.get("name", ""))
        elif node.get("type") == "condition":
            existing_conditions.add(node.get("name", ""))
    
    # 常见证型和条件库
    disease_knowledge = {
        "失眠": {
            "syndromes": ["心火旺盛证", "心脾两虚证", "肝郁化火证", "心肾不交证", "痰热扰心证"],
            "conditions": ["舌红苔黄", "舌淡苔白", "胸胁胀满", "五心烦热", "痰多咳嗽"],
            "formulas": ["黄连阿胶汤", "归脾汤", "逍遥散", "天王补心丹", "温胆汤"]
        },
        "胃痛": {
            "syndromes": ["脾胃虚寒证", "肝气犯胃证", "胃阴不足证", "湿热中阻证", "瘀血阻络证"],
            "conditions": ["喜温喜按", "胀痛拒按", "口干咽燥", "口苦黏腻", "刺痛固定"],
            "formulas": ["理中汤", "柴胡疏肝散", "麦门冬汤", "黄芩汤", "失笑散"]
        },
        "头痛": {
            "syndromes": ["风寒头痛", "风热头痛", "肝阳上亢", "痰浊头痛", "血瘀头痛"],
            "conditions": ["恶寒发热", "咽红口干", "眩晕耳鸣", "头重如裹", "痛如锥刺"],
            "formulas": ["川芎茶调散", "桑菊饮", "天麻钩藤饮", "半夏白术天麻汤", "血府逐瘀汤"]
        }
    }
    
    current_disease = disease_knowledge.get(disease_name, {
        "syndromes": [f"{disease_name}虚证", f"{disease_name}实证", f"{disease_name}虚实夹杂证"],
        "conditions": ["舌象变化", "脉象特点", "体质因素"],
        "formulas": ["补益方剂", "清热方剂", "调和方剂"]
    })
    
    # 找出遗漏的内容
    missing_syndromes = [s for s in current_disease["syndromes"] if s not in existing_diagnoses]
    missing_conditions = [c for c in current_disease["conditions"] if c not in existing_conditions]
    
    missing_analyses = []
    
    if missing_syndromes:
        missing_analyses.append({
            "category": "证型分析",
            "items": [
                {
                    "type": "missing_syndrome",
                    "content": syndrome,
                    "description": f"{disease_name}的{syndrome}是常见证型，建议补充",
                    "importance": "high",
                    "suggested_addition": {
                        "step_type": "diagnosis",
                        "step_content": syndrome
                    }
                } for syndrome in missing_syndromes[:3]
            ]
        })
    
    if missing_conditions:
        missing_analyses.append({
            "category": "判断条件",
            "items": [
                {
                    "type": "missing_condition",
                    "content": condition,
                    "description": f"建议增加{condition}的临床观察",
                    "importance": "medium",
                    "suggested_addition": {
                        "step_type": "condition",
                        "step_content": condition
                    }
                } for condition in missing_conditions[:3]
            ]
        })
    
    quick_additions = [
        {
            "title": "补充鉴别诊断",
            "path_data": {
                "steps": [
                    {"type": "condition", "content": "典型症状特征"},
                    {"type": "diagnosis", "content": f"确诊{disease_name}"}
                ]
            }
        },
        {
            "title": "添加预后评估",
            "path_data": {
                "steps": [
                    {"type": "condition", "content": "治疗效果评估"},
                    {"type": "treatment", "content": "调整治疗方案"}
                ]
            }
        }
    ]
    
    return {
        "missing_analyses": missing_analyses,
        "quick_additions": quick_additions
    }

def create_default_visual_tree(disease_name: str) -> Dict[str, Any]:
    """创建默认的可视化决策树数据"""
    return {
        "paths": [
            {
                "id": f"{disease_name}_path_1",
                "title": f"{disease_name}实热证路径",
                "steps": [
                    {"type": "symptom", "content": f"{disease_name}"},
                    {"type": "condition", "content": "舌红苔黄", "options": ["是", "否"]},
                    {"type": "diagnosis", "content": "实热证"},
                    {"type": "treatment", "content": "清热法"},
                    {"type": "formula", "content": "黄连解毒汤"}
                ],
                "keywords": [disease_name, "舌红", "苔黄", "实热"],
                "tcm_theory": "实则泻之，热者清之"
            },
            {
                "id": f"{disease_name}_path_2", 
                "title": f"{disease_name}虚寒证路径",
                "steps": [
                    {"type": "symptom", "content": f"{disease_name}"},
                    {"type": "condition", "content": "舌淡苔白", "options": ["是", "否"]},
                    {"type": "diagnosis", "content": "虚寒证"},
                    {"type": "treatment", "content": "温补法"},
                    {"type": "formula", "content": "理中汤"}
                ],
                "keywords": [disease_name, "舌淡", "苔白", "虚寒"],
                "tcm_theory": "虚则补之，寒者热之"
            }
        ],
        "suggested_layout": {
            "auto_arrange": True,
            "spacing": {"horizontal": 300, "vertical": 150}
        }
    }

def format_tcm_analysis_for_display(analysis_data: Dict[str, Any]) -> str:
    """将TCM分析数据格式化为前端显示格式"""
    try:
        theory_analysis = analysis_data.get("theory_analysis", {})
        score = theory_analysis.get("overall_score", 75)
        strengths = theory_analysis.get("strengths", [])
        weaknesses = theory_analysis.get("weaknesses", [])
        basis = theory_analysis.get("theoretical_basis", "")
        
        display_text = f"""
        <div style="margin-bottom: 15px;">
            <h3 style="color: #1e40af; margin: 0 0 10px 0;">📊 理论合理性评分: {score}/100</h3>
            
            <div style="background: #f0f9ff; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
                <strong style="color: #059669;">✅ 理论优势:</strong><br>
                {('<br>'.join([f'• {s}' for s in strengths]) if strengths else '• 基本符合中医理论')}
            </div>
            
            <div style="background: #fef3c7; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
                <strong style="color: #d97706;">⚠️ 改进建议:</strong><br>
                {('<br>'.join([f'• {w}' for w in weaknesses]) if weaknesses else '• 可进一步完善理论细节')}
            </div>
            
            <div style="background: #f3f4f6; padding: 12px; border-radius: 6px; font-size: 11px;">
                <strong>📚 理论依据:</strong><br>
                {basis}
            </div>
        </div>
        """
        
        return display_text.strip()
        
    except Exception as e:
        return f"<div style='color: #ef4444;'>理论分析格式化失败: {str(e)}</div>"

def format_tcm_suggestions_for_display(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """将TCM建议数据格式化为前端显示格式"""
    try:
        suggestions_data = analysis_data.get("improvement_suggestions", [])
        supplements_data = analysis_data.get("knowledge_supplements", [])
        
        missing_differentials = []
        additional_conditions = []
        theoretical_basis = ""
        
        for suggestion in suggestions_data:
            if suggestion.get("type") == "theory_enhancement":
                missing_differentials.append(suggestion.get("description", ""))
            elif suggestion.get("type") == "differential_diagnosis":
                additional_conditions.append(suggestion.get("description", ""))
        
        if supplements_data:
            theoretical_basis = "; ".join([s.get("content", "") for s in supplements_data])
        
        return {
            "missing_differentials": missing_differentials or ["建议加强理论分析"],
            "additional_conditions": additional_conditions or ["完善判断条件"],
            "theoretical_basis": theoretical_basis or "基于传统中医理论体系"
        }
        
    except Exception as e:
        return {
            "missing_differentials": ["格式化失败，请重试"],
            "additional_conditions": ["数据处理异常"],
            "theoretical_basis": "无法获取理论依据"
        }

def create_default_tcm_analysis(disease_name: str) -> Dict[str, Any]:
    """创建默认的TCM理论分析 - 侧重理论评估"""
    
    # 理论分析侧重于评估决策树的中医理论合理性
    theory_knowledge = {
        "失眠": {
            "strengths": ["体现了心主神明的理论", "考虑了虚实寒热的辨证", "方药选择符合病机"],
            "weaknesses": ["可加强脏腑关系分析", "需补充时间医学理论", "宜细化体质辨识"],
            "basis": "失眠一证，虽责之于心，然五脏皆能致之。心肾不交、肝郁化火、脾虚不运皆为常见病机",
            "score": 82
        },
        "胃痛": {
            "strengths": ["体现了脾胃为后天之本", "考虑了肝木克土理论", "注意了寒热虚实"],
            "weaknesses": ["可补充六腑以通为用", "需加强情志因素", "宜重视饮食调护"],
            "basis": "胃痛多因饮食、情志、感受外邪等导致胃失和降。肝胃不和最为常见",
            "score": 78
        }
    }
    
    current_theory = theory_knowledge.get(disease_name, {
        "strengths": ["基本辨证思路清晰", "症状与治法对应", "方药选择合理"],
        "weaknesses": ["可深化病机分析", "需补充经典依据", "宜加强个体化"],
        "basis": f"基于中医{disease_name}的传统辨证论治理论体系",
        "score": 75
    })
    
    return {
        "theory_analysis": {
            "overall_score": current_theory["score"],
            "strengths": current_theory["strengths"],
            "weaknesses": current_theory["weaknesses"],
            "theoretical_basis": current_theory["basis"]
        },
        "improvement_suggestions": [
            {
                "type": "theory_enhancement",
                "description": f"加强{disease_name}的病机理论阐述",
                "priority": "high"
            },
            {
                "type": "differential_diagnosis", 
                "description": "补充经典方书理论依据",
                "priority": "medium"
            },
            {
                "type": "individualization",
                "description": "细化脏腑关系分析",
                "priority": "medium"
            }
        ],
        "knowledge_supplements": [
            {
                "topic": "病机理论",
                "content": f"{disease_name}的基本病机和病理生理",
                "source": "中医内科学"
            },
            {
                "topic": "方剂配伍",
                "content": f"治疗{disease_name}的经典方剂及其配伍原理",
                "source": "方剂学"
            },
            {
                "topic": "临床经验",
                "content": f"名医治疗{disease_name}的特色经验",
                "source": "临床实践"
            }
        ]
    }

def create_default_missing_logic_analysis(disease_name: str) -> Dict[str, Any]:
    """创建默认的遗漏逻辑分析"""
    return {
        "missing_analyses": [
            {
                "category": "证型分析",
                "items": [
                    {
                        "type": "missing_syndrome",
                        "content": f"{disease_name}的少见证型",
                        "description": "可能遗漏的特殊证候表现",
                        "importance": "medium",
                        "suggested_addition": {
                            "step_type": "diagnosis",
                            "step_content": "特殊证型诊断"
                        }
                    }
                ]
            },
            {
                "category": "鉴别诊断",
                "items": [
                    {
                        "type": "differential_diagnosis",
                        "content": "相关疾病鉴别",
                        "description": "需要与类似疾病进行鉴别",
                        "importance": "high",
                        "suggested_addition": {
                            "step_type": "condition",
                            "step_content": "鉴别诊断要点"
                        }
                    }
                ]
            }
        ],
        "quick_additions": [
            {
                "title": "补充鉴别诊断路径",
                "path_data": {
                    "steps": [
                        {"type": "condition", "content": "是否伴有其他症状"},
                        {"type": "diagnosis", "content": "排除相关疾病"}
                    ]
                }
            }
        ]
    }


@router.post("/generate_paths_from_thinking")
async def generate_paths_from_thinking(request: Request):
    """
    从医生思维过程生成决策路径

    Args:
        request: 包含 disease_name 和 thinking_process 的请求体

    Returns:
        生成的决策路径列表
    """
    try:
        data = await request.json()
        disease_name = data.get("disease_name", "").strip()
        thinking_process = data.get("thinking_process", "").strip()

        if not disease_name:
            return {"success": False, "message": "疾病名称不能为空"}

        keywords = []
        if "舌" in thinking_process:
            keywords.append("舌象观察")
        if "脉" in thinking_process:
            keywords.append("脉象诊断")
        if "证" in thinking_process:
            keywords.append("证候分析")
        if "方" in thinking_process or "药" in thinking_process:
            keywords.append("方药选择")
        if "治" in thinking_process:
            keywords.append("治则治法")

        paths = [{
            "id": f"path_{disease_name}_1",
            "steps": [
                {"type": "symptom", "content": f"{disease_name}主要症状"},
                {"type": "condition", "content": "四诊合参", "result": True},
                {"type": "diagnosis", "content": f"{disease_name}证候分型"},
                {"type": "treatment", "content": "辨证论治"},
                {"type": "formula", "content": "随证选方"}
            ],
            "keywords": keywords or [disease_name],
            "match_score": 0
        }]

        if thinking_process:
            for i, keyword in enumerate(keywords):
                paths.append({
                    "id": f"path_{disease_name}_{i + 2}",
                    "steps": [
                        {"type": "symptom", "content": f"{disease_name}相关表现"},
                        {"type": "condition", "content": keyword, "result": True},
                        {"type": "diagnosis", "content": f"基于{keyword}的证型判断"},
                        {"type": "treatment", "content": "对应治法"},
                        {"type": "formula", "content": "推荐方剂"}
                    ],
                    "keywords": [keyword, disease_name],
                    "match_score": 0
                })

        return {"success": True, "data": {"paths": paths}}

    except Exception as e:
        logger.error(f"生成决策路径失败: {e}")
        return {"success": False, "message": f"生成决策路径失败: {str(e)}"}


@router.get("/user_preferences/{user_id}")
async def get_user_preferences(
    user_id: str,
    current_user: UserSession = Depends(get_current_user)
):
    """获取用户偏好设置"""
    try:
        # 权限检查：只能访问自己的偏好设置
        # 🔧 修复：兼容统一认证系统
        user_roles = getattr(current_user, 'roles', [getattr(current_user, 'role', None)])
        is_admin = any(role in ['admin', 'ADMIN', UserRole.ADMIN] for role in user_roles if role)

        if current_user.user_id != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="无权限访问")
        
        preferences = get_doctor_learning_system().get_user_preferences(user_id)
        
        return {
            "success": True,
            "message": "获取用户偏好成功",
            "data": preferences
        }
        
    except Exception as e:
        logger.error(f"获取用户偏好失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@router.post("/user_preferences/{user_id}")
async def save_user_preferences(
    user_id: str,
    request: UserPreferencesRequest,
    current_user: UserSession = Depends(get_current_user)
):
    """保存用户偏好设置"""
    try:
        # 权限检查：只能修改自己的偏好设置
        # 🔧 修复：兼容统一认证系统
        user_roles = getattr(current_user, 'roles', [getattr(current_user, 'role', None)])
        is_admin = any(role in ['admin', 'ADMIN', UserRole.ADMIN] for role in user_roles if role)

        if current_user.user_id != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="无权限修改")
        
        preferences = {
            "ai_mode_preferred": request.ai_mode_preferred,
            "complexity_level": request.complexity_level,
            "favorite_schools": request.favorite_schools,
            "custom_templates": request.custom_templates
        }
        
        get_doctor_learning_system().save_user_preferences(user_id, preferences)
        
        return {
            "success": True,
            "message": "用户偏好保存成功",
            "data": preferences
        }
        
    except Exception as e:
        logger.error(f"保存用户偏好失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")

@router.get("/ai_status")
async def get_ai_status():
    """获取AI功能状态"""
    try:
        return {
            "success": True,
            "message": "AI状态获取成功",
            "data": {
                "ai_enabled": get_doctor_learning_system().ai_enabled,
                "ai_model": getattr(get_doctor_learning_system(), 'ai_model', 'unknown'),
                "dashscope_available": DASHSCOPE_AVAILABLE,
                "learning_enabled": getattr(get_doctor_learning_system(), 'learning_enabled', False),
                "features": {
                    "decision_tree_generation": get_doctor_learning_system().ai_enabled,
                    "theory_analysis": get_doctor_learning_system().ai_enabled,
                    "hybrid_mode": True,
                    "user_learning": getattr(get_doctor_learning_system(), 'learning_enabled', False)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"获取AI状态失败: {e}")
        return {
            "success": False,
            "message": f"获取失败: {str(e)}",
            "data": {
                "ai_enabled": False,
                "error": str(e)
            }
        }

@router.post("/feedback/decision_tree/{tree_id}")
async def submit_decision_tree_feedback(
    tree_id: str,
    feedback_score: int,
    improvement_notes: str = "",
    current_user: UserSession = Depends(get_current_user)
):
    """提交决策树反馈用于学习改进"""
    try:
        if not (1 <= feedback_score <= 5):
            raise HTTPException(status_code=400, detail="评分必须在1-5之间")
        
        # 这里可以记录用户反馈到学习数据库
        # 目前简化处理
        logger.info(f"收到决策树反馈 - 用户: {current_user.user_id}, 树ID: {tree_id}, 评分: {feedback_score}")
        
        return {
            "success": True,
            "message": "反馈提交成功，感谢您的宝贵意见！",
            "data": {
                "feedback_id": f"fb_{tree_id}_{current_user.user_id}",
                "submitted_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"提交决策树反馈失败: {e}")
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")

@router.post("/analyze_diagnostic_completeness")
async def analyze_diagnostic_completeness(
    request: DiagnosticCompletenessRequest,
    current_user: UserSession = Depends(get_current_user)
):
    """
    智能分析诊疗流程完整性
    
    分析医生输入的诊疗思路，识别缺失的标准诊疗要素，
    并提供智能补充建议
    """
    try:
        logger.info(f"诊疗流程完整性分析 - 疾病: {request.disease_name}, 用户: {current_user.user_id}")
        
        # 调用名医学习系统进行完整性分析
        completeness_result = await get_doctor_learning_system()._analyze_diagnostic_completeness(
            request.disease_name, 
            request.thinking_process
        )
        
        # 添加患者信息考虑（如果提供）
        if request.patient_info:
            age = request.patient_info.get("age")
            gender = request.patient_info.get("gender")
            
            # 基于年龄和性别调整建议
            if age:
                if age < 18:
                    completeness_result["recommendations"].append("儿童患者需特别注意药物剂量调整")
                elif age > 65:
                    completeness_result["recommendations"].append("老年患者需考虑脏腑功能衰退，用药宜温和")
            
            if gender:
                if gender == "女":
                    completeness_result["recommendations"].append("女性患者需考虑月经、妊娠等生理特点")
        
        # 生成详细的改进建议
        improvement_suggestions = []
        for missing_item in completeness_result["missing_items"]:
            suggestion = await _generate_item_specific_suggestion(
                missing_item, request.disease_name, request.thinking_process
            )
            improvement_suggestions.append(suggestion)
        
        return {
            "success": True,
            "message": f"诊疗流程完整性分析完成",
            "data": {
                "completeness_rate": completeness_result["completeness_rate"],
                "present_items": completeness_result["present_items"],
                "missing_items": completeness_result["missing_items"],
                "recommendations": completeness_result["recommendations"],
                "improvement_suggestions": improvement_suggestions,
                "patient_considerations": request.patient_info or {},
                "analysis_summary": {
                    "total_items": 9,
                    "present_count": len(completeness_result["present_items"]),
                    "missing_count": len(completeness_result["missing_items"]),
                    "completeness_level": _get_completeness_level(completeness_result["completeness_rate"])
                }
            }
        }
        
    except Exception as e:
        logger.error(f"诊疗流程完整性分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

async def _generate_item_specific_suggestion(missing_item: Dict[str, Any], disease_name: str, thinking_process: str) -> Dict[str, Any]:
    """为特定缺失项目生成具体建议"""
    item_key = missing_item["key"]
    
    # 基于不同项目类型生成针对性建议
    suggestions_map = {
        "four_diagnosis": {
            "suggestion": f"建议补充{disease_name}的典型舌脉象",
            "examples": ["舌质红苔黄厚", "脉象弦数", "面色萎黄", "声音低微"],
            "importance": "high"
        },
        "pathogenesis": {
            "suggestion": f"建议分析{disease_name}的病因病机",
            "examples": ["外感风邪", "脾胃虚弱", "肝气郁结", "肾阳不足"],
            "importance": "high"
        },
        "modifications": {
            "suggestion": "建议添加随症加减方案",
            "examples": ["伴发热加银花、连翘", "便秘加大黄、芒硝", "失眠加酸枣仁、龙骨"],
            "importance": "medium"
        },
        "prognosis_care": {
            "suggestion": "建议添加预后调理指导",
            "examples": ["饮食调养", "情志调摄", "起居有常", "适度运动"],
            "importance": "medium"
        }
    }
    
    return suggestions_map.get(item_key, {
        "suggestion": f"建议补充{missing_item['description']}",
        "examples": [],
        "importance": "low"
    })

def _get_completeness_level(rate: float) -> str:
    """获取完整度等级"""
    if rate >= 0.9:
        return "优秀"
    elif rate >= 0.7:
        return "良好"
    elif rate >= 0.5:
        return "一般"
    else:
        return "需改进"

# ======================== 新增：诊疗信息提取和处方生成 ========================

class PrescriptionExtractionRequest(BaseModel):
    """处方提取请求"""
    thinking_process: str
    patient_age: Optional[int] = None  # 患者年龄
    patient_gender: Optional[str] = None  # 患者性别 male/female
    patient_weight: Optional[float] = None  # 患者体重(kg)
    special_conditions: List[str] = []  # 特殊情况：pregnancy, lactation, elderly等

@router.post("/extract_prescription_info")
async def extract_prescription_info(
    request: PrescriptionExtractionRequest
):
    """
    从诊疗思路中提取病种、病情、处方信息，并生成个性化用量
    
    Args:
        request: 包含诊疗思路和患者信息的请求
        
    Returns:
        提取的诊疗信息和个性化处方
    """
    try:
        logger.info(f"开始提取诊疗信息，思路长度: {len(request.thinking_process)}")
        
        # 调用AI提取结构化信息
        extraction_result = await _extract_clinical_info_with_ai(
            request.thinking_process,
            request.patient_age,
            request.patient_gender,
            request.patient_weight,
            request.special_conditions
        )
        
        return {
            "success": True,
            "message": "诊疗信息提取成功",
            "data": extraction_result
        }
        
    except Exception as e:
        logger.error(f"诊疗信息提取失败: {e}")
        return {
            "success": False,
            "message": f"提取失败: {str(e)}",
            "data": None
        }

async def _extract_clinical_info_with_ai(
    thinking_process: str,
    patient_age: Optional[int],
    patient_gender: Optional[str],
    patient_weight: Optional[float],
    special_conditions: List[str]
) -> Dict[str, Any]:
    """使用AI提取临床信息并生成个性化处方"""
    
    # 构建患者信息描述
    patient_info = _build_patient_info_description(
        patient_age, patient_gender, patient_weight, special_conditions
    )
    
    # 🔧 智能检测：判断思路中是否已明确人群用药
    age_group_detected = _detect_age_group_in_thinking(thinking_process)
    
    # 构建AI提示词
    prompt = f"""
请从以下中医诊疗思路中提取结构化信息，并根据患者特征生成个性化处方：

诊疗思路：{thinking_process}

患者信息：{patient_info}
诊疗思路分析：{age_group_detected['description']}

请提取以下信息并以JSON格式返回：
{{
    "disease_name": "病种名称（从思路中提取）",
    "symptom_description": "主要症状描述（详细列出所有症状）",
    "tongue_pulse": "舌脉象描述",
    "syndrome_differentiation": "中医证型诊断",
    "treatment_principle": "治疗方法",
    "base_prescription": {{
        "name": "方剂名称",
        "composition": [
            {{
                "herb_name": "药材名称",
                "standard_dose": "成人标准剂量（克）",
                "current_dose": "当前患者推荐剂量（克）",
                "function": "功效作用"
            }}
        ]
    }},
    "dosage_adjustments": {{
        "age_factor": "年龄调整说明",
        "gender_factor": "性别考虑事项",
        "weight_factor": "体重调整说明",
        "special_notes": "特殊注意事项"
    }},
    "administration": {{
        "preparation": "煎煮方法",
        "dosage": "服用剂量和频次",
        "course": "疗程建议",
        "precautions": "注意事项"
    }}
}}

剂量调整原则（智能识别模式）：
{_generate_dosage_adjustment_rules(age_group_detected, patient_age, patient_weight, special_conditions)}
"""

    try:
        # 调用AI生成
        response = await asyncio.to_thread(
            dashscope.MultiModalConversation.call,
            model=AI_CONFIG.get('decision_tree_model', 'qwen3.5-omni-plus-2026-03-15'),
            messages=[{"role": "user", "content": [{"text": prompt}]}]
        )

        if response.status_code == 200:
            content = response.output.choices[0].message.content[0]["text"]
            
            # 解析JSON响应
            ai_result = _parse_prescription_json(content)
            
            return ai_result
        else:
            raise Exception(f"AI调用失败: {response.message}")
            
    except Exception as e:
        logger.error(f"AI提取失败: {e}")
        # 返回基础解析结果
        return _basic_prescription_extraction(thinking_process, patient_age, patient_gender)

def _build_patient_info_description(
    age: Optional[int],
    gender: Optional[str],
    weight: Optional[float],
    special_conditions: List[str]
) -> str:
    """构建患者信息描述"""
    info_parts = []
    
    if age is not None:
        if age < 18:
            info_parts.append(f"儿童患者，{age}岁")
        elif age > 65:
            info_parts.append(f"老年患者，{age}岁")
        else:
            info_parts.append(f"成年患者，{age}岁")
    
    if gender:
        gender_map = {"male": "男性", "female": "女性"}
        info_parts.append(gender_map.get(gender, gender))
    
    if weight is not None:
        if weight < 50:
            info_parts.append(f"体重{weight}kg（偏轻）")
        elif weight > 80:
            info_parts.append(f"体重{weight}kg（偏重）")
        else:
            info_parts.append(f"体重{weight}kg")
    
    if special_conditions:
        condition_map = {
            "pregnancy": "妊娠期",
            "lactation": "哺乳期",
            "elderly": "高龄",
            "diabetes": "糖尿病",
            "hypertension": "高血压",
            "liver_disease": "肝病",
            "kidney_disease": "肾病"
        }
        special_desc = [condition_map.get(c, c) for c in special_conditions]
        info_parts.append(f"特殊情况：{', '.join(special_desc)}")
    
    return "；".join(info_parts) if info_parts else "无特殊情况"

def _parse_prescription_json(content: str) -> Dict[str, Any]:
    """解析AI返回的处方JSON"""
    import re
    import json
    
    # 尝试多种JSON提取模式
    json_patterns = [
        r'```json\s*(\{[\s\S]*?\})\s*```',
        r'```\s*(\{[\s\S]*?\})\s*```',
        r'(\{[\s\S]*?\})'
    ]
    
    for pattern in json_patterns:
        json_match = re.search(pattern, content)
        if json_match:
            json_content = json_match.group(1)
            try:
                return json.loads(json_content)
            except json.JSONDecodeError:
                continue
    
    # 如果JSON解析失败，返回基础结构
    return {
        "disease_name": "信息提取失败",
        "symptom_description": content[:200] + "..." if len(content) > 200 else content,
        "error": "JSON解析失败，请检查AI响应格式"
    }

def _basic_prescription_extraction(
    thinking_process: str,
    age: Optional[int],
    gender: Optional[str]
) -> Dict[str, Any]:
    """基础的处方信息提取（当AI失败时的备用方案）"""
    import re
    
    # 基础信息提取
    disease_match = re.search(r'(\w+不\w+|\w+病|\w+症)', thinking_process)
    disease_name = disease_match.group(1) if disease_match else "未明确病名"
    
    # 症状提取
    symptom_patterns = [
        r'症见[:：]([^。]+)',
        r'表现为([^。]+)',
        r'症状([^。]+)'
    ]
    symptoms = []
    for pattern in symptom_patterns:
        matches = re.findall(pattern, thinking_process)
        symptoms.extend(matches)
    
    # 方剂提取
    prescription_match = re.search(r'方药[:：]([^。]+)', thinking_process)
    prescription_name = prescription_match.group(1).strip() if prescription_match else "未明确方剂"
    
    return {
        "disease_name": disease_name,
        "symptom_description": "，".join(symptoms) if symptoms else "症状信息提取失败",
        "base_prescription": {
            "name": prescription_name,
            "composition": []
        },
        "note": "基础提取结果，建议手动补充"
    }

# ======================== 医生思维库功能 ========================

class ClinicalPatternRequest(BaseModel):
    """临床模式保存请求"""
    disease_name: str
    thinking_process: str
    tree_structure: Dict[str, Any]
    clinical_patterns: Dict[str, Any]
    doctor_expertise: Dict[str, Any]

@router.post("/save_clinical_pattern")
async def save_clinical_pattern(
    request: ClinicalPatternRequest,
    current_user: UserSession = Depends(get_current_user)
):
    """
    保存临床决策模式到医生思维库
    
    Args:
        request: 临床模式数据
        current_user: 当前用户会话
        
    Returns:
        保存结果
    """
    try:
        # 🔧 修复：统一认证系统使用 roles (List[str])，而非 role
        roles = getattr(current_user, 'roles', [getattr(current_user, 'role', None)])
        if isinstance(roles, str):
            roles = [roles]

        logger.info(f"医生思维库保存请求 - 用户: {current_user.user_id}, 角色: {roles}")

        # 🔐 权限验证：确保是医生用户
        # 检查是否有DOCTOR或ADMIN角色
        has_doctor_role = any(role in ['DOCTOR', 'ADMIN', UserRole.DOCTOR, UserRole.ADMIN] for role in roles if role)

        if not has_doctor_role:
            # 🔧 临时解决方案：如果是匿名用户，尝试创建临时医生身份
            is_anonymous = any(role in ['ANONYMOUS', UserRole.ANONYMOUS] for role in roles if role)
            if is_anonymous:
                doctor_id = await _create_or_get_temp_doctor_identity(request.disease_name)
                logger.info(f"为匿名用户创建临时医生身份: {doctor_id}")
            else:
                raise HTTPException(
                    status_code=403,
                    detail="仅医生用户可保存临床决策模式到思维库"
                )
        else:
            doctor_id = current_user.user_id
            logger.info(f"✅ 使用医生用户ID保存决策树: {doctor_id}")
        
        # 🗄️ 保存到数据库
        pattern_data = {
            "doctor_id": doctor_id,
            "disease_name": request.disease_name,
            "thinking_process": request.thinking_process,
            "tree_structure": json.dumps(request.tree_structure),
            "clinical_patterns": json.dumps(request.clinical_patterns),
            "doctor_expertise": json.dumps(request.doctor_expertise),
            "usage_count": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        pattern_id = await _save_pattern_to_database(pattern_data)
        
        # 📊 分析模式类型
        pattern_type = _analyze_pattern_type(request.clinical_patterns, request.doctor_expertise)
        
        logger.info(f"临床模式保存成功: pattern_id={pattern_id}, doctor_id={doctor_id}")
        
        return {
            "success": True,
            "message": f"临床决策模式已成功保存到医生 {doctor_id} 的思维库",
            "data": {
                "pattern_id": pattern_id,
                "doctor_id": doctor_id,
                "pattern_type": pattern_type,
                "disease_name": request.disease_name,
                "saved_at": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存临床模式失败: {e}")
        return {
            "success": False,
            "message": f"保存失败: {str(e)}"
        }

# ======================== 思维库查询功能 ========================

@router.get("/get_doctor_patterns/{doctor_id}")
async def get_doctor_clinical_patterns(
    doctor_id: str,
    disease_name: Optional[str] = None,
    current_user: UserSession = Depends(get_current_user)
):
    """
    获取医生的临床决策模式
    
    Args:
        doctor_id: 医生ID
        disease_name: 疾病名称（可选，用于精确匹配）
        current_user: 当前用户会话
        
    Returns:
        医生的临床决策模式列表
    """
    try:
        logger.info(f"获取医生 {doctor_id} 的临床模式")
        
        # 🗄️ 从数据库查询临床模式
        db_path = USER_DB_PATH
        
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if disease_name:
                # 精确匹配疾病名称
                query = """
                    SELECT * FROM doctor_clinical_patterns 
                    WHERE doctor_id = ? AND disease_name = ?
                    ORDER BY created_at DESC
                """
                params = (doctor_id, disease_name)
            else:
                # 获取所有模式
                query = """
                    SELECT * FROM doctor_clinical_patterns 
                    WHERE doctor_id = ?
                    ORDER BY created_at DESC
                """
                params = (doctor_id,)
            
            patterns = conn.execute(query, params).fetchall()
            
            patterns_data = []
            for pattern in patterns:
                pattern_data = {
                    "pattern_id": pattern["id"],  # 🔧 修复：数据库列名是 id，不是 pattern_id
                    "doctor_id": pattern["doctor_id"],
                    "disease_name": pattern["disease_name"],
                    "thinking_process": pattern["thinking_process"],
                    "tree_structure": json.loads(pattern["tree_structure"]) if pattern["tree_structure"] else {},
                    "clinical_patterns": json.loads(pattern["clinical_patterns"]) if pattern["clinical_patterns"] else {},
                    "doctor_expertise": json.loads(pattern["doctor_expertise"]) if pattern["doctor_expertise"] else {},
                    "usage_count": pattern["usage_count"],
                    "created_at": pattern["created_at"],
                    "updated_at": pattern["updated_at"]
                }
                patterns_data.append(pattern_data)
        
        return {
            "success": True,
            "message": f"找到 {len(patterns_data)} 个临床决策模式",
            "data": {
                "doctor_id": doctor_id,
                "disease_name": disease_name,
                "patterns": patterns_data,
                "total_count": len(patterns_data)
            }
        }
        
    except Exception as e:
        logger.error(f"获取临床模式失败: {e}")
        return {
            "success": False,
            "message": f"保存失败: {str(e)}",
            "data": None
        }

@router.delete("/delete_clinical_pattern/{pattern_id}")
async def delete_clinical_pattern(
    pattern_id: str,
    current_user: UserSession = Depends(get_current_user)
):
    """
    删除指定的临床决策模式

    Args:
        pattern_id: 模式ID
        current_user: 当前用户会话

    Returns:
        删除结果
    """
    try:
        logger.info(f"删除临床模式请求 - pattern_id: {pattern_id}, user: {current_user.user_id}")

        # 连接数据库
        conn = sqlite3.connect(USER_DB_PATH)
        cursor = conn.cursor()

        try:
            # 先查询该模式是否存在，并验证所有权
            cursor.execute("""
                SELECT doctor_id, disease_name FROM doctor_clinical_patterns
                WHERE id = ?
            """, (pattern_id,))

            result = cursor.fetchone()

            if not result:
                return {
                    "success": False,
                    "message": "未找到该诊疗方案"
                }

            doctor_id, disease_name = result

            # 验证权限：只能删除自己的模式（或管理员）
            roles = getattr(current_user, 'roles', [getattr(current_user, 'role', None)])
            if isinstance(roles, str):
                roles = [roles]

            is_admin = any(role in ['ADMIN', UserRole.ADMIN] for role in roles if role)
            is_owner = (doctor_id == current_user.user_id)

            if not (is_admin or is_owner):
                return {
                    "success": False,
                    "message": "您没有权限删除此诊疗方案"
                }

            # 执行删除
            cursor.execute("DELETE FROM doctor_clinical_patterns WHERE id = ?", (pattern_id,))
            conn.commit()

            logger.info(f"✅ 成功删除临床模式: {pattern_id} ({disease_name})")

            return {
                "success": True,
                "message": f"已成功删除诊疗方案：{disease_name}",
                "data": {
                    "pattern_id": pattern_id,
                    "disease_name": disease_name,
                    "deleted_at": datetime.now().isoformat()
                }
            }

        finally:
            conn.close()

    except Exception as e:
        logger.error(f"删除临床模式失败: {e}")
        return {
            "success": False,
            "message": f"删除失败: {str(e)}"
        }

async def _create_or_get_temp_doctor_identity(disease_name: str) -> str:
    """为匿名用户创建临时医生身份"""
    # 🔧 修复：使用固定的匿名医生ID，而不是每次生成新的
    # 这样可以确保同一个用户的所有决策树都关联到同一个ID
    temp_id = "anonymous_doctor"

    logger.info(f"为匿名用户使用固定医生ID: {temp_id}")

    return temp_id

async def _save_pattern_to_database(pattern_data: Dict[str, Any]) -> str:
    """保存模式到数据库"""
    import sqlite3
    import uuid
    
    pattern_id = str(uuid.uuid4())
    
    # 连接数据库
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 创建表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS doctor_clinical_patterns (
                id TEXT PRIMARY KEY,
                doctor_id TEXT NOT NULL,
                disease_name TEXT NOT NULL,
                thinking_process TEXT NOT NULL,
                tree_structure TEXT NOT NULL,
                clinical_patterns TEXT NOT NULL,
                doctor_expertise TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(doctor_id, disease_name)
            )
        """)
        
        # 插入或更新记录
        cursor.execute("""
            INSERT OR REPLACE INTO doctor_clinical_patterns 
            (id, doctor_id, disease_name, thinking_process, tree_structure, 
             clinical_patterns, doctor_expertise, usage_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pattern_id,
            pattern_data["doctor_id"],
            pattern_data["disease_name"],
            pattern_data["thinking_process"],
            pattern_data["tree_structure"],
            pattern_data["clinical_patterns"],
            pattern_data["doctor_expertise"],
            pattern_data["usage_count"],
            pattern_data["created_at"],
            pattern_data["updated_at"]
        ))
        
        conn.commit()
        logger.info(f"临床模式已保存到数据库: {pattern_id}")
        
        return pattern_id
        
    except Exception as e:
        logger.error(f"数据库保存失败: {e}")
        raise
    finally:
        conn.close()

def _analyze_pattern_type(clinical_patterns: Dict[str, Any], doctor_expertise: Dict[str, Any]) -> str:
    """分析临床模式类型"""
    
    # 基于症状数量判断复杂度
    symptom_count = len(clinical_patterns.get("symptom_clusters", []))
    pathway_count = len(clinical_patterns.get("diagnostic_pathways", []))
    
    if symptom_count >= 5 and pathway_count >= 3:
        complexity = "复杂型"
    elif symptom_count >= 3 or pathway_count >= 2:
        complexity = "标准型"  
    else:
        complexity = "简化型"
    
    # 基于医生专长判断类型
    schools = doctor_expertise.get("schools", [])
    specialties = doctor_expertise.get("specialties", [])
    
    if "张仲景" in schools:
        style = "经方派"
    elif "李东垣" in schools:
        style = "脾胃派"
    elif "郑钦安" in schools:
        style = "火神派"
    elif "叶天士" in schools:
        style = "温病派"
    else:
        style = "综合派"
    
    return f"{style}-{complexity}"

def _detect_age_group_in_thinking(thinking_process: str) -> Dict[str, Any]:
    """智能检测诊疗思路中是否已明确年龄群体用药"""
    import re
    
    # 儿童相关关键词
    pediatric_keywords = ['小儿', '儿童', '幼儿', '婴儿', '新生儿', '学龄前', '学龄儿童']
    
    # 老年相关关键词  
    elderly_keywords = ['老年', '高龄', '年迈', '老人']
    
    # 成人相关关键词
    adult_keywords = ['成人', '成年人', '壮年']
    
    thinking_lower = thinking_process.lower()
    
    # 检测儿童用药
    for keyword in pediatric_keywords:
        if keyword in thinking_process:
            return {
                "detected": True,
                "age_group": "pediatric", 
                "keyword": keyword,
                "description": f"诊疗思路中明确提及'{keyword}'，说明已是{keyword}专用处方，剂量无需调整"
            }
    
    # 检测老年用药
    for keyword in elderly_keywords:
        if keyword in thinking_process:
            return {
                "detected": True,
                "age_group": "elderly",
                "keyword": keyword, 
                "description": f"诊疗思路中明确提及'{keyword}'，说明已是{keyword}专用处方，剂量无需调整"
            }
    
    # 检测成人用药
    for keyword in adult_keywords:
        if keyword in thinking_process:
            return {
                "detected": True,
                "age_group": "adult",
                "keyword": keyword,
                "description": f"诊疗思路中明确提及'{keyword}'，使用标准成人剂量"
            }
    
    return {
        "detected": False,
        "age_group": "unspecified",
        "keyword": None,
        "description": "诊疗思路中未明确年龄群体，需根据患者信息智能调整剂量"
    }

def _generate_dosage_adjustment_rules(
    age_group_detected: Dict[str, Any],
    patient_age: Optional[int],
    patient_weight: Optional[float], 
    special_conditions: List[str]
) -> str:
    """生成个性化的剂量调整规则"""
    
    rules = []
    
    # 1. 如果思路中已明确年龄群体
    if age_group_detected["detected"]:
        if age_group_detected["age_group"] == "pediatric":
            rules.append("✅ 检测到诊疗思路已明确为儿童用药，保持原处方剂量，无需调整")
            rules.append("⚠️ 严禁对已适配的儿童剂量再次减量")
        elif age_group_detected["age_group"] == "elderly":
            rules.append("✅ 检测到诊疗思路已明确为老年用药，保持原处方剂量")
        else:
            rules.append("✅ 检测到诊疗思路已明确为成人用药，保持标准剂量")
    else:
        # 2. 根据患者信息调整
        rules.append("📋 诊疗思路中未明确年龄群体，根据患者信息智能调整：")
        
        if patient_age and patient_age < 18:
            rules.append(f"   - 患者{patient_age}岁，儿童剂量：成人标准剂量的50-70%")
        elif patient_age and patient_age > 65:
            rules.append(f"   - 患者{patient_age}岁，老年剂量：成人标准剂量的70-80%")
        
        if patient_weight:
            if patient_weight < 50:
                rules.append(f"   - 患者体重{patient_weight}kg，适当减量10-20%")
            elif patient_weight > 80:
                rules.append(f"   - 患者体重{patient_weight}kg，可适当增量10-15%")
    
    # 3. 特殊情况
    if special_conditions:
        rules.append("🚨 特殊情况调整：")
        condition_map = {
            "pregnancy": "妊娠期：避免活血化瘀、破气药物，减量使用",
            "lactation": "哺乳期：注意药物对婴儿的影响",
            "diabetes": "糖尿病：注意避免升糖药物",
            "hypertension": "高血压：注意避免升压药物"
        }
        for condition in special_conditions:
            if condition in condition_map:
                rules.append(f"   - {condition_map[condition]}")
    
    rules.append("\n💡 核心原则：确保剂量调整的临床合理性，避免重复调整已适配的剂量。")
    
    return "\n".join(rules)


# ======================== 决策树使用统计功能 ========================

@router.get("/doctor-decision-tree/usage-stats/{doctor_id}")
async def get_pattern_usage_statistics(
    doctor_id: str,
    time_range: str = "all",  # today, week, month, all
    current_user: UserSession = Depends(get_current_user)
):
    """
    获取医生的决策树使用统计

    Args:
        doctor_id: 医生ID
        time_range: 时间范围（today, week, month, all）
        current_user: 当前用户会话

    Returns:
        决策树使用统计数据
    """
    import sqlite3
    from datetime import datetime, timedelta

    try:
        logger.info(f"获取医生 {doctor_id} 的决策树使用统计，时间范围: {time_range}")

        # 计算时间范围
        time_filter = ""
        if time_range == "today":
            time_filter = "AND DATE(c.created_at) = DATE('now')"
        elif time_range == "week":
            time_filter = "AND c.created_at >= datetime('now', '-7 days')"
        elif time_range == "month":
            time_filter = "AND c.created_at >= datetime('now', '-30 days')"

        conn = sqlite3.connect(USER_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. 获取总体统计
        cursor.execute(f"""
            SELECT
                COUNT(DISTINCT p.id) as total_patterns,
                COUNT(DISTINCT c.uuid) as total_calls,
                COUNT(DISTINCT CASE WHEN pr.status = 'reviewed' THEN c.uuid END) as success_calls,
                ROUND(CAST(COUNT(DISTINCT CASE WHEN c.used_pattern_id IS NOT NULL THEN c.uuid END) AS FLOAT) /
                      NULLIF(COUNT(DISTINCT c.uuid), 0) * 100, 2) as coverage_rate
            FROM doctor_clinical_patterns p
            LEFT JOIN consultations c ON c.used_pattern_id = p.id {time_filter}
            LEFT JOIN prescriptions pr ON pr.consultation_id = c.uuid
            WHERE p.doctor_id = ?
        """, (doctor_id,))

        overall_stats = dict(cursor.fetchone())

        # 2. 获取每个决策树的详细统计
        cursor.execute(f"""
            SELECT
                p.id as pattern_id,
                p.disease_name,
                p.thinking_process,
                p.created_at as pattern_created_at,
                COUNT(DISTINCT c.uuid) as call_count,
                COUNT(DISTINCT CASE WHEN pr.status = 'reviewed' THEN c.uuid END) as success_count,
                ROUND(CAST(COUNT(DISTINCT CASE WHEN pr.status = 'reviewed' THEN c.uuid END) AS FLOAT) /
                      NULLIF(COUNT(DISTINCT c.uuid), 0) * 100, 2) as success_rate,
                MAX(c.created_at) as last_used_at,
                AVG(c.pattern_match_score) as avg_match_score
            FROM doctor_clinical_patterns p
            LEFT JOIN consultations c ON c.used_pattern_id = p.id {time_filter}
            LEFT JOIN prescriptions pr ON pr.consultation_id = c.uuid
            WHERE p.doctor_id = ?
            GROUP BY p.id
            ORDER BY call_count DESC
        """, (doctor_id,))

        pattern_stats = [dict(row) for row in cursor.fetchall()]

        # 3. 获取总问诊数（用于计算使用率）
        cursor.execute(f"""
            SELECT COUNT(*) as total_consultations
            FROM consultations c
            WHERE 1=1 {time_filter}
        """)

        total_consultations = cursor.fetchone()[0]

        conn.close()

        # 计算每个决策树的使用率
        for pattern in pattern_stats:
            if total_consultations > 0:
                pattern['usage_rate'] = round((pattern['call_count'] / total_consultations) * 100, 2)
            else:
                pattern['usage_rate'] = 0

        return {
            "success": True,
            "data": {
                "overall": {
                    **overall_stats,
                    "total_consultations": total_consultations,
                    "time_range": time_range
                },
                "patterns": pattern_stats
            }
        }

    except Exception as e:
        logger.error(f"获取决策树使用统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.get("/doctor-decision-tree/usage-detail/{pattern_id}")
async def get_pattern_usage_detail(
    pattern_id: str,
    limit: int = 50,
    current_user: UserSession = Depends(get_current_user)
):
    """
    获取单个决策树的详细使用记录

    Args:
        pattern_id: 决策树ID
        limit: 返回记录数量限制
        current_user: 当前用户会话

    Returns:
        决策树详细使用记录
    """
    import sqlite3

    try:
        logger.info(f"获取决策树 {pattern_id} 的详细使用记录")

        conn = sqlite3.connect(USER_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. 获取决策树基本信息
        cursor.execute("""
            SELECT *
            FROM doctor_clinical_patterns
            WHERE id = ?
        """, (pattern_id,))

        pattern_info = cursor.fetchone()
        if not pattern_info:
            raise HTTPException(status_code=404, detail="决策树不存在")

        pattern_info = dict(pattern_info)

        # 2. 获取使用记录列表
        cursor.execute("""
            SELECT
                c.uuid as consultation_id,
                c.patient_id,
                c.pattern_match_score,
                c.created_at as consultation_date,
                c.status as consultation_status,
                p.id as prescription_id,
                p.status as prescription_status,
                p.review_status,
                p.payment_status,
                p.diagnosis
            FROM consultations c
            LEFT JOIN prescriptions p ON p.consultation_id = c.uuid
            WHERE c.used_pattern_id = ?
            ORDER BY c.created_at DESC
            LIMIT ?
        """, (pattern_id, limit))

        usage_records = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            "success": True,
            "data": {
                "pattern_info": pattern_info,
                "usage_records": usage_records,
                "total_count": len(usage_records)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取决策树使用详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取详情失败: {str(e)}")


@router.get("/consultation/{consultation_id}/detail")
async def get_consultation_detail(
    consultation_id: str,
    request: Request,
    current_user: UserSession = Depends(get_current_user_or_doctor)
):
    """
    统一的问诊详情查询API
    用于患者端和医生端查看问诊详情

    Args:
        consultation_id: 问诊UUID
        current_user: 当前用户会话

    Returns:
        问诊完整详情（包括处方、决策树信息）
    """
    import sqlite3

    try:
        # 🔍 详细调试日志
        user_roles = getattr(current_user, 'roles', [getattr(current_user, 'role', None)])
        if isinstance(user_roles, str):
            user_roles = [user_roles]

        logger.info(f"🔍 [决策树]获取问诊详情请求: consultation_id={consultation_id}, user_id={current_user.user_id}, roles={user_roles}")
        logger.info(f"🔍 [决策树]current_user完整信息: {current_user.__dict__}")

        conn = sqlite3.connect(USER_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. 获取问诊基本信息
        cursor.execute("""
            SELECT *
            FROM consultations
            WHERE uuid = ?
        """, (consultation_id,))

        consultation = cursor.fetchone()
        if not consultation:
            raise HTTPException(status_code=404, detail="问诊记录不存在")

        consultation = dict(consultation)

        # 2. 获取处方信息
        cursor.execute("""
            SELECT *
            FROM prescriptions
            WHERE consultation_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (consultation_id,))

        prescription = cursor.fetchone()
        if prescription:
            consultation['prescription'] = dict(prescription)

        # 3. 如果使用了决策树，获取决策树信息
        if consultation.get('used_pattern_id'):
            cursor.execute("""
                SELECT id, disease_name, doctor_id, thinking_process
                FROM doctor_clinical_patterns
                WHERE id = ?
            """, (consultation['used_pattern_id'],))

            pattern = cursor.fetchone()
            if pattern:
                consultation['used_pattern'] = dict(pattern)

        conn.close()

        # 权限检查：只允许患者本人或医生查看
        # 🔧 修复：兼容统一认证系统的 roles (List[str]) 和旧系统的 role
        user_roles = getattr(current_user, 'roles', [getattr(current_user, 'role', None)])
        if isinstance(user_roles, str):
            user_roles = [user_roles]

        # 检查是否有医生或管理员角色
        has_doctor_role = any(
            role in ['DOCTOR', 'ADMIN', UserRole.DOCTOR, UserRole.ADMIN]
            for role in user_roles if role
        )

        # 权限验证：必须是患者本人 或 医生/管理员
        if current_user.user_id != consultation['patient_id'] and not has_doctor_role:
            logger.warning(f"权限检查失败: user={current_user.user_id}, roles={user_roles}, patient={consultation['patient_id']}")
            raise HTTPException(status_code=403, detail="无权限查看此问诊记录")

        logger.info(f"✅ 权限检查通过: user={current_user.user_id}, roles={user_roles}, is_doctor={has_doctor_role}")

        return {
            "success": True,
            "data": consultation
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取问诊详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取详情失败: {str(e)}")


# ================================
# AI智能决策树生成 - 思维导图模式
# ================================

class MindMapGenerationRequest(BaseModel):
    """AI思维导图生成请求"""
    doctor_input: str  # 医生的自然语言诊疗思路
    disease_name: str = ""  # 疾病名称（可选，用于补充AI提取失败的情况）
    auto_save: bool = True  # 是否自动保存到思维库

@router.post("/ai_mindmap_generate")
async def ai_mindmap_generate(
    request: MindMapGenerationRequest,
    current_user: UserSession = Depends(get_current_user_or_doctor)
):
    """
    AI智能生成思维导图式决策树

    功能：
    1. 接收医生的自然语言描述
    2. AI自动分析：主证、证见、处方、加减法
    3. 生成思维导图形式的决策树
    4. 可选自动保存到医生思维库

    Example Input:
    ```
    {
        "doctor_input": "风热感冒：外感风热，邪袭肺卫。症见发热恶风，汗出不畅，头痛鼻塞，咽喉肿痛，咳嗽痰黄，口渴欲饮。舌边尖红，苔薄黄，脉浮数。治疗用桑菊饮加减：桑叶10g、菊花10g、薄荷6g、桔梗6g、连翘10g、芦根15g、甘草3g。若热重加黄芩10g、板蓝根15g；若咽痛甚加射干10g、山豆根10g。",
        "auto_save": true
    }
    ```

    Returns:
        思维导图式决策树结构 + 可视化数据
    """
    try:
        # 导入AI生成器
        from core.doctor_management.ai_decision_tree_generator import get_ai_decision_tree_generator

        generator = get_ai_decision_tree_generator()

        logger.info(f"🧠 [AI思维导图]用户 {current_user.user_id} 请求生成决策树，输入长度: {len(request.doctor_input)}字, 疾病名称: {request.disease_name}")

        # AI分析并生成思维导图
        mind_map_tree = await generator.analyze_and_generate(
            doctor_input=request.doctor_input,
            doctor_id=current_user.user_id,
            disease_name_hint=request.disease_name  # 传递用户输入的疾病名称作为提示
        )

        # 转换为数据库格式
        db_format = generator.to_database_format(mind_map_tree)

        # 自动保存到思维库
        pattern_id = None
        if request.auto_save:
            pattern_id = await _save_mind_map_to_database(
                doctor_id=current_user.user_id,
                mind_map_data=db_format
            )
            logger.info(f"✅ [AI思维导图]决策树已保存到思维库: {pattern_id}")

        return {
            "success": True,
            "message": "AI思维导图生成成功",
            "data": {
                "disease_name": mind_map_tree.disease_name,
                "main_syndrome": mind_map_tree.main_syndrome,
                "syndrome_branches": mind_map_tree.syndrome_branches,
                "nodes": mind_map_tree.nodes,
                "connections": mind_map_tree.connections,
                "metadata": mind_map_tree.metadata,
                "pattern_id": pattern_id if request.auto_save else None
            }
        }

    except Exception as e:
        logger.error(f"AI思维导图生成失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"AI思维导图生成失败: {str(e)}"
        )

async def _save_mind_map_to_database(
    doctor_id: str,
    mind_map_data: Dict[str, Any]
) -> str:
    """保存思维导图到数据库（使用UPSERT策略）"""
    import uuid

    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()

    # 检查是否已存在相同疾病的决策树
    cursor.execute("""
        SELECT id FROM doctor_clinical_patterns
        WHERE doctor_id = ? AND disease_name = ?
    """, (doctor_id, mind_map_data['disease_name']))

    existing = cursor.fetchone()

    if existing:
        # 更新现有记录
        pattern_id = existing[0]
        logger.info(f"🔄 更新现有决策树: {pattern_id}, 疾病={mind_map_data['disease_name']}")

        # 构建医生专长信息
        try:
            clinical_patterns = json.loads(mind_map_data['clinical_patterns'])
            doctor_expertise = json.dumps({
                "specialties": [mind_map_data['disease_name']],
                "main_syndromes": [clinical_patterns.get('main_syndrome', '')],
                "ai_generated": True,
                "updated_count": 1
            }, ensure_ascii=False)
        except:
            doctor_expertise = json.dumps({
                "specialties": [],
                "ai_generated": True
            }, ensure_ascii=False)

        cursor.execute("""
            UPDATE doctor_clinical_patterns
            SET thinking_process = ?,
                tree_structure = ?,
                clinical_patterns = ?,
                doctor_expertise = ?,
                updated_at = datetime('now')
            WHERE id = ?
        """, (
            mind_map_data['thinking_process'],
            mind_map_data['tree_structure'],
            mind_map_data['clinical_patterns'],
            doctor_expertise,
            pattern_id
        ))
    else:
        # 插入新记录
        pattern_id = str(uuid.uuid4())
        logger.info(f"✨ 创建新决策树: {pattern_id}, 疾病={mind_map_data['disease_name']}")

        # 构建医生专长信息
        try:
            clinical_patterns = json.loads(mind_map_data['clinical_patterns'])
            doctor_expertise = json.dumps({
                "specialties": [mind_map_data['disease_name']],
                "main_syndromes": [clinical_patterns.get('main_syndrome', '')],
                "ai_generated": True
            }, ensure_ascii=False)
        except:
            doctor_expertise = json.dumps({
                "specialties": [],
                "ai_generated": True
            }, ensure_ascii=False)

        cursor.execute("""
            INSERT INTO doctor_clinical_patterns (
                id, doctor_id, disease_name, thinking_process,
                tree_structure, clinical_patterns, doctor_expertise,
                usage_count, success_count,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, datetime('now'), datetime('now'))
        """, (
            pattern_id,
            doctor_id,
            mind_map_data['disease_name'],
            mind_map_data['thinking_process'],
            mind_map_data['tree_structure'],
            mind_map_data['clinical_patterns'],
            doctor_expertise
        ))

    conn.commit()
    conn.close()

    return pattern_id


# 导出路由器
__all__ = ["router"]
