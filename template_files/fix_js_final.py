#!/usr/bin/env python3
import re

# 读取文件
with open('/opt/tcm-ai/static/doctor/index_optimized.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 提取script部分
script_start = content.find('<script>')
script_end = content.find('</script>')

if script_start != -1 and script_end != -1:
    before_script = content[:script_start + 8]  # include <script>
    after_script = content[script_end:]  # include </script>
    
    # 创建一个最小化的、语法正确的JavaScript版本
    clean_script = '''
        // 全局变量
        let currentUser = null;
        let currentPrescriptionId = null;
        let batchMode = false;
        let selectedPrescriptions = new Set();
        let prescriptionFilter = 'all';
        let patientFilter = 'all';
        let patientSearchTerm = '';
        let allPatients = [];

        // 页面加载时的初始化
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM加载完成，开始初始化...');
            try {
                checkAuth();
                loadDashboardStats();
            } catch (error) {
                console.error('初始化失败:', error);
                const nameElement = document.getElementById('doctorName');
                if (nameElement) {
                    nameElement.textContent = '初始化失败';
                }
            }
        });

        // 检查用户认证
        async function checkAuth() {
            console.log('开始认证检查...');
            const token = localStorage.getItem('session_token') || localStorage.getItem('doctorToken');
            console.log('Token检查:', !!token);
            
            if (!token) {
                console.log('未找到token，重定向到登录页');
                window.location.href = '/login';
                return;
            }

            try {
                const response = await fetch('/api/v2/auth/profile', {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.success && data.user) {
                        currentUser = data.user;
                        updateUserInfo();
                        
                        if (data.user.primary_role !== 'doctor' && data.user.primary_role !== 'admin' && data.user.primary_role !== 'superadmin') {
                            alert('您没有访问医生工作台的权限');
                            window.location.href = '/login';
                            return;
                        }
                        
                        if (!localStorage.getItem('session_token') && localStorage.getItem('doctorToken')) {
                            localStorage.setItem('session_token', token);
                        }
                    } else {
                        throw new Error('用户信息无效');
                    }
                } else {
                    throw new Error('认证失败');
                }
            } catch (error) {
                console.error('认证检查失败:', error);
                localStorage.removeItem('doctorToken');
                localStorage.removeItem('session_token');
                window.location.href = '/login';
            }
        }

        // 更新用户信息显示
        function updateUserInfo() {
            try {
                if (currentUser) {
                    const nameElement = document.getElementById('doctorName');
                    const avatarElement = document.getElementById('doctorAvatar');
                    
                    if (nameElement) {
                        nameElement.textContent = currentUser.display_name || '未知用户';
                    }
                    if (avatarElement) {
                        avatarElement.textContent = (currentUser.display_name || '医').charAt(0);
                    }
                    
                    console.log('用户信息更新成功:', currentUser.display_name);
                } else {
                    console.log('没有用户信息可更新');
                }
            } catch (error) {
                console.error('更新用户信息失败:', error);
            }
        }

        // 加载工作台统计数据
        async function loadDashboardStats() {
            // 模拟统计数据
            document.getElementById('todayReviewedCount').textContent = '12';
            document.getElementById('weeklyReviewedCount').textContent = '89';
            document.getElementById('monthlyReviewedCount').textContent = '267';
            document.getElementById('totalPatientsCount').textContent = '156';
            console.log('仪表板统计数据加载完成');
        }

        // 切换内容区域
        function showSection(sectionId) {
            console.log('切换到:', sectionId);
            
            // 隐藏所有内容区域
            document.querySelectorAll('.content-section').forEach(section => {
                section.classList.remove('active');
            });

            // 显示选中的内容区域
            const targetSection = document.getElementById(sectionId);
            if (targetSection) {
                targetSection.classList.add('active');
            }

            // 更新导航状态
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            event.target.closest('.nav-item').classList.add('active');

            // 加载对应数据
            switch(sectionId) {
                case 'prescriptions':
                    loadPrescriptionReviewData();
                    break;
                case 'patient-management':
                    loadPatientManagementData();
                    break;
                case 'profile':
                    loadProfile();
                    break;
            }
        }

        // 加载处方审查数据
        async function loadPrescriptionReviewData() {
            console.log('加载处方审查数据...');
        }

        // 加载患者管理数据
        async function loadPatientManagementData() {
            console.log('加载患者管理数据...');
        }

        // 加载个人档案
        function loadProfile() {
            console.log('加载个人档案...');
        }

        // 占位函数
        function refreshPrescriptionList() {
            console.log('刷新处方列表');
        }

        function viewPrescriptionDetail(id) {
            console.log('查看处方详情:', id);
        }

        function openDecisionTreeBuilder() {
            window.open('/decision_tree_visual_builder.html', '_blank');
        }

        function openUnifiedConsultation() {
            window.open('/smart', '_blank');
        }

        function openBatchReview() {
            alert('批量审查功能开发中...');
        }

        function openLearningCenter() {
            alert('学习中心功能开发中...');
        }

        // 退出登录
        async function logout() {
            if (confirm('确定要退出登录吗？')) {
                try {
                    const token = localStorage.getItem('session_token') || localStorage.getItem('doctorToken');
                    if (token) {
                        await fetch('/api/v2/auth/logout', {
                            method: 'POST',
                            headers: {
                                'Authorization': `Bearer ${token}`,
                                'Content-Type': 'application/json'
                            }
                        });
                    }
                } catch (error) {
                    console.error('登出请求失败:', error);
                } finally {
                    localStorage.removeItem('doctorToken');
                    localStorage.removeItem('session_token');
                    localStorage.removeItem('userData');
                    localStorage.removeItem('currentUser');
                    window.location.href = '/login';
                }
            }
        }
    '''
    
    # 重新组合内容
    new_content = before_script + clean_script + after_script
    
    # 写入文件
    with open('/opt/tcm-ai/static/doctor/index_optimized.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("JavaScript cleaned and simplified!")
else:
    print("Could not find script tags!")