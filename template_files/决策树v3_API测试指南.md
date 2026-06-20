# 决策树v3.0 API测试指南

## 快速测试脚本

### 1. 测试列表查询

```bash
curl -X POST http://localhost:8000/api/decision-tree-data/list \
  -H "Content-Type: application/json" \
  -d '{
    "doctor_id": "zhang_zhongjing",
    "page": 1,
    "page_size": 10
  }' | python3 -m json.tool
```

**预期响应**:
```json
{
    "success": true,
    "message": "查询成功",
    "data": {
        "total": 0,
        "page": 1,
        "page_size": 10,
        "items": []
    }
}
```

### 2. 测试从文本保存

```bash
curl -X POST http://localhost:8000/api/decision-tree-data/save-from-text \
  -H "Content-Type: application/json" \
  -d '{
    "text_content": "【疾病】风寒感冒\n【主症】恶寒发热（重）、头痛（中）\n【兼症】鼻塞、流清涕\n【舌象】舌淡红，苔薄白\n【脉象】脉浮紧\n【证候】风寒表证\n【处方】麻黄汤\n【方剂】麻黄9克(君药) + 桂枝6克(臣药) + 杏仁6克(佐药) + 甘草3克(使药)",
    "doctor_id": "zhang_zhongjing"
  }' | python3 -m json.tool
```

**预期响应**:
```json
{
    "success": true,
    "message": "新建决策记录成功",
    "data": {
        "id": "decision_xxxxxxxx",
        "structured_content": {...},
        "text_format": "【疾病】风寒感冒...",
        "tree_structure": {"nodes": [...], "connections": [...]},
        "disease_name": "风寒感冒"
    }
}
```

### 3. 测试获取数据

```bash
# 先保存获取ID，然后查询
DECISION_ID="decision_xxxxxxxx"  # 替换为实际ID

curl -X GET "http://localhost:8000/api/decision-tree-data/${DECISION_ID}?doctor_id=zhang_zhongjing" \
  -H "Content-Type: application/json" | python3 -m json.tool
```

### 4. 测试AI生成（需要API KEY）

```bash
curl -X POST http://localhost:8000/api/decision-tree-data/generate \
  -H "Content-Type: application/json" \
  -d '{
    "natural_language": "患者出现恶寒发热，头痛身痛，无汗而喘，舌苔薄白，脉浮紧，请生成诊疗决策。",
    "doctor_id": "zhang_zhongjing"
  }' | python3 -m json.tool
```

### 5. 测试历史版本

```bash
# 获取历史列表
curl -X GET "http://localhost:8000/api/decision-tree-data/${DECISION_ID}/history?doctor_id=zhang_zhongjing" \
  -H "Content-Type: application/json" | python3 -m json.tool

# 获取指定版本
curl -X GET "http://localhost:8000/api/decision-tree-data/${DECISION_ID}/history/1?doctor_id=zhang_zhongjing" \
  -H "Content-Type: application/json" | python3 -m json.tool
```

---

## 完整测试流程

### 测试脚本

创建文件 `/opt/tcm-ai/scripts/test_decision_tree_api.sh`:

```bash
#!/bin/bash

echo "==================================="
echo "决策树v3.0 API完整测试"
echo "==================================="

BASE_URL="http://localhost:8000"
DOCTOR_ID="zhang_zhongjing"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function test_api() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4

    echo ""
    echo "测试: $name"
    echo "-----------------------------------"

    if [ "$method" == "GET" ]; then
        response=$(curl -s "$BASE_URL$endpoint")
    else
        response=$(curl -s -X $method "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi

    if echo "$response" | grep -q '"success":true'; then
        echo -e "${GREEN}✅ 通过${NC}"
    else
        echo -e "${RED}❌ 失败${NC}"
    fi

    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
}

# 1. 测试列表查询（初始为空）
test_api "列表查询" "POST" "/api/decision-tree-data/list" \
'{
    "doctor_id": "'$DOCTOR_ID'",
    "page": 1,
    "page_size": 10
}'

# 2. 测试从文本保存
echo ""
echo "保存新的决策记录..."
save_response=$(curl -s -X POST "$BASE_URL/api/decision-tree-data/save-from-text" \
    -H "Content-Type: application/json" \
    -d '{
    "text_content": "【疾病】风寒感冒\n【主症】恶寒发热（重）、头痛（中）\n【兼症】鼻塞、流清涕\n【舌象】舌淡红，苔薄白\n【脉象】脉浮紧\n【证候】风寒表证\n【处方】麻黄汤\n【方剂】麻黄9克(君药) + 桂枝6克(臣药) + 杏仁6克(佐药) + 甘草3克(使药)",
    "doctor_id": "'$DOCTOR_ID'"
}')

DECISION_ID=$(echo "$save_response" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null)

if [ -n "$DECISION_ID" ]; then
    echo -e "${GREEN}✅ 保存成功，ID: $DECISION_ID${NC}"
    echo "$save_response" | python3 -m json.tool

    # 3. 测试获取数据
    test_api "获取决策数据" "GET" "/api/decision-tree-data/$DECISION_ID?doctor_id=$DOCTOR_ID"

    # 4. 测试列表查询（应该有1条记录）
    test_api "列表查询（应有记录）" "POST" "/api/decision-tree-data/list" \
    '{
        "doctor_id": "'$DOCTOR_ID'",
        "page": 1,
        "page_size": 10
    }'

    # 5. 测试历史版本
    test_api "获取历史版本列表" "GET" "/api/decision-tree-data/$DECISION_ID/history?doctor_id=$DOCTOR_ID"

    # 6. 测试删除
    test_api "软删除决策记录" "DELETE" "/api/decision-tree-data/$DECISION_ID?doctor_id=$DOCTOR_ID"

    # 7. 测试列表查询（应该为空）
    test_api "列表查询（删除后应为空）" "POST" "/api/decision-tree-data/list" \
    '{
        "doctor_id": "'$DOCTOR_ID'",
        "page": 1,
        "page_size": 10
    }'
else
    echo -e "${RED}❌ 保存失败${NC}"
    echo "$save_response"
fi

echo ""
echo "==================================="
echo "测试完成"
echo "==================================="
```

### 运行测试

```bash
chmod +x /opt/tcm-ai/scripts/test_decision_tree_api.sh
/opt/tcm-ai/scripts/test_decision_tree_api.sh
```

---

## 验证数据转换

### Python脚本验证

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/tcm-ai')

from services.decision_tree_data_service import DecisionTreeDataService

# 初始化服务
service = DecisionTreeDataService()

# 测试文本
text = """【疾病】风寒感冒
【主症】恶寒发热（重）、头痛（中）、身痛（中）
【兼症】鼻塞、流清涕、咳嗽
【舌象】舌淡红，苔薄白
【脉象】脉浮紧
【证候】风寒表证
【处方】麻黄汤
【方剂】麻黄9克(君药) + 桂枝6克(臣药) + 杏仁6克(佐药) + 甘草3克(使药)"""

print("原始文本:")
print(text)
print("\n" + "="*50 + "\n")

# 转换为结构化数据
structured = service.text_to_structured(text, "zhang_zhongjing")
print("结构化数据:")
print(f"疾病: {structured['disease']['name']}")
print(f"主症数量: {len(structured['diagnosis']['main_symptoms'])}")
print(f"兼症数量: {len(structured['diagnosis']['secondary_symptoms'])}")
print(f"证候: {structured['syndrome']['name']}")
print(f"处方: {structured['prescriptions'][0]['name']}")
print("\n" + "="*50 + "\n")

# 转换回文本
text_back = service.structured_to_text(structured)
print("转换回的文本:")
print(text_back)
print("\n" + "="*50 + "\n")

# 转换为树形结构
tree = service.structured_to_tree(structured)
print("树形结构:")
print(f"节点数量: {len(tree['nodes'])}")
print(f"连接数量: {len(tree['connections'])}")
print("节点类型:", [node['type'] for node in tree['nodes']])
print("\n" + "="*50 + "\n")

# 往返转换
structured2 = service.tree_to_structured(tree, "zhang_zhongjing")
print("往返转换后:")
print(f"疾病: {structured2['disease']['name']}")
print(f"证候: {structured2['syndrome']['name']}")

print("\n✅ 所有转换测试完成！")
```

保存为 `/opt/tcm-ai/scripts/test_data_conversion.py` 并运行:

```bash
python3 /opt/tcm-ai/scripts/test_data_conversion.py
```

---

## 预期结果

### 成功标志

1. ✅ 所有API返回 `"success": true`
2. ✅ 保存后能正确获取数据
3. ✅ 三种格式数据都存在且格式正确
4. ✅ 标准库数据已关联（疾病、症状、处方有ID）
5. ✅ 树形结构节点和连接关系正确
6. ✅ 往返转换数据不丢失

### 常见问题

**问题1: 服务未启动**
```bash
sudo service tcm-ai status
sudo service tcm-ai start
```

**问题2: API返回404**
- 检查路由是否已注册
- 检查main.py是否包含decision_tree_data_router

**问题3: 数据库错误**
- 检查数据库文件权限
- 验证migrations已执行

**问题4: AI生成失败**
- 检查DASHSCOPE_API_KEY环境变量
- 验证API KEY有效性

---

## 数据库验证

```bash
# 查看数据库表
sqlite3 /opt/tcm-ai/data/user_history.sqlite "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'clinical%' OR name LIKE 'tcm%';"

# 查看决策记录
sqlite3 /opt/tcm-ai/data/user_history.sqlite "SELECT id, disease_name, version, created_at FROM clinical_decision_data LIMIT 10;"

# 查看标准库数据
sqlite3 /opt/tcm-ai/data/user_history.sqlite "SELECT id, name FROM tcm_diseases_standard;"
sqlite3 /opt/tcm-ai/data/user_history.sqlite "SELECT id, name FROM tcm_prescriptions_standard;"
```

---

## 性能测试

```bash
# 测试响应时间
time curl -s -X POST http://localhost:8000/api/decision-tree-data/list \
  -H "Content-Type: application/json" \
  -d '{"doctor_id":"zhang_zhongjing","page":1,"page_size":10}' > /dev/null

# 预期: < 100ms
```

---

**文档版本**: v1.0
**更新日期**: 2025-10-31
