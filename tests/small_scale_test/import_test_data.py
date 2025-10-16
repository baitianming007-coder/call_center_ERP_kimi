#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据导入器
将生成的测试数据导入到数据库
"""

import csv
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入配置
from tests.small_scale_test.config import *
from core.auth import hash_password

# 确保日志目录存在
Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)

# 设置日志
log_file = Path(LOGS_DIR) / 'import.log'
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


class TestDataImporter:
    """测试数据导入器"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.join(BASE_DIR, DB_PATH)
        self.conn = None
        self.cursor = None
        self.stats = {
            'employees_imported': 0,
            'employees_failed': 0,
            'performance_imported': 0,
            'performance_failed': 0,
            'users_created': 0
        }
    
    def connect(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            logger.info(f"✓ 已连接数据库: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"✗ 数据库连接失败: {str(e)}")
            return False
    
    def clear_test_data(self):
        """清除测试数据"""
        logger.info("清除旧的测试数据...")
        
        try:
            # 清除TEST开头的员工相关数据
            self.cursor.execute('''
                DELETE FROM performance 
                WHERE employee_id IN (
                    SELECT id FROM employees WHERE employee_no LIKE 'TEST%'
                )
            ''')
            
            self.cursor.execute('''
                DELETE FROM users 
                WHERE employee_id IN (
                    SELECT id FROM employees WHERE employee_no LIKE 'TEST%'
                )
            ''')
            
            self.cursor.execute("DELETE FROM employees WHERE employee_no LIKE 'TEST%'")
            
            self.conn.commit()
            logger.info("✓ 旧数据清除完成")
            return True
            
        except Exception as e:
            logger.error(f"✗ 清除数据失败: {str(e)}")
            self.conn.rollback()
            return False
    
    def import_employees(self):
        """导入员工数据"""
        logger.info("开始导入员工数据...")
        
        csv_file = os.path.join(OUTPUT_DIR, 'test_employees.csv')
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    try:
                        self.cursor.execute('''
                            INSERT INTO employees (
                                employee_no, name, status, join_date, team, is_active
                            ) VALUES (?, ?, ?, ?, ?, 1)
                        ''', (
                            row['employee_no'],
                            row['name'],
                            row['status'],
                            row['join_date'],
                            row['team']
                        ))
                        
                        self.stats['employees_imported'] += 1
                        
                    except Exception as e:
                        logger.warning(f"导入员工 {row['employee_no']} 失败: {str(e)}")
                        self.stats['employees_failed'] += 1
            
            self.conn.commit()
            logger.info(f"✓ 员工导入完成: 成功 {self.stats['employees_imported']}, 失败 {self.stats['employees_failed']}")
            return True
            
        except Exception as e:
            logger.error(f"✗ 员工数据导入失败: {str(e)}")
            self.conn.rollback()
            return False
    
    def import_performance(self):
        """导入业绩数据"""
        logger.info("开始导入业绩数据...")
        
        csv_file = os.path.join(OUTPUT_DIR, 'test_performance.csv')
        
        # 先获取员工ID映射
        self.cursor.execute("SELECT id, employee_no FROM employees WHERE employee_no LIKE 'TEST%'")
        emp_mapping = {row[1]: row[0] for row in self.cursor.fetchall()}
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                batch = []
                batch_size = 1000
                
                for row in reader:
                    emp_id = emp_mapping.get(row['employee_no'])
                    if not emp_id:
                        self.stats['performance_failed'] += 1
                        continue
                    
                    # 只导入出勤的记录（attendance=1）
                    # 不出勤的日子不创建记录
                    if int(row['attendance']) == 0:
                        continue
                    
                    # 计算提成
                    orders_count = int(row['orders_count'])
                    commission = orders_count * 15  # 简化：统一15元/单
                    
                    batch.append((
                        emp_id,
                        row['work_date'],
                        orders_count,
                        commission,
                        1  # is_valid_workday
                    ))
                    
                    # 批量插入
                    if len(batch) >= batch_size:
                        try:
                            self.cursor.executemany('''
                                INSERT INTO performance (
                                    employee_id, work_date, orders_count, 
                                    commission, is_valid_workday
                                ) VALUES (?, ?, ?, ?, ?)
                            ''', batch)
                            self.stats['performance_imported'] += len(batch)
                            batch = []
                            
                            if self.stats['performance_imported'] % 5000 == 0:
                                logger.info(f"  已导入 {self.stats['performance_imported']} 条业绩记录...")
                        except Exception as e:
                            logger.warning(f"批量插入失败: {str(e)}")
                            self.stats['performance_failed'] += len(batch)
                            batch = []
                
                # 插入剩余数据
                if batch:
                    try:
                        self.cursor.executemany('''
                            INSERT INTO performance (
                                employee_id, work_date, orders_count, 
                                commission, is_valid_workday
                            ) VALUES (?, ?, ?, ?, ?)
                        ''', batch)
                        self.stats['performance_imported'] += len(batch)
                    except Exception as e:
                        logger.warning(f"最后批次插入失败: {str(e)}")
                        self.stats['performance_failed'] += len(batch)
            
            self.conn.commit()
            logger.info(f"✓ 业绩导入完成: 成功 {self.stats['performance_imported']}, 失败 {self.stats['performance_failed']}")
            return True
            
        except Exception as e:
            logger.error(f"✗ 业绩数据导入失败: {str(e)}")
            self.conn.rollback()
            return False
    
    def create_user_accounts(self):
        """为测试员工创建登录账号"""
        logger.info("创建用户账号...")
        
        # 获取所有测试员工
        self.cursor.execute("SELECT id, employee_no FROM employees WHERE employee_no LIKE 'TEST%'")
        employees = self.cursor.fetchall()
        
        # 统一密码
        password = hash_password('123456')
        
        try:
            for emp_id, emp_no in employees:
                username = emp_no.lower()
                
                try:
                    self.cursor.execute('''
                        INSERT INTO users (username, password, role, employee_id)
                        VALUES (?, ?, 'employee', ?)
                    ''', (username, password, emp_id))
                    self.stats['users_created'] += 1
                except Exception as e:
                    logger.warning(f"创建账号 {username} 失败: {str(e)}")
            
            self.conn.commit()
            logger.info(f"✓ 账号创建完成: {self.stats['users_created']} 个")
            return True
            
        except Exception as e:
            logger.error(f"✗ 账号创建失败: {str(e)}")
            self.conn.rollback()
            return False
    
    def verify_import(self):
        """验证导入结果"""
        logger.info("验证导入结果...")
        
        verification = {}
        
        # 验证员工数量
        self.cursor.execute("SELECT COUNT(*) FROM employees WHERE employee_no LIKE 'TEST%'")
        verification['employees_count'] = self.cursor.fetchone()[0]
        
        # 验证业绩记录数量
        self.cursor.execute('''
            SELECT COUNT(*) FROM performance 
            WHERE employee_id IN (SELECT id FROM employees WHERE employee_no LIKE 'TEST%')
        ''')
        verification['performance_count'] = self.cursor.fetchone()[0]
        
        # 验证用户账号数量
        self.cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE employee_id IN (SELECT id FROM employees WHERE employee_no LIKE 'TEST%')
        ''')
        verification['users_count'] = self.cursor.fetchone()[0]
        
        # 打印验证结果
        print("\n" + "="*70)
        print("导入验证结果")
        print("="*70)
        print(f"员工数量: {verification['employees_count']} / {TOTAL_EMPLOYEES}")
        print(f"业绩记录: {verification['performance_count']}")
        print(f"用户账号: {verification['users_count']}")
        print("="*70 + "\n")
        
        return verification
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("✓ 数据库连接已关闭")
    
    def run(self):
        """执行完整的导入流程"""
        start_time = datetime.now()
        logger.info("="*70)
        logger.info("开始导入测试数据")
        logger.info("="*70)
        
        success = False
        
        try:
            # 步骤1: 连接数据库
            if not self.connect():
                return False
            
            # 步骤2: 清除旧数据
            if not self.clear_test_data():
                return False
            
            # 步骤3: 导入员工
            if not self.import_employees():
                return False
            
            # 步骤4: 导入业绩
            if not self.import_performance():
                return False
            
            # 步骤5: 创建账号
            if not self.create_user_accounts():
                return False
            
            # 步骤6: 验证结果
            verification = self.verify_import()
            
            # 计算耗时
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✓ 数据导入完成，耗时: {elapsed:.1f}秒")
            
            success = True
            
        except Exception as e:
            logger.error(f"✗ 导入过程出错: {str(e)}", exc_info=True)
        
        finally:
            self.close()
        
        return success


def main():
    """主函数"""
    importer = TestDataImporter()
    success = importer.run()
    
    if success:
        print("\n✅ 测试数据导入成功！")
        return 0
    else:
        print("\n❌ 测试数据导入失败！")
        return 1


if __name__ == '__main__':
    exit(main())

