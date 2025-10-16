# 大规模业务逻辑测试套件

## 概述

本测试套件用于验证系统在500人×6个月场景下的核心业务逻辑：
- 晋级流程（量化达标+主管确认）
- A级保级挑战全流程
- 各阶段薪资计算
- 异常场景处理

## 测试数据规模

- **员工数量**: 500人
- **时间范围**: 2025-01-01 至 2025-06-30（6个月）
- **业绩记录**: 约90,000条
- **员工类型分布**:
  - 快速成长型: 100人（20%）
  - 达标波动型: 200人（40%）
  - 待淘汰型: 125人（25%）
  - 特殊规则型: 75人（15%）

## 快速开始

### 方式1: 一键运行完整测试

```bash
cd "/Users/kimi/Desktop/call center 2.0"
python3 tests/large_scale_test/run_full_test.py
```

预计耗时: 20-30分钟

### 方式2: 分步执行

```bash
# 步骤1: 生成测试数据
python3 tests/large_scale_test/data_generator.py

# 步骤2: 导入数据到数据库
python3 tests/large_scale_test/import_data.py

# 步骤3: 执行触发检测
python3 tests/large_scale_test/trigger_checks.py

# 步骤4: 模拟主管操作
python3 tests/large_scale_test/supervisor_simulation.py

# 步骤5: 验证业务逻辑
python3 tests/large_scale_test/business_validator.py

# 步骤6: 生成测试报告
python3 tests/large_scale_test/generate_report.py
```

## 输出文件

所有输出文件位于 `tests/large_scale_test/output/`:

- `employees.csv` - 员工基础信息
- `daily_performance.csv` - 每日业绩数据
- `expected_events.json` - 预期触发事件
- `trigger_log.txt` - 触发事件日志
- `supervisor_operations.log` - 主管操作日志
- `validation_results.json` - 验证结果（JSON格式）
- `test_report.md` - 详细测试报告（Markdown格式）
- `test_summary.json` - 测试摘要（JSON格式）

## 验证项目

### 1. 晋级逻辑验证
- ✓ 所有晋级同时满足"量化达标"+"主管确认"
- ✓ 晋级生效时间为"主管确认次日"
- ✓ 驳回后需重新达标才能再次触发
- ✓ 逾期未处理触发二次提醒

### 2. 保级挑战验证
- ✓ 触发条件正确（最近6个工作日≤12单）
- ✓ 挑战周期准确（3个工作日）
- ✓ 成功/失败判定正确（3天≥9单）
- ✓ 每月保级次数≤1次
- ✓ 主管逾期未处理的系统默认行为

### 3. 薪资计算验证
- ✓ 各阶段固定薪资计算（trainee/C/B/A）
- ✓ 保级期间薪资特殊规则
- ✓ 提成阶梯计算（1-3单10元、4-5单20元、≥6单30元）
- ✓ 绩效奖金档位（<75:0、75-99:300、100-124:600、≥125:1000）
- ✓ 全勤奖条件（有效出勤≥25 + 最近6个工作日出单≥12）

### 4. 数据一致性验证
- ✓ 员工状态变更与薪资核算周期匹配
- ✓ 所有审批操作日志完整留存
- ✓ 状态流转时间链完整

## 配置参数

可在 `config.py` 中调整测试参数：

```python
TOTAL_EMPLOYEES = 500  # 员工数量
START_DATE = date(2025, 1, 1)  # 开始日期
END_DATE = date(2025, 6, 30)  # 结束日期
NUM_SUPERVISORS = 5  # 主管数量
```

## 注意事项

1. **数据库备份**: 导入测试数据前会自动备份数据库到 `data/callcenter_backup_before_test.db`
2. **服务器运行**: 主管操作模拟需要Flask服务器运行在 `http://127.0.0.1:8080`
3. **数据清理**: 测试会清空现有的员工和业绩数据，请确保已备份重要数据
4. **执行时间**: 完整测试约需20-30分钟，请耐心等待

## 故障排除

### 数据生成失败
- 检查系统时间是否正确
- 确保有足够的磁盘空间（至少100MB）

### 导入失败
- 确保数据库文件可写
- 检查CSV文件是否完整生成

### 主管操作失败
- 确保Flask服务器正在运行
- 检查端口8080是否被占用

### 验证失败
- 查看 `validation_results.json` 了解具体失败原因
- 检查数据库中是否有正确的表结构

## 查看测试报告

测试完成后，查看详细报告：

```bash
cat tests/large_scale_test/output/test_report.md
```

或在文本编辑器中打开该文件。

## 技术架构

- **数据生成**: 基于员工类型生成差异化行为数据
- **工作日计算**: 使用 `core/workday.py` 确保与系统逻辑一致
- **批量导入**: 使用 `executemany()` 优化性能，每批1000条
- **主管模拟**: 使用 `requests.Session` 模拟HTTP请求
- **业务验证**: 抽样验证+全量检查相结合

## 扩展性

可以轻松扩展测试规模：

```python
# 测试1000人×12个月
TOTAL_EMPLOYEES = 1000
END_DATE = date(2025, 12, 31)
```

注意：更大规模的测试需要更长的执行时间。

## 许可证

本测试套件作为呼叫中心管理系统的一部分，遵循相同的许可证条款。




