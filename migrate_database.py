#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 应用 schema_extensions.sql
版本：2.0
日期：2025-10-15
"""

import sqlite3
import os
from config import Config

def migrate_database():
    """执行数据库迁移"""
    print("="*60)
    print("数据库迁移工具 v2.0")
    print("="*60)
    
    db_path = Config.DATABASE
    
    # 检查数据库是否存在
    if not os.path.exists(db_path):
        print(f"错误：数据库文件不存在：{db_path}")
        print("请先运行 init_test_data_advanced.py 初始化数据库")
        return False
    
    # 备份数据库
    print("\n[1/5] 备份数据库...")
    backup_path = db_path + '.backup'
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✓ 数据库已备份到: {backup_path}")
    except Exception as e:
        print(f"✗ 备份失败: {e}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 步骤2：更新users表的CHECK约束（添加finance角色）
        print("\n[2/5] 更新users表（添加finance角色）...")
        
        # SQLite不支持直接修改CHECK约束，需要重建表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('employee', 'manager', 'admin', 'finance')),
                employee_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            )
        """)
        
        # 复制数据
        cursor.execute("""
            INSERT INTO users_new SELECT * FROM users
        """)
        
        # 删除旧表，重命名新表
        cursor.execute("DROP TABLE users")
        cursor.execute("ALTER TABLE users_new RENAME TO users")
        
        # 重建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        
        print("✓ users表已更新")
        
        # 步骤3：更新notifications表的CHECK约束
        print("\n[3/5] 更新notifications表（添加新通知类型）...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                type TEXT DEFAULT 'system' CHECK(type IN (
                    'system', 'status_change', 'salary', 'performance', 'dispute', 'announcement',
                    'promotion_pending', 'promotion_approved', 'promotion_rejected',
                    'challenge_triggered', 'challenge_success', 'challenge_failed',
                    'calendar_changed', 'payroll_ready', 'payroll_paid'
                )),
                link TEXT,
                is_read INTEGER DEFAULT 0 CHECK(is_read IN (0, 1)),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        cursor.execute("INSERT INTO notifications_new SELECT * FROM notifications")
        cursor.execute("DROP TABLE notifications")
        cursor.execute("ALTER TABLE notifications_new RENAME TO notifications")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read, created_at)")
        
        print("✓ notifications表已更新")
        
        # 步骤4：应用schema_extensions.sql
        print("\n[4/5] 应用schema扩展...")
        
        with open('schema_extensions.sql', 'r', encoding='utf-8') as f:
            sql_content = f.read()
            # 移除已经处理的部分
            # 执行剩余的SQL语句
            cursor.executescript(sql_content)
        
        print("✓ schema扩展已应用")
        
        # 步骤5：验证新表
        print("\n[5/5] 验证新表...")
        
        expected_tables = [
            'promotion_confirmations',
            'demotion_challenges',
            'training_assessments',
            'work_calendar',
            'audit_logs',
            'payroll_records',
            'payroll_adjustments',
            'payroll_archives'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        all_exists = True
        for table in expected_tables:
            if table in existing_tables:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table} (未找到)")
                all_exists = False
        
        if all_exists:
            conn.commit()
            print("\n" + "="*60)
            print("✅ 数据库迁移成功完成！")
            print("="*60)
            print(f"\n新增表：{len(expected_tables)}个")
            print(f"备份文件：{backup_path}")
            print("\n可以安全删除备份文件（如果测试通过）")
            return True
        else:
            print("\n⚠️  部分表创建失败")
            conn.rollback()
            return False
            
    except Exception as e:
        print(f"\n✗ 迁移失败: {e}")
        print("正在回滚...")
        conn.rollback()
        
        # 恢复备份
        try:
            conn.close()
            import shutil
            shutil.copy2(backup_path, db_path)
            print("✓ 数据库已从备份恢复")
        except Exception as e2:
            print(f"✗ 恢复失败: {e2}")
        
        return False
    
    finally:
        conn.close()


if __name__ == '__main__':
    success = migrate_database()
    exit(0 if success else 1)



