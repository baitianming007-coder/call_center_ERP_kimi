"""
员工端路由
"""
from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from datetime import datetime, timedelta
from core.auth import login_required, role_required, get_current_user, decrypt_phone
from core.database import query_db, execute_db, get_db
from core.commission import calculate_total_commission
from core.salary_engine import get_or_calculate_salary

bp = Blueprint('employee', __name__, url_prefix='/employee')


@bp.route('/performance')
@login_required
@role_required('employee')
def performance():
    """个人业绩页面"""
    user = get_current_user()
    employee_id = user['employee_id']
    
    if not employee_id:
        flash('员工信息未关联', 'danger')
        return redirect(url_for('auth.login'))
    
    # 获取员工基本信息
    employee = query_db(
        'SELECT name, employee_no, status, team FROM employees WHERE id = ?',
        (employee_id,),
        one=True
    )
    
    today = datetime.now().date()
    
    # 今日业绩
    today_perf = query_db(
        'SELECT orders_count, commission FROM performance WHERE employee_id = ? AND work_date = ?',
        (employee_id, today.strftime('%Y-%m-%d')),
        one=True
    )
    
    today_orders = today_perf['orders_count'] if today_perf else 0
    today_commission = today_perf['commission'] if today_perf else 0
    
    # 当月累计
    year_month = today.strftime('%Y-%m')
    month_perf = query_db(
        '''SELECT COUNT(*) as work_days, 
                  SUM(orders_count) as total_orders, 
                  SUM(commission) as total_commission
           FROM performance 
           WHERE employee_id = ? AND strftime('%Y-%m', work_date) = ?''',
        (employee_id, year_month),
        one=True
    )
    
    month_work_days = month_perf['work_days'] if month_perf else 0
    month_orders = month_perf['total_orders'] if month_perf else 0
    month_commission = month_perf['total_commission'] if month_perf else 0
    
    # 最近N天（根据状态：C=3天，B/A=6天）
    status = employee['status']
    recent_days = 3 if status == 'C' else 6
    recent_start = today - timedelta(days=recent_days-1)
    
    recent_perf = query_db(
        '''SELECT SUM(orders_count) as total_orders, SUM(commission) as total_commission
           FROM performance 
           WHERE employee_id = ? AND work_date >= ? AND work_date <= ?''',
        (employee_id, recent_start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')),
        one=True
    )
    
    recent_orders = recent_perf['total_orders'] if recent_perf else 0
    recent_commission = recent_perf['total_commission'] if recent_perf else 0
    
    # 获取最近7天的详细数据（用于图表）
    chart_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        perf = query_db(
            'SELECT orders_count, commission FROM performance WHERE employee_id = ? AND work_date = ?',
            (employee_id, date.strftime('%Y-%m-%d')),
            one=True
        )
        chart_data.append({
            'date': date.strftime('%m-%d'),
            'orders': perf['orders_count'] if perf else 0,
            'commission': perf['commission'] if perf else 0
        })
    
    return render_template('employee/performance.html',
                         employee=employee,
                         today_orders=today_orders,
                         today_commission=today_commission,
                         month_work_days=month_work_days,
                         month_orders=month_orders,
                         month_commission=month_commission,
                         recent_days=recent_days,
                         recent_orders=recent_orders,
                         recent_commission=recent_commission,
                         chart_data=chart_data)


@bp.route('/salary')
@login_required
@role_required('employee')
def salary():
    """个人薪资页面"""
    user = get_current_user()
    employee_id = user['employee_id']
    
    if not employee_id:
        flash('员工信息未关联', 'danger')
        return redirect(url_for('auth.login'))
    
    # 获取员工基本信息
    employee = query_db(
        'SELECT id, name, employee_no, status, team FROM employees WHERE id = ?',
        (employee_id,),
        one=True
    )
    
    # 当月薪资（实时计算或获取已确认的）
    today = datetime.now().date()
    current_month = today.strftime('%Y-%m')
    current_salary = get_or_calculate_salary(employee_id, current_month)
    
    # 历史6个月薪资（实时计算或获取已确认的）
    history_salaries = []
    for i in range(1, 7):
        past_date = today - timedelta(days=30*i)
        year_month = past_date.strftime('%Y-%m')
        salary_data = get_or_calculate_salary(employee_id, year_month)
        salary_data['year_month'] = year_month
        history_salaries.append(salary_data)
    
    # 查询异议记录
    disputes = query_db(
        '''SELECT d.id, d.salary_id, d.reason, d.status, d.response, 
                  d.created_at, s.year_month
           FROM salary_disputes d
           JOIN salary s ON d.salary_id = s.id
           WHERE d.employee_id = ?
           ORDER BY d.created_at DESC
           LIMIT 10''',
        (employee_id,)
    )
    
    return render_template('employee/salary.html',
                         employee=employee,
                         current_month=current_month,
                         current_salary=current_salary,
                         history_salaries=history_salaries,
                         disputes=disputes)


@bp.route('/submit_dispute', methods=['POST'])
@login_required
@role_required('employee')
def submit_dispute():
    """提交薪资异议"""
    user = get_current_user()
    employee_id = user['employee_id']
    
    salary_id = request.form.get('salary_id')
    reason = request.form.get('reason', '').strip()
    
    if not salary_id or not reason:
        return jsonify({'success': False, 'message': '请填写完整信息'})
    
    # 验证 salary_id 是否属于当前员工
    salary = query_db(
        'SELECT id FROM salary WHERE id = ? AND employee_id = ?',
        (salary_id, employee_id),
        one=True
    )
    
    if not salary:
        return jsonify({'success': False, 'message': '无效的薪资记录'})
    
    # 检查是否已有pending的异议
    existing = query_db(
        "SELECT id FROM salary_disputes WHERE salary_id = ? AND employee_id = ? AND status = 'pending'",
        (salary_id, employee_id),
        one=True
    )
    
    if existing:
        return jsonify({'success': False, 'message': '该月薪资已有待处理的异议'})
    
    # 创建异议
    try:
        execute_db(
            '''INSERT INTO salary_disputes (employee_id, salary_id, reason, status)
               VALUES (?, ?, ?, 'pending')''',
            (employee_id, salary_id, reason)
        )
        
        # 更新薪资状态为 disputed
        execute_db(
            "UPDATE salary SET status = 'disputed' WHERE id = ?",
            (salary_id,)
        )
        
        return jsonify({'success': True, 'message': '异议已提交，等待管理员处理'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'提交失败: {str(e)}'})


@bp.route('/profile')
@login_required
@role_required('employee')
def profile():
    """个人信息页面 (P2-15增强)"""
    user = get_current_user()
    employee_id = user['employee_id']
    
    if not employee_id:
        flash('员工信息未关联', 'danger')
        return redirect(url_for('auth.login'))
    
    # 获取员工完整信息（包含银行信息）
    employee = query_db(
        '''SELECT id, employee_no, name, phone, phone_encrypted, team, status, 
                  join_date, is_active, bank_account_number, bank_name, 
                  account_holder_name, bank_info_status
           FROM employees WHERE id = ?''',
        (employee_id,),
        one=True
    )
    
    # 解密手机号（用于显示）
    phone_display = decrypt_phone(employee['phone_encrypted']) if employee['phone_encrypted'] else employee['phone']
    
    # P2-15: 获取近30天业绩统计
    from datetime import datetime, timedelta
    today = datetime.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    performance_stats = query_db(
        '''SELECT 
               COUNT(*) as days_worked,
               SUM(orders_count) as total_orders,
               SUM(commission) as total_commission,
               AVG(orders_count) as avg_orders_per_day
           FROM performance
           WHERE employee_id = ? AND work_date >= ? AND work_date <= ?''',
        (employee_id, thirty_days_ago, today),
        one=True
    )
    
    # P2-15: 获取近7天每日业绩（用于图表）
    seven_days_ago = today - timedelta(days=7)
    recent_performance = query_db(
        '''SELECT work_date as date, orders_count as orders, commission
           FROM performance
           WHERE employee_id = ? AND work_date >= ?
           ORDER BY work_date ASC''',
        (employee_id, seven_days_ago)
    )
    
    # P2-15: 获取近6个月薪资记录
    from core.salary_engine import get_or_calculate_salary
    six_months_ago = today - timedelta(days=180)
    
    salary_history = []
    current_month = today.replace(day=1)
    for i in range(6):
        year_month = current_month.strftime('%Y-%m')
        salary_data = get_or_calculate_salary(employee_id, year_month)
        if salary_data and salary_data.get('total_salary', 0) > 0:
            salary_history.append({
                'year_month': year_month,
                'total_salary': salary_data['total_salary'],
                'base_salary': salary_data.get('base_salary', 0),
                'commission': salary_data.get('commission', 0)
            })
        
        # 回退到上个月
        current_month = (current_month - timedelta(days=1)).replace(day=1)
    
    salary_history.reverse()  # 从旧到新排列
    
    # 获取状态变更历史
    status_history = query_db(
        '''SELECT from_status, to_status, change_date, reason, days_in_status
           FROM status_history
           WHERE employee_id = ?
           ORDER BY change_date DESC
           LIMIT 10''',
        (employee_id,)
    )
    
    # 格式化状态名称
    status_map = {'trainee': '培训期', 'C': 'C级', 'B': 'B级', 'A': 'A级', 'eliminated': '已淘汰'}
    current_status_name = status_map.get(employee['status'], employee['status'])
    
    # 计算在职天数
    if employee['join_date']:
        # join_date从SQLite返回的可能是字符串或date对象
        join_date_obj = employee['join_date']
        if isinstance(join_date_obj, str):
            from datetime import datetime
            join_date_obj = datetime.strptime(join_date_obj, '%Y-%m-%d').date()
        days_employed = (today - join_date_obj).days
    else:
        days_employed = 0
    
    return render_template('employee/profile.html',
                         employee=employee,
                         phone_display=phone_display,
                         current_status_name=current_status_name,
                         performance_stats=performance_stats,
                         recent_performance=recent_performance,
                         salary_history=salary_history,
                         status_history=status_history,
                         today=today,
                         days_employed=days_employed)


@bp.route('/update_phone', methods=['POST'])
@login_required
@role_required('employee')
def update_phone():
    """更新手机号"""
    user = get_current_user()
    employee_id = user['employee_id']
    
    new_phone = request.form.get('phone', '').strip()
    
    if not new_phone:
        return jsonify({'success': False, 'message': '请输入手机号'})
    
    # 简单验证手机号格式
    if len(new_phone) != 11 or not new_phone.isdigit():
        return jsonify({'success': False, 'message': '手机号格式不正确'})
    
    try:
        from core.auth import encrypt_phone
        encrypted = encrypt_phone(new_phone)
        
        execute_db(
            'UPDATE employees SET phone = ?, phone_encrypted = ? WHERE id = ?',
            (new_phone, encrypted, employee_id)
        )
        
        return jsonify({'success': True, 'message': '手机号已更新'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})


