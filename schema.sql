-- 呼叫中心职场管理系统 数据库结构

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,  -- SHA256 哈希
    role TEXT NOT NULL CHECK(role IN ('employee', 'manager', 'admin', 'finance')),
    employee_id INTEGER,  -- 关联员工表，可为空（manager/admin可能不是员工）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

-- 员工表
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_no TEXT NOT NULL UNIQUE,  -- 工号
    name TEXT NOT NULL,
    phone TEXT,
    phone_encrypted TEXT,  -- 加密后的手机号
    team TEXT NOT NULL,  -- 所属团队
    status TEXT NOT NULL DEFAULT 'trainee' CHECK(status IN ('trainee', 'C', 'B', 'A', 'eliminated')),
    join_date DATE NOT NULL,  -- 入职日期
    leave_date DATE,  -- 离职日期
    is_active INTEGER DEFAULT 1 CHECK(is_active IN (0, 1)),  -- 是否在职
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 状态变更历史表
CREATE TABLE IF NOT EXISTS status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    change_date DATE NOT NULL,
    reason TEXT,
    days_in_status INTEGER,  -- 在旧状态的天数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

-- 每日业绩表
CREATE TABLE IF NOT EXISTS performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    work_date DATE NOT NULL,
    orders_count INTEGER NOT NULL DEFAULT 0,  -- 出单数
    commission REAL NOT NULL DEFAULT 0,  -- 日提成
    is_valid_workday INTEGER DEFAULT 1 CHECK(is_valid_workday IN (0, 1)),  -- 是否有效工作日
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    UNIQUE(employee_id, work_date)  -- 每人每天唯一
);

-- 月度薪资表
CREATE TABLE IF NOT EXISTS salary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    year_month TEXT NOT NULL,  -- YYYY-MM 格式
    base_salary REAL NOT NULL DEFAULT 0,  -- 基础薪资/底薪
    attendance_bonus REAL NOT NULL DEFAULT 0,  -- 全勤奖
    performance_bonus REAL NOT NULL DEFAULT 0,  -- 绩效奖
    commission REAL NOT NULL DEFAULT 0,  -- 提成
    total_salary REAL NOT NULL DEFAULT 0,  -- 总薪资
    calculation_detail TEXT,  -- 计算明细（文本说明）
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'confirmed', 'disputed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    UNIQUE(employee_id, year_month)
);

-- 薪资异议表
CREATE TABLE IF NOT EXISTS salary_disputes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    salary_id INTEGER NOT NULL,
    reason TEXT NOT NULL,  -- 异议原因
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
    response TEXT,  -- 管理员回复
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (salary_id) REFERENCES salary(id)
);

-- 团队表
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_name TEXT NOT NULL UNIQUE,
    team_leader TEXT,  -- 团队负责人
    description TEXT,
    is_active INTEGER DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 看板配置表
CREATE TABLE IF NOT EXISTS dashboard_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    config_name TEXT NOT NULL,
    config_type TEXT DEFAULT 'custom' CHECK(config_type IN ('preset', 'custom')),
    components TEXT,  -- JSON: 组件配置
    filters TEXT,  -- JSON: 筛选条件
    layout TEXT,  -- JSON: 布局配置
    is_shared INTEGER DEFAULT 0 CHECK(is_shared IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 筛选方案表
CREATE TABLE IF NOT EXISTS filter_schemes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    scheme_name TEXT NOT NULL,
    filters TEXT NOT NULL,  -- JSON: 筛选条件
    is_shared INTEGER DEFAULT 0 CHECK(is_shared IN (0, 1)),
    share_level TEXT DEFAULT 'self' CHECK(share_level IN ('self', 'same_level', 'all')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 系统参数表
CREATE TABLE IF NOT EXISTS system_params (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    param_key TEXT NOT NULL UNIQUE,
    param_value TEXT NOT NULL,
    param_desc TEXT,
    is_core INTEGER DEFAULT 0 CHECK(is_core IN (0, 1)),  -- 是否核心参数（不可随意修改）
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 通知表
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT DEFAULT 'system' CHECK(type IN ('system', 'status_change', 'salary', 'performance', 'dispute', 'announcement')),
    link TEXT,  -- 相关链接
    is_read INTEGER DEFAULT 0 CHECK(is_read IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ==================== 扩展表：晋级确认与保级挑战 ====================

-- 晋级确认记录表
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

-- 保级挑战记录表
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

-- 培训考核记录表
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

-- 工作日配置表
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

-- 操作日志表
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

-- 审计日志索引（优化查询性能）
CREATE INDEX IF NOT EXISTS idx_audit_logs_operation_type ON audit_logs(operation_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_operator_id ON audit_logs(operator_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_target_employee_id ON audit_logs(target_employee_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_operator_created ON audit_logs(operator_id, created_at DESC);

-- ==================== 扩展表：工资管理系统 ====================

-- 工资单表
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

-- 工资调整记录表
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

-- 年度归档表
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

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_employees_team ON employees(team);
CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status);
CREATE INDEX IF NOT EXISTS idx_employees_is_active ON employees(is_active);
CREATE INDEX IF NOT EXISTS idx_performance_employee_date ON performance(employee_id, work_date);
CREATE INDEX IF NOT EXISTS idx_performance_work_date ON performance(work_date);
CREATE INDEX IF NOT EXISTS idx_salary_employee_month ON salary(employee_id, year_month);
CREATE INDEX IF NOT EXISTS idx_status_history_employee ON status_history(employee_id, change_date);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read, created_at);

-- 扩展表索引
CREATE INDEX IF NOT EXISTS idx_promotion_status ON promotion_confirmations(status, employee_id);
CREATE INDEX IF NOT EXISTS idx_promotion_trigger ON promotion_confirmations(trigger_date);
CREATE INDEX IF NOT EXISTS idx_promotion_employee ON promotion_confirmations(employee_id, status);

CREATE INDEX IF NOT EXISTS idx_challenge_status ON demotion_challenges(decision, employee_id);
CREATE INDEX IF NOT EXISTS idx_challenge_month ON demotion_challenges(year_month, employee_id);
CREATE INDEX IF NOT EXISTS idx_challenge_trigger ON demotion_challenges(trigger_date);

CREATE INDEX IF NOT EXISTS idx_training_employee ON training_assessments(employee_id);
CREATE INDEX IF NOT EXISTS idx_training_date ON training_assessments(assessment_date);

CREATE INDEX IF NOT EXISTS idx_work_calendar_date ON work_calendar(calendar_date);
CREATE INDEX IF NOT EXISTS idx_work_calendar_workday ON work_calendar(is_workday);

CREATE INDEX IF NOT EXISTS idx_audit_operator ON audit_logs(operator_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_employee ON audit_logs(target_employee_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_logs(operation_type, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_module ON audit_logs(operation_module, created_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_payroll_unique ON payroll_records(employee_id, year_month) 
    WHERE is_archived = 0;

CREATE INDEX IF NOT EXISTS idx_payroll_month ON payroll_records(year_month);
CREATE INDEX IF NOT EXISTS idx_payroll_status ON payroll_records(status);
CREATE INDEX IF NOT EXISTS idx_payroll_archive ON payroll_records(is_archived, archive_year);
CREATE INDEX IF NOT EXISTS idx_payroll_employee ON payroll_records(employee_id);

CREATE INDEX IF NOT EXISTS idx_adjustment_payroll ON payroll_adjustments(payroll_id);
CREATE INDEX IF NOT EXISTS idx_adjustment_date ON payroll_adjustments(adjusted_at);

