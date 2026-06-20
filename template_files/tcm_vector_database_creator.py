#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCM向量数据库创建器
基于提取的病症-处方数据创建优化的向量数据库，用于问诊应用
"""

import sys
import os
import json
import numpy as np
from typing import Dict, List, Any, Tuple
import logging
from datetime import datetime
import pickle

# 检查并安装必要的包
try:
    import jieba
    import jieba.analyse
except ImportError:
    os.system("pip install jieba")
    import jieba
    import jieba.analyse

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    os.system("pip install sentence-transformers")
    from sentence_transformers import SentenceTransformer

try:
    import faiss
except ImportError:
    os.system("pip install faiss-cpu")
    import faiss

sys.path.append('/opt/tcm-ai')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TCMVectorDatabase:
    """TCM向量数据库管理器"""
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """初始化向量数据库"""
        print("🔧 初始化TCM向量数据库...")
        
        # 加载预训练模型（支持中文）
        try:
            self.model = SentenceTransformer(model_name)
            print(f"✅ 加载预训练模型: {model_name}")
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            # 使用备用模型
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            print("✅ 使用备用模型: all-MiniLM-L6-v2")
        
        # 设置jieba
        jieba.set_dictionary('dict.txt') if os.path.exists('dict.txt') else None
        
        # 数据容器
        self.prescriptions = []
        self.vectors = None
        self.index = None
        self.metadata = {}
        
        # 向量维度
        self.vector_dim = 384  # MiniLM模型的向量维度
        
    def load_tcm_database(self, database_path: str) -> bool:
        """加载TCM数据库"""
        try:
            with open(database_path, 'r', encoding='utf-8') as f:
                self.tcm_data = json.load(f)
            
            print(f"✅ 成功加载TCM数据库")
            print(f"   - 文档数: {self.tcm_data['total_documents']}")
            print(f"   - 处方数: {self.tcm_data['total_prescriptions']}")
            print(f"   - 病症数: {len(self.tcm_data['diseases_index'])}")
            
            return True
        except Exception as e:
            print(f"❌ 加载数据库失败: {e}")
            return False
    
    def prepare_prescription_texts(self) -> List[Dict[str, Any]]:
        """准备处方文本用于向量化"""
        print("📝 准备处方文本数据...")
        
        prescription_texts = []
        prescription_id = 0
        
        for doc in self.tcm_data['documents']:
            disease_name = doc['disease_name']
            
            for prescription in doc['prescriptions']:
                prescription_id += 1
                
                # 构建完整的处方描述文本
                text_parts = []
                
                # 1. 病症名称
                text_parts.append(f"病症：{disease_name}")
                
                # 2. 证型
                if prescription['syndrome']:
                    text_parts.append(f"证型：{prescription['syndrome']}")
                
                # 3. 治法
                if prescription['treatment_method']:
                    text_parts.append(f"治法：{prescription['treatment_method']}")
                
                # 4. 方剂名称
                text_parts.append(f"方剂：{prescription['formula_name']}")
                
                # 5. 药物组成
                herbs_text = "药物组成："
                herb_names = []
                for herb in prescription['herbs']:
                    herb_names.append(f"{herb['name']}{herb['dose']}{herb['unit']}")
                herbs_text += "、".join(herb_names)
                text_parts.append(herbs_text)
                
                # 6. 用法
                if prescription['usage']:
                    text_parts.append(f"用法：{prescription['usage']}")
                
                # 7. 症状描述（从原文中提取关键词）
                symptoms = self._extract_symptoms_from_text(prescription['source_text'])
                if symptoms:
                    text_parts.append(f"主要症状：{symptoms}")
                
                # 合并成完整文本
                full_text = "；".join(text_parts)
                
                # 创建处方记录
                prescription_record = {
                    'id': prescription_id,
                    'disease_name': disease_name,
                    'syndrome': prescription['syndrome'],
                    'treatment_method': prescription['treatment_method'],
                    'formula_name': prescription['formula_name'],
                    'herbs': prescription['herbs'],
                    'herb_count': prescription['herb_count'],
                    'usage': prescription['usage'],
                    'source_document': doc['filename'],
                    'source_text': prescription['source_text'],
                    'full_text': full_text,
                    'search_keywords': self._generate_search_keywords(prescription, disease_name)
                }
                
                prescription_texts.append(prescription_record)
        
        print(f"✅ 准备了 {len(prescription_texts)} 条处方文本")
        return prescription_texts
    
    def _extract_symptoms_from_text(self, text: str) -> str:
        """从原文中提取症状关键词"""
        # 常见症状关键词
        symptom_keywords = [
            '发热', '恶寒', '咳嗽', '痰多', '气短', '胸闷', '头痛', '头晕',
            '恶心', '呕吐', '腹痛', '腹泻', '便秘', '尿频', '尿急', '尿痛',
            '心悸', '失眠', '多梦', '盗汗', '自汗', '乏力', '疲倦',
            '食欲不振', '口干', '口苦', '咽痛', '鼻塞', '流涕',
            '月经不调', '痛经', '闭经', '白带', '阳痿', '早泄',
            '腰酸', '腰痛', '膝软', '手足冰冷', '潮热', '烦躁',
            '舌红', '舌淡', '苔薄', '苔厚', '苔黄', '苔白', '脉数', '脉缓'
        ]
        
        found_symptoms = []
        for symptom in symptom_keywords:
            if symptom in text:
                found_symptoms.append(symptom)
        
        return "、".join(found_symptoms[:10])  # 最多返回10个症状
    
    def _generate_search_keywords(self, prescription: Dict, disease_name: str) -> List[str]:
        """生成搜索关键词"""
        keywords = []
        
        # 病症名称
        keywords.append(disease_name)
        
        # 证型
        if prescription['syndrome']:
            keywords.append(prescription['syndrome'])
            # 拆分证型的组成部分
            syndrome_parts = jieba.lcut(prescription['syndrome'])
            keywords.extend([part for part in syndrome_parts if len(part) >= 2])
        
        # 治法
        if prescription['treatment_method']:
            treatment_parts = jieba.lcut(prescription['treatment_method'])
            keywords.extend([part for part in treatment_parts if len(part) >= 2])
        
        # 方剂名称
        keywords.append(prescription['formula_name'])
        
        # 主要药物
        for herb in prescription['herbs'][:10]:  # 前10味药
            keywords.append(herb['name'])
        
        # 去重并过滤短词
        keywords = list(set([kw for kw in keywords if len(kw) >= 2]))
        
        return keywords
    
    def create_vectors(self, prescription_texts: List[Dict[str, Any]]) -> np.ndarray:
        """创建向量"""
        print("🧮 创建向量嵌入...")
        
        texts = [item['full_text'] for item in prescription_texts]
        
        # 分批处理避免内存不足
        batch_size = 32
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batch_embeddings = self.model.encode(batch_texts, show_progress_bar=True)
            all_embeddings.append(batch_embeddings)
            
            if (i // batch_size + 1) % 10 == 0:
                print(f"   已处理: {i + len(batch_texts)}/{len(texts)}")
        
        vectors = np.vstack(all_embeddings)
        print(f"✅ 创建了 {vectors.shape[0]} 个向量，维度: {vectors.shape[1]}")
        
        return vectors
    
    def build_faiss_index(self, vectors: np.ndarray) -> faiss.Index:
        """构建FAISS索引"""
        print("🏗️ 构建FAISS索引...")
        
        # 使用IVF索引提高搜索效率
        nlist = min(100, vectors.shape[0] // 10)  # 聚类数量
        quantizer = faiss.IndexFlatIP(vectors.shape[1])  # 内积相似度
        index = faiss.IndexIVFFlat(quantizer, vectors.shape[1], nlist)
        
        # 训练索引
        index.train(vectors.astype('float32'))
        
        # 添加向量
        index.add(vectors.astype('float32'))
        
        # 设置搜索参数
        index.nprobe = min(10, nlist)
        
        print(f"✅ FAISS索引构建完成，包含 {index.ntotal} 个向量")
        return index
    
    def save_vector_database(self, output_dir: str):
        """保存向量数据库"""
        print(f"💾 保存向量数据库到: {output_dir}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存FAISS索引
        faiss.write_index(self.index, os.path.join(output_dir, 'tcm_prescriptions.index'))
        
        # 保存处方数据
        with open(os.path.join(output_dir, 'prescriptions.json'), 'w', encoding='utf-8') as f:
            json.dump(self.prescriptions, f, ensure_ascii=False, indent=2)
        
        # 保存元数据
        metadata = {
            'creation_time': datetime.now().isoformat(),
            'model_name': self.model.get_sentence_embedding_dimension(),
            'total_prescriptions': len(self.prescriptions),
            'vector_dimension': self.vector_dim,
            'diseases_count': len(set([p['disease_name'] for p in self.prescriptions])),
            'herbs_count': len(set([herb['name'] for p in self.prescriptions for herb in p['herbs']])),
            'index_type': 'IVFFlat',
            'similarity_metric': 'inner_product'
        }
        
        with open(os.path.join(output_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # 保存向量（用于备份）
        np.save(os.path.join(output_dir, 'vectors.npy'), self.vectors)
        
        print("✅ 向量数据库保存完成")
        
        # 生成使用说明
        readme_content = f"""# TCM向量数据库使用说明

## 数据库信息
- 创建时间: {metadata['creation_time']}
- 处方总数: {metadata['total_prescriptions']}
- 病症数量: {metadata['diseases_count']}
- 药物数量: {metadata['herbs_count']}
- 向量维度: {metadata['vector_dimension']}

## 文件说明
- `tcm_prescriptions.index`: FAISS索引文件
- `prescriptions.json`: 处方详细数据
- `vectors.npy`: 向量数组
- `metadata.json`: 元数据信息

## 使用示例
```python
import faiss
import json

# 加载索引
index = faiss.read_index('tcm_prescriptions.index')

# 加载处方数据
with open('prescriptions.json', 'r', encoding='utf-8') as f:
    prescriptions = json.load(f)

# 搜索相似处方
query_vector = model.encode(["患者咳嗽痰多，舌苔黄腻"])
D, I = index.search(query_vector, k=5)

# 获取结果
results = [prescriptions[i] for i in I[0]]
```

## 优化特点
1. 基于实际TCM文档提取的{metadata['total_prescriptions']}个处方
2. 包含完整的病症-证型-治法-处方映射
3. 支持症状、药物、方剂名称等多维度搜索
4. 使用高效的FAISS索引，支持快速相似度搜索
5. 中文优化的向量化处理
"""
        
        with open(os.path.join(output_dir, 'README.md'), 'w', encoding='utf-8') as f:
            f.write(readme_content)
    
    def create_complete_database(self, database_path: str, output_dir: str):
        """创建完整的向量数据库"""
        print("🚀 开始创建TCM向量数据库...")
        
        # 1. 加载数据
        if not self.load_tcm_database(database_path):
            return False
        
        # 2. 准备文本
        self.prescriptions = self.prepare_prescription_texts()
        
        # 3. 创建向量
        self.vectors = self.create_vectors(self.prescriptions)
        
        # 4. 构建索引
        self.index = self.build_faiss_index(self.vectors)
        
        # 5. 保存数据库
        self.save_vector_database(output_dir)
        
        print("🎉 TCM向量数据库创建完成！")
        return True

def main():
    """主函数"""
    print("=" * 80)
    print("TCM病症-处方向量数据库创建器")
    print("=" * 80)
    
    # 创建向量数据库
    db_creator = TCMVectorDatabase()
    
    # 输入输出路径
    database_path = '/opt/tcm-ai/template_files/complete_tcm_database.json'
    output_dir = '/opt/tcm-ai/template_files/tcm_vector_db'
    
    # 创建数据库
    success = db_creator.create_complete_database(database_path, output_dir)
    
    if success:
        print(f"\n✅ 向量数据库已成功创建在: {output_dir}")
        print("🔍 可以开始用于问诊应用了！")
    else:
        print("\n❌ 向量数据库创建失败")
    
    return success

if __name__ == "__main__":
    main()