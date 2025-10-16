"""
高级测试数据生成器
生成200个员工，模拟过去3个月的真实业务场景
"""
import sqlite3
import random
from datetime import datetime, timedelta
from config import Config
from core.auth import hash_password, encrypt_phone
from core.commission import calculate_daily_commission


def generate_advanced_test_data():
    """生成高级测试数据"""
    print("=" * 70)
    print("高级测试数据生成器 - 200名员工 × 90天动态模拟")
    print("=" * 70)
    
    conn = sqlite3.connect(Config.DATABASE)
    cursor = conn.cursor()
    
    # 先创建表结构（如果不存在）
    print("\n[0/5] 创建数据库表结构...")
    with open('schema.sql', 'r', encoding='utf-8') as f:
        cursor.executescript(f.read())
    conn.commit()
    print("✓ 表结构已创建")
    
    # 清理旧数据（保留管理员账号）
    print("\n[1/5] 清理旧测试数据...")
    cursor.execute("DELETE FROM performance")
    cursor.execute("DELETE FROM status_history")
    cursor.execute("DELETE FROM salary")
    cursor.execute("DELETE FROM salary_disputes")
    cursor.execute("DELETE FROM notifications")
    cursor.execute("DELETE FROM employees")
    cursor.execute("DELETE FROM users WHERE role = 'employee'")
    
    # 创建管理员账号（如果不存在）
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ('admin', hash_password('admin123'), 'admin')
        )
    
    # 创建经理账号（如果不存在）
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'manager'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ('manager', hash_password('manager123'), 'manager')
        )
    
    # 创建团队（如果不存在）
    for team_name in ['A组', 'B组', 'C组', 'D组']:
        cursor.execute("SELECT COUNT(*) FROM teams WHERE team_name = ?", (team_name,))
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO teams (team_name, team_leader, description) VALUES (?, ?, ?)",
                (team_name, f'{team_name}负责人', f'{team_name}业务团队')
            )
    
    conn.commit()
    print("✓ 旧数据已清理，基础数据已创建")
    
    # 创建200名员工
    print("\n[2/5] 创建200名员工...")
    today = datetime.now().date()
    start_date = today - timedelta(days=90)  # 90天前开始
    
    teams = ['A组', 'B组', 'C组', 'D组']
    employees = []
    
    for i in range(1, 201):
        team = random.choice(teams)
        # 入职时间在90天前到60天前之间
        days_ago = random.randint(60, 90)
        join_date = today - timedelta(days=days_ago)
        
        employee_no = f"{team[0]}{i:03d}"
        name = f"测试员工{i:03d}"
        phone = f"13{random.randint(100000000, 999999999)}"
        
        cursor.execute(
            '''INSERT INTO employees 
               (employee_no, name, phone, phone_encrypted, team, status, join_date, is_active)
               VALUES (?, ?, ?, ?, ?, 'trainee', ?, 1)''',
            (employee_no, name, phone, encrypt_phone(phone), team, join_date.strftime('%Y-%m-%d'))
        )
        
        employee_id = cursor.lastrowid
        employees.append({
            'id': employee_id,
            'employee_no': employee_no,
            'name': name,
            'team': team,
            'join_date': join_date,
            'current_status': 'trainee',
            'status_start_date': join_date
        })
        
        # 为部分员工创建登录账号
        if i <= 20:  # 前20个员工创建账号
            cursor.execute(
                'INSERT INTO users (username, password, role, employee_id) VALUES (?, ?, ?, ?)',
                (employee_no.lower(), hash_password('test123'), 'employee', employee_id)
            )
    
    conn.commit()
    print(f"✓ 已创建200名员工，分布在{len(teams)}个团队")
    print(f"  - 入职时间范围：{start_date.strftime('%Y-%m-%d')} ~ {(today - timedelta(days=60)).strftime('%Y-%m-%d')}")
    
    # 模拟90天业绩数据和状态流转
    print("\n[3/5] 模拟90天业绩数据和状态流转...")
    print("  这个过程会模拟真实的业务场景：")
    print("  - 每天随机出单 0-5 单")
    print("  - 根据规则自动流转状态")
    print("  - 记录所有状态变更历史")
    
    status_changes_count = 0
    performance_records_count = 0
    
    # 按日期顺序模拟
    for day_offset in range(90, -1, -1):  # 从90天前到今天
        current_date = today - timedelta(days=day_offset)
        
        # 每10天输出一次进度
        if day_offset % 10 == 0:
            print(f"  处理日期: {current_date.strftime('%Y-%m-%d')} (剩余{day_offset}天)")
        
        for emp in employees:
            # 检查员工是否已入职
            if current_date < emp['join_date']:
                continue
            
            # 如果已淘汰，不再生成数据
            if emp['current_status'] == 'eliminated':
                continue
            
            # 模拟出单数（0-5单，根据状态调整概率）
            if emp['current_status'] == 'trainee':
                # 培训期出单少
                orders = random.choices([0, 1, 2, 3], weights=[30, 40, 20, 10])[0]
            elif emp['current_status'] == 'C':
                # C级员工
                orders = random.choices([0, 1, 2, 3, 4], weights=[20, 30, 25, 20, 5])[0]
            elif emp['current_status'] == 'B':
                # B级员工出单较多
                orders = random.choices([1, 2, 3, 4, 5], weights=[10, 20, 30, 30, 10])[0]
            elif emp['current_status'] == 'A':
                # A级员工出单最多
                orders = random.choices([2, 3, 4, 5], weights=[10, 20, 40, 30])[0]
            else:
                orders = 0
            
            # 计算提成
            commission = calculate_daily_commission(orders)
            
            # 80% 概率是有效工作日
            is_valid = 1 if random.random() < 0.8 else 0
            
            # 插入业绩记录
            cursor.execute(
                '''INSERT OR IGNORE INTO performance 
                   (employee_id, work_date, orders_count, commission, is_valid_workday)
                   VALUES (?, ?, ?, ?, ?)''',
                (emp['id'], current_date.strftime('%Y-%m-%d'), orders, commission, is_valid)
            )
            performance_records_count += 1
            
            # 检查状态流转（每3天检查一次，提高效率）
            if day_offset % 3 == 0:
                # 更新数据库中的状态
                cursor.execute(
                    'UPDATE employees SET status = ? WHERE id = ?',
                    (emp['current_status'], emp['id'])
                )
                
                # 计算在当前状态的天数
                days_in_status = (current_date - emp['status_start_date']).days
                
                # 简化的状态流转逻辑（直接在这里实现，避免Flask上下文问题）
                old_status = emp['current_status']
                new_status = old_status
                reason = ''
                should_change = False
                
                if old_status == 'trainee' and days_in_status >= 3:
                    new_status = 'C'
                    reason = '培训期满3天'
                    should_change = True
                
                elif old_status == 'C' and days_in_status >= 3:
                    # 获取最近3天出单数
                    recent_date = current_date - timedelta(days=2)
                    cursor.execute(
                        '''SELECT COALESCE(SUM(orders_count), 0) as total 
                           FROM performance 
                           WHERE employee_id = ? AND work_date >= ? AND work_date <= ?''',
                        (emp['id'], recent_date.strftime('%Y-%m-%d'), current_date.strftime('%Y-%m-%d'))
                    )
                    recent_orders = cursor.fetchone()[0]
                    
                    if days_in_status <= 6 and recent_orders >= 3:
                        new_status = 'B'
                        reason = f'6天内最近3天出单≥3单（实际{recent_orders}单）'
                        should_change = True
                    elif days_in_status > 6 and recent_orders < 3:
                        new_status = 'eliminated'
                        reason = f'超6天最近3天出单<3单（实际{recent_orders}单）'
                        should_change = True
                
                elif old_status == 'B' and days_in_status >= 6:
                    # 获取最近6天出单数
                    recent_date = current_date - timedelta(days=5)
                    cursor.execute(
                        '''SELECT COALESCE(SUM(orders_count), 0) as total 
                           FROM performance 
                           WHERE employee_id = ? AND work_date >= ? AND work_date <= ?''',
                        (emp['id'], recent_date.strftime('%Y-%m-%d'), current_date.strftime('%Y-%m-%d'))
                    )
                    recent_orders = cursor.fetchone()[0]
                    
                    if days_in_status <= 9 and recent_orders >= 12:
                        new_status = 'A'
                        reason = f'9天内最近6天出单≥12单（实际{recent_orders}单）'
                        should_change = True
                    elif days_in_status > 9 and recent_orders < 12:
                        new_status = 'C'
                        reason = f'超9天最近6天出单<12单（实际{recent_orders}单）'
                        should_change = True
                
                elif old_status == 'A':
                    # 获取最近6天出单数
                    recent_date = current_date - timedelta(days=5)
                    cursor.execute(
                        '''SELECT COALESCE(SUM(orders_count), 0) as total 
                           FROM performance 
                           WHERE employee_id = ? AND work_date >= ? AND work_date <= ?''',
                        (emp['id'], recent_date.strftime('%Y-%m-%d'), current_date.strftime('%Y-%m-%d'))
                    )
                    recent_orders = cursor.fetchone()[0]
                    
                    if recent_orders <= 12:
                        new_status = 'C'
                        reason = f'最近6天出单≤12单（实际{recent_orders}单）'
                        should_change = True
                
                if should_change:
                    # 写入状态变更历史
                    cursor.execute(
                        '''INSERT INTO status_history 
                           (employee_id, from_status, to_status, change_date, reason, days_in_status)
                           VALUES (?, ?, ?, ?, ?, ?)''',
                        (emp['id'], old_status, new_status, current_date.strftime('%Y-%m-%d'), 
                         reason, days_in_status)
                    )
                    
                    # 更新员工当前状态
                    emp['current_status'] = new_status
                    emp['status_start_date'] = current_date
                    
                    status_changes_count += 1
                    
                    # 调试信息（仅显示关键变更）
                    if new_status in ['A', 'eliminated']:
                        print(f"    → {emp['employee_no']} {old_status}→{new_status}: {reason}")
                
                conn.commit()
    
    conn.commit()
    
    print(f"✓ 业绩模拟完成")
    print(f"  - 生成业绩记录：{performance_records_count} 条")
    print(f"  - 状态变更次数：{status_changes_count} 次")
    
    # 统计最终状态分布
    print("\n[4/5] 统计员工状态分布...")
    cursor.execute('''
        SELECT status, COUNT(*) as count
        FROM employees
        WHERE is_active = 1
        GROUP BY status
        ORDER BY 
            CASE status
                WHEN 'A' THEN 1
                WHEN 'B' THEN 2
                WHEN 'C' THEN 3
                WHEN 'trainee' THEN 4
                WHEN 'eliminated' THEN 5
            END
    ''')
    
    status_dist = cursor.fetchall()
    status_labels = {
        'A': 'A级', 'B': 'B级', 'C': 'C级', 
        'trainee': '培训期', 'eliminated': '已淘汰'
    }
    
    print("  最终状态分布：")
    for status, count in status_dist:
        percentage = count / 200 * 100
        print(f"    {status_labels.get(status, status):6s}: {count:3d}人 ({percentage:5.1f}%)")
    
    # 验证核心业务逻辑
    print("\n[5/5] 验证核心业务逻辑...")
    
    # 验证1：检查提成计算
    cursor.execute('''
        SELECT orders_count, commission
        FROM performance
        WHERE orders_count > 0
        ORDER BY RANDOM()
        LIMIT 5
    ''')
    
    print("  ✓ 验证提成计算（随机抽样5条）：")
    for orders, commission in cursor.fetchall():
        expected = calculate_daily_commission(orders)
        status_icon = "✓" if abs(commission - expected) < 0.01 else "✗"
        print(f"    {status_icon} {orders}单 → ¥{commission:.2f} (预期¥{expected:.2f})")
    
    # 验证2：检查状态流转合理性
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM status_history
        WHERE from_status = 'trainee' AND to_status = 'C'
    ''')
    trainee_to_c = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM status_history
        WHERE from_status = 'C' AND to_status = 'B'
    ''')
    c_to_b = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM status_history
        WHERE from_status = 'B' AND to_status = 'A'
    ''')
    b_to_a = cursor.fetchone()[0]
    
    print(f"  ✓ 验证状态流转路径：")
    print(f"    trainee → C: {trainee_to_c} 次")
    print(f"    C → B:       {c_to_b} 次")
    print(f"    B → A:       {b_to_a} 次")
    
    # 验证3：检查A级员工是否真的达标
    cursor.execute('''
        SELECT e.employee_no, e.name, 
               (SELECT SUM(orders_count) 
                FROM performance p 
                WHERE p.employee_id = e.id 
                AND p.work_date >= date('now', '-6 days')) as recent_orders
        FROM employees e
        WHERE e.status = 'A'
        ORDER BY RANDOM()
        LIMIT 3
    ''')
    
    print(f"  ✓ 验证A级员工达标情况（随机抽样3人）：")
    for emp_no, name, recent_orders in cursor.fetchall():
        recent_orders = recent_orders or 0
        status_icon = "✓" if recent_orders > 12 else "⚠"
        print(f"    {status_icon} {emp_no} 最近6天出单: {recent_orders}单")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ 高级测试数据生成完成！")
    print("=" * 70)
    print("\n核心数据统计：")
    print(f"  - 员工总数: 200人")
    print(f"  - 时间跨度: 90天")
    print(f"  - 业绩记录: {performance_records_count} 条")
    print(f"  - 状态变更: {status_changes_count} 次")
    print(f"  - 测试账号: 20个（工号小写+test123）")
    print("\n建议测试流程：")
    print("  1. 用 admin/admin123 登录查看全局数据")
    print("  2. 查看主看板统计数据")
    print("  3. 进入状态检查，查看待变更员工")
    print("  4. 进入薪资统计，验证薪资计算")
    print("  5. 查看团队对比报表")
    print("  6. 用员工账号（如a001/test123）登录验证员工端")
    print("\n" + "=" * 70)


if __name__ == '__main__':
    try:
        generate_advanced_test_data()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

