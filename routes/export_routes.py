"""
导出功能路由
"""
from flask import Blueprint, request, send_file
from datetime import datetime
from core.auth import login_required, role_required, get_current_user, get_user_team
from core.database import query_db
from core.export import (
    export_employees_to_excel,
    export_performance_to_excel,
    export_salary_to_excel,
    generate_salary_pdf
)
from core.salary_engine import get_or_calculate_salary

bp = Blueprint('export', __name__, url_prefix='/export')


@bp.route('/employees/excel')
@login_required
@role_required('manager', 'admin')
def export_employees_excel():
    """导出员工数据为 Excel"""
    user = get_current_user()
    team = get_user_team(user)
    
    # 构建查询
    query = 'SELECT * FROM employees WHERE is_active = 1'
    params = []
    
    if team:
        query += ' AND team = ?'
        params.append(team)
    
    query += ' ORDER BY employee_no'
    
    employees = query_db(query, params)
    
    # 生成 Excel
    excel_file = export_employees_to_excel(employees)
    
    filename = f"员工数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@bp.route('/performance/excel')
@login_required
@role_required('manager', 'admin')
def export_performance_excel():
    """导出业绩数据为 Excel"""
    user = get_current_user()
    team = get_user_team(user)
    
    # 获取筛选参数
    filter_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # 构建查询
    query = '''
        SELECT p.*, e.employee_no, e.name, e.team, e.status
        FROM performance p
        JOIN employees e ON p.employee_id = e.id
        WHERE p.work_date = ?
    '''
    params = [filter_date]
    
    if team:
        query += ' AND e.team = ?'
        params.append(team)
    
    query += ' ORDER BY p.orders_count DESC'
    
    performance_list = query_db(query, params)
    
    # 生成 Excel
    excel_file = export_performance_to_excel(performance_list)
    
    filename = f"业绩数据_{filter_date}.xlsx"
    
    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@bp.route('/salary/excel')
@login_required
@role_required('manager', 'admin')
def export_salary_excel():
    """导出薪资数据为 Excel"""
    user = get_current_user()
    team = get_user_team(user)
    
    year_month = request.args.get('year_month', datetime.now().strftime('%Y-%m'))
    
    # 获取员工列表
    query = 'SELECT id, employee_no, name, status, team FROM employees WHERE is_active = 1'
    params = []
    
    if team:
        query += ' AND team = ?'
        params.append(team)
    
    query += ' ORDER BY employee_no'
    employees = query_db(query, params)
    
    # 计算薪资
    salary_list = []
    for emp in employees:
        salary_data = get_or_calculate_salary(emp['id'], year_month)
        salary_list.append({
            'employee_no': emp['employee_no'],
            'name': emp['name'],
            'team': emp['team'],
            'status': emp['status'],
            'base_salary': salary_data['base_salary'],
            'attendance_bonus': salary_data['attendance_bonus'],
            'performance_bonus': salary_data['performance_bonus'],
            'commission': salary_data['commission'],
            'total_salary': salary_data['total_salary']
        })
    
    # 生成 Excel
    excel_file = export_salary_to_excel(salary_list, year_month)
    
    filename = f"薪资数据_{year_month}.xlsx"
    
    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@bp.route('/salary/pdf/<int:employee_id>')
@login_required
def export_salary_pdf(employee_id):
    """导出个人薪资单为 PDF (P2-10增强)"""
    user = get_current_user()
    
    # 权限检查
    if user['role'] == 'employee' and user['employee_id'] != employee_id:
        return '无权访问', 403
    
    year_month = request.args.get('year_month', datetime.now().strftime('%Y-%m'))
    
    # P2-10: 获取密码保护参数（可选）
    password = request.args.get('password', None)  # 可以从查询参数获取
    add_watermark = request.args.get('watermark', 'true').lower() == 'true'  # 默认添加水印
    
    # 获取员工信息
    employee = query_db(
        'SELECT employee_no, name, team, status FROM employees WHERE id = ?',
        (employee_id,),
        one=True
    )
    
    if not employee:
        return '员工不存在', 404
    
    # 获取薪资数据
    salary_data = get_or_calculate_salary(employee_id, year_month)
    
    # 格式化状态
    status_map = {'trainee': '培训期', 'C': 'C级', 'B': 'B级', 'A': 'A级', 'eliminated': '已淘汰'}
    employee_data = {
        'employee_no': employee['employee_no'],
        'name': employee['name'],
        'team': employee['team'],
        'status': status_map.get(employee['status'], employee['status'])
    }
    
    # 生成 PDF (P2-10: 支持密码保护和水印)
    pdf_file = generate_salary_pdf(
        employee_data, 
        salary_data, 
        year_month,
        password=password,
        add_watermark=add_watermark
    )
    
    filename = f"薪资单_{employee['name']}_{year_month}.pdf"
    
    return send_file(
        pdf_file,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )



