"""
工具函数模块
"""
import sys
import os
from datetime import date, timedelta
from typing import List

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.workday import get_recent_workdays, count_workdays_between, is_workday
from core.commission import calculate_daily_commission


def calculate_commission_by_orders(orders: int) -> float:
    """
    根据订单数计算提成（阶梯计算）
    
    Args:
        orders: 订单数
        
    Returns:
        float: 提成金额
    """
    return calculate_daily_commission(orders)


def get_workday_list(start_date: date, end_date: date) -> List[date]:
    """
    获取指定日期范围内的所有工作日列表
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        List[date]: 工作日列表
    """
    workdays = []
    current = start_date
    while current <= end_date:
        if is_workday(current):
            workdays.append(current)
        current += timedelta(days=1)
    return workdays


def format_date(d: date) -> str:
    """格式化日期为YYYY-MM-DD"""
    return d.strftime('%Y-%m-%d')


def parse_date(s: str) -> date:
    """解析YYYY-MM-DD格式的日期字符串"""
    from datetime import datetime
    return datetime.strptime(s, '%Y-%m-%d').date()


def calculate_days_in_status(start_date: date, end_date: date) -> int:
    """
    计算在某状态的天数（包含起始日）
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        int: 天数
    """
    return (end_date - start_date).days + 1


def get_month_str(d: date) -> str:
    """获取月份字符串 YYYY-MM"""
    return d.strftime('%Y-%m')


class ProgressBar:
    """简单的进度条工具"""
    
    def __init__(self, total: int, prefix: str = 'Progress'):
        self.total = total
        self.prefix = prefix
        self.current = 0
        
    def update(self, n: int = 1):
        """更新进度"""
        self.current += n
        percentage = (self.current / self.total) * 100
        bar_length = 50
        filled = int(bar_length * self.current / self.total)
        bar = '=' * filled + '-' * (bar_length - filled)
        print(f'\r{self.prefix}: [{bar}] {percentage:.1f}% ({self.current}/{self.total})', end='', flush=True)
        if self.current >= self.total:
            print()  # 完成后换行




