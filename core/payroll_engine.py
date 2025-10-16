#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工资管理引擎
处理工资单生成、调整、发放流程
"""

from datetime import datetime, date
import json
from core.database import query_db, get_db
from core.audit import log_payroll_generate, log_payroll_adjustment, log_payroll_payment
from core.notifications import create_notification


# ==================== 工资单生成 ====================

def generate_payroll_for_month(year_month, overwrite=False, operator_id=None, operator_name=None):
    """
    生成指定月份的工资单
    
    Args:
        year_month: 年月（YYYY-MM）
        overwrite: 是否覆盖已有工资单
        operator_id: 操作人ID
        operator_name: 操作人姓名
    
    Returns:
        dict: {
            'success': bool,
            'generated_count': int,
            'total_amount': float,
            'message': str
        }
    """
    # 检查是否已存在工资单
    existing = query_db('''
        SELECT COUNT(*) as count
        FROM payroll_records
        WHERE year_month = ?
        AND is_archived = 0
    ''', [year_month], one=True)
    
    if existing and existing['count'] > 0:
        if not overwrite:
            return {
                'success': False,
                'message': f'{year_month}月工资单已存在（{existing["count"]}条）'
            }
        else:
            # 删除旧工资单
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                DELETE FROM payroll_records
                WHERE year_month = ?
                AND is_archived = 0
            ''', [year_month])
            cursor.execute('''
                DELETE FROM payroll_adjustments
                WHERE payroll_id IN (
                    SELECT id FROM payroll_records
                    WHERE year_month = ?
                    AND is_archived = 0
                )
            ''', [year_month])
            db.commit()
    
    # 从salary表获取数据
    salary_records = query_db('''
        SELECT 
            s.*,
            e.employee_no,
            e.name as employee_name,
            e.team,
            e.status
        FROM salary s
        JOIN employees e ON s.employee_id = e.id
        WHERE s.year_month = ?
    ''', [year_month])
    
    if not salary_records:
        return {
            'success': False,
            'message': f'{year_month}月没有薪资记录（请先运行薪资计算）'
        }
    
    # 生成工资单
    db = get_db()
    cursor = db.cursor()
    
    generated_count = 0
    total_amount = 0.0
    
    for salary in salary_records:
        subtotal = (
            salary['base_salary'] +
            salary['attendance_bonus'] +
            salary['performance_bonus'] +
            salary['commission']
        )
        
        cursor.execute('''
            INSERT INTO payroll_records (
                employee_id, employee_no, employee_name, team, status_at_time,
                year_month,
                base_salary, attendance_bonus, performance_bonus, commission,
                subtotal, deductions, allowances, total_salary,
                status, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, 'pending', 1)
        ''', (
            salary['employee_id'],
            salary['employee_no'],
            salary['employee_name'],
            salary['team'],
            salary['status'],
            year_month,
            salary['base_salary'],
            salary['attendance_bonus'],
            salary['performance_bonus'],
            salary['commission'],
            subtotal,
            subtotal  # 初始total_salary = subtotal
        ))
        
        generated_count += 1
        total_amount += subtotal
    
    db.commit()
    
    # 记录日志
    if operator_id and operator_name:
        log_payroll_generate(year_month, generated_count, total_amount)
    
    return {
        'success': True,
        'generated_count': generated_count,
        'total_amount': total_amount,
        'message': f'成功生成{generated_count}条工资单，总计¥{total_amount:,.2f}'
    }


# ==================== 工资调整 ====================

def adjust_payroll(payroll_id, adjustment_type, amount, reason, operator_id, operator_name, operator_role):
    """
    调整工资（扣款或补贴）
    
    Args:
        payroll_id: 工资单ID
        adjustment_type: 'deduction' 扣款 | 'allowance' 补贴
        amount: 金额（正数）
        reason: 原因
        operator_id: 操作人ID
        operator_name: 操作人姓名
        operator_role: 操作人角色
    
    Returns:
        dict: {'success': bool, 'new_total': float, 'message': str}
    """
    payroll = query_db(
        'SELECT * FROM payroll_records WHERE id = ?',
        [payroll_id],
        one=True
    )
    
    if not payroll:
        return {'success': False, 'message': '工资单不存在'}
    
    # 检查权限：经理只能调整本团队
    if operator_role == 'manager':
        operator_emp = query_db(
            'SELECT team FROM employees WHERE id IN (SELECT employee_id FROM users WHERE id = ?)',
            [operator_id],
            one=True
        )
        
        if operator_emp and operator_emp['team'] != payroll['team']:
            return {'success': False, 'message': '无权限调整其他团队员工工资'}
    
    # 检查工资单状态
    if payroll['status'] == 'paid':
        return {'success': False, 'message': '已发放的工资单不能调整'}
    
    if adjustment_type not in ['deduction', 'allowance']:
        return {'success': False, 'message': f'无效的调整类型：{adjustment_type}'}
    
    if amount <= 0:
        return {'success': False, 'message': '金额必须大于0'}
    
    if not reason or reason.strip() == '':
        return {'success': False, 'message': '必须填写调整原因'}
    
    db = get_db()
    cursor = db.cursor()
    
    # 更新工资单
    if adjustment_type == 'deduction':
        new_deductions = payroll['deductions'] + amount
        new_total = payroll['subtotal'] + payroll['allowances'] - new_deductions
        
        cursor.execute('''
            UPDATE payroll_records
            SET deductions = ?,
                total_salary = ?,
                adjusted_by = ?,
                adjusted_by_name = ?,
                adjusted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_deductions, new_total, operator_id, operator_name, payroll_id))
    
    else:  # allowance
        new_allowances = payroll['allowances'] + amount
        new_total = payroll['subtotal'] + new_allowances - payroll['deductions']
        
        cursor.execute('''
            UPDATE payroll_records
            SET allowances = ?,
                total_salary = ?,
                adjusted_by = ?,
                adjusted_by_name = ?,
                adjusted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_allowances, new_total, operator_id, operator_name, payroll_id))
    
    # 记录调整明细
    cursor.execute('''
        INSERT INTO payroll_adjustments (
            payroll_id, adjustment_type, amount, reason,
            adjusted_by, adjusted_by_name, adjusted_by_role
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (payroll_id, adjustment_type, amount, reason,
          operator_id, operator_name, operator_role))
    
    db.commit()
    
    # 记录日志
    log_payroll_adjustment(
        payroll_id, payroll['employee_id'], payroll['employee_name'],
        adjustment_type, amount, reason
    )
    
    return {
        'success': True,
        'new_total': new_total,
        'message': f'调整成功：{"扣款" if adjustment_type == "deduction" else "补贴"}¥{amount:.2f}'
    }


def get_payroll_adjustments(payroll_id):
    """获取工资调整记录"""
    adjustments = query_db('''
        SELECT * FROM payroll_adjustments
        WHERE payroll_id = ?
        ORDER BY adjusted_at DESC
    ''', [payroll_id])
    
    return adjustments


# ==================== 工资发放 ====================

def confirm_payroll_for_payment(payroll_id, finance_id, finance_name):
    """
    财务确认工资单可发放
    
    Args:
        payroll_id: 工资单ID
        finance_id: 财务人员ID
        finance_name: 财务人员姓名
    
    Returns:
        dict: {'success': bool, 'message': str}
    """
    payroll = query_db(
        'SELECT * FROM payroll_records WHERE id = ?',
        [payroll_id],
        one=True
    )
    
    if not payroll:
        return {'success': False, 'message': '工资单不存在'}
    
    if payroll['status'] != 'pending':
        return {'success': False, 'message': f'当前状态为{payroll["status"]}，不可确认'}
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        UPDATE payroll_records
        SET status = 'confirmed',
            confirmed_by = ?,
            confirmed_by_name = ?,
            confirmed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (finance_id, finance_name, payroll_id))
    
    db.commit()
    
    return {'success': True, 'message': '工资单已确认，可以发放'}


def mark_payroll_payment(payroll_id, payment_method, payment_date, payment_reference=None, 
                         finance_id=None, finance_name=None, notes=None):
    """
    标记工资发放
    
    Args:
        payroll_id: 工资单ID
        payment_method: 发放方式（'bank_transfer', 'cash', 'other'）
        payment_date: 发放日期
        payment_reference: 转账凭证号
        finance_id: 财务人员ID
        finance_name: 财务人员姓名
        notes: 备注
    
    Returns:
        dict: {'success': bool, 'message': str}
    """
    payroll = query_db(
        'SELECT * FROM payroll_records WHERE id = ?',
        [payroll_id],
        one=True
    )
    
    if not payroll:
        return {'success': False, 'message': '工资单不存在'}
    
    # 如果选择银行转账，需要验证银行信息
    if payment_method == 'bank_transfer':
        employee = query_db(
            'SELECT bank_account_number, account_holder_name, name FROM employees WHERE id = ?',
            [payroll['employee_id']],
            one=True
        )
        
        if not employee or not employee['bank_account_number']:
            return {'success': False, 'message': '员工未录入银行卡信息'}
        
        if employee['account_holder_name'] != employee['name']:
            return {'success': False, 'message': '银行卡户名与员工姓名不符，不能使用银行转账'}
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        UPDATE payroll_records
        SET status = 'paid',
            payment_method = ?,
            payment_date = ?,
            payment_reference = ?,
            finance_notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (payment_method, payment_date, payment_reference, notes, payroll_id))
    
    db.commit()
    
    # 记录日志
    if finance_id and finance_name:
        log_payroll_payment(
            payroll_id, payroll['employee_id'], payroll['employee_name'],
            payment_method, payroll['total_salary'], 'paid'
        )
    
    # 通知员工（可选，因为员工看不到工资）
    # notify_payroll_paid(payroll)
    
    return {'success': True, 'message': '工资发放成功'}


def mark_payroll_payment_failed(payroll_id, failure_reason, finance_id=None, finance_name=None):
    """
    标记工资发放失败
    """
    payroll = query_db(
        'SELECT * FROM payroll_records WHERE id = ?',
        [payroll_id],
        one=True
    )
    
    if not payroll:
        return {'success': False, 'message': '工资单不存在'}
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        UPDATE payroll_records
        SET status = 'failed',
            failure_reason = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (failure_reason, payroll_id))
    
    db.commit()
    
    # 记录日志
    if finance_id and finance_name:
        log_payroll_payment(
            payroll_id, payroll['employee_id'], payroll['employee_name'],
            payroll['payment_method'], payroll['total_salary'], 'failed'
        )
    
    # 通知管理员
    notify_payroll_failed(payroll, failure_reason)
    
    return {'success': True, 'message': '已标记为发放失败'}


def retry_payroll_payment(payroll_id):
    """
    重试工资发放
    """
    payroll = query_db(
        'SELECT * FROM payroll_records WHERE id = ?',
        [payroll_id],
        one=True
    )
    
    if not payroll:
        return {'success': False, 'message': '工资单不存在'}
    
    if payroll['status'] not in ['failed', 'retry']:
        return {'success': False, 'message': '只有失败状态的工资单可以重试'}
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        UPDATE payroll_records
        SET status = 'retry',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', [payroll_id])
    
    db.commit()
    
    return {'success': True, 'message': '已设置为待重试状态'}


def notify_payroll_failed(payroll, reason):
    """通知管理员工资发放失败"""
    admins = query_db('''
        SELECT id FROM users WHERE role = 'admin'
    ''')
    
    for admin in admins:
        create_notification(
            user_id=admin['id'],
            title='工资发放失败',
            content=f'员工{payroll["employee_name"]}的工资发放失败：{reason}',
            notification_type='payroll_paid'
        )


# ==================== 批量操作 ====================

def batch_confirm_payrolls(year_month, finance_id, finance_name):
    """
    批量确认工资单
    
    Returns:
        dict: {'success': bool, 'confirmed_count': int, 'message': str}
    """
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        UPDATE payroll_records
        SET status = 'confirmed',
            confirmed_by = ?,
            confirmed_by_name = ?,
            confirmed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE year_month = ?
        AND status = 'pending'
        AND is_archived = 0
    ''', (finance_id, finance_name, year_month))
    
    confirmed_count = cursor.rowcount
    db.commit()
    
    return {
        'success': True,
        'confirmed_count': confirmed_count,
        'message': f'成功确认{confirmed_count}条工资单'
    }


# ==================== 年度归档 ====================

def archive_payroll_year(archive_year, operator_id, operator_name):
    """
    归档指定年份的工资记录
    
    Args:
        archive_year: 归档年份（如：2024）
        operator_id: 操作人ID
        operator_name: 操作人姓名
    
    Returns:
        dict: {'success': bool, 'archived_count': int, 'message': str}
    """
    # 检查是否有未发放的工资单
    unpaid = query_db('''
        SELECT COUNT(*) as count
        FROM payroll_records
        WHERE year_month LIKE ?
        AND status NOT IN ('paid', 'cancelled')
        AND is_archived = 0
    ''', [f'{archive_year}-%'], one=True)
    
    if unpaid and unpaid['count'] > 0:
        return {
            'success': False,
            'message': f'{archive_year}年存在{unpaid["count"]}条未发放工资单，不能归档'
        }
    
    # 统计数据
    summary = query_db('''
        SELECT 
            COUNT(DISTINCT employee_id) as total_employees,
            COUNT(*) as total_records,
            SUM(total_salary) as total_amount,
            year_month
        FROM payroll_records
        WHERE year_month LIKE ?
        AND is_archived = 0
        GROUP BY year_month
    ''', [f'{archive_year}-%'])
    
    if not summary:
        return {'success': False, 'message': f'{archive_year}年没有工资记录'}
    
    # 构建汇总JSON
    summary_json = json.dumps([dict(row) for row in summary], ensure_ascii=False)
    
    total_employees = len(set(row['total_employees'] for row in summary))
    total_records = sum(row['total_records'] for row in summary)
    total_amount = sum(row['total_amount'] for row in summary)
    
    db = get_db()
    cursor = db.cursor()
    
    # 创建归档记录
    cursor.execute('''
        INSERT INTO payroll_archives (
            archive_year, total_employees, total_records, total_amount,
            summary_json, archived_by, archived_by_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (archive_year, total_employees, total_records, total_amount,
          summary_json, operator_id, operator_name))
    
    # 标记工资单为已归档
    cursor.execute('''
        UPDATE payroll_records
        SET is_archived = 1,
            archive_year = ?
        WHERE year_month LIKE ?
        AND is_archived = 0
    ''', (archive_year, f'{archive_year}-%'))
    
    archived_count = cursor.rowcount
    db.commit()
    
    return {
        'success': True,
        'archived_count': archived_count,
        'total_amount': total_amount,
        'message': f'成功归档{archive_year}年工资记录：{archived_count}条，总计¥{total_amount:,.2f}'
    }


def get_archive_summary(archive_year):
    """获取归档汇总信息"""
    archive = query_db('''
        SELECT * FROM payroll_archives
        WHERE archive_year = ?
    ''', [archive_year], one=True)
    
    if not archive:
        return None
    
    # 解析summary_json
    summary = json.loads(archive['summary_json']) if archive['summary_json'] else []
    
    return {
        'archive': dict(archive),
        'monthly_summary': summary
    }


# 测试函数
if __name__ == '__main__':
    print("工资管理引擎已加载")
    print("="*60)
    print("可用函数：")
    print("  - generate_payroll_for_month()")
    print("  - adjust_payroll()")
    print("  - confirm_payroll_for_payment()")
    print("  - mark_payroll_payment()")
    print("  - mark_payroll_payment_failed()")
    print("  - batch_confirm_payrolls()")
    print("  - archive_payroll_year()")



