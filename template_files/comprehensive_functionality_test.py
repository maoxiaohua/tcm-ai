#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI中医诊断助手综合功能测试脚本
专业的软件开发、项目管理、产品管理视角的全面功能验证
"""

import sys
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any

# 添加项目路径
sys.path.insert(0, '/opt/tcm-ai')

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveFunctionalityTester:
    """AI中医诊断助手综合功能测试器"""
    
    def __init__(self):
        self.test_results = {
            'core_modules': {},
            'database_systems': {},
            'medical_safety': {},
            'user_interaction': {},
            'diagnostic_flow': {},
            'knowledge_retrieval': {},
            'prescription_system': {},
            'cache_system': {},
            'errors': []
        }
    
    def test_module_imports(self):
        """测试核心模块导入完整性"""
        print("🔍 测试1: 核心模块导入完整性")
        print("=" * 60)
        
        critical_modules = [
            ('config.settings', '配置系统'),
            ('database.postgresql_knowledge_interface', 'PostgreSQL接口'),
            ('core.cache_system.intelligent_cache_system', '智能缓存系统'),
            ('core.doctor_system.tcm_doctor_personas', '中医医生人格系统'),
            ('services.medical_diagnosis_controller', '诊断流程控制器'),
            ('services.user_history_system', '用户历史系统'),
            ('core.prescription.prescription_checker', '处方检查系统'),
            ('core.knowledge_retrieval.enhanced_retrieval', '知识检索增强'),
        ]
        
        for module_name, description in critical_modules:
            try:
                __import__(module_name)
                self.test_results['core_modules'][module_name] = {
                    'status': 'SUCCESS',
                    'description': description
                }
                print(f"✅ {description}: 导入成功")
            except Exception as e:
                self.test_results['core_modules'][module_name] = {
                    'status': 'FAILED',
                    'description': description,
                    'error': str(e)
                }
                print(f"❌ {description}: 导入失败 - {e}")
                self.test_results['errors'].append(f"模块导入失败: {module_name} - {e}")
    
    def test_database_connectivity(self):
        """测试数据库连接和功能"""
        print("\n🔍 测试2: 数据库连接和功能")
        print("=" * 60)
        
        # 测试PostgreSQL连接
        try:
            from database.postgresql_knowledge_interface import PostgreSQLKnowledgeInterface
            pg_interface = PostgreSQLKnowledgeInterface()
            
            if pg_interface.is_available():
                self.test_results['database_systems']['postgresql'] = {
                    'status': 'SUCCESS',
                    'connection': 'ACTIVE'
                }
                print("✅ PostgreSQL数据库: 连接成功")
                
                # 测试向量搜索能力
                try:
                    # 这里应该会失败，因为向量扩展未安装
                    test_embedding = [0.1] * 768
                    results = pg_interface.search_doctor_specific_knowledge(
                        "测试查询", "zhang_zhongjing", test_embedding, 1
                    )
                    self.test_results['database_systems']['vector_search'] = {
                        'status': 'SUCCESS' if results else 'WARNING',
                        'message': f'返回{len(results)}条结果'
                    }
                    print(f"⚠️  向量搜索: 功能可用但可能降级到全文搜索")
                except Exception as ve:
                    self.test_results['database_systems']['vector_search'] = {
                        'status': 'DEGRADED',
                        'error': str(ve),
                        'fallback': 'FULLTEXT_SEARCH'
                    }
                    print(f"⚠️  向量搜索: 已降级到全文搜索 - {ve}")
            else:
                self.test_results['database_systems']['postgresql'] = {
                    'status': 'FAILED',
                    'connection': 'INACTIVE'
                }
                print("❌ PostgreSQL数据库: 连接失败")
                self.test_results['errors'].append("PostgreSQL数据库连接失败")
                
        except Exception as e:
            self.test_results['database_systems']['postgresql'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"❌ PostgreSQL接口: 初始化失败 - {e}")
            self.test_results['errors'].append(f"PostgreSQL接口初始化失败: {e}")
        
        # 测试SQLite数据库
        sqlite_files = [
            '/opt/tcm-ai/data/cache.sqlite',
            '/opt/tcm-ai/data/user_history.sqlite',
            '/opt/tcm-ai/data/learning_db.sqlite'
        ]
        
        for db_file in sqlite_files:
            if os.path.exists(db_file):
                self.test_results['database_systems'][f'sqlite_{os.path.basename(db_file)}'] = {
                    'status': 'SUCCESS',
                    'file_exists': True,
                    'size_kb': os.path.getsize(db_file) // 1024
                }
                print(f"✅ SQLite数据库 ({os.path.basename(db_file)}): 文件存在, 大小{os.path.getsize(db_file)//1024}KB")
            else:
                print(f"⚠️  SQLite数据库 ({os.path.basename(db_file)}): 文件不存在")
    
    def test_medical_safety_mechanisms(self):
        """测试医疗安全机制"""
        print("\n🔍 测试3: 医疗安全机制")
        print("=" * 60)
        
        try:
            from services.medical_diagnosis_controller import MedicalDiagnosisController
            controller = MedicalDiagnosisController()
            
            # 测试信息不足时拒绝开方
            insufficient_conversation = [
                {"role": "user", "content": "我头痛"},
                {"role": "user", "content": "请开个处方"}
            ]
            
            can_prescribe, reason = controller.can_prescribe(
                "test_safety", insufficient_conversation, "开处方"
            )
            
            if not can_prescribe:
                self.test_results['medical_safety']['prescription_safety'] = {
                    'status': 'SUCCESS',
                    'correctly_refused': True,
                    'reason': reason
                }
                print("✅ 处方安全控制: 正确拒绝信息不足的开方请求")
            else:
                self.test_results['medical_safety']['prescription_safety'] = {
                    'status': 'FAILED',
                    'incorrectly_allowed': True,
                    'reason': reason
                }
                print("❌ 处方安全控制: 错误允许信息不足的开方请求")
                self.test_results['errors'].append("医疗安全机制失效：信息不足仍允许开方")
            
            # 测试完整信息时允许开方
            complete_conversation = [
                {"role": "user", "content": "我头痛3天了，太阳穴胀痛"},
                {"role": "user", "content": "伴随恶心，怕光怕声"},
                {"role": "user", "content": "舌质红，苔薄白"},
                {"role": "user", "content": "脉弦数"},
                {"role": "user", "content": "睡眠不好，食欲减退"},
                {"role": "user", "content": "大便偏干，小便黄"},
                {"role": "user", "content": "情绪焦虑，压力大"},
                {"role": "user", "content": "请开具处方"}
            ]
            
            can_prescribe_complete, reason_complete = controller.can_prescribe(
                "test_complete", complete_conversation, "开处方"
            )
            
            if can_prescribe_complete:
                self.test_results['medical_safety']['complete_info_prescription'] = {
                    'status': 'SUCCESS',
                    'correctly_allowed': True,
                    'reason': reason_complete
                }
                print("✅ 完整信息开方: 正确允许信息完整的开方请求")
            else:
                self.test_results['medical_safety']['complete_info_prescription'] = {
                    'status': 'WARNING',
                    'reason': reason_complete
                }
                print(f"⚠️  完整信息开方: 仍然拒绝开方 - {reason_complete}")
            
        except Exception as e:
            self.test_results['medical_safety']['controller'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"❌ 医疗安全控制器: 测试失败 - {e}")
            self.test_results['errors'].append(f"医疗安全控制器测试失败: {e}")
    
    def test_diagnostic_flow(self):
        """测试诊断流程"""
        print("\n🔍 测试4: 诊断流程完整性")
        print("=" * 60)
        
        # 检查是否存在关键的诊断流程文件
        diagnostic_files = [
            '/opt/tcm-ai/services/medical_diagnosis_controller.py',
            '/opt/tcm-ai/core/doctor_system/tcm_doctor_personas.py',
            '/opt/tcm-ai/core/doctor_system/zhang_zhongjing_decision_system.py'
        ]
        
        missing_files = []
        for file_path in diagnostic_files:
            if os.path.exists(file_path):
                self.test_results['diagnostic_flow'][os.path.basename(file_path)] = {
                    'status': 'SUCCESS',
                    'file_exists': True,
                    'size_kb': os.path.getsize(file_path) // 1024
                }
                print(f"✅ 诊断文件 {os.path.basename(file_path)}: 存在 ({os.path.getsize(file_path)//1024}KB)")
            else:
                missing_files.append(file_path)
                print(f"❌ 诊断文件 {os.path.basename(file_path)}: 不存在")
        
        if missing_files:
            self.test_results['errors'].extend([f"缺失诊断流程文件: {f}" for f in missing_files])
        
        # 检查医生人格系统
        try:
            from core.doctor_system.tcm_doctor_personas import get_doctor_persona
            doctors = ['zhang_zhongjing', 'li_dongyuan', 'ye_tianshi']
            
            for doctor in doctors:
                persona = get_doctor_persona(doctor)
                if persona:
                    self.test_results['diagnostic_flow'][f'persona_{doctor}'] = {
                        'status': 'SUCCESS',
                        'has_persona': True
                    }
                    print(f"✅ 医生人格 {doctor}: 配置完整")
                else:
                    self.test_results['diagnostic_flow'][f'persona_{doctor}'] = {
                        'status': 'WARNING',
                        'has_persona': False
                    }
                    print(f"⚠️  医生人格 {doctor}: 配置缺失")
        
        except Exception as e:
            self.test_results['diagnostic_flow']['persona_system'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"❌ 医生人格系统: 测试失败 - {e}")
    
    def test_knowledge_retrieval(self):
        """测试知识检索系统"""
        print("\n🔍 测试5: 知识检索系统")
        print("=" * 60)
        
        # 检查FAISS索引文件
        faiss_files = [
            '/opt/tcm-ai/knowledge_db/knowledge.index',
            '/opt/tcm-ai/knowledge_db/documents.pkl',
            '/opt/tcm-ai/knowledge_db/metadata.pkl'
        ]
        
        faiss_status = True
        for file_path in faiss_files:
            if os.path.exists(file_path):
                print(f"✅ FAISS文件 {os.path.basename(file_path)}: 存在 ({os.path.getsize(file_path)//1024}KB)")
            else:
                print(f"❌ FAISS文件 {os.path.basename(file_path)}: 不存在")
                faiss_status = False
        
        self.test_results['knowledge_retrieval']['faiss_index'] = {
            'status': 'SUCCESS' if faiss_status else 'FAILED',
            'all_files_present': faiss_status
        }
        
        # 检查知识文档
        docs_path = '/opt/tcm-ai/all_tcm_docs'
        if os.path.exists(docs_path):
            doc_count = len([f for f in os.listdir(docs_path) if f.endswith('.docx') or f.endswith('.txt')])
            self.test_results['knowledge_retrieval']['knowledge_docs'] = {
                'status': 'SUCCESS',
                'doc_count': doc_count,
                'path_exists': True
            }
            print(f"✅ 知识文档库: {doc_count}个文档")
        else:
            self.test_results['knowledge_retrieval']['knowledge_docs'] = {
                'status': 'FAILED',
                'path_exists': False
            }
            print("❌ 知识文档库: 路径不存在")
    
    def test_prescription_system(self):
        """测试处方系统"""
        print("\n🔍 测试6: 处方系统")
        print("=" * 60)
        
        prescription_files = [
            '/opt/tcm-ai/core/prescription/prescription_checker.py',
            '/opt/tcm-ai/core/prescription/tcm_formula_analyzer.py',
            '/opt/tcm-ai/data/unified_herb_database.json'
        ]
        
        for file_path in prescription_files:
            if os.path.exists(file_path):
                self.test_results['prescription_system'][os.path.basename(file_path)] = {
                    'status': 'SUCCESS',
                    'file_exists': True,
                    'size_kb': os.path.getsize(file_path) // 1024
                }
                print(f"✅ 处方文件 {os.path.basename(file_path)}: 存在 ({os.path.getsize(file_path)//1024}KB)")
            else:
                self.test_results['prescription_system'][os.path.basename(file_path)] = {
                    'status': 'FAILED',
                    'file_exists': False
                }
                print(f"❌ 处方文件 {os.path.basename(file_path)}: 不存在")
                self.test_results['errors'].append(f"缺失处方系统文件: {file_path}")
    
    def test_cache_system(self):
        """测试缓存系统"""
        print("\n🔍 测试7: 缓存系统")
        print("=" * 60)
        
        try:
            from core.cache_system.intelligent_cache_system import IntelligentCacheSystem
            cache_system = IntelligentCacheSystem()
            
            # 测试缓存基本功能
            test_key = "test_functionality_check"
            test_data = {"test": "data", "timestamp": datetime.now().isoformat()}
            
            # 存储测试
            cache_system.store_response(test_key, test_data, "test_doctor")
            
            # 检索测试
            cached_data = cache_system.get_cached_response(test_key)
            
            if cached_data:
                self.test_results['cache_system']['basic_operations'] = {
                    'status': 'SUCCESS',
                    'store_retrieve': True
                }
                print("✅ 缓存基本操作: 存储和检索功能正常")
            else:
                self.test_results['cache_system']['basic_operations'] = {
                    'status': 'FAILED',
                    'store_retrieve': False
                }
                print("❌ 缓存基本操作: 存储或检索失败")
                self.test_results['errors'].append("缓存系统基本操作失败")
            
        except Exception as e:
            self.test_results['cache_system']['system'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"❌ 缓存系统: 测试失败 - {e}")
            self.test_results['errors'].append(f"缓存系统测试失败: {e}")
    
    def generate_comprehensive_report(self):
        """生成综合测试报告"""
        print("\n🔍 测试完成 - 生成综合报告")
        print("=" * 60)
        
        # 统计测试结果
        total_tests = sum(len(category) for category in self.test_results.values() if isinstance(category, dict))
        successful_tests = 0
        failed_tests = 0
        warning_tests = 0
        
        for category_name, category_data in self.test_results.items():
            if isinstance(category_data, dict):
                for test_name, test_result in category_data.items():
                    if isinstance(test_result, dict) and 'status' in test_result:
                        if test_result['status'] == 'SUCCESS':
                            successful_tests += 1
                        elif test_result['status'] == 'FAILED':
                            failed_tests += 1
                        else:
                            warning_tests += 1
        
        # 生成报告
        report = {
            'test_summary': {
                'total_tests': total_tests - len(self.test_results['errors']),  # 排除错误列表
                'successful_tests': successful_tests,
                'failed_tests': failed_tests,
                'warning_tests': warning_tests,
                'success_rate': round((successful_tests / (total_tests - len(self.test_results['errors']))) * 100, 2) if total_tests > 0 else 0
            },
            'critical_issues': self.test_results['errors'],
            'detailed_results': self.test_results,
            'timestamp': datetime.now().isoformat(),
            'recommendations': self.generate_recommendations()
        }
        
        # 保存报告
        report_file = '/opt/tcm-ai/template_files/functionality_test_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📊 测试统计:")
        print(f"   总测试项: {report['test_summary']['total_tests']}")
        print(f"   成功: {successful_tests} (✅)")
        print(f"   失败: {failed_tests} (❌)")
        print(f"   警告: {warning_tests} (⚠️)")
        print(f"   成功率: {report['test_summary']['success_rate']}%")
        
        if self.test_results['errors']:
            print(f"\n🚨 关键问题 ({len(self.test_results['errors'])}个):")
            for error in self.test_results['errors']:
                print(f"   • {error}")
        
        print(f"\n📄 详细报告已保存至: {report_file}")
        
        return report
    
    def generate_recommendations(self):
        """生成改进建议"""
        recommendations = []
        
        # 数据库相关建议
        if 'postgresql' in self.test_results['database_systems']:
            pg_result = self.test_results['database_systems']['postgresql']
            if pg_result.get('status') == 'FAILED':
                recommendations.append({
                    'category': 'Database',
                    'priority': 'High',
                    'issue': 'PostgreSQL连接失败',
                    'recommendation': '检查PostgreSQL服务状态，确认数据库配置和权限设置'
                })
        
        if 'vector_search' in self.test_results['database_systems']:
            vs_result = self.test_results['database_systems']['vector_search']
            if vs_result.get('status') in ['FAILED', 'DEGRADED']:
                recommendations.append({
                    'category': 'Database',
                    'priority': 'High',
                    'issue': 'PostgreSQL向量搜索功能缺失',
                    'recommendation': '安装pgvector扩展以启用向量搜索功能：CREATE EXTENSION vector;'
                })
        
        # 医疗安全相关建议
        if 'prescription_safety' in self.test_results['medical_safety']:
            safety_result = self.test_results['medical_safety']['prescription_safety']
            if safety_result.get('status') == 'FAILED':
                recommendations.append({
                    'category': 'Medical Safety',
                    'priority': 'Critical',
                    'issue': '医疗安全机制失效',
                    'recommendation': '立即检查和修复医疗安全控制逻辑，确保不会草率开具处方'
                })
        
        # 知识检索相关建议
        if 'faiss_index' in self.test_results['knowledge_retrieval']:
            faiss_result = self.test_results['knowledge_retrieval']['faiss_index']
            if faiss_result.get('status') == 'FAILED':
                recommendations.append({
                    'category': 'Knowledge Retrieval',
                    'priority': 'High',
                    'issue': 'FAISS索引文件缺失',
                    'recommendation': '重新构建FAISS向量索引，确保知识检索功能正常'
                })
        
        # 通用建议
        if len(self.test_results['errors']) > 5:
            recommendations.append({
                'category': 'General',
                'priority': 'High',
                'issue': '系统存在多个关键错误',
                'recommendation': '进行全面的系统检查和修复，优先解决数据库连接和医疗安全问题'
            })
        
        return recommendations
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始AI中医诊断助手综合功能测试")
        print("📋 测试目标: 验证系统各项功能的完整性和安全性")
        print("=" * 80)
        
        try:
            self.test_module_imports()
            self.test_database_connectivity()
            self.test_medical_safety_mechanisms()
            self.test_diagnostic_flow()
            self.test_knowledge_retrieval()
            self.test_prescription_system()
            self.test_cache_system()
            
            return self.generate_comprehensive_report()
            
        except Exception as e:
            logger.error(f"测试执行过程中发生严重错误: {e}")
            self.test_results['errors'].append(f"测试执行严重错误: {e}")
            return self.generate_comprehensive_report()

def main():
    """主函数"""
    tester = ComprehensiveFunctionalityTester()
    report = tester.run_all_tests()
    
    # 根据测试结果返回适当的退出码
    if report['test_summary']['failed_tests'] == 0 and len(report['critical_issues']) == 0:
        print("\n🎉 所有测试通过！系统功能完整。")
        return 0
    elif report['test_summary']['failed_tests'] > 0:
        print(f"\n⚠️  存在 {report['test_summary']['failed_tests']} 个失败测试项，需要关注。")
        return 1
    else:
        print(f"\n🚨 存在 {len(report['critical_issues'])} 个关键问题，需要立即处理。")
        return 2

if __name__ == "__main__":
    sys.exit(main())