#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量级TCM向量数据库创建器
不依赖网络下载，使用TF-IDF和中文分词的本地方案
"""

import sys
import os
import json
import numpy as np
from typing import Dict, List, Any, Tuple
import logging
from datetime import datetime
import pickle
from collections import Counter, defaultdict
import math

# 检查并安装jieba
try:
    import jieba
    import jieba.analyse
except ImportError:
    os.system("pip install jieba")
    import jieba
    import jieba.analyse

# sklearn的TF-IDF
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    os.system("pip install scikit-learn")
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

sys.path.append('/opt/tcm-ai')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LightweightTCMVectorDatabase:
    """轻量级TCM向量数据库管理器"""
    
    def __init__(self):
        """初始化向量数据库"""
        print("🔧 初始化轻量级TCM向量数据库...")
        
        # 设置jieba自定义词典
        self._setup_custom_dict()
        
        # TF-IDF向量化器
        self.vectorizer = TfidfVectorizer(
            tokenizer=self._jieba_tokenizer,
            lowercase=False,
            max_features=5000,  # 最大特征数
            min_df=2,  # 最小文档频率
            max_df=0.8,  # 最大文档频率
            ngram_range=(1, 2)  # 1-2gram
        )
        
        # 数据容器
        self.prescriptions = []
        self.vectors = None
        self.metadata = {}
        
    def _setup_custom_dict(self):
        """设置自定义中医词典"""
        # 中医专业词汇
        tcm_vocab = [
            # 病症
            '感冒', '咳嗽', '发热', '头痛', '腹泻', '便秘', '失眠', '咽炎',
            '高血压', '糖尿病', '月经失调', '痛经', '肾炎', '肝硬化',
            # 证型
            '风寒感冒', '风热感冒', '阴虚火旺', '痰湿咳嗽', '肺热咳嗽',
            '脾虚湿盛', '肝郁气滞', '心血不足', '肾阳虚', '肾阴虚',
            # 症状
            '恶寒', '发热', '咳痰', '气短', '胸闷', '心悸', '盗汗',
            '口干', '咽痛', '腹痛', '腰酸', '头晕', '乏力',
            # 治法
            '辛温解表', '辛凉解表', '清热解毒', '化痰止咳', '润肺止咳',
            '健脾益气', '疏肝理气', '活血化瘀', '滋阴润燥', '温阳利水',
            # 药物
            '甘草', '当归', '白芍', '川芎', '茯苓', '白术', '陈皮',
            '半夏', '黄芩', '柴胡', '桔梗', '杏仁', '麻黄', '桂枝',
            # 方剂
            '银翘散', '麻杏石甘汤', '小柴胡汤', '四君子汤', '六味地黄丸'
        ]
        
        for word in tcm_vocab:
            jieba.add_word(word)
    
    def _jieba_tokenizer(self, text: str) -> List[str]:
        """使用jieba进行中文分词"""
        # 分词
        words = jieba.lcut(text)
        
        # 过滤掉标点符号和单字符
        filtered_words = []
        for word in words:
            word = word.strip()
            if len(word) >= 2 and not self._is_punctuation(word):
                filtered_words.append(word)
        
        return filtered_words
    
    def _is_punctuation(self, word: str) -> bool:
        """判断是否为标点符号"""
        punctuations = set('，。！？；：""''（）【】《》、·～@#￥%……&*+-={}[]|\\/')
        return all(c in punctuations or c.isspace() or c.isdigit() for c in word)
    
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
                
                # 构建搜索文本 - 包含多个维度的信息
                text_parts = []
                
                # 1. 病症名称
                text_parts.append(disease_name)
                
                # 2. 证型
                if prescription['syndrome']:
                    text_parts.append(prescription['syndrome'])
                
                # 3. 治法
                if prescription['treatment_method']:
                    text_parts.append(prescription['treatment_method'])
                
                # 4. 方剂名称
                text_parts.append(prescription['formula_name'])
                
                # 5. 药物名称
                herb_names = [herb['name'] for herb in prescription['herbs']]
                text_parts.extend(herb_names)
                
                # 6. 症状关键词（从原文中提取）
                symptoms = self._extract_symptom_keywords(prescription['source_text'])
                text_parts.extend(symptoms)
                
                # 合并成搜索文本
                search_text = ' '.join(text_parts)
                
                # 创建显示文本（更易读）
                display_parts = []
                display_parts.append(f"病症：{disease_name}")
                
                if prescription['syndrome']:
                    display_parts.append(f"证型：{prescription['syndrome']}")
                
                if prescription['treatment_method']:
                    display_parts.append(f"治法：{prescription['treatment_method']}")
                
                display_parts.append(f"方剂：{prescription['formula_name']}")
                
                herbs_text = "药物："
                herb_list = []
                for herb in prescription['herbs'][:10]:  # 显示前10味药
                    herb_list.append(f"{herb['name']}{herb['dose']}{herb['unit']}")
                herbs_text += "、".join(herb_list)
                if len(prescription['herbs']) > 10:
                    herbs_text += f"等{len(prescription['herbs'])}味药"
                display_parts.append(herbs_text)
                
                if prescription['usage']:
                    display_parts.append(f"用法：{prescription['usage']}")
                
                display_text = "；".join(display_parts)
                
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
                    'search_text': search_text,
                    'display_text': display_text,
                    'search_keywords': self._generate_search_keywords(prescription, disease_name)
                }
                
                prescription_texts.append(prescription_record)
        
        print(f"✅ 准备了 {len(prescription_texts)} 条处方文本")
        return prescription_texts
    
    def _extract_symptom_keywords(self, text: str) -> List[str]:
        """从文本中提取症状关键词"""
        symptom_keywords = [
            '发热', '恶寒', '咳嗽', '痰多', '痰少', '痰黄', '痰白', '痰粘',
            '气短', '胸闷', '胸痛', '心悸', '心烦', '失眠', '多梦',
            '头痛', '头晕', '目眩', '耳鸣', '咽痛', '咽干', '口干',
            '口苦', '口淡', '恶心', '呕吐', '腹痛', '腹胀', '腹泻',
            '便秘', '便血', '尿频', '尿急', '尿痛', '水肿', '乏力',
            '疲倦', '自汗', '盗汗', '潮热', '怕冷', '腰酸', '腰痛',
            '膝软', '月经不调', '痛经', '白带', '阳痿', '早泄',
            '舌红', '舌淡', '舌胖', '苔薄', '苔厚', '苔黄', '苔白',
            '苔腻', '脉数', '脉缓', '脉细', '脉滑', '脉弦', '脉沉'
        ]
        
        found_symptoms = []
        for symptom in symptom_keywords:
            if symptom in text:
                found_symptoms.append(symptom)
        
        return found_symptoms[:15]  # 最多返回15个症状
    
    def _generate_search_keywords(self, prescription: Dict, disease_name: str) -> List[str]:
        """生成搜索关键词"""
        keywords = []
        
        # 病症名称及其分词
        keywords.append(disease_name)
        disease_words = jieba.lcut(disease_name)
        keywords.extend([w for w in disease_words if len(w) >= 2])
        
        # 证型
        if prescription['syndrome']:
            keywords.append(prescription['syndrome'])
            syndrome_words = jieba.lcut(prescription['syndrome'])
            keywords.extend([w for w in syndrome_words if len(w) >= 2])
        
        # 治法
        if prescription['treatment_method']:
            treatment_words = jieba.lcut(prescription['treatment_method'])
            keywords.extend([w for w in treatment_words if len(w) >= 2])
        
        # 方剂名称
        keywords.append(prescription['formula_name'])
        
        # 主要药物
        for herb in prescription['herbs'][:8]:  # 前8味药
            keywords.append(herb['name'])
        
        # 去重并过滤
        keywords = list(set([kw for kw in keywords if len(kw) >= 2]))
        
        return keywords
    
    def create_vectors(self, prescription_texts: List[Dict[str, Any]]) -> np.ndarray:
        """创建TF-IDF向量"""
        print("🧮 创建TF-IDF向量...")
        
        texts = [item['search_text'] for item in prescription_texts]
        
        # 训练TF-IDF模型并转换文本
        vectors = self.vectorizer.fit_transform(texts)
        
        print(f"✅ 创建了 {vectors.shape[0]} 个向量，维度: {vectors.shape[1]}")
        print(f"🔤 词汇表大小: {len(self.vectorizer.vocabulary_)}")
        
        return vectors
    
    def save_vector_database(self, output_dir: str):
        """保存向量数据库"""
        print(f"💾 保存向量数据库到: {output_dir}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存TF-IDF向量（稀疏矩阵）
        with open(os.path.join(output_dir, 'tfidf_vectors.pkl'), 'wb') as f:
            pickle.dump(self.vectors, f)
        
        # 保存TF-IDF向量化器
        with open(os.path.join(output_dir, 'tfidf_vectorizer.pkl'), 'wb') as f:
            pickle.dump(self.vectorizer, f)
        
        # 保存处方数据
        with open(os.path.join(output_dir, 'prescriptions.json'), 'w', encoding='utf-8') as f:
            json.dump(self.prescriptions, f, ensure_ascii=False, indent=2)
        
        # 保存元数据
        metadata = {
            'creation_time': datetime.now().isoformat(),
            'model_type': 'TF-IDF',
            'total_prescriptions': len(self.prescriptions),
            'vector_dimension': self.vectors.shape[1] if self.vectors is not None else 0,
            'vocabulary_size': len(self.vectorizer.vocabulary_),
            'diseases_count': len(set([p['disease_name'] for p in self.prescriptions])),
            'herbs_count': len(set([herb['name'] for p in self.prescriptions for herb in p['herbs']])),
            'similarity_metric': 'cosine'
        }
        
        with open(os.path.join(output_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print("✅ 向量数据库保存完成")
        
        # 生成简单的测试脚本
        test_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCM向量数据库测试脚本
"""
import pickle
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import jieba

def load_database():
    """加载数据库"""
    # 加载向量
    with open('tfidf_vectors.pkl', 'rb') as f:
        vectors = pickle.load(f)
    
    # 加载向量化器
    with open('tfidf_vectorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)
    
    # 加载处方数据
    with open('prescriptions.json', 'r', encoding='utf-8') as f:
        prescriptions = json.load(f)
    
    return vectors, vectorizer, prescriptions

def search_prescriptions(query, k=5):
    """搜索相似处方"""
    vectors, vectorizer, prescriptions = load_database()
    
    # 将查询转换为向量
    query_vector = vectorizer.transform([query])
    
    # 计算余弦相似度
    similarities = cosine_similarity(query_vector, vectors)[0]
    
    # 获取top-k结果
    top_indices = np.argsort(similarities)[::-1][:k]
    
    results = []
    for i, idx in enumerate(top_indices):
        result = {
            'rank': i + 1,
            'similarity': similarities[idx],
            'prescription': prescriptions[idx]
        }
        results.append(result)
    
    return results

if __name__ == "__main__":
    # 测试查询
    test_queries = [
        "咳嗽痰多发热",
        "风寒感冒恶寒",
        "头痛失眠心烦",
        "腹泻腹痛"
    ]
    
    print("🔍 TCM向量数据库测试")
    print("=" * 60)
    
    for test_query in test_queries:
        print(f"\\n查询: {test_query}")
        results = search_prescriptions(test_query, k=3)
        
        for result in results:
            print(f"  [{result['rank']}] 相似度: {result['similarity']:.3f}")
            print(f"      {result['prescription']['display_text'][:100]}...")
'''
        
        with open(os.path.join(output_dir, 'test_search.py'), 'w', encoding='utf-8') as f:
            f.write(test_script)
        
        # 生成使用说明
        readme_content = f"""# TCM轻量级向量数据库

## 数据库信息
- 创建时间: {metadata['creation_time']}
- 模型类型: {metadata['model_type']}
- 处方总数: {metadata['total_prescriptions']}
- 向量维度: {metadata['vector_dimension']}
- 词汇表大小: {metadata['vocabulary_size']}
- 病症数量: {metadata['diseases_count']}
- 药物数量: {metadata['herbs_count']}

## 文件说明
- `tfidf_vectors.pkl`: TF-IDF向量数据（scipy稀疏矩阵）
- `tfidf_vectorizer.pkl`: TF-IDF向量化器
- `prescriptions.json`: 处方详细数据
- `metadata.json`: 元数据信息
- `test_search.py`: 测试搜索脚本

## 快速测试
```bash
python test_search.py
```

## 使用示例
```python
import pickle
import json
from sklearn.metrics.pairwise import cosine_similarity

# 加载数据库
with open('tfidf_vectors.pkl', 'rb') as f:
    vectors = pickle.load(f)

with open('tfidf_vectorizer.pkl', 'rb') as f:
    vectorizer = pickle.load(f)

with open('prescriptions.json', 'r', encoding='utf-8') as f:
    prescriptions = json.load(f)

# 搜索
query = "咳嗽痰多发热"
query_vector = vectorizer.transform([query])
similarities = cosine_similarity(query_vector, vectors)[0]
top_indices = similarities.argsort()[::-1][:5]

# 显示结果
for i, idx in enumerate(top_indices):
    print(f"{{i+1}}. 相似度: {{similarities[idx]:.3f}}")
    print(f"   {{prescriptions[idx]['display_text']}}")
```

## 优势
1. 完全本地化，无需网络连接
2. 轻量级，文件大小适中
3. 快速搜索，毫秒级响应
4. 支持中文分词和语义匹配
5. 易于集成到现有系统
"""
        
        with open(os.path.join(output_dir, 'README.md'), 'w', encoding='utf-8') as f:
            f.write(readme_content)
    
    def create_complete_database(self, database_path: str, output_dir: str):
        """创建完整的向量数据库"""
        print("🚀 开始创建轻量级TCM向量数据库...")
        
        # 1. 加载数据
        if not self.load_tcm_database(database_path):
            return False
        
        # 2. 准备文本
        self.prescriptions = self.prepare_prescription_texts()
        
        # 3. 创建向量
        self.vectors = self.create_vectors(self.prescriptions)
        
        # 4. 保存数据库
        self.save_vector_database(output_dir)
        
        print("🎉 轻量级TCM向量数据库创建完成！")
        return True

def main():
    """主函数"""
    print("=" * 80)
    print("轻量级TCM病症-处方向量数据库创建器")
    print("=" * 80)
    
    # 创建向量数据库
    db_creator = LightweightTCMVectorDatabase()
    
    # 输入输出路径
    database_path = '/opt/tcm-ai/template_files/complete_tcm_database.json'
    output_dir = '/opt/tcm-ai/template_files/lightweight_vector_db'
    
    # 创建数据库
    success = db_creator.create_complete_database(database_path, output_dir)
    
    if success:
        print(f"\n✅ 轻量级向量数据库已成功创建在: {output_dir}")
        print("🔍 运行测试: python test_search.py")
        print("📖 查看说明: cat README.md")
    else:
        print("\n❌ 向量数据库创建失败")
    
    return success

if __name__ == "__main__":
    main()