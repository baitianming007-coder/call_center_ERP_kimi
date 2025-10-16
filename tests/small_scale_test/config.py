#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小规模测试配置文件
"""

from datetime import datetime, date

# ==================== 基本配置 ====================

# 测试周期
START_DATE = date(2025, 5, 1)
END_DATE = date(2025, 10, 31)

# 员工配置
EMPLOYEES_PER_MONTH = 50
TOTAL_MONTHS = 6
TOTAL_EMPLOYEES = EMPLOYEES_PER_MONTH * TOTAL_MONTHS  # 300人

# 员工编号前缀
EMPLOYEE_PREFIX = 'TEST'

# ==================== 入职批次配置 ====================

BATCH_DATES = [
    date(2025, 5, 1),   # 第1批：TEST001-TEST050
    date(2025, 6, 1),   # 第2批：TEST051-TEST100
    date(2025, 7, 1),   # 第3批：TEST101-TEST150
    date(2025, 8, 1),   # 第4批：TEST151-TEST200
    date(2025, 9, 1),   # 第5批：TEST201-TEST250
    date(2025, 10, 1),  # 第6批：TEST251-TEST300
]

# ==================== 团队和主管配置 ====================

TEAMS = ['Team1', 'Team2', 'Team3', 'Team4', 'Team5']
MANAGERS = ['manager001', 'manager002', 'manager003', 'manager004', 'manager005']

# ==================== 业绩模式配置 ====================

# 业绩类型分布比例
PERFORMANCE_TYPES = {
    'excellent': 0.30,   # 优秀型 30%
    'normal': 0.50,      # 正常型 50%
    'poor': 0.20,        # 待提升型 20%
}

# 各类型的出单范围（日均）
ORDERS_RANGE = {
    'excellent': (4, 6),   # 4-6单/天
    'normal': (2, 4),      # 2-4单/天
    'poor': (0, 2),        # 0-2单/天
}

# 订单金额范围
REVENUE_PER_ORDER = (150, 300)

# 通话时长范围（分钟）
CALL_DURATION_RANGE = (180, 420)

# ==================== 出勤模式配置 ====================

# 出勤率范围
ATTENDANCE_RATE = {
    'high': (0.95, 1.0),      # 95-100%
    'medium': (0.85, 0.95),   # 85-95%
    'low': (0.70, 0.85),      # 70-85%
}

# 出勤模式分布
ATTENDANCE_DISTRIBUTION = {
    'high': 0.70,      # 70%高出勤
    'medium': 0.20,    # 20%中等出勤
    'low': 0.10,       # 10%低出勤
}

# ==================== 工作日配置 ====================

# 周日为休息日
WEEKEND_DAYS = [6]  # 6 = Sunday (Monday is 0)

# ==================== 晋升规则配置 ====================
# 注意：这个配置仅用于测试数据生成参考
# 核心业务逻辑由 core/promotion_engine.py 控制（已验证符合产品文档）

PROMOTION_RULES = {
    'trainee_to_c': {
        'min_workdays': 3,  # 产品文档：在岗满3天自动转C
        'description': '在岗满3天自动转C'
    },
    'c_to_b': {
        'max_workdays': 6,  # 产品文档：C在岗天数≤6
        'recent_days': 3,   # 产品文档：最近3天
        'min_orders': 3,    # 产品文档：累计出单≥3
        'description': 'C级周期≤6个工作日 且 最近3个工作日出单≥3单'
    },
    'b_to_a': {
        'max_workdays': 9,  # 产品文档：B在岗天数≤9
        'recent_days': 6,   # 产品文档：最近6天
        'min_orders': 12,   # 产品文档：累计出单≥12
        'description': 'B级周期≤9个工作日 且 最近6个工作日出单≥12单'
    }
}

# ==================== 保级规则配置 ====================

DEMOTION_RULES = {
    'a_challenge_threshold': 50,   # A级月单<50触发挑战
    'challenge_pass_threshold': 80,  # 挑战月单>=80为通过
    'max_consecutive_challenges': 2,  # 最多连续2次挑战失败
}

# ==================== 薪资规则配置 ====================

SALARY_RULES = {
    'trainee': {
        'base': 1000,
        'commission_per_order': 10,
    },
    'C': {
        'base': 1500,
        'attendance_bonus': 200,
        'attendance_bonus_threshold': 0.95,
        'commission_per_order': 15,
    },
    'B': {
        'base': 1800,
        'attendance_bonus': 300,
        'attendance_bonus_threshold': 0.95,
        'commission_per_order': 20,
        'performance_bonus': {
            50: 200,   # 50-74单: 200元
            75: 400,   # 75-99单: 400元
            100: 800,  # 100+单: 800元
        }
    },
    'A': {
        'base': 2200,
        'attendance_bonus': 400,
        'attendance_bonus_conditions': {
            'min_valid_days': 25,
            'min_recent_6_orders': 12,
        },
        'commission_per_order': 25,
        'performance_bonus': {
            75: 300,    # 75-99单: 300元
            100: 600,   # 100-124单: 600元
            125: 1000,  # 125+单: 1000元
        }
    }
}

# ==================== 审批模拟配置 ====================

APPROVAL_SIMULATION = {
    'timely': 0.70,     # 70% 及时审批（3天内）
    'delayed': 0.20,    # 20% 延迟审批（3-7天）
    'rejected': 0.05,   # 5% 拒绝
    'overdue': 0.05,    # 5% 超期
}

# 审批时间范围（天数）
APPROVAL_DAYS = {
    'timely': (1, 3),
    'delayed': (3, 7),
    'overdue': (7, 14),
}

# ==================== 测试配置 ====================

# 数据库配置
DB_PATH = 'data/callcenter.db'

# 输出配置（相对于项目根目录）
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, 'tests/small_scale_test/output')
LOGS_DIR = os.path.join(BASE_DIR, 'tests/small_scale_test/logs')
REPORTS_DIR = os.path.join(BASE_DIR, 'tests/small_scale_test/reports')

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 验证配置
SALARY_ERROR_TOLERANCE = 1.0  # 薪资计算允许±1元误差
SAMPLE_SIZE_FOR_SALARY_CHECK = 100  # 薪资验证抽样数量

# ==================== 成功标准 ====================

SUCCESS_CRITERIA = {
    'data_completeness': 1.0,      # 100% 数据完整性
    'promotion_accuracy': 0.98,    # 98% 晋升准确率
    'demotion_accuracy': 0.98,     # 98% 保级准确率
    'salary_accuracy': 0.99,       # 99% 薪资准确率
    'approval_success': 1.0,       # 100% 审批流程成功
}

# ==================== 性能指标 ====================

# 预期执行时间（秒）
EXPECTED_EXECUTION_TIME = {
    'data_generation': 300,   # 5分钟
    'data_import': 600,       # 10分钟
    'trigger_logic': 900,     # 15分钟
    'approval': 300,          # 5分钟
    'validation': 600,        # 10分钟
    'report': 300,            # 5分钟
}

# ==================== 辅助函数 ====================

def get_employee_no(index):
    """生成员工编号"""
    return f"{EMPLOYEE_PREFIX}{str(index).zfill(3)}"


def get_employee_name(index):
    """生成员工姓名"""
    return f"测试员工{str(index).zfill(3)}"


def get_team_for_employee(index):
    """为员工分配团队"""
    return TEAMS[index % len(TEAMS)]


def get_manager_for_employee(index):
    """为员工分配主管"""
    return MANAGERS[index % len(MANAGERS)]


def print_config_summary():
    """打印配置摘要"""
    print("="*70)
    print("小规模测试配置摘要")
    print("="*70)
    print(f"测试周期: {START_DATE} ~ {END_DATE}")
    print(f"测试员工: {TOTAL_EMPLOYEES}人 ({EMPLOYEES_PER_MONTH}人/月 × {TOTAL_MONTHS}月)")
    print(f"员工编号: {get_employee_no(1)} ~ {get_employee_no(TOTAL_EMPLOYEES)}")
    print(f"团队数量: {len(TEAMS)}")
    print(f"主管数量: {len(MANAGERS)}")
    print(f"\n业绩模式分布:")
    print(f"  - 优秀型: {PERFORMANCE_TYPES['excellent']*100:.0f}%")
    print(f"  - 正常型: {PERFORMANCE_TYPES['normal']*100:.0f}%")
    print(f"  - 待提升型: {PERFORMANCE_TYPES['poor']*100:.0f}%")
    print(f"\n预期总执行时间: {sum(EXPECTED_EXECUTION_TIME.values())/60:.0f}分钟")
    print("="*70)


if __name__ == '__main__':
    print_config_summary()

