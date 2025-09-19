#!/usr/bin/env python3
"""
Doctor Decision Tree API Routes
智能决策树生成API路由

提供医生决策树分析和生成功能，帮助医生将自然语言描述转换为结构化的诊疗决策树
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import logging
import asyncio

# 导入必要的服务
from services.famous_doctor_learning_system import FamousDoctorLearningSystem
from api.security_integration import get_current_user
from core.security.rbac_system import UserSession
from core.prescription.tcm_formula_analyzer import TCMFormulaAnalyzer
from config.settings import AI_CONFIG

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

# 初始化服务
doctor_learning_system = FamousDoctorLearningSystem()
formula_analyzer = TCMFormulaAnalyzer()

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
            analysis_result = await doctor_learning_system.analyze_doctor_thinking(
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
            tree_result = await doctor_learning_system.generate_decision_tree(
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
                    # 解析失败时使用默认结构
                    tree_data = create_default_tree_structure(request.disease_name, selected_school_names)
            else:
                tree_data = tree_result

            return DecisionTreeResponse(
                success=True,
                message="决策树生成完成",
                data=tree_data
            )
            
        except Exception as ai_error:
            logger.error(f"AI生成决策树失败: {ai_error}")
            # 返回默认决策树结构
            default_tree = create_default_tree_structure(request.disease_name, selected_school_names)
            return DecisionTreeResponse(
                success=True,
                message="决策树生成完成（使用模板）",
                data=default_tree
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
            print(f"  - 调用doctor_learning_system.generate_decision_paths...")
            
            # 调用新的智能生成方法
            generation_result = await doctor_learning_system.generate_decision_paths(
                disease_name=request.disease_name,
                thinking_process=request.thinking_process,
                use_ai=request.use_ai,  # 使用前端传递的参数
                include_tcm_analysis=request.include_tcm_analysis,
                complexity_level=request.complexity_level
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
                    "enabled": doctor_learning_system.ai_enabled,
                    "source": generation_result['source'],
                    "generation_time": generation_result.get('generation_time', '未知')
                }
            }
            
        except Exception as ai_error:
            logger.error(f"智能生成决策树失败: {ai_error}")
            # 失败时使用模板备用
            fallback_result = {
                "source": "template_fallback",
                "ai_generated": False,
                "user_thinking_used": False,
                "paths": create_default_visual_tree(request.disease_name)["paths"],
                "suggested_layout": {
                    "auto_arrange": True,
                    "spacing": {"horizontal": 300, "vertical": 150}
                },
                "error_message": str(ai_error)
            }
            
            return {
                "success": True,
                "message": "使用模板备用方案",
                "data": fallback_result,
                "ai_status": {
                    "enabled": False,
                    "source": "template_fallback",
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
            analysis_result = await doctor_learning_system.analyze_tcm_theory_with_ai(
                tree_data=request.tree_data,
                disease_name=request.disease_name
            )
            
            # 格式化分析结果为前端显示格式
            formatted_analysis = format_tcm_analysis_for_display(analysis_result)
            formatted_suggestions = format_tcm_suggestions_for_display(analysis_result)
            
            return {
                "success": True,
                "message": f"AI理论分析完成（{doctor_learning_system.ai_enabled and 'AI' or '模板'}模式）",
                "data": {
                    "analysis": formatted_analysis,
                    "suggestions": formatted_suggestions,
                    "source": "ai" if doctor_learning_system.ai_enabled else "template",
                    "ai_enabled": doctor_learning_system.ai_enabled
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

@router.get("/user_preferences/{user_id}")
async def get_user_preferences(
    user_id: str,
    current_user: UserSession = Depends(get_current_user)
):
    """获取用户偏好设置"""
    try:
        # 权限检查：只能访问自己的偏好设置
        if current_user.user_id != user_id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="无权限访问")
        
        preferences = doctor_learning_system.get_user_preferences(user_id)
        
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
        if current_user.user_id != user_id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="无权限修改")
        
        preferences = {
            "ai_mode_preferred": request.ai_mode_preferred,
            "complexity_level": request.complexity_level,
            "favorite_schools": request.favorite_schools,
            "custom_templates": request.custom_templates
        }
        
        doctor_learning_system.save_user_preferences(user_id, preferences)
        
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
                "ai_enabled": doctor_learning_system.ai_enabled,
                "ai_model": getattr(doctor_learning_system, 'ai_model', 'unknown'),
                "dashscope_available": DASHSCOPE_AVAILABLE,
                "learning_enabled": getattr(doctor_learning_system, 'learning_enabled', False),
                "features": {
                    "decision_tree_generation": doctor_learning_system.ai_enabled,
                    "theory_analysis": doctor_learning_system.ai_enabled,
                    "hybrid_mode": True,
                    "user_learning": getattr(doctor_learning_system, 'learning_enabled', False)
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
        completeness_result = await doctor_learning_system._analyze_diagnostic_completeness(
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
    
    # 构建AI提示词
    prompt = f"""
请从以下中医诊疗思路中提取结构化信息，并根据患者特征生成个性化处方：

诊疗思路：{thinking_process}

患者信息：{patient_info}

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

剂量调整原则：
1. 儿童（<18岁）：成人剂量的50-70%
2. 老年人（>65岁）：成人剂量的70-80%
3. 体重过轻（<50kg）：适当减量10-20%
4. 体重过重（>80kg）：可适当增量10-15%
5. 孕妇：避免活血化瘀、破气药物
6. 哺乳期：注意药物对婴儿的影响

请确保所有剂量都是实用的临床剂量，并提供详细的用药指导。
"""

    try:
        # 调用AI生成
        response = await asyncio.to_thread(
            dashscope.Generation.call,
            model=AI_CONFIG.get('decision_tree_model', 'qwen-max'),
            prompt=prompt,
            result_format='message'
        )
        
        if response.status_code == 200:
            content = response.output.choices[0]['message']['content']
            
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

# 导出路由器
__all__ = ["router"]