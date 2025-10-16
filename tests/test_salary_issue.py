"""
薪资统计和工资单数据测试
"""
import requests
from datetime import datetime

BASE_URL = "http://127.0.0.1:8080"

def test_salary_page():
    """测试薪资统计页面"""
    print("\n" + "="*60)
    print("测试薪资统计页面")
    print("="*60)
    
    # 创建session并登录
    s = requests.Session()
    
    # 登录管理员
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    r = s.post(f"{BASE_URL}/login", data=login_data, allow_redirects=True)
    
    if "退出登录" in r.text or "admin" in r.text:
        print("✅ 管理员登录成功")
    else:
        print("❌ 管理员登录失败")
        return False
    
    # 访问薪资统计页面
    year_month = datetime.now().strftime('%Y-%m')
    r = s.get(f"{BASE_URL}/admin/salary?year_month={year_month}")
    
    print(f"\n访问 /admin/salary?year_month={year_month}")
    print(f"响应状态: {r.status_code}")
    
    if r.status_code != 200:
        print(f"❌ 页面访问失败: {r.status_code}")
        print(f"响应内容前500字符:\n{r.text[:500]}")
        return False
    
    # 检查页面内容
    has_data = False
    issues = []
    
    if "salary_list" in r.text or "薪资统计" in r.text:
        print("✅ 页面标题显示正常")
    else:
        issues.append("页面标题未显示")
    
    if "该月份暂无薪资数据" in r.text:
        print("⚠️  显示无数据提示")
        has_data = False
    elif "employee_no" in r.text or "<tbody>" in r.text:
        print("✅ 检测到表格数据")
        has_data = True
        # 统计行数
        tbody_count = r.text.count("<tr>") - 1  # 减去表头
        print(f"   表格行数: {tbody_count}")
    else:
        issues.append("表格未正常渲染")
    
    # 检查统计数据
    if "总薪资" in r.text:
        print("✅ 统计摘要显示正常")
    else:
        issues.append("统计摘要未显示")
    
    if issues:
        print(f"\n❌ 发现问题:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print(f"\n✅ 薪资统计页面测试通过 (有数据: {has_data})")
        return True


def test_employee_salary():
    """测试员工工资单页面"""
    print("\n" + "="*60)
    print("测试员工工资单页面")
    print("="*60)
    
    # 创建session并登录
    s = requests.Session()
    
    # 登录员工
    login_data = {
        'username': 'a001',
        'password': 'emp123'
    }
    r = s.post(f"{BASE_URL}/login", data=login_data, allow_redirects=True)
    
    if "退出登录" in r.text:
        print("✅ 员工登录成功")
    else:
        print("❌ 员工登录失败")
        return False
    
    # 访问工资单页面
    r = s.get(f"{BASE_URL}/employee/salary")
    
    print(f"\n访问 /employee/salary")
    print(f"响应状态: {r.status_code}")
    
    if r.status_code != 200:
        print(f"❌ 页面访问失败: {r.status_code}")
        print(f"响应内容前500字符:\n{r.text[:500]}")
        return False
    
    # 检查页面内容
    issues = []
    
    if "我的工资单" in r.text or "工资单" in r.text:
        print("✅ 页面标题显示正常")
    else:
        issues.append("页面标题未显示")
    
    if "暂无工资单" in r.text:
        print("⚠️  显示无数据提示")
    elif "salary_history" in r.text or "历史工资单" in r.text:
        print("✅ 检测到工资单数据")
    else:
        issues.append("工资单数据未显示")
    
    if issues:
        print(f"\n❌ 发现问题:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print(f"\n✅ 员工工资单页面测试通过")
        return True


def check_database_data():
    """检查数据库中的数据"""
    print("\n" + "="*60)
    print("检查数据库薪资数据")
    print("="*60)
    
    import sqlite3
    
    conn = sqlite3.connect('data/callcenter.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 检查员工数量
    cursor.execute("SELECT COUNT(*) as cnt FROM employees WHERE is_active = 1")
    emp_count = cursor.fetchone()['cnt']
    print(f"活跃员工数量: {emp_count}")
    
    # 检查业绩数据
    year_month = datetime.now().strftime('%Y-%m')
    cursor.execute("""
        SELECT COUNT(*) as cnt, SUM(orders_count) as total_orders 
        FROM performance 
        WHERE strftime('%Y-%m', work_date) = ?
    """, (year_month,))
    perf = cursor.fetchone()
    print(f"本月业绩记录: {perf['cnt']} 条, 总订单: {perf['total_orders'] or 0}")
    
    # 检查薪资表
    cursor.execute("""
        SELECT COUNT(*) as cnt 
        FROM salary 
        WHERE year_month = ?
    """, (year_month,))
    salary_count = cursor.fetchone()['cnt']
    print(f"本月薪资记录: {salary_count} 条")
    
    conn.close()
    
    return {
        'employees': emp_count,
        'performance': perf['cnt'],
        'salaries': salary_count
    }


if __name__ == '__main__':
    print("\n🔍 开始检测薪资和工资单数据显示问题")
    print("="*60)
    
    # 检查数据库
    db_info = check_database_data()
    
    # 测试管理员薪资统计页面
    salary_ok = test_salary_page()
    
    # 测试员工工资单页面
    employee_ok = test_employee_salary()
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"数据库状态: 员工{db_info['employees']}人, 业绩{db_info['performance']}条, 确认薪资{db_info['salaries']}条")
    print(f"薪资统计页面: {'✅ 通过' if salary_ok else '❌ 失败'}")
    print(f"员工工资单页面: {'✅ 通过' if employee_ok else '❌ 失败'}")
    
    if not salary_ok or not employee_ok:
        print("\n⚠️  发现问题，需要进一步调查")
    else:
        print("\n✅ 所有测试通过")

