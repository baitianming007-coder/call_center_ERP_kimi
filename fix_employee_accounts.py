#!/usr/bin/env python3
"""修复员工测试账号"""
import sqlite3
from core.auth import hash_password
from datetime import datetime, timedelta

DB_PATH = 'data/callcenter.db'

print("正在创建标准测试员工账号...")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 统一密码
password = hash_password('123456')

# 查找或创建测试员工
join_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')

test_employees = []
for i in range(1, 11):
    emp_no = f'A{i:03d}'  # A001, A002, ...
    emp_name = f'测试员工{i:02d}'
    
    # 检查员工是否存在
    cursor.execute('SELECT id FROM employees WHERE employee_no = ?', (emp_no,))
    emp = cursor.fetchone()
    
    if emp:
        emp_id = emp[0]
        print(f"  ✓ 员工已存在: {emp_no} (ID: {emp_id})")
    else:
        # 创建新员工
        cursor.execute('''
            INSERT INTO employees (employee_no, name, status, join_date, is_active, team)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (emp_no, emp_name, 'trainee', join_date, 1, 'Team1'))
        emp_id = cursor.lastrowid
        print(f"  ✓ 创建员工: {emp_no} ({emp_name})")
    
    # 创建或更新用户账号
    username = emp_no.lower()  # a001, a002, ...
    
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    if cursor.fetchone():
        # 更新密码
        cursor.execute('UPDATE users SET password = ?, employee_id = ? WHERE username = ?',
                      (password, emp_id, username))
        print(f"  ✓ 更新账号: {username} / 123456")
    else:
        # 创建账号
        cursor.execute('''
            INSERT INTO users (username, password, role, employee_id)
            VALUES (?, ?, ?, ?)
        ''', (username, password, 'employee', emp_id))
        print(f"  ✓ 创建账号: {username} / 123456")
    
    test_employees.append(username)

conn.commit()
conn.close()

print("\n" + "="*60)
print("✅ 员工测试账号创建完成！")
print("="*60)
print("\n📋 可用员工账号（密码：123456）:")
for username in test_employees:
    print(f"  {username} / 123456")
print("="*60 + "\n")

