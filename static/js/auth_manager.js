/**
 * TCM-AI 统一认证管理器
 * Unified Authentication Manager
 * 
 * 解决问题：
 * 1. localStorage键名不统一
 * 2. token传递机制混乱
 * 3. 用户状态管理分散
 * 
 * Version: 1.0
 * Author: TCM-AI Team
 * Date: 2025-09-24
 */

class AuthManager {
    constructor() {
        // 统一的存储键名
        this.KEYS = {
            USER: 'currentUser',           // 用户信息
            TOKEN: 'session_token',        // 会话token
            REMEMBER: 'rememberedUser'     // 记住的用户名
        };
        
        // Cookie配置
        this.COOKIE_CONFIG = {
            path: '/',
            maxAge: 86400,      // 24小时
            secure: true,
            sameSite: 'strict'
        };
    }
    
    /**
     * 保存登录状态
     * @param {Object} user - 用户信息对象
     * @param {string} token - 会话token
     * @param {boolean} remember - 是否记住用户
     */
    saveLoginState(user, token, remember = false) {
        try {
            // 保存用户信息到localStorage
            localStorage.setItem(this.KEYS.USER, JSON.stringify(user));
            localStorage.setItem(this.KEYS.TOKEN, token);
            
            // 保存token到cookie (用于后端验证)
            this.setCookie(this.KEYS.TOKEN, token, this.COOKIE_CONFIG);
            
            // 向后兼容：保存角色专用token
            if (user.primary_role) {
                localStorage.setItem(`${user.primary_role}Token`, token);
            }
            
            // 记住用户名
            if (remember && user.username) {
                localStorage.setItem(this.KEYS.REMEMBER, user.username);
            }
            
            console.log('✅ 登录状态已保存:', {
                username: user.username || user.display_name,
                role: user.primary_role,
                tokenLength: token.length
            });
            
            return true;
        } catch (error) {
            console.error('❌ 保存登录状态失败:', error);
            return false;
        }
    }
    
    /**
     * 获取当前登录用户
     * @returns {Object|null} 用户对象或null
     */
    getCurrentUser() {
        try {
            const userStr = localStorage.getItem(this.KEYS.USER);
            return userStr ? JSON.parse(userStr) : null;
        } catch (error) {
            console.error('❌ 获取用户信息失败:', error);
            return null;
        }
    }
    
    /**
     * 获取会话token
     * @returns {string|null} token或null
     */
    getToken() {
        // 优先从cookie读取
        const cookieToken = this.getCookie(this.KEYS.TOKEN);
        if (cookieToken) return cookieToken;
        
        // fallback到localStorage
        const localToken = localStorage.getItem(this.KEYS.TOKEN);
        if (localToken) return localToken;
        
        // 向后兼容：尝试角色专用token
        const roles = ['patient', 'doctor', 'admin'];
        for (const role of roles) {
            const roleToken = localStorage.getItem(`${role}Token`);
            if (roleToken) return roleToken;
        }
        
        return null;
    }
    
    /**
     * 检查是否已登录
     * @returns {boolean}
     */
    isLoggedIn() {
        return !!(this.getCurrentUser() && this.getToken());
    }
    
    /**
     * 清除登录状态
     */
    clearLoginState() {
        // 清除localStorage
        localStorage.removeItem(this.KEYS.USER);
        localStorage.removeItem(this.KEYS.TOKEN);
        localStorage.removeItem('patientToken');
        localStorage.removeItem('doctorToken');
        localStorage.removeItem('adminToken');
        
        // 清除cookie
        this.deleteCookie(this.KEYS.TOKEN);
        
        console.log('✅ 登录状态已清除');
    }
    
    /**
     * 验证token有效性
     * @param {string} token - 要验证的token
     * @returns {Promise<Object|null>} 用户对象或null
     */
    async verifyToken(token) {
        try {
            const response = await fetch('/api/v2/auth/profile', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.user) {
                    // 更新本地用户信息
                    this.saveLoginState(data.user, token);
                    return data.user;
                }
            }
            
            return null;
        } catch (error) {
            console.error('❌ Token验证失败:', error);
            return null;
        }
    }
    
    /**
     * 获取用户权限
     * @returns {Array} 权限列表
     */
    getUserPermissions() {
        const user = this.getCurrentUser();
        return user?.permissions || [];
    }
    
    /**
     * 检查是否有特定权限
     * @param {string} permission - 权限名称
     * @returns {boolean}
     */
    hasPermission(permission) {
        return this.getUserPermissions().includes(permission);
    }
    
    /**
     * 获取用户角色
     * @returns {string|null}
     */
    getUserRole() {
        const user = this.getCurrentUser();
        return user?.primary_role || null;
    }
    
    /**
     * 设置Cookie
     */
    setCookie(name, value, options = {}) {
        let cookieStr = `${name}=${value}`;
        
        if (options.path) cookieStr += `; path=${options.path}`;
        if (options.maxAge) cookieStr += `; max-age=${options.maxAge}`;
        if (options.secure) cookieStr += '; secure';
        if (options.sameSite) cookieStr += `; samesite=${options.sameSite}`;
        
        document.cookie = cookieStr;
    }
    
    /**
     * 获取Cookie
     */
    getCookie(name) {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [key, value] = cookie.trim().split('=');
            if (key === name) return value;
        }
        return null;
    }
    
    /**
     * 删除Cookie
     */
    deleteCookie(name) {
        document.cookie = `${name}=; path=/; max-age=0`;
    }
    
    /**
     * 获取记住的用户名
     */
    getRememberedUser() {
        return localStorage.getItem(this.KEYS.REMEMBER);
    }
}

// 创建全局单例
window.authManager = new AuthManager();

// 导出（用于模块化环境）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthManager;
}