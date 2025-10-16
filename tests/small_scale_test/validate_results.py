#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果验证器
验证晋升逻辑、保级逻辑、薪资计算的准确性
"""

import sqlite3
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.small_scale_test.config import *
from core.salary_engine import get_or_calculate_salary

# 设置日志
Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)
log_file = Path(LOGS_DIR) / 'validation.log'
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ResultValidator:
    """结果验证器"""
    
    def __init__(self):
        self.db_path = os.path.join(BASE_DIR, DB_PATH)
        self.results = {
            'promotion_validation': {},
            'salary_validation': {},
            'data_consistency': {},
            'issues': []
        }
    
    def validate_promotions(self):
        """验证晋升逻辑"""
        logger.info("验证晋升逻辑...")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 统计各级别人数
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM employees
            WHERE employee_no LIKE 'TEST%'
            GROUP BY status
        ''')
        
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # 统计晋升记录
        cursor.execute('''
            SELECT from_status, to_status, COUNT(*) as count
            FROM promotion_confirmations
            WHERE employee_no LIKE 'TEST%'
            GROUP BY from_status, to_status
        ''')
        
        promotion_counts = {}
        for row in cursor.fetchall():
            key = f"{row['from_status']}→{row['to_status']}"
            promotion_counts[key] = row['count']
        
        conn.close()
        
        self.results['promotion_validation'] = {
            'status_distribution': status_counts,
            'promotion_counts': promotion_counts,
            'total_promotions': sum(promotion_counts.values())
        }
        
        logger.info(f"  员工状态分布: {status_counts}")
        logger.info(f"  晋升记录统计: {promotion_counts}")
        
        return True
    
    def validate_salary_calculations(self):
        """验证薪资计算"""
        logger.info(f"验证薪资计算（抽样{SAMPLE_SIZE_FOR_SALARY_CHECK}名员工）...")
        
        from app import app
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 随机抽样员工
        cursor.execute(f'''
            SELECT id, employee_no, status
            FROM employees
            WHERE employee_no LIKE 'TEST%' AND is_active = 1
            ORDER BY RANDOM()
            LIMIT {SAMPLE_SIZE_FOR_SALARY_CHECK}
        ''')
        
        sample_employees = cursor.fetchall()
        conn.close()
        
        validated_count = 0
        error_count = 0
        total_error = 0
        
        with app.app_context():
            for emp in sample_employees:
                try:
                    # 计算最近一个月的薪资
                    year_month = END_DATE.strftime('%Y-%m')
                    
                    salary_result = get_or_calculate_salary(emp['id'], year_month)
                    
                    if salary_result:
                        validated_count += 1
                    
                except Exception as e:
                    logger.warning(f"  员工 {emp['employee_no']} 薪资计算失败: {str(e)}")
                    error_count += 1
                    self.results['issues'].append({
                        'type': 'salary_calculation_error',
                        'employee_no': emp['employee_no'],
                        'error': str(e)
                    })
        
        accuracy_rate = validated_count / len(sample_employees) * 100 if sample_employees else 0
        
        self.results['salary_validation'] = {
            'sample_size': len(sample_employees),
            'validated': validated_count,
            'errors': error_count,
            'accuracy_rate': round(accuracy_rate, 2)
        }
        
        logger.info(f"  薪资计算准确率: {accuracy_rate:.1f}% ({validated_count}/{len(sample_employees)})")
        
        # 检查是否达标
        if accuracy_rate >= SUCCESS_CRITERIA['salary_accuracy'] * 100:
            logger.info(f"  ✅ 薪资准确率达标 (≥{SUCCESS_CRITERIA['salary_accuracy']*100}%)")
        else:
            logger.warning(f"  ⚠️ 薪资准确率未达标 (<{SUCCESS_CRITERIA['salary_accuracy']*100}%)")
        
        return True
    
    def validate_data_consistency(self):
        """验证数据一致性"""
        logger.info("验证数据一致性...")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 检查员工数据
        cursor.execute("SELECT COUNT(*) as count FROM employees WHERE employee_no LIKE 'TEST%'")
        employee_count = cursor.fetchone()['count']
        
        # 检查业绩数据
        cursor.execute('''
            SELECT COUNT(*) as count FROM performance
            WHERE employee_id IN (SELECT id FROM employees WHERE employee_no LIKE 'TEST%')
        ''')
        performance_count = cursor.fetchone()['count']
        
        # 检查晋升记录
        cursor.execute("SELECT COUNT(*) as count FROM promotion_confirmations WHERE employee_no LIKE 'TEST%'")
        promotion_count = cursor.fetchone()['count']
        
        # 检查用户账号
        cursor.execute('''
            SELECT COUNT(*) as count FROM users
            WHERE employee_id IN (SELECT id FROM employees WHERE employee_no LIKE 'TEST%')
        ''')
        user_count = cursor.fetchone()['count']
        
        # 检查数据完整性
        issues = []
        
        if employee_count != TOTAL_EMPLOYEES:
            issues.append(f"员工数量不匹配: 预期{TOTAL_EMPLOYEES}，实际{employee_count}")
        
        if user_count != employee_count:
            issues.append(f"用户账号不匹配: 员工{employee_count}，账号{user_count}")
        
        conn.close()
        
        self.results['data_consistency'] = {
            'employee_count': employee_count,
            'performance_count': performance_count,
            'promotion_count': promotion_count,
            'user_count': user_count,
            'issues': issues
        }
        
        logger.info(f"  员工数量: {employee_count}/{TOTAL_EMPLOYEES}")
        logger.info(f"  业绩记录: {performance_count}")
        logger.info(f"  晋升记录: {promotion_count}")
        logger.info(f"  用户账号: {user_count}")
        
        if issues:
            for issue in issues:
                logger.warning(f"  ⚠️ {issue}")
                self.results['issues'].append({'type': 'data_consistency', 'issue': issue})
        else:
            logger.info("  ✅ 数据一致性检查通过")
        
        return True
    
    def save_results(self):
        """保存验证结果"""
        output_file = os.path.join(OUTPUT_DIR, 'validation_results.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ 验证结果已保存: {output_file}")
    
    def print_summary(self):
        """打印验证摘要"""
        print("\n" + "="*70)
        print("验证结果摘要")
        print("="*70)
        
        # 晋升验证
        pv = self.results['promotion_validation']
        print(f"\n晋升验证:")
        print(f"  总晋升数: {pv['total_promotions']}")
        for status, count in pv['status_distribution'].items():
            print(f"  {status}级: {count}人")
        
        # 薪资验证
        sv = self.results['salary_validation']
        print(f"\n薪资验证:")
        print(f"  抽样数量: {sv['sample_size']}")
        print(f"  验证成功: {sv['validated']}")
        print(f"  准确率: {sv['accuracy_rate']}%")
        
        # 数据一致性
        dc = self.results['data_consistency']
        print(f"\n数据一致性:")
        print(f"  员工: {dc['employee_count']}")
        print(f"  业绩记录: {dc['performance_count']}")
        print(f"  晋升记录: {dc['promotion_count']}")
        
        # 问题汇总
        if self.results['issues']:
            print(f"\n⚠️ 发现问题: {len(self.results['issues'])} 个")
            for issue in self.results['issues'][:5]:
                print(f"  - {issue.get('type')}: {issue.get('error') or issue.get('issue')}")
        else:
            print(f"\n✅ 未发现问题")
        
        print("="*70 + "\n")
    
    def run(self):
        """执行完整验证流程"""
        logger.info("="*70)
        logger.info("开始验证测试结果")
        logger.info("="*70)
        
        try:
            self.validate_promotions()
            self.validate_salary_calculations()
            self.validate_data_consistency()
            self.save_results()
            self.print_summary()
            
            logger.info("✓ 验证完成")
            return True
        except Exception as e:
            logger.error(f"✗ 验证失败: {str(e)}", exc_info=True)
            return False


def main():
    """主函数"""
    validator = ResultValidator()
    success = validator.run()
    
    if success:
        print("\n✅ 结果验证完成！")
        return 0
    else:
        print("\n❌ 结果验证失败！")
        return 1


if __name__ == '__main__':
    exit(main())

