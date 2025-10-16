# 呼叫中心系统 - 新功能开发报告

**版本**: 2.0  
**日期**: 2025-10-15  
**开发状态**: 核心功能已完成，前端模板待开发

---

## 📋 需求概述

本次开发包含两个重大需求：

### 需求1：晋级确认 + 保级挑战管理系统
- **晋级确认规则**：培训期→C、C→B、B→A，需要量化指标+主管确认
- **保级挑战机制**：A级员工业绩下滑时的保级流程
- **工作日计算**：管理员自定义工作日配置
- **操作日志**：完整的审计追踪

### 需求2：工资管理系统
- **工资单生成**：从salary表同步，支持覆盖
- **工资调整**：扣款/补贴功能，权限隔离
- **发放管理**：财务角色，多种发放方式
- **年度归档**：历史数据归档查询

---

## ✅ 已完成功能清单

### 🗄️ 1. 数据库设计（已完成）

#### 新增8个核心表：
1. **`promotion_confirmations`** - 晋级确认记录表
2. **`demotion_challenges`** - 保级挑战记录表
3. **`training_assessments`** - 培训考核记录表
4. **`work_calendar`** - 工作日配置表
5. **`audit_logs`** - 操作日志表
6. **`payroll_records`** - 工资单表
7. **`payroll_adjustments`** - 工资调整记录表
8. **`payroll_archives`** - 年度归档表

#### 扩展现有表：
- **`users`** 表：新增 `finance` 角色
- **`employees`** 表：新增银行信息字段、保级挑战字段
- **`notifications`** 表：新增9种通知类型

#### 迁移脚本：
- ✅ `migrate_database.py` - 自动执行数据库迁移
- ✅ `schema_extensions.sql` - 完整的扩展SQL

---

### ⚙️ 2. 核心业务引擎（已完成）

#### 📅 **工作日计算模块** (`core/workday.py`)
```python
核心函数：
- is_workday(date) - 判断是否为工作日
- count_workdays_between(start, end) - 计算两日期间工作日数
- get_next_workday(from_date) - 获取下一个工作日
- get_recent_workdays(end_date, count) - 获取最近N个工作日
- get_next_n_workdays(start_date, count) - 获取未来N个工作日
- get_workdays_in_range(start, end) - 获取区间内所有工作日
```

**特点**：
- 未配置日期默认为工作日
- 支持管理员自定义配置
- 高效的日期计算算法

---

#### 📈 **晋级确认引擎** (`core/promotion_engine.py`)

```python
核心函数：
- check_trainee_to_c_eligible() - 检查培训期→C级资格
- check_c_to_b_eligible() - 检查C→B级资格
- check_b_to_a_eligible() - 检查B→A级资格
- trigger_promotion_confirmation() - 触发晋级确认流程
- approve_promotion() - 批准晋级
- reject_promotion() - 驳回晋级
- override_promotion() - 管理员否决
- check_all_employees_for_promotion() - 批量检查（定时任务）
```

**晋级规则**：

| 晋级路径 | 量化条件 | 额外要求 | 主管确认 | 生效时间 |
|---------|---------|---------|---------|---------|
| 培训期→C | 入职≥3工作日 | 培训考核通过 | 经理确认 | 次工作日 |
| C→B | C级≤6工作日 + 最近3日≥3单 | 无 | 经理确认 | 次工作日 |
| B→A | B级≤9工作日 + 最近6日≥12单 | 无 | 经理确认 | 次工作日 |

**关键特性**：
- ✅ 无时间限制审批（提醒持续存在）
- ✅ 管理员可否决任何审批
- ✅ 完整的通知流程
- ✅ 审计日志记录

---

#### 🏆 **保级挑战引擎** (`core/challenge_engine.py`)

```python
核心函数：
- check_a_level_demotion_alert() - 检查A级降级预警
- trigger_demotion_alert() - 触发降级预警
- make_challenge_decision() - 经理决策（降级/挑战/取消）
- check_challenge_completion() - 检查挑战进度
- finalize_challenge() - 完成挑战（确认结果）
- batch_check_challenges() - 批量检查进行中挑战
```

**保级规则**：

1. **触发条件**：最近6个工作日出单≤12单
2. **主管决策**（无时间限制）：
   - 直接降级：降为C级，次工作日生效
   - 保级挑战：启动3个工作日挑战期
   - 取消预警：恢复正常评估

3. **挑战期规则**：
   - 周期：3个工作日
   - 目标：≥9单
   - 成功：维持A级，正常薪资
   - 失败：降为C级，挑战期30元/天（提成按A级）

4. **月度限制**：每月最多1次保级挑战

---

#### 💰 **工资管理引擎** (`core/payroll_engine.py`)

```python
核心函数：
- generate_payroll_for_month() - 生成月度工资单
- adjust_payroll() - 调整工资（扣款/补贴）
- get_payroll_adjustments() - 获取调整记录
- confirm_payroll_for_payment() - 财务确认
- mark_payroll_payment() - 标记发放
- mark_payroll_payment_failed() - 标记发放失败
- retry_payroll_payment() - 重试发放
- batch_confirm_payrolls() - 批量确认
- archive_payroll_year() - 年度归档
- get_archive_summary() - 获取归档汇总
```

**工资单流程**：

```
pending (待确认) 
  ↓ 经理/管理员调整（可选）
  ↓ 财务确认
confirmed (已确认，待发放)
  ↓ 财务选择发放方式
  ↓ 财务标记发放状态
  ├─ paid (已发放)
  ├─ failed (失败) → retry (待重试)
  └─ cancelled (已取消)
```

**权限控制**：
- 管理员：可调整所有人工资
- 经理：只能调整本团队工资
- 财务：只能确认和发放，不能调整金额

---

#### 📝 **操作日志系统** (`core/audit.py`)

```python
核心函数：
- log_operation() - 通用日志记录
- log_promotion_*() - 晋级相关日志
- log_challenge_*() - 保级挑战日志
- log_training_assessment() - 培训考核日志
- log_calendar_change() - 工作日配置日志
- log_payroll_*() - 工资相关日志
- log_bank_verification() - 银行信息审核日志
- log_status_change() - 状态变更日志
- get_employee_logs() - 查询员工日志
- get_operator_logs() - 查询操作人日志
- get_recent_logs() - 查询最近日志
```

**日志内容**：
- ✅ 操作类型、模块、动作
- ✅ 操作人信息（ID、姓名、角色）
- ✅ 目标对象（员工、记录ID）
- ✅ 变更前后值
- ✅ 原因和备注
- ✅ IP地址和User-Agent
- ✅ 时间戳

---

### 🌐 3. Web路由层（已完成）

#### 👨‍💼 **经理工作台路由** (`routes/manager_routes.py`)

```python
路由列表：
✅ /manager/training_assessments - 培训考核管理
✅ /manager/training_assessments/record - 录入考核结果
✅ /manager/promotions - 晋级确认管理
✅ /manager/promotions/<id>/approve - 批准晋级
✅ /manager/promotions/<id>/reject - 驳回晋级
✅ /manager/challenges - 保级挑战管理
✅ /manager/challenges/<id>/decide - 做出决策
✅ /manager/challenges/<id>/finalize - 完成挑战
✅ /manager/payroll - 查看本团队工资
✅ /manager/logs - 查看操作日志
✅ /manager/api/check_promotion/<id> - 检查晋级资格API
✅ /manager/api/check_challenge/<id> - 检查挑战进度API
```

---

#### 👨‍💻 **管理员扩展路由** (`routes/admin_extended_routes.py`)

```python
路由列表：
✅ /admin/work_calendar - 工作日配置管理
✅ /admin/work_calendar/configure - 配置单个工作日
✅ /admin/work_calendar/batch - 批量配置工作日
✅ /admin/payroll_management - 工资管理主页
✅ /admin/payroll_management/generate - 生成工资单
✅ /admin/payroll_management/<id>/adjust - 调整工资
✅ /admin/payroll_archive - 年度归档管理
✅ /admin/payroll_archive/create - 创建归档
✅ /admin/payroll_archive/<year> - 查看归档详情
✅ /admin/bank_verification - 银行信息审核
✅ /admin/bank_verification/<id>/verify - 审核银行信息
✅ /admin/api/workday/check/<date> - 检查工作日API
✅ /admin/api/workday/count - 计算工作日数API
```

---

#### 💳 **财务工作台路由** (`routes/finance_routes.py`)

```python
路由列表：
✅ /finance/dashboard - 财务工作台主页
✅ /finance/confirm/<id> - 确认工资单
✅ /finance/batch_confirm - 批量确认工资单
✅ /finance/payment/<id> - 工资发放页面
✅ /finance/mark_failed/<id> - 标记发放失败
✅ /finance/retry/<id> - 重试发放
✅ /finance/payment_history - 发放历史记录
✅ /finance/bank_audit - 银行信息审核
✅ /finance/bank_audit/<id>/verify - 审核银行信息
✅ /finance/api/payroll/<id> - 获取工资单详情API
✅ /finance/api/stats/<year_month> - 获取月度统计API
```

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                         Web层 (Flask)                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Manager Routes│  │ Admin Routes │  │Finance Routes│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                       业务逻辑层 (Core)                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐   │
│  │  promotion_engine  │  challenge_engine  │ payroll   │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  workday  │  audit  │  notifications  │  auth       │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                      数据访问层 (Database)                    │
├─────────────────────────────────────────────────────────────┤
│              SQLite (8个新表 + 扩展现有表)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 数据流示例

### 晋级流程：
```
员工达标 → 系统自动检测 → 创建晋级记录 → 
通知经理 → 经理审批 → 更新员工状态 → 
记录日志 → 通知员工
```

### 保级挑战流程：
```
A级员工业绩下滑 → 系统触发预警 → 通知经理 → 
经理决策（降级/挑战/取消）→ 
  [挑战] → 3天挑战期 → 统计出单 → 
  判定结果 → 更新状态 → 特殊薪资计算
```

### 工资单流程：
```
管理员生成工资单 → 从salary表同步 → 
经理调整（可选）→ 财务确认 → 
财务发放 → 状态更新 → 记录日志
```

---

## 🔐 权限矩阵

| 功能模块 | 员工 | 经理 | 管理员 | 财务 |
|---------|------|------|--------|------|
| 培训考核录入 | ❌ | ✅ 本团队 | ✅ 全部 | ❌ |
| 晋级审批 | ❌ | ✅ 本团队 | ✅ 全部+否决 | ❌ |
| 保级决策 | ❌ | ✅ 本团队 | ✅ 全部 | ❌ |
| 工作日配置 | ❌ | ❌ | ✅ | ❌ |
| 工资单生成 | ❌ | ❌ | ✅ | ❌ |
| 工资调整 | ❌ | ✅ 本团队 | ✅ 全部 | ❌ |
| 工资发放 | ❌ | ❌ | ❌ | ✅ |
| 银行审核 | ❌ | ❌ | ✅ | ✅ |
| 年度归档 | ❌ | ❌ | ✅ | ❌ |
| 操作日志 | ❌ | ✅ 自己 | ✅ 全部 | ❌ |

---

## 🎨 待完成工作

### ❗ 重要：前端模板开发

由于前端HTML模板数量多、复杂度高，需要单独开发。以下是需要创建的模板列表：

#### 经理工作台模板：
1. `templates/manager/training_assessments.html` - 培训考核页面
2. `templates/manager/promotions.html` - 晋级审批页面
3. `templates/manager/challenges.html` - 保级挑战页面
4. `templates/manager/payroll.html` - 工资查看页面
5. `templates/manager/logs.html` - 操作日志页面

#### 管理员模板：
6. `templates/admin/work_calendar.html` - 工作日配置页面
7. `templates/admin/payroll_management.html` - 工资管理页面
8. `templates/admin/payroll_archive.html` - 年度归档页面
9. `templates/admin/payroll_archive_detail.html` - 归档详情页面
10. `templates/admin/bank_verification.html` - 银行信息审核页面

#### 财务工作台模板：
11. `templates/finance/dashboard.html` - 财务工作台主页
12. `templates/finance/payment.html` - 工资发放页面
13. `templates/finance/payment_history.html` - 发放历史页面
14. `templates/finance/bank_audit.html` - 银行审核页面

#### 公共组件（可选）：
15. `templates/components/promotion_card.html` - 晋级卡片组件
16. `templates/components/challenge_card.html` - 挑战卡片组件
17. `templates/components/payroll_table.html` - 工资表格组件
18. `templates/components/calendar_grid.html` - 日历网格组件

---

## 🧪 测试计划

### 1. 单元测试（核心引擎）
```bash
# 测试工作日计算
python3 -c "from core.workday import *; print(is_workday('2025-10-15'))"

# 测试晋级检测
python3 -c "from core.promotion_engine import check_trainee_to_c_eligible; print(check_trainee_to_c_eligible(1))"

# 测试保级检测
python3 -c "from core.challenge_engine import check_a_level_demotion_alert; print(check_a_level_demotion_alert(1))"
```

### 2. 集成测试（完整流程）
#### 测试场景1：培训期→C级晋级
1. 创建培训期员工
2. 录入培训考核结果（通过）
3. 等待3个工作日
4. 触发晋级确认
5. 经理批准
6. 验证员工状态变更

#### 测试场景2：A级保级挑战
1. 创建A级员工
2. 录入最近6天业绩（≤12单）
3. 触发降级预警
4. 经理选择"保级挑战"
5. 录入3天挑战期业绩
6. 完成挑战，验证结果

#### 测试场景3：工资管理流程
1. 管理员生成2025-10工资单
2. 经理调整本团队工资（扣款50元）
3. 财务批量确认
4. 财务发放（银行转账）
5. 验证状态变更和日志

### 3. 权限测试
- ✅ 经理只能看到本团队数据
- ✅ 经理不能调整其他团队工资
- ✅ 财务不能调整工资金额
- ✅ 管理员可以否决任何审批

---

## 📈 性能优化建议

### 数据库索引（已添加）
- ✅ `idx_promotion_status` - 晋级记录状态索引
- ✅ `idx_challenge_status` - 挑战记录状态索引
- ✅ `idx_payroll_month` - 工资单月份索引
- ✅ `idx_audit_operator` - 日志操作人索引
- ✅ `idx_work_calendar_date` - 工作日日期索引

### 缓存策略（待实现）
- 工作日配置缓存（减少数据库查询）
- 晋级规则配置缓存
- 用户权限缓存

---

## 🔄 后续扩展方向

### Phase 3（建议）：
1. **定时任务系统**
   - 每日自动检测晋级资格
   - 每日自动检测保级预警
   - 每月自动生成工资单

2. **数据统计报表**
   - 晋级成功率统计
   - 保级挑战成功率统计
   - 工资发放统计

3. **移动端适配**
   - 响应式设计
   - PWA支持

4. **高级权限管理**
   - 细粒度权限控制
   - 角色自定义

---

## 💡 关键技术决策

### 1. 为什么选择SQLite？
- ✅ 零配置，易于部署
- ✅ 单文件数据库，便于备份
- ✅ 足够满足中小规模团队需求
- ⚠️ 如需并发高，可迁移至PostgreSQL

### 2. 为什么无时间限制审批？
- ✅ 符合实际业务需求
- ✅ 避免自动驳回的不合理性
- ✅ 提醒持续存在，不会遗漏

### 3. 为什么工作日未配置默认为工作日？
- ✅ 简化初始配置
- ✅ 符合大多数场景
- ✅ 管理员可随时调整

---

## 📞 联系与支持

如有问题或需要进一步开发，请联系开发团队。

**文档版本**: v2.0  
**最后更新**: 2025-10-15

---

## ✅ 签署确认

- [x] 数据库设计完成
- [x] 核心引擎完成
- [x] 路由层完成
- [ ] 前端模板待开发
- [ ] 集成测试待执行
- [ ] UI/UX优化待完成

**下一步行动**: 开发前端HTML模板（14个页面）



