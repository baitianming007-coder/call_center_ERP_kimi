"""检查工资单数据显示"""
import requests

BASE_URL = "http://127.0.0.1:8080"

# 登录
s = requests.Session()
r = s.post(f"{BASE_URL}/login", data={'username': 'a001', 'password': 'emp123'}, allow_redirects=True)

if "个人业绩" in r.text or "navbar" in r.text:
    print("✅ 员工登录成功")
    
    # 访问工资单页面
    r = s.get(f"{BASE_URL}/employee/salary")
    
    print(f"\n工资单页面状态: {r.status_code}")
    print(f"页面长度: {len(r.text)} 字符")
    
    # 检查关键内容
    checks = {
        "个人薪资": "个人薪资" in r.text,
        "本月薪资": "本月薪资" in r.text,
        "历史工资单": "历史工资单" in r.text,
        "薪资数据": ("current_salary" in r.text or "salary_history" in r.text),
        "提成": "提成" in r.text,
        "底薪": ("底薪" in r.text or "固定" in r.text),
    }
    
    print("\n关键内容检查:")
    for key, value in checks.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}")
    
    # 检查是否有数据显示
    if "¥0.00" in r.text or "暂无" in r.text:
        print("\n⚠️  可能没有数据或数据为空")
    
    # 查找薪资相关数字
    import re
    currency_pattern = r'¥[\d,]+\.\d{2}'
    currencies = re.findall(currency_pattern, r.text)
    if currencies:
        print(f"\n找到的金额数据: {currencies[:10]}")
    else:
        print("\n❌ 未找到任何金额数据")
        
else:
    print("❌ 员工登录失败")

