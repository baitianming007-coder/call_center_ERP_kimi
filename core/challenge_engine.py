#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
保级挑战引擎
处理A级员工的降级预警、保级挑战流程
"""

from datetime import datetime, date, timedelta
from core.database import query_db, get_db
from core.workday import get_recent_workdays, count_workdays_between, get_next_n_workdays
from core.audit import log_challenge_trigger, log_challenge_decision, log_challenge_result
from core.notifications import create_notification


# ==================== 保级规则配置 ====================

CHALLENGE_RULES = {
    'trigger_threshold': {
        'recent_days': 6,  # 最近6个工作日
        'min_orders': 12   # 最低12单
    },
    'challenge_period': {
        'workdays': 3,      # 3个工作日
        'target_orders': 9  # 目标9单
    },
    'monthly_limit': 1,     # 每月最多1次挑战
    'salary': {
        'failed_daily_rate': 30.0,  # 失败时30元/天（3天）
        'success_calculation': 'normal'  # 成功时按正常A级计算
    }
}


# ==================== 降级检测函数 ====================

def check_a_level_demotion_alert(employee_id):
    """
    检查A级员工是否触发降级预警
    
    Returns:
        dict: {
            'should_alert': bool,
            'recent_orders': int,
            'threshold': int,
            'reason': str
        }
    """
    employee = query_db(
        'SELECT * FROM employees WHERE id = ? AND status = ?',
        [employee_id, 'A'],
        one=True
    )
    
    if not employee:
        return {'should_alert': False, 'reason': '员工不存在或状态不是A级'}
    
    # 检查是否正在进行保级挑战
    ongoing_challenge = query_db('''
        SELECT * FROM demotion_challenges
        WHERE employee_id = ?
        AND decision = 'challenge'
        AND challenge_result = 'ongoing'
    ''', [employee_id], one=True)
    
    if ongoing_challenge:
        return {'should_alert': False, 'reason': '正在进行保级挑战'}
    
    # 获取最近N个工作日的出单数
    rule = CHALLENGE_RULES['trigger_threshold']
    today = date.today()
    recent_workdays = get_recent_workdays(today, rule['recent_days'], include_end=True)
    
    if len(recent_workdays) < rule['recent_days']:
        return {
            'should_alert': False,
            'recent_orders': 0,
            'threshold': rule['min_orders'],
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
    
    # 判断是否低于阈值
    should_alert = recent_orders <= rule['min_orders']
    
    reason = ''
    if should_alert:
        reason = f'最近{rule["recent_days"]}个工作日出单{recent_orders}单，低于{rule["min_orders"]}单阈值'
    else:
        reason = f'最近{rule["recent_days"]}个工作日出单{recent_orders}单，表现良好'
    
    return {
        'should_alert': should_alert,
        'recent_orders': recent_orders,
        'threshold': rule['min_orders'],
        'reason': reason
    }


def trigger_demotion_alert(employee_id):
    """
    触发降级预警流程
    
    Returns:
        dict: {'success': bool, 'challenge_id': int, 'message': str}
    """
    employee = query_db(
        'SELECT * FROM employees WHERE id = ?',
        [employee_id],
        one=True
    )
    
    if not employee:
        return {'success': False, 'message': '员工不存在'}
    
    if employee['status'] != 'A':
        return {'success': False, 'message': '仅A级员工可触发保级挑战'}
    
    # 检查是否已有待处理的预警
    pending = query_db('''
        SELECT * FROM demotion_challenges
        WHERE employee_id = ?
        AND decision = 'pending'
    ''', [employee_id])
    
    if pending:
        return {'success': False, 'message': '已有待处理的降级预警'}
    
    # 检查月度限制
    current_month = date.today().strftime('%Y-%m')
    month_challenges = query_db('''
        SELECT COUNT(*) as count
        FROM demotion_challenges
        WHERE employee_id = ?
        AND year_month = ?
        AND decision IN ('challenge', 'downgrade')
    ''', [employee_id, current_month], one=True)
    
    if month_challenges and month_challenges['count'] >= CHALLENGE_RULES['monthly_limit']:
        return {
            'success': False,
            'message': f'本月已达到保级挑战次数上限（{CHALLENGE_RULES["monthly_limit"]}次）'
        }
    
    # 执行检查
    check_result = check_a_level_demotion_alert(employee_id)
    
    if not check_result['should_alert']:
        return {'success': False, 'message': f'未触发降级条件：{check_result["reason"]}'}
    
    # 创建降级挑战记录
    db = get_db()
    cursor = db.cursor()
    
    trigger_date = date.today()
    
    cursor.execute('''
        INSERT INTO demotion_challenges (
            employee_id, employee_no, employee_name, year_month,
            trigger_date, trigger_orders,
            decision
        ) VALUES (?, ?, ?, ?, ?, ?, 'pending')
    ''', (
        employee_id, employee['employee_no'], employee['name'],
        current_month,
        trigger_date, check_result['recent_orders']
    ))
    
    challenge_id = cursor.lastrowid
    db.commit()
    
    # 记录日志
    log_challenge_trigger(
        employee_id, employee['name'],
        check_result['reason']
    )
    
    # 通知经理和员工
    notify_challenge_triggered(employee, challenge_id, check_result)
    
    return {
        'success': True,
        'challenge_id': challenge_id,
        'message': f'降级预警已触发：{check_result["reason"]}'
    }


def notify_challenge_triggered(employee, challenge_id, check_result):
    """通知经理和员工降级预警"""
    # 通知经理
    managers = query_db('''
        SELECT u.id, u.username
        FROM users u
        JOIN employees e ON u.employee_id = e.id
        WHERE u.role = 'manager'
        AND e.team = ?
    ''', [employee['team']])
    
    for manager in managers:
        create_notification(
            user_id=manager['id'],
            title='降级预警待处理',
            content=f'A级员工 {employee["name"]}（{employee["employee_no"]}）触发降级预警，请尽快处理',
            notification_type='challenge_triggered',
            link=f'/manager/challenges/{challenge_id}'
        )
    
    # 通知员工
    employee_user = query_db(
        'SELECT id FROM users WHERE employee_id = ?',
        [employee['id']],
        one=True
    )
    
    if employee_user:
        create_notification(
            user_id=employee_user['id'],
            title='降级预警通知',
            content=f'您的业绩触发降级预警，请关注主管的处理决定',
            notification_type='challenge_triggered'
        )


def make_challenge_decision(challenge_id, decision, manager_id, manager_name, reason=None):
    """
    经理做出保级挑战决策
    
    Args:
        decision: 'downgrade' 直接降级 | 'challenge' 保级挑战 | 'cancelled' 取消预警
    
    Returns:
        dict: {'success': bool, 'message': str}
    """
    challenge = query_db(
        'SELECT * FROM demotion_challenges WHERE id = ?',
        [challenge_id],
        one=True
    )
    
    if not challenge:
        return {'success': False, 'message': '挑战记录不存在'}
    
    if challenge['decision'] != 'pending':
        return {'success': False, 'message': f'当前状态为{challenge["decision"]}，不可再次决策'}
    
    db = get_db()
    cursor = db.cursor()
    
    # 更新决策
    cursor.execute('''
        UPDATE demotion_challenges
        SET decision = ?,
            decision_by = ?,
            decision_name = ?,
            decision_at = CURRENT_TIMESTAMP,
            decision_reason = ?
        WHERE id = ?
    ''', (decision, manager_id, manager_name, reason, challenge_id))
    
    if decision == 'downgrade':
        # 直接降级到C级
        effective_date = date.today() + timedelta(days=1)  # 次日生效（这里简化，实际应该用get_next_workday）
        
        cursor.execute('''
            UPDATE demotion_challenges
            SET effective_date = ?,
                challenge_result = 'failed'
            WHERE id = ?
        ''', (effective_date, challenge_id))
        
        # 更新员工状态
        cursor.execute('''
            UPDATE employees
            SET status = 'C'
            WHERE id = ?
        ''', [challenge['employee_id']])
        
        # 记录状态变更历史
        cursor.execute('''
            INSERT INTO status_history (
                employee_id, from_status, to_status,
                change_date, reason
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            challenge['employee_id'], 'A', 'C',
            effective_date,
            f'经理确认降级：{reason}'
        ))
        
        message = f'已确认降级，将于{effective_date}生效'
        
        # 通知员工
        notify_demotion_result(challenge, decision, message)
    
    elif decision == 'challenge':
        # 启动保级挑战
        from core.workday import get_next_n_workdays
        
        # 挑战周期：从次日开始的3个工作日
        start_date = date.today()  # 这里实际应该使用get_next_workday
        challenge_workdays = get_next_n_workdays(start_date, CHALLENGE_RULES['challenge_period']['workdays'], include_start=False)
        
        if len(challenge_workdays) >= CHALLENGE_RULES['challenge_period']['workdays']:
            challenge_start = challenge_workdays[0]
            challenge_end = challenge_workdays[-1]
        else:
            # 如果工作日不足，使用自然日
            challenge_start = start_date + timedelta(days=1)
            challenge_end = start_date + timedelta(days=3)
        
        cursor.execute('''
            UPDATE demotion_challenges
            SET challenge_start_date = ?,
                challenge_end_date = ?,
                challenge_result = 'ongoing'
            WHERE id = ?
        ''', (challenge_start, challenge_end, challenge_id))
        
        # 更新员工表的挑战标记
        cursor.execute('''
            UPDATE employees
            SET current_challenge_id = ?,
                challenge_count_this_month = challenge_count_this_month + 1,
                last_challenge_date = ?,
                status_display = 'A（保级挑战中）'
            WHERE id = ?
        ''', (challenge_id, challenge_start, challenge['employee_id']))
        
        message = f'保级挑战已启动：{challenge_start} 至 {challenge_end}'
        
        # 通知员工
        notify_challenge_started(challenge, challenge_start, challenge_end)
    
    elif decision == 'cancelled':
        # 取消预警
        cursor.execute('''
            UPDATE demotion_challenges
            SET challenge_result = 'cancelled'
            WHERE id = ?
        ''', [challenge_id])
        
        message = f'降级预警已取消：{reason}'
        
        # 通知员工
        notify_challenge_cancelled(challenge, reason)
    
    else:
        db.rollback()
        return {'success': False, 'message': f'无效的决策类型：{decision}'}
    
    db.commit()
    
    # 记录日志
    log_challenge_decision(
        challenge['employee_id'], challenge['employee_name'],
        decision, reason
    )
    
    return {'success': True, 'message': message}


def notify_demotion_result(challenge, decision, message):
    """通知员工降级结果"""
    employee_user = query_db(
        'SELECT id FROM users WHERE employee_id = ?',
        [challenge['employee_id']],
        one=True
    )
    
    if employee_user:
        create_notification(
            user_id=employee_user['id'],
            title='降级通知',
            content=message,
            notification_type='challenge_failed'
        )


def notify_challenge_started(challenge, start_date, end_date):
    """通知员工保级挑战开始"""
    employee_user = query_db(
        'SELECT id FROM users WHERE employee_id = ?',
        [challenge['employee_id']],
        one=True
    )
    
    target_orders = CHALLENGE_RULES['challenge_period']['target_orders']
    
    if employee_user:
        create_notification(
            user_id=employee_user['id'],
            title='保级挑战已启动',
            content=f'保级挑战期：{start_date} 至 {end_date}，目标：{target_orders}单',
            notification_type='challenge_triggered'
        )


def notify_challenge_cancelled(challenge, reason):
    """通知员工预警已取消"""
    employee_user = query_db(
        'SELECT id FROM users WHERE employee_id = ?',
        [challenge['employee_id']],
        one=True
    )
    
    if employee_user:
        create_notification(
            user_id=employee_user['id'],
            title='降级预警已取消',
            content=f'您的降级预警已取消。原因：{reason}',
            notification_type='status_change'
        )


def check_challenge_completion(challenge_id):
    """
    检查保级挑战是否完成（挑战期结束后调用）
    
    Returns:
        dict: {'completed': bool, 'success': bool, 'orders': int, 'message': str}
    """
    challenge = query_db(
        'SELECT * FROM demotion_challenges WHERE id = ?',
        [challenge_id],
        one=True
    )
    
    if not challenge:
        return {'completed': False, 'message': '挑战记录不存在'}
    
    if challenge['decision'] != 'challenge':
        return {'completed': False, 'message': '不是保级挑战'}
    
    if challenge['challenge_result'] != 'ongoing':
        return {'completed': True, 'message': '挑战已完成'}
    
    # 检查是否到达结束日期
    today = date.today()
    end_date = challenge['challenge_end_date']
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    if today <= end_date:
        # 还在挑战期内，统计当前出单数
        start_date = challenge['challenge_start_date']
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        # 统计挑战期间的出单数
        result = query_db('''
            SELECT SUM(orders_count) as total_orders
            FROM performance
            WHERE employee_id = ?
            AND work_date BETWEEN ? AND ?
            AND is_valid_workday = 1
        ''', [challenge['employee_id'], start_date, today], one=True)
        
        current_orders = result['total_orders'] if result and result['total_orders'] else 0
        
        return {
            'completed': False,
            'current_orders': current_orders,
            'target_orders': CHALLENGE_RULES['challenge_period']['target_orders'],
            'message': f'挑战进行中：当前{current_orders}单，目标{CHALLENGE_RULES["challenge_period"]["target_orders"]}单'
        }
    
    # 挑战期已结束，统计最终结果
    start_date = challenge['challenge_start_date']
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    result = query_db('''
        SELECT SUM(orders_count) as total_orders
        FROM performance
        WHERE employee_id = ?
        AND work_date BETWEEN ? AND ?
        AND is_valid_workday = 1
    ''', [challenge['employee_id'], start_date, end_date], one=True)
    
    total_orders = result['total_orders'] if result and result['total_orders'] else 0
    target_orders = CHALLENGE_RULES['challenge_period']['target_orders']
    
    success = total_orders >= target_orders
    
    result_text = '成功' if success else '失败'
    return {
        'completed': True,
        'success': success,
        'orders': total_orders,
        'target_orders': target_orders,
        'message': f'挑战{result_text}：出单{total_orders}单（目标{target_orders}单）'
    }


def finalize_challenge(challenge_id, manager_id, manager_name):
    """
    完成保级挑战（经理确认结果）
    
    Returns:
        dict: {'success': bool, 'result': str, 'message': str}
    """
    check_result = check_challenge_completion(challenge_id)
    
    if not check_result['completed']:
        return {'success': False, 'message': check_result['message']}
    
    challenge = query_db(
        'SELECT * FROM demotion_challenges WHERE id = ?',
        [challenge_id],
        one=True
    )
    
    db = get_db()
    cursor = db.cursor()
    
    success = check_result['success']
    result_status = 'success' if success else 'failed'
    
    # 更新挑战记录
    cursor.execute('''
        UPDATE demotion_challenges
        SET challenge_orders = ?,
            challenge_result = ?,
            result_confirmed_by = ?,
            result_confirmed_name = ?,
            result_confirmed_at = CURRENT_TIMESTAMP,
            salary_calculation_type = ?
        WHERE id = ?
    ''', (
        check_result['orders'],
        result_status,
        manager_id, manager_name,
        'challenge_success' if success else 'challenge_failed',
        challenge_id
    ))
    
    if not success:
        # 挑战失败，降级到C级
        effective_date = date.today() + timedelta(days=1)
        
        cursor.execute('''
            UPDATE demotion_challenges
            SET effective_date = ?
            WHERE id = ?
        ''', (effective_date, challenge_id))
        
        cursor.execute('''
            UPDATE employees
            SET status = 'C',
                current_challenge_id = NULL,
                status_display = NULL
            WHERE id = ?
        ''', [challenge['employee_id']])
        
        cursor.execute('''
            INSERT INTO status_history (
                employee_id, from_status, to_status,
                change_date, reason
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            challenge['employee_id'], 'A', 'C',
            effective_date,
            f'保级挑战失败（{check_result["orders"]}单<{check_result["target_orders"]}单）'
        ))
        
        message = f'保级挑战失败，将于{effective_date}降级为C级'
    else:
        # 挑战成功，维持A级
        cursor.execute('''
            UPDATE employees
            SET current_challenge_id = NULL,
                status_display = NULL
            WHERE id = ?
        ''', [challenge['employee_id']])
        
        message = f'保级挑战成功，维持A级'
    
    db.commit()
    
    # 记录日志
    log_challenge_result(
        challenge['employee_id'], challenge['employee_name'],
        result_status, check_result['orders']
    )
    
    # 通知员工
    notify_challenge_result(challenge, success, check_result)
    
    return {
        'success': True,
        'result': result_status,
        'message': message
    }


def notify_challenge_result(challenge, success, check_result):
    """通知员工保级挑战结果"""
    employee_user = query_db(
        'SELECT id FROM users WHERE employee_id = ?',
        [challenge['employee_id']],
        one=True
    )
    
    if employee_user:
        if success:
            title = '保级挑战成功'
            content = f'恭喜！您的保级挑战成功（{check_result["orders"]}单），继续保持A级'
            notification_type = 'challenge_success'
        else:
            title = '保级挑战失败'
            content = f'很遗憾，保级挑战未达标（{check_result["orders"]}单<{check_result["target_orders"]}单），将降级为C级'
            notification_type = 'challenge_failed'
        
        create_notification(
            user_id=employee_user['id'],
            title=title,
            content=content,
            notification_type=notification_type
        )


def batch_check_challenges():
    """
    批量检查所有进行中的保级挑战
    
    Returns:
        dict: {'completed_count': int, 'details': list}
    """
    # 获取所有进行中的挑战
    ongoing_challenges = query_db('''
        SELECT * FROM demotion_challenges
        WHERE decision = 'challenge'
        AND challenge_result = 'ongoing'
    ''')
    
    completed_count = 0
    details = []
    
    for challenge in ongoing_challenges:
        check_result = check_challenge_completion(challenge['id'])
        if check_result['completed']:
            # 自动触发完成流程（需要经理确认，这里只是检测）
            details.append({
                'employee_name': challenge['employee_name'],
                'result': check_result
            })
    
    return {
        'pending_count': len(details),
        'details': details
    }


# 测试函数
if __name__ == '__main__':
    print("保级挑战引擎已加载")
    print("="*60)
    print("可用函数：")
    print("  - check_a_level_demotion_alert()")
    print("  - trigger_demotion_alert()")
    print("  - make_challenge_decision()")
    print("  - check_challenge_completion()")
    print("  - finalize_challenge()")
    print("  - batch_check_challenges()")

