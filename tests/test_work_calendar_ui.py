#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作日配置UI功能测试
测试新的交互式日历配置功能
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = 'http://localhost:8080'
TEST_USERNAME = 'admin'
TEST_PASSWORD = '123456'

class WorkCalendarTester:
    def __init__(self):
        self.session = requests.Session()
        self.logged_in = False
    
    def login(self):
        """登录系统"""
        print("🔐 正在登录...")
        response = self.session.post(
            f'{BASE_URL}/login',
            data={
                'username': TEST_USERNAME,
                'password': TEST_PASSWORD
            },
            allow_redirects=True
        )
        
        if response.status_code == 200 or 'admin' in response.text.lower():
            self.logged_in = True
            print("✅ 登录成功")
            return True
        else:
            print(f"❌ 登录失败 (HTTP {response.status_code})")
            return False
    
    def test_page_load(self):
        """测试页面加载"""
        print("\n📄 测试1: 页面加载")
        response = self.session.get(f'{BASE_URL}/admin/work_calendar')
        
        if response.status_code == 200:
            # 检查关键元素
            checks = [
                ('工作日配置' in response.text, '页面标题'),
                ('calendar-table' in response.text, '日历表格'),
                ('mode-selector' in response.text, '模式选择器'),
                ('action-bar' in response.text, '操作栏'),
                ('confirmModal' in response.text, '确认对话框'),
            ]
            
            all_pass = True
            for check, name in checks:
                if check:
                    print(f"  ✅ {name}存在")
                else:
                    print(f"  ❌ {name}缺失")
                    all_pass = False
            
            return all_pass
        else:
            print(f"  ❌ 页面加载失败 (HTTP {response.status_code})")
            return False
    
    def test_batch_save_api(self):
        """测试批量保存API"""
        print("\n🔧 测试2: 批量保存API")
        
        # 准备测试数据
        test_dates = [
            (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            for i in range(1, 4)
        ]
        
        year_month = test_dates[0][:7]
        
        data = {
            'dates': test_dates,
            'is_workday': False,  # 设为假期
            'recalculate_performance': False,
            'year_month': year_month
        }
        
        response = self.session.post(
            f'{BASE_URL}/admin/work_calendar/batch_save',
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"  ✅ 批量保存成功")
                print(f"     - 配置天数: {result.get('affected_dates')}")
                print(f"     - 影响员工: {result.get('affected_employees', 0)}")
                return True
            else:
                print(f"  ❌ 保存失败: {result.get('message')}")
                return False
        else:
            print(f"  ❌ API请求失败 (HTTP {response.status_code})")
            print(f"     响应: {response.text[:200]}")
            return False
    
    def test_batch_save_with_recalculation(self):
        """测试带业绩重算的批量保存"""
        print("\n🔄 测试3: 批量保存 + 业绩重算")
        
        # 使用上个月的日期进行测试
        last_month = (datetime.now().replace(day=1) - timedelta(days=1))
        year_month = last_month.strftime('%Y-%m')
        
        test_dates = [
            f"{year_month}-{str(i).zfill(2)}"
            for i in range(1, 4)
        ]
        
        data = {
            'dates': test_dates,
            'is_workday': True,  # 设为工作日
            'recalculate_performance': True,
            'year_month': year_month
        }
        
        response = self.session.post(
            f'{BASE_URL}/admin/work_calendar/batch_save',
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"  ✅ 保存并重算成功")
                print(f"     - 配置天数: {result.get('affected_dates')}")
                print(f"     - 重算员工: {result.get('affected_employees', 0)}")
                return True
            else:
                print(f"  ❌ 失败: {result.get('message')}")
                return False
        else:
            print(f"  ❌ API请求失败 (HTTP {response.status_code})")
            return False
    
    def test_month_switch(self):
        """测试月份切换"""
        print("\n📅 测试4: 月份切换")
        
        # 测试不同月份
        months = [
            '2025-10',
            '2025-11',
            '2025-12'
        ]
        
        all_pass = True
        for month in months:
            response = self.session.get(
                f'{BASE_URL}/admin/work_calendar',
                params={'year_month': month}
            )
            
            if response.status_code == 200 and month in response.text:
                print(f"  ✅ {month} 加载成功")
            else:
                print(f"  ❌ {month} 加载失败")
                all_pass = False
        
        return all_pass
    
    def test_edge_cases(self):
        """测试边界情况"""
        print("\n⚠️  测试5: 边界情况")
        
        tests = []
        
        # 1. 空日期列表
        response = self.session.post(
            f'{BASE_URL}/admin/work_calendar/batch_save',
            json={
                'dates': [],
                'is_workday': True,
                'year_month': '2025-10'
            },
            headers={'Content-Type': 'application/json'}
        )
        tests.append(('空日期列表', response.status_code == 400))
        
        # 2. 无效日期格式
        response = self.session.post(
            f'{BASE_URL}/admin/work_calendar/batch_save',
            json={
                'dates': ['invalid-date'],
                'is_workday': True,
                'year_month': '2025-10'
            },
            headers={'Content-Type': 'application/json'}
        )
        tests.append(('无效日期格式', response.status_code in [400, 500]))
        
        for test_name, passed in tests:
            if passed:
                print(f"  ✅ {test_name}处理正确")
            else:
                print(f"  ❌ {test_name}处理错误")
        
        return all(result for _, result in tests)
    
    def run_all_tests(self):
        """运行所有测试"""
        print("="*60)
        print("工作日配置功能测试")
        print("="*60)
        
        if not self.login():
            print("\n❌ 登录失败，无法继续测试")
            return False
        
        tests = [
            self.test_page_load,
            self.test_batch_save_api,
            self.test_batch_save_with_recalculation,
            self.test_month_switch,
            self.test_edge_cases,
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"\n❌ 测试异常: {str(e)}")
                results.append(False)
        
        # 统计结果
        print("\n" + "="*60)
        print("测试结果汇总")
        print("="*60)
        
        passed = sum(results)
        total = len(results)
        
        print(f"\n✅ 通过: {passed}/{total}")
        print(f"❌ 失败: {total - passed}/{total}")
        
        if passed == total:
            print("\n🎉 所有测试通过！")
        else:
            print(f"\n⚠️  有 {total - passed} 个测试失败")
        
        return passed == total


if __name__ == '__main__':
    tester = WorkCalendarTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)

