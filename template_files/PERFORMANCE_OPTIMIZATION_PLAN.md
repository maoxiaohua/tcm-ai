# TCM-AI 页面加载性能优化方案

## 📊 当前性能问题

**加载时间**: ~10秒
**主要瓶颈**:
1. ❌ 15个JS文件串行加载（数千行代码）
2. ❌ marked.js CDN超时等待5秒
3. ❌ 数据库历史同步阻塞初始化
4. ❌ 多个管理器重复初始化

## 🎯 优化目标

- **首屏加载**: < 2秒
- **可交互时间**: < 3秒
- **完全加载**: < 5秒

## 💡 优化方案

### 方案1: 关键路径优化（立即实施）⭐

#### 1.1 移除marked.js CDN依赖
**问题**: CDN超时浪费5秒
**方案**: 直接使用本地降级方案，不等待CDN

```html
<!-- 修改前 -->
<script>
    const timeout = setTimeout(function() {
        if (!window.marked) {
            initializeMarkedFallback();
        }
    }, 5000);  // ❌ 浪费5秒

    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
</script>

<!-- 修改后 -->
<script>
    // 直接使用本地方案，不加载CDN
    window.marked = {
        parse: function(markdown) {
            return markdown
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>');
        }
    };
</script>
```

**预期提升**: -5秒

#### 1.2 JS文件异步加载
**问题**: 15个文件串行加载阻塞页面
**方案**: 核心文件同步，其他文件异步

```html
<!-- 核心文件：同步加载 -->
<script src="/static/js/auth_manager.js"></script>
<script src="/static/js/smart_workflow_core.js"></script>
<script src="/static/js/smart_workflow_init.js"></script>

<!-- 非关键文件：异步加载 -->
<script src="/static/js/conversation_manager.js" async></script>
<script src="/static/js/auto_sync_manager.js" async></script>
<script src="/static/js/simple_prescription_manager.js" async></script>
<!-- 其他文件... -->
```

**预期提升**: -3秒

#### 1.3 延迟数据库同步
**问题**: 初始化时同步6条历史记录阻塞页面
**方案**: 页面加载后3秒再同步

```javascript
// 修改前：立即同步
syncHistoryFromDatabase();

// 修改后：延迟同步
setTimeout(() => {
    syncHistoryFromDatabase();
}, 3000);  // 3秒后再同步
```

**预期提升**: -1秒

### 方案2: 代码合并优化（中期）

#### 2.1 合并JS文件
将15个文件合并为3个：
```
core.bundle.js       - 核心功能（500KB）
features.bundle.js   - 功能模块（300KB）
utils.bundle.js      - 工具函数（200KB）
```

使用webpack/rollup打包工具

**预期提升**: -2秒（减少HTTP请求）

#### 2.2 代码压缩
使用terser压缩JS代码

**预期提升**: -0.5秒（减少传输大小）

### 方案3: 懒加载优化（中期）

#### 3.1 按需加载管理器
```javascript
// 只在需要时加载
if (userNeedsPrescription) {
    await import('./simple_prescription_manager.js');
}

if (userNeedsHistory) {
    await import('./smart_workflow_history.js');
}
```

#### 3.2 图片懒加载
```html
<img loading="lazy" src="...">
```

### 方案4: 缓存优化（长期）

#### 4.1 Service Worker
使用Service Worker缓存JS/CSS文件

#### 4.2 CDN加速
将静态资源部署到CDN

## 📋 立即可执行的快速优化

### 优化1: 移除marked.js CDN等待 ⭐ 最快见效

**文件**: `/opt/tcm-ai/static/index_smart_workflow.html`

```javascript
// 第46-92行，替换为：
<script>
    // 直接使用简化版Markdown解析器，不等待CDN
    window.marked = {
        parse: function(markdown) {
            if (!markdown) return '';
            return markdown
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`(.*?)`/g, '<code>$1</code>')
                .replace(/\n\n/g, '</p><p>')
                .replace(/\n/g, '<br>')
                .replace(/^/, '<p>')
                .replace(/$/, '</p>');
        }
    };
</script>
```

### 优化2: 延迟非关键数据同步

**文件**: `/opt/tcm-ai/static/js/smart_workflow_init.js`

在初始化完成后添加：
```javascript
// 延迟执行非关键任务
setTimeout(() => {
    // 数据库同步
    if (typeof syncHistoryFromDatabase === 'function') {
        syncHistoryFromDatabase();
    }

    // 处方状态检查
    if (typeof checkPrescriptionStatus === 'function') {
        checkPrescriptionStatus();
    }
}, 2000); // 2秒后执行
```

### 优化3: 关键JS文件预加载

**文件**: `/opt/tcm-ai/static/index_smart_workflow.html`

在`<head>`中添加：
```html
<link rel="preload" href="/static/js/smart_workflow_core.js" as="script">
<link rel="preload" href="/static/js/smart_workflow_init.js" as="script">
<link rel="preload" href="/static/js/auth_manager.js" as="script">
```

### 优化4: 字体异步加载（已有但可优化）

移除Google Fonts，使用系统字体：
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Helvetica, Arial, sans-serif;
```

## 📊 预期效果

| 优化项 | 当前 | 优化后 | 提升 |
|-------|------|--------|------|
| marked.js加载 | 5秒 | 0秒 | -5秒 |
| JS文件加载 | 3秒 | 1.5秒 | -1.5秒 |
| 数据库同步 | 1秒 | 0秒* | -1秒 |
| 其他初始化 | 1秒 | 0.5秒 | -0.5秒 |
| **总计** | **10秒** | **2-3秒** | **-7-8秒** |

*延迟到后台执行

## 🔧 实施优先级

### P0 - 立即执行（今天）
- [ ] 移除marked.js CDN等待（-5秒）
- [ ] 延迟数据库同步（-1秒）

### P1 - 本周执行
- [ ] 添加关键文件preload
- [ ] 部分文件改为async加载
- [ ] 移除Google Fonts

### P2 - 下周执行
- [ ] 合并JS文件
- [ ] 代码压缩

### P3 - 长期优化
- [ ] Service Worker
- [ ] CDN部署

## 🧪 性能监控

使用Chrome DevTools Performance面板：
1. 打开DevTools → Performance
2. 点击Record → 刷新页面 → Stop
3. 查看：
   - **FCP** (First Contentful Paint): 首次内容绘制
   - **LCP** (Largest Contentful Paint): 最大内容绘制
   - **TTI** (Time to Interactive): 可交互时间

**目标**:
- FCP < 1秒
- LCP < 2.5秒
- TTI < 3秒

---

**创建时间**: 2025-11-27
**优先级**: P0 - 紧急
**预期提升**: 70-80%加载速度提升
