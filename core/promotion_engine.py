#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
晋级确认引擎
处理员工晋级的触发、审批、确认流程
"""

from datetime import datetime, date, timedelta
from core.database import query_db, get_db
from core.workday import count_workdays_between, get_recent_workdays, get_next_workday
from core.audit import log_promotion_trigger, log_promotion_approval, log_promotion_override
from core.notifications import create_notification


# ==================== 晋级规则配置 ====================

PROMOTION_RULES = {
    'trainee_to_C': {
        'from_status': 'trainee',
        'to_status': 'C',
        'workdays_required': 3,
        'requires_assessment': True,
        'assessment_criteria': 'basic_script_and_mock_order',
        'description': '入职满3个工作日 + 基础话术通关 + 模拟出单考核通过'
    },
    'C_to_B': {
        'from_status': 'C',
        'to_status': 'B',
        'max_workdays': 6,
        'recent_days': 3,
        'min_orders': 3,
        'description': 'C级周期≤6个工作日 且 最近3个工作日出单≥3单'
    },
    'B_to_A': {
        'from_status': 'B',
        'to_status': 'A',
        'max_workdays': 9,
        'recent_days': 6,
        'min_orders': 12,
        'description': 'B级周期≤9个工作日 且 最近6个工作日出单≥12单'
    }
}


# ==================== 晋级检测函数 ====================

def check_trainee_to_c_eligible(employee_id):
    """
    检查培训期→C级晋级资格
    
    Returns:
        dict: {
            'eligible': bool,
            'workdays': int,
            'has_assessment': bool,
            'assessment_passed': bool,
            'reason': str
        }
    """
    # 获取员工信息
    employee = query_db(
        'SELECT * FROM employees WHERE id = ? AND status = ?',
        [employee_id, 'trainee'],
        one=True
    )
    
    if not employee:
        return {'eligible': False, 'reason': '员工不存在或状态不是培训期'}
    
    # 获取状态变更历史（计算在培训期的天数）
    last_change = query_db(
        'SELECT * FROM status_history WHERE employee_id = ? ORDER BY change_date DESC LIMIT 1',
        [employee_id],
        one=True
    )
    
    # 计算工作日数
    if last_change:
        status_start_date = last_change['change_date']
        if isinstance(status_start_date, str):
            status_start_date = datetime.strptime(status_start_date, '%Y-%m-%d').date()
    else:
        # 没有变更历史，使用入职日期
        join_date = employee['join_date']
        if isinstance(join_date, str):
            join_date = datetime.strptime(join_date, '%Y-%m-%d').date()
        status_start_date = join_date
    
    today = date.today()
    workdays = count_workdays_between(status_start_date, today, include_start=True, include_end=True)
    
    # 检查工作日要求
    rule = PROMOTION_RULES['trainee_to_C']
    workdays_met = workdays >= rule['workdays_required']
    
    # 检查培训考核
    assessment = query_db('''
        SELECT * FROM training_assessments
        WHERE employee_id = ?
        AND both_passed = 1
        ORDER BY assessment_date DESC
        LIMIT 1
    ''', [employee_id], one=True)
    
    has_assessment = assessment is not None
    assessment_passed = has_assessment
    
    # 综合判断
    eligible = workdays_met and assessment_passed
    
    reason = ''
    if not workdays_met:
        reason = f'工作日不足（当前{workdays}天，需要{rule["workdays_required"]}天）'
    elif not assessment_passed:
        reason = '未通过培训考核'
    else:
        reason = f'已满足晋级条件（工作{workdays}天，已通过考核）'
    
    return {
        'eligible': eligible,
        'workdays': workdays,
        'has_assessment': has_assessment,
        'assessment_passed': assessment_passed,
        'reason': reason
    }


def check_c_to_b_eligible(employee_id):
    """
    检查C级→B级晋级资格
    
    Returns:
        dict: {
            'eligible': bool,
            'workdays_in_c': int,
            'recent_orders': int,
            'reason': str
        }
    """
    employee = query_db(
        'SELECT * FROM employees WHERE id = ? AND status = ?',
        [employee_id, 'C'],
        one=True
    )
    
    if not employee:
        return {'eligible': False, 'reason': '员工不存在或状态不是C级'}
    
    # 获取C级开始日期
    last_change = query_db(
        'SELECT * FROM status_history WHERE employee_id = ? AND to_status = ? ORDER BY change_date DESC LIMIT 1',
        [employee_id, 'C'],
        one=True
    )
    
    if last_change:
        c_start_date = last_change['change_date']
        if isinstance(c_start_date, str):
            c_start_date = datetime.strptime(c_start_date, '%Y-%m-%d').date()
    else:
        # 没有变更到C级的记录，可能是直接创建的，使用入职日期
        join_date = employee['join_date']
        if isinstance(join_date, str):
            join_date = datetime.strptime(join_date, '%Y-%m-%d').date()
        c_start_date = join_date
    
    today = date.today()
    workdays_in_c = count_workdays_between(c_start_date, today, include_start=True, include_end=True)
    
    # 检查周期要求
    rule = PROMOTION_RULES['C_to_B']
    workdays_met = workdays_in_c <= rule['max_workdays']
    
    # 获取最近N个工作日的出单数
    recent_workdays = get_recent_workdays(today, rule['recent_days'], include_end=True)
    if len(recent_workdays) < rule['recent_days']:
        return {
            'eligible': False,
            'workdays_in_c': workdays_in_c,
            'recent_orders': 0,
            'reason': f'工作日数不足{rule["recent_days"]}天'
        }
    
    # 计算出单数
    date_placeholders = ','.join('?' * len(recent_workdays))
    date_strs = [d.strftime('%Y-%m-%d') for d in recent_workdays]
    
    result = query_db(f'''
        SELECT SUM(orders_count) as total_orders
        FROM performance
        WHERE employee_id = ?
        AND work_date IN ({date_placeholders})
        AND is_valid_workday = 1
    ''', [employee_id] + date_strs, one=True)
    
    recent_orders = result['total_orders'] if result and result['total_orders'] else 0
    orders_met = recent_orders >= rule['min_orders']
    
    # 综合判断
    eligible = workdays_met and orders_met
    
    reason = ''
    if not workdays_met:
        reason = f'C级周期过长（当前{workdays_in_c}天，要求≤{rule["max_workdays"]}天）'
    elif not orders_met:
        reason = f'最近{rule["recent_days"]}个工作日出单不足（当前{recent_orders}单，要求≥{rule["min_orders"]}单）'
    else:
        reason = f'已满足晋级条件（C级{workdays_in_c}天，最近{rule["recent_days"]}日出单{recent_orders}单）'
    
    return {
        'eligible': eligible,
        'workdays_in_c': workdays_in_c,
        'recent_orders': recent_orders,
        'reason': reason
    }


def check_b_to_a_eligible(employee_id):
    """
    检查B级→A级晋级资格
    """
    employee = query_db(
        'SELECT * FROM employees WHERE id = ? AND status = ?',
        [employee_id, 'B'],
        one=True
    )
    
    if not employee:
        return {'eligible': False, 'reason': '员工不存在或状态不是B级'}
    
    # 获取B级开始日期
    last_change = query_db(
        'SELECT * FROM status_history WHERE employee_id = ? AND to_status = ? ORDER BY change_date DESC LIMIT 1',
        [employee_id, 'B'],
        one=True
    )
    
    if last_change:
        b_start_date = last_change['change_date']
        if isinstance(b_start_date, str):
            b_start_date = datetime.strptime(b_start_date, '%Y-%m-%d').date()
    else:
        join_date = employee['join_date']
        if isinstance(join_date, str):
            join_date = datetime.strptime(join_date, '%Y-%m-%d').date()
        b_start_date = join_date
    
    today = date.today()
    workdays_in_b = count_workdays_between(b_start_date, today, include_start=True, include_end=True)
    
    # 检查周期要求
    rule = PROMOTION_RULES['B_to_A']
    workdays_met = workdays_in_b <= rule['max_workdays']
    
    # 获取最近N个工作日的出单数
    recent_workdays = get_recent_workdays(today, rule['recent_days'], include_end=True)
    if len(recent_workdays) < rule['recent_days']:
        return {
            'eligible': False,
            'workdays_in_b': workdays_in_b,
            'recent_orders': 0,
            'reason': f'工作日数不足{rule["recent_days"]}天'
        }
    
    date_placeholders = ','.join('?' * len(recent_workdays))
    date_strs = [d.strftime('%Y-%m-%d') for d in recent_workdays]
    
    result = query_db(f'''
        SELECT SUM(orders_count) as total_orders
        FROM performance
        WHERE employee_id = ?
        AND work_date IN ({date_placeholders})
        AND is_valid_workday = 1
    ''', [employee_id] + date_strs, one=True)
    
    recent_orders = result['total_orders'] if result and result['total_orders'] else 0
    orders_met = recent_orders >= rule['min_orders']
    
    eligible = workdays_met and orders_met
    
    reason = ''
    if not workdays_met:
        reason = f'B级周期过长（当前{workdays_in_b}天，要求≤{rule["max_workdays"]}天）'
    elif not orders_met:
        reason = f'最近{rule["recent_days"]}个工作日出单不足（当前{recent_orders}单，要求≥{rule["min_orders"]}单）'
    else:
        reason = f'已满足晋级条件（B级{workdays_in_b}天，最近{rule["recent_days"]}日出单{recent_orders}单）'
    
    return {
        'eligible': eligible,
        'workdays_in_b': workdays_in_b,
        'recent_orders': recent_orders,
        'reason': reason
    }


def trigger_promotion_confirmation(employee_id):
    """
    触发晋级确认流程
    
    Returns:
        dict: {
            'success': bool,
            'promotion_id': int,
            'message': str
        }
    """
    # 获取员工信息
    employee = query_db(
        'SELECT * FROM employees WHERE id = ?',
        [employee_id],
        one=True
    )
    
    if not employee:
        return {'success': False, 'message': '员工不存在'}
    
    current_status = employee['status']
    
    # 检查是否有待审批的晋级申请
    pending = query_db('''
        SELECT * FROM promotion_confirmations
        WHERE employee_id = ?
        AND status = 'pending'
    ''', [employee_id])
    
    if pending:
        return {'success': False, 'message': '已有待审批的晋级申请'}
    
    # 根据当前状态检查晋级资格
    check_result = None
    to_status = None
    
    if current_status == 'trainee':
        check_result = check_trainee_to_c_eligible(employee_id)
        to_status = 'C'
    elif current_status == 'C':
        check_result = check_c_to_b_eligible(employee_id)
        to_status = 'B'
    elif current_status == 'B':
        check_result = check_b_to_a_eligible(employee_id)
        to_status = 'A'
    else:
        return {'success': False, 'message': f'状态{current_status}无晋级路径'}
    
    if not check_result['eligible']:
        return {'success': False, 'message': f'不满足晋级条件：{check_result["reason"]}'}
    
    # 创建晋级确认记录
    db = get_db()
    cursor = db.cursor()
    
    trigger_date = date.today()
    
    cursor.execute('''
        INSERT INTO promotion_confirmations (
            employee_id, employee_no, employee_name,
            from_status, to_status,
            trigger_date, trigger_reason,
            days_in_status, recent_orders,
            status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
    ''', (
        employee_id, employee['employee_no'], employee['name'],
        current_status, to_status,
        trigger_date, check_result['reason'],
        check_result.get('workdays', check_result.get('workdays_in_c', check_result.get('workdays_in_b', 0))),
        check_result.get('recent_orders', 0)
    ))
    
    promotion_id = cursor.lastrowid
    db.commit()
    
    # 记录日志
    log_promotion_trigger(
        employee_id, employee['name'],
        current_status, to_status,
        check_result['reason']
    )
    
    # 发送通知给经理（employee['team']的经理）
    notify_manager_promotion_pending(employee['team'], promotion_id, employee)
    
    return {
        'success': True,
        'promotion_id': promotion_id,
        'message': f'晋级确认已触发：{current_status} → {to_status}'
    }


def notify_manager_promotion_pending(team, promotion_id, employee):
    """通知经理有待审批的晋级申请"""
    # 获取该团队的经理
    managers = query_db('''
        SELECT u.id, u.username
        FROM users u
        JOIN employees e ON u.employee_id = e.id
        WHERE u.role = 'manager'
        AND e.team = ?
    ''', [team])
    
    for manager in managers:
        create_notification(
            user_id=manager['id'],
            title='晋级待审批',
            content=f'员工 {employee["name"]}（{employee["employee_no"]}）申请晋级，请及时审批',
            notification_type='promotion_pending',
            link=f'/manager/promotions/{promotion_id}'
        )


def approve_promotion(promotion_id, approver_id, approver_name, approver_role):
    """
    批准晋级
    
    Returns:
        dict: {'success': bool, 'message': str}
    """
    promotion = query_db(
        'SELECT * FROM promotion_confirmations WHERE id = ?',
        [promotion_id],
        one=True
    )
    
    if not promotion:
        return {'success': False, 'message': '晋级记录不存在'}
    
    if promotion['status'] != 'pending':
        return {'success': False, 'message': f'当前状态为{promotion["status"]}，不可批准'}
    
    # 计算生效日期（下一个工作日）
    effective_date = get_next_workday(date.today(), offset=1)
    
    db = get_db()
    cursor = db.cursor()
    
    # 更新晋级记录
    cursor.execute('''
        UPDATE promotion_confirmations
        SET status = 'approved',
            approver_id = ?,
            approver_name = ?,
            approver_role = ?,
            approved_at = CURRENT_TIMESTAMP,
            effective_date = ?
        WHERE id = ?
    ''', (approver_id, approver_name, approver_role, effective_date, promotion_id))
    
    # 更新员工状态
    cursor.execute('''
        UPDATE employees
        SET status = ?
        WHERE id = ?
    ''', (promotion['to_status'], promotion['employee_id']))
    
    # 记录状态变更历史
    cursor.execute('''
        INSERT INTO status_history (
            employee_id, from_status, to_status,
            change_date, reason
        ) VALUES (?, ?, ?, ?, ?)
    ''', (
        promotion['employee_id'],
        promotion['from_status'],
        promotion['to_status'],
        effective_date,
        f'晋级确认通过（{approver_name}批准）'
    ))
    
    db.commit()
    
    # 记录日志
    log_promotion_approval(
        promotion['employee_id'], promotion['employee_name'],
        promotion['from_status'], promotion['to_status'],
        approved=True
    )
    
    # 通知员工
    employee_user = query_db(
        'SELECT id FROM users WHERE employee_id = ?',
        [promotion['employee_id']],
        one=True
    )
    
    if employee_user:
        create_notification(
            user_id=employee_user['id'],
            title='晋级通过',
            content=f'恭喜！您的晋级申请已通过，将于{effective_date}生效，晋升为{promotion["to_status"]}级',
            notification_type='promotion_approved'
        )
    
    return {
        'success': True,
        'message': f'晋级已批准，将于{effective_date}生效'
    }


def reject_promotion(promotion_id, approver_id, approver_name, approver_role, reason):
    """
    驳回晋级
    """
    promotion = query_db(
        'SELECT * FROM promotion_confirmations WHERE id = ?',
        [promotion_id],
        one=True
    )
    
    if not promotion:
        return {'success': False, 'message': '晋级记录不存在'}
    
    if promotion['status'] != 'pending':
        return {'success': False, 'message': f'当前状态为{promotion["status"]}，不可驳回'}
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        UPDATE promotion_confirmations
        SET status = 'rejected',
            approver_id = ?,
            approver_name = ?,
            approver_role = ?,
            approved_at = CURRENT_TIMESTAMP,
            rejection_reason = ?
        WHERE id = ?
    ''', (approver_id, approver_name, approver_role, reason, promotion_id))
    
    db.commit()
    
    # 记录日志
    log_promotion_approval(
        promotion['employee_id'], promotion['employee_name'],
        promotion['from_status'], promotion['to_status'],
        approved=False, reason=reason
    )
    
    # 通知员工
    employee_user = query_db(
        'SELECT id FROM users WHERE employee_id = ?',
        [promotion['employee_id']],
        one=True
    )
    
    if employee_user:
        create_notification(
            user_id=employee_user['id'],
            title='晋级未通过',
            content=f'您的晋级申请未通过。原因：{reason}',
            notification_type='promotion_rejected'
        )
    
    return {'success': True, 'message': '晋级已驳回'}


def override_promotion(promotion_id, admin_id, admin_name, reason):
    """
    管理员否决晋级（无论当前状态）
    """
    promotion = query_db(
        'SELECT * FROM promotion_confirmations WHERE id = ?',
        [promotion_id],
        one=True
    )
    
    if not promotion:
        return {'success': False, 'message': '晋级记录不存在'}
    
    db = get_db()
    cursor = db.cursor()
    
    original_status = promotion['status']
    
    cursor.execute('''
        UPDATE promotion_confirmations
        SET status = 'overridden',
            overridden_by = ?,
            overridden_name = ?,
            overridden_at = CURRENT_TIMESTAMP,
            override_reason = ?
        WHERE id = ?
    ''', (admin_id, admin_name, reason, promotion_id))
    
    # 如果已经批准并变更了员工状态，需要回滚
    if original_status == 'approved':
        cursor.execute('''
            UPDATE employees
            SET status = ?
            WHERE id = ?
        ''', (promotion['from_status'], promotion['employee_id']))
    
    db.commit()
    
    # 记录日志
    log_promotion_override(
        promotion['employee_id'], promotion['employee_name'],
        original_status, 'overridden', reason
    )
    
    return {'success': True, 'message': '晋级已被管理员否决'}


def check_all_employees_for_promotion():
    """
    批量检查所有员工的晋级资格（定时任务）
    
    Returns:
        dict: {'triggered_count': int, 'details': list}
    """
    # 获取所有在职员工
    employees = query_db('''
        SELECT id, employee_no, name, status
        FROM employees
        WHERE is_active = 1
        AND status IN ('trainee', 'C', 'B')
    ''')
    
    triggered_count = 0
    details = []
    
    for emp in employees:
        result = trigger_promotion_confirmation(emp['id'])
        if result['success']:
            triggered_count += 1
            details.append({
                'employee_no': emp['employee_no'],
                'name': emp['name'],
                'message': result['message']
            })
    
    return {
        'triggered_count': triggered_count,
        'details': details
    }


# 测试函数
if __name__ == '__main__':
    print("晋级确认引擎已加载")
    print("="*60)
    print("可用函数：")
    print("  - check_trainee_to_c_eligible()")
    print("  - check_c_to_b_eligible()")
    print("  - check_b_to_a_eligible()")
    print("  - trigger_promotion_confirmation()")
    print("  - approve_promotion()")
    print("  - reject_promotion()")
    print("  - override_promotion()")
    print("  - check_all_employees_for_promotion()")



