"""
测试配置文件
"""
from datetime import date

# 测试数据规模配置
TOTAL_EMPLOYEES = 500
START_DATE = date(2025, 1, 1)
END_DATE = date(2025, 6, 30)

# 员工类型分布（总数应为TOTAL_EMPLOYEES）
EMPLOYEE_DISTRIBUTION = {
    'fast_growth': 100,      # 快速成长型 20%
    'fluctuating': 200,      # 达标波动型 40%
    'underperforming': 125,  # 待淘汰型 25%
    'edge_case': 75          # 特殊规则型 15%
}

# 主管配置
NUM_SUPERVISORS = 5
SUPERVISOR_PASSWORD = '123456'

# 主管操作分布（总和应为100%）
SUPERVISOR_OPERATION_DISTRIBUTION = {
    'timely_approve': 0.80,    # 及时确认 80%
    'delayed_approve': 0.10,   # 逾期确认 10%
    'reject': 0.07,            # 驳回 7%
    'no_action': 0.03          # 逾期未处理 3%
}

# 业务规则参数（与系统保持一致）
BUSINESS_RULES = {
    'trainee_to_c': {
        'workdays': 3,
        'requires_assessment': True
    },
    'c_to_b': {
        'max_workdays': 6,
        'recent_days': 3,
        'min_orders': 3
    },
    'b_to_a': {
        'max_workdays': 9,
        'recent_days': 6,
        'min_orders': 12
    },
    'a_demotion_threshold': {
        'recent_days': 6,
        'min_orders': 12
    },
    'challenge': {
        'workdays': 3,
        'target_orders': 9,
        'monthly_limit': 1
    }
}

# 提成阶梯规则
COMMISSION_RULES = {
    'tier1': {'max_orders': 3, 'rate': 10},
    'tier2': {'max_orders': 5, 'rate': 20},
    'tier3': {'rate': 30}
}

# 薪资规则
SALARY_RULES = {
    'A': {
        'base': 2200,
        'attendance_bonus': 400,
        'attendance_threshold': 25,
        'performance_tiers': [
            (0, 74, 0),
            (75, 99, 300),
            (100, 124, 600),
            (125, float('inf'), 1000)
        ]
    },
    'B': {
        'daily_rate': 88,
        'max_days': 6
    },
    'C': {
        'daily_rate': 30,
        'max_total': 90
    }
}

# 输出路径配置
OUTPUT_DIR = 'tests/large_scale_test/output'
EMPLOYEES_CSV = f'{OUTPUT_DIR}/employees.csv'
PERFORMANCE_CSV = f'{OUTPUT_DIR}/daily_performance.csv'
EXPECTED_EVENTS_JSON = f'{OUTPUT_DIR}/expected_events.json'
TRIGGER_LOG = f'{OUTPUT_DIR}/trigger_log.txt'
SUPERVISOR_LOG = f'{OUTPUT_DIR}/supervisor_operations.log'
VALIDATION_RESULTS = f'{OUTPUT_DIR}/validation_results.json'
TEST_REPORT_MD = f'{OUTPUT_DIR}/test_report.md'
TEST_SUMMARY_JSON = f'{OUTPUT_DIR}/test_summary.json'

# 数据库备份配置
DB_PATH = 'data/callcenter.db'
DB_BACKUP_PATH = 'data/callcenter_backup_before_test.db'

