#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作日计算核心模块
提供工作日判断、计算、获取等功能
"""

from datetime import datetime, timedelta, date
from core.database import query_db


def is_workday(check_date):
    """
    判断指定日期是否为工作日
    规则：查询work_calendar表，未配置默认为工作日
    
    Args:
        check_date: date对象或字符串(YYYY-MM-DD)
    
    Returns:
        bool: True=工作日, False=假期/周末
    """
    # 转换为date对象
    if isinstance(check_date, str):
        check_date = datetime.strptime(check_date, '%Y-%m-%d').date()
    elif isinstance(check_date, datetime):
        check_date = check_date.date()
    
    # 查询配置
    config = query_db(
        'SELECT is_workday FROM work_calendar WHERE calendar_date = ?',
        [check_date.strftime('%Y-%m-%d')],
        one=True
    )
    
    if config:
        return config['is_workday'] == 1
    else:
        # 未配置默认为工作日
        return True


def count_workdays_in_month(year_month):
    """
    计算指定月份的工作日数量
    
    Args:
        year_month: str, 格式 'YYYY-MM'
    
    Returns:
        int: 该月的工作日数量
    """
    import calendar
    
    year, month = map(int, year_month.split('-'))
    
    # 获取该月的第一天和最后一天
    first_day = date(year, month, 1)
    last_day_num = calendar.monthrange(year, month)[1]
    last_day = date(year, month, last_day_num)
    
    return count_workdays_between(first_day, last_day, include_start=True, include_end=True)


def count_workdays_between(start_date, end_date, include_start=True, include_end=True):
    """
    计算两个日期之间的工作日数量
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        include_start: 是否包含开始日期
        include_end: 是否包含结束日期
    
    Returns:
        int: 工作日数量
    """
    # 转换为date对象
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    elif isinstance(start_date, datetime):
        start_date = start_date.date()
    
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    elif isinstance(end_date, datetime):
        end_date = end_date.date()
    
    # 调整范围
    if not include_start:
        start_date += timedelta(days=1)
    if not include_end:
        end_date -= timedelta(days=1)
    
    # 如果开始日期晚于结束日期，返回0
    if start_date > end_date:
        return 0
    
    # 计数
    count = 0
    current = start_date
    while current <= end_date:
        if is_workday(current):
            count += 1
        current += timedelta(days=1)
    
    return count


def get_next_workday(from_date, offset=1):
    """
    获取指定日期之后的第N个工作日
    
    Args:
        from_date: 起始日期
        offset: 偏移量（第几个工作日，默认1=下一个工作日）
    
    Returns:
        date: 目标工作日
    """
    # 转换为date对象
    if isinstance(from_date, str):
        from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
    elif isinstance(from_date, datetime):
        from_date = from_date.date()
    
    current = from_date + timedelta(days=1)  # 从次日开始
    found_count = 0
    
    # 防止无限循环，最多查找365天
    max_days = 365
    days_checked = 0
    
    while found_count < offset and days_checked < max_days:
        if is_workday(current):
            found_count += 1
            if found_count == offset:
                return current
        current += timedelta(days=1)
        days_checked += 1
    
    # 如果找不到（理论上不应该发生）
    return from_date + timedelta(days=offset)


def get_recent_workdays(end_date, count, include_end=True):
    """
    获取最近N个工作日的日期列表（包含end_date）
    
    Args:
        end_date: 结束日期
        count: 需要的工作日数量
        include_end: 是否包含结束日期
    
    Returns:
        list: 日期列表（从旧到新排序）
    """
    # 转换为date对象
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    elif isinstance(end_date, datetime):
        end_date = end_date.date()
    
    workdays = []
    current = end_date
    
    # 如果不包含结束日期，从前一天开始
    if not include_end:
        current -= timedelta(days=1)
    
    # 向前查找
    max_days = 365  # 防止无限循环
    days_checked = 0
    
    while len(workdays) < count and days_checked < max_days:
        if is_workday(current):
            workdays.append(current)
        current -= timedelta(days=1)
        days_checked += 1
    
    # 反转，使其从旧到新
    return workdays[::-1]


def get_next_n_workdays(start_date, count, include_start=False):
    """
    获取从start_date开始的N个工作日
    
    Args:
        start_date: 开始日期
        count: 需要的工作日数量
        include_start: 是否包含开始日期
    
    Returns:
        list: 日期列表（从旧到新排序）
    """
    # 转换为date对象
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    elif isinstance(start_date, datetime):
        start_date = start_date.date()
    
    workdays = []
    current = start_date
    
    # 如果不包含开始日期，从次日开始
    if not include_start:
        current += timedelta(days=1)
    
    # 向后查找
    max_days = 365  # 防止无限循环
    days_checked = 0
    
    while len(workdays) < count and days_checked < max_days:
        if is_workday(current):
            workdays.append(current)
        current += timedelta(days=1)
        days_checked += 1
    
    return workdays


def get_workdays_in_range(start_date, end_date):
    """
    获取指定日期范围内的所有工作日
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        list: 工作日列表
    """
    # 转换为date对象
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    elif isinstance(start_date, datetime):
        start_date = start_date.date()
    
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    elif isinstance(end_date, datetime):
        end_date = end_date.date()
    
    workdays = []
    current = start_date
    
    while current <= end_date:
        if is_workday(current):
            workdays.append(current)
        current += timedelta(days=1)
    
    return workdays


def calculate_workdays_since_join(employee_id):
    """
    计算员工入职以来的工作日数量
    
    Args:
        employee_id: 员工ID
    
    Returns:
        int: 工作日数量
    """
    from core.database import query_db
    
    employee = query_db(
        'SELECT join_date FROM employees WHERE id = ?',
        [employee_id],
        one=True
    )
    
    if not employee:
        return 0
    
    join_date = employee['join_date']
    if isinstance(join_date, str):
        join_date = datetime.strptime(join_date, '%Y-%m-%d').date()
    
    today = date.today()
    
    # 入职当天不算，从次日开始
    return count_workdays_between(join_date, today, include_start=False, include_end=True)


def format_workday_range(start_date, end_date):
    """
    格式化工作日范围（用于显示）
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        str: 格式化字符串，如"2025-10-01至2025-10-15（10个工作日）"
    """
    count = count_workdays_between(start_date, end_date)
    
    if isinstance(start_date, date):
        start_str = start_date.strftime('%Y-%m-%d')
    else:
        start_str = start_date
    
    if isinstance(end_date, date):
        end_str = end_date.strftime('%Y-%m-%d')
    else:
        end_str = end_date
    
    return f"{start_str}至{end_str}（{count}个工作日）"


# 测试函数
if __name__ == '__main__':
    # 测试工作日判断
    print("测试工作日功能")
    print("="*60)
    
    today = date.today()
    print(f"今天是: {today}")
    print(f"今天是工作日吗? {is_workday(today)}")
    
    # 测试获取下一个工作日
    next_wd = get_next_workday(today)
    print(f"下一个工作日: {next_wd}")
    
    # 测试获取最近N个工作日
    recent = get_recent_workdays(today, 5)
    print(f"最近5个工作日: {[str(d) for d in recent]}")
    
    # 测试计数
    start = today - timedelta(days=30)
    count = count_workdays_between(start, today)
    print(f"最近30天的工作日数: {count}")



