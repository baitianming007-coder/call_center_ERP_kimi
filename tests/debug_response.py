"""调试响应内容"""
import requests

BASE_URL = "http://127.0.0.1:8080"

s = requests.Session()

# 登录
login_data = {'username': 'admin', 'password': 'admin123'}
r = s.post(f"{BASE_URL}/login", data=login_data, allow_redirects=True)
print(f"登录状态: {r.status_code}")
print(f"登录响应前300字符:\n{r.text[:300]}\n")

# 访问薪资页面
r = s.get(f"{BASE_URL}/admin/salary?year_month=2025-10")
print(f"薪资页面状态: {r.status_code}")
print(f"页面长度: {len(r.text)}")
print(f"\n检查关键词:")
print(f"  '薪资统计' 存在: {'薪资统计' in r.text}")
print(f"  'salary_list' 存在: {'salary_list' in r.text}")
print(f"  '该月份暂无薪资数据' 存在: {'该月份暂无薪资数据' in r.text}")
print(f"  '<table' 存在: {'<table' in r.text}")
print(f"  '总薪资' 存在: {'总薪资' in r.text}")

print(f"\n前1000字符:\n{r.text[:1000]}")


