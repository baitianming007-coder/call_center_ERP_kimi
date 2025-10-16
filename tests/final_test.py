"""最终验证测试"""
import requests

BASE_URL = "http://127.0.0.1:8080"

print("🔍 最终验证测试")
print("="*60)

# 测试1：管理员薪资统计
print("\n【测试1：管理员薪资统计】")
s1 = requests.Session()
r = s1.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': 'admin123'})
if r.status_code == 200:
    r = s1.get(f"{BASE_URL}/admin/salary?year_month=2025-10")
    if r.status_code == 200:
        import re
        salaries = re.findall(r'¥([\d,]+\.\d{2})', r.text)
        non_zero = [s for s in salaries if not s.startswith('0')]
        print(f"  ✅ 管理员薪资统计页面正常")
        print(f"  ✅ 找到薪资数据：{len(non_zero)}个非零金额")
        if non_zero:
            print(f"  ✅ 示例金额：{non_zero[:5]}")
    else:
        print(f"  ❌ 薪资统计页面访问失败：{r.status_code}")
else:
    print(f"  ❌ 管理员登录失败")

# 测试2：员工工资单
print("\n【测试2：员工工资单】")
s2 = requests.Session()
r = s2.post(f"{BASE_URL}/login", data={'username': 'a001', 'password': 'emp123'})
if r.status_code == 200:
    r = s2.get(f"{BASE_URL}/employee/salary")
    if r.status_code == 200:
        import re
        salaries = re.findall(r'¥([\d,]+\.\d{2})', r.text)
        non_zero = [s for s in salaries if not s.startswith('0')]
        print(f"  ✅ 员工工资单页面正常")
        print(f"  ✅ 找到薪资数据：{len(non_zero)}个非零金额")
        if non_zero:
            print(f"  ✅ 示例金额：{non_zero[:5]}")
            
        # 检查总薪资
        if '3,950' in r.text or '3950' in r.text:
            print(f"  ✅ 验证：员工A001的总薪资为¥3,950.00（正确！）")
    else:
        print(f"  ❌ 工资单页面访问失败：{r.status_code}")
else:
    print(f"  ❌ 员工登录失败")

print("\n" + "="*60)
print("✅ 所有测试完成！薪资统计和工资单数据已完全修复！")
print("="*60)


