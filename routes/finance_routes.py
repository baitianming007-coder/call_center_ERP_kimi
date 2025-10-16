#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务工作台路由
包括：工资发放管理、银行信息审核、状态标记、批量操作
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from core.auth import login_required, role_required
from core.database import query_db, get_db
from core.payroll_engine import (
    confirm_payroll_for_payment,
    mark_payroll_payment,
    mark_payroll_payment_failed,
    retry_payroll_payment,
    batch_confirm_payrolls
)
from datetime import datetime, date

bp = Blueprint('finance', __name__, url_prefix='/finance')


# ==================== 财务工作台主页 ====================

@bp.route('/dashboard')
@login_required
@role_required('finance')
def dashboard():
    """财务工作台主页"""
    # 获取月份参数
    year_month = request.args.get('year_month')
    if not year_month:
        year_month = date.today().strftime('%Y-%m')
    
    # 统计各状态的工资单数量
    stats = query_db('''
        SELECT 
            status,
            COUNT(*) as count,
            SUM(total_salary) as amount
        FROM payroll_records
        WHERE year_month = ?
        AND is_archived = 0
        GROUP BY status
    ''', [year_month])
    
    status_stats = {s['status']: {'count': s['count'], 'amount': s['amount']} for s in stats} if stats else {}
    
    # 获取待确认的工资单
    pending_payrolls = query_db('''
        SELECT * FROM payroll_records
        WHERE year_month = ?
        AND status = 'pending'
        AND is_archived = 0
        ORDER BY team, employee_no
        LIMIT 100
    ''', [year_month])
    
    # 获取已确认待发放的工资单
    confirmed_payrolls = query_db('''
        SELECT * FROM payroll_records
        WHERE year_month = ?
        AND status = 'confirmed'
        AND is_archived = 0
        ORDER BY team, employee_no
        LIMIT 100
    ''', [year_month])
    
    # 获取发放失败的工资单
    failed_payrolls = query_db('''
        SELECT * FROM payroll_records
        WHERE year_month = ?
        AND status IN ('failed', 'retry')
        AND is_archived = 0
        ORDER BY updated_at DESC
    ''', [year_month])
    
    return render_template('finance/dashboard.html',
                         year_month=year_month,
                         status_stats=status_stats,
                         pending_payrolls=pending_payrolls,
                         confirmed_payrolls=confirmed_payrolls,
                         failed_payrolls=failed_payrolls)


# ==================== 工资确认 ====================

@bp.route('/confirm/<int:payroll_id>', methods=['POST'])
@login_required
@role_required('finance')
def confirm_payroll(payroll_id):
    """确认工资单可发放"""
    result = confirm_payroll_for_payment(
        payroll_id,
        session.get('user_id'),
        session.get('username')
    )
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(request.referrer or url_for('finance.dashboard'))


@bp.route('/batch_confirm', methods=['POST'])
@login_required
@role_required('finance')
def batch_confirm():
    """批量确认工资单"""
    year_month = request.form.get('year_month')
    
    if not year_month:
        flash('请选择月份', 'error')
        return redirect(url_for('finance.dashboard'))
    
    result = batch_confirm_payrolls(
        year_month,
        session.get('user_id'),
        session.get('username')
    )
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('finance.dashboard', year_month=year_month))


# ==================== 工资发放 ====================

@bp.route('/payment/<int:payroll_id>', methods=['GET', 'POST'])
@login_required
@role_required('finance')
def payment(payroll_id):
    """工资发放页面"""
    payroll = query_db(
        'SELECT * FROM payroll_records WHERE id = ?',
        [payroll_id],
        one=True
    )
    
    if not payroll:
        flash('工资单不存在', 'error')
        return redirect(url_for('finance.dashboard'))
    
    # 获取员工银行信息
    employee = query_db('''
        SELECT 
            bank_account_number, bank_name, bank_branch,
            account_holder_name, bank_info_status, name
        FROM employees
        WHERE id = ?
    ''', [payroll['employee_id']], one=True)
    
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        payment_date_str = request.form.get('payment_date')
        payment_reference = request.form.get('payment_reference', '')
        notes = request.form.get('notes', '')
        
        if not payment_method or not payment_date_str:
            flash('请填写完整信息', 'error')
            return render_template('finance/payment.html',
                                 payroll=payroll,
                                 employee=employee)
        
        try:
            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('日期格式不正确', 'error')
            return render_template('finance/payment.html',
                                 payroll=payroll,
                                 employee=employee)
        
        result = mark_payroll_payment(
            payroll_id,
            payment_method,
            payment_date,
            payment_reference,
            session.get('user_id'),
            session.get('username'),
            notes
        )
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('finance.dashboard'))
        else:
            flash(result['message'], 'error')
    
    return render_template('finance/payment.html',
                         payroll=payroll,
                         employee=employee)


@bp.route('/mark_failed/<int:payroll_id>', methods=['POST'])
@login_required
@role_required('finance')
def mark_failed(payroll_id):
    """标记发放失败"""
    failure_reason = request.form.get('failure_reason', '')
    
    if not failure_reason:
        flash('请填写失败原因', 'error')
        return redirect(request.referrer or url_for('finance.dashboard'))
    
    result = mark_payroll_payment_failed(
        payroll_id,
        failure_reason,
        session.get('user_id'),
        session.get('username')
    )
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(request.referrer or url_for('finance.dashboard'))


@bp.route('/retry/<int:payroll_id>', methods=['POST'])
@login_required
@role_required('finance')
def retry_payment(payroll_id):
    """重试发放"""
    result = retry_payroll_payment(payroll_id)
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(request.referrer or url_for('finance.dashboard'))


# ==================== 发放记录查询 ====================

@bp.route('/payment_history')
@login_required
@role_required('finance')
def payment_history():
    """发放历史记录"""
    # 获取月份参数
    year_month = request.args.get('year_month')
    if not year_month:
        year_month = date.today().strftime('%Y-%m')
    
    # 获取状态参数
    status_filter = request.args.get('status', '')
    
    # 构建查询
    if status_filter:
        records = query_db('''
            SELECT * FROM payroll_records
            WHERE year_month = ?
            AND status = ?
            AND is_archived = 0
            ORDER BY payment_date DESC, employee_no
        ''', [year_month, status_filter])
    else:
        records = query_db('''
            SELECT * FROM payroll_records
            WHERE year_month = ?
            AND is_archived = 0
            ORDER BY 
                CASE status
                    WHEN 'pending' THEN 1
                    WHEN 'confirmed' THEN 2
                    WHEN 'paid' THEN 3
                    WHEN 'failed' THEN 4
                    WHEN 'retry' THEN 5
                    ELSE 6
                END,
                employee_no
        ''', [year_month])
    
    return render_template('finance/payment_history.html',
                         records=records,
                         year_month=year_month,
                         status_filter=status_filter)


# ==================== 银行信息审核 ====================

@bp.route('/bank_audit')
@login_required
@role_required('finance')
def bank_audit():
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
    
    # 获取审核历史
    audit_history = query_db('''
        SELECT 
            id, employee_no, name, team,
            bank_account_number, bank_name,
            account_holder_name, bank_info_status,
            bank_info_notes, bank_verified_at
        FROM employees
        WHERE bank_info_status IN ('verified', 'rejected')
        AND is_active = 1
        ORDER BY bank_verified_at DESC
        LIMIT 50
    ''')
    
    return render_template('finance/bank_audit.html',
                         pending_verifications=pending_verifications,
                         audit_history=audit_history)


@bp.route('/bank_audit/<int:employee_id>/verify', methods=['POST'])
@login_required
@role_required('finance')
def verify_bank(employee_id):
    """审核银行信息"""
    action = request.form.get('action')  # 'approve' or 'reject'
    notes = request.form.get('notes', '')
    
    if action not in ['approve', 'reject']:
        flash('无效的操作', 'error')
        return redirect(url_for('finance.bank_audit'))
    
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
    return redirect(url_for('finance.bank_audit'))


@bp.route('/batch_audit_bank', methods=['POST'])
@login_required
@role_required('finance')
def batch_audit_bank():
    """P2-12: 批量审核银行信息"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    employee_ids = data.get('employee_ids', [])
    action = data.get('action')  # 'approve' or 'reject'
    notes = data.get('notes', '')
    
    if not employee_ids:
        return jsonify({'success': False, 'message': '未选择任何员工'}), 400
    
    if action not in ['approve', 'reject']:
        return jsonify({'success': False, 'message': '无效的操作类型'}), 400
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        new_status = 'verified' if action == 'approve' else 'rejected'
        approved_count = 0
        rejected_count = 0
        
        for employee_id in employee_ids:
            # 验证员工存在且有待审核的银行信息
            employee = query_db(
                'SELECT id, employee_no, name, bank_info_status FROM employees WHERE id = ? AND bank_info_status = ?',
                (employee_id, 'pending'),
                one=True
            )
            
            if not employee:
                continue
            
            # 更新银行信息状态
            cursor.execute('''
                UPDATE employees
                SET bank_info_status = ?,
                    bank_info_notes = ?,
                    bank_verified_by = ?,
                    bank_verified_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_status, notes, session.get('user_id'), employee_id))
            
            # 记录日志
            from core.audit import log_bank_verification
            log_bank_verification(employee_id, employee['name'], new_status, notes)
            
            if action == 'approve':
                approved_count += 1
            else:
                rejected_count += 1
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'批量审核完成',
            'approved_count': approved_count,
            'rejected_count': rejected_count
        })
    
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': f'批量审核失败: {str(e)}'}), 500


# ==================== API 接口 ====================

@bp.route('/api/payroll/<int:payroll_id>')
@login_required
@role_required('finance')
def api_get_payroll(payroll_id):
    """获取工资单详情（API）"""
    payroll = query_db(
        'SELECT * FROM payroll_records WHERE id = ?',
        [payroll_id],
        one=True
    )
    
    if not payroll:
        return jsonify({'error': '工资单不存在'}), 404
    
    # 获取调整记录
    from core.payroll_engine import get_payroll_adjustments
    adjustments = get_payroll_adjustments(payroll_id)
    
    return jsonify({
        'payroll': dict(payroll),
        'adjustments': [dict(a) for a in adjustments] if adjustments else []
    })


@bp.route('/api/stats/<string:year_month>')
@login_required
@role_required('finance')
def api_get_stats(year_month):
    """获取月度统计（API）"""
    stats = query_db('''
        SELECT 
            COUNT(*) as total_count,
            SUM(total_salary) as total_amount,
            status,
            COUNT(*) as status_count
        FROM payroll_records
        WHERE year_month = ?
        AND is_archived = 0
        GROUP BY status
    ''', [year_month])
    
    total = query_db('''
        SELECT 
            COUNT(*) as count,
            SUM(total_salary) as amount
        FROM payroll_records
        WHERE year_month = ?
        AND is_archived = 0
    ''', [year_month], one=True)
    
    return jsonify({
        'year_month': year_month,
        'total_count': total['count'] if total else 0,
        'total_amount': total['amount'] if total else 0,
        'status_breakdown': [dict(s) for s in stats] if stats else []
    })



