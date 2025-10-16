#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为audit_logs表添加索引以优化查询性能
"""

import sqlite3
from pathlib import Path

DB_PATH = 'data/callcenter.db'

def add_indexes():
    """添加审计日志表的索引"""
    print("开始为 audit_logs 表添加索引...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    indexes = [
        ('idx_audit_logs_operation_type', 'CREATE INDEX IF NOT EXISTS idx_audit_logs_operation_type ON audit_logs(operation_type)'),
        ('idx_audit_logs_operator_id', 'CREATE INDEX IF NOT EXISTS idx_audit_logs_operator_id ON audit_logs(operator_id)'),
        ('idx_audit_logs_created_at', 'CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC)'),
        ('idx_audit_logs_target_employee_id', 'CREATE INDEX IF NOT EXISTS idx_audit_logs_target_employee_id ON audit_logs(target_employee_id)'),
        ('idx_audit_logs_operator_created', 'CREATE INDEX IF NOT EXISTS idx_audit_logs_operator_created ON audit_logs(operator_id, created_at DESC)')
    ]
    
    for index_name, sql in indexes:
        try:
            cursor.execute(sql)
            print(f"  ✓ 创建索引: {index_name}")
        except Exception as e:
            print(f"  ✗ 创建索引失败 {index_name}: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n索引创建完成！")
    print("查询性能已优化。")

if __name__ == '__main__':
    add_indexes()

