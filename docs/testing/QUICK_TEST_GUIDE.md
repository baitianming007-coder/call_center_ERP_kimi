# 🧪 快速测试指南

**目的**: 验证核心功能是否正常运行  
**前提**: 数据库已迁移完成

---

## 📋 测试前准备

### 1. 启动应用
```bash
cd "/Users/kimi/Desktop/call center 2.0"
python3 app.py
```

### 2. 验证数据库迁移
```bash
sqlite3 data/callcenter.db ".tables"
```

应该看到以下新表：
- promotion_confirmations
- demotion_challenges
- training_assessments
- work_calendar
- audit_logs
- payroll_records
- payroll_adjustments
- payroll_archives

---

## ✅ 核心功能测试

### 测试1：工作日计算功能

```bash
# 进入Python交互式环境
python3

# 测试代码
from core.workday import *
from datetime import date

# 测试1：判断今天是否为工作日
print("今天是工作日吗？", is_workday(date.today()))

# 测试2：计算最近7天的工作日数
from datetime import timedelta
start = date.today() - timedelta(days=7)
count = count_workdays_between(start, date.today())
print(f"最近7天工作日数：{count}")

# 测试3：获取最近3个工作日
recent = get_recent_workdays(date.today(), 3)
print("最近3个工作日：", [str(d) for d in recent])
```

**预期结果**: 
- 未配置日期默认为工作日
- 计数正确
- 日期列表正确

---

### 测试2：晋级引擎功能

```bash
python3

from core.promotion_engine import *
from core.database import query_db

# 查找一个培训期员工
trainee = query_db("SELECT id FROM employees WHERE status='trainee' LIMIT 1", one=True)

if trainee:
    # 检查晋级资格
    result = check_trainee_to_c_eligible(trainee['id'])
    print("晋级资格检查结果：", result)
else:
    print("没有找到培训期员工")
```

**预期结果**:
- 能正确检测工作日数
- 能正确检测培训考核状态
- 返回详细的原因说明

---

### 测试3：保级挑战引擎功能

```bash
python3

from core.challenge_engine import *
from core.database import query_db

# 查找一个A级员工
a_level = query_db("SELECT id FROM employees WHERE status='A' LIMIT 1", one=True)

if a_level:
    # 检查是否触发降级预警
    result = check_a_level_demotion_alert(a_level['id'])
    print("降级预警检查结果：", result)
else:
    print("没有找到A级员工")
```

**预期结果**:
- 能正确统计最近6个工作日出单数
- 能正确判断是否触发预警
- 返回详细的原因说明

---

### 测试4：工资单生成功能

```bash
python3

from core.payroll_engine import *
from datetime import date

# 生成当月工资单（测试模式）
year_month = date.today().strftime('%Y-%m')
result = generate_payroll_for_month(year_month, overwrite=False, operator_id=1, operator_name='测试')

print("工资单生成结果：", result)
```

**预期结果**:
- 能从salary表同步数据
- 生成成功并返回统计信息
- 如果已存在会提示

---

### 测试5：操作日志功能

```bash
python3

from core.audit import *

# 记录一条测试日志
log_id = log_operation(
    operation_type='test',
    operation_module='testing',
    operation_action='unit_test',
    notes='这是一条测试日志',
    operator_id=1,
    operator_name='测试员',
    operator_role='admin'
)

print(f"日志记录ID：{log_id}")

# 查询最近日志
logs = get_recent_logs(limit=5)
for log in logs:
    print(f"  - {log['operation_type']}: {log['notes']}")
```

**预期结果**:
- 日志记录成功
- 能查询到刚刚记录的日志

---

## 🔍 数据库验证测试

### 测试新表是否正常工作

```bash
sqlite3 data/callcenter.db

-- 测试1：检查工作日配置表
SELECT COUNT(*) FROM work_calendar;

-- 测试2：检查晋级记录表
SELECT COUNT(*) FROM promotion_confirmations;

-- 测试3：检查操作日志表
SELECT COUNT(*) FROM audit_logs;

-- 测试4：检查工资单表
SELECT COUNT(*) FROM payroll_records;

-- 测试5：验证users表finance角色
SELECT * FROM users WHERE role='finance';

-- 应该看到finance账号（如果之前迁移成功）
```

---

## 🌐 Web接口测试（如果有前端）

### 测试经理工作台路由
```bash
curl -I http://127.0.0.1:8080/manager/promotions
curl -I http://127.0.0.1:8080/manager/challenges
curl -I http://127.0.0.1:8080/manager/training_assessments
```

### 测试管理员路由
```bash
curl -I http://127.0.0.1:8080/admin/work_calendar
curl -I http://127.0.0.1:8080/admin/payroll_management
curl -I http://127.0.0.1:8080/admin/payroll_archive
```

### 测试财务路由
```bash
curl -I http://127.0.0.1:8080/finance/dashboard
curl -I http://127.0.0.1:8080/finance/payment_history
```

**预期结果**: 
- 如果有登录：返回200或302
- 如果未登录：返回302（重定向到登录页）
- 不应该返回404（路由不存在）或500（服务器错误）

---

## 🚨 常见问题排查

### 问题1：路由404错误
**原因**: app.py未正确注册新路由  
**解决**: 检查app.py中是否导入并注册了manager_routes、admin_extended_routes、finance_routes

### 问题2：数据库表不存在
**原因**: 未执行数据库迁移  
**解决**: 运行 `python3 migrate_database.py`

### 问题3：导入模块错误
**原因**: 新创建的core模块未找到  
**解决**: 确认文件存在于正确路径：
- core/workday.py
- core/promotion_engine.py
- core/challenge_engine.py
- core/payroll_engine.py
- core/audit.py

### 问题4：finance账号不存在
**原因**: schema_extensions.sql中的初始化SQL未执行  
**解决**: 手动创建finance账号：
```sql
INSERT INTO users (username, password, role) 
VALUES ('finance', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'finance');
```

---

## 📊 测试结果记录

请填写测试结果：

- [ ] 数据库迁移成功
- [ ] 工作日计算功能正常
- [ ] 晋级引擎功能正常
- [ ] 保级挑战引擎功能正常
- [ ] 工资单生成功能正常
- [ ] 操作日志功能正常
- [ ] Web路由正常（如果有前端）
- [ ] Finance账号存在且可登录

---

## ⏭️ 下一步

测试通过后，可以进行：
1. 前端模板开发
2. 完整的集成测试
3. UI/UX优化
4. 生产环境部署

**测试完成日期**: __________  
**测试人**: __________  
**测试状态**: ☐ 通过 ☐ 未通过（需修复）



