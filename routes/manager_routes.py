#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
经理工作台路由
包括：培训考核、晋级审批、保级管理、工资查看
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from core.auth import login_required, role_required
from core.database import query_db, get_db
from core.promotion_engine import (
    trigger_promotion_confirmation,
    approve_promotion,
    reject_promotion,
    check_trainee_to_c_eligible,
    check_c_to_b_eligible,
    check_b_to_a_eligible
)
from core.challenge_engine import (
    trigger_demotion_alert,
    make_challenge_decision,
    check_challenge_completion,
    finalize_challenge
)
from core.audit import get_operator_logs
from datetime import datetime, date

bp = Blueprint('manager', __name__, url_prefix='/manager')


@bp.route('/api/pending_count')
@login_required
@role_required('manager', 'admin')
def api_pending_count():
    """API: 获取待审批数量"""
    user_id = session.get('user_id')
    role = session.get('role')
    
    # 获取经理的团队
    team = None
    if role == 'manager':
        manager_emp = query_db(
            'SELECT team FROM employees WHERE id IN (SELECT employee_id FROM users WHERE id = ?)',
            [user_id],
            one=True
        )
        if manager_emp:
            team = manager_emp['team']
    
    # 统计待审批的晋级（安全查询，表可能不存在）
    try:
        if team:
            pending_promotions = query_db(
                '''SELECT COUNT(*) as count FROM promotion_confirmations pc
                   JOIN employees e ON pc.employee_id = e.id
                   WHERE pc.status = 'pending' AND e.team = ?''',
                [team],
                one=True
            )['count']
        else:
            pending_promotions = query_db(
                'SELECT COUNT(*) as count FROM promotion_confirmations WHERE status = "pending"',
                one=True
            )['count']
    except:
        pending_promotions = 0
    
    # 统计待处理的保级挑战（安全查询，表可能不存在）
    try:
        if team:
            pending_challenges = query_db(
                '''SELECT COUNT(*) as count FROM demotion_challenges dc
                   JOIN employees e ON dc.employee_id = e.id
                   WHERE dc.decision_type IS NULL AND e.team = ?''',
                [team],
                one=True
            )['count']
        else:
            pending_challenges = query_db(
                'SELECT COUNT(*) as count FROM demotion_challenges WHERE decision_type IS NULL',
                one=True
            )['count']
    except:
        pending_challenges = 0
    
    return jsonify({
        'success': True,
        'promotions': pending_promotions,
        'challenges': pending_challenges,
        'total': pending_promotions + pending_challenges
    })


# ==================== 培训考核 ====================

@bp.route('/training_assessments')
@login_required
@role_required('manager', 'admin')
def training_assessments():
    """培训考核管理页面"""
    # 获取当前经理的团队
    manager_id = session.get('user_id')
    manager_emp = query_db(
        'SELECT team FROM employees WHERE id IN (SELECT employee_id FROM users WHERE id = ?)',
        [manager_id],
        one=True
    )
    
    team_filter = manager_emp['team'] if manager_emp else None
    
    # 获取培训期员工
    if team_filter and session.get('role') == 'manager':
        trainees = query_db('''
            SELECT * FROM employees
            WHERE status = 'trainee'
            AND is_active = 1
            AND team = ?
            ORDER BY join_date DESC
        ''', [team_filter])
    else:
        trainees = query_db('''
            SELECT * FROM employees
            WHERE status = 'trainee'
            AND is_active = 1
            ORDER BY join_date DESC
        ''')
    
    # 获取考核记录
    assessments = query_db('''
        SELECT 
            ta.*,
            e.employee_no,
            e.team
        FROM training_assessments ta
        JOIN employees e ON ta.employee_id = e.id
        ORDER BY ta.assessment_date DESC
        LIMIT 50
    ''')
    
    return render_template('manager/training_assessments.html',
                         trainees=trainees,
                         assessments=assessments,
                         now=datetime.now())


@bp.route('/training_assessments/record', methods=['POST'])
@login_required
@role_required('manager', 'admin')
def record_assessment():
    """录入培训考核结果"""
    employee_id = request.form.get('employee_id')
    script_result = request.form.get('script_result')
    mock_result = request.form.get('mock_result')
    notes = request.form.get('notes', '')
    
    if not employee_id or not script_result or not mock_result:
        flash('请填写完整信息', 'error')
        return redirect(url_for('manager.training_assessments'))
    
    both_passed = 1 if (script_result == 'passed' and mock_result == 'passed') else 0
    
    employee = query_db('SELECT * FROM employees WHERE id = ?', [employee_id], one=True)
    if not employee:
        flash('员工不存在', 'error')
        return redirect(url_for('manager.training_assessments'))
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        INSERT INTO training_assessments (
            employee_id, employee_no, employee_name,
            assessment_date,
            script_test_result, mock_order_result, both_passed,
            recorded_by, recorder_name, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        employee_id, employee['employee_no'], employee['name'],
        date.today(),
        script_result, mock_result, both_passed,
        session.get('user_id'), session.get('username'), notes
    ))
    
    db.commit()
    
    # 记录日志
    from core.audit import log_training_assessment
    log_training_assessment(employee_id, employee['name'], both_passed, notes)
    
    flash(f'考核结果已录入：{"通过" if both_passed else "未通过"}', 'success')
    return redirect(url_for('manager.training_assessments'))


# ==================== 晋级确认 ====================

@bp.route('/promotions')
@login_required
@role_required('manager', 'admin')
def promotions():
    """晋级确认管理页面"""
    # 获取当前经理的团队
    manager_id = session.get('user_id')
    manager_emp = query_db(
        'SELECT team FROM employees WHERE id IN (SELECT employee_id FROM users WHERE id = ?)',
        [manager_id],
        one=True
    )
    
    team_filter = manager_emp['team'] if manager_emp else None
    
    # 获取待审批的晋级申请
    if team_filter and session.get('role') == 'manager':
        pending_promotions = query_db('''
            SELECT 
                pc.*,
                e.team
            FROM promotion_confirmations pc
            JOIN employees e ON pc.employee_id = e.id
            WHERE pc.status = 'pending'
            AND e.team = ?
            ORDER BY pc.trigger_date ASC
        ''', [team_filter])
    else:
        pending_promotions = query_db('''
            SELECT 
                pc.*,
                e.team
            FROM promotion_confirmations pc
            JOIN employees e ON pc.employee_id = e.id
            WHERE pc.status = 'pending'
            ORDER BY pc.trigger_date ASC
        ''')
    
    # 获取历史记录
    if team_filter and session.get('role') == 'manager':
        history_promotions = query_db('''
            SELECT 
                pc.*,
                e.team
            FROM promotion_confirmations pc
            JOIN employees e ON pc.employee_id = e.id
            WHERE pc.status != 'pending'
            AND e.team = ?
            ORDER BY pc.approved_at DESC
            LIMIT 30
        ''', [team_filter])
    else:
        history_promotions = query_db('''
            SELECT 
                pc.*,
                e.team
            FROM promotion_confirmations pc
            JOIN employees e ON pc.employee_id = e.id
            WHERE pc.status != 'pending'
            ORDER BY pc.approved_at DESC
            LIMIT 30
        ''')
    
    return render_template('manager/promotions.html',
                         pending_promotions=pending_promotions,
                         history_promotions=history_promotions)


@bp.route('/promotions/<int:promotion_id>/approve', methods=['POST'])
@login_required
@role_required('manager', 'admin')
def approve_promotion_action(promotion_id):
    """批准晋级"""
    result = approve_promotion(
        promotion_id,
        session.get('user_id'),
        session.get('username'),
        session.get('role')
    )
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('manager.promotions'))


@bp.route('/promotions/<int:promotion_id>/reject', methods=['POST'])
@login_required
@role_required('manager', 'admin')
def reject_promotion_action(promotion_id):
    """驳回晋级"""
    reason = request.form.get('reason', '')
    
    if not reason:
        flash('请填写驳回原因', 'error')
        return redirect(url_for('manager.promotions'))
    
    result = reject_promotion(
        promotion_id,
        session.get('user_id'),
        session.get('username'),
        session.get('role'),
        reason
    )
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('manager.promotions'))


# ==================== 保级挑战 ====================

@bp.route('/challenges')
@login_required
@role_required('manager', 'admin')
def challenges():
    """保级挑战管理页面"""
    # 获取当前经理的团队
    manager_id = session.get('user_id')
    manager_emp = query_db(
        'SELECT team FROM employees WHERE id IN (SELECT employee_id FROM users WHERE id = ?)',
        [manager_id],
        one=True
    )
    
    team_filter = manager_emp['team'] if manager_emp else None
    
    # 获取待处理的降级预警
    if team_filter and session.get('role') == 'manager':
        pending_challenges = query_db('''
            SELECT 
                dc.*,
                e.team
            FROM demotion_challenges dc
            JOIN employees e ON dc.employee_id = e.id
            WHERE dc.decision = 'pending'
            AND e.team = ?
            ORDER BY dc.trigger_date ASC
        ''', [team_filter])
    else:
        pending_challenges = query_db('''
            SELECT 
                dc.*,
                e.team
            FROM demotion_challenges dc
            JOIN employees e ON dc.employee_id = e.id
            WHERE dc.decision = 'pending'
            ORDER BY dc.trigger_date ASC
        ''')
    
    # 获取进行中的挑战
    if team_filter and session.get('role') == 'manager':
        ongoing_challenges = query_db('''
            SELECT 
                dc.*,
                e.team
            FROM demotion_challenges dc
            JOIN employees e ON dc.employee_id = e.id
            WHERE dc.decision = 'challenge'
            AND dc.challenge_result = 'ongoing'
            AND e.team = ?
            ORDER BY dc.challenge_start_date ASC
        ''', [team_filter])
    else:
        ongoing_challenges = query_db('''
            SELECT 
                dc.*,
                e.team
            FROM demotion_challenges dc
            JOIN employees e ON dc.employee_id = e.id
            WHERE dc.decision = 'challenge'
            AND dc.challenge_result = 'ongoing'
            ORDER BY dc.challenge_start_date ASC
        ''')
    
    # 获取历史记录
    if team_filter and session.get('role') == 'manager':
        history_challenges = query_db('''
            SELECT 
                dc.*,
                e.team
            FROM demotion_challenges dc
            JOIN employees e ON dc.employee_id = e.id
            WHERE dc.decision != 'pending'
            AND dc.challenge_result != 'ongoing'
            AND e.team = ?
            ORDER BY dc.decision_at DESC
            LIMIT 30
        ''', [team_filter])
    else:
        history_challenges = query_db('''
            SELECT 
                dc.*,
                e.team
            FROM demotion_challenges dc
            JOIN employees e ON dc.employee_id = e.id
            WHERE dc.decision != 'pending'
            AND dc.challenge_result != 'ongoing'
            ORDER BY dc.decision_at DESC
            LIMIT 30
        ''')
    
    return render_template('manager/challenges.html',
                         pending_challenges=pending_challenges,
                         ongoing_challenges=ongoing_challenges,
                         history_challenges=history_challenges)


@bp.route('/challenges/<int:challenge_id>/decide', methods=['POST'])
@login_required
@role_required('manager', 'admin')
def decide_challenge(challenge_id):
    """做出保级挑战决策"""
    decision = request.form.get('decision')  # downgrade/challenge/cancelled
    reason = request.form.get('reason', '')
    
    if not decision:
        flash('请选择处理方式', 'error')
        return redirect(url_for('manager.challenges'))
    
    result = make_challenge_decision(
        challenge_id,
        decision,
        session.get('user_id'),
        session.get('username'),
        reason
    )
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('manager.challenges'))


@bp.route('/challenges/<int:challenge_id>/finalize', methods=['POST'])
@login_required
@role_required('manager', 'admin')
def finalize_challenge_action(challenge_id):
    """完成保级挑战（确认结果）"""
    result = finalize_challenge(
        challenge_id,
        session.get('user_id'),
        session.get('username')
    )
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('manager.challenges'))


# ==================== 工资查看 ====================

@bp.route('/payroll')
@login_required
@role_required('manager', 'admin')
def payroll():
    """经理查看本团队工资"""
    # 获取当前经理的团队
    manager_id = session.get('user_id')
    manager_emp = query_db(
        'SELECT team FROM employees WHERE id IN (SELECT employee_id FROM users WHERE id = ?)',
        [manager_id],
        one=True
    )
    
    if not manager_emp and session.get('role') == 'manager':
        flash('未找到您的团队信息', 'error')
        return redirect(url_for('admin.dashboard'))
    
    team = manager_emp['team'] if manager_emp else None
    
    # 获取月份参数
    year_month = request.args.get('year_month')
    if not year_month:
        year_month = date.today().strftime('%Y-%m')
    
    # 获取本团队的工资单
    if team and session.get('role') == 'manager':
        payrolls = query_db('''
            SELECT * FROM payroll_records
            WHERE year_month = ?
            AND team = ?
            AND is_archived = 0
            ORDER BY employee_no
        ''', [year_month, team])
    else:
        payrolls = query_db('''
            SELECT * FROM payroll_records
            WHERE year_month = ?
            AND is_archived = 0
            ORDER BY team, employee_no
        ''', [year_month])
    
    return render_template('manager/payroll.html',
                         payrolls=payrolls,
                         year_month=year_month,
                         team=team)


# ==================== 操作日志 ====================

@bp.route('/logs')
@login_required
@role_required('manager', 'admin')
def logs():
    """查看操作日志（支持筛选和分页）"""
    from core.audit import get_filtered_logs
    
    # 获取筛选参数
    operation_type = request.args.get('operation_type', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    search_keyword = request.args.get('search', '').strip()
    operator_id_param = request.args.get('operator_id', '').strip()
    
    # 获取分页参数
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    
    # 确定当前角色
    current_role = session.get('role')
    is_admin = (current_role == 'admin')
    user_id = session.get('user_id')
    
    # 经理只能看自己的操作，管理员可以选择操作人筛选
    operator_id = None
    if not is_admin:
        operator_id = user_id
    elif operator_id_param:
        operator_id = int(operator_id_param)
    
    # 调用筛选函数
    result = get_filtered_logs(
        operator_id=operator_id,
        operation_type=operation_type if operation_type else None,
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
        search_keyword=search_keyword if search_keyword else None,
        page=page,
        per_page=per_page,
        is_admin=is_admin
    )
    
    # 传递筛选参数给模板（用于保持筛选状态）
    current_filters = {
        'operation_type': operation_type,
        'start_date': start_date,
        'end_date': end_date,
        'search': search_keyword,
        'operator_id': operator_id_param,
        'per_page': per_page
    }
    
    return render_template('manager/logs.html',
                         logs=result['logs'],
                         pagination=result['pagination'],
                         filters=result['filters'],
                         current_filters=current_filters,
                         current_role=current_role,
                         is_admin=is_admin)


@bp.route('/logs/export')
@login_required
@role_required('manager', 'admin')
def logs_export():
    """导出操作日志为CSV"""
    from core.audit import get_filtered_logs
    import csv
    from io import StringIO
    from flask import make_response
    
    # 获取筛选参数（与logs路由相同）
    operation_type = request.args.get('operation_type', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    search_keyword = request.args.get('search', '').strip()
    operator_id_param = request.args.get('operator_id', '').strip()
    
    current_role = session.get('role')
    is_admin = (current_role == 'admin')
    user_id = session.get('user_id')
    
    operator_id = None
    if not is_admin:
        operator_id = user_id
    elif operator_id_param:
        operator_id = int(operator_id_param)
    
    # 获取所有符合条件的日志（不分页）
    result = get_filtered_logs(
        operator_id=operator_id,
        operation_type=operation_type if operation_type else None,
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
        search_keyword=search_keyword if search_keyword else None,
        page=1,
        per_page=10000,  # 导出最多10000条
        is_admin=is_admin
    )
    
    # 创建CSV
    si = StringIO()
    writer = csv.writer(si)
    
    # 写入表头
    headers = ['时间', '操作类型', '操作描述', '操作人', '目标员工', '详情']
    writer.writerow(headers)
    
    # 写入数据
    for log in result['logs']:
        row = [
            log['created_at_formatted'],
            log['operation_type_label'],
            log['description'],
            log['operator_name'],
            log['target_employee_name'] or '-',
            log['notes'] or '-'
        ]
        writer.writerow(row)
    
    # 创建响应
    output = si.getvalue()
    si.close()
    
    response = make_response(output)
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
    response.headers['Content-Disposition'] = f'attachment; filename=operation_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response


# ==================== API 接口 ====================

@bp.route('/api/check_promotion/<int:employee_id>')
@login_required
@role_required('manager', 'admin')
def api_check_promotion(employee_id):
    """检查员工晋级资格（API）"""
    employee = query_db('SELECT status FROM employees WHERE id = ?', [employee_id], one=True)
    
    if not employee:
        return jsonify({'error': '员工不存在'}), 404
    
    status = employee['status']
    
    if status == 'trainee':
        result = check_trainee_to_c_eligible(employee_id)
    elif status == 'C':
        result = check_c_to_b_eligible(employee_id)
    elif status == 'B':
        result = check_b_to_a_eligible(employee_id)
    else:
        return jsonify({'error': f'状态{status}无晋级路径'}), 400
    
    return jsonify(result)


@bp.route('/api/check_challenge/<int:challenge_id>')
@login_required
@role_required('manager', 'admin')
def api_check_challenge(challenge_id):
    """检查保级挑战进度（API）"""
    result = check_challenge_completion(challenge_id)
    return jsonify(result)


