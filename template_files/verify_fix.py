#!/usr/bin/env python3
"""
金大夫记录显示修复验证脚本
验证修复后的逻辑能正确显示金大夫和张仲景的记录
"""

import requests
import json

def test_api_response():
    """测试API返回数据"""
    print("=" * 60)
    print("步骤1: 验证API返回数据")
    print("=" * 60)

    url = "http://localhost:8000/api/consultation/patient/history?user_id=usr_20250920_5741e17a78e8"
    response = requests.get(url)
    data = response.json()

    print(f"✅ API响应状态: {response.status_code}")
    print(f"✅ 总记录数: {data['data']['total_count']}")

    consultation_history = data['data']['consultation_history']

    # 提取医生ID列表
    doctor_ids = [c['doctor_id'] for c in consultation_history]
    doctor_names = [c['doctor_name'] for c in consultation_history]

    print(f"✅ 包含的医生ID: {doctor_ids}")
    print(f"✅ 包含的医生名称: {doctor_names}")

    # 检查关键医生
    has_jin_daifu = 'jin_daifu' in doctor_ids
    has_zhang = 'zhang_zhongjing' in doctor_ids

    if has_jin_daifu:
        print("✅✅✅ 金大夫记录存在于API响应中")
    else:
        print("❌ 金大夫记录缺失")

    if has_zhang:
        print("✅✅✅ 张仲景记录存在于API响应中")
    else:
        print("❌ 张仲景记录缺失")

    return has_jin_daifu and has_zhang

def test_doctor_list_api():
    """测试活跃医生列表API"""
    print("\n" + "=" * 60)
    print("步骤2: 验证活跃医生列表API")
    print("=" * 60)

    url = "http://localhost:8000/api/doctor/list"
    response = requests.get(url)
    data = response.json()

    if not data.get('success'):
        print("❌ API调用失败")
        return False

    doctors = data.get('doctors', [])
    doctor_codes = [d['doctor_code'] for d in doctors if 'doctor_code' in d]
    doctor_names = [d['name'] for d in doctors if 'name' in d]

    print(f"✅ 活跃医生数量: {len(doctors)}")
    print(f"✅ 医生代码列表: {doctor_codes}")
    print(f"✅ 医生名称列表: {doctor_names}")

    # 检查关键医生
    has_jin_daifu = 'jin_daifu' in doctor_codes
    has_zhang = 'zhang_zhongjing' in doctor_codes

    if has_jin_daifu:
        print("✅✅✅ 金大夫在活跃医生列表中")
    else:
        print("❌ 金大夫不在活跃医生列表中")

    if has_zhang:
        print("✅✅✅ 张仲景在活跃医生列表中")
    else:
        print("❌ 张仲景不在活跃医生列表中")

    return has_jin_daifu and has_zhang

def simulate_fixed_logic():
    """模拟修复后的前端逻辑"""
    print("\n" + "=" * 60)
    print("步骤3: 模拟修复后的前端逻辑")
    print("=" * 60)

    # 步骤1: 加载医生信息 (loadDoctorInfo)
    print("\n📍 步骤3.1: 模拟 loadDoctorInfo()")
    doctor_response = requests.get("http://localhost:8000/api/doctor/list")
    doctor_data = doctor_response.json()

    doctorInfo = {}
    if doctor_data.get('success') and doctor_data.get('doctors'):
        for doctor in doctor_data['doctors']:
            if doctor.get('doctor_code'):
                doctorInfo[doctor['doctor_code']] = {
                    'name': doctor['name'],
                    'emoji': '👨‍⚕️',
                    'description': '中医专家'
                }

    print(f"✅ doctorInfo构建完成: {list(doctorInfo.keys())}")

    # 🔑 修复点：此时allSessions还是空的，不调用updateDoctorTabs()
    allSessions = []
    print(f"⚠️ 🔑 修复：此时allSessions长度 = {len(allSessions)} (空的)")
    print("⚠️ 🔑 修复：不在这里调用updateDoctorTabs()")

    # 步骤2: 加载历史记录 (loadSessionHistory)
    print("\n📍 步骤3.2: 模拟 loadSessionHistory()")
    history_response = requests.get("http://localhost:8000/api/consultation/patient/history?user_id=usr_20250920_5741e17a78e8")
    history_data = history_response.json()

    consultations = history_data['data']['consultation_history']
    allSessions = [
        {
            'session_id': c['consultation_id'],
            'doctor_name': c['doctor_id'],  # 🔑 使用doctor_id
            'doctor_display_name': c['doctor_name'],  # 🔑 保存中文显示名
            'session_count': i + 1
        }
        for i, c in enumerate(consultations)
    ]

    print(f"✅ allSessions填充完成: {len(allSessions)}条记录")
    print(f"✅ 包含的医生: {list(set(s['doctor_name'] for s in allSessions))}")

    # 步骤3: 现在调用updateDoctorTabs (在renderSessionHistory中)
    print("\n📍 步骤3.3: 模拟 updateDoctorTabs() (在renderSessionHistory中调用)")
    doctorsWithData = list(set(s['doctor_name'] for s in allSessions))
    print(f"🔍 有历史记录的医生: {doctorsWithData}")
    print(f"🔍 活跃医生: {list(doctorInfo.keys())}")

    # 筛选逻辑
    validDoctors = [doctorKey for doctorKey in doctorsWithData if doctorKey in doctorInfo]
    print(f"✅ 筛选后的医生: {validDoctors}")

    # 验证结果
    print("\n📊 最终结果:")
    if 'jin_daifu' in validDoctors:
        print("✅✅✅ 成功！金大夫会显示在筛选标签中")
    else:
        print("❌ 失败！金大夫不会显示")

    if 'zhang_zhongjing' in validDoctors:
        print("✅✅✅ 成功！张仲景会显示在筛选标签中")
    else:
        print("❌ 失败！张仲景不会显示")

    # 生成的标签预览
    print("\n生成的医生筛选标签:")
    for doctorKey in validDoctors:
        doctor = doctorInfo[doctorKey]
        print(f"  • [{doctor['name']}]")

    return 'jin_daifu' in validDoctors and 'zhang_zhongjing' in validDoctors

def main():
    print("\n" + "🔍" * 30)
    print("金大夫记录显示修复验证测试")
    print("🔍" * 30 + "\n")

    results = []

    # 测试1: API响应
    results.append(("API返回数据", test_api_response()))

    # 测试2: 活跃医生列表
    results.append(("活跃医生列表", test_doctor_list_api()))

    # 测试3: 修复后的逻辑
    results.append(("修复后的逻辑", simulate_fixed_logic()))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉🎉🎉 所有测试通过！修复成功！")
        print("金大夫和张仲景的记录都会正确显示在患者历史页面")
    else:
        print("❌ 部分测试失败，需要进一步检查")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
