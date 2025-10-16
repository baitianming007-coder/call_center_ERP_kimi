#!/usr/bin/env python3
"""测试员工账号登录"""
import sqlite3
from core.auth import verify_password

DB_PATH = 'data/callcenter.db'

print("测试员工账号登录功能...")
print("="*60)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

test_accounts = ['a001', 'a002', 'a003', 'a004', 'a005']
password = '123456'

success_count = 0
total_count = len(test_accounts)

for username in test_accounts:
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    
    if user:
        if verify_password(password, user['password']):
            cursor.execute('SELECT name FROM employees WHERE id = ?', (user['employee_id'],))
            emp = cursor.fetchone()
            emp_name = emp['name'] if emp else '未知'
            print(f"✓ {username} / {password} - 登录成功 ({emp_name})")
            success_count += 1
        else:
            print(f"✗ {username} / {password} - 密码错误")
    else:
        print(f"✗ {username} / {password} - 账号不存在")

conn.close()

print("="*60)
print(f"测试结果: {success_count}/{total_count} 成功")
print("="*60)

if success_count == total_count:
    print("✅ 所有员工账号测试通过！")
else:
    print("⚠️ 部分账号测试失败，需要检查")

