-- 呼叫中心系统 - 数据库扩展（晋级确认 + 保级挑战 + 工资管理）
-- Version: 2.0
-- Date: 2025-10-15

-- ==================== 需求1：晋级确认与保级挑战 ====================

-- 1. 晋级确认记录表
CREATE TABLE IF NOT EXISTS promotion_confirmations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    employee_no TEXT NOT NULL,
    employee_name TEXT NOT NULL,
    
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    
    -- 触发信息
    trigger_date DATE NOT NULL,
    trigger_reason TEXT,
    days_in_status INTEGER,
    recent_orders INTEGER,
    
    -- 审批信息（无时间限制）
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'overridden')),
    approver_id INTEGER,
    approver_name TEXT,
    approver_role TEXT,
    approved_at TIMESTAMP,
    rejection_reason TEXT,
    effective_date DATE,
    
    -- 管理员否决
    overridden_by INTEGER,
    overridden_name TEXT,
    overridden_at TIMESTAMP,
    override_reason TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (approver_id) REFERENCES users(id),
    FOREIGN KEY (overridden_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_promotion_status ON promotion_confirmations(status, employee_id);
CREATE INDEX IF NOT EXISTS idx_promotion_trigger ON promotion_confirmations(trigger_date);
CREATE INDEX IF NOT EXISTS idx_promotion_employee ON promotion_confirmations(employee_id, status);

-- 2. 保级挑战记录表
CREATE TABLE IF NOT EXISTS demotion_challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    employee_no TEXT NOT NULL,
    employee_name TEXT NOT NULL,
    year_month TEXT NOT NULL,
    
    -- 触发信息
    trigger_date DATE NOT NULL,
    trigger_orders INTEGER,
    
    -- 主管决策（无时间限制）
    decision TEXT DEFAULT 'pending' CHECK(decision IN ('pending', 'downgrade', 'challenge', 'cancelled')),
    decision_by INTEGER,
    decision_name TEXT,
    decision_at TIMESTAMP,
    decision_reason TEXT,
    
    -- 挑战周期
    challenge_start_date DATE,
    challenge_end_date DATE,
    challenge_orders INTEGER DEFAULT 0,
    challenge_result TEXT CHECK(challenge_result IN ('success', 'failed', 'ongoing', NULL)),
    
    -- 结果确认
    result_confirmed_by INTEGER,
    result_confirmed_name TEXT,
    result_confirmed_at TIMESTAMP,
    effective_date DATE,
    
    -- 薪资计算标记
    salary_calculation_type TEXT CHECK(salary_calculation_type IN ('normal', 'challenge_success', 'challenge_failed', NULL)),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (decision_by) REFERENCES users(id),
    FOREIGN KEY (result_confirmed_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_challenge_status ON demotion_challenges(decision, employee_id);
CREATE INDEX IF NOT EXISTS idx_challenge_month ON demotion_challenges(year_month, employee_id);
CREATE INDEX IF NOT EXISTS idx_challenge_trigger ON demotion_challenges(trigger_date);

-- 3. 培训考核记录表
CREATE TABLE IF NOT EXISTS training_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    employee_no TEXT NOT NULL,
    employee_name TEXT NOT NULL,
    
    -- 考核信息
    assessment_date DATE NOT NULL,
    script_test_result TEXT CHECK(script_test_result IN ('passed', 'failed')),
    mock_order_result TEXT CHECK(mock_order_result IN ('passed', 'failed')),
    both_passed INTEGER DEFAULT 0 CHECK(both_passed IN (0, 1)),
    
    -- 经理录入
    recorded_by INTEGER NOT NULL,
    recorder_name TEXT NOT NULL,
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (recorded_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_training_employee ON training_assessments(employee_id);
CREATE INDEX IF NOT EXISTS idx_training_date ON training_assessments(assessment_date);

-- 4. 工作日配置表
CREATE TABLE IF NOT EXISTS work_calendar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calendar_date DATE NOT NULL UNIQUE,
    is_workday INTEGER DEFAULT 1 CHECK(is_workday IN (0, 1)),
    day_type TEXT DEFAULT 'workday' CHECK(day_type IN ('workday', 'holiday', 'weekend', 'custom')),
    notes TEXT,
    
    configured_by INTEGER,
    configured_name TEXT,
    configured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (configured_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_work_calendar_date ON work_calendar(calendar_date);
CREATE INDEX IF NOT EXISTS idx_work_calendar_workday ON work_calendar(is_workday);

-- 5. 操作日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 操作基本信息
    operation_type TEXT NOT NULL,
    operation_module TEXT NOT NULL,
    operation_action TEXT NOT NULL,
    
    -- 操作人信息
    operator_id INTEGER NOT NULL,
    operator_name TEXT NOT NULL,
    operator_role TEXT NOT NULL,
    
    -- 目标对象
    target_employee_id INTEGER,
    target_employee_name TEXT,
    target_record_id INTEGER,
    
    -- 变更内容
    before_value TEXT,
    after_value TEXT,
    changes_json TEXT,
    
    -- 原因/备注
    reason TEXT,
    notes TEXT,
    
    -- 请求信息
    ip_address TEXT,
    user_agent TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (operator_id) REFERENCES users(id),
    FOREIGN KEY (target_employee_id) REFERENCES employees(id)
);

CREATE INDEX IF NOT EXISTS idx_audit_operator ON audit_logs(operator_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_employee ON audit_logs(target_employee_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_logs(operation_type, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_module ON audit_logs(operation_module, created_at);

-- ==================== 需求2：工资管理系统 ====================

-- 6. 工资单表
CREATE TABLE IF NOT EXISTS payroll_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    employee_no TEXT NOT NULL,
    employee_name TEXT NOT NULL,
    team TEXT,
    status_at_time TEXT,
    year_month TEXT NOT NULL,
    
    -- 薪资明细（从salary同步）
    base_salary REAL DEFAULT 0,
    attendance_bonus REAL DEFAULT 0,
    performance_bonus REAL DEFAULT 0,
    commission REAL DEFAULT 0,
    subtotal REAL DEFAULT 0,
    
    -- 调整项
    deductions REAL DEFAULT 0,
    allowances REAL DEFAULT 0,
    adjustment_notes TEXT,
    
    -- 总计
    total_salary REAL NOT NULL,
    
    -- 调整记录
    adjusted_by INTEGER,
    adjusted_by_name TEXT,
    adjusted_at TIMESTAMP,
    
    -- 发放状态
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'confirmed', 'paid', 'failed', 'retry', 'cancelled')),
    
    -- 发放信息
    payment_method TEXT CHECK(payment_method IN ('bank_transfer', 'cash', 'other', NULL)),
    payment_date DATE,
    payment_reference TEXT,
    failure_reason TEXT,
    
    -- 财务操作
    confirmed_by INTEGER,
    confirmed_by_name TEXT,
    confirmed_at TIMESTAMP,
    finance_notes TEXT,
    
    -- 归档标记
    is_archived INTEGER DEFAULT 0 CHECK(is_archived IN (0, 1)),
    archive_year INTEGER,
    
    -- 版本控制
    version INTEGER DEFAULT 1,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (adjusted_by) REFERENCES users(id),
    FOREIGN KEY (confirmed_by) REFERENCES users(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_payroll_unique ON payroll_records(employee_id, year_month) 
    WHERE is_archived = 0;

CREATE INDEX IF NOT EXISTS idx_payroll_month ON payroll_records(year_month);
CREATE INDEX IF NOT EXISTS idx_payroll_status ON payroll_records(status);
CREATE INDEX IF NOT EXISTS idx_payroll_archive ON payroll_records(is_archived, archive_year);
CREATE INDEX IF NOT EXISTS idx_payroll_employee ON payroll_records(employee_id);

-- 7. 工资调整记录表
CREATE TABLE IF NOT EXISTS payroll_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payroll_id INTEGER NOT NULL,
    adjustment_type TEXT NOT NULL CHECK(adjustment_type IN ('deduction', 'allowance')),
    amount REAL NOT NULL,
    reason TEXT NOT NULL,
    adjusted_by INTEGER NOT NULL,
    adjusted_by_name TEXT NOT NULL,
    adjusted_by_role TEXT NOT NULL,
    adjusted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (payroll_id) REFERENCES payroll_records(id),
    FOREIGN KEY (adjusted_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_adjustment_payroll ON payroll_adjustments(payroll_id);
CREATE INDEX IF NOT EXISTS idx_adjustment_date ON payroll_adjustments(adjusted_at);

-- 8. 年度归档表
CREATE TABLE IF NOT EXISTS payroll_archives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    archive_year INTEGER NOT NULL UNIQUE,
    total_employees INTEGER,
    total_records INTEGER,
    total_amount REAL,
    summary_json TEXT,
    archived_by INTEGER,
    archived_by_name TEXT,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    
    FOREIGN KEY (archived_by) REFERENCES users(id)
);

-- ==================== 扩展现有表 ====================

-- 扩展users表（添加finance角色）
-- 注意：需要手动执行 ALTER TABLE 修改 CHECK 约束

-- 扩展employees表（添加保级挑战和银行信息字段）
ALTER TABLE employees ADD COLUMN challenge_count_this_month INTEGER DEFAULT 0;
ALTER TABLE employees ADD COLUMN current_challenge_id INTEGER;
ALTER TABLE employees ADD COLUMN last_challenge_date DATE;
ALTER TABLE employees ADD COLUMN status_display TEXT;

ALTER TABLE employees ADD COLUMN bank_account_number TEXT;
ALTER TABLE employees ADD COLUMN bank_name TEXT;
ALTER TABLE employees ADD COLUMN bank_branch TEXT;
ALTER TABLE employees ADD COLUMN account_holder_name TEXT;
ALTER TABLE employees ADD COLUMN bank_info_status TEXT DEFAULT 'pending' CHECK(bank_info_status IN ('pending', 'verified', 'rejected'));
ALTER TABLE employees ADD COLUMN bank_info_notes TEXT;
ALTER TABLE employees ADD COLUMN bank_verified_by INTEGER;
ALTER TABLE employees ADD COLUMN bank_verified_at TIMESTAMP;

-- 扩展notifications表（添加新通知类型）
-- 注意：需要手动修改notifications表的type字段CHECK约束，添加新类型

-- ==================== 数据初始化 ====================

-- 初始化财务账号
INSERT OR IGNORE INTO users (username, password, role) 
VALUES ('finance', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'finance');  -- 密码: 123456

-- 初始化系统参数
INSERT OR IGNORE INTO system_params (param_key, param_value, param_desc, is_core)
VALUES 
    ('workday_calculation_enabled', '1', '工作日计算功能启用', 1),
    ('promotion_auto_trigger', '1', '晋级自动触发', 1),
    ('challenge_monthly_limit', '1', '保级挑战月度次数限制', 1),
    ('payroll_generation_mode', 'manual', '工资单生成模式：manual/auto', 0);




