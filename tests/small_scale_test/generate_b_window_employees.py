#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成B级窗口期员工数据
用于测试B→A晋升和A级保级功能
"""

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tests.small_scale_test.config import OUTPUT_DIR, LOGS_DIR

# 确保目录存在
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)

# ==================== 配置参数 ====================

# 关键：B→A晋升窗口是B级6-9天
# 今天是2025-10-16，我们需要让B级开始日期在10月8-10日之间
# 这样到今天正好是B级6-8天，处于晋升窗口内

# 计算合适的日期
TODAY = date.today()  # 2025-10-16
B_TARGET_DAYS = 7  # 目标：B级7天（在6-9天窗口内）
C_TO_B_DATE = TODAY - timedelta(days=B_TARGET_DAYS)  # 2025-10-09
TRAINEE_TO_C_DATE = C_TO_B_DATE - timedelta(days=4)  # 2025-10-05（C级4天）
JOIN_DATE = TRAINEE_TO_C_DATE - timedelta(days=3)  # 2025-10-02（trainee 3天）

# 测试结束日期
END_DATE = date(2025, 10, 31)

# 员工数量和分布
TOTAL_EMPLOYEES = 30
PERFORMANCE_TYPES = {
    'excellent': 0.30,   # 9人：日均4-5单，月单120-150
    'normal': 0.50,      # 15人：日均2-3单，月单60-90
    'poor': 0.20,        # 6人：日均1-2单，月单30-60
}

# 员工编号前缀
EMPLOYEE_PREFIX = 'BWINDOW'

# 团队分配
TEAMS = ['Team1', 'Team2', 'Team3', 'Team4', 'Team5']


def generate_employee_data():
    """生成员工基本信息"""
    print("生成B级窗口期员工基本信息...")
    
    employees = []
    
    for i in range(1, TOTAL_EMPLOYEES + 1):
        emp_no = f"{EMPLOYEE_PREFIX}{str(i).zfill(3)}"
        name = f"B窗口员工{str(i).zfill(3)}"
        team = TEAMS[(i - 1) % len(TEAMS)]
        
        # 分配业绩类型
        rand = random.random()
        if rand < PERFORMANCE_TYPES['excellent']:
            perf_type = 'excellent'
        elif rand < PERFORMANCE_TYPES['excellent'] + PERFORMANCE_TYPES['normal']:
            perf_type = 'normal'
        else:
            perf_type = 'poor'
        
        employees.append({
            'employee_no': emp_no,
            'name': name,
            'status': 'B',  # 当前状态为B级
            'join_date': JOIN_DATE.strftime('%Y-%m-%d'),
            'team': team,
            'is_active': 1,
            'performance_type': perf_type
        })
    
    # 保存CSV
    csv_file = Path(OUTPUT_DIR) / 'b_window_employees.csv'
    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'employee_no', 'name', 'status', 'join_date', 'team', 'is_active'
        ])
        writer.writeheader()
        for emp in employees:
            writer.writerow({
                'employee_no': emp['employee_no'],
                'name': emp['name'],
                'status': emp['status'],
                'join_date': emp['join_date'],
                'team': emp['team'],
                'is_active': emp['is_active']
            })
    
    print(f"  ✓ 生成 {len(employees)} 名员工")
    print(f"  ✓ 保存到: {csv_file}")
    
    return employees


def generate_performance_data(employees):
    """生成业绩数据"""
    print("\n生成业绩数据...")
    
    performance_records = []
    
    # 业绩模式定义
    orders_range = {
        'excellent': (4, 5),  # 优秀型：日均4-5单
        'normal': (2, 3),     # 正常型：日均2-3单
        'poor': (1, 2)        # 待提升型：日均1-2单
    }
    
    for emp in employees:
        emp_no = emp['employee_no']
        perf_type = emp['performance_type']
        min_orders, max_orders = orders_range[perf_type]
        
        # 生成从入职到测试结束的业绩
        current_date = JOIN_DATE
        
        while current_date <= END_DATE:
            # 跳过周日
            if current_date.weekday() != 6:  # 6=Sunday
                # 出勤率：优秀型95-100%，正常型85-95%，待提升型75-85%
                if perf_type == 'excellent':
                    attend = random.random() < 0.98
                elif perf_type == 'normal':
                    attend = random.random() < 0.90
                else:
                    attend = random.random() < 0.82
                
                if attend:
                    # 生成订单数（有随机波动）
                    orders = random.randint(min_orders, max_orders)
                    
                    # 计算日提成（按产品文档规则）
                    if orders <= 3:
                        commission = orders * 10
                    elif orders <= 5:
                        commission = 3 * 10 + (orders - 3) * 20
                    else:
                        commission = 3 * 10 + 2 * 20 + (orders - 5) * 30
                    
                    performance_records.append({
                        'employee_no': emp_no,
                        'work_date': current_date.strftime('%Y-%m-%d'),
                        'orders_count': orders,
                        'commission': commission,
                        'is_valid_workday': 1
                    })
            
            current_date += timedelta(days=1)
    
    # 保存CSV
    csv_file = Path(OUTPUT_DIR) / 'b_window_performance.csv'
    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'employee_no', 'work_date', 'orders_count', 'commission', 'is_valid_workday'
        ])
        writer.writeheader()
        writer.writerows(performance_records)
    
    print(f"  ✓ 生成 {len(performance_records)} 条业绩记录")
    print(f"  ✓ 保存到: {csv_file}")
    
    return performance_records


def generate_status_history(employees):
    """生成状态变更历史"""
    print("\n生成状态变更历史...")
    
    status_history = []
    
    for emp in employees:
        emp_no = emp['employee_no']
        
        # trainee → C（3天后）
        status_history.append({
            'employee_no': emp_no,
            'from_status': 'trainee',
            'to_status': 'C',
            'change_date': TRAINEE_TO_C_DATE.strftime('%Y-%m-%d'),
            'reason': '培训期满3天，自动转C级',
            'days_in_status': 3
        })
        
        # C → B（7天后，符合条件）
        # 注意：这里设置为7天是为了在窗口边缘测试
        status_history.append({
            'employee_no': emp_no,
            'from_status': 'C',
            'to_status': 'B',
            'change_date': C_TO_B_DATE.strftime('%Y-%m-%d'),
            'reason': 'C级7天，最近3天出单≥3，晋升B级',
            'days_in_status': 7
        })
    
    # 保存JSON
    json_file = Path(OUTPUT_DIR) / 'b_window_status_history.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(status_history, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 生成 {len(status_history)} 条状态变更记录")
    print(f"  ✓ 保存到: {json_file}")
    
    return status_history


def generate_summary(employees, performance_records, status_history):
    """生成摘要信息"""
    print("\n生成数据摘要...")
    
    # 统计业绩类型分布
    type_counts = {'excellent': 0, 'normal': 0, 'poor': 0}
    for emp in employees:
        type_counts[emp['performance_type']] += 1
    
    # 计算日期范围
    b_start_date = C_TO_B_DATE
    days_in_b = (END_DATE - b_start_date).days
    
    summary = {
        'generation_date': date.today().strftime('%Y-%m-%d'),
        'employee_count': len(employees),
        'employee_types': type_counts,
        'join_date': JOIN_DATE.strftime('%Y-%m-%d'),
        'trainee_to_c_date': TRAINEE_TO_C_DATE.strftime('%Y-%m-%d'),
        'c_to_b_date': C_TO_B_DATE.strftime('%Y-%m-%d'),
        'end_date': END_DATE.strftime('%Y-%m-%d'),
        'days_in_b_status': days_in_b,
        'performance_records': len(performance_records),
        'status_changes': len(status_history),
        'key_dates': {
            'join': JOIN_DATE.strftime('%Y-%m-%d'),
            'to_c': TRAINEE_TO_C_DATE.strftime('%Y-%m-%d'),
            'to_b': C_TO_B_DATE.strftime('%Y-%m-%d'),
            'test_end': END_DATE.strftime('%Y-%m-%d')
        },
        'b_to_a_window': {
            'description': 'B→A晋升窗口是B级后的6-9天',
            'window_start': (b_start_date + timedelta(days=6)).strftime('%Y-%m-%d'),
            'window_end': (b_start_date + timedelta(days=9)).strftime('%Y-%m-%d'),
            'actual_days_in_b': days_in_b,
            'can_test_promotion': days_in_b >= 6
        }
    }
    
    # 保存摘要
    json_file = Path(OUTPUT_DIR) / 'b_window_summary.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 摘要保存到: {json_file}")
    
    return summary


def main():
    """主函数"""
    print("="*70)
    print("生成B级窗口期员工测试数据")
    print("="*70)
    print(f"\n目标：创建30名员工，用于测试B→A晋升和A级保级")
    print(f"入职日期：{JOIN_DATE}")
    print(f"C级日期：{TRAINEE_TO_C_DATE}（入职后3天）")
    print(f"B级日期：{C_TO_B_DATE}（C级后7天）")
    print(f"测试结束：{END_DATE}")
    print(f"B级天数：{(END_DATE - C_TO_B_DATE).days}天")
    print()
    
    # 生成数据
    employees = generate_employee_data()
    performance_records = generate_performance_data(employees)
    status_history = generate_status_history(employees)
    summary = generate_summary(employees, performance_records, status_history)
    
    print("\n" + "="*70)
    print("数据生成完成")
    print("="*70)
    print(f"\n员工数量: {summary['employee_count']}")
    print(f"  - 优秀型: {summary['employee_types']['excellent']}人")
    print(f"  - 正常型: {summary['employee_types']['normal']}人")
    print(f"  - 待提升型: {summary['employee_types']['poor']}人")
    print(f"\n业绩记录: {summary['performance_records']}条")
    print(f"状态变更: {summary['status_changes']}条")
    print(f"\nB级天数: {summary['days_in_b_status']}天")
    print(f"B→A窗口: {summary['b_to_a_window']['window_start']} ~ {summary['b_to_a_window']['window_end']}")
    print(f"可测试晋升: {'是' if summary['b_to_a_window']['can_test_promotion'] else '否'}")
    print("\n" + "="*70)


if __name__ == '__main__':
    main()

