# TCM轻量级向量数据库

## 数据库信息
- 创建时间: 2025-08-20T14:53:22.241648
- 模型类型: TF-IDF
- 处方总数: 3267
- 向量维度: 5000
- 词汇表大小: 5000
- 病症数量: 58
- 药物数量: 3980

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
    print(f"{i+1}. 相似度: {similarities[idx]:.3f}")
    print(f"   {prescriptions[idx]['display_text']}")
```

## 优势
1. 完全本地化，无需网络连接
2. 轻量级，文件大小适中
3. 快速搜索，毫秒级响应
4. 支持中文分词和语义匹配
5. 易于集成到现有系统
