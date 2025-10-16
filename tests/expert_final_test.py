#!/usr/bin/env python3
"""
专家团最终测试
测试所有核心功能
"""

import requests
import sys
from datetime import datetime

BASE_URL = 'http://127.0.0.1:8080'

class ExpertTest:
    def __init__(self):
        self.session = requests.Session()
        self.passed = 0
        self.failed = 0
        
    def test(self, name, func):
        """执行测试"""
        try:
            func()
            print(f'✅ {name}')
            self.passed += 1
        except Exception as e:
            print(f'❌ {name}: {str(e)}')
            self.failed += 1
    
    def login(self, username, password):
        """登录"""
        r = self.session.post(f'{BASE_URL}/login', 
            data={'username': username, 'password': password},
            allow_redirects=False)
        if r.status_code not in [200, 302]:
            raise Exception(f'Login failed: {r.status_code}')
    
    def test_page_load(self, path, expected_text):
        """测试页面加载"""
        r = self.session.get(f'{BASE_URL}{path}')
        if r.status_code != 200:
            raise Exception(f'Status {r.status_code}')
        if expected_text and expected_text not in r.text:
            raise Exception(f'Missing text: {expected_text}')
    
    def run_all_tests(self):
        """运行所有测试"""
        print('\n🔍 专家团最终测试\n')
        
        # P1测试
        print('📋 P1功能测试:')
        self.test('登录页面', lambda: self.test_page_load('/login', '登录'))
        
        self.login('admin', '123456')
        
        self.test('管理员主页', lambda: self.test_page_load('/admin/dashboard', '主看板'))
        self.test('员工管理', lambda: self.test_page_load('/admin/employees', '员工管理'))
        self.test('业绩管理', lambda: self.test_page_load('/admin/performance', '业绩管理'))
        self.test('薪资统计', lambda: self.test_page_load('/admin/salary', '薪资统计'))
        
        # P2测试
        print('\n📋 P2功能测试:')
        self.test('Excel导入页', lambda: self.test_page_load('/admin/performance/import', 'Excel导入'))
        self.test('个人中心', lambda: self.login('a001', '123456') or self.test_page_load('/employee/profile', '个人中心'))
        
        # P3测试
        print('\n📋 P3功能测试:')
        self.login('admin', '123456')
        self.test('业绩分析', lambda: self.test_page_load('/reports/performance_analysis', '业绩分析'))
        self.test('薪资分析', lambda: self.test_page_load('/reports/salary_analysis', '薪资分析'))
        
        # 性能测试
        print('\n⚡ 性能测试:')
        import time
        start = time.time()
        self.test_page_load('/admin/dashboard', '主看板')
        elapsed = time.time() - start
        self.test(f'页面加载 <2秒', lambda: None if elapsed < 2 else (_ for _ in ()).throw(Exception(f'{elapsed:.2f}s')))
        
        # 总结
        print(f'\n📊 测试结果:')
        print(f'✅ 通过: {self.passed}')
        print(f'❌ 失败: {self.failed}')
        print(f'📈 通过率: {self.passed/(self.passed+self.failed)*100:.1f}%')
        
        return self.failed == 0

if __name__ == '__main__':
    tester = ExpertTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

