/**
 * 认证验证器 - 全局Session状态监控
 *
 * 功能：
 * 1. 页面加载时验证session有效性
 * 2. 定期心跳检查session状态
 * 3. 友好的过期提示和自动登出
 */

class AuthValidator {
    constructor() {
        this.isValidating = false;
        this.lastCheckTime = 0;
        this.checkInterval = 5 * 60 * 1000; // 5分钟检查一次
        this.hasShownExpiredAlert = false; // 防止重复弹窗

        console.log('🔐 认证验证器已初始化');
    }

    /**
     * 验证当前session是否有效
     */
    async validateSession() {
        // 防止重复验证
        if (this.isValidating) {
            return;
        }

        // 限制检查频率（避免过度请求）
        const now = Date.now();
        if (now - this.lastCheckTime < 30000) { // 30秒内不重复检查
            return;
        }

        this.isValidating = true;
        this.lastCheckTime = now;

        try {
            const token = window.userToken || localStorage.getItem('tcm_auth_token');

            // 如果没有token，但页面显示已登录，说明有问题
            if (!token && window.currentUser) {
                console.warn('⚠️ 检测到登录状态不一致：有用户信息但无token');
                this.handleSessionExpired('no_token');
                return false;
            }

            // 如果有token，调用后端验证
            if (token) {
                const isValid = await this.checkSessionWithBackend(token);
                if (!isValid) {
                    this.handleSessionExpired('backend_validation_failed');
                    return false;
                }
            }

            return true;

        } catch (error) {
            console.error('❌ Session验证失败:', error);
            return false;
        } finally {
            this.isValidating = false;
        }
    }

    /**
     * 调用后端验证session
     */
    async checkSessionWithBackend(token) {
        try {
            // 使用一个轻量级API测试session有效性
            const response = await fetch('/api/auth/validate-session', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.status === 401) {
                console.warn('⚠️ Session已过期（后端返回401）');
                return false;
            }

            if (!response.ok) {
                console.warn(`⚠️ Session验证失败: ${response.status}`);
                return false;
            }

            const data = await response.json();
            console.log('✅ Session验证通过');
            return data.valid === true;

        } catch (error) {
            console.error('❌ 后端验证请求失败:', error);
            // 网络错误不强制登出，可能只是临时问题
            return true;
        }
    }

    /**
     * 处理session过期
     */
    handleSessionExpired(reason) {
        // 防止重复弹窗
        if (this.hasShownExpiredAlert) {
            return;
        }
        this.hasShownExpiredAlert = true;

        console.error(`❌ Session已过期 (原因: ${reason})`);

        // 清除本地状态
        this.clearLocalAuthData();

        // 更新UI显示
        this.updateUIToLoggedOut();

        // 显示友好提示
        this.showExpirationNotice();
    }

    /**
     * 清除本地认证数据
     */
    clearLocalAuthData() {
        // 清除localStorage中的认证信息
        localStorage.removeItem('tcm_auth_token');
        localStorage.removeItem('user_info');
        localStorage.removeItem('current_user');

        // 清除window全局变量
        window.userToken = null;
        window.currentUser = null;

        console.log('🧹 已清除本地认证数据');
    }

    /**
     * 更新UI为登出状态
     */
    updateUIToLoggedOut() {
        // 隐藏用户信息
        const userInfo = document.getElementById('userInfo');
        if (userInfo) {
            userInfo.style.display = 'none';
        }

        // 显示登录按钮
        const loginBtn = document.getElementById('loginBtn');
        const registerBtn = document.getElementById('registerBtn');
        if (loginBtn) loginBtn.style.display = 'inline-block';
        if (registerBtn) registerBtn.style.display = 'inline-block';

        // 清空用户名显示
        const usernameDisplay = document.getElementById('usernameDisplay');
        if (usernameDisplay) {
            usernameDisplay.textContent = '';
        }

        console.log('🎨 UI已更新为登出状态');
    }

    /**
     * 显示过期提示（友好的模态框）
     */
    showExpirationNotice() {
        // 创建模态框HTML
        const modalHTML = `
            <div id="sessionExpiredModal" style="
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.7);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            ">
                <div style="
                    background: white;
                    padding: 30px;
                    border-radius: 12px;
                    max-width: 400px;
                    text-align: center;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                ">
                    <div style="font-size: 48px; margin-bottom: 20px;">⏰</div>
                    <h2 style="margin: 0 0 15px 0; color: #333; font-size: 24px;">登录已过期</h2>
                    <p style="color: #666; margin: 0 0 25px 0; line-height: 1.6;">
                        您的登录会话已过期，为了保护您的账户安全，请重新登录。
                    </p>
                    <button id="reloginBtn" style="
                        background: #4CAF50;
                        color: white;
                        border: none;
                        padding: 12px 30px;
                        border-radius: 6px;
                        font-size: 16px;
                        cursor: pointer;
                        transition: background 0.3s;
                    " onmouseover="this.style.background='#45a049'"
                       onmouseout="this.style.background='#4CAF50'">
                        重新登录
                    </button>
                </div>
            </div>
        `;

        // 插入到页面
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // 绑定按钮事件
        document.getElementById('reloginBtn').addEventListener('click', () => {
            window.location.href = '/login';
        });

        // 5秒后自动跳转（如果用户没有点击）
        setTimeout(() => {
            const modal = document.getElementById('sessionExpiredModal');
            if (modal) {
                window.location.href = '/login';
            }
        }, 5000);

        console.log('💬 已显示过期提示模态框');
    }

    /**
     * 启动定期心跳检查
     */
    startHeartbeat() {
        // 立即执行一次验证
        setTimeout(() => {
            this.validateSession();
        }, 2000); // 页面加载2秒后检查

        // 定期检查
        setInterval(() => {
            this.validateSession();
        }, this.checkInterval);

        console.log(`💓 Session心跳检查已启动（间隔: ${this.checkInterval / 1000}秒）`);
    }

    /**
     * 拦截所有API请求，自动处理401错误
     */
    setupGlobalErrorHandler() {
        // 保存原始fetch
        const originalFetch = window.fetch;

        // 重写fetch
        window.fetch = async (...args) => {
            try {
                const response = await originalFetch(...args);

                // 拦截401错误
                if (response.status === 401) {
                    console.warn('⚠️ API返回401，session可能已过期');

                    // 如果是switch-doctor或其他关键API，立即处理
                    const url = args[0];
                    if (typeof url === 'string' &&
                        (url.includes('/api/conversation/') ||
                         url.includes('/api/consultation/') ||
                         url.includes('/api/prescription/'))) {

                        this.handleSessionExpired('api_401_error');
                    }
                }

                return response;
            } catch (error) {
                throw error;
            }
        };

        console.log('🛡️ 全局API错误拦截器已启动');
    }
}

// 创建全局实例
if (typeof window !== 'undefined') {
    window.authValidator = new AuthValidator();
    console.log('✅ AuthValidator全局实例已创建: window.authValidator');
}
