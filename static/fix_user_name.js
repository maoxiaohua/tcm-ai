/**
 * 用户名显示错误修复脚本
 * 在浏览器控制台运行:
 * 1. 打开历史记录页面
 * 2. 按F12打开控制台
 * 3. 粘贴并运行此脚本
 */

(function() {
    console.log('🔧 开始修复用户显示名称...');

    // 获取当前用户数据
    const currentUserStr = localStorage.getItem('currentUser');

    if (!currentUserStr) {
        console.error('❌ 未找到currentUser数据，请确保已登录');
        return;
    }

    try {
        const user = JSON.parse(currentUserStr);
        console.log('📋 当前用户数据:', user);

        let needsFix = false;

        // 检查问题1: name字段包含医生名称
        if (user.name && (user.name.includes('大夫') || user.name.includes('医生') || user.name.includes('仲景') || user.name.includes('天士'))) {
            console.warn('⚠️ 发现问题: name字段包含医生名称:', user.name);
            console.log('🔧 删除错误的name字段...');
            delete user.name;
            needsFix = true;
        }

        // 检查问题2: 缺少display_name但有username
        if (!user.display_name && user.username) {
            console.log('🔧 设置display_name = username');
            user.display_name = user.username;
            needsFix = true;
        }

        // 检查问题3: 都没有但有phone
        if (!user.username && !user.display_name && user.phone_number) {
            console.log('🔧 设置display_name = phone_number');
            user.display_name = user.phone_number;
            needsFix = true;
        }

        if (needsFix) {
            // 保存修复后的数据
            localStorage.setItem('currentUser', JSON.stringify(user));
            console.log('✅ 用户数据已修复!');
            console.log('📋 修复后的数据:', user);
            console.log('');
            console.log('🔄 请刷新页面查看效果 (按 Ctrl+F5 或 Cmd+Shift+R)');

            // 自动刷新
            if (confirm('用户数据已修复！是否立即刷新页面？')) {
                location.reload(true);
            }
        } else {
            console.log('✅ 用户数据看起来正常，无需修复');
            console.log('📋 字段值:');
            console.log('  username:', user.username);
            console.log('  display_name:', user.display_name);
            console.log('  name:', user.name);
            console.log('  phone_number:', user.phone_number);
        }

    } catch (error) {
        console.error('❌ 修复失败:', error);
    }
})();
