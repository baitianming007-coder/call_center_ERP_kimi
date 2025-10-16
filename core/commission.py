"""
日提成计算引擎
"""


def calculate_daily_commission(orders_count):
    """
    计算日提成（阶梯制）
    
    规则：
    - 1-3单：10元/单
    - 4-5单：20元/单
    - ≥6单：30元/单
    
    Args:
        orders_count: 订单数量
        
    Returns:
        float: 当日提成金额
    """
    if orders_count <= 0:
        return 0
    
    if orders_count <= 3:
        return orders_count * 10
    
    if orders_count <= 5:
        return 3 * 10 + (orders_count - 3) * 20
    
    # ≥6单
    return 3 * 10 + 2 * 20 + (orders_count - 5) * 30


def calculate_commission_detail(orders_count):
    """
    返回提成计算明细（用于展示）
    
    Args:
        orders_count: 订单数量
        
    Returns:
        str: 提成计算明细文本
    """
    if orders_count <= 0:
        return "0单，提成0元"
    
    if orders_count <= 3:
        return f"{orders_count}单 × 10元/单 = {orders_count * 10}元"
    
    if orders_count <= 5:
        tier1 = 3 * 10
        tier2 = (orders_count - 3) * 20
        return f"前3单(30元) + 第4-{orders_count}单({orders_count-3}×20元) = {tier1 + tier2}元"
    
    # ≥6单
    tier1 = 3 * 10
    tier2 = 2 * 20
    tier3 = (orders_count - 5) * 30
    return f"前3单(30元) + 第4-5单(40元) + 第6-{orders_count}单({orders_count-5}×30元) = {tier1 + tier2 + tier3}元"


def calculate_total_commission(daily_records):
    """
    计算多天的总提成
    
    Args:
        daily_records: 每日出单记录列表，每条记录包含 orders_count
        
    Returns:
        float: 总提成金额
    """
    total = 0
    for record in daily_records:
        orders = record.get('orders_count', 0)
        total += calculate_daily_commission(orders)
    return total


