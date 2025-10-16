#!/usr/bin/env python3
"""
快速功能验证脚本
验证系统基本功能可用性
"""

import requests
import sys

BASE_URL = 'http://127.0.0.1:8080'

def test_login(username, password):
    """测试登录"""
    s = requests.Session()
    r = s.post(f'{BASE_URL}/login', data={
        'username': username,
        'password': password
    }, allow_redirects=False)
    
    if r.status_code == 302:  # 重定向表示登录成功
        print(f'✅ 登录成功: {username}')
        return s
    else:
        # 获取实际响应内容
        r2 = s.post(f'{BASE_URL}/login', data={
            'username': username,
            'password': password
        })
        if '主看板' in r2.text or 'dashboard' in r2.text:
            print(f'✅ 登录成功: {username}')
            return s
        print(f'❌ 登录失败: {username}')
        return None

def test_page(session, path, expected_text, name):
    """测试页面访问"""
    try:
        r = session.get(f'{BASE_URL}{path}')
        if r.status_code == 200 and expected_text in r.text:
            print(f'✅ {name}')
            return True
        else:
            print(f'❌ {name} - Status: {r.status_code}')
            return False
    except Exception as e:
        print(f'❌ {name} - Error: {e}')
        return False

def main():
    print('🔍 系统快速功能验证\n')
    
    # 测试登录页面
    try:
        r = requests.get(f'{BASE_URL}/login')
        if r.status_code == 200:
            print('✅ 登录页面可访问')
        else:
            print('❌ 登录页面无法访问')
            sys.exit(1)
    except:
        print('❌ 服务器未运行')
        sys.exit(1)
    
    # 测试管理员登录
    admin_session = test_login('admin', 'admin123')
    if not admin_session:
        # 尝试其他密码
        admin_session = test_login('admin', '123456')
    
    if admin_session:
        print('\n📋 测试管理员功能:')
        test_page(admin_session, '/admin/dashboard', '主看板', '主看板')
        test_page(admin_session, '/admin/employees', '员工管理', '员工管理')
        test_page(admin_session, '/admin/performance', '业绩管理', '业绩管理')
        test_page(admin_session, '/admin/salary', '薪资统计', '薪资统计')
    
    # 测试员工登录
    print('\n📋 测试员工功能:')
    emp_session = test_login('a001', 'emp123')
    if not emp_session:
        emp_session = test_login('a001', '123456')
    
    if emp_session:
        test_page(emp_session, '/employee/profile', '个人中心', '个人中心')
        test_page(emp_session, '/employee/performance', '业绩记录', '业绩查看')
    
    print('\n✨ 基础验证完成')

if __name__ == '__main__':
    main()

