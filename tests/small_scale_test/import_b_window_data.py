#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入B级窗口期员工数据到数据库
"""

import csv
import json
import sqlite3
from pathlib import Path
import sys
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.small_scale_test.config import DB_PATH, OUTPUT_DIR, LOGS_DIR, BASE_DIR
from core.auth import hash_password
from app import app

# 设置日志
Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)
log_file = Path(LOGS_DIR) / 'import_b_window.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BWindowDataImporter:
    """B级窗口期数据导入器"""
    
    def __init__(self):
        self.db_path = Path(BASE_DIR) / DB_PATH
        self.output_dir = Path(OUTPUT_DIR)
        self.conn = None
        self.cursor = None
        self.stats = {
            'employees_imported': 0,
            'performance_imported': 0,
            'status_history_imported': 0,
            'users_created': 0,
            'errors': 0
        }
        self.emp_mapping = {}  # employee_no -> employee_id
    
    def connect_db(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            logger.info(f"✓ 已连接数据库: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"连接数据库失败: {e}")
            return False
    
    def close_db(self):
        """关闭数据库"""
        if self.conn:
            self.conn.close()
            logger.info("✓ 数据库连接已关闭")
    
    def clear_old_data(self):
        """清除旧的B窗口测试数据"""
        logger.info("清除旧的B窗口测试数据...")
        try:
            # 删除用户
            self.cursor.execute("DELETE FROM users WHERE username LIKE 'bwindow%'")
            
            # 删除业绩记录
            self.cursor.execute('''
                DELETE FROM performance 
                WHERE employee_id IN (
                    SELECT id FROM employees WHERE employee_no LIKE 'BWINDOW%'
                )
            ''')
            
            # 删除状态历史
            self.cursor.execute('''
                DELETE FROM status_history 
                WHERE employee_id IN (
                    SELECT id FROM employees WHERE employee_no LIKE 'BWINDOW%'
                )
            ''')
            
            # 删除员工
            self.cursor.execute("DELETE FROM employees WHERE employee_no LIKE 'BWINDOW%'")
            
            self.conn.commit()
            logger.info("✓ 旧数据清除完成")
        except Exception as e:
            logger.error(f"清除旧数据失败: {e}")
            self.conn.rollback()
    
    def import_employees(self):
        """导入员工数据"""
        logger.info("导入员工数据...")
        
        csv_file = self.output_dir / 'b_window_employees.csv'
        if not csv_file.exists():
            logger.error(f"文件不存在: {csv_file}")
            return False
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    self.cursor.execute('''
                        INSERT INTO employees (employee_no, name, status, join_date, team, is_active)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (row['employee_no'], row['name'], row['status'],
                          row['join_date'], row['team'], int(row['is_active'])))
                    
                    emp_id = self.cursor.lastrowid
                    self.emp_mapping[row['employee_no']] = emp_id
                    self.stats['employees_imported'] += 1
                    
                except Exception as e:
                    logger.warning(f"导入员工 {row['employee_no']} 失败: {e}")
                    self.stats['errors'] += 1
        
        self.conn.commit()
        logger.info(f"✓ 员工导入完成: {self.stats['employees_imported']} 名")
        return True
    
    def import_performance(self):
        """导入业绩数据"""
        logger.info("导入业绩数据...")
        
        csv_file = self.output_dir / 'b_window_performance.csv'
        if not csv_file.exists():
            logger.error(f"文件不存在: {csv_file}")
            return False
        
        batch = []
        batch_size = 500
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                emp_id = self.emp_mapping.get(row['employee_no'])
                if not emp_id:
                    logger.warning(f"找不到员工: {row['employee_no']}")
                    self.stats['errors'] += 1
                    continue
                
                batch.append((
                    emp_id,
                    row['work_date'],
                    int(row['orders_count']),
                    float(row['commission']),
                    int(row['is_valid_workday'])
                ))
                
                if len(batch) >= batch_size:
                    try:
                        self.cursor.executemany('''
                            INSERT INTO performance (
                                employee_id, work_date, orders_count, commission, is_valid_workday
                            ) VALUES (?, ?, ?, ?, ?)
                        ''', batch)
                        self.stats['performance_imported'] += len(batch)
                        batch = []
                    except Exception as e:
                        logger.error(f"批量插入失败: {e}")
                        self.stats['errors'] += len(batch)
                        batch = []
        
        # 插入剩余数据
        if batch:
            try:
                self.cursor.executemany('''
                    INSERT INTO performance (
                        employee_id, work_date, orders_count, commission, is_valid_workday
                    ) VALUES (?, ?, ?, ?, ?)
                ''', batch)
                self.stats['performance_imported'] += len(batch)
            except Exception as e:
                logger.error(f"最后批次插入失败: {e}")
                self.stats['errors'] += len(batch)
        
        self.conn.commit()
        logger.info(f"✓ 业绩导入完成: {self.stats['performance_imported']} 条")
        return True
    
    def import_status_history(self):
        """导入状态变更历史"""
        logger.info("导入状态变更历史...")
        
        json_file = self.output_dir / 'b_window_status_history.json'
        if not json_file.exists():
            logger.error(f"文件不存在: {json_file}")
            return False
        
        with open(json_file, 'r', encoding='utf-8') as f:
            history_records = json.load(f)
        
        for record in history_records:
            emp_id = self.emp_mapping.get(record['employee_no'])
            if not emp_id:
                logger.warning(f"找不到员工: {record['employee_no']}")
                self.stats['errors'] += 1
                continue
            
            try:
                self.cursor.execute('''
                    INSERT INTO status_history (
                        employee_id, from_status, to_status, change_date, reason, days_in_status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (emp_id, record['from_status'], record['to_status'],
                      record['change_date'], record['reason'], record['days_in_status']))
                
                self.stats['status_history_imported'] += 1
                
            except Exception as e:
                logger.warning(f"导入状态历史失败: {e}")
                self.stats['errors'] += 1
        
        self.conn.commit()
        logger.info(f"✓ 状态历史导入完成: {self.stats['status_history_imported']} 条")
        return True
    
    def create_user_accounts(self):
        """创建用户账号"""
        logger.info("创建用户账号...")
        
        password_hash = hash_password("123456")
        
        for emp_no, emp_id in self.emp_mapping.items():
            username = emp_no.lower()  # bwindow001, bwindow002, ...
            
            try:
                self.cursor.execute('''
                    INSERT INTO users (username, password, role, employee_id)
                    VALUES (?, ?, ?, ?)
                ''', (username, password_hash, 'employee', emp_id))
                
                self.stats['users_created'] += 1
                
            except sqlite3.IntegrityError:
                # 用户名已存在，更新
                self.cursor.execute('''
                    UPDATE users SET password = ?, role = ?, employee_id = ?
                    WHERE username = ?
                ''', (password_hash, 'employee', emp_id, username))
                self.stats['users_created'] += 1
            except Exception as e:
                logger.warning(f"创建用户 {username} 失败: {e}")
                self.stats['errors'] += 1
        
        self.conn.commit()
        logger.info(f"✓ 用户账号创建完成: {self.stats['users_created']} 个")
        return True
    
    def verify_import(self):
        """验证导入结果"""
        logger.info("\n验证导入结果...")
        
        # 检查员工数量
        self.cursor.execute("SELECT COUNT(*) FROM employees WHERE employee_no LIKE 'BWINDOW%'")
        emp_count = self.cursor.fetchone()[0]
        
        # 检查业绩数量
        self.cursor.execute('''
            SELECT COUNT(*) FROM performance 
            WHERE employee_id IN (SELECT id FROM employees WHERE employee_no LIKE 'BWINDOW%')
        ''')
        perf_count = self.cursor.fetchone()[0]
        
        # 检查状态历史
        self.cursor.execute('''
            SELECT COUNT(*) FROM status_history 
            WHERE employee_id IN (SELECT id FROM employees WHERE employee_no LIKE 'BWINDOW%')
        ''')
        history_count = self.cursor.fetchone()[0]
        
        # 检查用户账号
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE username LIKE 'bwindow%'")
        user_count = self.cursor.fetchone()[0]
        
        logger.info(f"  员工数量: {emp_count}")
        logger.info(f"  业绩记录: {perf_count}")
        logger.info(f"  状态历史: {history_count}")
        logger.info(f"  用户账号: {user_count}")
        
        return emp_count == self.stats['employees_imported']
    
    def run(self):
        """执行完整导入流程"""
        logger.info("="*70)
        logger.info("开始导入B级窗口期员工数据")
        logger.info("="*70)
        
        if not self.connect_db():
            return False
        
        try:
            self.clear_old_data()
            self.import_employees()
            self.import_performance()
            self.import_status_history()
            self.create_user_accounts()
            self.verify_import()
            
            logger.info("\n" + "="*70)
            logger.info("导入完成")
            logger.info("="*70)
            logger.info(f"员工: {self.stats['employees_imported']}")
            logger.info(f"业绩: {self.stats['performance_imported']}")
            logger.info(f"状态历史: {self.stats['status_history_imported']}")
            logger.info(f"用户: {self.stats['users_created']}")
            logger.info(f"错误: {self.stats['errors']}")
            logger.info("="*70)
            
            return True
            
        except Exception as e:
            logger.error(f"导入失败: {e}", exc_info=True)
            return False
        finally:
            self.close_db()


def main():
    """主函数"""
    with app.app_context():
        importer = BWindowDataImporter()
        success = importer.run()
        
        if success:
            print("\n✅ B级窗口期数据导入成功！")
            print("\n📋 测试账号信息:")
            print("   用户名: bwindow001 ~ bwindow030")
            print("   密码: 123456")
            return 0
        else:
            print("\n❌ 数据导入失败！")
            return 1


if __name__ == '__main__':
    exit(main())

