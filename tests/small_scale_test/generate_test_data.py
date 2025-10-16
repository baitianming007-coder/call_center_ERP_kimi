#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据生成器
生成300名员工及其6个月的业绩数据
"""

import random
import csv
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path

# 导入配置
from config import *

# 确保日志目录存在
Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# 设置日志
log_file = Path(LOGS_DIR) / 'data_generation.log'
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class TestDataGenerator:
    """测试数据生成器"""
    
    def __init__(self):
        self.employees = []
        self.performance_records = []
        self.expected_events = {
            'promotions': [],
            'demotions': [],
            'challenges': []
        }
        random.seed(42)  # 固定随机种子，便于复现
    
    def generate_employees(self):
        """生成员工数据"""
        logger.info(f"开始生成 {TOTAL_EMPLOYEES} 名员工...")
        
        for batch_idx, join_date in enumerate(BATCH_DATES):
            batch_start = batch_idx * EMPLOYEES_PER_MONTH + 1
            batch_end = batch_start + EMPLOYEES_PER_MONTH
            
            for emp_idx in range(batch_start, batch_end):
                # 随机分配业绩类型
                rand = random.random()
                if rand < PERFORMANCE_TYPES['excellent']:
                    perf_type = 'excellent'
                elif rand < PERFORMANCE_TYPES['excellent'] + PERFORMANCE_TYPES['normal']:
                    perf_type = 'normal'
                else:
                    perf_type = 'poor'
                
                # 随机分配出勤模式
                rand = random.random()
                if rand < ATTENDANCE_DISTRIBUTION['high']:
                    attendance_type = 'high'
                elif rand < ATTENDANCE_DISTRIBUTION['high'] + ATTENDANCE_DISTRIBUTION['medium']:
                    attendance_type = 'medium'
                else:
                    attendance_type = 'low'
                
                employee = {
                    'employee_no': get_employee_no(emp_idx),
                    'name': get_employee_name(emp_idx),
                    'join_date': join_date.strftime('%Y-%m-%d'),
                    'team': get_team_for_employee(emp_idx),
                    'manager': get_manager_for_employee(emp_idx),
                    'performance_type': perf_type,
                    'attendance_type': attendance_type,
                    'status': 'trainee'
                }
                
                self.employees.append(employee)
        
        logger.info(f"✓ 生成 {len(self.employees)} 名员工")
        return self.employees
    
    def is_workday(self, check_date):
        """判断是否为工作日（周日为休息日）"""
        return check_date.weekday() not in WEEKEND_DAYS
    
    def generate_daily_performance(self, employee, work_date):
        """生成员工的单日业绩数据"""
        # 如果不是工作日，不生成数据
        if not self.is_workday(work_date):
            return None
        
        # 如果还未入职，不生成数据
        join_date = datetime.strptime(employee['join_date'], '%Y-%m-%d').date()
        if work_date < join_date:
            return None
        
        # 根据出勤模式决定是否出勤
        attendance_rate_range = ATTENDANCE_RATE[employee['attendance_type']]
        is_attended = random.random() < random.uniform(*attendance_rate_range)
        
        if not is_attended:
            return {
                'employee_no': employee['employee_no'],
                'work_date': work_date.strftime('%Y-%m-%d'),
                'attendance': 0,
                'orders_count': 0,
                'revenue': 0,
                'call_duration': 0
            }
        
        # 根据业绩类型生成出单数
        orders_range = ORDERS_RANGE[employee['performance_type']]
        orders_count = random.randint(*orders_range)
        
        # 生成订单金额
        revenue = sum(random.uniform(*REVENUE_PER_ORDER) for _ in range(orders_count))
        
        # 生成通话时长
        call_duration = random.randint(*CALL_DURATION_RANGE)
        
        return {
            'employee_no': employee['employee_no'],
            'work_date': work_date.strftime('%Y-%m-%d'),
            'attendance': 1,
            'orders_count': orders_count,
            'revenue': round(revenue, 2),
            'call_duration': call_duration
        }
    
    def generate_performance_data(self):
        """生成所有员工的业绩数据"""
        logger.info(f"开始生成业绩数据 ({START_DATE} ~ {END_DATE})...")
        
        current_date = START_DATE
        total_days = (END_DATE - START_DATE).days + 1
        
        day_count = 0
        while current_date <= END_DATE:
            day_count += 1
            if day_count % 30 == 0:
                logger.info(f"  已生成 {day_count}/{total_days} 天的数据...")
            
            for employee in self.employees:
                record = self.generate_daily_performance(employee, current_date)
                if record:
                    self.performance_records.append(record)
            
            current_date += timedelta(days=1)
        
        logger.info(f"✓ 生成 {len(self.performance_records)} 条业绩记录")
        return self.performance_records
    
    def analyze_expected_events(self):
        """分析预期会触发的事件"""
        logger.info("分析预期触发事件...")
        
        # 按员工组织数据
        employee_data = {}
        for record in self.performance_records:
            emp_no = record['employee_no']
            if emp_no not in employee_data:
                employee_data[emp_no] = []
            employee_data[emp_no].append(record)
        
        # 分析每个员工的晋升可能性
        for employee in self.employees:
            emp_no = employee['employee_no']
            records = sorted(employee_data.get(emp_no, []), key=lambda x: x['work_date'])
            
            if not records:
                continue
            
            # 统计工作日数
            workdays = len([r for r in records if r['attendance'] == 1])
            
            # 统计连续出单天数
            consecutive_order_days = 0
            max_consecutive = 0
            for record in records:
                if record['attendance'] == 1 and record['orders_count'] > 0:
                    consecutive_order_days += 1
                    max_consecutive = max(max_consecutive, consecutive_order_days)
                else:
                    consecutive_order_days = 0
            
            # 判断是否可能转正
            if workdays >= PROMOTION_RULES['trainee_to_c']['min_workdays']:
                if max_consecutive >= PROMOTION_RULES['trainee_to_c']['consecutive_order_days']:
                    self.expected_events['promotions'].append({
                        'employee_no': emp_no,
                        'from_status': 'trainee',
                        'to_status': 'C',
                        'estimated_date': records[PROMOTION_RULES['trainee_to_c']['min_workdays']]['work_date']
                    })
        
        logger.info(f"✓ 预期转正人数: {len(self.expected_events['promotions'])}")
        return self.expected_events
    
    def save_to_csv(self):
        """保存数据到CSV文件"""
        logger.info("保存数据到CSV文件...")
        
        # 保存员工数据
        employees_file = f'{OUTPUT_DIR}/test_employees.csv'
        with open(employees_file, 'w', newline='', encoding='utf-8') as f:
            if self.employees:
                writer = csv.DictWriter(f, fieldnames=self.employees[0].keys())
                writer.writeheader()
                writer.writerows(self.employees)
        logger.info(f"✓ 员工数据已保存: {employees_file}")
        
        # 保存业绩数据
        performance_file = f'{OUTPUT_DIR}/test_performance.csv'
        with open(performance_file, 'w', newline='', encoding='utf-8') as f:
            if self.performance_records:
                writer = csv.DictWriter(f, fieldnames=self.performance_records[0].keys())
                writer.writeheader()
                writer.writerows(self.performance_records)
        logger.info(f"✓ 业绩数据已保存: {performance_file}")
        
        # 保存预期事件
        events_file = f'{OUTPUT_DIR}/expected_events.json'
        with open(events_file, 'w', encoding='utf-8') as f:
            json.dump(self.expected_events, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ 预期事件已保存: {events_file}")
    
    def generate_summary(self):
        """生成数据摘要"""
        summary = {
            'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'employees': {
                'total': len(self.employees),
                'by_performance_type': {
                    'excellent': len([e for e in self.employees if e['performance_type'] == 'excellent']),
                    'normal': len([e for e in self.employees if e['performance_type'] == 'normal']),
                    'poor': len([e for e in self.employees if e['performance_type'] == 'poor']),
                },
                'by_attendance_type': {
                    'high': len([e for e in self.employees if e['attendance_type'] == 'high']),
                    'medium': len([e for e in self.employees if e['attendance_type'] == 'medium']),
                    'low': len([e for e in self.employees if e['attendance_type'] == 'low']),
                }
            },
            'performance_records': {
                'total': len(self.performance_records),
                'with_orders': len([r for r in self.performance_records if r['orders_count'] > 0]),
                'total_orders': sum(r['orders_count'] for r in self.performance_records),
                'total_revenue': sum(r['revenue'] for r in self.performance_records),
            },
            'expected_events': {
                'promotions': len(self.expected_events['promotions']),
            }
        }
        
        # 保存摘要
        summary_file = f'{OUTPUT_DIR}/generation_summary.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # 打印摘要
        print("\n" + "="*70)
        print("数据生成摘要")
        print("="*70)
        print(f"员工总数: {summary['employees']['total']}")
        print(f"  - 优秀型: {summary['employees']['by_performance_type']['excellent']}")
        print(f"  - 正常型: {summary['employees']['by_performance_type']['normal']}")
        print(f"  - 待提升型: {summary['employees']['by_performance_type']['poor']}")
        print(f"\n业绩记录: {summary['performance_records']['total']} 条")
        print(f"  - 有效出单: {summary['performance_records']['with_orders']} 条")
        print(f"  - 总订单数: {summary['performance_records']['total_orders']} 单")
        print(f"  - 总营业额: ¥{summary['performance_records']['total_revenue']:.2f}")
        print(f"\n预期事件:")
        print(f"  - 转正人数: {summary['expected_events']['promotions']}")
        print("="*70 + "\n")
        
        return summary
    
    def run(self):
        """执行完整的数据生成流程"""
        start_time = datetime.now()
        logger.info("="*70)
        logger.info("开始生成测试数据")
        logger.info("="*70)
        
        try:
            # 步骤1: 生成员工
            self.generate_employees()
            
            # 步骤2: 生成业绩数据
            self.generate_performance_data()
            
            # 步骤3: 分析预期事件
            self.analyze_expected_events()
            
            # 步骤4: 保存到文件
            self.save_to_csv()
            
            # 步骤5: 生成摘要
            summary = self.generate_summary()
            
            # 计算耗时
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✓ 数据生成完成，耗时: {elapsed:.1f}秒")
            
            return True, summary
            
        except Exception as e:
            logger.error(f"✗ 数据生成失败: {str(e)}", exc_info=True)
            return False, None


def main():
    """主函数"""
    generator = TestDataGenerator()
    success, summary = generator.run()
    
    if success:
        print("\n✅ 测试数据生成成功！")
        print(f"📁 输出目录: {OUTPUT_DIR}")
        return 0
    else:
        print("\n❌ 测试数据生成失败！")
        return 1


if __name__ == '__main__':
    exit(main())

