"""
数据导入脚本
将生成的测试数据导入数据库
"""
import sys
import os
import csv
import json
import sqlite3
import shutil
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.large_scale_test.config import *
from tests.large_scale_test.utils import ProgressBar
from core.auth import hash_password


class DataImporter:
    """数据导入器"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        
    def import_all(self):
        """执行完整的数据导入流程"""
        print("="*60)
        print("开始导入测试数据")
        print("="*60)
        print()
        
        try:
            # 备份数据库
            print("步骤1: 备份现有数据库...")
            self._backup_database()
            print("✓ 数据库已备份")
            print()
            
            # 连接数据库
            print("步骤2: 连接数据库...")
            self._connect_database()
            print("✓ 数据库已连接")
            print()
            
            # 清空测试表
            print("步骤3: 清空测试相关表...")
            self._clear_test_tables()
            print("✓ 表已清空")
            print()
            
            # 导入员工数据
            print("步骤4: 导入员工数据...")
            self._import_employees()
            print("✓ 员工数据已导入")
            print()
            
            # 导入业绩数据
            print("步骤5: 导入业绩数据...")
            self._import_performance()
            print("✓ 业绩数据已导入")
            print()
            
            # 创建主管账号
            print("步骤6: 创建主管账号...")
            self._create_supervisors()
            print("✓ 主管账号已创建")
            print()
            
            # 重建索引
            print("步骤7: 重建索引...")
            self._rebuild_indexes()
            print("✓ 索引已重建")
            print()
            
            # 提交并验证
            print("步骤8: 验证数据...")
            self._verify_data()
            print("✓ 数据验证通过")
            print()
            
            self.conn.commit()
            
            print("="*60)
            print("数据导入完成！")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ 导入失败: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            if self.conn:
                self.conn.close()
    
    def _backup_database(self):
        """备份数据库"""
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, DB_BACKUP_PATH)
            print(f"  备份文件: {DB_BACKUP_PATH}")
    
    def _connect_database(self):
        """连接数据库"""
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def _clear_test_tables(self):
        """清空测试相关的表"""
        tables_to_clear = [
            'users',
            'employees',
            'performance',
            'status_history',
            'salary',
            'promotion_confirmations',
            'demotion_challenges',
            'audit_logs',
            'notifications'
        ]
        
        for table in tables_to_clear:
            try:
                self.cursor.execute(f'DELETE FROM {table}')
                print(f"  已清空表: {table}")
            except sqlite3.OperationalError as e:
                print(f"  跳过表 {table}: {e}")
    
    def _import_employees(self):
        """导入员工数据"""
        with open(EMPLOYEES_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            employees = list(reader)
        
        progress = ProgressBar(len(employees), '导入员工')
        
        # 批量插入
        batch_size = 100
        for i in range(0, len(employees), batch_size):
            batch = employees[i:i+batch_size]
            
            self.cursor.executemany('''
                INSERT INTO employees (
                    employee_no, name, team, status, 
                    join_date, is_active
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', [
                (
                    emp['employee_no'],
                    emp['name'],
                    emp['team'],
                    emp['status'],
                    emp['join_date'],
                    emp['is_active']
                ) for emp in batch
            ])
            
            progress.update(len(batch))
        
        self.conn.commit()
    
    def _import_performance(self):
        """导入业绩数据"""
        with open(PERFORMANCE_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            performance = list(reader)
        
        print(f"  总记录数: {len(performance)}")
        progress = ProgressBar(len(performance), '导入业绩')
        
        # 批量插入
        batch_size = 1000
        for i in range(0, len(performance), batch_size):
            batch = performance[i:i+batch_size]
            
            # 需要先获取employee_id
            batch_with_ids = []
            for perf in batch:
                emp_id = self.cursor.execute(
                    'SELECT id FROM employees WHERE employee_no = ?',
                    (perf['employee_no'],)
                ).fetchone()
                
                if emp_id:
                    batch_with_ids.append((
                        emp_id[0],
                        perf['work_date'],
                        perf['orders_count'],
                        perf['commission'],
                        perf['is_valid_workday']
                    ))
            
            if batch_with_ids:
                self.cursor.executemany('''
                    INSERT INTO performance (
                        employee_id, work_date, orders_count, 
                        commission, is_valid_workday
                    ) VALUES (?, ?, ?, ?, ?)
                ''', batch_with_ids)
            
            progress.update(len(batch))
        
        self.conn.commit()
    
    def _create_supervisors(self):
        """创建主管账号"""
        # 读取主管信息
        with open(EXPECTED_EVENTS_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
            supervisors = data.get('supervisors', [])
        
        for sup in supervisors:
            # 创建用户账号
            self.cursor.execute('''
                INSERT OR REPLACE INTO users (
                    username, password, role
                ) VALUES (?, ?, ?)
            ''', (
                sup['username'],
                hash_password(sup['password']),
                'manager'
            ))
            print(f"  已创建主管: {sup['username']}")
        
        self.conn.commit()
    
    def _rebuild_indexes(self):
        """重建索引以提升查询性能"""
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_perf_emp_date ON performance(employee_id, work_date)',
            'CREATE INDEX IF NOT EXISTS idx_perf_date ON performance(work_date)',
            'CREATE INDEX IF NOT EXISTS idx_emp_status ON employees(status)',
            'CREATE INDEX IF NOT EXISTS idx_emp_no ON employees(employee_no)',
        ]
        
        for idx_sql in indexes:
            self.cursor.execute(idx_sql)
        
        self.conn.commit()
    
    def _verify_data(self):
        """验证导入的数据"""
        # 验证员工数
        emp_count = self.cursor.execute('SELECT COUNT(*) FROM employees').fetchone()[0]
        print(f"  员工数: {emp_count}")
        
        # 验证业绩记录数
        perf_count = self.cursor.execute('SELECT COUNT(*) FROM performance').fetchone()[0]
        print(f"  业绩记录数: {perf_count}")
        
        # 验证主管数
        mgr_count = self.cursor.execute('SELECT COUNT(*) FROM users WHERE role = ?', ('manager',)).fetchone()[0]
        print(f"  主管数: {mgr_count}")
        
        # 抽查几条数据
        sample_emp = self.cursor.execute('SELECT * FROM employees LIMIT 1').fetchone()
        if sample_emp:
            print(f"  抽查员工: {dict(sample_emp)}")


def main():
    """主函数"""
    importer = DataImporter()
    importer.import_all()


if __name__ == '__main__':
    main()

