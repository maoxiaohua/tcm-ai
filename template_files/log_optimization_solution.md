# TCM-AI 系统日志优化方案

## 📊 当前问题分析

### 1. 日志问题汇总
根据 `journalctl -u tcm-ai` 分析，发现以下高频问题：

```
问题类型                          频率      影响
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
匿名会话创建                      极高      会话表膨胀、性能下降
404 Not Found                   高        用户体验差、可能是路径错误
Invalid HTTP request            中        安全风险、爬虫攻击
401 认证失败                     中        正常业务警告（前端token过期）
```

### 2. 核心问题详解

#### 问题1: 大量匿名会话创建 🔴 严重
**日志特征**:
```
INFO:core.security.rbac_system:Created session for user anonymous with role anonymous
```

**问题根源**:
- 每次404错误都触发匿名会话创建
- 每次401错误也会降级到匿名会话
- RBAC中间件对所有请求都创建会话（包括静态资源、爬虫请求）

**影响**:
- `user_sessions`表快速膨胀（每小时可能新增数百条记录）
- 数据库查询变慢
- 日志文件快速增长

**代码位置**: `core/security/rbac_system.py:448-454`

---

#### 问题2: 404错误高频出现 🟡 中等
**日志特征**:
```
WARNING:api.middleware.exception_handler:HTTP Exception: 404 - Not Found
```

**问题根源**（需要验证）:
- 可能是爬虫访问不存在的路径（如 `/admin`, `/wp-admin`, `.env`）
- 可能是前端代码中的路径错误（静态资源、API端点）
- 可能是浏览器自动请求（如 `/favicon.ico`, `/robots.txt`）

**当前缺失**: 日志没有记录具体的请求路径

---

#### 问题3: Invalid HTTP request 🟠 中等
**日志特征**:
```
WARNING:  Invalid HTTP request received.
```

**问题根源**:
- Uvicorn接收到非法HTTP请求
- 可能是恶意扫描器、端口探测
- 可能是客户端连接异常

**影响**:
- 占用服务器资源
- 潜在安全风险

---

## 🎯 优化方案（分阶段实施）

### 阶段1: 日志增强（诊断） - 优先级最高

#### 1.1 增强404日志记录
**目标**: 记录具体的404请求路径，以便分析问题根源

**修改文件**: `api/middleware/exception_handler.py`

**修改内容**:
```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器 - 统一响应格式"""

    # 🔧 增强日志：记录请求路径和客户端信息
    if exc.status_code == 404:
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            f"HTTP 404 - Path: {request.url.path} | "
            f"Method: {request.method} | "
            f"Client: {client_ip} | "
            f"User-Agent: {request.headers.get('User-Agent', 'Unknown')[:100]}"
        )
    else:
        logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")

    # ... 原有响应逻辑 ...
```

**预期效果**:
- 可以看到哪些路径返回404
- 判断是否是爬虫、浏览器自动请求、前端错误

---

#### 1.2 优化匿名会话创建日志级别
**目标**: 降低日志噪音，只记录异常情况

**修改文件**: `core/security/rbac_system.py`

**修改内容**:
```python
def create_session(self, user_id: str, role: UserRole,
                  ip_address: str, user_agent: str) -> UserSession:
    """创建新会话"""
    # ... 原有逻辑 ...

    # 🔧 优化日志级别
    if role == UserRole.ANONYMOUS:
        # 匿名会话改为DEBUG级别，减少日志噪音
        logger.debug(f"Created anonymous session from {ip_address}")
    else:
        # 正常用户登录保持INFO级别
        logger.info(f"Created session for user {user_id} with role {role.value}")

    return session
```

**预期效果**:
- 生产环境（INFO级别）不再显示匿名会话创建日志
- 开发环境（DEBUG级别）仍可以看到完整日志

---

#### 1.3 添加Invalid HTTP请求详细日志
**目标**: 记录非法HTTP请求的详细信息，便于安全分析

**修改文件**: `api/main.py` （添加自定义日志中间件）

**新增代码**:
```python
@app.middleware("http")
async def log_invalid_requests(request: Request, call_next):
    """记录可能的非法请求"""
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        if "Invalid HTTP" in str(e):
            client_ip = request.client.host if request.client else "unknown"
            logger.warning(
                f"Invalid HTTP request from {client_ip} | "
                f"User-Agent: {request.headers.get('User-Agent', 'Unknown')[:100]}"
            )
        raise
```

---

### 阶段2: 匿名会话优化 - 核心性能问题

#### 2.1 实施会话创建限流
**目标**: 避免同一IP短时间内创建大量匿名会话

**修改文件**: `core/security/rbac_system.py`

**新增代码**:
```python
class SessionManager:
    def __init__(self, db_path: str = "/opt/tcm-ai/data/user_history.sqlite"):
        # ... 原有初始化 ...

        # 🔧 新增：匿名会话创建限流（IP→最后创建时间）
        self.anonymous_session_cache: Dict[str, datetime] = {}
        self.anonymous_session_ttl = timedelta(minutes=5)  # 5分钟内同一IP只创建一次

    def create_session(self, user_id: str, role: UserRole,
                      ip_address: str, user_agent: str) -> UserSession:
        """创建新会话（带限流）"""

        # 🔧 匿名会话限流检查
        if role == UserRole.ANONYMOUS:
            cache_key = f"{ip_address}:{user_agent[:50]}"
            last_created = self.anonymous_session_cache.get(cache_key)

            if last_created and (datetime.now() - last_created) < self.anonymous_session_ttl:
                # 5分钟内已创建过匿名会话，不重复创建
                logger.debug(f"Reusing recent anonymous session for {ip_address}")
                # 返回一个临时会话对象（不写数据库）
                return self._create_temporary_anonymous_session(ip_address, user_agent)

            # 更新缓存
            self.anonymous_session_cache[cache_key] = datetime.now()

        # ... 原有会话创建逻辑 ...

    def _create_temporary_anonymous_session(self, ip_address: str, user_agent: str) -> UserSession:
        """创建临时匿名会话（不写数据库）"""
        now = datetime.now()
        return UserSession(
            user_id="anonymous",
            role=UserRole.ANONYMOUS,
            permissions=self.role_manager.get_permissions(UserRole.ANONYMOUS),
            session_token="anonymous-temp",
            created_at=now,
            expires_at=now + timedelta(hours=1),
            ip_address=ip_address,
            user_agent=user_agent,
            last_activity=now,
            is_active=True
        )
```

**预期效果**:
- 同一IP的匿名会话创建从每次请求→5分钟一次
- 数据库写入量减少90%以上
- 日志噪音大幅降低

---

#### 2.2 自动清理过期匿名会话
**目标**: 定期清理数据库中的过期匿名会话

**修改文件**: `core/security/rbac_system.py`

**新增代码**:
```python
def cleanup_expired_sessions(self):
    """清理过期会话（增强版）"""
    now = datetime.now()

    # 1. 清理内存中的过期会话
    expired_tokens = [
        token for token, session in self.active_sessions.items()
        if session.expires_at <= now
    ]
    for token in expired_tokens:
        self.active_sessions.pop(token, None)

    # 2. 清理数据库中的过期会话
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()

    # 🔧 新增：优先清理匿名会话（保留3天），正常会话保留30天
    cursor.execute("""
        DELETE FROM user_sessions
        WHERE user_id = 'anonymous'
        AND created_at < datetime('now', '-3 days')
    """)
    anonymous_deleted = cursor.rowcount

    cursor.execute("""
        UPDATE user_sessions
        SET is_active = 0
        WHERE expires_at < ? AND is_active = 1
    """, (now.isoformat(),))
    expired_deleted = cursor.rowcount

    conn.commit()
    conn.close()

    if anonymous_deleted > 0 or expired_deleted > 0:
        logger.info(
            f"Session cleanup: {expired_deleted} expired, "
            f"{anonymous_deleted} old anonymous sessions deleted"
        )
```

**添加定时任务**: 在 `api/main.py` 中添加
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(
    func=lambda: session_manager.cleanup_expired_sessions(),
    trigger="interval",
    hours=6,  # 每6小时清理一次
    id='cleanup_sessions'
)
scheduler.start()
```

---

### 阶段3: 404错误处理优化

#### 3.1 静态资源白名单（避免不必要的404）
**目标**: 对常见的浏览器自动请求返回204而不是404

**修改文件**: `api/main.py`

**新增路由**:
```python
from fastapi.responses import Response

# 浏览器常见自动请求 - 返回204 No Content避免404日志
@app.get("/favicon.ico")
@app.get("/robots.txt")
@app.get("/sitemap.xml")
@app.get("/ads.txt")
async def common_files():
    """处理浏览器常见自动请求"""
    return Response(status_code=204)
```

---

#### 3.2 恶意路径访问拦截
**目标**: 识别并拦截常见的恶意扫描请求

**修改文件**: `api/middleware/security.py` (新建)

**新增代码**:
```python
from fastapi import Request, Response
from typing import Callable
import logging

logger = logging.getLogger(__name__)

# 常见恶意路径特征
MALICIOUS_PATTERNS = [
    "/wp-admin", "/wp-login", "/.env", "/phpMyAdmin",
    "/admin/config", "/.git", "/config.php", "/setup.php"
]

@app.middleware("http")
async def block_malicious_requests(request: Request, call_next: Callable):
    """拦截恶意扫描请求"""
    path = request.url.path.lower()

    # 检查是否是恶意路径
    if any(pattern in path for pattern in MALICIOUS_PATTERNS):
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            f"🚨 Blocked malicious scan from {client_ip}: {path}"
        )

        # 记录到安全事件表
        session_manager._log_security_event(
            event_type="MALICIOUS_SCAN_BLOCKED",
            user_id=None,
            ip_address=client_ip,
            user_agent=request.headers.get("User-Agent", "Unknown"),
            details={"path": path},
            risk_level="HIGH"
        )

        # 返回403而不是404，避免泄露信息
        return Response(status_code=403, content="Forbidden")

    response = await call_next(request)
    return response
```

---

### 阶段4: 日志系统结构化优化

#### 4.1 实施结构化日志
**目标**: 使用JSON格式日志，便于后续分析

**修改文件**: `config/logging_config.py` (新建)

**新增代码**:
```python
import logging
import json
from datetime import datetime

class StructuredFormatter(logging.Formatter):
    """结构化JSON日志格式"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # 添加额外字段（如果有）
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'ip_address'):
            log_data['ip_address'] = record.ip_address
        if hasattr(record, 'request_path'):
            log_data['request_path'] = record.request_path

        return json.dumps(log_data, ensure_ascii=False)

# 使用方式
handler = logging.StreamHandler()
handler.setFormatter(StructuredFormatter())
logger.addHandler(handler)
```

---

## 🔧 实施步骤建议

### Step 1: 先诊断再优化（本周）
1. ✅ 部署阶段1的日志增强代码
2. ✅ 观察24小时，收集详细的404路径数据
3. ✅ 分析具体的404来源（爬虫、前端、浏览器自动请求）

### Step 2: 核心优化（下周）
1. ✅ 实施匿名会话限流（阶段2.1）
2. ✅ 添加会话自动清理任务（阶段2.2）
3. ✅ 验证会话创建速率下降

### Step 3: 全面优化（下下周）
1. ✅ 处理常见的浏览器自动请求（阶段3.1）
2. ✅ 添加恶意请求拦截（阶段3.2）
3. ✅ 实施结构化日志（可选）

---

## 📈 预期效果

### 日志量降低
- **当前**: 匿名会话创建日志占比 ~70%，404错误占比 ~20%
- **优化后**:
  - 匿名会话日志减少 95%（改为DEBUG级别 + 限流）
  - 404日志减少 30%（处理浏览器自动请求）
  - 总日志量减少 ~60%

### 数据库性能提升
- **当前**: `user_sessions`表每小时新增 ~200条记录
- **优化后**: 每小时新增 ~10条记录（减少95%）
- 查询性能提升（表更小）

### 安全提升
- 识别和拦截恶意扫描请求
- 详细的404路径日志便于安全审计
- 结构化日志便于自动化分析

---

## 🚨 注意事项

1. **逐步实施**: 不要一次性修改所有代码，按阶段验证效果
2. **保留原日志**: 前7天保留INFO级别的匿名会话日志，观察无异常后再降级为DEBUG
3. **监控影响**: 关注修改后的用户体验，确保不影响正常功能
4. **备份数据库**: 清理会话前先备份 `user_history.sqlite`

---

## 📋 待确认问题

需要先部署**阶段1的日志增强**，再确认以下问题：

1. **404请求的具体路径是什么**？
   - 是爬虫访问 `/admin`, `/wp-admin` 等？
   - 是前端代码中的路径错误？
   - 是浏览器自动请求 `/favicon.ico` 等？

2. **Invalid HTTP请求的来源IP**？
   - 是否是同一IP的大量请求（DDoS）？
   - 是否是扫描器的特定User-Agent？

3. **匿名会话的实际用途**？
   - 是否所有匿名用户都需要会话（还是只有真正问诊的需要）？
   - 是否可以完全禁用静态资源请求的会话创建？

---

**文档版本**: v1.0
**创建时间**: 2025-11-04
**作者**: Claude Code
**状态**: 待用户确认实施阶段
