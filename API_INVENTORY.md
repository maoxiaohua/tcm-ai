# TCM-AI 项目API接口完整清单

## 文档说明
本文档统计TCM-AI项目中所有API路由端点，包括请求参数、响应格式等详细信息。

**统计时间**: 2025-10-29
**扫描范围**: /opt/tcm-ai/api/routes/*.py (28个路由模块)
**总计**: 超过150个API端点

---

## 一、认证与用户管理

### 1. 统一认证v2 (/api/v2/auth) - unified_auth_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/login` | `{username, password, device_name?, remember_me?}` | `{success, message, user, session, permissions, redirect_url}` | 用户登录 |
| POST | `/register` | `{username, password, display_name, email?, phone_number?, user_type?}` | `{success, message, user, session, permissions, redirect_url}` | 用户注册 |
| POST | `/logout` | - | `{success, message}` | 用户登出 |
| GET | `/profile` | - | `{success, user, data_sync}` | 获取用户资料 |
| GET | `/permissions` | - | `{success, permissions, user_id, primary_role}` | 获取用户权限列表 |
| POST | `/sync-data` | `{data_type, data_key, data_content}` | `{success, message}` | 同步用户数据 |
| GET | `/sync-data/{data_type}` | - | `{success, data_type, data}` | 获取同步数据 |
| GET | `/sessions` | - | `{success, sessions}` | 获取用户所有会话 |
| DELETE | `/sessions/{session_id}` | - | `{success, message}` | 撤销指定会话 |
| GET | `/check-permission/{permission_code}` | - | `{has_permission, permission_code, user_id}` | 检查权限 |
| GET | `/admin/users` | `page?, size?` | `{success, message, page, size, total, users}` | 管理员：获取用户列表 |
| GET | `/admin/audit-logs` | `page?, size?, event_type?` | `{success, message, page, size, event_type, logs}` | 管理员：获取审计日志 |
| POST | `/maintenance/cleanup-sessions` | - | `{success, message}` | 系统管理员：清理过期会话 |
| GET | `/health` | - | `{status, timestamp, version, database_connected?}` | 健康检查接口 |
| POST | `/legacy/login` | `{username, password}` | `{success, user, redirect_url, message}` | 向后兼容的登录接口 |

### 2. 统一认证v1 (/api/auth) - auth_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/login` | `{username, password}` | `{success, message, user, redirect_url, token}` | 统一登录接口 |
| POST | `/logout` | - | `{success, message}` | 统一登出接口 |
| GET | `/profile` | - | `{success, user}` | 获取当前用户信息 |

### 3. 统一登录 (/api/login) - unified_login_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/login` | `{username, password}` | `{success, message, user, redirect_url, token}` | 统一登录 |
| POST | `/logout` | - | `{success, message}` | 登出 |
| GET | `/session` | - | `{success, session}` | 获取会话信息 |
| GET | `/verify` | - | `{success, verified}` | 验证登录状态 |
| GET | `/me` | - | `{success, user}` | 获取当前用户 |
| GET | `/doctor/current` | - | `{success, doctor}` | 获取当前医生信息 |

---

## 二、问诊与对话管理

### 1. 统一问诊服务 (/api/consultation) - unified_consultation_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/chat` | `{message, conversation_id, selected_doctor?, patient_id?, has_images?, conversation_history?}` | `{success, data{reply, conversation_id, doctor_name, contains_prescription, prescription_data, ...}, message}` | 统一问诊聊天接口 |
| POST | `/chat-legacy` | `{message, conversation_id, selected_doctor?, patient_id?, has_images?, conversation_history?}` | `{reply, conversation_id}` | 兼容原系统的问诊接口 |
| GET | `/doctor-info/{doctor_name}` | - | `{success, data{name, school, specialty, method}}` | 获取医生信息 |
| GET | `/service-status` | - | `{success, data{service_name, version, status, features, supported_doctors}}` | 获取统一问诊服务状态 |
| POST | `/save` | `{consultation_id, patient_id, doctor_id, conversation_log, status?, created_at, updated_at}` | `{success, message, data{consultation_id, patient_id, doctor_id, status}}` | 保存问诊对话 |
| GET | `/conversation/{conversation_id}/progress` | - | `{success, data{...}}` | 获取对话进度信息 |
| GET | `/conversation/{conversation_id}/guidance` | - | `{success, data{...}}` | 获取阶段引导信息 |
| POST | `/conversation/{conversation_id}/confirm-prescription` | - | `{success, message, data{next_step, message}}` | 确认处方 |
| POST | `/conversation/{conversation_id}/end` | `{reason?, satisfaction?}` | `{success, message, data{end_type, reason}}` | 结束对话 |
| GET | `/conversation/{conversation_id}/summary` | - | `{success, data{conversation_id, doctor_name, start_time, duration_minutes, turn_count, ...}}` | 获取对话摘要 |
| POST | `/update-status` | `{patient_id, status, prescription_id?, conversation_log?, symptoms_analysis?, updated_at?}` | `{success, message, consultation_id, status}` | 更新问诊状态 |
| GET | `/detail/{session_id}` | - | `{success, data{session_id, patient_id, doctor_id, chief_complaint, status, conversation_history, ...}, message}` | 获取对话详细信息 |
| GET | `/patient/history` | `user_id?` (Header) | `{success, data{consultation_history, total_count, user_id}, message}` | 获取患者历史问诊 |

### 2. 对话同步 (/api/user-data-sync) - conversation_sync_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/sync` | `{user_id, doctor_id, conversation_history, ...}` | `{success, history{}, timestamp, sync_id}` | 同步对话历史 |
| GET | `/history/{user_id}` | - | `{success, history, timestamp}` | 获取用户对话历史 |
| POST | `/clear` | `{user_id}` | `{success, message, history{}}` | 清除对话历史 |
| GET | `/status/{user_id}/{doctor_id}` | - | `{success, status, last_sync}` | 获取同步状态 |
| DELETE | `/cleanup/{user_id}` | - | `{success, message}` | 清理用户数据 |
| POST | `/backup/{user_id}` | - | `{success, backup_id, timestamp}` | 备份用户数据 |

### 3. 会话管理 (/api/user-sessions) - user_sessions_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| GET | `/sessions` | - | `{success, sessions}` | 获取用户会话列表 |
| GET | `/conversation/{session_id}` | - | `{success, conversation}` | 获取对话内容 |
| DELETE | `/sessions/clear` | - | `{success, message}` | 清除所有会话 |

---

## 三、处方管理

### 1. 处方基础管理 (/api/prescription) - prescription_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/create` | `{patient_id, conversation_id, doctor_id?, patient_name?, patient_phone?, symptoms?, diagnosis?, ai_prescription}` | `{success, message, prescription_id, status}` | 创建新处方 |
| GET | `/by-consultation/{consultation_id}` | - | `{success, prescriptions, count}` | 根据问诊ID获取处方 |
| GET | `/pending` | (Header) Authorization | `{success, prescriptions, total}` | 获取待审查处方列表 |
| GET | `/doctor/stats` | (Header) Authorization | `{success, statistics{total_reviewed, total_approved, total_rejected, today_reviewed, pending_review}}` | 获取医生处方审查统计 |
| GET | `/detail/{session_id}` | - | `{success, data{...} \| message}` | 通过session_id获取处方详情 |
| GET | `/learning_stats` | - | `{success, data{...}}` | 获取处方学习系统统计 |
| GET | `/{prescription_id}/status` | - | `{success, prescription{id, status, doctor_id, ...}}` | 查询处方状态 |
| GET | `/{prescription_id}` | - | `{success, prescription{...}}` | 获取处方详情（患者端） |
| GET | `/patient/{patient_id}/prescriptions` | - | `{success, prescriptions, total}` | 获取患者的所有处方 |
| GET | `/conversation/{conversation_id}` | - | `{success, prescription \| message}` | 通过对话ID获取处方 |
| PUT | `/{prescription_id}/patient-confirm` | `{confirm, notes?}` | `{success, message, prescription_id, new_status}` | 患者确认处方 |
| GET | `/statistics/status` | - | `{success, statistics{by_status, today_total, today_approved}}` | 获取处方状态统计 |
| GET | `/{prescription_id}/full-content` | - | `{success, prescription{id, full_content, payment_status, created_at}}` | 获取处方完整内容 |

### 2. AI增强处方管理 (/api/prescription/ai) - prescription_ai_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/analyze/{prescription_id}` | `{prescription_id, analysis_type?}` | (Header) Authorization | `{success, analysis_result, analysis_id}` | 使用AI分析处方 |
| POST | `/batch-operation` | `{prescription_ids, operation, notes?}` | (Header) Authorization | `{success, message, processed}` | 批量操作处方 |
| GET | `/risk-analysis` | (Header) Authorization | `{success, risk_summary}` | 获取风险分析 |
| GET | `/insights` | - | `{success, insights}` | 获取AI洞察 |
| POST | `/recommend` | `{patient_info?, symptoms?}` | (Header) Authorization | `{success, recommendations}` | 获取AI推荐 |

### 3. 处方审核 (/api/prescription/review) - prescription_review_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/payment-confirm` | `{prescription_id, payment_status, transaction_id?}` | `{success, message, prescription{}}` | 支付确认 |
| GET | `/doctor-queue/{doctor_id}` | - | `{success, queue{}}` | 获取医生审核队列 |
| POST | `/doctor-review` | `{prescription_id, action, doctor_prescription?, doctor_notes?}` | `{success, message, prescription{}}` | 医生审核处方 |
| GET | `/status/{prescription_id}` | - | `{success, status, review_status, payment_status}` | 获取审核状态 |

### 4. 处方结构化编辑 (/api/prescription/structured-edit) - prescription_structured_edit_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| GET | `/parse/{prescription_id}` | - | `{success, structure{medicines, dosage, ...}}` | 解析处方结构 |
| POST | `/edit` | `{prescription_id, structure{...}}` | `{success, message, prescription_id}` | 编辑处方 |
| GET | `/preview/{prescription_id}` | - | `{success, preview_text}` | 获取处方预览 |

---

## 四、医生相关接口

### 1. 医生管理 (/api/doctor) - doctor_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/register` | `{name, license_no, phone, email, password, speciality?, hospital?}` | `{success, message, doctor_id}` | 医生注册 |
| POST | `/login` | `{license_no, password}` | `{success, message, doctor}` | 医生登录 |
| POST | `/logout` | (Header) Authorization | `{success, message}` | 医生登出 |
| GET | `/profile` | (Header) Authorization | `{success, doctor}` | 获取医生档案 |
| PUT | `/profile` | `{name?, speciality?, hospital?, email?, phone?, bio?}` | (Header) Authorization | `{success, message, doctor}` | 更新医生档案 |
| PUT | `/change-password` | `{current_password, new_password, confirm_password}` | (Header) Authorization | `{success, message}` | 修改医生密码 |
| GET | `/pending-prescriptions` | (Header) Authorization | `{success, prescriptions, total}` | 获取待审查处方列表 |
| GET | `/prescription/{prescription_id}` | (Header) Authorization | `{success, prescription}` | 获取处方详情 |
| PUT | `/prescription/{prescription_id}/review` | `{action, doctor_prescription?, doctor_notes?}` | (Header) Authorization | `{success, message, prescription_id, new_status}` | 审查处方 |
| GET | `/current` | (Header) Authorization | `{success, role, name, id, license_no, speciality, hospital, doctor{}}` | 获取当前登录医生信息 |
| GET | `/today-reviewed` | (Header) Authorization | `{success, prescriptions, total}` | 获取今日已审查处方 |
| GET | `/all-prescriptions` | (Header) Authorization | `{success, prescriptions, total}` | 获取医生相关的所有处方 |
| GET | `/statistics` | (Header) Authorization | `{success, statistics{total_reviewed, approved, rejected, today_reviewed, pending_review, active_days}}` | 获取医生工作统计 |
| GET | `/list` | - | `{success, doctors, total}` | 获取所有可用医生列表 |

### 2. 医生决策树 (/api/doctor-decision-tree) - doctor_decision_tree_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/analyze_thinking` | `{thinking_text, context?}` | `{success, analysis{...}}` | 分析医生诊疗思维 |
| POST | `/generate_decision_tree` | `{symptoms, medical_history?, patient_info?}` | `{success, tree{...}}` | 生成决策树 |
| POST | `/save_decision_tree` | `{tree_data, doctor_id, version?}` | `{success, tree_id, message}` | 保存决策树 |
| POST | `/save_decision_tree_v3` | `{tree_data, doctor_id, version?}` | `{success, tree_id, message}` | 保存决策树v3版本 |
| POST | `/match_symptoms_to_paths` | `{symptoms, tree_id}` | `{success, matches{...}}` | 症状匹配决策路径 |
| POST | `/generate_visual_decision_tree` | `{tree_data}` | `{success, visual_tree{...}}` | 生成可视化决策树 |
| POST | `/analyze_tree_tcm_theory` | `{tree_data}` | `{success, analysis{...}}` | 分析决策树的中医理论 |
| POST | `/detect_missing_logic` | `{tree_data}` | `{success, missing_parts{...}}` | 检测缺失的诊疗逻辑 |
| GET | `/user_preferences/{user_id}` | - | `{success, preferences{...}}` | 获取用户偏好设置 |
| POST | `/user_preferences/{user_id}` | `{preferences{...}}` | `{success, message}` | 保存用户偏好设置 |
| GET | `/ai_status` | - | `{success, status{...}}` | 获取AI状态 |
| POST | `/feedback/decision_tree/{tree_id}` | `{rating, feedback}` | `{success, message}` | 提交决策树反馈 |
| POST | `/analyze_diagnostic_completeness` | `{symptoms, diagnosis}` | `{success, completeness_score, recommendations}` | 分析诊疗完整性 |
| POST | `/extract_prescription_info` | `{prescription_text}` | `{success, extracted_info{...}}` | 提取处方信息 |
| POST | `/save_clinical_pattern` | `{pattern_data, doctor_id}` | `{success, pattern_id, message}` | 保存临床思维模式 |
| GET | `/get_doctor_patterns/{doctor_id}` | - | `{success, patterns{...}}` | 获取医生的临床模式 |
| DELETE | `/delete_clinical_pattern/{pattern_id}` | - | `{success, message}` | 删除临床模式 |
| GET | `/doctor-decision-tree/usage-stats/{doctor_id}` | - | `{success, stats{...}}` | 获取决策树使用统计 |
| GET | `/doctor-decision-tree/usage-detail/{pattern_id}` | - | `{success, detail{...}}` | 获取决策树使用详情 |
| GET | `/consultation/{consultation_id}/detail` | - | `{success, detail{...}}` | 获取问诊详情 |
| POST | `/ai_mindmap_generate` | `{content, focus_area?}` | `{success, mindmap{...}}` | 生成AI思维导图 |

### 3. 医生匹配 (/api/doctor-matching) - doctor_matching_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/recommend` | `{symptoms, patient_condition?, ...}` | `{success, recommended_doctors}` | 推荐适合的医生 |
| GET | `/available` | - | `{success, available_doctors}` | 获取可用医生列表 |
| GET | `/doctor/{doctor_id}` | - | `{success, doctor_info}` | 获取医生信息 |
| POST | `/assign` | `{patient_id, doctor_id, reason?}` | `{success, message, assignment}` | 分配医生给患者 |
| POST | `/preferences` | `{user_id, preferences{...}}` | `{success, message}` | 保存医生偏好设置 |
| GET | `/preferences/{patient_id}` | - | `{success, preferences}` | 获取患者医生偏好 |
| GET | `/specialties` | - | `{success, specialties}` | 获取医生专科列表 |

### 4. 决策树使用记录 (/api/doctor-decision-tree/usage) - decision_tree_usage_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/record-usage` | `{pattern_id, success, feedback?}` | `{success, message, usage_id}` | 记录决策树使用 |
| GET | `/stats/{pattern_id}` | - | `{success, stats{usage_count, success_rate, ...}}` | 获取决策树统计 |

---

## 五、症状分析

### 1. 症状分析 (/api/symptom) - symptom_analysis_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/analyze_relations` | `{main_symptom, context_symptoms?, include_ai_analysis?}` | `{success, message, data{main_symptom, direct_symptoms, accompanying_symptoms, cluster_info, total_relations, data_sources}, analysis_time_ms}` | 分析症状关系 |
| GET | `/cluster/{symptom_name}` | - | `{success, cluster{...}}` | 获取症状聚类 |
| GET | `/database/stats` | - | `{success, stats{total_symptoms, total_relations, ...}}` | 获取数据库统计 |
| POST | `/database/init` | - | `{success, message}` | 初始化症状数据库 |
| GET | `/quick_analyze/{symptom_name}` | - | `{success, analysis{...}}` | 快速分析症状 |

---

## 六、支付与代煎

### 1. 支付管理 (/api/payment) - payment_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/alipay/create` | `{prescription_id, amount, payment_method}` | `{success, data{payment_id, payment_url, order_no, amount}, message}` | 创建支付宝支付订单 |
| POST | `/wechat/create` | `{prescription_id, amount, payment_method}` | `{success, data{...}, message}` | 创建微信支付订单 |
| GET | `/order/{order_id}` | - | `{success, order{...}}` | 获取订单信息 |
| POST | `/order/{order_id}/verify` | `{transaction_id, payment_proof?}` | `{success, message, order{}}` | 验证支付 |
| GET | `/order/{order_id}/status` | - | `{success, order{status, payment_status, ...}}` | 查询订单状态 |

### 2. 代煎服务 (/api/decoction) - decoction_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/create-order` | `{prescription_id, decoction_type, shipping_info?, ...}` | `{success, message, decoction_order_id}` | 创建代煎订单 |
| GET | `/order/{decoction_order_id}` | - | `{success, order{...}}` | 获取代煎订单详情 |
| GET | `/order/{decoction_order_id}/tracking` | - | `{success, tracking{...}}` | 获取代煎订单追踪 |
| PUT | `/order/{decoction_order_id}/status` | `{status, notes?}` | `{success, message, order{}}` | 更新代煎订单状态 |
| POST | `/webhook` | `{event_type, order_id, status}` | `{success, message}` | 代煎服务商webhook回调 |
| GET | `/providers` | - | `{success, providers{...}}` | 获取代煎服务商列表 |
| GET | `/statistics` | - | `{success, stats{total_orders, total_value, ...}}` | 获取代煎统计 |
| POST | `/auto-process` | `{order_ids}` | `{success, message, processed}` | 自动处理代煎订单 |

---

## 七、评价与反馈

### 1. 评价管理 (/api/review) - review_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/create` | `{consultation_id, doctor_id, rating, review_text?, ...}` | `{success, message, review_id}` | 创建评价 |
| GET | `/doctor/{doctor_id}` | - | `{success, reviews, average_rating, total_reviews}` | 获取医生评价列表 |
| GET | `/summary/{doctor_id}` | - | `{success, summary{average_rating, total_reviews, rating_breakdown}}` | 获取评价汇总 |
| POST | `/reply` | `{review_id, reply_text}` | `{success, message}` | 回复评价 |
| GET | `/patient/{patient_id}` | - | `{success, reviews}` | 获取患者的评价 |
| GET | `/can-review/{consultation_id}` | - | `{success, can_review, reason?}` | 检查是否可评价 |
| POST | `/helpful/{review_id}` | `{helpful}` | `{success, message}` | 标记评价有帮助 |
| GET | `/stats/platform` | - | `{success, stats{...}}` | 获取平台评价统计 |

---

## 八、数据同步与备份

### 1. 用户数据同步 (/api/user-data-sync) - user_data_sync_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/full-sync` | `{user_id, device_id, data{...}}` | `{success, timestamp, sync_id, conflicts?}` | 全量同步 |
| POST | `/incremental-sync` | `{user_id, device_id, last_sync_time, changes{...}}` | `{success, timestamp, applied_changes}` | 增量同步 |
| POST | `/resolve-conflicts` | `{sync_id, resolution{...}}` | `{success, message}` | 解决冲突 |
| GET | `/sync-status/{user_id}` | - | `{success, status{last_sync, devices, conflicts}}` | 获取同步状态 |
| POST | `/emergency-backup/{user_id}` | - | `{success, backup_id, timestamp}` | 紧急备份 |
| POST | `/restore-backup/{backup_id}` | `{restore_type?}` | `{success, message, restored_items}` | 恢复备份 |

### 2. 数据迁移 (/api/data-migration) - data_migration_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/export` | `{user_id, export_type?, format?}` | `{success, export_id, download_url}` | 导出用户数据 |
| POST | `/import` | `{user_id, data{...}}` | `{success, message, imported_count}` | 导入用户数据 |
| POST | `/migrate` | `{source_user_id, target_user_id}` | `{success, message, migrated_count}` | 迁移用户数据 |
| GET | `/export-history/{user_id}` | - | `{success, exports[]}` | 获取导出历史 |
| GET | `/data-preview/{user_id}` | - | `{success, preview{...}}` | 获取数据预览 |
| DELETE | `/cleanup/{user_id}` | - | `{success, message}` | 清理用户数据 |

---

## 九、系统管理

### 1. 管理员接口 (/api/admin) - admin_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| GET | `/users` | - | `{success, users, total}` | 获取所有用户列表 |
| GET | `/user/{user_id}` | - | `{success, user}` | 获取用户详情 |
| PUT | `/user/{user_id}` | `{username?, display_name?, email?, phone_number?, account_status?}` | `{success, message, user}` | 更新用户信息 |
| POST | `/user/{user_id}/reset-password` | `{new_password}` | `{success, message}` | 重置用户密码 |
| POST | `/user/{user_id}/activate` | - | `{success, message}` | 激活用户账户 |
| POST | `/user/{user_id}/deactivate` | - | `{success, message}` | 停用用户账户 |
| GET | `/system-info` | - | `{success, info{database, cache, users, consultations, ...}}` | 获取系统信息 |
| GET | `/activity-logs` | `page?, size?, user_id?` | `{success, logs, total}` | 获取活动日志 |
| POST | `/maintenance/clear-cache` | - | `{success, message}` | 清空缓存 |
| POST | `/maintenance/optimize-db` | - | `{success, message}` | 优化数据库 |

### 2. 安全管理 (/api/security) - security_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/log-event` | `{event_type, description, user_id?, severity?}` | `{success, message, event_id}` | 记录安全事件 |
| GET | `/events` | `page?, size?, type?, user_id?` | `{success, events, total}` | 获取安全事件 |
| GET | `/alerts` | - | `{success, alerts}` | 获取安全告警 |
| POST | `/alerts/{alert_id}/resolve` | `{resolution}` | `{success, message}` | 解决告警 |
| GET | `/statistics` | - | `{success, stats{...}}` | 获取安全统计 |

### 3. 会话管理 (/api/session) - session_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/update` | `{user_id, session_data{...}}` | `{success, message, session}` | 更新会话 |
| GET | `/status/{user_id}` | - | `{success, status, last_activity}` | 获取会话状态 |
| DELETE | `/clear/{user_id}` | - | `{success, message}` | 清除会话 |
| GET | `/active` | - | `{success, active_sessions, total}` | 获取活跃会话 |

### 4. 数据库管理 (/api/database-management) - database_management_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| POST | `/overview` | `{database}` | `{success, data{tables, total_records}}` | 获取数据库概览 |
| POST | `/query` | `{database, table?, sql?}` | `{success, results[], columns}` | 查询数据 |
| GET | `/tables/{database}` | - | `{success, tables[]}` | 获取表列表 |
| GET | `/schema/{database}/{table}` | - | `{success, schema{columns, indexes, ...}}` | 获取表结构 |
| GET | `/analyze/{database}` | - | `{success, analysis{...}}` | 分析数据库 |

### 5. WebSocket同步 (/api/sync) - websocket_sync_routes.py

| 方法 | 端点 | 请求参数 | 响应格式 | 说明 |
|------|------|---------|---------|------|
| GET | `/connection-stats` | - | `{success, stats{active_connections, messages_sent, ...}}` | 获取连接统计 |
| POST | `/broadcast-to-user/{user_id}` | `{message, data}` | `{success, message, delivery_status}` | 广播消息给用户 |

---

## API统计总结

| 类别 | 模块数 | API端点数 |
|------|--------|---------|
| 认证与用户管理 | 4 | 23 |
| 问诊与对话管理 | 3 | 20 |
| 处方管理 | 4 | 25 |
| 医生相关接口 | 4 | 38 |
| 症状分析 | 1 | 5 |
| 支付与代煎 | 2 | 15 |
| 评价与反馈 | 1 | 8 |
| 数据同步与备份 | 2 | 12 |
| 系统管理 | 5 | 22 |
| **总计** | **28** | **168** |

---

## API使用规范

### 1. 请求格式
```
POST /api/endpoint HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Authorization: Bearer <session_id>

{
  "field1": "value1",
  "field2": "value2"
}
```

### 2. 响应格式标准
```json
{
  "success": true,
  "message": "操作成功",
  "data": {
    // 具体数据
  }
}
```

### 3. 错误响应
```json
{
  "success": false,
  "message": "错误描述",
  "error": "error_code"
}
```

### 4. 认证方式
- **Header认证**: `Authorization: Bearer <session_id>`
- **Cookie认证**: `session_token=<token>`
- **查询参数**: `?token=<session_id>`

### 5. 常见状态码
- `200`: 请求成功
- `400`: 请求参数错误
- `401`: 未登录或认证失败
- `403`: 权限不足
- `404`: 资源不存在
- `500`: 服务器错误

---

## 数据库表与API对应关系

| 主要表 | 相关API模块 |
|-------|-----------|
| unified_users | auth, admin |
| unified_sessions | auth, session |
| consultations | consultation, conversation_sync |
| prescriptions | prescription, prescription_ai, payment |
| prescriptions_ai_* | prescription_ai |
| doctors | doctor, doctor_matching |
| doctor_sessions | consultation, doctor_decision_tree |
| doctor_review_queue | prescription, doctor |
| orders | payment, decoction |
| decoction_orders | decoction |
| tcm_symptoms | symptom_analysis |
| symptom_relationships | symptom_analysis |
| security_events | security |
| audit_logs | admin |

---

*文档生成时间: 2025-10-29*
*下次更新时: 添加新API端点时应同步更新本清单*

