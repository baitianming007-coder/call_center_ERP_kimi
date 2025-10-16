"""
呼叫中心职场管理系统 - 主应用
"""
from flask import Flask, render_template, redirect, url_for
from datetime import timedelta
from config import Config
from core.database import close_db, get_db
from core.auth import get_current_user

# 创建 Flask 应用
app = Flask(__name__)
app.config.from_object(Config)

# 注册数据库关闭钩子
app.teardown_appcontext(close_db)

# 导入并注册 Blueprint
from routes import (
    auth_routes, employee_routes, admin_routes, 
    export_routes, notification_routes, report_routes,
    manager_routes, admin_extended_routes, finance_routes,
    tools_routes
)

app.register_blueprint(auth_routes.bp)
app.register_blueprint(employee_routes.bp)
app.register_blueprint(admin_routes.bp)
app.register_blueprint(export_routes.bp)
app.register_blueprint(notification_routes.bp)
app.register_blueprint(report_routes.bp)
app.register_blueprint(manager_routes.bp)
app.register_blueprint(admin_extended_routes.bp)
app.register_blueprint(finance_routes.bp)
app.register_blueprint(tools_routes.bp)


@app.route('/check_users_tool')
def check_users_tool():
    """用户账号检查工具"""
    with open('check_users.html', 'r', encoding='utf-8') as f:
        return f.read()


@app.route('/')
def index():
    """首页：根据登录状态跳转"""
    user = get_current_user()
    
    if user:
        if user['role'] == 'employee':
            return redirect(url_for('employee.performance'))
        else:
            return redirect(url_for('admin.dashboard'))
    
    return redirect(url_for('auth.login'))


@app.after_request
def add_no_cache_headers(response):
    """添加禁用缓存的响应头，确保浏览器总是获取最新内容"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


@app.context_processor
def inject_user():
    """向所有模板注入当前用户"""
    return dict(current_user=get_current_user())


@app.template_filter('format_currency')
def format_currency(value):
    """货币格式化"""
    try:
        return f"¥{float(value):,.2f}"
    except:
        return "¥0.00"


@app.template_filter('format_date')
def format_date(value):
    """日期格式化"""
    if not value:
        return ''
    return str(value)


@app.template_filter('status_label')
def status_label(status):
    """状态标签"""
    labels = {
        'trainee': '培训期',
        'C': 'C级',
        'B': 'B级',
        'A': 'A级',
        'eliminated': '已淘汰'
    }
    return labels.get(status, status)


@app.template_filter('status_color')
def status_color(status):
    """状态颜色"""
    colors = {
        'trainee': '#9CA3AF',
        'C': '#F59E0B',
        'B': '#3B82F6',
        'A': '#10B981',
        'eliminated': '#EF4444'
    }
    return colors.get(status, '#6B7280')


@app.template_filter('role_label')
def role_label(role):
    """角色标签"""
    labels = {
        'employee': '员工',
        'manager': '经理',
        'admin': '管理员',
        'finance': '财务'
    }
    return labels.get(role, role)


if __name__ == '__main__':
    print("=" * 60)
    print("呼叫中心职场管理系统")
    print("=" * 60)
    print("访问地址: http://127.0.0.1:8080")
    print("默认账号:")
    print("  管理员: admin / 123456")
    print("  经理: manager / 123456")
    print("  财务: finance / 123456")
    print("  员工: a001 / 123456")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=8080)

