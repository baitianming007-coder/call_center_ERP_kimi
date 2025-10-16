#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
业绩重算核心模块
用于工作日配置变更后重新计算员工业绩
"""

from datetime import datetime, timedelta
from core.database import query_db, get_db
from core.workday import count_workdays_in_month


def get_affected_employees(year_month):
    """
    获取指定月份的所有活跃员工
    
    Args:
        year_month: str, 格式 'YYYY-MM'
    
    Returns:
        list: 员工ID列表
    """
    year, month = map(int, year_month.split('-'))
    
    # 获取该月份有业绩记录的所有员工
    employees = query_db('''
        SELECT DISTINCT e.id, e.employee_no, e.name, e.status
        FROM employees e
        WHERE e.is_active = 1
        AND EXISTS (
            SELECT 1 FROM performance p
            WHERE p.employee_id = e.id
            AND strftime('%Y-%m', p.work_date) = ?
        )
        ORDER BY e.employee_no
    ''', [year_month])
    
    return employees if employees else []


def recalculate_employee_month_attendance(employee_id, year_month):
    """
    重新计算员工的月度出勤统计
    基于最新的工作日配置
    
    Args:
        employee_id: int, 员工ID
        year_month: str, 格式 'YYYY-MM'
    
    Returns:
        dict: 更新后的出勤统计
    """
    # 获取该月的所有业绩记录
    performances = query_db('''
        SELECT work_date, attendance, orders_count
        FROM performance
        WHERE employee_id = ? AND strftime('%Y-%m', work_date) = ?
        ORDER BY work_date
    ''', [employee_id, year_month])
    
    if not performances:
        return {
            'valid_work_days': 0,
            'total_work_days': 0,
            'attendance_rate': 0
        }
    
    # 计算有效出勤天数（出勤且是工作日）
    from core.workday import is_workday
    
    valid_days = 0
    total_workdays = count_workdays_in_month(year_month)
    
    for perf in performances:
        work_date = perf['work_date']
        attendance = perf['attendance']
        
        # 只有出勤且确实是工作日才计入
        if attendance == 1 and is_workday(work_date):
            valid_days += 1
    
    attendance_rate = (valid_days / total_workdays * 100) if total_workdays > 0 else 0
    
    return {
        'valid_work_days': valid_days,
        'total_work_days': total_workdays,
        'attendance_rate': round(attendance_rate, 2)
    }


def recalculate_month_performance(year_month):
    """
    重新计算指定月份所有员工的业绩统计
    
    Args:
        year_month: str, 格式 'YYYY-MM'
    
    Returns:
        dict: 结果统计
    """
    employees = get_affected_employees(year_month)
    
    if not employees:
        return {
            'success': True,
            'recalculated_count': 0,
            'message': '该月份没有员工业绩数据'
        }
    
    db = get_db()
    cursor = db.cursor()
    
    recalculated_count = 0
    errors = []
    
    for emp in employees:
        try:
            employee_id = emp['id']
            
            # 重新计算出勤统计
            attendance_stats = recalculate_employee_month_attendance(employee_id, year_month)
            
            # 获取该月的总单数和总金额
            summary = query_db('''
                SELECT 
                    COALESCE(SUM(orders_count), 0) as total_orders,
                    COALESCE(SUM(revenue), 0) as total_revenue
                FROM performance
                WHERE employee_id = ? AND strftime('%Y-%m', work_date) = ?
            ''', [employee_id, year_month], one=True)
            
            # 注意：这里不更新薪资计算，因为薪资是在查询时动态计算的
            # 我们只需要确保业绩数据的工作日统计是准确的
            
            # 记录日志（可选）
            # log_performance_recalculation(employee_id, year_month, attendance_stats)
            
            recalculated_count += 1
            
        except Exception as e:
            errors.append(f"员工 {emp['employee_no']} 重算失败: {str(e)}")
    
    db.commit()
    
    return {
        'success': len(errors) == 0,
        'recalculated_count': recalculated_count,
        'total_employees': len(employees),
        'errors': errors if errors else None,
        'message': f'成功重新计算 {recalculated_count}/{len(employees)} 名员工的业绩'
    }


def validate_workday_impact(year_month):
    """
    验证工作日配置变更对业绩的影响
    
    Args:
        year_month: str, 格式 'YYYY-MM'
    
    Returns:
        dict: 影响分析
    """
    # 统计该月工作日数量
    total_workdays = count_workdays_in_month(year_month)
    
    # 统计有多少员工受影响
    affected_employees = get_affected_employees(year_month)
    
    # 统计该月的总业绩记录数
    perf_count = query_db('''
        SELECT COUNT(*) as count
        FROM performance
        WHERE strftime('%Y-%m', work_date) = ?
    ''', [year_month], one=True)
    
    return {
        'year_month': year_month,
        'total_workdays': total_workdays,
        'affected_employees': len(affected_employees),
        'performance_records': perf_count['count'] if perf_count else 0,
        'employees': [
            {
                'id': emp['id'],
                'employee_no': emp['employee_no'],
                'name': emp['name'],
                'status': emp['status']
            }
            for emp in affected_employees[:10]  # 只返回前10个作为示例
        ]
    }

