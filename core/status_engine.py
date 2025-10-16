"""
人员状态流转引擎
"""
from datetime import datetime, timedelta
from core.database import query_db


def check_status_transition(employee_id):
    """
    检查员工是否需要状态流转
    
    Args:
        employee_id: 员工ID
        
    Returns:
        dict: {
            'should_change': bool,
            'new_status': str,
            'reason': str,
            'days_in_status': int
        }
    """
    # 获取员工基本信息
    employee = query_db(
        'SELECT status, join_date, is_active FROM employees WHERE id = ?',
        (employee_id,),
        one=True
    )
    
    if not employee or not employee['is_active']:
        return {
            'should_change': False,
            'new_status': employee['status'] if employee else 'unknown',
            'reason': '员工不存在或已离职',
            'days_in_status': 0
        }
    
    status = employee['status']
    
    # 处理 join_date（可能是字符串或 date 对象）
    join_date = employee['join_date']
    if isinstance(join_date, str):
        join_date = datetime.strptime(join_date, '%Y-%m-%d').date()
    
    today = datetime.now().date()
    
    # 获取最后一次状态变更记录
    last_change = query_db(
        '''SELECT change_date, to_status 
           FROM status_history 
           WHERE employee_id = ? 
           ORDER BY change_date DESC, id DESC 
           LIMIT 1''',
        (employee_id,),
        one=True
    )
    
    # 计算在当前状态的天数
    if last_change:
        # 处理 change_date（可能是字符串或 date 对象）
        status_start_date = last_change['change_date']
        if isinstance(status_start_date, str):
            status_start_date = datetime.strptime(status_start_date, '%Y-%m-%d').date()
        days_in_status = (today - status_start_date).days
    else:
        # 没有状态变更记录，使用入职日期
        days_in_status = (today - join_date).days
    
    # 根据不同状态判断是否需要流转
    if status == 'trainee':
        return check_trainee_transition(employee_id, days_in_status)
    
    elif status == 'C':
        return check_c_transition(employee_id, days_in_status)
    
    elif status == 'B':
        return check_b_transition(employee_id, days_in_status)
    
    elif status == 'A':
        return check_a_transition(employee_id, days_in_status)
    
    elif status == 'eliminated':
        # 已淘汰，无需流转
        return {
            'should_change': False,
            'new_status': 'eliminated',
            'reason': '已淘汰',
            'days_in_status': days_in_status
        }
    
    # 默认不变更
    return {
        'should_change': False,
        'new_status': status,
        'reason': '无需变更',
        'days_in_status': days_in_status
    }


def check_trainee_transition(employee_id, days_in_status):
    """trainee → C：在岗满3天自动转C"""
    if days_in_status >= 3:
        return {
            'should_change': True,
            'new_status': 'C',
            'reason': '培训期满3天',
            'days_in_status': days_in_status
        }
    
    return {
        'should_change': False,
        'new_status': 'trainee',
        'reason': f'培训期未满3天（当前{days_in_status}天）',
        'days_in_status': days_in_status
    }


def check_c_transition(employee_id, days_in_status):
    """
    C → B：C在岗天数≤6 且 最近3天累计出单≥3
    C → eliminated：C在岗天数>6 且 最近3天累计出单<3
    """
    if days_in_status < 3:
        return {
            'should_change': False,
            'new_status': 'C',
            'reason': f'C状态未满3天（当前{days_in_status}天）',
            'days_in_status': days_in_status
        }
    
    # 计算最近3天的出单数
    recent_3_days_orders = get_recent_days_orders(employee_id, 3)
    
    # C在岗≤6天 且 最近3天出单≥3 → 晋升B
    if days_in_status <= 6 and recent_3_days_orders >= 3:
        return {
            'should_change': True,
            'new_status': 'B',
            'reason': f'6天内最近3天出单≥3单（实际{recent_3_days_orders}单）',
            'days_in_status': days_in_status
        }
    
    # C在岗>6天 且 最近3天出单<3 → 淘汰
    if days_in_status > 6 and recent_3_days_orders < 3:
        return {
            'should_change': True,
            'new_status': 'eliminated',
            'reason': f'超6天最近3天出单<3单（实际{recent_3_days_orders}单）',
            'days_in_status': days_in_status
        }
    
    return {
        'should_change': False,
        'new_status': 'C',
        'reason': f'暂不符合流转条件（在岗{days_in_status}天，最近3天{recent_3_days_orders}单）',
        'days_in_status': days_in_status
    }


def check_b_transition(employee_id, days_in_status):
    """
    B → A：B在岗天数≤9 且 最近6天累计出单≥12
    B → C：B在岗天数>9 且 最近6天累计出单<12
    """
    if days_in_status < 6:
        return {
            'should_change': False,
            'new_status': 'B',
            'reason': f'B状态未满6天（当前{days_in_status}天）',
            'days_in_status': days_in_status
        }
    
    # 计算最近6天的出单数
    recent_6_days_orders = get_recent_days_orders(employee_id, 6)
    
    # B在岗≤9天 且 最近6天出单≥12 → 晋升A
    if days_in_status <= 9 and recent_6_days_orders >= 12:
        return {
            'should_change': True,
            'new_status': 'A',
            'reason': f'9天内最近6天出单≥12单（实际{recent_6_days_orders}单）',
            'days_in_status': days_in_status
        }
    
    # B在岗>9天 且 最近6天出单<12 → 降级C
    if days_in_status > 9 and recent_6_days_orders < 12:
        return {
            'should_change': True,
            'new_status': 'C',
            'reason': f'超9天最近6天出单<12单（实际{recent_6_days_orders}单）',
            'days_in_status': days_in_status
        }
    
    return {
        'should_change': False,
        'new_status': 'B',
        'reason': f'暂不符合流转条件（在岗{days_in_status}天，最近6天{recent_6_days_orders}单）',
        'days_in_status': days_in_status
    }


def check_a_transition(employee_id, days_in_status):
    """
    A → C：最近6天累计出单≤12；或当月>25号时发现有效工作日<20
    """
    # 计算最近6天的出单数
    recent_6_days_orders = get_recent_days_orders(employee_id, 6)
    
    # 检查最近6天出单
    if recent_6_days_orders <= 12:
        return {
            'should_change': True,
            'new_status': 'C',
            'reason': f'最近6天出单≤12单（实际{recent_6_days_orders}单）',
            'days_in_status': days_in_status
        }
    
    # 检查当月有效工作日（仅在25号之后）
    today = datetime.now().date()
    if today.day > 25:
        valid_workdays = get_month_valid_workdays(employee_id, today.year, today.month)
        if valid_workdays < 20:
            return {
                'should_change': True,
                'new_status': 'C',
                'reason': f'月末有效工作日<20天（实际{valid_workdays}天）',
                'days_in_status': days_in_status
            }
    
    return {
        'should_change': False,
        'new_status': 'A',
        'reason': f'维持A级（最近6天{recent_6_days_orders}单）',
        'days_in_status': days_in_status
    }


def get_recent_days_orders(employee_id, days):
    """
    获取最近N天的总出单数
    
    Args:
        employee_id: 员工ID
        days: 天数
        
    Returns:
        int: 总出单数
    """
    today = datetime.now().date()
    start_date = today - timedelta(days=days-1)  # 包含今天
    
    result = query_db(
        '''SELECT COALESCE(SUM(orders_count), 0) as total 
           FROM performance 
           WHERE employee_id = ? 
           AND work_date >= ? 
           AND work_date <= ?''',
        (employee_id, start_date.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')),
        one=True
    )
    
    return result['total'] if result else 0


def get_month_valid_workdays(employee_id, year, month):
    """
    获取指定月份的有效工作日数
    
    Args:
        employee_id: 员工ID
        year: 年份
        month: 月份
        
    Returns:
        int: 有效工作日数
    """
    year_month = f"{year:04d}-{month:02d}"
    
    result = query_db(
        '''SELECT COUNT(*) as count 
           FROM performance 
           WHERE employee_id = ? 
           AND strftime('%Y-%m', work_date) = ?
           AND is_valid_workday = 1''',
        (employee_id, year_month),
        one=True
    )
    
    return result['count'] if result else 0


def apply_status_change(employee_id, new_status, reason, days_in_status):
    """
    应用状态变更
    
    Args:
        employee_id: 员工ID
        new_status: 新状态
        reason: 变更原因
        days_in_status: 在旧状态的天数
        
    Returns:
        bool: 是否成功
    """
    from core.database import get_db
    
    db = get_db()
    today = datetime.now().date().strftime('%Y-%m-%d')
    
    try:
        # 获取当前状态
        employee = query_db(
            'SELECT status FROM employees WHERE id = ?',
            (employee_id,),
            one=True
        )
        
        if not employee:
            return False
        
        old_status = employee['status']
        
        # 更新员工状态
        db.execute(
            'UPDATE employees SET status = ? WHERE id = ?',
            (new_status, employee_id)
        )
        
        # 写入状态变更历史
        db.execute(
            '''INSERT INTO status_history 
               (employee_id, from_status, to_status, change_date, reason, days_in_status)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (employee_id, old_status, new_status, today, reason, days_in_status)
        )
        
        db.commit()
        return True
    
    except Exception as e:
        db.rollback()
        print(f"状态变更失败: {e}")
        return False


def batch_check_all_employees():
    """
    批量检查所有在职员工的状态流转
    
    Returns:
        list: 需要变更的员工列表
    """
    employees = query_db(
        'SELECT id, employee_no, name, status, team FROM employees WHERE is_active = 1'
    )
    
    changes = []
    for emp in employees:
        result = check_status_transition(emp['id'])
        if result['should_change']:
            changes.append({
                'employee_id': emp['id'],
                'employee_no': emp['employee_no'],
                'name': emp['name'],
                'team': emp['team'],
                'old_status': emp['status'],
                'new_status': result['new_status'],
                'reason': result['reason'],
                'days_in_status': result['days_in_status']
            })
    
    return changes

