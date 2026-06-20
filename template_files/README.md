# 测试和校验脚本说明

本目录包含了用于测试和验证TCM-AI处方审核流程的脚本文件。

## 脚本说明

### 1. test_prescription_workflow.py
**完整处方审核流程测试**

- **功能**: 测试从患者问诊到医生审核再到支付解锁的完整流程
- **测试步骤**:
  1. 患者问诊并获得AI处方
  2. 检查处方是否进入医生审核队列
  3. 模拟医生审核处理
  4. 检查患者端状态更新
  5. 模拟支付流程
  6. 验证最终状态
  7. 测试患者历史记录同步

- **使用方法**:
  ```bash
  cd /opt/tcm-ai
  python template_files/test_prescription_workflow.py
  ```

### 2. validate_database_consistency.py
**数据库一致性校验**

- **功能**: 检查数据库中各表之间的数据一致性
- **检查项目**:
  - 表结构完整性
  - 处方状态一致性
  - 审核队列一致性
  - 支付数据一致性
  - 问诊记录一致性
  - 用户数据一致性

- **使用方法**:
  ```bash
  cd /opt/tcm-ai
  python template_files/validate_database_consistency.py
  ```

### 3. test_api_endpoints.py
**API端点功能测试**

- **功能**: 测试关键API接口的可用性和基本功能
- **测试接口**:
  - 问诊服务状态
  - 患者问诊API
  - 患者历史记录API
  - 医生审核API
  - 支付创建API
  - 处方状态查询API
  - 系统健康检查

- **使用方法**:
  ```bash
  cd /opt/tcm-ai
  python template_files/test_api_endpoints.py
  ```

## 使用建议

### 开发环境测试
1. 启动TCM-AI服务: `sudo service tcm-ai start`
2. 运行完整流程测试: `python template_files/test_prescription_workflow.py`
3. 检查数据库一致性: `python template_files/validate_database_consistency.py`

### 部署前验证
1. 运行API端点测试确认服务可用
2. 运行数据库一致性检查确认数据完整
3. 运行完整流程测试确认业务逻辑正确

### 定期维护
- 建议每周运行数据库一致性检查
- 在系统更新后运行完整流程测试
- 监控API测试结果，及时发现服务问题

## 注意事项

1. **测试数据清理**: 所有测试脚本都会生成测试数据，运行后会询问是否清理
2. **权限要求**: 脚本需要访问数据库文件，确保有足够权限
3. **服务依赖**: 部分测试需要TCM-AI服务运行，请先确认服务状态
4. **结果解读**: 注意区分预期的错误（如认证失败）和真正的问题

## 故障排查

### 数据库连接失败
- 检查数据库文件路径: `/opt/tcm-ai/data/user_history.sqlite`
- 确认文件权限和可访问性

### API调用失败
- 确认服务运行: `sudo service tcm-ai status`
- 检查端口占用: `netstat -tlnp | grep 8000`
- 查看服务日志: `/opt/tcm-ai/logs/api.log`

### 测试失败
- 查看具体错误信息
- 检查相关数据库表结构
- 确认业务逻辑是否符合预期

## 扩展开发

如需添加新的测试用例：

1. 参考现有脚本的结构和日志格式
2. 添加适当的错误处理和数据清理
3. 更新此README文件说明新功能
4. 在主测试流程中集成新测试

## 联系支持

如遇到问题请检查：
1. TCM-AI系统日志
2. 数据库表结构是否完整
3. 相关API接口文档

---

*这些脚本是TCM-AI系统质量保证的重要工具，请在系统维护中定期使用。*