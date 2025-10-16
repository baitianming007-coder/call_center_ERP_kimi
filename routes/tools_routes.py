"""
工具和管理路由
用于系统诊断和修复
"""
from flask import Blueprint, jsonify, render_template_string
from core.database import query_db, execute_db, get_db
from core.auth import hash_password, verify_password

bp = Blueprint('tools', __name__, url_prefix='/api')


@bp.route('/check_users')
def check_users():
    """检查当前用户"""
    users = query_db('SELECT username, role FROM users ORDER BY role, username')
    return jsonify({
        'count': len(users),
        'users': [{'username': u['username'], 'role': u['role']} for u in users]
    })


@bp.route('/fix_users', methods=['POST'])
def fix_users():
    """紧急修复用户账号"""
    db = get_db()
    cursor = db.cursor()
    
    # 清空现有用户
    cursor.execute('DELETE FROM users')
    
    # 统一密码
    pwd = hash_password('123456')
    
    # 创建测试账号
    accounts = [
        ('admin', pwd, 'admin'),
        ('manager', pwd, 'manager'),
        ('manager001', pwd, 'manager'),
        ('manager002', pwd, 'manager'),
        ('manager003', pwd, 'manager'),
        ('manager004', pwd, 'manager'),
        ('manager005', pwd, 'manager'),
        ('finance', pwd, 'finance'),
    ]
    
    account_list = []
    for username, password, role in accounts:
        cursor.execute(
            'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
            (username, password, role)
        )
        account_list.append(f"{username} ({role})")
    
    # 创建员工账号
    cursor.execute('SELECT id, employee_no FROM employees WHERE is_active = 1 LIMIT 10')
    for emp_id, emp_no in cursor.fetchall():
        username = emp_no.lower()
        cursor.execute(
            'INSERT OR IGNORE INTO users (username, password, role, employee_id) VALUES (?, ?, ?, ?)',
            (username, pwd, 'employee', emp_id)
        )
        account_list.append(f"{username} (employee)")
    
    db.commit()
    
    return jsonify({
        'success': True,
        'count': len(account_list),
        'accounts': account_list
    })


@bp.route('/test_login')
def test_login():
    """测试登录功能"""
    test_accounts = [
        ('admin', '123456'),
        ('manager', '123456'),
        ('finance', '123456'),
        ('a001', '123456'),
    ]
    
    results = []
    for username, password in test_accounts:
        user = query_db(
            'SELECT * FROM users WHERE username = ?',
            [username],
            one=True
        )
        
        if user and verify_password(password, user['password']):
            results.append({'username': username, 'success': True})
        else:
            results.append({'username': username, 'success': False})
    
    return jsonify({
        'results': results
    })




