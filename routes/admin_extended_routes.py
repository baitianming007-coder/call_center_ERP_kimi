#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员扩展路由
包括：工作日配置、工资管理、年度归档
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from core.auth import login_required, role_required
from core.database import query_db, get_db
from core.workday import is_workday, count_workdays_between
from core.payroll_engine import (
    generate_payroll_for_month,
    adjust_payroll,
    archive_payroll_year,
    get_archive_summary
)
from core.audit import log_calendar_change
from datetime import datetime, date, timedelta

bp = Blueprint('admin_ext', __name__, url_prefix='/admin')


@bp.route('/api/payroll_preview')
@login_required
@role_required('admin')
def payroll_preview():
    """API: 工资单预览"""
    year_month = request.args.get('year_month')
    
    if not year_month:
        return jsonify({'success': False, 'message': '缺少year_month参数'})
    
    # 获取当月所有在职员工的薪资数据
    employees = query_db(
        'SELECT id, employee_no, name, team, status FROM employees WHERE is_active = 1 ORDER BY employee_no'
    )
    
    if not employees:
        return jsonify({'success': False, 'message': '没有员工数据'})
    
    # 从salary表获取已有的薪资数据（如果有）
    preview_data = []
    total_amount = 0
    commission_total = 0
    
    for emp in employees[:10]:  # 只预览前10条
        # 查询该员工当月的薪资
        salary = query_db(
            'SELECT * FROM salary WHERE employee_id = ? AND year_month = ?',
            (emp['id'], year_month),
            one=True
        )
        
        if salary:
            salary_dict = dict(salary)
        else:
            # 如果没有薪资记录，使用默认值
            salary_dict = {
                'base_salary': 0,
                'attendance_bonus': 0,
                'performance_bonus': 0,
                'commission': 0,
                'total_salary': 0
            }
        
        preview_data.append({
            'employee_no': emp['employee_no'],
            'employee_name': emp['name'],
            'team': emp['team'],
            'status_at_time': emp['status'],
            'base_salary': float(salary_dict.get('base_salary', 0)),
            'attendance_bonus': float(salary_dict.get('attendance_bonus', 0)),
            'performance_bonus': float(salary_dict.get('performance_bonus', 0)),
            'commission': float(salary_dict.get('commission', 0)),
            'total_salary': float(salary_dict.get('total_salary', 0))
        })
        
        total_amount += float(salary_dict.get('total_salary', 0))
        commission_total += float(salary_dict.get('commission', 0))
    
    # 计算全部员工的统计（用于显示）
    all_salary = query_db(
        'SELECT COUNT(*) as count, SUM(total_salary) as total, AVG(total_salary) as avg, SUM(commission) as comm FROM salary WHERE year_month = ?',
        (year_month,),
        one=True
    )
    
    # 如果没有薪资数据，使用员工数量
    if all_salary and all_salary['count'] > 0:
        total_count = all_salary['count']
        total_amount_all = float(all_salary['total'] or 0)
        avg_salary = float(all_salary['avg'] or 0)
        commission_total_all = float(all_salary['comm'] or 0)
    else:
        total_count = len(employees)
        total_amount_all = 0
        avg_salary = 0
        commission_total_all = 0
    
    return jsonify({
        'success': True,
        'preview': preview_data,
        'total_count': total_count,
        'total_amount': total_amount_all,
        'avg_salary': avg_salary,
        'commission_total': commission_total_all
    })


# ==================== 工作日配置 ====================

@bp.route('/work_calendar')
@login_required
@role_required('admin')
def work_calendar():
    """工作日配置管理页面"""
    # 获取年月参数
    year_month = request.args.get('year_month')
    if not year_month:
        year_month = date.today().strftime('%Y-%m')
    
    year, month = map(int, year_month.split('-'))
    
    # 生成当月日历
    import calendar
    cal = calendar.monthcalendar(year, month)
    
    # 获取当月的工作日配置
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    configs = query_db('''
        SELECT * FROM work_calendar
        WHERE calendar_date BETWEEN ? AND ?
    ''', [start_date, end_date])
    
    # 转换为字典方便查询
    config_dict = {c['calendar_date']: c for c in configs} if configs else {}
    
    return render_template('admin/work_calendar.html',
                         calendar_data=cal,
                         year=year,
                         month=month,
                         year_month=year_month,
                         config_dict=config_dict)


@bp.route('/work_calendar/configure', methods=['POST'])
@login_required
@role_required('admin')
def configure_workday():
    """配置工作日"""
    calendar_date = request.form.get('calendar_date')
    is_workday_flag = request.form.get('is_workday')  # '1' or '0'
    day_type = request.form.get('day_type', 'workday')
    notes = request.form.get('notes', '')
    
    if not calendar_date or is_workday_flag is None:
        flash('请填写完整信息', 'error')
        return redirect(url_for('admin_ext.work_calendar'))
    
    db = get_db()
    cursor = db.cursor()
    
    # 检查是否已存在配置
    existing = query_db(
        'SELECT * FROM work_calendar WHERE calendar_date = ?',
        [calendar_date],
        one=True
    )
    
    if existing:
        # 更新
        cursor.execute('''
            UPDATE work_calendar
            SET is_workday = ?,
                day_type = ?,
                notes = ?,
                configured_by = ?,
                configured_name = ?,
                configured_at = CURRENT_TIMESTAMP
            WHERE calendar_date = ?
        ''', (is_workday_flag, day_type, notes,
              session.get('user_id'), session.get('username'),
              calendar_date))
    else:
        # 插入
        cursor.execute('''
            INSERT INTO work_calendar (
                calendar_date, is_workday, day_type, notes,
                configured_by, configured_name
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (calendar_date, is_workday_flag, day_type, notes,
              session.get('user_id'), session.get('username')))
    
    db.commit()
    
    # 记录日志
    log_calendar_change(
        calendar_date,
        int(is_workday_flag) == 1,
        day_type,
        notes
    )
    
    flash(f'{calendar_date} 已配置为{"工作日" if is_workday_flag == "1" else "假期"}', 'success')
    
    # 返回到当前月份
    year_month = calendar_date[:7]
    return redirect(url_for('admin_ext.work_calendar', year_month=year_month))


@bp.route('/work_calendar/batch_save', methods=['POST'])
@login_required
@role_required('admin')
def batch_save_workdays():
    """批量保存工作日配置（新版API，支持JSON）"""
    from core.performance_recalculator import recalculate_month_performance, get_affected_employees
    
    data = request.get_json()
    dates = data.get('dates', [])  # ['2025-10-01', '2025-10-02', ...]
    is_workday = data.get('is_workday', True)  # True or False
    recalculate = data.get('recalculate_performance', False)
    year_month = data.get('year_month')
    
    if not dates:
        return jsonify({
            'success': False,
            'message': '没有选择任何日期'
        }), 400
    
    db = get_db()
    cursor = db.cursor()
    
    configured_count = 0
    
    # 批量保存配置
    for date_str in dates:
        try:
            # 检查是否已存在
            existing = query_db(
                'SELECT * FROM work_calendar WHERE calendar_date = ?',
                [date_str],
                one=True
            )
            
            is_workday_flag = 1 if is_workday else 0
            
            if existing:
                cursor.execute('''
                    UPDATE work_calendar
                    SET is_workday = ?,
                        day_type = ?,
                        notes = ?,
                        configured_by = ?,
                        configured_name = ?,
                        configured_at = CURRENT_TIMESTAMP
                    WHERE calendar_date = ?
                ''', (is_workday_flag, 'custom', '批量配置',
                      session.get('user_id'), session.get('username'),
                      date_str))
            else:
                cursor.execute('''
                    INSERT INTO work_calendar (
                        calendar_date, is_workday, day_type, notes,
                        configured_by, configured_name
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (date_str, is_workday_flag, 'custom', '批量配置',
                      session.get('user_id'), session.get('username')))
            
            configured_count += 1
            
            # 记录日志
            from core.audit import log_calendar_change
            log_calendar_change(date_str, is_workday, 'custom', '批量配置')
            
        except Exception as e:
            db.rollback()
            return jsonify({
                'success': False,
                'message': f'配置失败: {str(e)}'
            }), 500
    
    db.commit()
    
    # 如果需要重新计算业绩
    affected_employees = 0
    if recalculate and year_month:
        try:
            result = recalculate_month_performance(year_month)
            affected_employees = result.get('recalculated_count', 0)
        except Exception as e:
            # 业绩重算失败不影响配置保存
            pass
    
    return jsonify({
        'success': True,
        'affected_dates': configured_count,
        'affected_employees': affected_employees,
        'message': f'成功配置 {configured_count} 天'
    })


@bp.route('/work_calendar/recalculate_performance', methods=['POST'])
@login_required
@role_required('admin')
def recalculate_performance():
    """重新计算受影响月份的员工业绩"""
    from core.performance_recalculator import recalculate_month_performance
    
    data = request.get_json()
    year_month = data.get('year_month')
    
    if not year_month:
        return jsonify({
            'success': False,
            'message': '请指定年月'
        }), 400
    
    try:
        result = recalculate_month_performance(year_month)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'重算失败: {str(e)}'
        }), 500


@bp.route('/work_calendar/batch', methods=['POST'])
@login_required
@role_required('admin')
def batch_configure_workdays():
    """批量配置工作日"""
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    is_workday_flag = request.form.get('is_workday')
    day_type = request.form.get('day_type', 'workday')
    
    if not start_date or not end_date or is_workday_flag is None:
        flash('请填写完整信息', 'error')
        return redirect(url_for('admin_ext.work_calendar'))
    
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    if start > end:
        flash('开始日期不能晚于结束日期', 'error')
        return redirect(url_for('admin_ext.work_calendar'))
    
    db = get_db()
    cursor = db.cursor()
    
    current = start
    configured_count = 0
    
    while current <= end:
        date_str = current.strftime('%Y-%m-%d')
        
        # 检查是否已存在
        existing = query_db(
            'SELECT * FROM work_calendar WHERE calendar_date = ?',
            [date_str],
            one=True
        )
        
        if existing:
            cursor.execute('''
                UPDATE work_calendar
                SET is_workday = ?,
                    day_type = ?,
                    configured_by = ?,
                    configured_name = ?,
                    configured_at = CURRENT_TIMESTAMP
                WHERE calendar_date = ?
            ''', (is_workday_flag, day_type,
                  session.get('user_id'), session.get('username'),
                  date_str))
        else:
            cursor.execute('''
                INSERT INTO work_calendar (
                    calendar_date, is_workday, day_type,
                    configured_by, configured_name
                ) VALUES (?, ?, ?, ?, ?)
            ''', (date_str, is_workday_flag, day_type,
                  session.get('user_id'), session.get('username')))
        
        configured_count += 1
        current += timedelta(days=1)
    
    db.commit()
    
    flash(f'批量配置成功：{configured_count}天', 'success')
    return redirect(url_for('admin_ext.work_calendar'))


# ==================== 工资管理 ====================

@bp.route('/payroll_management')
@login_required
@role_required('admin')
def payroll_management():
    """工资管理主页"""
    # 获取月份参数
    year_month = request.args.get('year_month')
    if not year_month:
        year_month = date.today().strftime('%Y-%m')
    
    # 获取工资单列表
    payrolls = query_db('''
        SELECT * FROM payroll_records
        WHERE year_month = ?
        AND is_archived = 0
        ORDER BY team, employee_no
    ''', [year_month])
    
    # 统计
    if payrolls:
        total_count = len(payrolls)
        total_amount = sum(p['total_salary'] for p in payrolls)
        status_counts = {}
        for p in payrolls:
            status = p['status']
            status_counts[status] = status_counts.get(status, 0) + 1
    else:
        total_count = 0
        total_amount = 0
        status_counts = {}
    
    return render_template('admin/payroll_management.html',
                         payrolls=payrolls,
                         year_month=year_month,
                         total_count=total_count,
                         total_amount=total_amount,
                         status_counts=status_counts)


@bp.route('/payroll_management/generate', methods=['POST'])
@login_required
@role_required('admin')
def generate_payroll():
    """生成工资单"""
    year_month = request.form.get('year_month')
    overwrite = request.form.get('overwrite') == '1'
    
    if not year_month:
        flash('请选择月份', 'error')
        return redirect(url_for('admin_ext.payroll_management'))
    
    result = generate_payroll_for_month(
        year_month,
        overwrite,
        session.get('user_id'),
        session.get('username')
    )
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('admin_ext.payroll_management', year_month=year_month))


@bp.route('/payroll_management/<int:payroll_id>/adjust', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def adjust_payroll_action(payroll_id):
    """调整工资"""
    adjustment_type = request.form.get('adjustment_type')
    amount = request.form.get('amount')
    reason = request.form.get('reason', '')
    
    if not adjustment_type or not amount or not reason:
        flash('请填写完整信息', 'error')
        return redirect(request.referrer or url_for('admin_ext.payroll_management'))
    
    try:
        amount = float(amount)
    except ValueError:
        flash('金额格式不正确', 'error')
        return redirect(request.referrer or url_for('admin_ext.payroll_management'))
    
    result = adjust_payroll(
        payroll_id,
        adjustment_type,
        amount,
        reason,
        session.get('user_id'),
        session.get('username'),
        session.get('role')
    )
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(request.referrer or url_for('admin_ext.payroll_management'))


# ==================== 年度归档 ====================

@bp.route('/payroll_archive')
@login_required
@role_required('admin')
def payroll_archive():
    """年度归档管理"""
    # 获取所有归档记录
    archives = query_db('''
        SELECT * FROM payroll_archives
        ORDER BY archive_year DESC
    ''')
    
    return render_template('admin/payroll_archive.html', archives=archives)


@bp.route('/payroll_archive/create', methods=['POST'])
@login_required
@role_required('admin')
def create_archive():
    """创建归档"""
    archive_year = request.form.get('archive_year')
    
    if not archive_year:
        flash('请输入归档年份', 'error')
        return redirect(url_for('admin_ext.payroll_archive'))
    
    try:
        archive_year = int(archive_year)
    except ValueError:
        flash('年份格式不正确', 'error')
        return redirect(url_for('admin_ext.payroll_archive'))
    
    result = archive_payroll_year(
        archive_year,
        session.get('user_id'),
        session.get('username')
    )
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('admin_ext.payroll_archive'))


@bp.route('/payroll_archive/<int:year>')
@login_required
@role_required('admin')
def view_archive(year):
    """查看归档详情"""
    archive_data = get_archive_summary(year)
    
    if not archive_data:
        flash(f'{year}年归档不存在', 'error')
        return redirect(url_for('admin_ext.payroll_archive'))
    
    return render_template('admin/payroll_archive_detail.html',
                         archive=archive_data['archive'],
                         monthly_summary=archive_data['monthly_summary'])


# ==================== 银行信息审核 ====================

@bp.route('/bank_verification')
@login_required
@role_required('admin', 'finance')
def bank_verification():
    """银行信息审核页面"""
    # 获取待审核的银行信息
    pending_verifications = query_db('''
        SELECT 
            id, employee_no, name, team,
            bank_account_number, bank_name, bank_branch,
            account_holder_name, bank_info_status, bank_info_notes
        FROM employees
        WHERE bank_info_status = 'pending'
        AND is_active = 1
        ORDER BY employee_no
    ''')
    
    return render_template('admin/bank_verification.html',
                         pending_verifications=pending_verifications)


@bp.route('/bank_verification/<int:employee_id>/verify', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def verify_bank_info(employee_id):
    """审核银行信息"""
    action = request.form.get('action')  # 'approve' or 'reject'
    notes = request.form.get('notes', '')
    
    if action not in ['approve', 'reject']:
        flash('无效的操作', 'error')
        return redirect(url_for('admin_ext.bank_verification'))
    
    db = get_db()
    cursor = db.cursor()
    
    new_status = 'verified' if action == 'approve' else 'rejected'
    
    cursor.execute('''
        UPDATE employees
        SET bank_info_status = ?,
            bank_info_notes = ?,
            bank_verified_by = ?,
            bank_verified_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (new_status, notes, session.get('user_id'), employee_id))
    
    db.commit()
    
    # 记录日志
    from core.audit import log_bank_verification
    employee = query_db('SELECT employee_no, name FROM employees WHERE id = ?', [employee_id], one=True)
    if employee:
        log_bank_verification(employee_id, employee['name'], new_status, notes)
    
    flash(f'银行信息已{"审核通过" if action == "approve" else "审核拒绝"}', 'success')
    return redirect(url_for('admin_ext.bank_verification'))


# ==================== API 接口 ====================

@bp.route('/api/workday/check/<string:check_date>')
@login_required
@role_required('admin', 'manager')
def api_check_workday(check_date):
    """检查是否为工作日（API）"""
    try:
        result = is_workday(check_date)
        return jsonify({
            'date': check_date,
            'is_workday': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/api/workday/count')
@login_required
@role_required('admin', 'manager')
def api_count_workdays():
    """计算工作日数量（API）"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({'error': '缺少参数'}), 400
    
    try:
        count = count_workdays_between(start_date, end_date)
        return jsonify({
            'start_date': start_date,
            'end_date': end_date,
            'workday_count': count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400



