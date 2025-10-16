"""
测试数据生成器
生成500人×6个月的员工信息、每日业绩数据和预期事件
"""
import sys
import os
import csv
import json
import random
from datetime import date, timedelta
from typing import List, Dict, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.large_scale_test.config import *
from tests.large_scale_test.utils import (
    calculate_commission_by_orders,
    get_workday_list,
    format_date,
    get_month_str,
    ProgressBar
)
from app import app


class EmployeeBehaviorGenerator:
    """员工行为数据生成器"""
    
    def __init__(self, employee_type: str, employee_no: str):
        self.type = employee_type
        self.employee_no = employee_no
        self.current_status = 'trainee'
        self.status_start_date = None
        self.days_in_current_status = 0
        self.promotion_rejected_count = 0  # 晋级被驳回次数
        
    def generate_daily_orders(self, work_date: date, workdays_since_status_start: int) -> int:
        """
        根据员工类型和当前状态生成每日出单数
        
        Args:
            work_date: 工作日期
            workdays_since_status_start: 在当前状态的工作日数
            
        Returns:
            int: 出单数
        """
        if self.type == 'fast_growth':
            return self._generate_fast_growth_orders(workdays_since_status_start)
        elif self.type == 'fluctuating':
            return self._generate_fluctuating_orders(workdays_since_status_start)
        elif self.type == 'underperforming':
            return self._generate_underperforming_orders(workdays_since_status_start)
        elif self.type == 'edge_case':
            return self._generate_edge_case_orders(workdays_since_status_start)
        else:
            return 0
    
    def _generate_fast_growth_orders(self, days: int) -> int:
        """快速成长型：稳定高出单"""
        if self.current_status == 'trainee':
            return random.randint(1, 2)  # 培训期少量出单
        elif self.current_status == 'C':
            return random.randint(2, 3)  # C级快速达标
        elif self.current_status == 'B':
            return random.randint(2, 3)  # B级稳定输出
        elif self.current_status == 'A':
            return random.randint(3, 5)  # A级高产出
        return 0
    
    def _generate_fluctuating_orders(self, days: int) -> int:
        """达标波动型：刚好踩线达标"""
        if self.current_status == 'trainee':
            return random.randint(0, 1)
        elif self.current_status == 'C':
            # C级：最近3天需要≥3单，刚好达标
            return 1  # 平均1单/天，3天3单
        elif self.current_status == 'B':
            # B级：最近6天需要≥12单，刚好达标
            return 2  # 平均2单/天，6天12单
        elif self.current_status == 'A':
            # A级：可能触发保级
            if days % 10 == 8:  # 偶尔触发降级预警
                return 1
            return random.randint(2, 3)
        return 0
    
    def _generate_underperforming_orders(self, days: int) -> int:
        """待淘汰型：经常不达标"""
        if self.current_status == 'trainee':
            return random.randint(0, 1)
        elif self.current_status == 'C':
            # C级：经常低于3单
            if days <= 6:
                return random.randint(0, 1)  # 前6天低产出
            else:
                return 0  # 超过6天后更差
        elif self.current_status == 'B':
            return random.randint(1, 2)  # B级勉强维持
        elif self.current_status == 'A':
            # A级但经常触发降级
            return random.randint(1, 2)
        return 0
    
    def _generate_edge_case_orders(self, days: int) -> int:
        """特殊规则型：触发边缘场景"""
        # 这类员工的行为模式需要特别设计以触发特殊场景
        if self.current_status == 'trainee':
            return 1
        elif self.current_status == 'C':
            return random.randint(1, 2)
        elif self.current_status == 'B':
            return 2
        elif self.current_status == 'A':
            # 可能多次触发保级
            month = get_month_str(date.today())
            # 根据月份变化行为
            return random.randint(1, 4)
        return 0


class DataGenerator:
    """主数据生成器"""
    
    def __init__(self):
        self.employees = []
        self.performance_data = []
        self.expected_events = []
        self.supervisors = []
        
    def generate_all(self):
        """生成所有测试数据"""
        print("="*60)
        print("开始生成大规模测试数据")
        print("="*60)
        print(f"员工数量: {TOTAL_EMPLOYEES}")
        print(f"时间范围: {START_DATE} - {END_DATE}")
        print(f"预计业绩记录数: ~{TOTAL_EMPLOYEES * 180}")
        print()
        
        # 生成主管列表
        self._generate_supervisors()
        
        # 生成员工基础信息
        print("步骤1: 生成员工基础信息...")
        self._generate_employees()
        print(f"✓ 已生成 {len(self.employees)} 名员工")
        print()
        
        # 生成每日业绩数据
        print("步骤2: 生成每日业绩数据...")
        self._generate_daily_performance()
        print(f"✓ 已生成 {len(self.performance_data)} 条业绩记录")
        print()
        
        # 计算预期事件
        print("步骤3: 计算预期触发事件...")
        self._calculate_expected_events()
        print(f"✓ 已计算 {len(self.expected_events)} 个预期事件")
        print()
        
        # 保存数据
        print("步骤4: 保存数据文件...")
        self._save_data()
        print("✓ 数据文件已保存")
        print()
        
        print("="*60)
        print("数据生成完成！")
        print("="*60)
        self._print_summary()
    
    def _generate_supervisors(self):
        """生成主管列表"""
        for i in range(1, NUM_SUPERVISORS + 1):
            self.supervisors.append({
                'id': i,
                'username': f'manager{i:03d}',
                'name': f'主管{i}',
                'password': SUPERVISOR_PASSWORD
            })
    
    def _generate_employees(self):
        """生成员工基础信息"""
        emp_no = 25001
        
        # 按类型分配员工
        for emp_type, count in EMPLOYEE_DISTRIBUTION.items():
            for i in range(count):
                # 随机入职日期（1月1日-6月1日）
                days_offset = random.randint(0, 150)  # 最多150天，确保有足够时间观察
                join_date = START_DATE + timedelta(days=days_offset)
                
                # 随机分配主管
                supervisor_id = random.randint(1, NUM_SUPERVISORS)
                
                employee = {
                    'employee_no': f'CC{emp_no}',
                    'name': f'员工{emp_no}',
                    'employee_type': emp_type,
                    'join_date': format_date(join_date),
                    'supervisor_id': supervisor_id,
                    'team': f'Team{supervisor_id}',  # 按主管分组
                    'status': 'trainee',
                    'is_active': 1
                }
                
                self.employees.append(employee)
                emp_no += 1
    
    def _generate_daily_performance(self):
        """生成每日业绩数据"""
        progress = ProgressBar(len(self.employees), '生成业绩数据')
        
        # 使用应用上下文
        with app.app_context():
            for emp in self.employees:
                generator = EmployeeBehaviorGenerator(
                    emp['employee_type'],
                    emp['employee_no']
                )
                
                # 从入职日期开始到测试结束日期
                join_date = date.fromisoformat(emp['join_date'])
                current_date = join_date
                workdays_count = 0
                
                while current_date <= END_DATE:
                    # 只在工作日生成数据（简化：周一到周五）
                    if current_date.weekday() < 5:  # 0-4 表示周一到周五
                        workdays_count += 1
                        
                        # 生成出单数
                        orders = generator.generate_daily_orders(current_date, workdays_count)
                        commission = calculate_commission_by_orders(orders)
                        
                        # 添加业绩记录
                        perf_record = {
                            'employee_no': emp['employee_no'],
                            'work_date': format_date(current_date),
                            'orders_count': orders,
                            'commission': commission,
                            'is_valid_workday': 1
                        }
                        
                        self.performance_data.append(perf_record)
                    
                    current_date += timedelta(days=1)
                
                progress.update()
    
    def _calculate_expected_events(self):
        """计算预期触发事件（晋级、保级等）"""
        # 这里简化处理：基于业绩数据预测应该触发的事件
        # 实际实现中需要严格按照业务规则计算
        
        for emp in self.employees:
            # 获取该员工的所有业绩记录
            emp_perfs = [p for p in self.performance_data if p['employee_no'] == emp['employee_no']]
            
            if not emp_perfs:
                continue
            
            # 按日期排序
            emp_perfs.sort(key=lambda x: x['work_date'])
            
            # 简化：假设培训期第3个工作日后可能晋级
            if len(emp_perfs) >= 3:
                event = {
                    'employee_no': emp['employee_no'],
                    'event_type': 'promotion_trainee_to_c',
                    'expected_date': emp_perfs[2]['work_date'],
                    'from_status': 'trainee',
                    'to_status': 'C',
                    'reason': '入职满3个工作日'
                }
                self.expected_events.append(event)
            
            # 其他事件的计算逻辑类似，这里省略详细实现
            # 实际应该根据业绩数据精确计算C->B、B->A、保级触发等
    
    def _save_data(self):
        """保存数据到文件"""
        # 确保输出目录存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # 保存员工信息
        with open(EMPLOYEES_CSV, 'w', newline='', encoding='utf-8') as f:
            if self.employees:
                writer = csv.DictWriter(f, fieldnames=self.employees[0].keys())
                writer.writeheader()
                writer.writerows(self.employees)
        
        # 保存业绩数据
        with open(PERFORMANCE_CSV, 'w', newline='', encoding='utf-8') as f:
            if self.performance_data:
                writer = csv.DictWriter(f, fieldnames=self.performance_data[0].keys())
                writer.writeheader()
                writer.writerows(self.performance_data)
        
        # 保存预期事件
        with open(EXPECTED_EVENTS_JSON, 'w', encoding='utf-8') as f:
            json.dump({
                'employees': self.employees,
                'supervisors': self.supervisors,
                'expected_events': self.expected_events
            }, f, ensure_ascii=False, indent=2)
    
    def _print_summary(self):
        """打印数据摘要"""
        print(f"\n📊 数据摘要:")
        print(f"  员工总数: {len(self.employees)}")
        
        # 按类型统计
        type_counts = {}
        for emp in self.employees:
            t = emp['employee_type']
            type_counts[t] = type_counts.get(t, 0) + 1
        
        print(f"\n  员工类型分布:")
        for emp_type, count in type_counts.items():
            print(f"    {emp_type}: {count}人")
        
        print(f"\n  业绩记录: {len(self.performance_data)}条")
        print(f"  预期事件: {len(self.expected_events)}个")
        print(f"\n  主管数量: {len(self.supervisors)}")
        
        print(f"\n📁 输出文件:")
        print(f"  {EMPLOYEES_CSV}")
        print(f"  {PERFORMANCE_CSV}")
        print(f"  {EXPECTED_EVENTS_JSON}")


def main():
    """主函数"""
    generator = DataGenerator()
    generator.generate_all()


if __name__ == '__main__':
    main()

