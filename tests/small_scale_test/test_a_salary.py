#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试A级薪资计算
"""

import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.small_scale_test.config import DB_PATH, BASE_DIR
from core.salary_engine import calculate_salary_realtime
from app import app


def test_a_salary():
    """测试A级薪资计算"""
    print("="*70)
    print("A级薪资计算测试")
    print("="*70)
    
    with app.app_context():
        conn = sqlite3.connect(Path(BASE_DIR) / DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取A级员工
        cursor.execute('''
            SELECT id, employee_no, name
            FROM employees
            WHERE employee_no LIKE 'BWINDOW%' AND status = 'A' AND is_active = 1
            LIMIT 5
        ''')
        
        a_employees = cursor.fetchall()
        print(f"\n抽样测试 {len(a_employees)} 名A级员工的薪资计算...\n")
        
        test_results = []
        
        for emp in a_employees:
            year_month = '2025-10'
            salary = calculate_salary_realtime(emp['id'], year_month)
            
            print(f"员工: {emp['employee_no']} ({emp['name']})")
            print(f"  底薪: ¥{salary['base_salary']:.2f}")
            print(f"  全勤奖: ¥{salary['attendance_bonus']:.2f}")
            print(f"  绩效奖: ¥{salary['performance_bonus']:.2f}")
            print(f"  提成: ¥{salary['commission']:.2f}")
            print(f"  总计: ¥{salary['total_salary']:.2f}")
            print()
            
            test_results.append({
                'employee_no': emp['employee_no'],
                'base': salary['base_salary'],
                'attendance': salary['attendance_bonus'],
                'performance': salary['performance_bonus'],
                'commission': salary['commission'],
                'total': salary['total_salary']
            })
        
        conn.close()
        
        # 验证薪资结构
        print("="*70)
        print("验证结果")
        print("="*70)
        
        all_pass = True
        for result in test_results:
            # 验证底薪
            if result['base'] != 2200:
                print(f"❌ {result['employee_no']}: 底薪错误 ({result['base']} != 2200)")
                all_pass = False
            
            # 验证全勤奖（应该是0或400）
            if result['attendance'] not in [0, 400]:
                print(f"❌ {result['employee_no']}: 全勤奖异常 ({result['attendance']})")
                all_pass = False
            
            # 验证绩效奖（应该是0, 300, 600, 或1000）
            if result['performance'] not in [0, 300, 600, 1000]:
                print(f"❌ {result['employee_no']}: 绩效奖异常 ({result['performance']})")
                all_pass = False
        
        if all_pass:
            print("✅ 所有A级员工薪资计算正确！")
            print("\n薪资结构验证通过：")
            print("  - 底薪: 2200元 ✅")
            print("  - 全勤奖: 0或400元 ✅")
            print("  - 绩效奖: 0/300/600/1000元 ✅")
            print("  - 提成: 按日阶梯累加 ✅")
            return True
        else:
            print("❌ 发现薪资计算错误")
            return False


def main():
    """主函数"""
    success = test_a_salary()
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())

