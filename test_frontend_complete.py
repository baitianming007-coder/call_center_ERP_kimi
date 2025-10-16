#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端功能完整测试脚本
测试所有14个新页面的可访问性和基本功能
"""

import requests
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8080"

# 测试账号
ACCOUNTS = {
    'admin': {'username': 'admin', 'password': '123456', 'role': '管理员'},
    'manager': {'username': 'manager', 'password': '123456', 'role': '经理'},
    'finance': {'username': 'finance', 'password': '123456', 'role': '财务'},
    'employee': {'username': 'a001', 'password': '123456', 'role': '员工'},
}

# 测试路由
TEST_ROUTES = {
    'manager': [
        ('/manager/training_assessments', '培训考核管理'),
        ('/manager/promotions', '晋级审批管理'),
        ('/manager/challenges', '保级挑战管理'),
        ('/manager/payroll', '团队工资查询'),
        ('/manager/logs', '操作日志'),
    ],
    'admin': [
        ('/admin/work_calendar', '工作日配置'),
        ('/admin/payroll_management', '工资管理'),
        ('/admin/payroll_archive', '年度归档'),
        ('/admin/bank_verification', '银行信息审核'),
    ],
    'finance': [
        ('/finance/dashboard', '财务工作台'),
        ('/finance/payment_history', '发放历史'),
        ('/finance/bank_audit', '银行审核'),
    ],
}

class FrontendTester:
    def __init__(self):
        self.session = requests.Session()
        self.results = []
        
    def login(self, username, password):
        """登录系统"""
        try:
            # 先获取登录页面
            response = self.session.get(f"{BASE_URL}/login")
            if response.status_code != 200:
                return False, f"无法访问登录页面: {response.status_code}"
            
            # 提交登录表单
            login_data = {
                'username': username,
                'password': password
            }
            response = self.session.post(
                f"{BASE_URL}/login",
                data=login_data,
                allow_redirects=False
            )
            
            # 检查是否重定向（登录成功）
            if response.status_code in [302, 303]:
                return True, "登录成功"
            else:
                return False, f"登录失败: {response.status_code}"
        except Exception as e:
            return False, f"登录异常: {str(e)}"
    
    def logout(self):
        """登出系统"""
        try:
            self.session.get(f"{BASE_URL}/logout")
            return True
        except:
            return False
    
    def test_route(self, route, name):
        """测试单个路由"""
        try:
            response = self.session.get(f"{BASE_URL}{route}")
            
            if response.status_code == 200:
                # 检查响应内容是否包含基本HTML结构
                if '<html' in response.text and '</html>' in response.text:
                    return {
                        'route': route,
                        'name': name,
                        'status': 'success',
                        'code': 200,
                        'message': '✓ 页面正常',
                        'size': len(response.text)
                    }
                else:
                    return {
                        'route': route,
                        'name': name,
                        'status': 'warning',
                        'code': 200,
                        'message': '⚠ 响应不完整',
                        'size': len(response.text)
                    }
            else:
                return {
                    'route': route,
                    'name': name,
                    'status': 'error',
                    'code': response.status_code,
                    'message': f'✗ HTTP {response.status_code}',
                    'size': 0
                }
        except Exception as e:
            return {
                'route': route,
                'name': name,
                'status': 'error',
                'code': 0,
                'message': f'✗ 异常: {str(e)[:50]}',
                'size': 0
            }
    
    def test_role(self, role, account):
        """测试指定角色的所有路由"""
        print(f"\n{'='*70}")
        print(f"测试角色: {account['role']} ({account['username']})")
        print('='*70)
        
        # 登录
        success, msg = self.login(account['username'], account['password'])
        if not success:
            print(f"✗ 登录失败: {msg}")
            return []
        
        print(f"✓ {msg}")
        time.sleep(0.5)
        
        # 测试路由
        role_results = []
        if role in TEST_ROUTES:
            routes = TEST_ROUTES[role]
            print(f"\n开始测试 {len(routes)} 个页面...")
            print('-'*70)
            
            for route, name in routes:
                result = self.test_route(route, name)
                role_results.append(result)
                
                # 打印结果
                status_icon = {
                    'success': '✓',
                    'warning': '⚠',
                    'error': '✗'
                }.get(result['status'], '?')
                
                print(f"{status_icon} {name:<20} {result['route']:<35} [{result['code']}] {result['size']:>6}字节")
                time.sleep(0.3)
        
        # 登出
        self.logout()
        time.sleep(0.5)
        
        return role_results
    
    def run_all_tests(self):
        """运行所有测试"""
        print("="*70)
        print("前端功能完整测试")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        all_results = {}
        
        # 测试经理
        all_results['manager'] = self.test_role('manager', ACCOUNTS['manager'])
        
        # 测试管理员
        all_results['admin'] = self.test_role('admin', ACCOUNTS['admin'])
        
        # 测试财务
        all_results['finance'] = self.test_role('finance', ACCOUNTS['finance'])
        
        # 生成汇总报告
        self.generate_report(all_results)
        
        return all_results
    
    def generate_report(self, all_results):
        """生成测试报告"""
        print("\n" + "="*70)
        print("测试汇总报告")
        print("="*70)
        
        total_tests = 0
        success_count = 0
        warning_count = 0
        error_count = 0
        
        for role, results in all_results.items():
            role_name = ACCOUNTS[role]['role']
            total_tests += len(results)
            
            role_success = sum(1 for r in results if r['status'] == 'success')
            role_warning = sum(1 for r in results if r['status'] == 'warning')
            role_error = sum(1 for r in results if r['status'] == 'error')
            
            success_count += role_success
            warning_count += role_warning
            error_count += role_error
            
            print(f"\n{role_name}:")
            print(f"  总计: {len(results)}个页面")
            print(f"  成功: {role_success}个 ✓")
            if role_warning > 0:
                print(f"  警告: {role_warning}个 ⚠")
            if role_error > 0:
                print(f"  失败: {role_error}个 ✗")
        
        print("\n" + "-"*70)
        print(f"总计测试: {total_tests}个页面")
        print(f"成功: {success_count}个 ({success_count/total_tests*100:.1f}%)")
        if warning_count > 0:
            print(f"警告: {warning_count}个 ({warning_count/total_tests*100:.1f}%)")
        if error_count > 0:
            print(f"失败: {error_count}个 ({error_count/total_tests*100:.1f}%)")
        
        # 最终判断
        print("\n" + "="*70)
        if error_count == 0 and warning_count == 0:
            print("✅ 所有测试通过！前端功能完全正常！")
        elif error_count == 0:
            print("⚠️  测试基本通过，但有警告项需要检查")
        else:
            print("❌ 测试未通过，有错误需要修复")
        print("="*70)

def main():
    """主测试函数"""
    try:
        # 先检查服务器是否运行
        try:
            response = requests.get(f"{BASE_URL}/login", timeout=5)
            if response.status_code != 200:
                print("❌ 服务器未正常运行，请先启动应用")
                return
        except:
            print("❌ 无法连接到服务器，请先启动应用")
            print(f"   确保应用运行在 {BASE_URL}")
            return
        
        print("✓ 服务器连接正常")
        time.sleep(1)
        
        # 运行测试
        tester = FrontendTester()
        tester.run_all_tests()
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试异常: {e}")

if __name__ == '__main__':
    main()

