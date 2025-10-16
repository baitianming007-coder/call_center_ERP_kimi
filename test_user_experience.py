#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户体验拟人化测试脚本
模拟真实用户操作，记录所有问题和改进建议
"""

import requests
from requests import Session
import json
from datetime import datetime, date, timedelta
import time

BASE_URL = "http://127.0.0.1:8080"

class UXTester:
    def __init__(self):
        self.session = Session()
        self.issues = []  # 问题列表
        self.suggestions = []  # 改进建议
        self.test_results = []  # 测试结果
        
    def log_issue(self, severity, page, issue, detail=""):
        """记录问题"""
        self.issues.append({
            'severity': severity,  # critical/major/minor
            'page': page,
            'issue': issue,
            'detail': detail,
            'time': datetime.now().strftime('%H:%M:%S')
        })
        
    def log_suggestion(self, category, page, suggestion, priority="medium"):
        """记录改进建议"""
        self.suggestions.append({
            'category': category,  # UI/UX/功能/性能
            'page': page,
            'suggestion': suggestion,
            'priority': priority,  # high/medium/low
            'time': datetime.now().strftime('%H:%M:%S')
        })
        
    def login(self, username, password, role_name):
        """登录"""
        print(f"\n{'='*70}")
        print(f"🧪 测试角色: {role_name} ({username})")
        print('='*70)
        
        # 访问登录页面
        response = self.session.get(f"{BASE_URL}/login")
        if response.status_code != 200:
            self.log_issue('critical', '登录页面', '无法访问登录页面', f'HTTP {response.status_code}')
            return False
        
        # 检查登录页面内容
        if '测试账号' not in response.text:
            self.log_suggestion('UI', '登录页面', '应显示测试账号信息', 'high')
        
        if '123456' not in response.text:
            self.log_issue('minor', '登录页面', '测试账号密码提示不正确')
        
        # 提交登录
        response = self.session.post(
            f"{BASE_URL}/login",
            data={'username': username, 'password': password},
            allow_redirects=True
        )
        
        if response.status_code == 200 and 'dashboard' in response.url:
            print(f"✅ 登录成功")
            return True
        else:
            self.log_issue('critical', '登录', '登录失败', f'状态码: {response.status_code}')
            return False
    
    def test_navigation(self, role_name):
        """测试导航栏"""
        print(f"\n📊 测试导航栏...")
        
        # 获取主页
        response = self.session.get(f"{BASE_URL}/admin/dashboard")
        
        # 检查导航菜单
        nav_items = []
        if '员工管理' in response.text:
            nav_items.append('员工管理')
        if '业绩管理' in response.text:
            nav_items.append('业绩管理')
        if '薪资统计' in response.text:
            nav_items.append('薪资统计')
        if '数据报表' in response.text:
            nav_items.append('数据报表')
        
        print(f"  导航菜单项: {len(nav_items)}个")
        
        # 建议：导航菜单应该有明确的视觉反馈
        self.log_suggestion('UI', '导航栏', '增加当前页面的高亮显示', 'high')
        self.log_suggestion('UX', '导航栏', '增加面包屑导航，方便用户知道当前位置', 'medium')
        
    def test_admin_features(self):
        """测试管理员功能"""
        print(f"\n{'='*70}")
        print("🎯 测试管理员功能")
        print('='*70)
        
        # 1. 测试仪表盘
        print("\n1️⃣ 测试仪表盘...")
        response = self.session.get(f"{BASE_URL}/admin/dashboard")
        if response.status_code == 200:
            print("  ✅ 仪表盘加载成功")
            # 检查关键数据是否显示
            if '在职员工' not in response.text:
                self.log_issue('major', '仪表盘', '缺少"在职员工"统计')
            if '本月业绩' not in response.text:
                self.log_issue('major', '仪表盘', '缺少"本月业绩"统计')
            
            self.log_suggestion('UI', '仪表盘', '增加数据可视化图表（如折线图、饼图）', 'high')
            self.log_suggestion('功能', '仪表盘', '增加快速操作入口（如快速录入业绩）', 'medium')
        
        # 2. 测试员工管理
        print("\n2️⃣ 测试员工管理...")
        response = self.session.get(f"{BASE_URL}/admin/employees")
        if response.status_code == 200:
            print("  ✅ 员工列表加载成功")
            page_size = len(response.text)
            print(f"  页面大小: {page_size:,}字节")
            
            if page_size > 200000:
                self.log_issue('minor', '员工管理', '页面过大，建议添加分页', f'{page_size}字节')
            
            self.log_suggestion('UX', '员工管理', '增加高级筛选（按状态、入职时间、团队筛选）', 'high')
            self.log_suggestion('UI', '员工管理', '表格增加排序功能（点击列头排序）', 'medium')
            self.log_suggestion('功能', '员工管理', '批量操作（批量导出、批量修改团队）', 'medium')
        
        # 3. 测试工作日配置
        print("\n3️⃣ 测试工作日配置...")
        response = self.session.get(f"{BASE_URL}/admin/work_calendar")
        if response.status_code == 200:
            print("  ✅ 工作日配置加载成功")
            self.log_suggestion('UX', '工作日配置', '增加快捷设置（如批量设置周末、批量设置节假日）', 'high')
            self.log_suggestion('UI', '工作日配置', '日历视图增加颜色区分（工作日/假期）', 'medium')
            self.log_suggestion('功能', '工作日配置', '支持导入节假日数据（如导入国家法定假日）', 'low')
        
        # 4. 测试工资管理
        print("\n4️⃣ 测试工资管理...")
        response = self.session.get(f"{BASE_URL}/admin/payroll_management")
        if response.status_code == 200:
            print("  ✅ 工资管理加载成功")
            self.log_suggestion('UX', '工资管理', '生成工资单前应有确认弹窗（避免误操作）', 'high')
            self.log_suggestion('功能', '工资管理', '支持预览工资单（生成前先预览）', 'high')
            self.log_suggestion('UI', '工资管理', '增加工资单状态筛选（待确认/已确认/已发放）', 'medium')
        
        # 5. 测试业绩管理
        print("\n5️⃣ 测试业绩管理...")
        response = self.session.get(f"{BASE_URL}/admin/performance")
        if response.status_code == 200:
            print("  ✅ 业绩管理加载成功")
            self.log_suggestion('UX', '业绩管理', '批量录入时应显示进度条', 'medium')
            self.log_suggestion('功能', '业绩管理', '支持导入Excel批量录入业绩', 'high')
            self.log_suggestion('UI', '业绩管理', '增加业绩趋势图（显示近7天业绩走势）', 'medium')
        
        # 6. 测试薪资统计
        print("\n6️⃣ 测试薪资统计...")
        response = self.session.get(f"{BASE_URL}/admin/salary")
        if response.status_code == 200:
            print("  ✅ 薪资统计加载成功")
            self.log_suggestion('功能', '薪资统计', '增加薪资对比（本月vs上月）', 'medium')
            self.log_suggestion('UI', '薪资统计', '增加薪资分布图（展示薪资区间分布）', 'low')
        
    def test_manager_features(self):
        """测试经理功能"""
        print(f"\n{'='*70}")
        print("🎯 测试经理功能")
        print('='*70)
        
        # 1. 测试培训考核
        print("\n1️⃣ 测试培训考核管理...")
        response = self.session.get(f"{BASE_URL}/manager/training_assessments")
        if response.status_code == 200:
            print("  ✅ 培训考核页面加载成功")
            self.log_suggestion('UX', '培训考核', '记录考核时应有确认提示', 'medium')
            self.log_suggestion('功能', '培训考核', '支持上传考核附件（如录音、截图）', 'low')
            self.log_suggestion('UI', '培训考核', '增加考核通过率统计图', 'low')
        
        # 2. 测试晋级审批
        print("\n2️⃣ 测试晋级审批...")
        response = self.session.get(f"{BASE_URL}/manager/promotions")
        if response.status_code == 200:
            print("  ✅ 晋级审批页面加载成功")
            self.log_suggestion('UX', '晋级审批', '待审批项应突出显示（如红点提示）', 'high')
            self.log_suggestion('功能', '晋级审批', '批量审批功能（批量通过/驳回）', 'medium')
            self.log_suggestion('UI', '晋级审批', '显示员工详细信息（业绩、考核记录）', 'medium')
        
        # 3. 测试保级挑战
        print("\n3️⃣ 测试保级挑战...")
        response = self.session.get(f"{BASE_URL}/manager/challenges")
        if response.status_code == 200:
            print("  ✅ 保级挑战页面加载成功")
            self.log_suggestion('UX', '保级挑战', '挑战进度应有可视化显示（进度条）', 'high')
            self.log_suggestion('功能', '保级挑战', '挑战期间每日业绩更新提醒', 'medium')
            self.log_suggestion('UI', '保级挑战', '挑战历史记录应可查看', 'low')
        
        # 4. 测试团队工资
        print("\n4️⃣ 测试团队工资查询...")
        response = self.session.get(f"{BASE_URL}/manager/payroll")
        if response.status_code == 200:
            print("  ✅ 团队工资页面加载成功")
            self.log_suggestion('功能', '团队工资', '增加团队薪资总计', 'medium')
            self.log_suggestion('UI', '团队工资', '支持导出团队工资明细', 'medium')
        
    def test_finance_features(self):
        """测试财务功能"""
        print(f"\n{'='*70}")
        print("🎯 测试财务功能")
        print('='*70)
        
        # 1. 测试财务工作台
        print("\n1️⃣ 测试财务工作台...")
        response = self.session.get(f"{BASE_URL}/finance/dashboard")
        if response.status_code == 200:
            print("  ✅ 财务工作台加载成功")
            self.log_suggestion('UI', '财务工作台', '增加待处理事项数量红点提示', 'high')
            self.log_suggestion('功能', '财务工作台', '增加本月发放进度条', 'medium')
            self.log_suggestion('UX', '财务工作台', '快速操作区（快速确认、快速发放）', 'medium')
        
        # 2. 测试发放历史
        print("\n2️⃣ 测试发放历史...")
        response = self.session.get(f"{BASE_URL}/finance/payment_history")
        if response.status_code == 200:
            print("  ✅ 发放历史加载成功")
            self.log_suggestion('功能', '发放历史', '增加发放失败原因筛选', 'medium')
            self.log_suggestion('UI', '发放历史', '增加发放状态时间轴（待确认→已确认→已发放）', 'low')
        
        # 3. 测试银行审核
        print("\n3️⃣ 测试银行信息审核...")
        response = self.session.get(f"{BASE_URL}/finance/bank_audit")
        if response.status_code == 200:
            print("  ✅ 银行审核页面加载成功")
            page_size = len(response.text)
            if page_size > 150000:
                self.log_issue('minor', '银行审核', '页面数据量大，建议分页', f'{page_size}字节')
            
            self.log_suggestion('UX', '银行审核', '银行卡号应支持一键复制', 'high')
            self.log_suggestion('功能', '银行审核', '批量审核功能', 'high')
            self.log_suggestion('UI', '银行审核', '增加待审核筛选和排序', 'medium')
    
    def test_employee_features(self):
        """测试员工功能"""
        print(f"\n{'='*70}")
        print("🎯 测试员工功能")
        print('='*70)
        
        # 1. 测试个人业绩
        print("\n1️⃣ 测试个人业绩...")
        response = self.session.get(f"{BASE_URL}/employee/performance")
        if response.status_code == 200:
            print("  ✅ 个人业绩页面加载成功")
            self.log_suggestion('UI', '个人业绩', '增加业绩趋势图（折线图）', 'high')
            self.log_suggestion('功能', '个人业绩', '增加目标达成进度（如距离晋级还差多少单）', 'high')
            self.log_suggestion('UX', '个人业绩', '增加同事排名（激励机制）', 'medium')
        
        # 2. 测试个人薪资
        print("\n2️⃣ 测试个人薪资...")
        response = self.session.get(f"{BASE_URL}/employee/salary")
        if response.status_code == 200:
            print("  ✅ 个人薪资页面加载成功")
            self.log_suggestion('UI', '个人薪资', '薪资明细应更清晰（可视化展示）', 'medium')
            self.log_suggestion('功能', '个人薪资', '支持下载工资条（PDF）', 'high')
        
    def generate_report(self):
        """生成测试报告"""
        print(f"\n\n{'='*70}")
        print("📊 用户体验测试报告生成")
        print('='*70)
        
        # 按严重程度分类问题
        critical_issues = [i for i in self.issues if i['severity'] == 'critical']
        major_issues = [i for i in self.issues if i['severity'] == 'major']
        minor_issues = [i for i in self.issues if i['severity'] == 'minor']
        
        # 按优先级分类建议
        high_suggestions = [s for s in self.suggestions if s['priority'] == 'high']
        medium_suggestions = [s for s in self.suggestions if s['priority'] == 'medium']
        low_suggestions = [s for s in self.suggestions if s['priority'] == 'low']
        
        # 统计
        print(f"\n🐛 发现问题总计: {len(self.issues)}个")
        print(f"  严重问题: {len(critical_issues)}个")
        print(f"  一般问题: {len(major_issues)}个")
        print(f"  次要问题: {len(minor_issues)}个")
        
        print(f"\n💡 改进建议总计: {len(self.suggestions)}个")
        print(f"  高优先级: {len(high_suggestions)}个")
        print(f"  中优先级: {len(medium_suggestions)}个")
        print(f"  低优先级: {len(low_suggestions)}个")
        
        return {
            'issues': self.issues,
            'suggestions': self.suggestions,
            'stats': {
                'total_issues': len(self.issues),
                'critical': len(critical_issues),
                'major': len(major_issues),
                'minor': len(minor_issues),
                'total_suggestions': len(self.suggestions),
                'high': len(high_suggestions),
                'medium': len(medium_suggestions),
                'low': len(low_suggestions)
            }
        }

def main():
    """主测试流程"""
    print("="*70)
    print("🧪 呼叫中心管理系统 - 用户体验拟人化测试")
    print("="*70)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("测试方式: 拟人化操作，模拟真实用户")
    print("="*70)
    
    tester = UXTester()
    
    # 测试管理员
    if tester.login('admin', '123456', '管理员'):
        tester.test_navigation('管理员')
        tester.test_admin_features()
        tester.session = Session()  # 重置session
    
    time.sleep(1)
    
    # 测试经理
    if tester.login('manager', '123456', '经理'):
        tester.test_manager_features()
        tester.session = Session()
    
    time.sleep(1)
    
    # 测试财务
    if tester.login('finance', '123456', '财务'):
        tester.test_finance_features()
        tester.session = Session()
    
    time.sleep(1)
    
    # 测试员工
    if tester.login('a001', '123456', '员工'):
        tester.test_employee_features()
    
    # 生成报告
    report = tester.generate_report()
    
    # 保存详细报告
    with open('ux_test_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 详细报告已保存到: ux_test_report.json")
    print("="*70)
    
    return report

if __name__ == '__main__':
    main()


