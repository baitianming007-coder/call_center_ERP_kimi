"""
管理端路由（manager & admin）
"""
from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for, send_file
from datetime import datetime, timedelta
from core.auth import login_required, role_required, get_current_user, get_user_team, check_employee_access, hash_password, encrypt_phone
from core.database import query_db, execute_db, get_db
from core.status_engine import batch_check_all_employees, apply_status_change, check_status_transition
from core.salary_engine import get_or_calculate_salary, calculate_monthly_salary
from core.commission import calculate_daily_commission
from core.import_helper import ExcelImporter, generate_import_template
from config import Config
import io
import os
from werkzeug.utils import secure_filename

bp = Blueprint('admin', __name__, url_prefix='/admin')


# ==================== 主看板 ====================

@bp.route('/dashboard')
@login_required
@role_required('manager', 'admin')
def dashboard():
    """主看板"""
    user = get_current_user()
    team = get_user_team(user)
    
    today = datetime.now().date()
    year_month = today.strftime('%Y-%m')
    
    # 构建团队过滤条件
    team_filter = 'WHERE e.is_active = 1'
    params = []
    if team:
        team_filter += ' AND e.team = ?'
        params.append(team)
    
    # 统计数据
    # 1. 人员统计
    staff_stats = query_db(f'''
        SELECT status, COUNT(*) as count
        FROM employees e
        {team_filter}
        GROUP BY status
    ''', params)
    
    stats_dict = {s['status']: s['count'] for s in staff_stats}
    total_staff = sum(stats_dict.values())
    
    # 2. 今日业绩
    today_perf = query_db(f'''
        SELECT COUNT(DISTINCT e.id) as working_count,
               SUM(p.orders_count) as total_orders,
               SUM(p.commission) as total_commission
        FROM employees e
        LEFT JOIN performance p ON e.id = p.employee_id AND p.work_date = ?
        {team_filter}
    ''', [today.strftime('%Y-%m-%d')] + params, one=True)
    
    # 3. 本月累计
    month_perf = query_db(f'''
        SELECT SUM(p.orders_count) as total_orders,
               SUM(p.commission) as total_commission,
               COUNT(DISTINCT p.employee_id) as active_count
        FROM performance p
        JOIN employees e ON p.employee_id = e.id
        WHERE strftime('%Y-%m', p.work_date) = ?
        {'' if not team else 'AND e.team = ?'}
    ''', [year_month] + ([] if not team else [team]), one=True)
    
    # 4. 收入成本（本月）
    month_revenue = (month_perf['total_orders'] or 0) * Config.REVENUE_PER_ORDER
    
    # 估算成本（查询已确认薪资或实时计算）
    month_cost = 0
    employees = query_db(f'''
        SELECT id FROM employees e
        {team_filter}
    ''', params)
    
    for emp in employees:
        salary_data = get_or_calculate_salary(emp['id'], year_month)
        month_cost += salary_data.get('total_salary', 0)
    
    month_profit = month_revenue - month_cost
    
    # 5. 最近7天趋势
    trend_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        day_perf = query_db(f'''
            SELECT SUM(p.orders_count) as orders, SUM(p.commission) as commission
            FROM performance p
            JOIN employees e ON p.employee_id = e.id
            WHERE p.work_date = ?
            {'' if not team else 'AND e.team = ?'}
        ''', [date.strftime('%Y-%m-%d')] + ([] if not team else [team]), one=True)
        
        trend_data.append({
            'date': date.strftime('%m-%d'),
            'orders': day_perf['orders'] or 0,
            'commission': day_perf['commission'] or 0
        })
    
    # 6. 状态分布（用于饼图）
    status_distribution = [
        {'status': 'A', 'count': stats_dict.get('A', 0), 'label': 'A级'},
        {'status': 'B', 'count': stats_dict.get('B', 0), 'label': 'B级'},
        {'status': 'C', 'count': stats_dict.get('C', 0), 'label': 'C级'},
        {'status': 'trainee', 'count': stats_dict.get('trainee', 0), 'label': '培训期'},
        {'status': 'eliminated', 'count': stats_dict.get('eliminated', 0), 'label': '已淘汰'},
    ]
    
    return render_template('admin/dashboard.html',
                         user=user,
                         team=team,
                         total_staff=total_staff,
                         today_working=today_perf['working_count'] or 0,
                         today_orders=today_perf['total_orders'] or 0,
                         today_commission=today_perf['total_commission'] or 0,
                         month_orders=month_perf['total_orders'] or 0,
                         month_commission=month_perf['total_commission'] or 0,
                         month_revenue=month_revenue,
                         month_cost=month_cost,
                         month_profit=month_profit,
                         trend_data=trend_data,
                         status_distribution=status_distribution)


# ==================== 员工管理 ====================

@bp.route('/employees')
@login_required
@role_required('manager', 'admin')
def employees():
    """员工管理列表"""
    user = get_current_user()
    team = get_user_team(user)
    
    # 获取筛选参数
    filter_team = request.args.get('team', '')
    filter_status = request.args.get('status', '')
    search_keyword = request.args.get('search', '')
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # 构建查询条件
    where_conditions = ['is_active = 1']
    params = []
    
    # 团队过滤（权限控制）
    if team:
        where_conditions.append('team = ?')
        params.append(team)
    elif filter_team:
        where_conditions.append('team = ?')
        params.append(filter_team)
    
    # 状态过滤
    if filter_status:
        where_conditions.append('status = ?')
        params.append(filter_status)
    
    # 搜索
    if search_keyword:
        where_conditions.append('(name LIKE ? OR employee_no LIKE ?)')
        params.extend([f'%{search_keyword}%', f'%{search_keyword}%'])
    
    where_clause = ' AND '.join(where_conditions)
    
    # 查询总数
    count_query = f'SELECT COUNT(*) as total FROM employees WHERE {where_clause}'
    total = query_db(count_query, params, one=True)['total']
    
    # 计算分页
    total_pages = (total + per_page - 1) // per_page  # 向上取整
    page = max(1, min(page, total_pages or 1))  # 确保页码在有效范围内
    offset = (page - 1) * per_page
    
    # 查询当前页数据
    query = f'SELECT * FROM employees WHERE {where_clause} ORDER BY join_date DESC LIMIT ? OFFSET ?'
    employees_list = query_db(query, params + [per_page, offset])
    
    # 获取所有团队（用于筛选）
    teams = query_db('SELECT DISTINCT team FROM employees ORDER BY team')
    
    # 生成分页信息
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None,
        'pages': list(range(max(1, page - 2), min(total_pages + 1, page + 3)))  # 显示当前页前后2页
    }
    
    return render_template('admin/employees.html',
                         breadcrumbs=[{'name': '员工管理'}],
                         employees=employees_list,
                         teams=teams,
                         user=user,
                         current_team=filter_team,
                         current_status=filter_status,
                         search_keyword=search_keyword,
                         pagination=pagination)


@bp.route('/employee/add', methods=['GET', 'POST'])
@login_required
@role_required('manager', 'admin')
def employee_add():
    """添加员工"""
    user = get_current_user()
    team = get_user_team(user)
    
    if request.method == 'POST':
        employee_no = request.form.get('employee_no', '').strip()
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        emp_team = request.form.get('team', '').strip()
        join_date = request.form.get('join_date', '').strip()
        
        # 权限检查：manager 只能添加本团队员工
        if team and emp_team != team:
            flash('您只能添加本团队员工', 'danger')
            return redirect(url_for('admin.employees'))
        
        # 验证必填字段
        if not all([employee_no, name, emp_team, join_date]):
            flash('请填写完整信息', 'warning')
            return redirect(url_for('admin.employee_add'))
        
        # 检查工号是否重复
        existing = query_db('SELECT id FROM employees WHERE employee_no = ?', (employee_no,), one=True)
        if existing:
            flash('工号已存在', 'danger')
            return redirect(url_for('admin.employee_add'))
        
        try:
            phone_encrypted = encrypt_phone(phone) if phone else None
            
            employee_id = execute_db(
                '''INSERT INTO employees 
                   (employee_no, name, phone, phone_encrypted, team, status, join_date, is_active)
                   VALUES (?, ?, ?, ?, ?, 'trainee', ?, 1)''',
                (employee_no, name, phone, phone_encrypted, emp_team, join_date)
            )
            
            flash(f'员工 {name} 添加成功', 'success')
            return redirect(url_for('admin.employees'))
        except Exception as e:
            flash(f'添加失败: {str(e)}', 'danger')
    
    # GET: 显示表单
    teams = query_db('SELECT team_name FROM teams WHERE is_active = 1')
    
    return render_template('admin/employee_form.html',
                         user=user,
                         teams=teams,
                         allowed_team=team,
                         action='add')


@bp.route('/employee/<int:emp_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('manager', 'admin')
def employee_edit(emp_id):
    """编辑员工"""
    user = get_current_user()
    
    # 权限检查
    if not check_employee_access(user, emp_id):
        flash('无权访问此员工', 'danger')
        return redirect(url_for('admin.employees'))
    
    employee = query_db('SELECT * FROM employees WHERE id = ?', (emp_id,), one=True)
    if not employee:
        flash('员工不存在', 'danger')
        return redirect(url_for('admin.employees'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        emp_team = request.form.get('team', '').strip()
        status = request.form.get('status', '').strip()
        
        if not all([name, emp_team, status]):
            flash('请填写完整信息', 'warning')
            return redirect(url_for('admin.employee_edit', emp_id=emp_id))
        
        try:
            phone_encrypted = encrypt_phone(phone) if phone else None
            
            execute_db(
                '''UPDATE employees 
                   SET name = ?, phone = ?, phone_encrypted = ?, team = ?, status = ?
                   WHERE id = ?''',
                (name, phone, phone_encrypted, emp_team, status, emp_id)
            )
            
            flash(f'员工 {name} 信息已更新', 'success')
            return redirect(url_for('admin.employees'))
        except Exception as e:
            flash(f'更新失败: {str(e)}', 'danger')
    
    # GET: 显示表单
    teams = query_db('SELECT team_name FROM teams WHERE is_active = 1')
    
    return render_template('admin/employee_form.html',
                         user=user,
                         employee=employee,
                         teams=teams,
                         action='edit')


@bp.route('/employee/<int:emp_id>/delete', methods=['POST'])
@login_required
@role_required('manager', 'admin')
def employee_delete(emp_id):
    """删除员工（软删除）"""
    user = get_current_user()
    
    # 权限检查
    if not check_employee_access(user, emp_id):
        return jsonify({'success': False, 'message': '无权操作此员工'})
    
    try:
        today = datetime.now().date().strftime('%Y-%m-%d')
        execute_db(
            'UPDATE employees SET is_active = 0, leave_date = ? WHERE id = ?',
            (today, emp_id)
        )
        return jsonify({'success': True, 'message': '员工已离职'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})


# ==================== 业绩管理 ====================

@bp.route('/performance')
@login_required
@role_required('manager', 'admin')
def performance():
    """业绩管理（支持单日和日期区间查询）"""
    user = get_current_user()
    team = get_user_team(user)
    
    # 获取筛选参数
    filter_date = request.args.get('date', '')  # 单日查询
    date_start = request.args.get('date_start', '')  # 日期区间开始
    date_end = request.args.get('date_end', '')  # 日期区间结束
    filter_employee = request.args.get('employee', '')
    filter_team = request.args.get('team', '')
    filter_status = request.args.get('status', '')
    
    # 确定查询日期模式
    if date_start and date_end:
        # 日期区间模式
        date_condition = 'p.work_date BETWEEN ? AND ?'
        date_params = [date_start, date_end]
        display_date = f'{date_start} 至 {date_end}'
    elif filter_date:
        # 单日模式
        date_condition = 'p.work_date = ?'
        date_params = [filter_date]
        display_date = filter_date
    else:
        # 默认今天
        today = datetime.now().date().strftime('%Y-%m-%d')
        date_condition = 'p.work_date = ?'
        date_params = [today]
        display_date = today
        filter_date = today
    
    # 构建查询
    query = f'''
        SELECT p.*, e.employee_no, e.name, e.team, e.status
        FROM performance p
        JOIN employees e ON p.employee_id = e.id
        WHERE {date_condition}
    '''
    params = date_params
    
    # 用户团队权限过滤
    if team:
        query += ' AND e.team = ?'
        params.append(team)
    # 额外的团队过滤
    elif filter_team:
        query += ' AND e.team = ?'
        params.append(filter_team)
    
    # 员工过滤
    if filter_employee:
        query += ' AND e.id = ?'
        params.append(filter_employee)
    
    # 状态过滤
    if filter_status:
        query += ' AND e.status = ?'
        params.append(filter_status)
    
    query += ' ORDER BY p.work_date DESC, p.orders_count DESC, e.name'
    
    performance_list = query_db(query, params)
    
    # 获取员工列表（用于筛选）
    emp_query = '''
        SELECT id, employee_no, name, team, status 
        FROM employees 
        WHERE is_active = 1
    '''
    emp_params = []
    if team:
        emp_query += ' AND team = ?'
        emp_params.append(team)
    emp_query += ' ORDER BY employee_no'
    
    employees_raw = query_db(emp_query, emp_params)
    
    # 转换为字典列表（用于JSON序列化）
    employees = [dict(emp) for emp in employees_raw] if employees_raw else []
    
    # 统计
    total_orders = sum(p['orders_count'] for p in performance_list)
    total_commission = sum(p['commission'] for p in performance_list)
    
    return render_template('admin/performance.html',
                         performance_list=performance_list,
                         employees=employees,
                         filter_date=filter_date or '',
                         date_start=date_start,
                         date_end=date_end,
                         filter_employee=filter_employee,
                         filter_team=filter_team,
                         filter_status=filter_status,
                         total_orders=total_orders,
                         total_commission=total_commission,
                         user=user)


@bp.route('/performance/add', methods=['GET', 'POST'])
@login_required
@role_required('manager', 'admin')
def performance_add():
    """添加业绩记录"""
    user = get_current_user()
    team = get_user_team(user)
    
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        work_date = request.form.get('work_date')
        orders_count = request.form.get('orders_count', 0, type=int)
        is_valid_workday = request.form.get('is_valid_workday', 1, type=int)
        
        if not employee_id or not work_date:
            return jsonify({'success': False, 'message': '请填写完整信息'})
        
        # 权限检查
        if not check_employee_access(user, int(employee_id)):
            return jsonify({'success': False, 'message': '无权操作此员工'})
        
        try:
            # 计算提成
            commission = calculate_daily_commission(orders_count)
            
            # 检查是否已存在
            existing = query_db(
                'SELECT id FROM performance WHERE employee_id = ? AND work_date = ?',
                (employee_id, work_date),
                one=True
            )
            
            if existing:
                # 更新
                execute_db(
                    '''UPDATE performance 
                       SET orders_count = ?, commission = ?, is_valid_workday = ?
                       WHERE id = ?''',
                    (orders_count, commission, is_valid_workday, existing['id'])
                )
                message = '业绩记录已更新'
            else:
                # 插入
                execute_db(
                    '''INSERT INTO performance 
                       (employee_id, work_date, orders_count, commission, is_valid_workday)
                       VALUES (?, ?, ?, ?, ?)''',
                    (employee_id, work_date, orders_count, commission, is_valid_workday)
                )
                message = '业绩记录已添加'
            
            return jsonify({'success': True, 'message': message})
        except Exception as e:
            return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})
    
    # GET: 获取员工列表
    emp_query = 'SELECT id, employee_no, name, team FROM employees WHERE is_active = 1'
    emp_params = []
    if team:
        emp_query += ' AND team = ?'
        emp_params.append(team)
    emp_query += ' ORDER BY employee_no'
    
    employees = query_db(emp_query, emp_params)
    
    return render_template('admin/performance_add.html',
                         employees=employees,
                         user=user)


@bp.route('/performance/batch', methods=['GET', 'POST'])
@login_required
@role_required('manager', 'admin')
def performance_batch():
    """批量录入业绩"""
    user = get_current_user()
    team = get_user_team(user)
    
    if request.method == 'POST':
        work_date = request.form.get('work_date')
        batch_data = request.get_json()
        
        if not work_date or not batch_data:
            return jsonify({'success': False, 'message': '数据不完整'})
        
        try:
            db = get_db()
            success_count = 0
            
            for item in batch_data:
                employee_id = item.get('employee_id')
                orders_count = item.get('orders_count', 0)
                is_valid = item.get('is_valid_workday', 1)
                
                # 权限检查
                if not check_employee_access(user, int(employee_id)):
                    continue
                
                commission = calculate_daily_commission(orders_count)
                
                # 使用 REPLACE 处理冲突
                db.execute(
                    '''INSERT OR REPLACE INTO performance 
                       (employee_id, work_date, orders_count, commission, is_valid_workday)
                       VALUES (?, ?, ?, ?, ?)''',
                    (employee_id, work_date, orders_count, commission, is_valid)
                )
                success_count += 1
            
            db.commit()
            return jsonify({'success': True, 'message': f'已录入{success_count}条记录'})
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'message': f'批量录入失败: {str(e)}'})
    
    # GET: 获取员工列表
    emp_query = 'SELECT id, employee_no, name, status FROM employees WHERE is_active = 1'
    emp_params = []
    if team:
        emp_query += ' AND team = ?'
        emp_params.append(team)
    emp_query += ' ORDER BY employee_no'
    
    employees = query_db(emp_query, emp_params)
    
    return render_template('admin/performance_batch.html',
                         employees=employees,
                         user=user,
                         default_date=datetime.now().date().strftime('%Y-%m-%d'))


@bp.route('/performance/import', methods=['GET', 'POST'])
@login_required
@role_required('manager', 'admin')
def performance_import():
    """Excel导入业绩"""
    user = get_current_user()
    
    if request.method == 'POST':
        # 检查文件
        if 'file' not in request.files:
            flash('请选择要导入的文件', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('未选择文件', 'danger')
            return redirect(request.url)
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('只支持Excel文件（.xlsx, .xls）', 'danger')
            return redirect(request.url)
        
        try:
            # 保存临时文件
            filename = secure_filename(file.filename)
            temp_path = os.path.join('/tmp', f'import_{datetime.now().timestamp()}_{filename}')
            file.save(temp_path)
            
            # 执行导入
            importer = ExcelImporter()
            result = importer.import_from_file(temp_path, user['id'])
            
            # 删除临时文件
            os.remove(temp_path)
            
            if result['success']:
                flash(result['message'], 'success')
                
                # 显示警告
                if result.get('warnings'):
                    for warning in result['warnings']:
                        flash(warning, 'warning')
                
                # 显示错误
                if result.get('errors'):
                    for error in result['errors'][:5]:  # 最多显示5个错误
                        flash(error, 'danger')
                    if len(result['errors']) > 5:
                        flash(f'还有 {len(result["errors"]) - 5} 个错误未显示', 'info')
            else:
                flash(result['message'], 'danger')
                for error in result.get('errors', [])[:10]:
                    flash(error, 'danger')
            
            return redirect(url_for('admin.performance'))
            
        except Exception as e:
            flash(f'导入失败: {str(e)}', 'danger')
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return redirect(request.url)
    
    # GET: 显示导入页面
    return render_template('admin/performance_import.html',
                         breadcrumbs=[
                             {'name': '业绩管理', 'url': url_for('admin.performance')},
                             {'name': 'Excel导入'}
                         ])


@bp.route('/performance/download_template')
@login_required
@role_required('manager', 'admin')
def performance_download_template():
    """下载Excel导入模板"""
    template_file = generate_import_template()
    
    return send_file(
        template_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'业绩导入模板_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )


# ==================== 状态检查与变更 ====================

@bp.route('/status_check')
@login_required
@role_required('manager', 'admin')
def status_check():
    """状态变更检查"""
    user = get_current_user()
    team = get_user_team(user)
    
    # 批量检查所有员工
    all_changes = batch_check_all_employees()
    
    # 团队过滤
    if team:
        changes = [c for c in all_changes if c['team'] == team]
    else:
        changes = all_changes
    
    return render_template('admin/status_check.html',
                         changes=changes,
                         user=user)


@bp.route('/status_change/apply', methods=['POST'])
@login_required
@role_required('manager', 'admin')
def status_change_apply():
    """应用状态变更"""
    user = get_current_user()
    
    data = request.get_json()
    employee_id = data.get('employee_id')
    new_status = data.get('new_status')
    reason = data.get('reason')
    days_in_status = data.get('days_in_status')
    
    if not all([employee_id, new_status, reason]):
        return jsonify({'success': False, 'message': '数据不完整'})
    
    # 权限检查
    if not check_employee_access(user, int(employee_id)):
        return jsonify({'success': False, 'message': '无权操作此员工'})
    
    # 应用变更
    success = apply_status_change(employee_id, new_status, reason, days_in_status)
    
    if success:
        return jsonify({'success': True, 'message': '状态已更新'})
    else:
        return jsonify({'success': False, 'message': '状态更新失败'})


# ==================== 薪资统计 ====================

@bp.route('/salary')
@login_required
@role_required('manager', 'admin')
def salary():
    """薪资统计（支持团队、员工和状态筛选）"""
    user = get_current_user()
    team = get_user_team(user)
    
    # 获取筛选参数
    year_month = request.args.get('year_month', datetime.now().date().strftime('%Y-%m'))
    filter_employee = request.args.get('employee', '')
    filter_team = request.args.get('team', '')
    filter_status = request.args.get('status', '')
    
    # 获取员工列表
    emp_query = 'SELECT id, employee_no, name, status, team FROM employees WHERE is_active = 1'
    emp_params = []
    
    # 用户团队权限过滤
    if team:
        emp_query += ' AND team = ?'
        emp_params.append(team)
    # 额外的团队过滤
    elif filter_team:
        emp_query += ' AND team = ?'
        emp_params.append(filter_team)
    
    # 员工过滤
    if filter_employee:
        emp_query += ' AND id = ?'
        emp_params.append(filter_employee)
    
    # 状态过滤
    if filter_status:
        emp_query += ' AND status = ?'
        emp_params.append(filter_status)
    
    emp_query += ' ORDER BY employee_no'
    employees = query_db(emp_query, emp_params)
    
    # 计算或获取薪资
    salary_list = []
    for emp in employees:
        salary_data = get_or_calculate_salary(emp['id'], year_month)
        salary_list.append({
            'employee_id': emp['id'],
            'employee_no': emp['employee_no'],
            'name': emp['name'],
            'status': emp['status'],
            'team': emp['team'],
            'base_salary': salary_data['base_salary'],
            'attendance_bonus': salary_data['attendance_bonus'],
            'performance_bonus': salary_data['performance_bonus'],
            'commission': salary_data['commission'],
            'total_salary': salary_data['total_salary'],
            'calculation_detail': salary_data.get('calculation_detail', '')
        })
    
    # 统计
    total_salary = sum(s['total_salary'] for s in salary_list)
    total_base = sum(s['base_salary'] for s in salary_list)
    total_commission = sum(s['commission'] for s in salary_list)
    
    # 获取所有员工（用于筛选）
    all_emp_query = '''
        SELECT id, employee_no, name, team, status 
        FROM employees 
        WHERE is_active = 1
    '''
    all_emp_params = []
    if team:
        all_emp_query += ' AND team = ?'
        all_emp_params.append(team)
    all_emp_query += ' ORDER BY employee_no'
    all_employees_raw = query_db(all_emp_query, all_emp_params)
    
    # 转换为字典列表（用于JSON序列化）
    all_employees = [dict(emp) for emp in all_employees_raw] if all_employees_raw else []
    
    return render_template('admin/salary.html',
                         salary_list=salary_list,
                         year_month=year_month,
                         filter_employee=filter_employee,
                         filter_team=filter_team,
                         filter_status=filter_status,
                         all_employees=all_employees,
                         total_salary=total_salary,
                         total_base=total_base,
                         total_commission=total_commission,
                         user=user)


# ==================== 收入成本分析 ====================

@bp.route('/revenue_cost')
@login_required
@role_required('manager', 'admin')
def revenue_cost():
    """收入成本分析"""
    user = get_current_user()
    team = get_user_team(user)
    
    dimension = request.args.get('dimension', 'monthly')  # daily, monthly, yearly
    date_param = request.args.get('date', datetime.now().date().strftime('%Y-%m-%d'))
    
    # 解析日期
    try:
        target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
    except:
        target_date = datetime.now().date()
    
    data_list = []
    
    if dimension == 'daily':
        # 最近30天
        for i in range(29, -1, -1):
            date = target_date - timedelta(days=i)
            day_data = calculate_daily_revenue_cost(date, team)
            data_list.append(day_data)
    
    elif dimension == 'monthly':
        # 最近12个月
        for i in range(11, -1, -1):
            month_date = target_date - timedelta(days=30*i)
            year_month = month_date.strftime('%Y-%m')
            month_data = calculate_monthly_revenue_cost(year_month, team)
            data_list.append(month_data)
    
    elif dimension == 'yearly':
        # 最近3年
        current_year = target_date.year
        for year in range(current_year-2, current_year+1):
            year_data = calculate_yearly_revenue_cost(year, team)
            data_list.append(year_data)
    
    return render_template('admin/revenue_cost.html',
                         data_list=data_list,
                         dimension=dimension,
                         date_param=date_param,
                         user=user)


def calculate_daily_revenue_cost(date, team=None):
    """计算单日收入成本"""
    date_str = date.strftime('%Y-%m-%d')
    
    query = '''
        SELECT SUM(p.orders_count) as orders, SUM(p.commission) as commission
        FROM performance p
        JOIN employees e ON p.employee_id = e.id
        WHERE p.work_date = ?
    '''
    params = [date_str]
    
    if team:
        query += ' AND e.team = ?'
        params.append(team)
    
    result = query_db(query, params, one=True)
    
    orders = result['orders'] or 0
    revenue = orders * Config.REVENUE_PER_ORDER
    cost = result['commission'] or 0  # 简化：仅计提成作为成本
    profit = revenue - cost
    
    return {
        'period': date.strftime('%Y-%m-%d'),
        'orders': orders,
        'revenue': revenue,
        'cost': cost,
        'profit': profit,
        'margin': (profit / revenue * 100) if revenue > 0 else 0
    }


def calculate_monthly_revenue_cost(year_month, team=None):
    """计算月度收入成本"""
    query = '''
        SELECT SUM(p.orders_count) as orders, SUM(p.commission) as commission
        FROM performance p
        JOIN employees e ON p.employee_id = e.id
        WHERE strftime('%Y-%m', p.work_date) = ?
    '''
    params = [year_month]
    
    if team:
        query += ' AND e.team = ?'
        params.append(team)
    
    result = query_db(query, params, one=True)
    
    orders = result['orders'] or 0
    revenue = orders * Config.REVENUE_PER_ORDER
    cost = result['commission'] or 0
    profit = revenue - cost
    
    return {
        'period': year_month,
        'orders': orders,
        'revenue': revenue,
        'cost': cost,
        'profit': profit,
        'margin': (profit / revenue * 100) if revenue > 0 else 0
    }


def calculate_yearly_revenue_cost(year, team=None):
    """计算年度收入成本"""
    query = '''
        SELECT SUM(p.orders_count) as orders, SUM(p.commission) as commission
        FROM performance p
        JOIN employees e ON p.employee_id = e.id
        WHERE strftime('%Y', p.work_date) = ?
    '''
    params = [str(year)]
    
    if team:
        query += ' AND e.team = ?'
        params.append(team)
    
    result = query_db(query, params, one=True)
    
    orders = result['orders'] or 0
    revenue = orders * Config.REVENUE_PER_ORDER
    cost = result['commission'] or 0
    profit = revenue - cost
    
    return {
        'period': str(year),
        'orders': orders,
        'revenue': revenue,
        'cost': cost,
        'profit': profit,
        'margin': (profit / revenue * 100) if revenue > 0 else 0
    }


# ==================== 定制中心 ====================

@bp.route('/customize')
@login_required
@role_required('manager', 'admin')
def customize():
    """定制中心：管理看板配置和筛选方案"""
    user = get_current_user()
    
    # 获取用户的看板配置
    dashboard_configs = query_db(
        'SELECT * FROM dashboard_configs WHERE user_id = ? ORDER BY updated_at DESC',
        (user['id'],)
    )
    
    # 获取用户的筛选方案
    filter_schemes = query_db(
        'SELECT * FROM filter_schemes WHERE user_id = ? ORDER BY created_at DESC',
        (user['id'],)
    )
    
    return render_template('admin/customize.html',
                         dashboard_configs=dashboard_configs,
                         filter_schemes=filter_schemes,
                         user=user)


# ==================== 团队管理（仅 admin）====================

@bp.route('/teams')
@login_required
@role_required('admin')
def teams():
    """团队管理"""
    teams = query_db('SELECT * FROM teams ORDER BY team_name')
    
    # 统计每个团队的人数
    team_stats = []
    for team in teams:
        count = query_db(
            'SELECT COUNT(*) as count FROM employees WHERE team = ? AND is_active = 1',
            (team['team_name'],),
            one=True
        )
        team_stats.append({
            'team': dict(team),
            'employee_count': count['count']
        })
    
    return render_template('admin/teams.html',
                         team_stats=team_stats,
                         user=get_current_user())


@bp.route('/team/add', methods=['POST'])
@login_required
@role_required('admin')
def team_add():
    """添加团队"""
    team_name = request.form.get('team_name', '').strip()
    team_leader = request.form.get('team_leader', '').strip()
    description = request.form.get('description', '').strip()
    
    if not team_name:
        return jsonify({'success': False, 'message': '请输入团队名称'})
    
    # 检查重复
    existing = query_db('SELECT id FROM teams WHERE team_name = ?', (team_name,), one=True)
    if existing:
        return jsonify({'success': False, 'message': '团队名称已存在'})
    
    try:
        execute_db(
            'INSERT INTO teams (team_name, team_leader, description) VALUES (?, ?, ?)',
            (team_name, team_leader, description)
        )
        return jsonify({'success': True, 'message': '团队已添加'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})


@bp.route('/team/<int:team_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def team_delete(team_id):
    """删除团队"""
    # 检查是否有在职员工
    team = query_db('SELECT team_name FROM teams WHERE id = ?', (team_id,), one=True)
    if not team:
        return jsonify({'success': False, 'message': '团队不存在'})
    
    count = query_db(
        'SELECT COUNT(*) as count FROM employees WHERE team = ? AND is_active = 1',
        (team['team_name'],),
        one=True
    )
    
    if count['count'] > 0:
        return jsonify({'success': False, 'message': f'该团队还有{count["count"]}名在职员工，无法删除'})
    
    try:
        execute_db('DELETE FROM teams WHERE id = ?', (team_id,))
        return jsonify({'success': True, 'message': '团队已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})


# ==================== 管理员账号管理（仅 admin）====================

@bp.route('/managers')
@login_required
@role_required('admin')
def managers():
    """管理员账号管理"""
    managers = query_db(
        "SELECT id, username, role, employee_id, created_at FROM users WHERE role IN ('manager', 'admin') ORDER BY created_at"
    )
    
    return render_template('admin/managers.html',
                         managers=managers,
                         user=get_current_user())


@bp.route('/manager/add', methods=['POST'])
@login_required
@role_required('admin')
def manager_add():
    """添加管理员账号"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'manager')
    
    if not username or not password:
        return jsonify({'success': False, 'message': '请填写完整信息'})
    
    if role not in ['manager', 'admin']:
        return jsonify({'success': False, 'message': '角色无效'})
    
    # 检查重复
    existing = query_db('SELECT id FROM users WHERE username = ?', (username,), one=True)
    if existing:
        return jsonify({'success': False, 'message': '用户名已存在'})
    
    try:
        hashed_pwd = hash_password(password)
        execute_db(
            'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
            (username, hashed_pwd, role)
        )
        return jsonify({'success': True, 'message': '管理员账号已创建'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'创建失败: {str(e)}'})


@bp.route('/manager/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def manager_delete(user_id):
    """删除管理员账号"""
    current_user = get_current_user()
    
    # 不能删除自己
    if user_id == current_user['id']:
        return jsonify({'success': False, 'message': '不能删除自己的账号'})
    
    try:
        execute_db('DELETE FROM users WHERE id = ?', (user_id,))
        return jsonify({'success': True, 'message': '账号已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

