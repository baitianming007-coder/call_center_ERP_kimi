#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
触发B→A晋升，实际将符合条件的B级员工晋升到A级
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
log_file = Path(LOGS_DIR) / 'trigger_b_to_a.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def trigger_promotions():
    """触发B→A晋升"""
    logger.info("="*70)
    logger.info("开始触发B→A晋升")
    logger.info("="*70)
    
    with app.app_context():
        conn = sqlite3.connect(Path(BASE_DIR) / DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取所有B级员工
        cursor.execute('''
            SELECT id, employee_no, name
            FROM employees
            WHERE employee_no LIKE 'BWINDOW%' AND status = 'B' AND is_active = 1
        ''')
        
        b_employees = cursor.fetchall()
        logger.info(f"\n找到 {len(b_employees)} 名B级员工")
        
        promoted_count = 0
        
        for emp in b_employees:
            emp_id = emp['id']
            emp_no = emp['employee_no']
            
            # 检查晋升资格
            result = check_b_to_a_eligible(emp_id)
            
            if result['eligible']:
                logger.info(f"\n✅ {emp_no} 符合晋升条件，执行晋升...")
                
                # 生成晋升记录
                cursor.execute('''
                    INSERT INTO promotion_confirmations (
                        employee_id, employee_no, employee_name, from_status, to_status,
                        trigger_date, trigger_reason, days_in_status, recent_orders
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (emp_id, emp_no, emp['name'], 'B', 'A',
                      date.today().strftime('%Y-%m-%d'),
                      f"B级{result.get('workdays', 0)}天，最近6天出单{result.get('recent_orders', 0)}单",
                      result.get('workdays', 0),
                      result.get('recent_orders', 0)))
                
                # 更新员工状态
                cursor.execute('UPDATE employees SET status = ? WHERE id = ?', ('A', emp_id))
                
                promoted_count += 1
                logger.info(f"   已晋升到A级")
        
        conn.commit()
        conn.close()
        
        logger.info(f"\n" + "="*70)
        logger.info(f"晋升完成：{promoted_count} 名员工晋升到A级")
        logger.info("="*70)
        
        return promoted_count


def main():
    """主函数"""
    promoted_count = trigger_promotions()
    
    print(f"\n✅ 成功将 {promoted_count} 名B级员工晋升到A级！")
    
    if promoted_count > 0:
        print("\n📋 可以继续测试A级功能：")
        print("   - A级保级挑战")
        print("   - A级薪资计算")
        print("   - A级降级场景")
        return 0
    else:
        print("\n⚠️  没有员工被晋升，请检查数据")
        return 1


if __name__ == '__main__':
    exit(main())

