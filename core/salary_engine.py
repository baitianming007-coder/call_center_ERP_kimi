"""
薪资计算引擎
"""
from core.database import query_db


def get_or_calculate_salary(employee_id, year_month):
    """
    获取或计算员工某月薪资
    
    参数:
        employee_id: 员工ID
        year_month: 年月，格式：YYYY-MM
        
    返回:
        dict: 薪资数据字典
    """
    # 先从salary表查询已确认的薪资
    salary = query_db(
        'SELECT * FROM salary WHERE employee_id = ? AND year_month = ?',
        (employee_id, year_month),
        one=True
    )
    
    if salary:
        return dict(salary)
    
    # 如果没有记录，实时计算薪资
    return calculate_salary_realtime(employee_id, year_month)


def calculate_salary_realtime(employee_id, year_month):
    """
    实时计算员工某月薪资
    
    根据产品规则：
    - trainee：仅当月日提成合计
    - C：固定薪资= min(达标日数×30, 90)，达标日数=工作日数≥3则取3，否则0；提成=当月日阶梯提成累加
    - B：固定薪资= 晋级后前6天在本月发生的实际出勤天数×88；提成=当月日阶梯提成累加
    - A：底薪2200；全勤奖= 满足(有效出勤≥25 且 最近6个工作日出单≥12)则400，否则0；
         绩效= 总单<75:0；75-99:300；100-124:600；≥125:1000；提成=当月日阶梯提成累加
    """
    # 获取员工信息
    employee = query_db(
        'SELECT id, employee_no, name, status FROM employees WHERE id = ?',
        (employee_id,),
        one=True
    )
    
    if not employee:
        return _empty_salary(employee_id, year_month)
    
    status = employee['status']
    
    # 查询该月业绩数据
    perf_data = query_db('''
        SELECT 
            COUNT(*) as work_days,
            COUNT(CASE WHEN is_valid_workday = 1 THEN 1 END) as valid_work_days,
            SUM(orders_count) as total_orders,
            SUM(commission) as total_commission
        FROM performance
        WHERE employee_id = ? AND strftime('%Y-%m', work_date) = ?
    ''', (employee_id, year_month), one=True)
    
    work_days = perf_data['work_days'] or 0
    valid_work_days = perf_data['valid_work_days'] or 0
    total_orders = perf_data['total_orders'] or 0
    total_commission = perf_data['total_commission'] or 0
    
    # 根据状态计算薪资
    base_salary = 0
    attendance_bonus = 0
    performance_bonus = 0
    calculation_detail = []
    
    calculation_detail.append(f"员工: {employee['name']} ({employee['employee_no']})")
    calculation_detail.append(f"状态: {status}")
    calculation_detail.append(f"月份: {year_month}")
    calculation_detail.append(f"工作日数: {work_days}, 有效工作日: {valid_work_days}")
    calculation_detail.append(f"总订单数: {total_orders}, 总提成: ¥{total_commission:.2f}")
    calculation_detail.append("")
    
    if status == 'trainee':
        # 培训期：仅提成
        calculation_detail.append("【培训期薪资】")
        calculation_detail.append("- 固定薪资: ¥0")
        calculation_detail.append(f"- 提成: ¥{total_commission:.2f}")
        
    elif status == 'C':
        # C级：固定薪资= min(达标日数×30, 90)
        qualified_days = 3 if work_days >= 3 else 0
        base_salary = min(qualified_days * 30, 90)
        calculation_detail.append("【C级薪资】")
        calculation_detail.append(f"- 工作日数: {work_days} ({'达标' if work_days >= 3 else '未达标'})")
        calculation_detail.append(f"- 固定薪资: min({qualified_days}×30, 90) = ¥{base_salary:.2f}")
        calculation_detail.append(f"- 提成: ¥{total_commission:.2f}")
        
    elif status == 'B':
        # B级：固定薪资= 晋级后前6天在本月发生的实际出勤天数×88
        # 简化处理：取前6个有效工作日，但最多不超过实际工作日数
        b_days = min(work_days, 6)
        base_salary = b_days * 88
        calculation_detail.append("【B级薪资】")
        calculation_detail.append(f"- 前6天出勤: {b_days}天")
        calculation_detail.append(f"- 固定薪资: {b_days}×88 = ¥{base_salary:.2f}")
        calculation_detail.append(f"- 提成: ¥{total_commission:.2f}")
        
    elif status == 'A':
        # A级：底薪2200 + 全勤奖 + 绩效奖 + 提成
        base_salary = 2200
        
        # 全勤奖：有效出勤≥25 且 最近6个工作日出单≥12
        recent_6_orders = query_db('''
            SELECT COALESCE(SUM(orders_count), 0) as orders 
            FROM (
                SELECT orders_count FROM performance
                WHERE employee_id = ? AND strftime('%Y-%m', work_date) = ?
                ORDER BY work_date DESC LIMIT 6
            )
        ''', (employee_id, year_month), one=True)['orders']
        
        if valid_work_days >= 25 and recent_6_orders >= 12:
            attendance_bonus = 400
            calculation_detail.append(f"- 全勤奖: 有效出勤{valid_work_days}≥25 且 最近6日出单{recent_6_orders}≥12，奖励¥400")
        else:
            calculation_detail.append(f"- 全勤奖: 未达标 (有效出勤{valid_work_days}, 最近6日出单{recent_6_orders}) ¥0")
        
        # 绩效奖：总单<75:0；75-99:300；100-124:600；≥125:1000
        if total_orders < 75:
            performance_bonus = 0
        elif total_orders < 100:
            performance_bonus = 300
        elif total_orders < 125:
            performance_bonus = 600
        else:
            performance_bonus = 1000
        
        calculation_detail.append(f"- 绩效奖: 总单{total_orders} → ¥{performance_bonus}")
        calculation_detail.append(f"- 底薪: ¥{base_salary}")
        calculation_detail.append(f"- 提成: ¥{total_commission:.2f}")
    
    total_salary = base_salary + attendance_bonus + performance_bonus + total_commission
    
    calculation_detail.append("")
    calculation_detail.append(f"【总计】 ¥{total_salary:.2f}")
    
    return {
        'employee_id': employee_id,
        'year_month': year_month,
        'base_salary': base_salary,
        'attendance_bonus': attendance_bonus,
        'performance_bonus': performance_bonus,
        'commission': total_commission,
        'total_salary': total_salary,
        'calculation_detail': '\n'.join(calculation_detail)
    }


def _empty_salary(employee_id, year_month):
    """返回空薪资数据"""
    return {
        'employee_id': employee_id,
        'year_month': year_month,
        'base_salary': 0,
        'attendance_bonus': 0,
        'performance_bonus': 0,
        'commission': 0,
        'total_salary': 0,
        'calculation_detail': '未找到员工信息'
    }


def calculate_monthly_salary(employee_id, year_month):
    """
    计算员工某月薪资（触发计算引擎）
    
    注：本系统薪资计算由专门的工资单生成模块处理
    此函数仅为兼容性保留
    
    参数:
        employee_id: 员工ID
        year_month: 年月，格式：YYYY-MM
        
    返回:
        dict: 薪资数据字典
    """
    return get_or_calculate_salary(employee_id, year_month)
