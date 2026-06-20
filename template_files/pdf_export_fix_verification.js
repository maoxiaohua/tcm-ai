// PDF导出功能修复验证脚本
// 用于测试修复后的PDF导出功能是否正确处理实际数据

// 模拟新版多模态API返回的数据格式
const mockMultimodalResult = {
    success: true,
    document_analysis: {
        type: "中药处方",
        quality: "高清",
        confidence: 0.92
    },
    prescription: {
        herbs: [
            { name: "黄芪", dosage: "30", unit: "g", processing: "生用" },
            { name: "当归", dosage: "15", unit: "g" },
            { name: "川芎", dosage: "10", unit: "g" },
            { name: "白芍", dosage: "12", unit: "g" },
            { name: "甘草", dosage: "6", unit: "g" }
        ],
        total_herbs: 5,
        estimated_cost: "45",
        usage: {
            method: "水煎服",
            frequency: "每日1剂",
            duration: "7-10天",
            timing: "饭后温服"
        }
    },
    diagnosis: {
        primary: "气血两虚",
        tcm_syndrome: "脾胃虚弱，气血不足",
        symptoms: ["乏力", "面色萎黄", "食欲不振"]
    },
    formula_analysis: {
        roles: {
            "君药": [
                { name: "黄芪", dosage: "30g", reason: "大补元气，为君药", confidence: 0.95 }
            ],
            "臣药": [
                { name: "当归", dosage: "15g", reason: "补血活血，为臣药", confidence: 0.88 }
            ],
            "佐药": [
                { name: "川芎", dosage: "10g", reason: "行气活血，为佐药", confidence: 0.82 },
                { name: "白芍", dosage: "12g", reason: "养血敛阴，为佐药", confidence: 0.85 }
            ],
            "使药": [
                { name: "甘草", dosage: "6g", reason: "调和诸药，为使药", confidence: 0.90 }
            ]
        },
        summary: {
            formula_characteristics: ["补气养血", "健脾益胃"],
            compatibility_analysis: ["配伍合理", "君臣佐使明确"]
        },
        confidence_level: "high"
    },
    clinical_analysis: {
        formula_type: "补益剂",
        therapeutic_principle: "补气养血，健脾益胃",
        expected_effects: ["改善乏力", "增进食欲", "改善面色"],
        modification_suggestions: ["气虚重者可加党参", "血虚重者可加熟地"]
    },
    safety_analysis: {
        overall_safety: "安全",
        warnings: [],
        contraindications: [],
        interactions: [],
        special_populations: ["孕妇慎用"]
    },
    patient_info: {
        name: "张三"
    },
    medical_info: {
        hospital: "北京中医医院"
    }
};

// 模拟旧版OCR+检查API返回的数据格式
const mockOCRResult = {
    success: true,
    ocr_result: {
        success: true,
        original_text: "黄芪30g 当归15g 川芎10g 白芍12g 甘草6g",
        corrected_text: "黄芪 30g\n当归 15g\n川芎 10g\n白芍 12g\n甘草 6g",
        confidence: 0.89,
        corrections_made: ["修正了药材间的分隔符", "标准化了剂量格式"]
    },
    prescription_check: {
        success: true,
        data: {
            prescription: {
                herbs: [
                    { name: "黄芪", dosage: "30", unit: "g" },
                    { name: "当归", dosage: "15", unit: "g" },
                    { name: "川芎", dosage: "10", unit: "g" },
                    { name: "白芍", dosage: "12", unit: "g" },
                    { name: "甘草", dosage: "6", unit: "g" }
                ]
            },
            tcm_analysis: {
                syndrome_analysis: {
                    primary_syndrome: "脾胃虚弱，气血不足证"
                },
                prescription_pattern: "四君子汤加味方",
                professional_comments: [
                    "方中黄芪补气为君，当归养血为臣",
                    "川芎、白芍活血养血，甘草调和诸药",
                    "整体配伍合理，适用于气血两虚证"
                ]
            },
            detailed_analysis: {
                herb_roles_analysis: {
                    "君药": [
                        { name: "黄芪", dosage: "30g", role_reason: "大补元气，健脾益胃" }
                    ],
                    "臣药": [
                        { name: "当归", dosage: "15g", role_reason: "补血活血，助君药补益" }
                    ],
                    "佐药": [
                        { name: "川芎", dosage: "10g", role_reason: "行气活血，防止补血壅滞" },
                        { name: "白芍", dosage: "12g", role_reason: "养血敛阴，平肝止痛" }
                    ],
                    "使药": [
                        { name: "甘草", dosage: "6g", role_reason: "调和诸药，缓急止痛" }
                    ]
                },
                dosage_analysis: {
                    total_dosage: "73g",
                    dosage_range_ratio: "1:5:2:2.4:1.2",
                    ratio_analysis: [
                        "君药用量最大，符合配伍原则",
                        "各药用量比例合理",
                        "总剂量适中，适合慢性调理"
                    ]
                },
                therapeutic_analysis: {
                    treatment_methods: ["补气", "养血", "健脾"],
                    therapeutic_focus: ["改善气血不足", "增强脾胃功能"],
                    expected_effects: ["精神好转", "食欲改善", "面色红润"]
                }
            },
            safety_check: {
                is_safe: true,
                warnings: [],
                errors: []
            }
        }
    },
    processing_summary: {
        ocr_confidence: 0.89,
        prescription_found: true,
        safety_passed: true,
        total_herbs: 5
    }
};

// 测试函数
function testPDFGeneration() {
    console.log("=== PDF导出功能修复验证 ===");
    
    // 测试1: 新版多模态API格式
    console.log("\n1. 测试新版多模态API格式...");
    try {
        // 模拟调用修复后的函数
        const html1 = generatePDFReportContent(mockMultimodalResult);
        console.log("✅ 新版格式处理成功");
        console.log("- 检测到document_analysis:", !!mockMultimodalResult.document_analysis);
        console.log("- 药材数量:", mockMultimodalResult.prescription?.herbs?.length || 0);
        console.log("- 君臣佐使分析:", !!mockMultimodalResult.formula_analysis?.roles);
        console.log("- 安全分析:", !!mockMultimodalResult.safety_analysis);
    } catch (error) {
        console.log("❌ 新版格式处理失败:", error.message);
    }
    
    // 测试2: 旧版OCR+检查API格式
    console.log("\n2. 测试旧版OCR+检查API格式...");
    try {
        // 模拟调用修复后的函数
        const html2 = generatePDFReportContent(mockOCRResult);
        console.log("✅ 旧版格式处理成功");
        console.log("- 检测到ocr_result:", !!mockOCRResult.ocr_result);
        console.log("- 药材数量:", mockOCRResult.prescription_check?.data?.prescription?.herbs?.length || 0);
        console.log("- 君臣佐使分析:", !!mockOCRResult.prescription_check?.data?.detailed_analysis?.herb_roles_analysis);
        console.log("- 安全检查:", !!mockOCRResult.prescription_check?.data?.safety_check);
    } catch (error) {
        console.log("❌ 旧版格式处理失败:", error.message);
    }
    
    // 测试3: 空数据处理
    console.log("\n3. 测试空数据处理...");
    try {
        const html3 = generatePDFReportContent({});
        console.log("✅ 空数据处理成功，应显示错误提示");
    } catch (error) {
        console.log("❌ 空数据处理失败:", error.message);
    }
    
    console.log("\n=== 验证完成 ===");
}

// 验证关键数据路径
function verifyDataPaths() {
    console.log("\n=== 数据路径验证 ===");
    
    // 新版格式路径
    const newPaths = [
        "document_analysis.confidence",
        "prescription.herbs",
        "diagnosis.primary",
        "formula_analysis.roles",
        "clinical_analysis.formula_type",
        "safety_analysis.overall_safety"
    ];
    
    console.log("新版格式数据路径:");
    newPaths.forEach(path => {
        const value = getNestedValue(mockMultimodalResult, path);
        console.log(`- ${path}: ${value !== undefined ? '✅' : '❌'}`);
    });
    
    // 旧版格式路径
    const oldPaths = [
        "ocr_result.confidence",
        "prescription_check.data.prescription.herbs",
        "prescription_check.data.tcm_analysis.syndrome_analysis",
        "prescription_check.data.detailed_analysis.herb_roles_analysis",
        "prescription_check.data.detailed_analysis.therapeutic_analysis",
        "prescription_check.data.safety_check.is_safe"
    ];
    
    console.log("\n旧版格式数据路径:");
    oldPaths.forEach(path => {
        const value = getNestedValue(mockOCRResult, path);
        console.log(`- ${path}: ${value !== undefined ? '✅' : '❌'}`);
    });
}

// 辅助函数：获取嵌套对象值
function getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => {
        return current && current[key] !== undefined ? current[key] : undefined;
    }, obj);
}

// 如果在浏览器环境中运行
if (typeof window !== 'undefined') {
    // 在控制台中运行测试
    window.testPDFExportFix = {
        testPDFGeneration,
        verifyDataPaths,
        mockMultimodalResult,
        mockOCRResult
    };
    
    console.log("PDF导出修复验证工具已加载");
    console.log("使用 window.testPDFExportFix.testPDFGeneration() 开始测试");
} else {
    // Node.js环境
    module.exports = {
        testPDFGeneration,
        verifyDataPaths,
        mockMultimodalResult,
        mockOCRResult
    };
}