#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
操作日志（审计日志）模块
记录所有关键操作，包括人员变动、工资调整、审批操作等
"""

from datetime import datetime
import json
from core.database import query_db, get_db
from flask import session, request

# 操作类型中文映射
OPERATION_TYPE_LABELS = {
    'promotion': '晋升',
    'challenge': '保级',
    'training': '培训',
    'calendar': '工作日',
    'payroll': '工资',
    'bank_info': '银行信息',
    'status_change': '状态变更'
}

# 操作类型徽章颜色
OPERATION_TYPE_COLORS = {
    'promotion': 'success',
    'challenge': 'warning',
    'training': 'info',
    'calendar': 'secondary',
    'payroll': 'primary',
    'bank_info': 'info',
    'status_change': 'secondary'
}


def log_operation(
    operation_type,
    operation_module,
    operation_action,
    target_employee_id=None,
    target_employee_name=None,
    target_record_id=None,
    before_value=None,
    after_value=None,
    changes_dict=None,
    reason=None,
    notes=None,
    operator_id=None,
    operator_name=None,
    operator_role=None
):
    """
    记录操作日志
    
    Args:
        operation_type: 操作类型（如：promotion, demotion, salary, calendar）
        operation_module: 操作模块（如：promotion_confirmation, payroll, work_calendar）
        operation_action: 操作动作（如：approve, reject, adjust, configure）
        target_employee_id: 目标员工ID
        target_employee_name: 目标员工姓名
        target_record_id: 目标记录ID
        before_value: 变更前的值
        after_value: 变更后的值
        changes_dict: 变更内容字典（将转为JSON）
        reason: 原因
        notes: 备注
        operator_id: 操作人ID（可选，默认从session获取）
        operator_name: 操作人姓名（可选，默认从session获取）
        operator_role: 操作人角色（可选，默认从session获取）
    
    Returns:
        int: 日志记录ID
    """
    # 获取操作人信息
    if not operator_id:
        operator_id = session.get('user_id')
    if not operator_name:
        operator_name = session.get('username')
    if not operator_role:
        operator_role = session.get('role')
    
    # 获取请求信息
    ip_address = None
    user_agent = None
    try:
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')[:200]  # 限制长度
    except:
        pass
    
    # 转换changes_dict为JSON
    changes_json = None
    if changes_dict:
        changes_json = json.dumps(changes_dict, ensure_ascii=False)
    
    # 插入日志
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        INSERT INTO audit_logs (
            operation_type, operation_module, operation_action,
            operator_id, operator_name, operator_role,
            target_employee_id, target_employee_name, target_record_id,
            before_value, after_value, changes_json,
            reason, notes,
            ip_address, user_agent
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        operation_type, operation_module, operation_action,
        operator_id, operator_name, operator_role,
        target_employee_id, target_employee_name, target_record_id,
        before_value, after_value, changes_json,
        reason, notes,
        ip_address, user_agent
    ))
    
    db.commit()
    return cursor.lastrowid


# 预定义的日志记录函数

def log_promotion_trigger(employee_id, employee_name, from_status, to_status, trigger_reason):
    """记录晋级触发"""
    return log_operation(
        operation_type='promotion',
        operation_module='promotion_confirmation',
        operation_action='trigger',
        target_employee_id=employee_id,
        target_employee_name=employee_name,
        before_value=from_status,
        after_value=to_status,
        reason=trigger_reason
    )


def log_promotion_approval(employee_id, employee_name, from_status, to_status, approved, reason=None):
    """记录晋级审批"""
    action = 'approve' if approved else 'reject'
    return log_operation(
        operation_type='promotion',
        operation_module='promotion_confirmation',
        operation_action=action,
        target_employee_id=employee_id,
        target_employee_name=employee_name,
        before_value=from_status,
        after_value=to_status if approved else from_status,
        reason=reason
    )


def log_promotion_override(employee_id, employee_name, original_decision, new_decision, reason):
    """记录管理员否决晋级"""
    return log_operation(
        operation_type='promotion',
        operation_module='promotion_confirmation',
        operation_action='override',
        target_employee_id=employee_id,
        target_employee_name=employee_name,
        before_value=original_decision,
        after_value=new_decision,
        reason=reason
    )


def log_challenge_trigger(employee_id, employee_name, reason):
    """记录保级挑战触发"""
    return log_operation(
        operation_type='challenge',
        operation_module='demotion_challenge',
        operation_action='trigger',
        target_employee_id=employee_id,
        target_employee_name=employee_name,
        reason=reason
    )


def log_challenge_decision(employee_id, employee_name, decision, reason=None):
    """记录保级挑战决策"""
    return log_operation(
        operation_type='challenge',
        operation_module='demotion_challenge',
        operation_action=f'decision_{decision}',
        target_employee_id=employee_id,
        target_employee_name=employee_name,
        reason=reason
    )


def log_challenge_result(employee_id, employee_name, result, orders_count):
    """记录保级挑战结果"""
    return log_operation(
        operation_type='challenge',
        operation_module='demotion_challenge',
        operation_action=f'result_{result}',
        target_employee_id=employee_id,
        target_employee_name=employee_name,
        notes=f'挑战期间出单数：{orders_count}'
    )


def log_training_assessment(employee_id, employee_name, result, notes=None):
    """记录培训考核"""
    return log_operation(
        operation_type='training',
        operation_module='training_assessment',
        operation_action='record',
        target_employee_id=employee_id,
        target_employee_name=employee_name,
        after_value='通过' if result else '未通过',
        notes=notes
    )


def log_calendar_change(date_str, is_workday, day_type, reason=None):
    """记录工作日配置变更"""
    return log_operation(
        operation_type='calendar',
        operation_module='work_calendar',
        operation_action='configure',
        notes=f'{date_str}: {"工作日" if is_workday else "假期"}（{day_type}）',
        reason=reason
    )


def log_payroll_generate(year_month, employee_count, total_amount):
    """记录工资单生成"""
    return log_operation(
        operation_type='payroll',
        operation_module='payroll_records',
        operation_action='generate',
        notes=f'{year_month}月工资单：{employee_count}人，总计¥{total_amount:,.2f}'
    )


def log_payroll_adjustment(payroll_id, employee_id, employee_name, adjustment_type, amount, reason):
    """记录工资调整"""
    return log_operation(
        operation_type='payroll',
        operation_module='payroll_adjustments',
        operation_action=f'adjust_{adjustment_type}',
        target_employee_id=employee_id,
        target_employee_name=employee_name,
        target_record_id=payroll_id,
        after_value=f'¥{amount:.2f}',
        reason=reason
    )


def log_payroll_payment(payroll_id, employee_id, employee_name, payment_method, amount, status):
    """记录工资发放"""
    return log_operation(
        operation_type='payroll',
        operation_module='payroll_records',
        operation_action=f'payment_{status}',
        target_employee_id=employee_id,
        target_employee_name=employee_name,
        target_record_id=payroll_id,
        notes=f'发放方式：{payment_method}，金额：¥{amount:.2f}'
    )


def log_bank_verification(employee_id, employee_name, status, reason=None):
    """记录银行信息审核"""
    return log_operation(
        operation_type='bank_info',
        operation_module='employees',
        operation_action=f'verify_{status}',
        target_employee_id=employee_id,
        target_employee_name=employee_name,
        reason=reason
    )


def log_status_change(employee_id, employee_name, from_status, to_status, reason):
    """记录员工状态变更"""
    return log_operation(
        operation_type='status_change',
        operation_module='employees',
        operation_action='change_status',
        target_employee_id=employee_id,
        target_employee_name=employee_name,
        before_value=from_status,
        after_value=to_status,
        reason=reason
    )


def get_employee_logs(employee_id, limit=50):
    """
    获取员工相关的操作日志
    
    Args:
        employee_id: 员工ID
        limit: 返回记录数限制
    
    Returns:
        list: 日志记录列表
    """
    logs = query_db('''
        SELECT * FROM audit_logs
        WHERE target_employee_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', [employee_id, limit])
    
    return logs


def get_operator_logs(operator_id, limit=50):
    """
    获取操作人的日志
    
    Args:
        operator_id: 操作人ID
        limit: 返回记录数限制
    
    Returns:
        list: 日志记录列表
    """
    logs = query_db('''
        SELECT * FROM audit_logs
        WHERE operator_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', [operator_id, limit])
    
    return logs


def get_recent_logs(operation_type=None, limit=100):
    """
    获取最近的操作日志
    
    Args:
        operation_type: 操作类型筛选（可选）
        limit: 返回记录数限制
    
    Returns:
        list: 日志记录列表
    """
    if operation_type:
        logs = query_db('''
            SELECT * FROM audit_logs
            WHERE operation_type = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', [operation_type, limit])
    else:
        logs = query_db('''
            SELECT * FROM audit_logs
            ORDER BY created_at DESC
            LIMIT ?
        ''', [limit])
    
    return logs


def get_filtered_logs(operator_id=None, operation_type=None, start_date=None, 
                      end_date=None, search_keyword=None, page=1, per_page=50, 
                      is_admin=False):
    """
    获取筛选后的操作日志（支持分页）
    
    Args:
        operator_id: 操作人ID（经理只能看自己的）
        operation_type: 操作类型筛选
        start_date: 开始日期
        end_date: 结束日期
        search_keyword: 搜索关键词（员工姓名/工号）
        page: 页码（从1开始）
        per_page: 每页记录数
        is_admin: 是否管理员
    
    Returns:
        dict: {
            'logs': 日志记录列表,
            'pagination': 分页信息,
            'filters': 筛选器选项
        }
    """
    # 构建WHERE条件
    conditions = []
    params = []
    
    # 经理只能看自己的操作
    if not is_admin and operator_id:
        conditions.append('operator_id = ?')
        params.append(operator_id)
    
    # 操作类型筛选
    if operation_type:
        conditions.append('operation_type = ?')
        params.append(operation_type)
    
    # 日期范围筛选
    if start_date:
        conditions.append('DATE(created_at) >= ?')
        params.append(start_date)
    
    if end_date:
        conditions.append('DATE(created_at) <= ?')
        params.append(end_date)
    
    # 关键词搜索（员工姓名或工号）
    if search_keyword:
        conditions.append('(target_employee_name LIKE ? OR target_employee_id IN (SELECT id FROM employees WHERE employee_no LIKE ?))')
        search_pattern = f'%{search_keyword}%'
        params.extend([search_pattern, search_pattern])
    
    # 构建WHERE子句
    where_clause = ' AND '.join(conditions) if conditions else '1=1'
    
    # 查询总记录数
    count_query = f'SELECT COUNT(*) as total FROM audit_logs WHERE {where_clause}'
    total_count = query_db(count_query, params, one=True)['total']
    
    # 计算分页
    total_pages = (total_count + per_page - 1) // per_page
    offset = (page - 1) * per_page
    
    # 查询数据
    data_query = f'''
        SELECT * FROM audit_logs 
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    '''
    logs = query_db(data_query, params + [per_page, offset])
    
    # 格式化日志
    formatted_logs = [format_log_for_display(log) for log in logs]
    
    # 获取筛选器选项
    filter_options = get_filter_options(is_admin)
    
    # 分页信息
    pagination = {
        'page': page,
        'per_page': per_page,
        'total_count': total_count,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None,
        'start_index': offset + 1 if total_count > 0 else 0,
        'end_index': min(offset + per_page, total_count)
    }
    
    return {
        'logs': formatted_logs,
        'pagination': pagination,
        'filters': filter_options
    }


def get_filter_options(is_admin=False):
    """
    获取筛选器选项
    
    Args:
        is_admin: 是否管理员
    
    Returns:
        dict: 筛选器选项
    """
    options = {
        'operation_types': [
            {'value': '', 'label': '全部类型'},
            {'value': 'promotion', 'label': '晋升'},
            {'value': 'challenge', 'label': '保级'},
            {'value': 'training', 'label': '培训'},
            {'value': 'calendar', 'label': '工作日'},
            {'value': 'payroll', 'label': '工资'},
            {'value': 'bank_info', 'label': '银行信息'},
            {'value': 'status_change', 'label': '状态变更'}
        ],
        'per_page_options': [25, 50, 100, 200]
    }
    
    # 管理员可以看到所有操作人
    if is_admin:
        operators = query_db('''
            SELECT DISTINCT operator_id, operator_name 
            FROM audit_logs 
            ORDER BY operator_name
        ''')
        options['operators'] = [{'value': '', 'label': '全部操作人'}] + [
            {'value': op['operator_id'], 'label': op['operator_name']}
            for op in operators
        ]
    
    return options


def format_log_for_display(log):
    """
    格式化日志用于显示
    
    Args:
        log: 日志记录（dict）
    
    Returns:
        dict: 格式化后的日志
    """
    formatted = dict(log)
    
    # 解析changes_json
    if log['changes_json']:
        try:
            formatted['changes'] = json.loads(log['changes_json'])
        except:
            formatted['changes'] = {}
    else:
        formatted['changes'] = {}
    
    # 格式化时间（保留秒数）
    if log['created_at']:
        try:
            dt = datetime.strptime(log['created_at'], '%Y-%m-%d %H:%M:%S')
            formatted['created_at_formatted'] = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            formatted['created_at_formatted'] = log['created_at']
    
    # 添加操作类型中文标签
    formatted['operation_type_label'] = OPERATION_TYPE_LABELS.get(
        log['operation_type'], 
        log['operation_type']
    )
    
    # 添加操作类型颜色
    formatted['operation_type_color'] = OPERATION_TYPE_COLORS.get(
        log['operation_type'], 
        'secondary'
    )
    
    # 生成操作描述
    formatted['description'] = generate_log_description(log)
    
    return formatted


def generate_log_description(log):
    """
    生成日志的中文描述
    
    Args:
        log: 日志记录
    
    Returns:
        str: 描述文本
    """
    op_type = log['operation_type']
    op_action = log['operation_action']
    
    # 操作类型映射
    type_map = {
        'promotion': '晋级',
        'challenge': '保级挑战',
        'training': '培训考核',
        'calendar': '工作日配置',
        'payroll': '工资管理',
        'bank_info': '银行信息',
        'status_change': '状态变更'
    }
    
    # 操作动作映射
    action_map = {
        'trigger': '触发',
        'approve': '批准',
        'reject': '驳回',
        'override': '否决',
        'configure': '配置',
        'generate': '生成',
        'adjust_deduction': '扣款',
        'adjust_allowance': '补贴',
        'payment_paid': '发放成功',
        'payment_failed': '发放失败',
        'verify_verified': '审核通过',
        'verify_rejected': '审核拒绝',
        'change_status': '变更'
    }
    
    type_str = type_map.get(op_type, op_type)
    action_str = action_map.get(op_action, op_action)
    
    # 基础描述
    desc = f"{type_str} - {action_str}"
    
    # 添加目标员工信息
    if log['target_employee_name']:
        desc += f" - {log['target_employee_name']}"
    
    # 添加变更信息
    if log['before_value'] and log['after_value']:
        desc += f"（{log['before_value']} → {log['after_value']}）"
    
    return desc


# 测试函数
if __name__ == '__main__':
    print("操作日志模块已加载")
    print("可用函数：")
    print("  - log_operation() - 通用日志记录")
    print("  - log_promotion_*() - 晋级相关日志")
    print("  - log_challenge_*() - 保级挑战日志")
    print("  - log_payroll_*() - 工资相关日志")
    print("  - get_employee_logs() - 查询员工日志")
    print("  - get_operator_logs() - 查询操作人日志")



