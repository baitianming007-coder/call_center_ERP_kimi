"""测试薪资计算函数"""
import sys
sys.path.insert(0, '/Users/kimi/Desktop/call center 2.0')

from app import app
from core.salary_engine import get_or_calculate_salary
from core.database import query_db
from datetime import datetime

with app.app_context():
    # 获取第一个员工
    emp = query_db('SELECT id, name, employee_no FROM employees WHERE is_active=1 LIMIT 1', one=True)
    print(f'测试员工: {emp["employee_no"]} - {emp["name"]} (ID: {emp["id"]})')
    
    # 检查该员工的业绩数据
    year_month = datetime.now().strftime('%Y-%m')
    perf = query_db('''
        SELECT COUNT(*) as cnt, SUM(orders_count) as total_orders, SUM(commission) as total_commission
        FROM performance 
        WHERE employee_id = ? AND strftime('%Y-%m', work_date) = ?
    ''', (emp['id'], year_month), one=True)
    
    print(f'\n{year_month} 业绩数据:')
    print(f'  记录数: {perf["cnt"]}')
    print(f'  总订单: {perf["total_orders"] or 0}')
    print(f'  总提成: {perf["total_commission"] or 0}')
    
    # 计算薪资
    print(f'\n开始计算薪资...')
    salary = get_or_calculate_salary(emp['id'], year_month)
    
    print(f'\n薪资计算结果:')
    print(f'  底薪: ¥{salary.get("base_salary", 0):.2f}')
    print(f'  全勤奖: ¥{salary.get("attendance_bonus", 0):.2f}')
    print(f'  绩效奖: ¥{salary.get("performance_bonus", 0):.2f}')
    print(f'  提成: ¥{salary.get("commission", 0):.2f}')
    print(f'  总计: ¥{salary.get("total_salary", 0):.2f}')
    
    if salary.get("calculation_detail"):
        print(f'\n计算明细:')
        print(salary["calculation_detail"][:300])


