/**
 * 患者历史记录 - API调用层
 * 负责所有与后端的HTTP通信
 */

export class HistoryAPI {
    constructor() {
        this.baseURL = '';
    }

    /**
     * 获取认证头
     */
    getAuthHeaders() {
        const token = (window.authManager && typeof window.authManager.getToken === 'function'
            ? window.authManager.getToken()
            : null) ||
            localStorage.getItem('session_token') ||
            localStorage.getItem('tcm_auth_token') ||
            localStorage.getItem('auth_token');
        const headers = {
            'Content-Type': 'application/json'
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        return headers;
    }

    /**
     * 获取用户会话列表
     * @param {string} userId - 用户ID
     * @returns {Promise<Object>} 会话列表数据
     */
    async getSessions(userId) {
        try {
            const token = (window.authManager && typeof window.authManager.getToken === 'function'
                ? window.authManager.getToken()
                : null) ||
                localStorage.getItem('session_token') ||
                localStorage.getItem('tcm_auth_token') ||
                localStorage.getItem('auth_token');

            // 登录用户优先由后端从token解析user_id，避免前端缓存旧user_id导致拉错历史
            const url = token
                ? '/api/user/sessions'
                : (userId ? `/api/user/sessions?user_id=${encodeURIComponent(userId)}` : '/api/user/sessions');

            const response = await fetch(url, {
                headers: this.getAuthHeaders()
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('❌ 获取会话列表失败:', error);
            throw error;
        }
    }

    /**
     * 获取单个会话的详细信息
     * @param {string} sessionId - 会话ID
     * @returns {Promise<Object>} 会话详情数据
     */
    async getConversationDetail(sessionId) {
        try {
            const response = await fetch(`/api/user/conversation/${sessionId}`, {
                headers: this.getAuthHeaders()
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.message || '获取会话详情失败');
            }

            return data;
        } catch (error) {
            console.error('❌ 获取会话详情失败:', error);
            throw error;
        }
    }

    /**
     * 加载医生信息列表
     * @returns {Promise<Object>} 医生信息数据
     */
    async loadDoctorInfo() {
        try {
            const response = await fetch('/api/doctor/list');

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error('加载医生信息失败');
            }

            return data;
        } catch (error) {
            console.warn('⚠️ 加载医生信息失败:', error);
            // 返回空数据而不是抛出错误，让应用继续运行
            return { success: false, doctors: [] };
        }
    }

    /**
     * 获取当前用户信息
     * @returns {Promise<Object>} 用户信息
     */
    async getCurrentUser() {
        try {
            // 🔑 v4.3修复：统一token获取顺序，与authManager保持一致
            const token = localStorage.getItem('session_token') ||
                          localStorage.getItem('tcm_auth_token') ||
                          localStorage.getItem('auth_token');

            if (token) {
                try {
                    // 🔑 修复：使用正确的API端点 /api/v2/auth/profile
                    const response = await fetch('/api/v2/auth/profile', {
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        }
                    });

                    if (response.ok) {
                        const data = await response.json();
                        if (data.success && data.user) {
                            console.log('✅ 从服务器API获取用户信息:', data.user);
                            // 更新localStorage缓存
                            localStorage.setItem('currentUser', JSON.stringify(data.user));
                            return data.user;
                        }
                    } else {
                        console.warn('⚠️ API返回非200状态:', response.status);
                    }
                } catch (apiError) {
                    console.warn('⚠️ API获取用户信息失败，尝试使用缓存:', apiError);
                }
            }

            // 🔑 v4.3修复：优先使用authManager（它总是包含最新的登录状态）
            if (window.authManager && typeof window.authManager.isLoggedIn === 'function' && window.authManager.isLoggedIn()) {
                const user = window.authManager.getCurrentUser();
                console.log('✅ 从authManager获取用户信息:', user);
                return user;
            }

            // 备选方案：从localStorage读取缓存（可能过期）
            const userDataStr = localStorage.getItem('currentUser') || localStorage.getItem('userData');
            if (userDataStr) {
                try {
                    const userData = JSON.parse(userDataStr);
                    console.log('⚠️ 从localStorage缓存获取用户信息（可能不是最新）:', userData);
                    return userData;
                } catch (e) {
                    console.warn('⚠️ 解析localStorage用户数据失败');
                }
            }

            console.log('⚠️ 无用户信息，返回null');
            return null;
        } catch (error) {
            console.warn('⚠️ 获取用户信息失败:', error);
            return null;
        }
    }

    /**
     * 清空用户历史记录
     * @returns {Promise<Object>} 清空结果
     */
    async clearHistory() {
        try {
            const response = await fetch('/api/user/sessions/clear', {
                method: 'DELETE',
                headers: this.getAuthHeaders()
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('❌ 清空历史记录失败:', error);
            throw error;
        }
    }

    /**
     * 导出历史记录
     * @returns {Promise<Blob>} 导出的文件数据
     */
    async exportHistory() {
        try {
            const response = await fetch('/api/user/sessions/export', {
                headers: this.getAuthHeaders()
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.blob();
        } catch (error) {
            console.error('❌ 导出历史记录失败:', error);
            throw error;
        }
    }
}
