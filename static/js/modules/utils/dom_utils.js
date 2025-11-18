/**
 * DOM 操作工具模块
 * 提供常用的 DOM 查询、操作、事件处理等功能
 */

export class DOMUtils {
    /**
     * 查询单个元素（querySelector的封装）
     * @param {string} selector - CSS选择器
     * @param {Element} parent - 父元素（可选）
     * @returns {Element|null} DOM元素
     */
    static $(selector, parent = document) {
        return parent.querySelector(selector);
    }

    /**
     * 查询多个元素（querySelectorAll的封装）
     * @param {string} selector - CSS选择器
     * @param {Element} parent - 父元素（可选）
     * @returns {NodeList} DOM元素列表
     */
    static $$(selector, parent = document) {
        return parent.querySelectorAll(selector);
    }

    /**
     * 通过ID获取元素
     * @param {string} id - 元素ID
     * @returns {Element|null} DOM元素
     */
    static getById(id) {
        return document.getElementById(id);
    }

    /**
     * 创建元素
     * @param {string} tag - 标签名
     * @param {Object} attrs - 属性对象
     * @param {string} content - 内容（可选）
     * @returns {Element} DOM元素
     */
    static createElement(tag, attrs = {}, content = '') {
        const element = document.createElement(tag);

        // 设置属性
        Object.keys(attrs).forEach(key => {
            if (key === 'className') {
                element.className = attrs[key];
            } else if (key === 'style' && typeof attrs[key] === 'object') {
                Object.assign(element.style, attrs[key]);
            } else if (key.startsWith('data-')) {
                element.setAttribute(key, attrs[key]);
            } else {
                element[key] = attrs[key];
            }
        });

        // 设置内容
        if (content) {
            if (content.trim().startsWith('<')) {
                element.innerHTML = content;
            } else {
                element.textContent = content;
            }
        }

        return element;
    }

    /**
     * 添加class
     * @param {Element} element - DOM元素
     * @param {string|Array} classes - class名称或数组
     */
    static addClass(element, classes) {
        if (!element) return;

        if (Array.isArray(classes)) {
            element.classList.add(...classes);
        } else {
            element.classList.add(classes);
        }
    }

    /**
     * 移除class
     * @param {Element} element - DOM元素
     * @param {string|Array} classes - class名称或数组
     */
    static removeClass(element, classes) {
        if (!element) return;

        if (Array.isArray(classes)) {
            element.classList.remove(...classes);
        } else {
            element.classList.remove(classes);
        }
    }

    /**
     * 切换class
     * @param {Element} element - DOM元素
     * @param {string} className - class名称
     * @returns {boolean} 切换后是否存在
     */
    static toggleClass(element, className) {
        if (!element) return false;

        return element.classList.toggle(className);
    }

    /**
     * 检查是否有class
     * @param {Element} element - DOM元素
     * @param {string} className - class名称
     * @returns {boolean} 是否存在
     */
    static hasClass(element, className) {
        if (!element) return false;

        return element.classList.contains(className);
    }

    /**
     * 显示元素
     * @param {Element} element - DOM元素
     * @param {string} display - display值（默认'block'）
     */
    static show(element, display = 'block') {
        if (!element) return;

        element.style.display = display;
    }

    /**
     * 隐藏元素
     * @param {Element} element - DOM元素
     */
    static hide(element) {
        if (!element) return;

        element.style.display = 'none';
    }

    /**
     * 切换显示/隐藏
     * @param {Element} element - DOM元素
     * @param {string} display - 显示时的display值
     */
    static toggle(element, display = 'block') {
        if (!element) return;

        if (element.style.display === 'none' || !element.style.display) {
            this.show(element, display);
        } else {
            this.hide(element);
        }
    }

    /**
     * 滚动到元素
     * @param {Element} element - DOM元素
     * @param {Object} options - 滚动选项
     */
    static scrollToElement(element, options = { behavior: 'smooth', block: 'center' }) {
        if (!element) return;

        element.scrollIntoView(options);
    }

    /**
     * 滚动到底部
     * @param {Element} element - 容器元素
     * @param {boolean} smooth - 是否平滑滚动
     */
    static scrollToBottom(element, smooth = true) {
        if (!element) return;

        if (smooth) {
            element.scrollTo({
                top: element.scrollHeight,
                behavior: 'smooth'
            });
        } else {
            element.scrollTop = element.scrollHeight;
        }
    }

    /**
     * 获取元素的位置和尺寸
     * @param {Element} element - DOM元素
     * @returns {DOMRect} 位置和尺寸信息
     */
    static getRect(element) {
        if (!element) return null;

        return element.getBoundingClientRect();
    }

    /**
     * 判断元素是否在视口内
     * @param {Element} element - DOM元素
     * @returns {boolean} 是否在视口内
     */
    static isInViewport(element) {
        if (!element) return false;

        const rect = this.getRect(element);
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }

    /**
     * 清空元素内容
     * @param {Element} element - DOM元素
     */
    static empty(element) {
        if (!element) return;

        while (element.firstChild) {
            element.removeChild(element.firstChild);
        }
    }

    /**
     * 移除元素
     * @param {Element} element - DOM元素
     */
    static remove(element) {
        if (!element) return;

        element.remove();
    }

    /**
     * 在元素前插入
     * @param {Element} element - 参考元素
     * @param {Element} newElement - 新元素
     */
    static insertBefore(element, newElement) {
        if (!element || !newElement) return;

        element.parentNode.insertBefore(newElement, element);
    }

    /**
     * 在元素后插入
     * @param {Element} element - 参考元素
     * @param {Element} newElement - 新元素
     */
    static insertAfter(element, newElement) {
        if (!element || !newElement) return;

        element.parentNode.insertBefore(newElement, element.nextSibling);
    }

    /**
     * 获取/设置元素属性
     * @param {Element} element - DOM元素
     * @param {string|Object} attr - 属性名或属性对象
     * @param {*} value - 属性值（可选）
     * @returns {*} 属性值或undefined
     */
    static attr(element, attr, value) {
        if (!element) return;

        // 获取属性
        if (typeof attr === 'string' && value === undefined) {
            return element.getAttribute(attr);
        }

        // 设置单个属性
        if (typeof attr === 'string') {
            element.setAttribute(attr, value);
            return;
        }

        // 设置多个属性
        if (typeof attr === 'object') {
            Object.keys(attr).forEach(key => {
                element.setAttribute(key, attr[key]);
            });
        }
    }

    /**
     * 移除属性
     * @param {Element} element - DOM元素
     * @param {string} attr - 属性名
     */
    static removeAttr(element, attr) {
        if (!element) return;

        element.removeAttribute(attr);
    }

    /**
     * 绑定事件
     * @param {Element} element - DOM元素
     * @param {string} event - 事件名
     * @param {Function} handler - 事件处理函数
     * @param {boolean|Object} options - 事件选项
     */
    static on(element, event, handler, options = false) {
        if (!element) return;

        element.addEventListener(event, handler, options);
    }

    /**
     * 解绑事件
     * @param {Element} element - DOM元素
     * @param {string} event - 事件名
     * @param {Function} handler - 事件处理函数
     */
    static off(element, event, handler) {
        if (!element) return;

        element.removeEventListener(event, handler);
    }

    /**
     * 绑定一次性事件
     * @param {Element} element - DOM元素
     * @param {string} event - 事件名
     * @param {Function} handler - 事件处理函数
     */
    static once(element, event, handler) {
        if (!element) return;

        const onceHandler = (e) => {
            handler(e);
            this.off(element, event, onceHandler);
        };

        this.on(element, event, onceHandler);
    }

    /**
     * 触发事件
     * @param {Element} element - DOM元素
     * @param {string} event - 事件名
     * @param {Object} detail - 事件详情
     */
    static trigger(element, event, detail = {}) {
        if (!element) return;

        const customEvent = new CustomEvent(event, {
            detail,
            bubbles: true,
            cancelable: true
        });

        element.dispatchEvent(customEvent);
    }

    /**
     * 等待DOM准备就绪
     * @param {Function} callback - 回调函数
     */
    static ready(callback) {
        if (document.readyState !== 'loading') {
            callback();
        } else {
            document.addEventListener('DOMContentLoaded', callback);
        }
    }

    /**
     * 防抖
     * @param {Function} func - 函数
     * @param {number} wait - 等待时间（毫秒）
     * @returns {Function} 防抖后的函数
     */
    static debounce(func, wait = 300) {
        let timeout;

        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };

            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * 节流
     * @param {Function} func - 函数
     * @param {number} limit - 时间限制（毫秒）
     * @returns {Function} 节流后的函数
     */
    static throttle(func, limit = 300) {
        let inThrottle;

        return function executedFunction(...args) {
            if (!inThrottle) {
                func(...args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * 复制文本到剪贴板
     * @param {string} text - 文本
     * @returns {Promise<boolean>} 是否成功
     */
    static async copyToClipboard(text) {
        try {
            if (navigator.clipboard) {
                await navigator.clipboard.writeText(text);
                return true;
            }

            // 降级方案
            const textarea = this.createElement('textarea', {
                value: text,
                style: { position: 'fixed', left: '-9999px' }
            });

            document.body.appendChild(textarea);
            textarea.select();

            const success = document.execCommand('copy');
            document.body.removeChild(textarea);

            return success;
        } catch (error) {
            console.error('复制失败:', error);
            return false;
        }
    }

    /**
     * 检测移动设备
     * @returns {boolean} 是否为移动设备
     */
    static isMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    /**
     * 检测iOS设备
     * @returns {boolean} 是否为iOS设备
     */
    static isIOS() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    }

    /**
     * 检测微信浏览器
     * @returns {boolean} 是否为微信浏览器
     */
    static isWeChat() {
        return /MicroMessenger/i.test(navigator.userAgent);
    }
}
