#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试操作日志优化功能
"""

import requests
import sys
from datetime import date, timedelta

BASE_URL = "http://localhost:8080"

def test_admin_login():
    """测试管理员登录"""
    print("1️⃣  测试管理员登录...")
    session = requests.Session()
    login_url = f"{BASE_URL}/login"
    login_data = {'username': 'admin', 'password': '123456'}
    response = session.post(login_url, data=login_data, allow_redirects=False)
    
    if response.status_code == 302 and '/admin/dashboard' in response.headers.get('Location', ''):
        print("  ✅ 管理员登录成功")
        return session
    else:
        print("  ❌ 管理员登录失败")
        return None

def test_manager_login():
    """测试经理登录"""
    print("\n2️⃣  测试经理登录...")
    session = requests.Session()
    login_url = f"{BASE_URL}/login"
    login_data = {'username': 'manager', 'password': '123456'}
    response = session.post(login_url, data=login_data, allow_redirects=False)
    
    if response.status_code == 302:
        print("  ✅ 经理登录成功")
        return session
    else:
        print("  ❌ 经理登录失败")
        return None

def test_page_load(session, role):
    """测试页面加载"""
    print(f"\n3️⃣  测试{role}页面加载...")
    response = session.get(f"{BASE_URL}/manager/logs")
    
    if response.status_code == 200:
        print(f"  ✅ 页面加载成功 (HTTP {response.status_code})")
        
        # 检查关键元素
        checks = {
            '标题存在': '操作日志' in response.text,
            '筛选器存在': 'filter-bar' in response.text,
            '表格存在': 'logs-table' in response.text,
            '操作类型筛选': 'operation_type' in response.text,
            '日期筛选': 'start_date' in response.text,
            '搜索框': 'search' in response.text,
            '分页': 'pagination' in response.text,
            '导出按钮': '导出CSV' in response.text
        }
        
        all_passed = True
        for check_name, result in checks.items():
            if result:
                print(f"    ✅ {check_name}")
            else:
                print(f"    ❌ {check_name}")
                all_passed = False
        
        # 检查管理员特有的操作人列
        if role == '管理员':
            if '操作人' in response.text and 'operator_id' in response.text:
                print("    ✅ 操作人筛选器（管理员专属）")
            else:
                print("    ❌ 缺少操作人筛选器")
                all_passed = False
        
        return all_passed
    else:
        print(f"  ❌ 页面加载失败 (HTTP {response.status_code})")
        return False

def test_filtering(session):
    """测试筛选功能"""
    print("\n4️⃣  测试筛选功能...")
    
    # 测试操作类型筛选
    response = session.get(f"{BASE_URL}/manager/logs?operation_type=calendar")
    if response.status_code == 200:
        print("  ✅ 操作类型筛选正常")
    else:
        print("  ❌ 操作类型筛选失败")
        return False
    
    # 测试日期范围筛选
    today = date.today()
    start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    response = session.get(f"{BASE_URL}/manager/logs?start_date={start_date}&end_date={end_date}")
    if response.status_code == 200:
        print("  ✅ 日期范围筛选正常")
    else:
        print("  ❌ 日期范围筛选失败")
        return False
    
    # 测试搜索功能
    response = session.get(f"{BASE_URL}/manager/logs?search=测试")
    if response.status_code == 200:
        print("  ✅ 搜索功能正常")
    else:
        print("  ❌ 搜索功能失败")
        return False
    
    return True

def test_pagination(session):
    """测试分页功能"""
    print("\n5️⃣  测试分页功能...")
    
    # 测试每页数量
    response = session.get(f"{BASE_URL}/manager/logs?per_page=25")
    if response.status_code == 200 and 'per_page' in response.text:
        print("  ✅ 每页数量设置正常")
    else:
        print("  ❌ 每页数量设置失败")
        return False
    
    # 测试页码跳转
    response = session.get(f"{BASE_URL}/manager/logs?page=1")
    if response.status_code == 200:
        print("  ✅ 页码跳转正常")
    else:
        print("  ❌ 页码跳转失败")
        return False
    
    return True

def test_export(session):
    """测试导出功能"""
    print("\n6️⃣  测试导出功能...")
    
    response = session.get(f"{BASE_URL}/manager/logs/export")
    if response.status_code == 200 and 'text/csv' in response.headers.get('Content-Type', ''):
        print("  ✅ CSV导出正常")
        print(f"    文件大小: {len(response.content)} 字节")
        return True
    else:
        print("  ❌ CSV导出失败")
        return False

def test_combined_filters(session):
    """测试组合筛选"""
    print("\n7️⃣  测试组合筛选...")
    
    today = date.today()
    params = {
        'operation_type': 'calendar',
        'start_date': (today - timedelta(days=30)).strftime('%Y-%m-%d'),
        'end_date': today.strftime('%Y-%m-%d'),
        'per_page': 50,
        'page': 1
    }
    
    response = session.get(f"{BASE_URL}/manager/logs", params=params)
    if response.status_code == 200:
        print("  ✅ 组合筛选正常")
        return True
    else:
        print("  ❌ 组合筛选失败")
        return False

def main():
    print("=" * 70)
    print("操作日志优化功能测试")
    print("=" * 70)
    
    # 测试管理员视角
    print("\n【测试管理员视角】")
    admin_session = test_admin_login()
    if not admin_session:
        print("\n❌ 管理员登录失败，无法继续测试")
        sys.exit(1)
    
    admin_results = {
        'page_load': test_page_load(admin_session, '管理员'),
        'filtering': test_filtering(admin_session),
        'pagination': test_pagination(admin_session),
        'export': test_export(admin_session),
        'combined': test_combined_filters(admin_session)
    }
    
    # 测试经理视角
    print("\n" + "=" * 70)
    print("【测试经理视角】")
    manager_session = test_manager_login()
    if not manager_session:
        print("\n⚠️  经理登录失败，跳过经理视角测试")
        manager_results = {}
    else:
        manager_results = {
            'page_load': test_page_load(manager_session, '经理'),
            'filtering': test_filtering(manager_session),
            'pagination': test_pagination(manager_session),
            'export': test_export(manager_session)
        }
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    
    print("\n【管理员视角】")
    for test_name, result in admin_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    if manager_results:
        print("\n【经理视角】")
        for test_name, result in manager_results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {test_name}: {status}")
    
    # 统计
    admin_passed = sum(1 for r in admin_results.values() if r)
    admin_total = len(admin_results)
    
    if manager_results:
        manager_passed = sum(1 for r in manager_results.values() if r)
        manager_total = len(manager_results)
        total_passed = admin_passed + manager_passed
        total_tests = admin_total + manager_total
    else:
        total_passed = admin_passed
        total_tests = admin_total
    
    print("\n" + "=" * 70)
    print(f"总体通过率: {total_passed}/{total_tests} ({total_passed*100//total_tests}%)")
    print("=" * 70)
    
    if total_passed == total_tests:
        print("\n✅ 所有测试通过！操作日志优化功能正常。")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total_tests - total_passed} 个测试失败，请检查相关功能。")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到服务器")
        print("请确保Flask应用正在运行: python3 app.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

