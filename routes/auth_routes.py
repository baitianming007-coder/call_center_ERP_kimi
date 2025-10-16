"""
认证路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from core.auth import authenticate_user

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('请输入用户名和密码', 'warning')
            return render_template('login.html')
        
        user = authenticate_user(username, password)
        
        if user:
            # 设置 session
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['employee_id'] = user['employee_id']
            session.permanent = True
            
            # 根据角色跳转
            next_url = request.args.get('next')
            if next_url:
                return redirect(next_url)
            
            # 不同角色跳转到各自的工作台
            if user['role'] == 'employee':
                return redirect(url_for('employee.performance'))
            elif user['role'] == 'manager':
                return redirect(url_for('manager.promotions'))
            elif user['role'] == 'finance':
                return redirect(url_for('finance.dashboard'))
            elif user['role'] == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                # 默认跳转到管理员页面
                return redirect(url_for('admin.dashboard'))
        else:
            flash('用户名或密码错误', 'danger')
    
    return render_template('login.html')


@bp.route('/logout')
def logout():
    """登出"""
    session.clear()
    flash('已成功退出登录', 'success')
    return redirect(url_for('auth.login'))


