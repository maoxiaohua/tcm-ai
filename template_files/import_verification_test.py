#!/usr/bin/env python3
"""
导入路径验证测试脚本
验证重组后的所有模块是否能正常导入
"""

import sys
import traceback

# 添加项目路径
sys.path.insert(0, '/opt/tcm-ai')

def test_imports():
    """测试所有关键模块导入"""
    test_results = []
    
    # 配置系统测试
    try:
        from config.settings import PATHS, API_CONFIG, DATABASE_CONFIG
        test_results.append(("✅", "配置系统", "成功"))
        print(f"项目根目录: {PATHS['project_root']}")
    except Exception as e:
        test_results.append(("❌", "配置系统", str(e)))
    
    # 核心模块测试
    core_modules = [
        ("缓存系统", "core.cache_system.intelligent_cache_system", "IntelligentCacheSystem"),
        ("知识检索", "core.knowledge_retrieval.enhanced_retrieval", "EnhancedKnowledgeRetrieval"),
        ("查询意图识别", "core.knowledge_retrieval.query_intent_recognition", "QueryIntentRecognizer"),
        ("医生流派", "core.doctor_system.tcm_doctor_personas", "PersonalizedTreatmentGenerator"),
        ("医生思维", "core.doctor_system.doctor_mind_integration", "DoctorMindAPI"),
        ("处方分析", "core.prescription.intelligent_prescription_analyzer", "ChineseMedicineDatabase"),
        ("方剂分析", "core.prescription.tcm_formula_analyzer", "TCMFormulaAnalyzer"),
    ]
    
    for name, module, class_name in core_modules:
        try:
            module_obj = __import__(module, fromlist=[class_name])
            getattr(module_obj, class_name)
            test_results.append(("✅", f"核心模块-{name}", "成功"))
        except Exception as e:
            test_results.append(("❌", f"核心模块-{name}", str(e)))
    
    # 服务模块测试
    service_modules = [
        ("用户历史", "services.user_history_system", "UserHistorySystem"),
        ("个性化学习", "services.personalized_learning", "PersonalizedLearningSystem"),
        ("医疗诊断控制", "services.medical_diagnosis_controller", "medical_diagnosis_controller"),
        ("多模态处理", "services.multimodal_processor", "analyze_prescription_image_bytes"),
        ("名医学习", "services.famous_doctor_learning_system", "FamousDoctorLearningSystem"),
    ]
    
    for name, module, item in service_modules:
        try:
            module_obj = __import__(module, fromlist=[item])
            getattr(module_obj, item)
            test_results.append(("✅", f"服务模块-{name}", "成功"))
        except Exception as e:
            test_results.append(("❌", f"服务模块-{name}", str(e)))
    
    # 数据库模块测试
    db_modules = [
        ("PostgreSQL接口", "database.postgresql_knowledge_interface", "get_hybrid_knowledge_system"),
        ("连接池", "database.database_connection_pool", "DatabaseConnectionPool"),
        ("备份系统", "database.database_backup_system", "PostgreSQLBackupSystem"),
    ]
    
    for name, module, item in db_modules:
        try:
            module_obj = __import__(module, fromlist=[item])
            getattr(module_obj, item)
            test_results.append(("✅", f"数据库模块-{name}", "成功"))
        except Exception as e:
            test_results.append(("❌", f"数据库模块-{name}", str(e)))
    
    return test_results

def main():
    print("=" * 60)
    print("🔍 TCM AI系统 - 导入路径验证测试")
    print("=" * 60)
    
    results = test_imports()
    
    # 统计结果
    success_count = sum(1 for status, _, _ in results if status == "✅")
    total_count = len(results)
    
    print(f"\n📊 测试结果统计:")
    print(f"总测试项: {total_count}")
    print(f"成功项目: {success_count}")
    print(f"失败项目: {total_count - success_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    
    print(f"\n📋 详细测试结果:")
    for status, module, result in results:
        if result == "成功":
            print(f"{status} {module}: {result}")
        else:
            print(f"{status} {module}: {result[:80]}...")
    
    if success_count == total_count:
        print(f"\n🎉 所有模块导入验证成功！重组完全成功！")
        return True
    else:
        print(f"\n⚠️ 还有 {total_count - success_count} 个模块需要修复")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)