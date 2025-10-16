"""测试员工登录"""
import requests

BASE_URL = "http://127.0.0.1:8080"
s = requests.Session()

# 尝试不同的员工账号
test_accounts = [
    ('a001', 'emp123'),
    ('b001', 'emp123'),
    ('c001', 'emp123'),
]

for username, password in test_accounts:
    print(f"\n测试登录: {username} / {password}")
    
    r = s.post(f"{BASE_URL}/login", data={'username': username, 'password': password}, allow_redirects=True)
    
    if "个人业绩" in r.text or "退出登录" in r.text or "navbar" in r.text:
        print(f"  ✅ 登录成功")
        
        # 访问工资单页面
        r2 = s.get(f"{BASE_URL}/employee/salary")
        print(f"  工资单页面状态: {r2.status_code}")
        
        if "工资单" in r2.text:
            print(f"  ✅ 工资单页面正常")
        else:
            print(f"  ❌ 工资单页面异常")
            print(f"  前500字符: {r2.text[:500]}")
        
        break
    else:
        print(f"  ❌ 登录失败")
        print(f"  响应前300字符: {r.text[:300]}")

