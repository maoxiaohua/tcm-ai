# enhanced_retrieval.py - 增强检索精度系统

import os
import re
import jieba
import numpy as np
import faiss
import pickle
from collections import defaultdict, Counter
from typing import List, Dict, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class EnhancedKnowledgeRetrieval:
    def __init__(self, knowledge_db_path: str):
        self.knowledge_db_path = knowledge_db_path
        self.faiss_index_file = os.path.join(knowledge_db_path, "knowledge.index")
        self.documents_file = os.path.join(knowledge_db_path, "documents.pkl")
        self.metadata_file = os.path.join(knowledge_db_path, "metadata.pkl")
        
        # 混合检索组件
        self.faiss_index = None
        self.documents = []
        self.metadata = []
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        
        # 疾病精确匹配权重字典 - 用于提升疾病名称查询精度
        self.disease_exact_weights = {
            # 主要疾病 - 高权重
            "高血压": 10.0, "糖尿病": 10.0, "冠心病": 10.0, "肺结核病": 10.0,
            "消化性溃疡": 9.0, "肝硬化": 9.0, "慢性气管炎": 9.0, "神经衰弱": 9.0,
            "月经失调": 8.0, "脑血管病": 8.0, "肾炎": 8.0, "关节炎": 8.0,
            "肿瘤病": 8.0, "虚损": 7.0, "哮喘": 7.0, "湿疹": 7.0,
            
            # 儿科疾病
            "小儿支气管炎": 9.0, "小儿消化不良": 9.0, "小儿遗尿症": 8.0,
            "小儿病毒性肺炎": 8.0, "小儿痿证": 7.0, "百日咳": 7.0,
            "流行性腮腺炎": 7.0, "麻疹": 7.0, "风疹": 6.0, "水痘": 6.0,
            
            # 妇科疾病
            "功能性子宫出血": 8.0, "痛经": 7.0, "流产": 7.0, 
            "子宫脱垂": 7.0, "缺乳": 6.0, "妊娠呕吐": 6.0,
            
            # 外科疾病
            "泌尿系结石": 8.0, "胆石病": 8.0, "腰痛": 7.0, "头晕": 7.0,
            "肛门直肠病": 7.0, "乳房疾患": 6.0, "颈淋巴结核": 6.0,
            
            # 五官科疾病
            "咽炎": 7.0, "扁桃体炎": 7.0, "化脓性中耳炎": 7.0,
            "青光眼": 6.0, "夏季常见皮肤病": 6.0,
            
            # 内科杂病
            "感冒": 8.0, "咳嗽": 7.0, "便秘": 7.0, "泄泻": 7.0,
            "疟疾": 6.0, "癔病": 6.0, "癫痫": 6.0, "食欲不振": 6.0,
            "出汗异常": 6.0, "血栓闭塞性脉管炎": 6.0, "贫血": 6.0,
            
            # 老年病和常见病
            "老年病": 7.0, "中暑": 6.0, "大叶性肺炎": 7.0, "肺脓肿": 7.0,
            "胆道蛔虫病": 6.0, "脑炎后遗症": 6.0, "大脑发育不全": 6.0,
            "常见肠寄生虫病": 6.0, "小儿营养不良": 6.0, "男子不育": 6.0
        }
        
        # 大幅扩展的中医术语同义词字典
        self.tcm_synonyms = {
            # 基础症状
            "头痛": ["头疼", "脑袋疼", "偏头痛", "头晕痛", "头胀痛", "巅顶痛"],
            "发热": ["发烧", "高热", "低热", "身热", "潮热", "寒热往来", "微热"],
            "咳嗽": ["咳", "干咳", "湿咳", "久咳", "痰咳", "咳痰", "咳逆"],
            "失眠": ["不寐", "睡不着", "多梦", "早醒", "入睡困难", "神经衰弱失眠"],
            "便秘": ["大便干", "排便难", "便结", "大便不通", "便难"],
            "腹泻": ["泄泻", "拉肚子", "大便溏", "水样便", "溏泄", "滑泄"],
            
            # 主要疾病
            "高血压": ["血压高", "高血压病", "眩晕", "头晕目眩"],
            "糖尿病": ["消渴", "消渴症", "三多一少", "多尿多饮多食"],
            "月经失调": ["月经不调", "经期紊乱", "月事不调", "经水不调", "经血异常"],
            "脑血管病": ["中风", "卒中", "偏瘫", "半身不遂", "脑梗", "脑出血"],
            "肝硬化": ["肝硬变", "肝纤维化", "积聚", "鼓胀"],
            "消化性溃疡": ["胃溃疡", "十二指肠溃疡", "胃脘痛", "心下痛"],
            "肺结核病": ["肺痨", "痨病", "肺病", "咯血"],
            "慢性气管炎": ["气管炎", "支气管炎", "慢支", "咳喘"],
            "神经衰弱": ["神经衰弱失眠", "心神不宁", "心悸失眠", "健忘"],
            
            # 妇科疾病
            "流产": ["小产", "胎堕", "胎动不安", "胎漏"],
            "子宫脱垂": ["阴挺", "阴脱", "子宫下垂"],
            "白带异常": ["带下", "赤白带", "带下过多", "阴道分泌物"],
            
            # 肿瘤相关
            "肿瘤病": ["肿瘤", "癌症", "恶性肿瘤", "积聚", "症瘕"],
            "乳腺肿块": ["乳癖", "乳中结核", "乳房肿块"],
            
            # 内科疾病  
            "虚损": ["虚劳", "体虚", "气血虚", "精神不振", "乏力"],
            "出汗异常": ["自汗", "盗汗", "汗出", "多汗", "无汗"],
            "水肿": ["肿胀", "浮肿", "身肿", "面肿", "足肿"],
            "黄疸": ["身黄", "目黄", "小便黄", "阳黄", "阴黄"],
            
            # 呼吸系统
            "咽炎": ["咽痛", "喉痛", "咽干", "咽部不适"],
            "扁桃体炎": ["乳蛾", "喉蛾", "扁桃体肿大"],
            "哮喘": ["喘证", "气喘", "哮吼", "喘息"],
            
            # 消化系统
            "胃炎": ["胃脘痛", "胃痛", "心下痛", "胃胀"],
            "肝炎": ["胁痛", "肝区痛", "黄疸", "肝病"],
            "胆囊炎": ["胆胀", "右胁痛", "胆石症"],
            "肠炎": ["腹痛", "肠鸣", "泄泻", "痢疾"],
            
            # 泌尿系统
            "肾炎": ["水肿", "腰痛", "小便不利", "肾病"],
            "尿路感染": ["淋证", "小便涩痛", "尿频尿急"],
            "前列腺炎": ["精浊", "白浊", "前阴不适"],
            
            # 骨科疾病
            "颈椎病": ["项强", "颈项强痛", "落枕"],
            "腰椎病": ["腰痛", "腰脊痛", "腰膝酸软"],
            "关节炎": ["痹证", "关节痛", "骨痹", "行痹", "痛痹", "着痹"],
            
            # 皮肤疾病
            "湿疹": ["湿疮", "浸淫疮", "四弯风"],
            "荨麻疹": ["瘾疹", "风疹块", "风团"],
            "银屑病": ["白疕", "松皮癣", "牛皮癣"],
            
            # 五官科
            "结膜炎": ["目赤", "红眼病", "风热眼", "天行赤眼"],
            "中耳炎": ["耳痛", "脓耳", "聤耳"],
            "鼻炎": ["鼻塞", "鼻渊", "鼻窒"],
            
            # 老年疾病
            "老年病": ["老年综合征", "衰老", "精神萎靡", "体弱"],
            "动脉硬化": ["血脉瘀阻", "血管硬化", "脉道不利"],
            "冠心病": ["胸痹", "心痛", "真心痛", "厥心痛"],
            
            # 儿科疾病
            "小儿病毒性肺炎": ["小儿肺炎", "儿童肺炎", "小儿咳喘", "小儿发热咳嗽"],
            "小儿腹泻": ["小儿泄泻", "婴幼儿腹泻", "小儿消化不良"],
            "小儿感冒": ["小儿外感", "儿童感冒", "小儿发热"],
            
            # 精神神经
            "抑郁症": ["郁证", "情志不畅", "心情抑郁", "悲伤"],
            "焦虑症": ["惊悸", "心神不宁", "烦躁不安"],
            "健忘": ["善忘", "记忆力减退", "神志不清"],
            
            # 代谢疾病
            "痛风": ["痹证", "白虎历节风", "历节病"],
            "甲亢": ["瘿病", "心悸多汗", "甲状腺肿大"],
            "甲减": ["虚劳", "畏寒乏力", "甲状腺功能减退"]
        }
        
        # 症状与疾病的映射关系
        self.symptom_disease_mapping = {
            "头痛头晕": ["高血压", "脑血管病", "神经衰弱"],
            "咳嗽咳痰": ["慢性气管炎", "肺结核病", "咽炎"],
            "胸闷心悸": ["冠心病", "神经衰弱", "甲亢"],
            "腹痛腹泻": ["肠炎", "消化性溃疡", "肝硬化"],
            "腰痛": ["肾炎", "腰椎病", "前列腺炎"],
            "月经异常": ["月经失调", "子宫脱垂", "流产"],
            "失眠多梦": ["神经衰弱", "抑郁症", "焦虑症"],
            "乏力虚弱": ["虚损", "老年病", "甲减"]
        }
        
        # 症状权重（根据中医重要性）
        self.symptom_weights = {
            "主诉": 1.5,
            "发热": 1.3,
            "疼痛": 1.3,
            "咳嗽": 1.2,
            "失眠": 1.2,
            "便秘": 1.1,
            "腹泻": 1.1
        }
        
        self.load_knowledge_base()
        
    def load_knowledge_base(self):
        """加载知识库"""
        try:
            if os.path.exists(self.faiss_index_file):
                self.faiss_index = faiss.read_index(self.faiss_index_file)
                
            with open(self.documents_file, 'rb') as f:
                self.documents = pickle.load(f)
                
            with open(self.metadata_file, 'rb') as f:
                self.metadata = pickle.load(f)
                
            # 建立TF-IDF索引用于关键词检索
            self._build_tfidf_index()
            
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            
    def _build_tfidf_index(self):
        """建立TF-IDF索引"""
        if not self.documents:
            return
            
        # 中文分词
        segmented_docs = []
        for doc in self.documents:
            # 使用jieba分词，保留中医专业词汇
            words = jieba.cut(doc)
            segmented_docs.append(" ".join(words))
            
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            stop_words=self._get_chinese_stopwords()
        )
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(segmented_docs)
        
    def _get_chinese_stopwords(self) -> List[str]:
        """中文停用词"""
        return ["的", "了", "在", "是", "有", "和", "与", "及", "或", "但", "而", "因为", "所以"]
        
    def expand_query(self, query: str) -> str:
        """查询扩展 - 添加同义词和相关术语"""
        expanded_terms = [query]
        
        # 1. 直接同义词扩展
        for main_term, synonyms in self.tcm_synonyms.items():
            if main_term in query:
                expanded_terms.extend(synonyms[:3])  # 添加前3个最相关的同义词
            for synonym in synonyms:
                if synonym in query and main_term not in expanded_terms:
                    expanded_terms.append(main_term)
                    break
        
        # 2. 症状-疾病关联扩展
        for symptom_key, diseases in self.symptom_disease_mapping.items():
            if any(term in query for term in symptom_key.split()):
                expanded_terms.extend(diseases[:2])  # 添加相关疾病
                
        # 去重并返回（保持顺序）
        unique_terms = list(dict.fromkeys(expanded_terms))
        return " ".join(unique_terms)
        
    def semantic_search(self, query_embedding: List[float], k: int = 10) -> List[Dict]:
        """语义检索"""
        if self.faiss_index.ntotal == 0:
            return []
            
        query_array = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_array)
        
        scores, indices = self.faiss_index.search(query_array, min(k, self.faiss_index.ntotal))
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(self.documents):
                results.append({
                    'document': self.documents[idx],
                    'metadata': self.metadata[idx],
                    'semantic_score': float(scores[0][i]),
                    'index': idx,
                    'method': 'semantic'
                })
                
        # 确保即使没有高分结果也返回最佳的几个
        if len(results) == 0 and len(top_indices) > 0:
            for idx in top_indices[:k]:
                results.append({
                    'document': self.documents[idx],
                    'metadata': self.metadata[idx],
                    'similarity_score': float(similarities[idx]),
                    'keyword_score': float(similarities[idx]),
                    'source': self.metadata[idx].get('source', 'unknown'),
                    'index': idx,
                    'method': 'keyword'
                })
        
        return results
        
    def keyword_search(self, query: str, k: int = 10) -> List[Dict]:
        """关键词检索（TF-IDF）"""
        if self.tfidf_matrix is None:
            return []
            
        # 扩展查询
        expanded_query = self.expand_query(query)
        
        # 分词并向量化查询
        words = jieba.cut(expanded_query)
        query_text = " ".join(words)
        query_vector = self.tfidf_vectorizer.transform([query_text])
        
        # 计算相似度
        similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
        
        # 获取top-k结果
        top_indices = similarities.argsort()[-k:][::-1]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.001:  # 降低阈值确保更多结果
                results.append({
                    'document': self.documents[idx],
                    'metadata': self.metadata[idx],
                    'similarity_score': float(similarities[idx]),  # 统一字段名
                    'keyword_score': float(similarities[idx]),     # 保持兼容性
                    'source': self.metadata[idx].get('source', 'unknown'),
                    'index': idx,
                    'method': 'keyword'
                })
                
        # 确保即使没有高分结果也返回最佳的几个
        if len(results) == 0 and len(top_indices) > 0:
            for idx in top_indices[:k]:
                results.append({
                    'document': self.documents[idx],
                    'metadata': self.metadata[idx],
                    'similarity_score': float(similarities[idx]),
                    'keyword_score': float(similarities[idx]),
                    'source': self.metadata[idx].get('source', 'unknown'),
                    'index': idx,
                    'method': 'keyword'
                })
        
        return results
        
    def hybrid_search(self, query: str, query_embedding: List[float], 
                     semantic_weight: float = 0.7, keyword_weight: float = 0.3,
                     total_results: int = 5) -> List[Dict]:
        """混合检索 - 融合语义和关键词检索结果"""
        
        # 分别进行两种检索
        semantic_results = self.semantic_search(query_embedding, k=15)
        keyword_results = self.keyword_search(query, k=15)
        
        # 创建文档索引到结果的映射
        result_map = defaultdict(dict)
        
        # 处理语义检索结果
        for result in semantic_results:
            idx = result['index']
            result_map[idx]['document'] = result['document']
            result_map[idx]['metadata'] = result['metadata']
            result_map[idx]['semantic_score'] = result['semantic_score']
            
        # 处理关键词检索结果
        for result in keyword_results:
            idx = result['index']
            if idx not in result_map:
                result_map[idx]['document'] = result['document']
                result_map[idx]['metadata'] = result['metadata']
            result_map[idx]['keyword_score'] = result['keyword_score']
            
        # 计算混合分数
        final_results = []
        for idx, data in result_map.items():
            semantic_score = data.get('semantic_score', 0.0)
            keyword_score = data.get('keyword_score', 0.0)
            
            # 归一化分数
            normalized_semantic = self._normalize_score(semantic_score, 'semantic')
            normalized_keyword = self._normalize_score(keyword_score, 'keyword')
            
            # 计算症状权重加成
            symptom_bonus = self._calculate_symptom_bonus(query, data['document'])
            
            # 计算疾病精确匹配加成
            disease_exact_bonus = self._calculate_disease_exact_bonus(query, data['document'], data['metadata'])
            
            # 混合分数
            hybrid_score = (semantic_weight * normalized_semantic + 
                          keyword_weight * normalized_keyword + 
                          symptom_bonus + disease_exact_bonus)
            
            final_results.append({
                'document': data['document'],
                'metadata': data['metadata'],
                'hybrid_score': hybrid_score,
                'semantic_score': semantic_score,
                'keyword_score': keyword_score,
                'symptom_bonus': symptom_bonus,
                'disease_exact_bonus': disease_exact_bonus
            })
            
        # 按混合分数排序并去重
        final_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        final_results = self._remove_duplicates(final_results)
        
        return final_results[:total_results]
        
    def _normalize_score(self, score: float, method: str) -> float:
        """分数归一化"""
        if method == 'semantic':
            # FAISS内积分数通常在0-1之间
            return max(0, min(1, score))
        elif method == 'keyword':
            # TF-IDF余弦相似度在0-1之间
            return score
        return score
        
    def _calculate_symptom_bonus(self, query: str, document: str) -> float:
        """计算症状权重加成"""
        bonus = 0.0
        query_lower = query.lower()
        doc_lower = document.lower()
        
        for symptom, weight in self.symptom_weights.items():
            if symptom in query_lower and symptom in doc_lower:
                bonus += (weight - 1.0) * 0.1  # 转换为0.1以内的加成
                
        return min(bonus, 0.3)  # 最大加成0.3
    
    def _calculate_disease_exact_bonus(self, query: str, document: str, metadata: Dict) -> float:
        """计算疾病精确匹配加成 - 核心功能"""
        bonus = 0.0
        query_clean = query.strip().lower()
        doc_lower = document.lower()
        source = metadata.get('source', '').lower()
        
        # 1. 直接疾病名匹配 - 最高优先级
        for disease_name, weight in self.disease_exact_weights.items():
            disease_lower = disease_name.lower()
            
            # 精确匹配查询
            if disease_lower == query_clean:
                # 文档标题匹配
                if disease_lower in source:
                    bonus += weight * 0.8  # 超高权重：标题精确匹配
                    print(f"🎯 疾病精确匹配(标题): {disease_name} -> 权重:{weight * 0.8:.1f}")
                # 文档内容匹配
                elif disease_lower in doc_lower:
                    bonus += weight * 0.6  # 高权重：内容精确匹配
                    print(f"🎯 疾病精确匹配(内容): {disease_name} -> 权重:{weight * 0.6:.1f}")
                    
        # 2. 疾病名包含匹配 - 次优先级
        for disease_name, weight in self.disease_exact_weights.items():
            disease_lower = disease_name.lower()
            
            # 查询包含疾病名
            if disease_lower in query_clean and len(disease_lower) >= 3:
                if disease_lower in source:
                    bonus += weight * 0.5  # 中高权重：标题部分匹配
                elif disease_lower in doc_lower:
                    bonus += weight * 0.3  # 中等权重：内容部分匹配
                    
        # 3. 同义词精确匹配 - 第三优先级
        for main_disease, synonyms in self.tcm_synonyms.items():
            if main_disease in self.disease_exact_weights:
                main_weight = self.disease_exact_weights[main_disease]
                
                for synonym in synonyms:
                    synonym_lower = synonym.lower()
                    
                    # 同义词精确匹配
                    if synonym_lower == query_clean:
                        if synonym_lower in source or main_disease.lower() in source:
                            bonus += main_weight * 0.4  # 同义词标题匹配
                        elif synonym_lower in doc_lower:
                            bonus += main_weight * 0.25  # 同义词内容匹配
                            
        # 4. 限制最大加成，避免分数爆炸
        return min(bonus, 15.0)  # 最大加成15.0
        
    def _remove_duplicates(self, results: List[Dict], threshold: float = 0.85) -> List[Dict]:
        """去除重复和高度相似的结果"""
        if len(results) <= 1:
            return results
            
        filtered_results = [results[0]]  # 保留第一个结果
        
        for current in results[1:]:
            is_duplicate = False
            current_doc = current['document']
            
            for existing in filtered_results:
                existing_doc = existing['document']
                
                # 计算文档相似度
                similarity = self._calculate_document_similarity(current_doc, existing_doc)
                
                if similarity > threshold:
                    is_duplicate = True
                    # 如果当前结果分数更高，替换现有结果
                    if current['hybrid_score'] > existing['hybrid_score']:
                        filtered_results.remove(existing)
                        filtered_results.append(current)
                    break
                    
            if not is_duplicate:
                filtered_results.append(current)
                
        return filtered_results
        
    def _calculate_document_similarity(self, doc1: str, doc2: str) -> float:
        """计算两个文档的相似度"""
        # 简单的字符串相似度计算
        if len(doc1) == 0 or len(doc2) == 0:
            return 0.0
            
        # 计算字符重叠度
        set1 = set(doc1)
        set2 = set(doc2)
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        if union == 0:
            return 0.0
            
        return intersection / union