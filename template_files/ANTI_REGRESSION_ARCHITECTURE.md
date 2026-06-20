# TCM-AI 防回归架构设计

## 🎯 核心问题分析

### 回归原因
1. **职责边界模糊** - 格式化、支付检测、状态管理混在一起
2. **状态管理分散** - 支付状态、处方状态散布在多个文件
3. **缺乏隔离机制** - 修改一个功能影响其他功能
4. **测试覆盖不足** - 没有自动化回归测试

## 🏗️ 防回归架构设计

### 1. 核心原则

#### 1.1 单一职责原则 (SRP)
```javascript
// ❌ 错误：一个类承担多个职责
class PrescriptionRenderer {
    renderContent() {}      // 格式化职责
    containsPrescription() {} // 检测职责
    unlockPrescription() {}  // 支付职责
}

// ✅ 正确：职责分离
class PrescriptionFormatter {
    formatContent() {}
    formatStructure() {}
}

class PrescriptionDetector {
    containsPrescription() {}
    isTemporaryAdvice() {}
}

class PaymentManager {
    checkPaymentStatus() {}
    initiatePrescriptionPayment() {}
}
```

#### 1.2 开放封闭原则 (OCP)
```javascript
// ✅ 通过策略模式扩展功能，而不修改现有代码
class PrescriptionProcessor {
    constructor() {
        this.detectors = [];
        this.formatters = [];
        this.paymentHandlers = [];
    }
    
    addDetector(detector) { this.detectors.push(detector); }
    addFormatter(formatter) { this.formatters.push(formatter); }
    addPaymentHandler(handler) { this.paymentHandlers.push(handler); }
}
```

### 2. 分层架构设计

```
┌─────────────────────────────────────┐
│           表现层 (UI Layer)          │  消息显示、用户交互
├─────────────────────────────────────┤
│         业务逻辑层 (BLL)             │  处方检测、状态管理
├─────────────────────────────────────┤
│         服务层 (Service)             │  支付服务、格式化服务
├─────────────────────────────────────┤
│         数据层 (DAL)                │  状态存储、配置管理
└─────────────────────────────────────┘
```

### 3. 状态管理中心化

#### 3.1 统一状态管理器
```javascript
class PrescriptionStateManager {
    constructor() {
        this.state = {
            currentPrescription: null,
            paymentStatus: 'unpaid',
            prescriptionType: 'temporary', // temporary, complete
            detectionRules: this.loadDetectionRules()
        };
        this.listeners = [];
    }
    
    // 🔒 封装状态变更，防止外部直接修改
    updatePrescriptionState(prescription, type, paymentStatus) {
        const oldState = { ...this.state };
        
        this.state.currentPrescription = prescription;
        this.state.prescriptionType = type;
        this.state.paymentStatus = paymentStatus;
        
        this.notifyListeners(oldState, this.state);
        this.persistState(); // 持久化状态
    }
    
    // 🔍 统一的处方检测逻辑
    detectPrescriptionType(content) {
        const rules = this.state.detectionRules;
        
        if (this.isTemporaryAdvice(content, rules.temporary)) {
            return 'temporary';
        }
        
        if (this.isCompletePrescription(content, rules.complete)) {
            return 'complete';
        }
        
        return 'none';
    }
}
```

### 4. 事件驱动架构

#### 4.1 事件系统设计
```javascript
class PrescriptionEventSystem {
    constructor() {
        this.events = new Map();
    }
    
    // 注册事件监听器
    on(eventType, handler) {
        if (!this.events.has(eventType)) {
            this.events.set(eventType, []);
        }
        this.events.get(eventType).push(handler);
    }
    
    // 发布事件
    emit(eventType, data) {
        const handlers = this.events.get(eventType) || [];
        handlers.forEach(handler => {
            try {
                handler(data);
            } catch (error) {
                console.error(`Event handler error for ${eventType}:`, error);
            }
        });
    }
}

// 使用示例
const eventSystem = new PrescriptionEventSystem();

// 格式化组件监听
eventSystem.on('prescription.detected', (data) => {
    if (data.type === 'complete') {
        // 显示支付界面
        showPaymentInterface(data.prescription);
    }
});

// 支付组件监听
eventSystem.on('payment.completed', (data) => {
    // 更新显示状态
    updatePrescriptionDisplay(data.prescriptionId, true);
});
```

### 5. 配置驱动模式

#### 5.1 检测规则配置化
```javascript
// prescription-detection-config.js
const DETECTION_CONFIG = {
    version: "2.1.0",
    
    temporaryAdvice: {
        keywords: [
            '初步处方建议', '待确认', '若您能提供', '请补充',
            '暂拟方药', '初步考虑', '待详诊后', '舌象信息后'
        ],
        patterns: [
            /初步建议.*待.*确认/i,
            /补充.*信息.*后.*处方/i
        ]
    },
    
    completePrescription: {
        requiredElements: {
            keywords: ['处方如下', '方剂组成', '【君药】'],
            dosagePattern: /\d+[克g]\s*[，,，。]/gi,
            herbCount: 4 // 至少4味药材
        },
        exclusions: {
            temporaryKeywords: true, // 排除临时建议
            incompleteStructure: true
        }
    },
    
    paymentTriggers: {
        conditions: [
            'completePrescription && !temporaryAdvice',
            '!isPaid',
            'herbCount >= 4'
        ]
    }
};
```

### 6. 防回归测试策略

#### 6.1 自动化测试套件
```javascript
// prescription-regression-tests.js
describe('处方支付功能回归测试', () => {
    let stateManager, eventSystem, detector, formatter;
    
    beforeEach(() => {
        // 初始化测试环境
        stateManager = new PrescriptionStateManager();
        eventSystem = new PrescriptionEventSystem();
        detector = new PrescriptionDetector(DETECTION_CONFIG);
        formatter = new PrescriptionFormatter();
    });
    
    describe('核心场景测试', () => {
        it('应该正确检测完整处方并触发支付', () => {
            const completePrescription = `
                ## 处方建议
                
                ### 【君药】
                党参 15g - 大补元气
                白术 12g - 健脾燥湿
                
                ### 【臣药】
                茯苓 15g - 健脾渗湿
                山药 20g - 补脾养胃
            `;
            
            const result = detector.detectPrescriptionType(completePrescription);
            expect(result).toBe('complete');
            
            const needsPayment = stateManager.shouldTriggerPayment(
                completePrescription, false
            );
            expect(needsPayment).toBe(true);
        });
        
        it('应该正确识别临时建议且不触发支付', () => {
            const temporaryAdvice = `
                ## 初步处方建议（待确认）
                
                根据您的症状，初步考虑：
                党参 15g、白术 12g
                
                请补充舌象信息后确认最终处方。
            `;
            
            const result = detector.detectPrescriptionType(temporaryAdvice);
            expect(result).toBe('temporary');
            
            const needsPayment = stateManager.shouldTriggerPayment(
                temporaryAdvice, false
            );
            expect(needsPayment).toBe(false);
        });
        
        it('格式化功能不应影响支付检测逻辑', () => {
            const originalContent = "党参 15g\n白术 12g\n处方如下：上述药材";
            
            // 格式化前检测
            const beforeFormat = detector.containsPrescription(originalContent);
            
            // 执行格式化
            const formatted = formatter.formatContent(originalContent);
            
            // 格式化后检测
            const afterFormat = detector.containsPrescription(originalContent);
            
            // 检测结果应该保持一致
            expect(beforeFormat).toBe(afterFormat);
        });
    });
    
    describe('边界情况测试', () => {
        it('应该处理混合内容（诊断+临时建议）', () => {
            const mixedContent = `
                ## 辨证分析
                您的症状属于脾胃虚弱证
                
                ## 初步处方建议
                党参 15g、白术 12g
                
                请提供舌象后确认最终处方
            `;
            
            const result = detector.detectPrescriptionType(mixedContent);
            expect(result).toBe('temporary'); // 应识别为临时建议
        });
    });
});
```

#### 6.2 集成测试
```javascript
// integration-test.js
describe('处方支付完整流程集成测试', () => {
    it('完整的处方→支付→解锁流程', async () => {
        // 1. 模拟AI回复完整处方
        const aiReply = createCompletePrescription();
        
        // 2. 检测处方类型
        const detected = await processAIReply(aiReply);
        expect(detected.needsPayment).toBe(true);
        
        // 3. 显示支付界面
        const paymentModal = await showPaymentInterface(detected.prescription);
        expect(paymentModal.isVisible).toBe(true);
        
        // 4. 模拟支付完成
        await simulatePaymentSuccess(detected.prescriptionId);
        
        // 5. 验证处方解锁
        const isUnlocked = await checkPrescriptionUnlocked(detected.prescriptionId);
        expect(isUnlocked).toBe(true);
    });
});
```

## 🔧 实施计划

### Phase 1: 核心重构 (本次修复)
1. ✅ 修复当前支付功能回归问题
2. ✅ 分离检测逻辑和显示逻辑
3. ⏳ 创建统一状态管理

### Phase 2: 架构升级 (下一阶段)
1. 实施事件驱动架构
2. 配置驱动的检测规则
3. 建立自动化测试套件

### Phase 3: 长期优化
1. 性能监控和优化
2. 用户体验持续改进
3. 架构文档和最佳实践

## 🚨 关键控制点

### 1. 代码审查检查清单
- [ ] 新功能是否遵循单一职责原则？
- [ ] 是否有足够的单元测试覆盖？
- [ ] 是否会影响现有的支付流程？
- [ ] 配置变更是否向后兼容？

### 2. 部署前验证
- [ ] 运行完整回归测试套件
- [ ] 验证关键用户路径
- [ ] 检查性能指标
- [ ] 确认配置正确性

### 3. 监控指标
- 处方检测准确率
- 支付转化率
- 用户体验评分
- 系统错误率

## 📋 最佳实践

1. **功能隔离**: 每个功能模块独立，通过事件通信
2. **配置驱动**: 业务规则配置化，避免硬编码
3. **测试优先**: 关键功能必须有自动化测试
4. **版本控制**: 重要变更必须有清晰的版本标记
5. **监控告警**: 关键指标异常时及时告警

通过这套防回归架构，我们可以确保：
- 🛡️ 功能独立性：修改一个功能不会影响其他功能
- 🔍 可测试性：每个组件都可以独立测试
- 📈 可维护性：清晰的职责划分，易于维护和扩展
- ⚡ 高性能：事件驱动，避免不必要的耦合