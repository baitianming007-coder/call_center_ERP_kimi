#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1性能测试脚本
测试页面加载时间、API响应时间和并发性能
"""

import requests
from requests import Session
import time
from datetime import datetime
import statistics
import concurrent.futures

BASE_URL = "http://127.0.0.1:8080"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{'='*80}")
    print(f"{Colors.BLUE}{text}{Colors.END}")
    print(f"{'='*80}")

def print_metric(name, value, unit, target, passed):
    status = f"{Colors.GREEN}✅ PASS{Colors.END}" if passed else f"{Colors.RED}❌ FAIL{Colors.END}"
    print(f"{name:30} {value:8.2f} {unit:8} (目标: <{target}{unit}) {status}")

class P1PerformanceTest:
    def __init__(self):
        self.results = {}
        
    def measure_page_load(self, session, url, page_name):
        """测量页面加载时间"""
        start = time.time()
        response = session.get(f"{BASE_URL}{url}")
        end = time.time()
        
        load_time = end - start
        page_size = len(response.content) / 1024  # KB
        
        return {
            'load_time': load_time,
            'page_size': page_size,
            'status_code': response.status_code
        }
    
    def measure_api_response(self, session, url, params=None):
        """测量API响应时间"""
        start = time.time()
        response = session.get(f"{BASE_URL}{url}", params=params)
        end = time.time()
        
        response_time = (end - start) * 1000  # ms
        
        return {
            'response_time': response_time,
            'status_code': response.status_code
        }
    
    def test_page_load_times(self):
        """测试页面加载时间"""
        print_header("页面加载时间测试")
        
        # 管理员登录
        admin_session = Session()
        admin_session.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': '123456'})
        
        pages = [
            ('/admin/employees', '员工管理', 2.0),
            ('/admin/performance', '业绩管理', 2.0),
            ('/admin/salary', '薪资统计', 2.0),
            ('/admin/payroll_management', '工资管理', 2.0),
        ]
        
        print("\n页面加载性能（目标 <2秒）:")
        print("-" * 80)
        
        results = []
        for url, name, target in pages:
            result = self.measure_page_load(admin_session, url, name)
            passed = result['load_time'] < target
            print_metric(f"{name} ({result['page_size']:.1f}KB)", 
                        result['load_time'], "s", target, passed)
            results.append({
                'page': name,
                'time': result['load_time'],
                'size': result['page_size'],
                'passed': passed
            })
        
        avg_time = statistics.mean([r['time'] for r in results])
        print(f"\n{Colors.BLUE}平均加载时间: {avg_time:.2f}s{Colors.END}")
        
        self.results['page_load'] = results
        return results
    
    def test_api_response_times(self):
        """测试API响应时间"""
        print_header("API响应时间测试")
        
        # 经理登录
        manager_session = Session()
        manager_session.post(f"{BASE_URL}/login", data={'username': 'manager', 'password': '123456'})
        
        # 管理员登录
        admin_session = Session()
        admin_session.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': '123456'})
        
        apis = [
            (manager_session, '/manager/api/pending_count', None, '待审批数量API', 200),
            (admin_session, '/admin/api/payroll_preview', {'year_month': '2025-10'}, '工资预览API', 200),
        ]
        
        print("\nAPI响应性能（目标 <200ms）:")
        print("-" * 80)
        
        results = []
        for session, url, params, name, target in apis:
            # 测试5次取平均值
            times = []
            for _ in range(5):
                result = self.measure_api_response(session, url, params)
                times.append(result['response_time'])
            
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            passed = avg_time < target
            
            print_metric(name, avg_time, "ms", target, passed)
            print(f"  └─ 最快: {min_time:.2f}ms, 最慢: {max_time:.2f}ms, 标准差: {statistics.stdev(times):.2f}ms")
            
            results.append({
                'api': name,
                'avg': avg_time,
                'min': min_time,
                'max': max_time,
                'passed': passed
            })
        
        self.results['api_response'] = results
        return results
    
    def test_concurrent_users(self, num_users=10):
        """测试并发用户访问"""
        print_header(f"并发访问测试 ({num_users}个用户)")
        
        def user_session():
            """模拟单个用户会话"""
            try:
                session = Session()
                start = time.time()
                
                # 登录
                session.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': '123456'})
                
                # 访问几个页面
                session.get(f"{BASE_URL}/admin/employees")
                session.get(f"{BASE_URL}/admin/performance")
                
                end = time.time()
                return end - start
            except Exception as e:
                return None
        
        print(f"\n模拟{num_users}个用户同时访问系统...")
        
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(user_session) for _ in range(num_users)]
            session_times = [f.result() for f in concurrent.futures.as_completed(futures)]
        end = time.time()
        
        # 过滤失败的会话
        valid_times = [t for t in session_times if t is not None]
        failed_count = len(session_times) - len(valid_times)
        
        if valid_times:
            avg_time = statistics.mean(valid_times)
            max_time = max(valid_times)
            total_time = end - start
            
            print(f"\n并发测试结果:")
            print(f"  总用户数: {num_users}")
            print(f"  成功会话: {len(valid_times)}")
            print(f"  失败会话: {failed_count}")
            print(f"  总耗时: {total_time:.2f}s")
            print(f"  平均会话时间: {avg_time:.2f}s")
            print(f"  最慢会话时间: {max_time:.2f}s")
            print(f"  吞吐量: {num_users/total_time:.2f} 请求/秒")
            
            passed = failed_count == 0 and avg_time < 5.0
            status = f"{Colors.GREEN}✅ PASS{Colors.END}" if passed else f"{Colors.RED}❌ FAIL{Colors.END}"
            print(f"\n并发测试状态: {status}")
            
            self.results['concurrent'] = {
                'total_users': num_users,
                'successful': len(valid_times),
                'failed': failed_count,
                'total_time': total_time,
                'avg_session_time': avg_time,
                'passed': passed
            }
        else:
            print(f"\n{Colors.RED}所有会话失败！{Colors.END}")
            self.results['concurrent'] = {'passed': False}
    
    def test_pagination_performance(self):
        """测试分页性能提升"""
        print_header("分页性能对比测试")
        
        session = Session()
        session.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': '123456'})
        
        print("\n测试分页加载性能...")
        
        # 测试第1页（分页）
        result_page1 = self.measure_page_load(session, '/admin/employees?page=1', '第1页')
        
        # 测试第2页（分页）
        result_page2 = self.measure_page_load(session, '/admin/employees?page=2', '第2页')
        
        print(f"\n分页性能:")
        print(f"  第1页: {result_page1['load_time']:.2f}s ({result_page1['page_size']:.1f}KB)")
        print(f"  第2页: {result_page2['load_time']:.2f}s ({result_page2['page_size']:.1f}KB)")
        
        # 估算性能提升（假设之前是171KB）
        old_size = 171
        new_size = result_page1['page_size']
        size_reduction = ((old_size - new_size) / old_size) * 100
        
        print(f"\n{Colors.GREEN}页面大小优化: {old_size}KB → {new_size:.1f}KB (-{size_reduction:.1f}%){Colors.END}")
        
        self.results['pagination'] = {
            'old_size': old_size,
            'new_size': new_size,
            'reduction': size_reduction,
            'passed': new_size < 50
        }
    
    def generate_report(self):
        """生成性能测试报告"""
        print_header("性能测试总结报告")
        
        # 统计通过率
        all_tests = []
        if 'page_load' in self.results:
            all_tests.extend([r['passed'] for r in self.results['page_load']])
        if 'api_response' in self.results:
            all_tests.extend([r['passed'] for r in self.results['api_response']])
        if 'concurrent' in self.results:
            all_tests.append(self.results['concurrent']['passed'])
        if 'pagination' in self.results:
            all_tests.append(self.results['pagination']['passed'])
        
        total_tests = len(all_tests)
        passed_tests = sum(all_tests)
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n测试统计:")
        print(f"  总计测试: {total_tests}")
        print(f"  通过: {passed_tests}")
        print(f"  失败: {total_tests - passed_tests}")
        print(f"  通过率: {pass_rate:.1f}%")
        
        # 评级
        if pass_rate == 100:
            rating = f"{Colors.GREEN}⭐⭐⭐⭐⭐ 优秀{Colors.END}"
        elif pass_rate >= 80:
            rating = f"{Colors.GREEN}⭐⭐⭐⭐ 良好{Colors.END}"
        elif pass_rate >= 60:
            rating = f"{Colors.YELLOW}⭐⭐⭐ 一般{Colors.END}"
        else:
            rating = f"{Colors.RED}⭐⭐ 较差{Colors.END}"
        
        print(f"\n性能评级: {rating}")
        
        # 关键指标总结
        print(f"\n{Colors.BLUE}关键性能指标:{Colors.END}")
        if 'page_load' in self.results:
            avg_load = statistics.mean([r['time'] for r in self.results['page_load']])
            print(f"  ✓ 平均页面加载: {avg_load:.2f}s (目标 <2s)")
        
        if 'api_response' in self.results:
            avg_api = statistics.mean([r['avg'] for r in self.results['api_response']])
            print(f"  ✓ 平均API响应: {avg_api:.2f}ms (目标 <200ms)")
        
        if 'concurrent' in self.results and self.results['concurrent']['passed']:
            print(f"  ✓ 并发测试: 通过 ({self.results['concurrent']['successful']}个用户)")
        
        if 'pagination' in self.results:
            reduction = self.results['pagination']['reduction']
            print(f"  ✓ 页面大小优化: -{reduction:.1f}%")
        
        print(f"\n{'='*80}")
        print(f"{Colors.BLUE}性能测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        print(f"{'='*80}\n")

if __name__ == '__main__':
    print("\n等待服务器启动...")
    time.sleep(2)
    
    tester = P1PerformanceTest()
    
    try:
        # 执行所有测试
        tester.test_page_load_times()
        tester.test_api_response_times()
        tester.test_pagination_performance()
        tester.test_concurrent_users(10)
        
        # 生成报告
        tester.generate_report()
        
    except Exception as e:
        print(f"{Colors.RED}测试过程异常: {str(e)}{Colors.END}")
        import traceback
        traceback.print_exc()

