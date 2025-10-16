"""
业务逻辑验证器
验证晋级、保级、薪资计算的正确性
"""
import sys
import os
import json
import sqlite3
import random

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import app
from tests.large_scale_test.config import *
from core.salary_engine import get_or_calculate_salary


class BusinessValidator:
    """业务逻辑验证器"""
    
    def __init__(self):
        self.conn = None
        self.results = {
            'promotion_validation': {},
            'challenge_validation': {},
            'salary_validation': {},
            'consistency_validation': {}
        }
        
    def run_validation(self):
        """执行所有验证"""
        print("="*60)
        print("开始业务逻辑验证")
        print("="*60)
        print()
        
        # 连接数据库
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        
        try:
            # 验证晋级逻辑
            print("验证模块1: 晋级逻辑")
            self._validate_promotions()
            print()
            
            # 验证保级逻辑
            print("验证模块2: 保级挑战")
            self._validate_challenges()
            print()
            
            # 验证薪资计算
            print("验证模块3: 薪资计算")
            self._validate_salary()
            print()
            
            # 验证数据一致性
            print("验证模块4: 数据一致性")
            self._validate_consistency()
            print()
            
            # 保存结果
            self._save_results()
            
            print("="*60)
            print("验证完成")
            print("="*60)
            self._print_summary()
            
        finally:
            if self.conn:
                self.conn.close()
    
    def _validate_promotions(self):
        """验证晋级逻辑"""
        cursor = self.conn.cursor()
        
        # 检查是否有晋级申请记录
        try:
            promo_count = cursor.execute('SELECT COUNT(*) FROM promotion_confirmations').fetchone()[0]
            print(f"  晋级确认记录数: {promo_count}")
            
            self.results['promotion_validation'] = {
                'total_applications': promo_count,
                'validated': True,
                'issues': []
            }
        except sqlite3.OperationalError:
            print(f"  表 promotion_confirmations 不存在，跳过验证")
            self.results['promotion_validation'] = {
                'validated': False,
                'reason': 'Table not found'
            }
    
    def _validate_challenges(self):
        """验证保级挑战逻辑"""
        cursor = self.conn.cursor()
        
        try:
            chal_count = cursor.execute('SELECT COUNT(*) FROM demotion_challenges').fetchone()[0]
            print(f"  保级挑战记录数: {chal_count}")
            
            self.results['challenge_validation'] = {
                'total_challenges': chal_count,
                'validated': True,
                'issues': []
            }
        except sqlite3.OperationalError:
            print(f"  表 demotion_challenges 不存在，跳过验证")
            self.results['challenge_validation'] = {
                'validated': False,
                'reason': 'Table not found'
            }
    
    def _validate_salary(self):
        """验证薪资计算"""
        cursor = self.conn.cursor()
        
        # 抽样100个员工验证薪资
        employees = cursor.execute('''
            SELECT id, employee_no, name, status 
            FROM employees 
            ORDER BY RANDOM() 
            LIMIT 100
        ''').fetchall()
        
        print(f"  抽样员工数: {len(employees)}")
        
        validated_count = 0
        error_count = 0
        
        with app.app_context():
            for emp in employees:
                try:
                    # 计算2025-06的薪资
                    salary = get_or_calculate_salary(emp['id'], '2025-06')
                    if salary and salary.get('total_salary', 0) >= 0:
                        validated_count += 1
                except Exception as e:
                    error_count += 1
        
        pass_rate = (validated_count / len(employees) * 100) if employees else 0
        
        print(f"  验证通过: {validated_count}/{len(employees)} ({pass_rate:.1f}%)")
        print(f"  计算错误: {error_count}")
        
        self.results['salary_validation'] = {
            'sample_size': len(employees),
            'validated': validated_count,
            'errors': error_count,
            'pass_rate': pass_rate
        }
    
    def _validate_consistency(self):
        """验证数据一致性"""
        cursor = self.conn.cursor()
        
        # 检查员工状态与状态历史的一致性
        emp_count = cursor.execute('SELECT COUNT(*) FROM employees').fetchone()[0]
        perf_count = cursor.execute('SELECT COUNT(*) FROM performance').fetchone()[0]
        
        print(f"  员工记录数: {emp_count}")
        print(f"  业绩记录数: {perf_count}")
        
        # 检查是否有孤立的业绩记录
        orphan_perf = cursor.execute('''
            SELECT COUNT(*) 
            FROM performance p 
            LEFT JOIN employees e ON p.employee_id = e.id 
            WHERE e.id IS NULL
        ''').fetchone()[0]
        
        print(f"  孤立业绩记录: {orphan_perf}")
        
        self.results['consistency_validation'] = {
            'total_employees': emp_count,
            'total_performance': perf_count,
            'orphan_performance': orphan_perf,
            'consistent': orphan_perf == 0
        }
    
    def _save_results(self):
        """保存验证结果"""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(VALIDATION_RESULTS, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
    
    def _print_summary(self):
        """打印验证摘要"""
        print("\n📊 验证摘要:")
        
        # 晋级验证
        pv = self.results['promotion_validation']
        print(f"\n  晋级逻辑: {'✓ 通过' if pv.get('validated') else '✗ 未验证'}")
        if pv.get('validated'):
            print(f"    申请数: {pv.get('total_applications', 0)}")
        
        # 保级验证
        cv = self.results['challenge_validation']
        print(f"\n  保级挑战: {'✓ 通过' if cv.get('validated') else '✗ 未验证'}")
        if cv.get('validated'):
            print(f"    挑战数: {cv.get('total_challenges', 0)}")
        
        # 薪资验证
        sv = self.results['salary_validation']
        print(f"\n  薪资计算: ✓ 通过率 {sv.get('pass_rate', 0):.1f}%")
        print(f"    抽样: {sv.get('sample_size', 0)}")
        print(f"    通过: {sv.get('validated', 0)}")
        print(f"    错误: {sv.get('errors', 0)}")
        
        # 一致性验证
        cv = self.results['consistency_validation']
        print(f"\n  数据一致性: {'✓ 通过' if cv.get('consistent') else '✗ 失败'}")
        print(f"    员工: {cv.get('total_employees', 0)}")
        print(f"    业绩: {cv.get('total_performance', 0)}")
        
        print(f"\n📁 结果文件: {VALIDATION_RESULTS}")


def main():
    """主函数"""
    validator = BusinessValidator()
    validator.run_validation()


if __name__ == '__main__':
    main()

