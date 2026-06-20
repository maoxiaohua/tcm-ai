# 统一账户管理系统实施方案

## 📋 项目概览

**项目名称**: TCM-AI统一账户管理系统升级  
**项目目标**: 解决现有账户管理混乱问题，建立企业级统一身份管理系统  
**预期收益**: 用户跨设备数据同步、统一权限管理、安全审计追踪  
**实施周期**: 2-3周  
**风险等级**: 中等（涉及核心数据迁移）

## 🎯 **解决的核心问题**

### 现有系统问题
1. **账户身份混乱**: 硬编码账户、用户ID不统一、跨设备数据割裂
2. **权限管理分散**: 权限检查逻辑分散、缺乏统一RBAC模型
3. **会话管理混乱**: 多套会话系统并存、过期策略不一致
4. **数据孤岛**: 用户数据分散存储、缺乏统一同步机制
5. **安全隐患**: 硬编码密码、缺乏审计日志、风险评估缺失

### 新系统优势
1. **统一身份**: 全局唯一用户ID、终身不变、跨平台一致
2. **企业级RBAC**: 动态权限分配、角色继承、权限审计
3. **智能会话**: 多设备管理、风险评估、自动过期清理
4. **数据同步**: 实时跨设备同步、冲突解决、版本控制
5. **安全审计**: 完整行为记录、风险评分、异常检测

## 🗺️ **实施路线图**

### 第一阶段：基础架构部署 (3-4天)

#### Day 1: 数据库架构升级
```bash
# 1. 备份现有数据库
sqlite3 /opt/tcm-ai/data/user_history.sqlite ".backup backup_pre_unified_$(date +%Y%m%d).db"

# 2. 运行统一账户系统迁移
sqlite3 /opt/tcm-ai/data/user_history.sqlite < /opt/tcm-ai/database/migrations/010_unified_account_system.sql

# 3. 验证表结构
sqlite3 /opt/tcm-ai/data/user_history.sqlite ".schema unified_users"
```

#### Day 2: 核心服务部署
```bash
# 1. 部署统一账户管理器
cp /opt/tcm-ai/core/unified_account/account_manager.py /opt/tcm-ai/core/unified_account/

# 2. 部署新API路由
cp /opt/tcm-ai/api/routes/unified_auth_routes.py /opt/tcm-ai/api/routes/

# 3. 更新主应用引入新路由
# 在 api/main.py 中添加:
# from api.routes.unified_auth_routes import router as unified_auth_router
# app.include_router(unified_auth_router)
```

#### Day 3-4: 数据迁移脚本
创建数据迁移工具，将现有用户数据迁移到新表结构

### 第二阶段：用户迁移与测试 (4-5天)

#### Day 5-7: 现有用户数据迁移
1. **硬编码账户迁移**: 将硬编码账户转换为数据库记录
2. **现有用户迁移**: 迁移 `users` 表数据到 `unified_users`
3. **权限数据初始化**: 根据现有角色分配新权限
4. **会话数据清理**: 清理并重新创建所有会话

#### Day 8-9: 向后兼容测试
1. **API兼容性**: 确保现有前端可以正常工作
2. **功能完整性**: 验证登录、权限、数据访问功能
3. **性能测试**: 确保新系统性能不低于现有系统

### 第三阶段：渐进式切换 (3-4天)

#### Day 10-12: 双系统并行
1. **路由切换**: 逐步将API调用切换到新系统
2. **数据同步**: 确保新旧系统数据一致
3. **监控告警**: 实时监控系统状态和错误

#### Day 13: 完全切换
1. **停用旧系统**: 停用旧的认证和会话管理
2. **清理冗余**: 删除或归档旧的认证相关代码
3. **最终验证**: 全面功能测试和性能验证

## 📊 **数据迁移策略**

### 用户数据迁移映射

```sql
-- 现有用户 -> 统一用户映射
INSERT INTO unified_users (
    global_user_id,
    username, 
    email,
    phone_number,
    display_name,
    password_hash,
    salt,
    account_status,
    created_at,
    last_login_at
)
SELECT 
    CASE 
        WHEN user_id LIKE 'patient_%' THEN 'usr_' || substr(user_id, 9)
        WHEN user_id LIKE 'doctor_%' THEN 'usr_' || substr(user_id, 8) 
        WHEN user_id LIKE 'admin_%' THEN 'usr_' || substr(user_id, 7)
        ELSE 'usr_' || strftime('%Y%m%d', 'now') || '_' || substr(user_id, 1, 6)
    END as global_user_id,
    COALESCE(username, 'user_' || substr(user_id, 1, 8)) as username,
    email,
    phone_number,
    COALESCE(nickname, display_name, username, 'User') as display_name,
    COALESCE(password_hash, 'temp_hash') as password_hash,
    COALESCE('temp_salt_' || substr(user_id, 1, 8)) as salt,
    CASE WHEN is_active = 1 THEN 'active' ELSE 'suspended' END as account_status,
    created_at,
    last_active as last_login_at
FROM users
WHERE user_id IS NOT NULL;
```

### 角色权限迁移

```sql
-- 角色迁移
INSERT INTO user_roles (user_id, role_name, is_primary, assigned_at)
SELECT 
    u.global_user_id,
    UPPER(COALESCE(old_u.role, 'PATIENT')) as role_name,
    true as is_primary,
    COALESCE(old_u.created_at, datetime('now')) as assigned_at
FROM unified_users u
JOIN users old_u ON u.username = old_u.username OR u.global_user_id LIKE '%' || substr(old_u.user_id, -6);
```

### 会话迁移

```sql
-- 清理所有旧会话，强制重新登录（最安全的方式）
UPDATE user_sessions SET is_active = 0 WHERE is_active = 1;
INSERT INTO security_audit_logs (
    log_id, event_type, event_category, event_result, 
    event_details, risk_level, event_timestamp
) VALUES (
    'migration_' || strftime('%Y%m%d%H%M%S', 'now'),
    'system_migration',
    'admin',
    'success',
    '{"action": "force_relogin", "reason": "unified_account_migration"}',
    'medium',
    datetime('now')
);
```

## 🔧 **分步骤实施指南**

### Step 1: 环境准备

```bash
# 1. 创建实施分支
cd /opt/tcm-ai
git checkout -b feature/unified-account-system
git add -A && git commit -m "🔄 修改前备份: 统一账户系统实施"

# 2. 安装必要依赖
pip install bcrypt passlib python-jose

# 3. 创建备份
cp -r /opt/tcm-ai/data /opt/tcm-ai/data_backup_$(date +%Y%m%d)
```

### Step 2: 数据库迁移

```bash
# 1. 执行数据库架构升级
sqlite3 /opt/tcm-ai/data/user_history.sqlite < /opt/tcm-ai/database/migrations/010_unified_account_system.sql

# 2. 验证新表结构
sqlite3 /opt/tcm-ai/data/user_history.sqlite "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'unified_%'"

# 3. 检查权限初始化
sqlite3 /opt/tcm-ai/data/user_history.sqlite "SELECT COUNT(*) FROM permissions"
sqlite3 /opt/tcm-ai/data/user_history.sqlite "SELECT COUNT(*) FROM role_permissions"
```

### Step 3: 服务集成

```python
# 在 api/main.py 中集成新路由
from api.routes.unified_auth_routes import router as unified_auth_router

# 添加到应用
app.include_router(unified_auth_router)

# 可选：添加向后兼容中间件
@app.middleware("http")
async def compatibility_middleware(request: Request, call_next):
    # 处理旧API到新API的路由映射
    if request.url.path.startswith("/api/auth/login"):
        # 重定向到新的登录接口
        pass
    response = await call_next(request)
    return response
```

### Step 4: 数据迁移执行

```python
# 创建迁移脚本 scripts/migrate_users.py
import sys
sys.path.append('/opt/tcm-ai')
from core.unified_account.account_manager import unified_account_manager, UserType
import sqlite3

def migrate_hardcoded_users():
    """迁移硬编码用户"""
    hardcoded_users = [
        {
            "username": "admin",
            "password": "admin123",
            "display_name": "系统管理员",
            "user_type": UserType.ADMIN
        },
        {
            "username": "doctor", 
            "password": "doctor123",
            "display_name": "测试医生",
            "user_type": UserType.DOCTOR
        },
        {
            "username": "patient",
            "password": "patient123", 
            "display_name": "测试患者",
            "user_type": UserType.PATIENT
        }
    ]
    
    for user_data in hardcoded_users:
        try:
            user = unified_account_manager.create_user(**user_data)
            print(f"✅ 迁移用户成功: {user.username}")
        except Exception as e:
            print(f"❌ 迁移用户失败: {user_data['username']} - {e}")

def migrate_existing_users():
    """迁移现有数据库用户"""
    # 实现现有用户迁移逻辑
    pass

if __name__ == "__main__":
    migrate_hardcoded_users()
    migrate_existing_users()
```

### Step 5: 前端适配

```javascript
// 更新前端认证逻辑
class UnifiedAuthService {
    constructor() {
        this.baseURL = '/api/v2/auth';
        this.legacyURL = '/api/auth';  // 向后兼容
    }
    
    async login(username, password) {
        try {
            // 优先使用新API
            const response = await fetch(`${this.baseURL}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.saveUserSession(data);
                return data;
            }
        } catch (error) {
            console.warn('新API调用失败，回退到旧API:', error);
            // 回退到旧API
            return this.legacyLogin(username, password);
        }
    }
    
    saveUserSession(authData) {
        if (authData.session) {
            localStorage.setItem('session_token', authData.session.session_id);
            localStorage.setItem('user_data', JSON.stringify(authData.user));
            localStorage.setItem('permissions', JSON.stringify(authData.permissions));
        }
    }
    
    async syncData(dataType, dataKey, content) {
        const response = await fetch(`${this.baseURL}/sync-data`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getSessionToken()}`
            },
            body: JSON.stringify({
                data_type: dataType,
                data_key: dataKey,
                data_content: content
            })
        });
        
        return response.json();
    }
    
    getSessionToken() {
        return localStorage.getItem('session_token');
    }
}

// 全局实例
window.authService = new UnifiedAuthService();
```

## 🚨 **风险控制与回滚方案**

### 风险识别
1. **数据丢失风险**: 迁移过程中数据损坏或丢失
2. **服务中断风险**: 迁移期间用户无法正常登录
3. **兼容性风险**: 现有前端功能异常
4. **性能风险**: 新系统性能不达预期

### 控制措施
1. **完整备份**: 多重备份策略，自动备份验证
2. **灰度发布**: 部分用户先行试用，逐步扩大范围
3. **监控告警**: 实时监控关键指标，异常自动告警
4. **快速回滚**: 一键回滚机制，5分钟内恢复

### 回滚方案

```bash
# 紧急回滚脚本 scripts/emergency_rollback.sh
#!/bin/bash

echo "🚨 执行紧急回滚..."

# 1. 停止服务
sudo systemctl stop tcm-ai

# 2. 恢复数据库
cp /opt/tcm-ai/data_backup_$(date +%Y%m%d)/user_history.sqlite /opt/tcm-ai/data/

# 3. 切换到备份分支
cd /opt/tcm-ai
git checkout master

# 4. 重启服务
sudo systemctl start tcm-ai

# 5. 验证服务状态
curl -f http://localhost:8000/api/auth/health || echo "❌ 服务未正常启动"

echo "✅ 回滚完成"
```

## 📈 **成功指标与验证**

### 功能指标
- [ ] 用户可以正常登录/注册
- [ ] 权限检查正确生效
- [ ] 跨设备数据同步正常
- [ ] 会话管理功能完整
- [ ] 安全审计日志完整

### 性能指标
- [ ] 登录响应时间 < 2秒
- [ ] API响应时间 < 500ms
- [ ] 数据库查询时间 < 100ms
- [ ] 并发用户支持 > 100

### 安全指标
- [ ] 密码哈希强度符合标准
- [ ] 会话安全机制有效
- [ ] 权限控制无泄露
- [ ] 审计日志完整性

## 📚 **培训与文档**

### 开发团队培训
1. **新架构介绍**: 统一账户系统设计原理
2. **API使用指南**: 新接口调用方法和最佳实践
3. **故障排查**: 常见问题诊断和解决方法

### 用户文档更新
1. **登录流程变更**: 新的登录界面和功能说明
2. **跨设备同步**: 数据同步功能使用指南
3. **安全设置**: 密码安全和会话管理

### 运维手册
1. **系统监控**: 关键指标监控配置
2. **备份策略**: 数据备份和恢复流程
3. **应急响应**: 故障处理和联系人信息

## 🔧 **运维和监控**

### 监控指标
```bash
# 系统健康监控
curl -s http://localhost:8000/api/v2/auth/health | jq '.status'

# 用户活跃度监控
sqlite3 /opt/tcm-ai/data/user_history.sqlite "
    SELECT COUNT(*) as active_users 
    FROM unified_sessions 
    WHERE session_status = 'active' 
    AND last_activity_at > datetime('now', '-1 hour')
"

# 安全事件监控
sqlite3 /opt/tcm-ai/data/user_history.sqlite "
    SELECT risk_level, COUNT(*) as count
    FROM security_audit_logs 
    WHERE event_timestamp > datetime('now', '-24 hours')
    GROUP BY risk_level
"
```

### 日志管理
```python
# 配置专门的账户管理日志
import logging

# 创建专用日志记录器
account_logger = logging.getLogger('tcm_ai.account_management')
account_logger.setLevel(logging.INFO)

# 配置日志处理器
handler = logging.FileHandler('/opt/tcm-ai/logs/account_management.log')
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
account_logger.addHandler(handler)
```

## 📅 **项目时间表**

| 阶段 | 任务 | 责任人 | 预计时间 | 状态 |
|------|------|--------|----------|------|
| 准备 | 架构设计和技术方案 | 架构师 | 1天 | ✅ 完成 |
| 开发 | 数据库迁移脚本 | 后端开发 | 1天 | 🔄 进行中 |
| 开发 | 账户管理器开发 | 后端开发 | 2天 | ✅ 完成 |
| 开发 | API接口开发 | 后端开发 | 2天 | ✅ 完成 |
| 测试 | 单元测试和集成测试 | 测试工程师 | 2天 | ⏳ 待开始 |
| 部署 | 生产环境部署 | 运维工程师 | 1天 | ⏳ 待开始 |
| 迁移 | 数据迁移和验证 | 全员 | 2天 | ⏳ 待开始 |
| 监控 | 系统监控和优化 | 运维工程师 | 持续 | ⏳ 待开始 |

## 🎉 **预期效果**

### 用户体验提升
1. **无缝登录**: 一次登录，全平台使用
2. **数据同步**: 设备间数据实时同步
3. **安全保障**: 多层安全防护，风险实时监控

### 系统管理优化
1. **统一管理**: 集中式用户和权限管理
2. **审计追踪**: 完整的操作历史记录
3. **扩展性强**: 支持未来业务扩展需求

### 开发效率提升
1. **标准化**: 统一的认证和权限接口
2. **维护简化**: 减少重复代码和逻辑
3. **测试完善**: 完整的测试覆盖和质量保证

---

**实施负责人**: TCM-AI开发团队  
**文档版本**: 1.0  
**最后更新**: 2025-09-20  

*本文档为TCM-AI统一账户管理系统的完整实施指南，包含详细的技术方案、风险控制和实施步骤。请严格按照本方案执行系统升级工作。*