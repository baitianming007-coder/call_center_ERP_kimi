"""
数据库初始化脚本
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random
from core.auth import hash_password, encrypt_phone
from config import Config


def init_database():
    """初始化数据库"""
    # 确保data目录存在
    os.makedirs(os.path.dirname(Config.DATABASE), exist_ok=True)
    
    # 连接数据库
    conn = sqlite3.connect(Config.DATABASE)
    cursor = conn.cursor()
    
    # 读取并执行 schema
    print("正在创建数据库表...")
    with open('schema.sql', 'r', encoding='utf-8') as f:
        cursor.executescript(f.read())
    
    print("正在插入初始数据...")
    
    # 1. 创建团队
    teams = [
        ('A组', '张经理', 'A组负责区域A业务'),
        ('B组', '李经理', 'B组负责区域B业务'),
        ('C组', '王经理', 'C组负责区域C业务'),
    ]
    
    for team_name, leader, desc in teams:
        cursor.execute(
            'INSERT OR IGNORE INTO teams (team_name, team_leader, description) VALUES (?, ?, ?)',
            (team_name, leader, desc)
        )
    
    # 2. 创建系统参数
    system_params = [
        ('revenue_per_order', '170', '每单收入（元）', 1),
        ('manager_team_manager', 'A组', '经理manager管理的团队', 0),
    ]
    
    for key, value, desc, is_core in system_params:
        cursor.execute(
            'INSERT OR IGNORE INTO system_params (param_key, param_value, param_desc, is_core) VALUES (?, ?, ?, ?)',
            (key, value, desc, is_core)
        )
    
    # 3. 创建测试员工数据
    print("正在创建测试员工...")
    today = datetime.now().date()
    
    employees_data = []
    
    # A组员工（15人）
    for i in range(1, 16):
        join_date = today - timedelta(days=random.randint(10, 180))
        status = random.choice(['trainee', 'C', 'B', 'A']) if i <= 12 else 'eliminated'
        if i > 12:
            status = 'eliminated'
        elif i <= 3:
            status = 'A'
        elif i <= 8:
            status = 'B'
        elif i <= 12:
            status = 'C'
        else:
            status = 'trainee'
        
        employees_data.append((
            f'A{i:03d}',
            f'员工A{i:02d}',
            f'138{i:08d}',
            encrypt_phone(f'138{i:08d}'),
            'A组',
            status,
            join_date.strftime('%Y-%m-%d'),
            1
        ))
    
    # B组员工（12人）
    for i in range(1, 13):
        join_date = today - timedelta(days=random.randint(10, 180))
        status = random.choice(['trainee', 'C', 'B', 'A']) if i <= 10 else 'eliminated'
        
        employees_data.append((
            f'B{i:03d}',
            f'员工B{i:02d}',
            f'139{i:08d}',
            encrypt_phone(f'139{i:08d}'),
            'B组',
            status,
            join_date.strftime('%Y-%m-%d'),
            1
        ))
    
    # C组员工（8人）
    for i in range(1, 9):
        join_date = today - timedelta(days=random.randint(10, 180))
        status = random.choice(['trainee', 'C', 'B', 'A'])
        
        employees_data.append((
            f'C{i:03d}',
            f'员工C{i:02d}',
            f'137{i:08d}',
            encrypt_phone(f'137{i:08d}'),
            'C组',
            status,
            join_date.strftime('%Y-%m-%d'),
            1
        ))
    
    for emp_data in employees_data:
        cursor.execute(
            '''INSERT OR IGNORE INTO employees 
               (employee_no, name, phone, phone_encrypted, team, status, join_date, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            emp_data
        )
    
    # 4. 创建用户账号
    print("正在创建用户账号...")
    
    # 管理员账号 (1个)
    cursor.execute(
        'INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)',
        ('admin', hash_password('123456'), 'admin')
    )
    
    # 经理账号 (6个) - 确保大规模测试有足够的主管
    manager_accounts = [
        'manager',
        'manager001',
        'manager002',
        'manager003',
        'manager004',
        'manager005'
    ]
    
    for manager_username in manager_accounts:
        cursor.execute(
            'INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)',
            (manager_username, hash_password('123456'), 'manager')
        )
    
    # 财务账号 (1个)
    cursor.execute(
        'INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)',
        ('finance', hash_password('123456'), 'finance')
    )
    
    # 员工账号（取前10个员工）
    cursor.execute('SELECT id, employee_no FROM employees LIMIT 10')
    employees = cursor.fetchall()
    
    for emp_id, emp_no in employees:
        username = emp_no.lower()
        cursor.execute(
            'INSERT OR IGNORE INTO users (username, password, role, employee_id) VALUES (?, ?, ?, ?)',
            (username, hash_password('123456'), 'employee', emp_id)
        )
    
    # 5. 生成测试业绩数据（最近30天）
    print("正在生成测试业绩数据...")
    
    cursor.execute('SELECT id, status FROM employees WHERE is_active = 1')
    active_employees = cursor.fetchall()
    
    for emp_id, status in active_employees:
        # 根据状态生成不同的业绩
        for day_offset in range(30):
            work_date = (today - timedelta(days=day_offset)).strftime('%Y-%m-%d')
            
            # 根据状态决定出单数
            if status == 'A':
                orders = random.randint(3, 8)
            elif status == 'B':
                orders = random.randint(2, 5)
            elif status == 'C':
                orders = random.randint(0, 3)
            elif status == 'trainee':
                orders = random.randint(0, 2)
            else:
                orders = 0
            
            # 计算提成
            commission = calculate_daily_commission_for_init(orders)
            
            # 80% 概率是有效工作日
            is_valid = 1 if random.random() < 0.8 else 0
            
            cursor.execute(
                '''INSERT OR IGNORE INTO performance 
                   (employee_id, work_date, orders_count, commission, is_valid_workday)
                   VALUES (?, ?, ?, ?, ?)''',
                (emp_id, work_date, orders, commission, is_valid)
            )
    
    # 6. 生成部分状态变更历史
    print("正在生成状态变更历史...")
    
    for emp_id, status in active_employees:
        if status != 'trainee':
            # 生成一条从trainee到当前状态的历史
            change_date = (today - timedelta(days=random.randint(15, 60))).strftime('%Y-%m-%d')
            cursor.execute(
                '''INSERT INTO status_history 
                   (employee_id, from_status, to_status, change_date, reason, days_in_status)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (emp_id, 'trainee', status, change_date, '系统初始化测试数据', random.randint(3, 10))
            )
    
    conn.commit()
    conn.close()
    
    print("✅ 数据库初始化完成！")
    print("\n" + "="*60)
    print("测试账号信息 (统一密码: 123456)")
    print("="*60)
    print("\n【管理员账号】")
    print("  admin / 123456")
    print("\n【经理账号】(6个)")
    print("  manager / 123456")
    print("  manager001 / 123456")
    print("  manager002 / 123456")
    print("  manager003 / 123456")
    print("  manager004 / 123456")
    print("  manager005 / 123456")
    print("\n【财务账号】")
    print("  finance / 123456")
    print("\n【员工账号】(10个)")
    print("  a001 / 123456")
    print("  a002 / 123456")
    print("  ... (其他员工工号小写)")
    print("\n" + "="*60)
    print(f"数据库文件: {Config.DATABASE}")


def calculate_daily_commission_for_init(orders_count):
    """计算日提成（用于初始化）"""
    if orders_count <= 0:
        return 0
    if orders_count <= 3:
        return orders_count * 10
    if orders_count <= 5:
        return 3 * 10 + (orders_count - 3) * 20
    return 3 * 10 + 2 * 20 + (orders_count - 5) * 30


if __name__ == '__main__':
    print("=" * 50)
    print("呼叫中心职场管理系统 - 数据库初始化")
    print("=" * 50)
    init_database()



