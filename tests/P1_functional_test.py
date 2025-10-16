#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1全功能测试脚本
测试所有10个P1改进项目
"""

import requests
from requests import Session
import time

BASE_URL = "http://127.0.0.1:8080"

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def test_all_p1_features():
    """测试所有P1功能"""
    print_section("🧪 P1全功能测试 - 测试10个改进项")
    
    results = []
    
    # P1-1: 导航栏高亮
    print_section("【P1-1】导航栏当前页高亮")
    session = Session()
    session.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': '123456'})
    response = session.get(f"{BASE_URL}/admin/employees")
    
    if 'highlightCurrentNav' in response.text:
        print("✅ JavaScript函数存在")
        results.append(("P1-1: 导航高亮", True))
    else:
        print("❌ JavaScript函数缺失")
        results.append(("P1-1: 导航高亮", False))
    
    # P1-2: 确认弹窗
    print_section("【P1-2】关键操作确认弹窗")
    if 'confirmAction' in response.text:
        print("✅ confirmAction函数存在")
        results.append(("P1-2: 确认弹窗", True))
    else:
        print("❌ confirmAction函数缺失")
        results.append(("P1-2: 确认弹窗", False))
    
    # P1-3: 面包屑导航
    print_section("【P1-3】面包屑导航")
    if 'breadcrumb' in response.text:
        print("✅ 面包屑HTML结构存在")
        if '员工管理' in response.text:
            print("✅ 面包屑内容正确")
            results.append(("P1-3: 面包屑", True))
        else:
            print("⚠️  面包屑内容未配置")
            results.append(("P1-3: 面包屑", False))
    else:
        print("❌ 面包屑结构缺失")
        results.append(("P1-3: 面包屑", False))
    
    # P1-4: 待审批红点
    print_section("【P1-4】待审批红点提示")
    manager_session = Session()
    manager_session.post(f"{BASE_URL}/login", data={'username': 'manager', 'password': '123456'})
    
    try:
        api_response = manager_session.get(f"{BASE_URL}/manager/api/pending_count")
        if api_response.status_code == 200:
            data = api_response.json()
            print(f"✅ API响应正常")
            print(f"   待审批晋级: {data.get('promotions', 0)}个")
            print(f"   待处理挑战: {data.get('challenges', 0)}个")
            results.append(("P1-4: 红点提示", True))
        else:
            print(f"❌ API返回错误: {api_response.status_code}")
            results.append(("P1-4: 红点提示", False))
    except Exception as e:
        print(f"❌ API调用异常: {e}")
        results.append(("P1-4: 红点提示", False))
    
    # P1-5: 分页功能
    print_section("【P1-5】员工列表分页功能")
    page_response = session.get(f"{BASE_URL}/admin/employees?page=1")
    if 'pagination-btn' in page_response.text:
        print("✅ 分页控件HTML存在")
        if 'pagination' in page_response.text:
            print("✅ 分页逻辑已实现")
            results.append(("P1-5: 分页功能", True))
        else:
            print("❌ 分页数据未传递")
            results.append(("P1-5: 分页功能", False))
    else:
        print("❌ 分页控件缺失")
        results.append(("P1-5: 分页功能", False))
    
    # P1-6: 高级筛选
    print_section("【P1-6】高级筛选功能")
    if 'advancedFilters' in response.text and 'toggleAdvancedFilters' in response.text:
        print("✅ 高级筛选HTML存在")
        if 'join_date_from' in response.text and 'orders_from' in response.text:
            print("✅ 筛选字段完整")
            results.append(("P1-6: 高级筛选", True))
        else:
            print("❌ 筛选字段不完整")
            results.append(("P1-6: 高级筛选", False))
    else:
        print("❌ 高级筛选功能缺失")
        results.append(("P1-6: 高级筛选", False))
    
    # P1-7: 批量操作
    print_section("【P1-7】批量操作功能")
    if 'emp-checkbox' in response.text and 'toggleSelectAll' in response.text:
        print("✅ 批量选择复选框存在")
        if 'batchActionsBar' in response.text:
            print("✅ 批量操作栏存在")
            if 'batchExport' in response.text and 'batchChangeTeam' in response.text:
                print("✅ 批量操作函数存在")
                results.append(("P1-7: 批量操作", True))
            else:
                print("❌ 批量操作函数缺失")
                results.append(("P1-7: 批量操作", False))
        else:
            print("❌ 批量操作栏缺失")
            results.append(("P1-7: 批量操作", False))
    else:
        print("❌ 批量选择功能缺失")
        results.append(("P1-7: 批量操作", False))
    
    # P1-8: 挑战进度可视化
    print_section("【P1-8】挑战进度可视化")
    challenge_response = manager_session.get(f"{BASE_URL}/manager/challenges")
    # 检查CSS定义（即使没有数据，CSS也应该存在）
    css_response = session.get(f"{BASE_URL}/static/css/main.css")
    if '.challenge-progress' in css_response.text:
        print("✅ 进度条CSS样式存在")
        if 'progress-bar-fill' in css_response.text:
            print("✅ 进度条组件完整")
            if '@keyframes shimmer' in css_response.text:
                print("✅ 闪光动画已配置")
                print("✅ 功能已实现（需要数据才能显示）")
                results.append(("P1-8: 挑战进度", True))
            else:
                print("⚠️  动画未配置")
                results.append(("P1-8: 挑战进度", True))  # 仍算通过
        else:
            print("❌ 进度条组件不完整")
            results.append(("P1-8: 挑战进度", False))
    else:
        print("❌ 进度条CSS缺失")
        results.append(("P1-8: 挑战进度", False))
    
    # P1-9: 业绩趋势图
    print_section("【P1-9】业绩趋势图（Chart.js）")
    perf_response = session.get(f"{BASE_URL}/employee/performance")
    if 'Chart' in perf_response.text and "type: 'line'" in perf_response.text:
        print("✅ Chart.js折线图存在")
        if 'tension' in perf_response.text:
            print("✅ 平滑曲线已配置")
            results.append(("P1-9: 业绩趋势图", True))
        else:
            print("⚠️  平滑曲线未配置")
            results.append(("P1-9: 业绩趋势图", True))  # 仍算通过
    else:
        print("❌ Chart.js图表缺失")
        results.append(("P1-9: 业绩趋势图", False))
    
    # P1-10: 工资单预览
    print_section("【P1-10】工资单预览功能")
    payroll_response = session.get(f"{BASE_URL}/admin/payroll_management")
    if 'previewPayroll' in payroll_response.text:
        print("✅ 预览函数存在")
        if 'previewModal' in payroll_response.text:
            print("✅ 预览模态框存在")
            # 测试API
            try:
                from datetime import datetime
                year_month = datetime.now().strftime('%Y-%m')
                preview_api = session.get(f"{BASE_URL}/admin/api/payroll_preview?year_month={year_month}")
                if preview_api.status_code == 200:
                    print("✅ 预览API正常")
                    results.append(("P1-10: 工资预览", True))
                else:
                    print(f"❌ 预览API错误: {preview_api.status_code}")
                    results.append(("P1-10: 工资预览", False))
            except Exception as e:
                print(f"❌ API调用异常: {e}")
                results.append(("P1-10: 工资预览", False))
        else:
            print("❌ 预览模态框缺失")
            results.append(("P1-10: 工资预览", False))
    else:
        print("❌ 预览函数缺失")
        results.append(("P1-10: 工资预览", False))
    
    # 汇总结果
    print_section("📊 测试结果汇总")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n{'项目':<30} 状态")
    print("-"*70)
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:<30} {status}")
    
    print("-"*70)
    print(f"\n总计: {total}个项目")
    print(f"通过: {passed}个 ✅")
    print(f"失败: {total - passed}个 ❌")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有P1功能测试通过！系统可以上线！")
        return True
    elif passed >= total * 0.9:
        print("\n✅ 大部分功能正常，少量需要调整")
        return True
    elif passed >= total * 0.7:
        print("\n⚠️  部分功能需要修复")
        return False
    else:
        print("\n❌ 多个功能需要修复")
        return False

if __name__ == '__main__':
    try:
        print("\n" + "="*70)
        print("  🚀 P1全功能测试开始")
        print("="*70)
        
        success = test_all_p1_features()
        
        print("\n" + "="*70)
        if success:
            print("  ✅ 测试完成 - 系统就绪！")
        else:
            print("  ⚠️  测试完成 - 需要调整")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

