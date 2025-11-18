/**
 * 用户认证模块
 * 提供用户登录、登出、注册、Token验证等功能
 * 依赖全局 authManager (auth_manager.js)
 */

import { StorageUtils } from '../utils/storage_utils.js';

export class UserAuth {
    constructor() {
        this.currentUser = null;
        this.userToken = null;
        this.authManager = window.authManager;
    }

    /**
     * 检查登录状态
     * @returns {Promise<boolean>} 是否已登录
     */
    async checkLoginStatus() {
        console.log('🔍 检查登录状态...');

        // 检查是否是访客模式
        const urlParams = new URLSearchParams(window.location.search);
        const isGuestMode = urlParams.get('mode') === 'guest';

        // 使用authManager检查登录状态
        const user = this.authManager.getCurrentUser();
        const token = this.authManager.getToken();

        console.log('📋 登录状态检查结果:', {
            isGuestMode,
            isLoggedIn: this.authManager.isLoggedIn(),
            hasUser: !!user,
            hasToken: !!token,
            username: user?.username || user?.display_name
        });

        if (this.authManager.isLoggedIn()) {
            // 已登录 - 直接使用
            this.currentUser = user;
            this.userToken = token;
            console.log('✅ 登录状态有效，用户:', user.username || user.display_name, '角色:', user.primary_role);
            return true;
        } else if (token) {
            // 有token但用户信息缺失 - 尝试从后端验证
            console.log('⚠️ 有token但缺少完整用户数据，尝试验证...');
            return await this.verifyTokenAndLoadUserData(token);
        } else if (isGuestMode) {
            // 访客模式 - 允许无登录访问
            console.log('ℹ️ 访客模式：允许无登录访问');
            return false;
        } else {
            // 非访客模式且无token - 需要登录
            console.log('❌ 未检测到有效登录状态');
            return false;
        }
    }

    /**
     * 验证Token并加载用户数据
     * @param {string} token - 认证Token
     * @returns {Promise<boolean>} 验证是否成功
     */
    async verifyTokenAndLoadUserData(token) {
        console.log('🔄 验证token并加载用户数据...');

        const user = await this.authManager.verifyToken(token);

        if (user) {
            this.currentUser = user;
            this.userToken = token;
            console.log('✅ 从后端验证成功，用户:', user.username || user.display_name);
            return true;
        } else {
            console.log('❌ Token验证失败，清除数据');
            this.authManager.clearLoginState();
            return false;
        }
    }

    /**
     * 获取当前用户
     * @returns {Object|null} 用户对象
     */
    getCurrentUser() {
        if (this.currentUser) {
            return this.currentUser;
        }

        // 尝试从authManager获取
        return this.authManager.getCurrentUser();
    }

    /**
     * 获取当前用户Token
     * @returns {string|null} Token
     */
    getToken() {
        if (this.userToken) {
            return this.userToken;
        }

        return this.authManager.getToken();
    }

    /**
     * 是否已登录
     * @returns {boolean}
     */
    isLoggedIn() {
        return this.authManager.isLoggedIn();
    }

    /**
     * 获取用户角色
     * @returns {string|null} 用户角色
     */
    getUserRole() {
        const user = this.getCurrentUser();
        return user?.primary_role || user?.role || null;
    }

    /**
     * 获取用户显示名称
     * @returns {string} 显示名称
     */
    getDisplayName() {
        const user = this.getCurrentUser();

        if (!user) {
            return '游客';
        }

        return user.display_name || user.username || user.name || user.phone || '用户';
    }

    /**
     * 获取用户头像首字母
     * @returns {string} 头像字符
     */
    getAvatarInitial() {
        const displayName = this.getDisplayName();
        return displayName.charAt(0).toUpperCase();
    }

    /**
     * 退出登录
     * @param {boolean} redirect - 是否重定向到登录页
     */
    logout(redirect = true) {
        console.log('🚪 用户退出登录');

        // 使用统一认证管理器清除登录状态
        this.authManager.clearLoginState();

        // 清除本地用户数据
        this.currentUser = null;
        this.userToken = null;

        // 清除用户相关的本地数据
        this.clearUserData();

        if (redirect) {
            // 退出后跳转到登录页面
            console.log('🔄 跳转到登录页面');
            setTimeout(() => {
                window.location.href = '/login';
            }, 1000);
        }
    }

    /**
     * 清除用户数据
     */
    clearUserData() {
        // 清除基础用户信息
        localStorage.removeItem('userData');
        localStorage.removeItem('userToken');
        localStorage.removeItem('currentUser');
        localStorage.removeItem('patientToken');
        localStorage.removeItem('doctorToken');
        localStorage.removeItem('adminToken');

        // 清除所有用户相关的对话历史数据
        const userId = StorageUtils.getCurrentUserId();
        if (userId) {
            const keys = Object.keys(localStorage);
            const userDataKeys = keys.filter(key =>
                key.startsWith(`tcm_doctor_history_${userId}_`) ||
                key.startsWith(`conversationId_${userId}`) ||
                key.startsWith(`followup_shown_`) ||
                key.includes(userId)
            );

            userDataKeys.forEach(key => {
                localStorage.removeItem(key);
                console.log(`🧹 已清除用户数据: ${key}`);
            });

            console.log(`✅ 清除了 ${userDataKeys.length} 条用户数据`);
        }

        // 清空sessionStorage
        sessionStorage.clear();

        console.log('✅ 用户数据清除完成');
    }

    /**
     * 检查是否需要登录（非访客模式）
     * @returns {boolean} 是否需要登录
     */
    requiresLogin() {
        const urlParams = new URLSearchParams(window.location.search);
        const isGuestMode = urlParams.get('mode') === 'guest';

        return !isGuestMode && !this.isLoggedIn();
    }

    /**
     * 强制跳转到登录页
     * @param {string} message - 提示消息
     * @param {number} delay - 延迟时间（毫秒）
     */
    redirectToLogin(message = '请先登录后使用', delay = 1500) {
        console.log('🔄 准备跳转到登录页:', message);

        if (message && typeof window.showMessage === 'function') {
            window.showMessage(message, 'warning');
        }

        setTimeout(() => {
            window.location.href = '/login';
        }, delay);
    }

    /**
     * 获取用户权限列表
     * @returns {Array} 权限列表
     */
    getPermissions() {
        const user = this.getCurrentUser();
        return user?.permissions || [];
    }

    /**
     * 检查是否有指定权限
     * @param {string} permission - 权限名称
     * @returns {boolean} 是否有权限
     */
    hasPermission(permission) {
        const permissions = this.getPermissions();
        return permissions.includes(permission);
    }

    /**
     * 是否为医生角色
     * @returns {boolean}
     */
    isDoctor() {
        const role = this.getUserRole();
        return role === 'doctor';
    }

    /**
     * 是否为患者角色
     * @returns {boolean}
     */
    isPatient() {
        const role = this.getUserRole();
        return role === 'patient';
    }

    /**
     * 是否为管理员角色
     * @returns {boolean}
     */
    isAdmin() {
        const role = this.getUserRole();
        return role === 'admin';
    }

    /**
     * 获取用户ID
     * @returns {string|null} 用户ID
     */
    getUserId() {
        const user = this.getCurrentUser();
        return user?.id || user?.user_id || null;
    }

    /**
     * 更新用户信息（从后端刷新）
     * @returns {Promise<Object|null>} 更新后的用户信息
     */
    async refreshUserInfo() {
        console.log('🔄 刷新用户信息...');

        const token = this.getToken();
        if (!token) {
            console.log('❌ 无Token，无法刷新');
            return null;
        }

        const user = await this.authManager.verifyToken(token);

        if (user) {
            this.currentUser = user;
            console.log('✅ 用户信息已刷新');
            return user;
        }

        return null;
    }

    /**
     * 保存用户偏好设置
     * @param {string} key - 设置键
     * @param {any} value - 设置值
     */
    savePreference(key, value) {
        const userId = this.getUserId();
        if (!userId) return;

        const prefKey = `user_pref_${userId}_${key}`;
        StorageUtils.saveUserData(prefKey, value, false);
    }

    /**
     * 获取用户偏好设置
     * @param {string} key - 设置键
     * @param {any} defaultValue - 默认值
     * @returns {any} 设置值
     */
    getPreference(key, defaultValue = null) {
        const userId = this.getUserId();
        if (!userId) return defaultValue;

        const prefKey = `user_pref_${userId}_${key}`;
        return StorageUtils.getUserData(prefKey, false, defaultValue);
    }
}
