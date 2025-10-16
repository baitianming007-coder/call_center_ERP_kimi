#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1专家团拟人化测试脚本
模拟真实用户操作，全面测试前后端功能
"""

import requests
from requests import Session
import time
import json
from datetime import datetime

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

def print_test(text):
    print(f"\n{Colors.YELLOW}▶ {text}{Colors.END}")

def print_pass(text):
    print(f"  {Colors.GREEN}✓ {text}{Colors.END}")

def print_fail(text):
    print(f"  {Colors.RED}✗ {text}{Colors.END}")

def print_info(text):
    print(f"  ℹ {text}")

class P1ExpertTester:
    def __init__(self):
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.bugs_found = []
        
    def record_result(self, test_name, passed, details=""):
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            print_pass(f"{test_name} - 通过")
        else:
            self.failed_tests += 1
            print_fail(f"{test_name} - 失败: {details}")
            self.bugs_found.append({
                'test': test_name,
                'details': details,
                'timestamp': datetime.now().isoformat()
            })
        self.results.append((test_name, passed, details))
    
    # ==================== 前端测试 ====================
    
    def test_navigation_highlight(self):
        """测试P1-1: 导航栏当前页高亮"""
        print_test("P1-1: 导航栏当前页高亮")
        
        session = Session()
        session.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': '123456'})
        
        # 测试多个页面
        pages = [
            ('/admin/employees', '员工管理'),
            ('/admin/performance', '业绩管理'),
            ('/admin/salary', '薪资统计'),
        ]
        
        for url, page_name in pages:
            response = session.get(f"{BASE_URL}{url}")
            has_highlight_js = 'highlightCurrentNav' in response.text
            has_active_class = 'navbar-link active' in response.text or '.active' in response.text
            
            if has_highlight_js:
                self.record_result(f"导航高亮JS - {page_name}", True)
            else:
                self.record_result(f"导航高亮JS - {page_name}", False, "缺少高亮JavaScript")
    
    def test_breadcrumb_navigation(self):
        """测试P1-3: 面包屑导航"""
        print_test("P1-3: 面包屑导航")
        
        session = Session()
        session.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': '123456'})
        
        response = session.get(f"{BASE_URL}/admin/employees")
        
        has_breadcrumb_html = 'breadcrumb' in response.text
        has_breadcrumb_content = '员工管理' in response.text
        
        if has_breadcrumb_html and has_breadcrumb_content:
            self.record_result("面包屑导航显示", True)
        else:
            self.record_result("面包屑导航显示", False, "面包屑未正确显示")
    
    def test_pending_badge(self):
        """测试P1-4: 待审批红点提示"""
        print_test("P1-4: 待审批红点提示")
        
        # 测试经理角色
        session = Session()
        session.post(f"{BASE_URL}/login", data={'username': 'manager', 'password': '123456'})
        
        # 测试API
        try:
            api_response = session.get(f"{BASE_URL}/manager/api/pending_count")
            if api_response.status_code == 200:
                data = api_response.json()
                if 'promotions' in data and 'challenges' in data:
                    self.record_result("红点API响应", True)
                    print_info(f"待审批晋级: {data['promotions']}个, 挑战: {data['challenges']}个")
                else:
                    self.record_result("红点API响应", False, "API响应缺少必要字段")
            else:
                self.record_result("红点API响应", False, f"API返回{api_response.status_code}")
        except Exception as e:
            self.record_result("红点API响应", False, str(e))
        
        # 测试前端显示
        page_response = session.get(f"{BASE_URL}/manager/promotions")
        has_badge_html = 'promotion-badge' in page_response.text or 'nav-badge' in page_response.text
        has_update_function = 'updatePendingCount' in page_response.text
        
        if has_update_function:
            self.record_result("红点更新函数", True)
        else:
            self.record_result("红点更新函数", False, "缺少更新函数")
    
    def test_pagination(self):
        """测试P1-5: 员工列表分页功能"""
        print_test("P1-5: 员工列表分页功能")
        
        session = Session()
        session.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': '123456'})
        
        # 测试第1页
        response1 = session.get(f"{BASE_URL}/admin/employees?page=1")
        has_pagination = 'pagination-btn' in response1.text
        
        if has_pagination:
            self.record_result("分页控件显示", True)
        else:
            self.record_result("分页控件显示", False, "未找到分页控件")
        
        # 测试翻页
        response2 = session.get(f"{BASE_URL}/admin/employees?page=2")
        if response2.status_code == 200:
            self.record_result("分页翻页功能", True)
        else:
            self.record_result("分页翻页功能", False, "翻页失败")
        
        # 测试边界（第0页应该自动跳转到第1页）
        response3 = session.get(f"{BASE_URL}/admin/employees?page=0")
        if response3.status_code == 200:
            self.record_result("分页边界保护", True)
        else:
            self.record_result("分页边界保护", False, "边界保护失败")
    
    def test_advanced_filters(self):
        """测试P1-6: 高级筛选功能"""
        print_test("P1-6: 高级筛选功能")
        
        session = Session()
        session.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': '123456'})
        
        response = session.get(f"{BASE_URL}/admin/employees")
        
        # 检查筛选字段
        filters = {
            'advancedFilters': '高级筛选区域',
            'join_date_from': '入职日期筛选',
            'orders_from': '出单数量筛选',
            'work_days_from': '在职天数筛选',
            'toggleAdvancedFilters': '切换函数'
        }
        
        for field, desc in filters.items():
            if field in response.text:
                self.record_result(f"高级筛选 - {desc}", True)
            else:
                self.record_result(f"高级筛选 - {desc}", False, f"缺少{field}")
        
        # 测试筛选功能
        filter_response = session.get(f"{BASE_URL}/admin/employees?join_date_from=2024-01-01&orders_from=5")
        if filter_response.status_code == 200:
            self.record_result("高级筛选 - 组合查询", True)
        else:
            self.record_result("高级筛选 - 组合查询", False, "查询失败")
    
    def test_batch_operations(self):
        """测试P1-7: 批量操作功能"""
        print_test("P1-7: 批量操作功能")
        
        session = Session()
        session.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': '123456'})
        
        response = session.get(f"{BASE_URL}/admin/employees")
        
        # 检查批量操作组件
        components = {
            'emp-checkbox': '员工复选框',
            'selectAll': '全选框',
            'batchActionsBar': '批量操作栏',
            'toggleSelectAll': '全选函数',
            'batchExport': '批量导出函数',
            'batchChangeTeam': '批量修改团队函数'
        }
        
        for component, desc in components.items():
            if component in response.text:
                self.record_result(f"批量操作 - {desc}", True)
            else:
                self.record_result(f"批量操作 - {desc}", False, f"缺少{component}")
    
    def test_challenge_progress(self):
        """测试P1-8: 挑战进度可视化"""
        print_test("P1-8: 挑战进度可视化")
        
        session = Session()
        session.post(f"{BASE_URL}/login", data={'username': 'manager', 'password': '123456'})
        
        # 检查CSS样式
        css_response = session.get(f"{BASE_URL}/static/css/main.css")
        
        css_components = {
            '.challenge-progress': '进度条容器',
            '.progress-bar-fill': '进度条填充',
            '@keyframes shimmer': '闪光动画'
        }
        
        for css_class, desc in css_components.items():
            if css_class in css_response.text:
                self.record_result(f"进度可视化CSS - {desc}", True)
            else:
                self.record_result(f"进度可视化CSS - {desc}", False, f"缺少{css_class}")
        
        # 检查模板
        page_response = session.get(f"{BASE_URL}/manager/challenges")
        if '挑战进度' in page_response.text or 'challenge_orders' in page_response.text:
            self.record_result("进度可视化模板", True)
        else:
            self.record_result("进度可视化模板", False, "模板未配置")
    
    def test_performance_chart(self):
        """测试P1-9: 业绩趋势图"""
        print_test("P1-9: 业绩趋势图 (Chart.js)")
        
        session = Session()
        session.post(f"{BASE_URL}/login", data={'username': 'a001', 'password': '123456'})
        
        response = session.get(f"{BASE_URL}/employee/performance")
        
        # 检查Chart.js配置
        chart_features = {
            "type: 'line'": '折线图类型',
            'tension': '平滑曲线',
            'Chart': 'Chart.js库',
            'performanceChart': '图表Canvas'
        }
        
        for feature, desc in chart_features.items():
            if feature in response.text:
                self.record_result(f"业绩趋势图 - {desc}", True)
            else:
                self.record_result(f"业绩趋势图 - {desc}", False, f"缺少{feature}")
    
    def test_payroll_preview(self):
        """测试P1-10: 工资单预览功能"""
        print_test("P1-10: 工资单预览功能")
        
        session = Session()
        session.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': '123456'})
        
        # 检查页面组件
        page_response = session.get(f"{BASE_URL}/admin/payroll_management")
        
        components = {
            'previewPayroll': '预览函数',
            'previewModal': '预览模态框',
            'renderPreview': '渲染函数'
        }
        
        for component, desc in components.items():
            if component in page_response.text:
                self.record_result(f"工资预览 - {desc}", True)
            else:
                self.record_result(f"工资预览 - {desc}", False, f"缺少{component}")
        
        # 测试API
        try:
            year_month = datetime.now().strftime('%Y-%m')
            api_response = session.get(f"{BASE_URL}/admin/api/payroll_preview?year_month={year_month}")
            if api_response.status_code == 200:
                data = api_response.json()
                if 'preview' in data and 'total_count' in data:
                    self.record_result("工资预览API", True)
                    print_info(f"预览数据: {data['total_count']}人")
                else:
                    self.record_result("工资预览API", False, "API响应格式错误")
            else:
                self.record_result("工资预览API", False, f"API返回{api_response.status_code}")
        except Exception as e:
            self.record_result("工资预览API", False, str(e))
    
    # ==================== 集成测试 ====================
    
    def test_admin_workflow(self):
        """测试管理员完整工作流"""
        print_test("集成测试: 管理员工作流")
        
        session = Session()
        login = session.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': '123456'})
        
        if login.status_code == 200:
            self.record_result("管理员登录", True)
        else:
            self.record_result("管理员登录", False, "登录失败")
            return
        
        # 访问关键页面
        pages = [
            ('/admin/dashboard', '主看板'),
            ('/admin/employees', '员工管理'),
            ('/admin/performance', '业绩管理'),
            ('/admin/salary', '薪资统计'),
            ('/admin/payroll_management', '工资管理')
        ]
        
        for url, name in pages:
            response = session.get(f"{BASE_URL}{url}")
            if response.status_code == 200:
                self.record_result(f"管理员访问 - {name}", True)
            else:
                self.record_result(f"管理员访问 - {name}", False, f"返回{response.status_code}")
    
    def test_manager_workflow(self):
        """测试经理完整工作流"""
        print_test("集成测试: 经理工作流")
        
        session = Session()
        session.post(f"{BASE_URL}/login", data={'username': 'manager', 'password': '123456'})
        
        pages = [
            ('/admin/dashboard', '主看板'),
            ('/manager/promotions', '晋级审批'),
            ('/manager/challenges', '保级挑战'),
            ('/manager/training_assessments', '培训考核')
        ]
        
        for url, name in pages:
            response = session.get(f"{BASE_URL}{url}")
            if response.status_code == 200:
                self.record_result(f"经理访问 - {name}", True)
            else:
                self.record_result(f"经理访问 - {name}", False, f"返回{response.status_code}")
    
    def test_finance_workflow(self):
        """测试财务完整工作流"""
        print_test("集成测试: 财务工作流")
        
        session = Session()
        session.post(f"{BASE_URL}/login", data={'username': 'finance', 'password': '123456'})
        
        response = session.get(f"{BASE_URL}/finance/dashboard")
        if response.status_code == 200:
            self.record_result("财务访问 - 主页", True)
        else:
            self.record_result("财务访问 - 主页", False, f"返回{response.status_code}")
    
    def test_employee_workflow(self):
        """测试员工完整工作流"""
        print_test("集成测试: 员工工作流")
        
        session = Session()
        session.post(f"{BASE_URL}/login", data={'username': 'a001', 'password': '123456'})
        
        pages = [
            ('/employee/performance', '个人业绩'),
            ('/employee/salary', '个人薪资')
        ]
        
        for url, name in pages:
            response = session.get(f"{BASE_URL}{url}")
            if response.status_code == 200:
                self.record_result(f"员工访问 - {name}", True)
            else:
                self.record_result(f"员工访问 - {name}", False, f"返回{response.status_code}")
    
    # ==================== 主测试流程 ====================
    
    def run_all_tests(self):
        """执行所有测试"""
        print_header("P1专家团拟人化测试 - 开始")
        print_info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info(f"测试服务器: {BASE_URL}")
        
        try:
            # 前端功能测试
            print_header("第一部分: 前端功能测试")
            self.test_navigation_highlight()
            self.test_breadcrumb_navigation()
            self.test_pending_badge()
            self.test_pagination()
            self.test_advanced_filters()
            self.test_batch_operations()
            self.test_challenge_progress()
            self.test_performance_chart()
            self.test_payroll_preview()
            
            # 集成测试
            print_header("第二部分: 集成测试 (4个角色)")
            self.test_admin_workflow()
            self.test_manager_workflow()
            self.test_finance_workflow()
            self.test_employee_workflow()
            
            # 生成报告
            self.generate_report()
            
        except Exception as e:
            print_fail(f"测试过程异常: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def generate_report(self):
        """生成测试报告"""
        print_header("测试报告")
        
        print(f"\n总计测试: {self.total_tests}项")
        print(f"{Colors.GREEN}通过: {self.passed_tests}项{Colors.END}")
        print(f"{Colors.RED}失败: {self.failed_tests}项{Colors.END}")
        print(f"成功率: {self.passed_tests/self.total_tests*100:.1f}%")
        
        if self.bugs_found:
            print(f"\n{Colors.RED}发现的问题 ({len(self.bugs_found)}个):{Colors.END}")
            for i, bug in enumerate(self.bugs_found, 1):
                print(f"  {i}. [{bug['test']}] {bug['details']}")
        
        # 评级
        success_rate = self.passed_tests / self.total_tests
        if success_rate == 1.0:
            rating = f"{Colors.GREEN}⭐⭐⭐⭐⭐ 优秀{Colors.END}"
            status = f"{Colors.GREEN}✓ 可以商业化交付{Colors.END}"
        elif success_rate >= 0.9:
            rating = f"{Colors.GREEN}⭐⭐⭐⭐ 良好{Colors.END}"
            status = f"{Colors.YELLOW}⚠ 修复问题后可交付{Colors.END}"
        elif success_rate >= 0.7:
            rating = f"{Colors.YELLOW}⭐⭐⭐ 一般{Colors.END}"
            status = f"{Colors.YELLOW}⚠ 需要修复多个问题{Colors.END}"
        else:
            rating = f"{Colors.RED}⭐⭐ 较差{Colors.END}"
            status = f"{Colors.RED}✗ 不建议交付{Colors.END}"
        
        print(f"\n质量评级: {rating}")
        print(f"交付状态: {status}")
        
        print(f"\n{'='*80}")
        print(f"{Colors.BLUE}测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        print(f"{'='*80}\n")
        
        return {
            'total': self.total_tests,
            'passed': self.passed_tests,
            'failed': self.failed_tests,
            'success_rate': success_rate,
            'bugs': self.bugs_found
        }

if __name__ == '__main__':
    print("\n等待服务器启动...")
    time.sleep(2)
    
    tester = P1ExpertTester()
    tester.run_all_tests()

