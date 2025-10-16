#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
业务逻辑触发器
模拟系统运行，触发晋升、保级等业务逻辑
"""

import sqlite3
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入配置和核心模块
from tests.small_scale_test.config import *
from core.database import get_db
from app import app

# 确保日志目录存在
Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)

# 设置日志
log_file = Path(LOGS_DIR) / 'trigger.log'
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


class BusinessLogicTrigger:
    """业务逻辑触发器"""
    
    def __init__(self):
        self.db_path = os.path.join(BASE_DIR, DB_PATH)
        self.results = {
            'promotions': {
                'trainee_to_c': [],
                'c_to_b': [],
                'b_to_a': []
            },
            'challenges': [],
            'errors': []
        }
    
    def check_trainee_promotion(self):
        """检查实习生转正条件"""
        logger.info("检查实习生转正条件...")
        
        with app.app_context():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取所有实习生
            cursor.execute('''
                SELECT id, employee_no, name, join_date, status
                FROM employees
                WHERE employee_no LIKE 'TEST%' AND status = 'trainee' AND is_active = 1
            ''')
            
            trainees = cursor.fetchall()
            logger.info(f"  找到 {len(trainees)} 名实习生")
            
            promoted_count = 0
            failed_count = 0
            
            for trainee in trainees:
                try:
                    emp_id = trainee['id']
                    emp_no = trainee['employee_no']
                    join_date = datetime.strptime(trainee['join_date'], '%Y-%m-%d').date()
                    
                    # 检查工作天数
                    cursor.execute('''
                        SELECT COUNT(*) as workdays
                        FROM performance
                        WHERE employee_id = ? AND is_valid_workday = 1
                    ''', (emp_id,))
                    workdays = cursor.fetchone()['workdays']
                    
                    if workdays < PROMOTION_RULES['trainee_to_c']['min_workdays']:
                        continue
                    
                    # 检查出勤率
                    cursor.execute('''
                        SELECT COUNT(*) as attended
                        FROM performance
                        WHERE employee_id = ? AND orders_count >= 0
                    ''', (emp_id,))
                    attended = cursor.fetchone()['attended']
                    attendance_rate = attended / workdays if workdays > 0 else 0
                    
                    if attendance_rate < PROMOTION_RULES['trainee_to_c']['min_attendance_rate']:
                        continue
                    
                    # 检查连续出单天数
                    cursor.execute('''
                        SELECT work_date, orders_count
                        FROM performance
                        WHERE employee_id = ?
                        ORDER BY work_date
                    ''', (emp_id,))
                    
                    records = cursor.fetchall()
                    consecutive_days = 0
                    max_consecutive = 0
                    
                    for record in records:
                        if record['orders_count'] > 0:
                            consecutive_days += 1
                            max_consecutive = max(max_consecutive, consecutive_days)
                        else:
                            consecutive_days = 0
                    
                    if max_consecutive < PROMOTION_RULES['trainee_to_c']['consecutive_order_days']:
                        continue
                    
                    # 符合转正条件，生成转正记录
                    promotion_date = (join_date + timedelta(days=PROMOTION_RULES['trainee_to_c']['min_workdays'])).strftime('%Y-%m-%d')
                    
                    cursor.execute('''
                        INSERT INTO promotion_confirmations (
                            employee_id, employee_no, employee_name, from_status, to_status, 
                            trigger_date, trigger_reason, days_in_status, recent_orders
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (emp_id, emp_no, trainee['name'], 'trainee', 'C', promotion_date,
                          f'工作{workdays}天，出勤率{attendance_rate*100:.1f}%，连续出单{max_consecutive}天',
                          workdays, max_consecutive))
                    
                    # 更新员工状态
                    cursor.execute('''
                        UPDATE employees SET status = 'C' WHERE id = ?
                    ''', (emp_id,))
                    
                    self.results['promotions']['trainee_to_c'].append({
                        'employee_no': emp_no,
                        'workdays': workdays,
                        'attendance_rate': round(attendance_rate * 100, 2),
                        'consecutive_days': max_consecutive
                    })
                    
                    promoted_count += 1
                    
                except Exception as e:
                    logger.error(f"  处理员工 {trainee['employee_no']} 时出错: {str(e)}")
                    self.results['errors'].append({
                        'type': 'trainee_promotion',
                        'employee_no': trainee['employee_no'],
                        'error': str(e)
                    })
                    failed_count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"✓ 转正检查完成: {promoted_count} 人转正, {failed_count} 人失败")
            return promoted_count
    
    def check_c_to_b_promotion(self):
        """检查C级晋升B级"""
        logger.info("检查C级晋升B级...")
        
        with app.app_context():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取所有C级员工
            cursor.execute('''
                SELECT id, employee_no, name, join_date, status
                FROM employees
                WHERE employee_no LIKE 'TEST%' AND status = 'C' AND is_active = 1
            ''')
            
            c_employees = cursor.fetchall()
            logger.info(f"  找到 {len(c_employees)} 名C级员工")
            
            promoted_count = 0
            
            for emp in c_employees:
                try:
                    emp_id = emp['id']
                    
                    # 检查C级工作天数
                    cursor.execute('''
                        SELECT trigger_date FROM promotion_confirmations
                        WHERE employee_id = ? AND to_status = 'C'
                        ORDER BY trigger_date DESC LIMIT 1
                    ''', (emp_id,))
                    
                    promotion_record = cursor.fetchone()
                    if not promotion_record:
                        continue
                    
                    c_start_date = datetime.strptime(promotion_record['trigger_date'], '%Y-%m-%d').date()
                    
                    cursor.execute('''
                        SELECT COUNT(*) as workdays
                        FROM performance
                        WHERE employee_id = ? AND work_date >= ?
                    ''', (emp_id, c_start_date.strftime('%Y-%m-%d')))
                    
                    c_workdays = cursor.fetchone()['workdays']
                    
                    if c_workdays < PROMOTION_RULES['c_to_b']['min_workdays']:
                        continue
                    
                    # 检查月单量（取最近一个完整月）
                    cursor.execute('''
                        SELECT strftime('%Y-%m', work_date) as month, SUM(orders_count) as total_orders
                        FROM performance
                        WHERE employee_id = ? AND work_date >= ?
                        GROUP BY month
                        ORDER BY month DESC
                        LIMIT 1
                    ''', (emp_id, c_start_date.strftime('%Y-%m-%d')))
                    
                    monthly = cursor.fetchone()
                    if not monthly or monthly['total_orders'] < PROMOTION_RULES['c_to_b']['min_monthly_orders']:
                        continue
                    
                    # 符合晋升条件
                    promotion_date = datetime.now().strftime('%Y-%m-%d')
                    
                    cursor.execute('''
                        INSERT INTO promotion_confirmations (
                            employee_id, employee_no, employee_name, from_status, to_status, 
                            trigger_date, trigger_reason, days_in_status, recent_orders
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (emp_id, emp['employee_no'], emp['name'], 'C', 'B', promotion_date,
                          f'月单{monthly["total_orders"]}，C级{c_workdays}天',
                          c_workdays, monthly["total_orders"]))
                    
                    cursor.execute('UPDATE employees SET status = "B" WHERE id = ?', (emp_id,))
                    
                    self.results['promotions']['c_to_b'].append({
                        'employee_no': emp['employee_no'],
                        'c_workdays': c_workdays,
                        'monthly_orders': monthly['total_orders']
                    })
                    
                    promoted_count += 1
                    
                except Exception as e:
                    logger.error(f"  处理员工 {emp['employee_no']} 时出错: {str(e)}")
                    self.results['errors'].append({
                        'type': 'c_to_b_promotion',
                        'employee_no': emp['employee_no'],
                        'error': str(e)
                    })
            
            conn.commit()
            conn.close()
            
            logger.info(f"✓ C→B晋升检查完成: {promoted_count} 人晋升")
            return promoted_count
    
    def check_b_to_a_promotion(self):
        """检查B级晋升A级"""
        logger.info("检查B级晋升A级...")
        
        with app.app_context():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, employee_no, name, status
                FROM employees
                WHERE employee_no LIKE 'TEST%' AND status = 'B' AND is_active = 1
            ''')
            
            b_employees = cursor.fetchall()
            logger.info(f"  找到 {len(b_employees)} 名B级员工")
            
            promoted_count = 0
            
            for emp in b_employees:
                try:
                    emp_id = emp['id']
                    
                    # 检查B级工作天数
                    cursor.execute('''
                        SELECT trigger_date FROM promotion_confirmations
                        WHERE employee_id = ? AND to_status = 'B'
                        ORDER BY trigger_date DESC LIMIT 1
                    ''', (emp_id,))
                    
                    promotion_record = cursor.fetchone()
                    if not promotion_record:
                        continue
                    
                    b_start_date = datetime.strptime(promotion_record['trigger_date'], '%Y-%m-%d').date()
                    
                    cursor.execute('''
                        SELECT COUNT(*) as workdays
                        FROM performance
                        WHERE employee_id = ? AND work_date >= ?
                    ''', (emp_id, b_start_date.strftime('%Y-%m-%d')))
                    
                    b_workdays = cursor.fetchone()['workdays']
                    
                    if b_workdays < PROMOTION_RULES['b_to_a']['min_workdays']:
                        continue
                    
                    # 检查月单量
                    cursor.execute('''
                        SELECT strftime('%Y-%m', work_date) as month, SUM(orders_count) as total_orders
                        FROM performance
                        WHERE employee_id = ? AND work_date >= ?
                        GROUP BY month
                        ORDER BY month DESC
                        LIMIT 1
                    ''', (emp_id, b_start_date.strftime('%Y-%m-%d')))
                    
                    monthly = cursor.fetchone()
                    if not monthly or monthly['total_orders'] < PROMOTION_RULES['b_to_a']['min_monthly_orders']:
                        continue
                    
                    # 符合晋升条件
                    promotion_date = datetime.now().strftime('%Y-%m-%d')
                    
                    cursor.execute('''
                        INSERT INTO promotion_confirmations (
                            employee_id, employee_no, employee_name, from_status, to_status, 
                            trigger_date, trigger_reason, days_in_status, recent_orders
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (emp_id, emp['employee_no'], emp['name'], 'B', 'A', promotion_date,
                          f'月单{monthly["total_orders"]}，B级{b_workdays}天',
                          b_workdays, monthly["total_orders"]))
                    
                    cursor.execute('UPDATE employees SET status = "A" WHERE id = ?', (emp_id,))
                    
                    self.results['promotions']['b_to_a'].append({
                        'employee_no': emp['employee_no'],
                        'b_workdays': b_workdays,
                        'monthly_orders': monthly['total_orders']
                    })
                    
                    promoted_count += 1
                    
                except Exception as e:
                    logger.error(f"  处理员工 {emp['employee_no']} 时出错: {str(e)}")
                    self.results['errors'].append({
                        'type': 'b_to_a_promotion',
                        'employee_no': emp['employee_no'],
                        'error': str(e)
                    })
            
            conn.commit()
            conn.close()
            
            logger.info(f"✓ B→A晋升检查完成: {promoted_count} 人晋升")
            return promoted_count
    
    def check_a_level_challenges(self):
        """检查A级保级挑战"""
        logger.info("检查A级保级挑战...")
        
        with app.app_context():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, employee_no, name, status
                FROM employees
                WHERE employee_no LIKE 'TEST%' AND status = 'A' AND is_active = 1
            ''')
            
            a_employees = cursor.fetchall()
            logger.info(f"  找到 {len(a_employees)} 名A级员工")
            
            challenge_count = 0
            
            for emp in a_employees:
                try:
                    emp_id = emp['id']
                    
                    # 检查最近一个月的单量
                    cursor.execute('''
                        SELECT strftime('%Y-%m', work_date) as month, SUM(orders_count) as total_orders
                        FROM performance
                        WHERE employee_id = ?
                        GROUP BY month
                        ORDER BY month DESC
                        LIMIT 1
                    ''', (emp_id,))
                    
                    monthly = cursor.fetchone()
                    if not monthly:
                        continue
                    
                    if monthly['total_orders'] < DEMOTION_RULES['a_challenge_threshold']:
                        # 触发保级挑战
                        challenge_month = monthly['month']
                        trigger_date = datetime.now().strftime('%Y-%m-%d')
                        
                        cursor.execute('''
                            INSERT INTO demotion_challenges (
                                employee_id, employee_no, employee_name, year_month, 
                                trigger_date, trigger_orders
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        ''', (emp_id, emp['employee_no'], emp['name'], challenge_month,
                              trigger_date, monthly['total_orders']))
                        
                        self.results['challenges'].append({
                            'employee_no': emp['employee_no'],
                            'month': challenge_month,
                            'orders': monthly['total_orders']
                        })
                        
                        challenge_count += 1
                    
                except Exception as e:
                    logger.error(f"  处理员工 {emp['employee_no']} 时出错: {str(e)}")
                    self.results['errors'].append({
                        'type': 'a_challenge',
                        'employee_no': emp['employee_no'],
                        'error': str(e)
                    })
            
            conn.commit()
            conn.close()
            
            logger.info(f"✓ A级保级检查完成: {challenge_count} 人触发挑战")
            return challenge_count
    
    def save_results(self):
        """保存触发结果"""
        output_file = os.path.join(OUTPUT_DIR, 'trigger_results.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ 结果已保存: {output_file}")
    
    def print_summary(self):
        """打印摘要"""
        print("\n" + "="*70)
        print("业务逻辑触发摘要")
        print("="*70)
        print(f"\n晋升统计:")
        print(f"  实习生→C级: {len(self.results['promotions']['trainee_to_c'])} 人")
        print(f"  C级→B级: {len(self.results['promotions']['c_to_b'])} 人")
        print(f"  B级→A级: {len(self.results['promotions']['b_to_a'])} 人")
        print(f"\n保级挑战:")
        print(f"  触发人数: {len(self.results['challenges'])} 人")
        print(f"\n错误统计:")
        print(f"  错误数量: {len(self.results['errors'])} 个")
        
        if self.results['errors']:
            print(f"\n⚠️  发现错误:")
            for error in self.results['errors'][:5]:  # 只显示前5个
                print(f"  - {error['type']}: {error['employee_no']} - {error['error']}")
        
        print("="*70 + "\n")
    
    def run(self):
        """执行完整流程"""
        start_time = datetime.now()
        logger.info("="*70)
        logger.info("开始触发业务逻辑")
        logger.info("="*70)
        
        try:
            # 步骤1: 检查实习生转正
            self.check_trainee_promotion()
            
            # 步骤2: 检查C→B晋升
            self.check_c_to_b_promotion()
            
            # 步骤3: 检查B→A晋升
            self.check_b_to_a_promotion()
            
            # 步骤4: 检查A级保级
            self.check_a_level_challenges()
            
            # 步骤5: 保存结果
            self.save_results()
            
            # 步骤6: 打印摘要
            self.print_summary()
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✓ 业务逻辑触发完成，耗时: {elapsed:.1f}秒")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 触发过程出错: {str(e)}", exc_info=True)
            return False


def main():
    """主函数"""
    trigger = BusinessLogicTrigger()
    success = trigger.run()
    
    if success:
        print("\n✅ 业务逻辑触发成功！")
        return 0
    else:
        print("\n❌ 业务逻辑触发失败！")
        return 1


if __name__ == '__main__':
    exit(main())

