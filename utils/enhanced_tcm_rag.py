#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的中医RAG系统
集成改进的文档处理和检索功能
"""

import os
import sys
import json
import pickle
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

# 添加项目路径
sys.path.append('/home/ute/tcm-ai')

from utils.tcm_document_processor import TCMDocumentProcessor
from core.knowledge_retrieval.enhanced_retrieval import EnhancedKnowledgeRetrieval

logger = logging.getLogger(__name__)

class EnhancedTCMRAG:
    """增强的中医RAG系统"""
    
    def __init__(self, knowledge_db_path: str = "/home/ute/tcm-ai/knowledge_db"):
        self.knowledge_db_path = knowledge_db_path
        self.documents_file = os.path.join(knowledge_db_path, "tcm_documents.pkl")
        self.metadata_file = os.path.join(knowledge_db_path, "tcm_metadata.pkl")
        
        # 初始化组件
        self.doc_processor = TCMDocumentProcessor()
        self.enhanced_retrieval = EnhancedKnowledgeRetrieval(knowledge_db_path)
        
        # 确保知识库目录存在
        os.makedirs(knowledge_db_path, exist_ok=True)
        
        # 加载已处理的文档
        self.documents = []
        self.metadata = []
        self.load_processed_documents()
        
    def load_processed_documents(self):
        """加载已处理的文档"""
        try:
            if os.path.exists(self.documents_file):
                with open(self.documents_file, 'rb') as f:
                    self.documents = pickle.load(f)
                    
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'rb') as f:
                    self.metadata = pickle.load(f)
                    
            logger.info(f"加载已处理文档: {len(self.documents)}个分块")
        except Exception as e:
            logger.error(f"加载文档失败: {e}")
            self.documents = []
            self.metadata = []
    
    def save_processed_documents(self):
        """保存处理后的文档"""
        try:
            with open(self.documents_file, 'wb') as f:
                pickle.dump(self.documents, f)
                
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(self.metadata, f)
                
            logger.info(f"保存文档成功: {len(self.documents)}个分块")
        except Exception as e:
            logger.error(f"保存文档失败: {e}")
    
    def process_docx_files(self, docx_files: List[str]) -> Dict[str, Any]:
        """处理docx文件并更新知识库"""
        processing_result = {
            'success': False,
            'processed_files': [],
            'total_chunks': 0,
            'failed_files': [],
            'stats': {}
        }
        
        try:
            new_documents = []
            new_metadata = []
            
            for docx_file in docx_files:
                logger.info(f"处理文件: {docx_file}")
                
                # 处理单个文档
                result = self.doc_processor.process_tcm_document(docx_file)
                
                if result['success']:
                    filename = result['filename']
                    chunks = result['chunks']
                    
                    # 添加分块到知识库
                    for i, chunk in enumerate(chunks):
                        # 文档内容
                        document_text = chunk['text']
                        new_documents.append(document_text)
                        
                        # 元数据
                        metadata = {
                            'source': filename,
                            'chunk_index': i,
                            'section_type': chunk['section_type'],
                            'char_count': chunk['char_count'],
                            'disease_category': self._extract_disease_category(filename),
                            'processing_timestamp': str(result.get('timestamp', ''))
                        }
                        new_metadata.append(metadata)
                    
                    processing_result['processed_files'].append({
                        'filename': filename,
                        'chunks_count': len(chunks),
                        'stats': result['stats']
                    })
                    
                    print(f"✅ {filename}: {len(chunks)}个分块")
                    
                else:
                    processing_result['failed_files'].append({
                        'filename': os.path.basename(docx_file),
                        'error': result['error_message']
                    })
                    print(f"❌ {os.path.basename(docx_file)}: {result['error_message']}")
            
            # 更新文档列表
            self.documents.extend(new_documents)
            self.metadata.extend(new_metadata)
            
            # 保存到文件
            self.save_processed_documents()
            
            processing_result.update({
                'success': True,
                'total_chunks': len(new_documents),
                'stats': {
                    'total_documents': len(self.documents),
                    'new_chunks': len(new_documents),
                    'avg_chunk_size': np.mean([len(doc) for doc in new_documents]) if new_documents else 0
                }
            })
            
        except Exception as e:
            processing_result['error'] = str(e)
            logger.error(f"处理文档失败: {e}")
            
        return processing_result
    
    def _extract_disease_category(self, filename: str) -> str:
        """从文件名提取疾病类别"""
        category_mapping = {
            '感冒': '外感疾病',
            '咳嗽': '呼吸系统',
            '高血压': '心血管系统', 
            '糖尿病': '内分泌系统',
            '月经失调': '妇科疾病',
            '小儿': '儿科疾病',
            '腰痛': '骨科疾病',
            '失眠': '神经精神科',
            '湿疹': '皮肤科',
            '消化': '消化系统'
        }
        
        for keyword, category in category_mapping.items():
            if keyword in filename:
                return category
        return '其他'
    
    def search_knowledge(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """搜索知识库"""
        search_result = {
            'success': False,
            'query': query,
            'results': [],
            'search_method': 'enhanced_hybrid',
            'total_candidates': len(self.documents)
        }
        
        try:
            if not self.documents:
                search_result['error'] = "知识库为空，请先处理文档"
                return search_result
            
            # 使用增强检索（如果可用）
            try:
                # 模拟向量嵌入（实际应用中应该使用真实的嵌入模型）
                query_embedding = self._generate_mock_embedding(query)
                
                # 混合检索
                enhanced_results = self.enhanced_retrieval.hybrid_search(
                    query=query,
                    query_embedding=query_embedding,
                    total_results=top_k
                )
                
                search_result['results'] = enhanced_results
                search_result['search_method'] = 'enhanced_hybrid'
                
            except Exception as e:
                logger.warning(f"增强检索失败，使用基础检索: {e}")
                # 回退到基础检索
                basic_results = self._basic_search(query, top_k)
                search_result['results'] = basic_results
                search_result['search_method'] = 'basic_fallback'
            
            search_result['success'] = True
            
        except Exception as e:
            search_result['error'] = str(e)
            logger.error(f"知识搜索失败: {e}")
            
        return search_result
    
    def _generate_mock_embedding(self, text: str) -> List[float]:
        """生成模拟嵌入向量（用于测试）"""
        # 基于文本hash生成固定维度的向量
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        # 转换为384维向量（常见的嵌入维度）
        vector = []
        for i in range(0, len(text_hash), 2):
            hex_val = text_hash[i:i+2]
            vector.append(int(hex_val, 16) / 255.0)
        
        # 填充到384维
        while len(vector) < 384:
            vector.extend(vector[:min(len(vector), 384-len(vector))])
        
        return vector[:384]
    
    def _basic_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """基础关键词搜索"""
        results = []
        query_lower = query.lower()
        
        for i, (doc, meta) in enumerate(zip(self.documents, self.metadata)):
            doc_lower = doc.lower()
            
            # 简单的关键词匹配评分
            score = 0.0
            for word in query_lower.split():
                if word in doc_lower:
                    score += doc_lower.count(word) / len(doc_lower.split())
            
            if score > 0:
                results.append({
                    'document': doc,
                    'metadata': meta,
                    'score': score,
                    'index': i
                })
        
        # 按评分排序
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
    
    def test_rag_system(self, test_queries: List[str]) -> Dict[str, Any]:
        """测试RAG系统效果"""
        test_result = {
            'success': False,
            'test_queries': test_queries,
            'results': [],
            'summary': {}
        }
        
        try:
            query_results = []
            
            for query in test_queries:
                print(f"\n🔍 测试查询: {query}")
                
                search_result = self.search_knowledge(query, top_k=3)
                
                if search_result['success']:
                    print(f"✅ 找到 {len(search_result['results'])} 个相关结果")
                    
                    # 显示前2个结果
                    for i, result in enumerate(search_result['results'][:2]):
                        score = result.get('hybrid_score', result.get('score', 0))
                        source = result['metadata'].get('source', 'unknown')
                        section = result['metadata'].get('section_type', 'other')
                        content = result['document'][:100]
                        
                        print(f"  结果{i+1} [评分:{score:.3f}] 来源:{source} 部分:{section}")
                        print(f"    内容: {content}...")
                else:
                    print(f"❌ 搜索失败: {search_result.get('error', 'unknown')}")
                
                query_results.append({
                    'query': query,
                    'search_result': search_result
                })
            
            test_result.update({
                'success': True,
                'results': query_results,
                'summary': {
                    'total_queries': len(test_queries),
                    'successful_queries': len([r for r in query_results if r['search_result']['success']]),
                    'avg_results_per_query': np.mean([len(r['search_result']['results']) for r in query_results])
                }
            })
            
        except Exception as e:
            test_result['error'] = str(e)
            logger.error(f"RAG测试失败: {e}")
            
        return test_result

def main():
    """主测试函数"""
    print("🚀 启动增强中医RAG系统测试")
    print("=" * 60)
    
    # 初始化系统
    rag_system = EnhancedTCMRAG()
    
    # 测试文件列表
    test_files = [
        '/home/ute/tcm-ai/all_tcm_docs/感冒.docx',
        '/home/ute/tcm-ai/all_tcm_docs/高血压.docx',
        '/home/ute/tcm-ai/all_tcm_docs/咳嗽.docx',
        '/home/ute/tcm-ai/all_tcm_docs/糖尿病.docx',
        '/home/ute/tcm-ai/all_tcm_docs/月经失调.docx'
    ]
    
    # 过滤存在的文件
    existing_files = [f for f in test_files if os.path.exists(f)]
    print(f"📁 找到 {len(existing_files)} 个测试文件")
    
    # 处理文档
    print(f"\n📝 开始处理文档...")
    processing_result = rag_system.process_docx_files(existing_files)
    
    if processing_result['success']:
        stats = processing_result['stats']
        print(f"\n✅ 文档处理完成!")
        print(f"   总分块数: {stats['total_documents']}")
        print(f"   新增分块: {stats['new_chunks']}")
        print(f"   平均分块大小: {stats['avg_chunk_size']:.0f}字符")
        
        # 测试查询
        test_queries = [
            "感冒的症状有哪些",
            "高血压如何治疗", 
            "咳嗽吃什么药",
            "糖尿病的病因",
            "月经失调的中医调理"
        ]
        
        print(f"\n🧪 开始RAG效果测试...")
        test_result = rag_system.test_rag_system(test_queries)
        
        if test_result['success']:
            summary = test_result['summary']
            print(f"\n📊 测试总结:")
            print(f"   测试查询数: {summary['total_queries']}")
            print(f"   成功查询数: {summary['successful_queries']}")
            print(f"   平均结果数: {summary['avg_results_per_query']:.1f}")
        else:
            print(f"❌ 测试失败: {test_result.get('error', 'unknown')}")
            
    else:
        print(f"❌ 文档处理失败: {processing_result.get('error', 'unknown')}")

if __name__ == "__main__":
    main()