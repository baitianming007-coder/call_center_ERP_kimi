"""
认证与权限控制模块
"""
import hashlib
from functools import wraps
from flask import session, redirect, url_for, flash, request
from core.database import query_db


def hash_password(password):
    """SHA256 密码哈希"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(password, hashed):
    """验证密码"""
    return hash_password(password) == hashed


def authenticate_user(username, password):
    """
    用户认证
    
    Args:
        username: 用户名
        password: 密码（明文）
        
    Returns:
        dict or None: 用户信息（不含密码）或 None
    """
    user = query_db(
        'SELECT id, username, password, role, employee_id FROM users WHERE username = ?',
        (username,),
        one=True
    )
    
    if user and verify_password(password, user['password']):
        return {
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'employee_id': user['employee_id']
        }
    
    return None


def get_current_user():
    """获取当前登录用户信息"""
    if 'user_id' in session:
        user = query_db(
            'SELECT id, username, role, employee_id FROM users WHERE id = ?',
            (session['user_id'],),
            one=True
        )
        if user:
            return dict(user)
    return None


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    """
    角色验证装饰器
    
    Usage:
        @role_required('admin')
        @role_required('admin', 'manager')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                flash('请先登录', 'warning')
                return redirect(url_for('auth.login'))
            
            if user['role'] not in allowed_roles:
                flash('您没有权限访问此页面', 'danger')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_user_team(user):
    """
    获取用户所属团队（对于 manager）
    
    Args:
        user: 用户信息字典
        
    Returns:
        str or None: 团队名称，admin 返回 None（全量），employee 返回员工团队
    """
    if user['role'] == 'admin':
        return None  # admin 可见全部
    
    if user['role'] == 'manager':
        # manager 需要查询其管理的团队
        # 简化实现：这里假设 manager 用户名关联了团队配置
        # 实际应该有单独的 manager_teams 表
        # 这里使用系统参数表来配置
        param = query_db(
            "SELECT param_value FROM system_params WHERE param_key = ?",
            (f"manager_team_{user['username']}",),
            one=True
        )
        if param:
            return param['param_value']
        
        # 默认返回 'A组'（示例）
        return 'A组'
    
    # employee 返回其所属团队
    if user['employee_id']:
        emp = query_db(
            'SELECT team FROM employees WHERE id = ?',
            (user['employee_id'],),
            one=True
        )
        if emp:
            return emp['team']
    
    return None


def apply_team_filter(query, user, table_alias='employees'):
    """
    应用团队数据过滤（用于 SQL 查询）
    
    Args:
        query: 原始 SQL 查询
        user: 用户信息
        table_alias: 表别名，默认 'employees'
        
    Returns:
        tuple: (modified_query, additional_params)
    """
    if user['role'] == 'admin':
        return query, ()
    
    team = get_user_team(user)
    if team:
        # 添加 team 过滤条件
        if 'WHERE' in query.upper():
            query += f' AND {table_alias}.team = ?'
        else:
            query += f' WHERE {table_alias}.team = ?'
        return query, (team,)
    
    return query, ()


def check_employee_access(user, employee_id):
    """
    检查用户是否有权限访问指定员工的数据
    
    Args:
        user: 用户信息
        employee_id: 员工ID
        
    Returns:
        bool: 是否有权限
    """
    if user['role'] == 'admin':
        return True
    
    if user['role'] == 'employee':
        # 员工只能访问自己的数据
        return user['employee_id'] == employee_id
    
    if user['role'] == 'manager':
        # manager 只能访问本团队员工
        team = get_user_team(user)
        if team:
            emp = query_db(
                'SELECT team FROM employees WHERE id = ?',
                (employee_id,),
                one=True
            )
            return emp and emp['team'] == team
    
    return False


def encrypt_phone(phone):
    """
    加密手机号（简单实现）
    实际应使用 cryptography 库的对称加密
    """
    if not phone:
        return None
    # 这里简化实现，实际应使用 Fernet 等加密算法
    from config import Config
    key = Config.ENCRYPTION_KEY
    # 确保 key 是字符串
    if isinstance(key, bytes):
        key = key.decode('utf-8')
    # 简单 XOR 加密示例（生产环境应使用专业加密库）
    encrypted = ''.join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(phone))
    return encrypted.encode('utf-8').hex()


def decrypt_phone(encrypted_phone):
    """
    解密手机号
    """
    if not encrypted_phone:
        return None
    try:
        from config import Config
        key = Config.ENCRYPTION_KEY
        # 确保 key 是字符串
        if isinstance(key, bytes):
            key = key.decode('utf-8')
        decrypted_bytes = bytes.fromhex(encrypted_phone)
        decrypted = ''.join(chr(b ^ ord(key[i % len(key)])) for i, b in enumerate(decrypted_bytes))
        return decrypted
    except:
        return None

