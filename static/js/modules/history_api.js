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
        const token = localStorage.getItem('auth_token') || localStorage.getItem('session_token');
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
            const url = userId
                ? `/api/user/sessions?user_id=${encodeURIComponent(userId)}`
                : '/api/user/sessions';

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
            // 🔑 关键修复：优先从服务器API获取最新用户信息，避免localStorage缓存错误
            const token = localStorage.getItem('auth_token') || localStorage.getItem('session_token');

            if (token) {
                try {
                    const response = await fetch('/api/unified-auth/me', {
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
                    }
                } catch (apiError) {
                    console.warn('⚠️ API获取用户信息失败，尝试使用缓存:', apiError);
                }
            }

            // 备选方案1：从localStorage读取缓存（可能过期）
            const userDataStr = localStorage.getItem('userData') || localStorage.getItem('currentUser');
            if (userDataStr) {
                try {
                    const userData = JSON.parse(userDataStr);
                    console.log('⚠️ 从localStorage缓存获取用户信息（可能不是最新）:', userData);
                    return userData;
                } catch (e) {
                    console.warn('⚠️ 解析localStorage用户数据失败');
                }
            }

            // 备选方案2：使用全局 authManager（如果可用）
            if (window.authManager && typeof window.authManager.isLoggedIn === 'function' && window.authManager.isLoggedIn()) {
                const user = window.authManager.getCurrentUser();
                console.log('✅ 从authManager获取用户信息:', user);
                return user;
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
