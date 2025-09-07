# PDF导出问题详细分析报告

## 问题描述
处方检测模块导出的PDF内容显示为初始模板而非实际检测内容。

## 问题位置
文件：`/opt/tcm-ai/static/prescription_checker_v2.html`
函数：`generatePDFReportContent()` (行 1812-2062)
调用函数：`exportReport()` (行 1722-1809)

## 问题分析

### 1. 数据流问题
- 全局变量 `currentResult` 存储处方检测结果
- `exportReport()` 函数依赖 `currentResult` 的数据
- `generatePDFReportContent()` 使用模板数据而非实际数据

### 2. 数据结构不匹配
- API返回的数据结构与PDF模板期望的结构不一致
- 多模态API (`check_image_v2`) 和传统API的数据格式差异
- 模板硬编码了示例数据而非动态读取

### 3. 关键代码问题

```javascript
// 问题代码示例 (行 1837-1863)
if (result.ocr_result) {
    const confidence = Math.round((result.ocr_result.confidence || 0) * 100);
    // 这里使用固定模板数据，未正确读取 currentResult
}

// 问题代码示例 (行 1868-1894) 
if (result.prescription_check?.data || result.data) {
    const data = result.prescription_check?.data || result.data;
    // 数据路径可能不正确，导致读取失败
}
```

### 4. 兼容性问题
- 新的多模态API (`check_image_v2`) 返回格式与旧版不同
- PDF生成逻辑只适配了旧格式，未更新到新格式

## 修复方案

### 方案1：数据路径修复
1. 确保 `currentResult` 正确保存API返回数据
2. 修复 `generatePDFReportContent()` 中的数据读取路径
3. 兼容新旧两种API格式

### 方案2：模板逻辑重构
1. 移除硬编码的示例数据
2. 动态读取实际检测结果
3. 添加数据验证和错误处理

### 方案3：统一数据格式
1. 在前端统一处理不同API的返回格式
2. 确保 `currentResult` 格式一致
3. 简化PDF生成逻辑

## 建议采用方案
**推荐方案1+方案2的组合**：
- 保持API兼容性
- 修复数据读取逻辑
- 移除硬编码数据
- 添加调试日志

## 影响评估
- 功能影响：PDF导出功能完全失效
- 用户体验：用户无法获得有效的处方分析报告
- 业务影响：中等，影响系统完整性和专业性