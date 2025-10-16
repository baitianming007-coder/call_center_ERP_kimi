#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试B→A晋升功能
"""

import sqlite3
import logging
from datetime import date, datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.small_scale_test.config import DB_PATH, BASE_DIR, LOGS_DIR
from core.promotion_engine import check_b_to_a_eligible
from app import app

# 设置日志
Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)
log_file = Path(LOGS_DIR) / 'test_b_to_a.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BToAPromotionTester:
    """B→A晋升测试器"""
    
    def __init__(self):
        self.db_path = Path(BASE_DIR) / DB_PATH
        self.results = {
            'total_b_employees': 0,
            'eligible_for_promotion': [],
            'not_eligible': [],
            'errors': []
        }
    
    def get_b_employees(self):
        """获取所有B级员工"""
        logger.info("获取B级员工列表...")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, employee_no, name, status, join_date
            FROM employees
            WHERE employee_no LIKE 'BWINDOW%' AND status = 'B' AND is_active = 1
        ''')
        
        employees = cursor.fetchall()
        conn.close()
        
        logger.info(f"  找到 {len(employees)} 名B级员工")
        return [dict(emp) for emp in employees]
    
    def check_promotion_eligibility(self, employee):
        """检查单个员工的晋升资格"""
        emp_id = employee['id']
        emp_no = employee['employee_no']
        
        logger.info(f"\n检查员工 {emp_no} 的晋升资格...")
        
        try:
            with app.app_context():
                result = check_b_to_a_eligible(emp_id)
            
            if result['eligible']:
                logger.info(f"  ✅ 符合晋升条件")
                logger.info(f"     - B级天数: {result.get('workdays', 'N/A')}")
                logger.info(f"     - 最近6天出单: {result.get('recent_orders', 'N/A')}")
                
                self.results['eligible_for_promotion'].append({
                    'employee_no': emp_no,
                    'name': employee['name'],
                    'workdays': result.get('workdays', 0),
                    'recent_orders': result.get('recent_orders', 0),
                    'reason': result.get('reason', '')
                })
            else:
                logger.info(f"  ❌ 不符合晋升条件")
                logger.info(f"     原因: {result.get('reason', 'N/A')}")
                
                self.results['not_eligible'].append({
                    'employee_no': emp_no,
                    'name': employee['name'],
                    'reason': result.get('reason', '')
                })
            
            return result['eligible']
            
        except Exception as e:
            logger.error(f"  ❌ 检查失败: {str(e)}")
            self.results['errors'].append({
                'employee_no': emp_no,
                'error': str(e)
            })
            return False
    
    def verify_promotion_records(self):
        """验证晋升记录是否生成"""
        logger.info("\n验证晋升记录...")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询B→A晋升记录
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM promotion_confirmations
            WHERE employee_no LIKE 'BWINDOW%' 
            AND from_status = 'B' AND to_status = 'A'
        ''')
        
        promotion_count = cursor.fetchone()['count']
        conn.close()
        
        logger.info(f"  数据库中B→A晋升记录: {promotion_count} 条")
        return promotion_count
    
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*70)
        print("B→A晋升测试摘要")
        print("="*70)
        print(f"\nB级员工总数: {self.results['total_b_employees']}")
        print(f"符合晋升条件: {len(self.results['eligible_for_promotion'])} 人")
        print(f"不符合条件: {len(self.results['not_eligible'])} 人")
        print(f"检查失败: {len(self.results['errors'])} 人")
        
        if self.results['eligible_for_promotion']:
            print("\n✅ 符合晋升条件的员工:")
            for emp in self.results['eligible_for_promotion']:
                print(f"  - {emp['employee_no']}: B级{emp['workdays']}天, 最近6天出单{emp['recent_orders']}单")
        
        if self.results['not_eligible']:
            print("\n❌ 不符合条件的员工（前5名）:")
            for emp in self.results['not_eligible'][:5]:
                print(f"  - {emp['employee_no']}: {emp['reason']}")
        
        if self.results['errors']:
            print("\n⚠️  检查失败的员工:")
            for emp in self.results['errors']:
                print(f"  - {emp['employee_no']}: {emp['error']}")
        
        print("="*70 + "\n")
    
    def run(self):
        """执行完整测试"""
        logger.info("="*70)
        logger.info("开始B→A晋升测试")
        logger.info("="*70)
        
        try:
            # 获取B级员工
            b_employees = self.get_b_employees()
            self.results['total_b_employees'] = len(b_employees)
            
            if not b_employees:
                logger.error("没有找到B级员工，测试终止")
                return False
            
            # 检查每个员工的晋升资格
            for employee in b_employees:
                self.check_promotion_eligibility(employee)
            
            # 验证晋升记录
            promotion_count = self.verify_promotion_records()
            
            # 打印摘要
            self.print_summary()
            
            # 判断测试是否成功
            eligible_count = len(self.results['eligible_for_promotion'])
            
            logger.info("\n" + "="*70)
            logger.info("测试结果")
            logger.info("="*70)
            
            if eligible_count > 0:
                logger.info(f"✅ 测试成功：发现 {eligible_count} 名员工符合B→A晋升条件")
                return True
            else:
                logger.warning("⚠️  警告：没有员工符合B→A晋升条件")
                logger.warning("   可能原因：")
                logger.warning("   1. B级天数不在6-9天窗口内")
                logger.warning("   2. 最近6天出单<12单")
                logger.warning("   3. 数据生成有问题")
                return False
            
        except Exception as e:
            logger.error(f"测试失败: {str(e)}", exc_info=True)
            return False


def main():
    """主函数"""
    tester = BToAPromotionTester()
    success = tester.run()
    
    if success:
        print("\n✅ B→A晋升测试完成！")
        return 0
    else:
        print("\n❌ B→A晋升测试存在问题")
        return 1


if __name__ == '__main__':
    exit(main())

