/**
 * 格式化工具模块
 * 提供日期、时间、文本等格式化功能
 */

export class FormatUtils {
    /**
     * 格式化会话时间（相对时间显示）
     * @param {string} dateStr - ISO日期字符串
     * @returns {string} 格式化后的时间
     */
    static formatConversationTime(dateStr) {
        try {
            const date = new Date(dateStr);
            const now = new Date();
            const diff = now - date;

            // 1分钟内
            if (diff < 60 * 1000) {
                return '刚刚';
            }

            // 1小时内
            if (diff < 60 * 60 * 1000) {
                const minutes = Math.floor(diff / (60 * 1000));
                return `${minutes}分钟前`;
            }

            // 24小时内
            if (diff < 24 * 60 * 60 * 1000) {
                const hours = Math.floor(diff / (60 * 60 * 1000));
                return `${hours}小时前`;
            }

            // 7天内
            if (diff < 7 * 24 * 60 * 60 * 1000) {
                const days = Math.floor(diff / (24 * 60 * 60 * 1000));
                return `${days}天前`;
            }

            // 超过7天，显示日期
            const month = date.getMonth() + 1;
            const day = date.getDate();
            return `${month}月${day}日`;

        } catch (error) {
            console.error('日期格式化失败:', error);
            return dateStr;
        }
    }

    /**
     * 格式化完整日期时间
     * @param {string|Date} date - 日期对象或字符串
     * @returns {string} 格式化后的日期时间
     */
    static formatDateTime(date) {
        try {
            const d = typeof date === 'string' ? new Date(date) : date;

            const year = d.getFullYear();
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            const hours = String(d.getHours()).padStart(2, '0');
            const minutes = String(d.getMinutes()).padStart(2, '0');
            const seconds = String(d.getSeconds()).padStart(2, '0');

            return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
        } catch (error) {
            console.error('日期格式化失败:', error);
            return String(date);
        }
    }

    /**
     * 格式化日期（不含时间）
     * @param {string|Date} date - 日期对象或字符串
     * @returns {string} 格式化后的日期
     */
    static formatDate(date) {
        try {
            const d = typeof date === 'string' ? new Date(date) : date;

            const year = d.getFullYear();
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');

            return `${year}-${month}-${day}`;
        } catch (error) {
            console.error('日期格式化失败:', error);
            return String(date);
        }
    }

    /**
     * 格式化时间（不含日期）
     * @param {string|Date} date - 日期对象或字符串
     * @returns {string} 格式化后的时间
     */
    static formatTime(date) {
        try {
            const d = typeof date === 'string' ? new Date(date) : date;

            const hours = String(d.getHours()).padStart(2, '0');
            const minutes = String(d.getMinutes()).padStart(2, '0');

            return `${hours}:${minutes}`;
        } catch (error) {
            console.error('时间格式化失败:', error);
            return String(date);
        }
    }

    /**
     * 清理HTML标签（用于纯文本显示）
     * @param {string} html - 包含HTML的字符串
     * @returns {string} 纯文本
     */
    static stripHTML(html) {
        if (!html) return '';

        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        return tempDiv.textContent || tempDiv.innerText || '';
    }

    /**
     * 截断文本
     * @param {string} text - 文本
     * @param {number} maxLength - 最大长度
     * @param {string} suffix - 后缀（默认"..."）
     * @returns {string} 截断后的文本
     */
    static truncate(text, maxLength = 50, suffix = '...') {
        if (!text) return '';
        if (text.length <= maxLength) return text;

        return text.substring(0, maxLength - suffix.length) + suffix;
    }

    /**
     * 格式化文件大小
     * @param {number} bytes - 字节数
     * @returns {string} 格式化后的大小
     */
    static formatFileSize(bytes) {
        if (bytes === 0) return '0 B';

        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * 格式化数字（添加千位分隔符）
     * @param {number} num - 数字
     * @returns {string} 格式化后的数字
     */
    static formatNumber(num) {
        if (typeof num !== 'number') return String(num);

        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }

    /**
     * 转义HTML特殊字符
     * @param {string} text - 文本
     * @returns {string} 转义后的文本
     */
    static escapeHTML(text) {
        if (!text) return '';

        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 解析Markdown为HTML（简单版本）
     * @param {string} markdown - Markdown文本
     * @returns {string} HTML
     */
    static parseMarkdown(markdown) {
        if (!markdown) return '';

        // 如果有marked库，使用它
        if (window.marked && typeof window.marked.parse === 'function') {
            return window.marked.parse(markdown);
        }

        // 否则使用简单的替换
        return markdown
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // **粗体**
            .replace(/\*(.*?)\*/g, '<em>$1</em>')              // *斜体*
            .replace(/`(.*?)`/g, '<code>$1</code>')            // `代码`
            .replace(/\n\n/g, '</p><p>')                        // 段落
            .replace(/\n/g, '<br>')                             // 换行
            .replace(/^/, '<p>')                                // 开始段落
            .replace(/$/, '</p>');                              // 结束段落
    }

    /**
     * 高亮关键词
     * @param {string} text - 文本
     * @param {string} keyword - 关键词
     * @returns {string} 高亮后的HTML
     */
    static highlightKeyword(text, keyword) {
        if (!text || !keyword) return text;

        const regex = new RegExp(`(${keyword})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    /**
     * 格式化中药剂量
     * @param {string} dosage - 剂量字符串
     * @returns {string} 格式化后的剂量
     */
    static formatHerbDosage(dosage) {
        if (!dosage) return '';

        // 统一剂量单位
        return dosage
            .replace(/克/g, 'g')
            .replace(/毫升/g, 'ml')
            .replace(/片/g, '片')
            .replace(/粒/g, '粒');
    }

    /**
     * 解析证候类型并返回徽章样式
     * @param {string} syndrome - 证候类型
     * @returns {Object} {text, className}
     */
    static getSyndromeBadge(syndrome) {
        const badges = {
            '寒证': { text: '寒', className: 'badge-cold' },
            '热证': { text: '热', className: 'badge-hot' },
            '虚证': { text: '虚', className: 'badge-deficiency' },
            '实证': { text: '实', className: 'badge-excess' },
            '表证': { text: '表', className: 'badge-exterior' },
            '里证': { text: '里', className: 'badge-interior' }
        };

        return badges[syndrome] || { text: syndrome, className: 'badge-default' };
    }

    /**
     * 格式化电话号码
     * @param {string} phone - 电话号码
     * @returns {string} 格式化后的电话号码
     */
    static formatPhone(phone) {
        if (!phone) return '';

        // 移除所有非数字字符
        const cleaned = phone.replace(/\D/g, '');

        // 格式化为 xxx-xxxx-xxxx
        if (cleaned.length === 11) {
            return `${cleaned.slice(0, 3)}-${cleaned.slice(3, 7)}-${cleaned.slice(7)}`;
        }

        return phone;
    }

    /**
     * 脱敏电话号码
     * @param {string} phone - 电话号码
     * @returns {string} 脱敏后的电话号码
     */
    static maskPhone(phone) {
        if (!phone) return '';

        const cleaned = phone.replace(/\D/g, '');

        if (cleaned.length === 11) {
            return `${cleaned.slice(0, 3)}****${cleaned.slice(7)}`;
        }

        return phone;
    }

    /**
     * 验证电话号码
     * @param {string} phone - 电话号码
     * @returns {boolean} 是否有效
     */
    static isValidPhone(phone) {
        if (!phone) return false;

        const cleaned = phone.replace(/\D/g, '');
        return /^1[3-9]\d{9}$/.test(cleaned);
    }

    /**
     * 验证邮箱
     * @param {string} email - 邮箱
     * @returns {boolean} 是否有效
     */
    static isValidEmail(email) {
        if (!email) return false;

        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }
}
