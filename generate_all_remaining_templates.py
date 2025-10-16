#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键生成所有剩余前端模板
包括：管理员5个 + 财务4个
"""

import os

TEMPLATES = {
    # === 管理员模板 ===
    
    # 1. 工作日配置
    'admin/work_calendar.html': '''{% extends "base.html" %}
{% block title %}工作日配置 - 呼叫中心管理系统{% endblock %}
{% block content %}
<div class="page-header">
    <h1>📅 工作日配置</h1>
    <p style="color: var(--gray-600); margin-top: var(--space-8);">配置系统工作日和假期</p>
</div>
<div class="card">
    <div class="card-header">
        <h2>{{ year }}年{{ month }}月</h2>
        <form method="GET" style="display: inline-block; margin-left: var(--space-16);">
            <input type="month" name="year_month" value="{{ year_month }}" class="form-input" onchange="this.form.submit()">
        </form>
    </div>
    <div class="card-body">
        <div style="margin-bottom: var(--space-16);">
            <button class="btn btn-primary" onclick="document.getElementById('batchForm').style.display='block'">批量配置</button>
        </div>
        <table class="table" style="text-align: center;">
            <thead>
                <tr>
                    <th>周一</th><th>周二</th><th>周三</th><th>周四</th><th>周五</th><th>周六</th><th>周日</th>
                </tr>
            </thead>
            <tbody>
                {% for week in calendar_data %}
                <tr>
                    {% for day in week %}
                    <td>
                        {% if day != 0 %}
                        <div style="padding: var(--space-8);">
                            <div>{{ day }}</div>
                            {% set date_str = "%04d-%02d-%02d"|format(year, month, day) %}
                            {% set config = config_dict.get(date_str) %}
                            <form method="POST" action="{{ url_for('admin_ext.configure_workday') }}" style="margin-top: 4px;">
                                <input type="hidden" name="calendar_date" value="{{ date_str }}">
                                <input type="hidden" name="day_type" value="custom">
                                <input type="hidden" name="notes" value="手动配置">
                                {% if config and config.is_workday == 0 %}
                                <button type="submit" name="is_workday" value="1" class="btn btn-sm" style="background: var(--color-danger);">假期</button>
                                {% else %}
                                <button type="submit" name="is_workday" value="0" class="btn btn-sm btn-success">工作日</button>
                                {% endif %}
                            </form>
                        </div>
                        {% endif %}
                    </td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
<div id="batchForm" style="display: none; margin-top: var(--space-24);">
    <div class="card">
        <div class="card-header"><h2>批量配置</h2></div>
        <div class="card-body">
            <form method="POST" action="{{ url_for('admin_ext.batch_configure_workdays') }}">
                <div class="form-group">
                    <label>日期范围</label>
                    <input type="date" name="start_date" class="form-input" required>
                    至
                    <input type="date" name="end_date" class="form-input" required>
                </div>
                <div class="form-group">
                    <label>类型</label>
                    <select name="is_workday" class="form-select" required>
                        <option value="1">工作日</option>
                        <option value="0">假期</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-primary">批量配置</button>
            </form>
        </div>
    </div>
</div>
{% endblock %}
''',

    # 2. 工资管理
    'admin/payroll_management.html': '''{% extends "base.html" %}
{% block title %}工资管理 - 呼叫中心管理系统{% endblock %}
{% block content %}
<div class="page-header">
    <h1>💰 工资管理</h1>
</div>
<div class="card" style="margin-bottom: var(--space-24);">
    <div class="card-header">
        <h2>{{ year_month }}月工资单</h2>
        <form method="GET" style="display: inline-block;">
            <input type="month" name="year_month" value="{{ year_month }}" class="form-input" onchange="this.form.submit()">
        </form>
    </div>
    <div class="card-body">
        <div style="margin-bottom: var(--space-16);">
            <button class="btn btn-primary" onclick="generatePayroll()">生成工资单</button>
            <button class="btn btn-success" onclick="exportExcel()">导出Excel</button>
        </div>
        <div style="margin-bottom: var(--space-16);">
            <span>总计：{{ total_count }}人 | 总额：¥{{ "%.2f"|format(total_amount) }}</span>
        </div>
        {% if payrolls %}
        <table class="table">
            <thead>
                <tr>
                    <th>工号</th><th>姓名</th><th>团队</th><th>应发</th><th>状态</th><th>操作</th>
                </tr>
            </thead>
            <tbody>
                {% for p in payrolls %}
                <tr>
                    <td>{{ p.employee_no }}</td>
                    <td>{{ p.employee_name }}</td>
                    <td>{{ p.team }}</td>
                    <td>¥{{ "%.2f"|format(p.total_salary) }}</td>
                    <td>
                        {% if p.status == 'pending' %}<span class="badge badge-warning">待确认</span>
                        {% elif p.status == 'confirmed' %}<span class="badge badge-info">已确认</span>
                        {% elif p.status == 'paid' %}<span class="badge badge-success">已发放</span>
                        {% endif %}
                    </td>
                    <td>
                        <button class="btn btn-sm btn-secondary" onclick="adjustPayroll({{ p.id }}, '{{ p.employee_name }}')">调整</button>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state"><p>暂无工资记录</p></div>
        {% endif %}
    </div>
</div>
<script>
function generatePayroll() {
    if(confirm('确认生成本月工资单吗？如已存在将覆盖。')) {
        document.location = '{{ url_for("admin_ext.generate_payroll") }}?year_month={{ year_month }}&overwrite=1';
    }
}
function adjustPayroll(id, name) {
    alert('调整功能请在详情页操作');
}
function exportExcel() {
    alert('导出功能开发中');
}
</script>
{% endblock %}
''',

    # 3. 年度归档
    'admin/payroll_archive.html': '''{% extends "base.html" %}
{% block title %}年度归档 - 呼叫中心管理系统{% endblock %}
{% block content %}
<div class="page-header">
    <h1>📦 年度归档</h1>
</div>
<div class="card" style="margin-bottom: var(--space-24);">
    <div class="card-header"><h2>创建归档</h2></div>
    <div class="card-body">
        <form method="POST" action="{{ url_for('admin_ext.create_archive') }}">
            <div style="display: flex; gap: var(--space-12);">
                <input type="number" name="archive_year" class="form-input" placeholder="年份（如2024）" required min="2020" max="2099">
                <button type="submit" class="btn btn-primary">创建归档</button>
            </div>
        </form>
    </div>
</div>
<div class="card">
    <div class="card-header"><h2>归档记录</h2></div>
    <div class="card-body">
        {% if archives %}
        <table class="table">
            <thead>
                <tr>
                    <th>年份</th><th>总人数</th><th>总记录数</th><th>总金额</th><th>归档时间</th><th>操作</th>
                </tr>
            </thead>
            <tbody>
                {% for archive in archives %}
                <tr>
                    <td>{{ archive.archive_year }}年</td>
                    <td>{{ archive.total_employees }}人</td>
                    <td>{{ archive.total_records }}条</td>
                    <td>¥{{ "%.2f"|format(archive.total_amount) }}</td>
                    <td>{{ archive.archived_at }}</td>
                    <td>
                        <a href="{{ url_for('admin_ext.view_archive', year=archive.archive_year) }}" class="btn btn-sm btn-info">查看详情</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state"><p>暂无归档记录</p></div>
        {% endif %}
    </div>
</div>
{% endblock %}
''',

    # 4. 归档详情
    'admin/payroll_archive_detail.html': '''{% extends "base.html" %}
{% block title %}归档详情 - 呼叫中心管理系统{% endblock %}
{% block content %}
<div class="page-header">
    <h1>📦 {{ archive.archive_year }}年度归档详情</h1>
    <a href="{{ url_for('admin_ext.payroll_archive') }}" class="btn btn-secondary">返回列表</a>
</div>
<div class="card" style="margin-bottom: var(--space-24);">
    <div class="card-header"><h2>年度汇总</h2></div>
    <div class="card-body">
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-16);">
            <div>
                <div style="color: var(--gray-600);">总人数</div>
                <div style="font-size: 24px; font-weight: bold;">{{ archive.total_employees }}人</div>
            </div>
            <div>
                <div style="color: var(--gray-600);">总记录数</div>
                <div style="font-size: 24px; font-weight: bold;">{{ archive.total_records }}条</div>
            </div>
            <div>
                <div style="color: var(--gray-600);">总金额</div>
                <div style="font-size: 24px; font-weight: bold; color: var(--color-success);">¥{{ "%.2f"|format(archive.total_amount) }}</div>
            </div>
            <div>
                <div style="color: var(--gray-600);">归档时间</div>
                <div style="font-size: 14px;">{{ archive.archived_at }}</div>
            </div>
        </div>
    </div>
</div>
<div class="card">
    <div class="card-header"><h2>月度明细</h2></div>
    <div class="card-body">
        {% if monthly_summary %}
        <table class="table">
            <thead>
                <tr>
                    <th>月份</th><th>人数</th><th>记录数</th><th>金额</th>
                </tr>
            </thead>
            <tbody>
                {% for month in monthly_summary %}
                <tr>
                    <td>{{ month.year_month }}</td>
                    <td>{{ month.total_employees }}人</td>
                    <td>{{ month.total_records }}条</td>
                    <td>¥{{ "%.2f"|format(month.total_amount) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state"><p>无月度数据</p></div>
        {% endif %}
    </div>
</div>
{% endblock %}
''',

    # 5. 银行审核
    'admin/bank_verification.html': '''{% extends "base.html" %}
{% block title %}银行信息审核 - 呼叫中心管理系统{% endblock %}
{% block content %}
<div class="page-header">
    <h1>🏦 银行信息审核</h1>
</div>
<div class="card">
    <div class="card-header"><h2>待审核</h2></div>
    <div class="card-body">
        {% if pending_verifications %}
        <table class="table">
            <thead>
                <tr>
                    <th>工号</th><th>姓名</th><th>团队</th><th>银行卡号</th><th>开户行</th><th>户名</th><th>操作</th>
                </tr>
            </thead>
            <tbody>
                {% for emp in pending_verifications %}
                <tr>
                    <td>{{ emp.employee_no }}</td>
                    <td>{{ emp.name }}</td>
                    <td>{{ emp.team }}</td>
                    <td>{{ emp.bank_account_number }}</td>
                    <td>{{ emp.bank_name }}</td>
                    <td>{{ emp.account_holder_name }}</td>
                    <td>
                        <form method="POST" action="{{ url_for('admin_ext.verify_bank_info', employee_id=emp.id) }}" style="display: inline;">
                            <input type="hidden" name="action" value="approve">
                            <button type="submit" class="btn btn-sm btn-success">通过</button>
                        </form>
                        <button class="btn btn-sm btn-danger" onclick="rejectBank({{ emp.id }}, '{{ emp.name }}')">拒绝</button>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state"><p>暂无待审核</p></div>
        {% endif %}
    </div>
</div>
<script>
function rejectBank(id, name) {
    const reason = prompt(`拒绝 ${name} 的银行信息，请输入原因：`);
    if (reason) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/admin/bank_verification/${id}/verify`;
        form.innerHTML = `<input name="action" value="reject"><input name="notes" value="${reason}">`;
        document.body.appendChild(form);
        form.submit();
    }
}
</script>
{% endblock %}
''',

    # === 财务模板 ===
    
    # 6. 财务工作台
    'finance/dashboard.html': '''{% extends "base.html" %}
{% block title %}财务工作台 - 呼叫中心管理系统{% endblock %}
{% block content %}
<div class="page-header">
    <h1>💳 财务工作台</h1>
</div>
<div style="margin-bottom: var(--space-24);">
    <form method="GET">
        <input type="month" name="year_month" value="{{ year_month }}" class="form-input" onchange="this.form.submit()">
    </form>
</div>
<div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--space-16); margin-bottom: var(--space-24);">
    {% for status, data in status_stats.items() %}
    <div class="card">
        <div class="card-body" style="text-align: center;">
            <div style="color: var(--gray-600);">{{ status }}</div>
            <div style="font-size: 24px; font-weight: bold;">{{ data.count }}</div>
            <div style="font-size: 14px; color: var(--gray-600);">¥{{ "%.2f"|format(data.amount) }}</div>
        </div>
    </div>
    {% endfor %}
</div>
<div class="card" style="margin-bottom: var(--space-24);">
    <div class="card-header">
        <h2>待确认工资单</h2>
        <button class="btn btn-success" onclick="batchConfirm()">批量确认</button>
    </div>
    <div class="card-body">
        {% if pending_payrolls %}
        <table class="table">
            <thead>
                <tr>
                    <th><input type="checkbox" id="selectAll"></th>
                    <th>工号</th><th>姓名</th><th>应发</th><th>操作</th>
                </tr>
            </thead>
            <tbody>
                {% for p in pending_payrolls %}
                <tr>
                    <td><input type="checkbox" class="pay-check" value="{{ p.id }}"></td>
                    <td>{{ p.employee_no }}</td>
                    <td>{{ p.employee_name }}</td>
                    <td>¥{{ "%.2f"|format(p.total_salary) }}</td>
                    <td>
                        <form method="POST" action="{{ url_for('finance.confirm_payroll', payroll_id=p.id) }}" style="display: inline;">
                            <button type="submit" class="btn btn-sm btn-success">确认</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state"><p>无待确认</p></div>
        {% endif %}
    </div>
</div>
<div class="card">
    <div class="card-header"><h2>已确认待发放</h2></div>
    <div class="card-body">
        {% if confirmed_payrolls %}
        <table class="table">
            <thead>
                <tr>
                    <th>工号</th><th>姓名</th><th>应发</th><th>操作</th>
                </tr>
            </thead>
            <tbody>
                {% for p in confirmed_payrolls %}
                <tr>
                    <td>{{ p.employee_no }}</td>
                    <td>{{ p.employee_name }}</td>
                    <td>¥{{ "%.2f"|format(p.total_salary) }}</td>
                    <td>
                        <a href="{{ url_for('finance.payment', payroll_id=p.id) }}" class="btn btn-sm btn-primary">发放</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state"><p>无待发放</p></div>
        {% endif %}
    </div>
</div>
<script>
function batchConfirm() {
    if(confirm('确认批量确认吗？')) {
        window.location = '{{ url_for("finance.batch_confirm") }}?year_month={{ year_month }}';
    }
}
</script>
{% endblock %}
''',

    # 7. 工资发放
    'finance/payment.html': '''{% extends "base.html" %}
{% block title %}工资发放 - 呼叫中心管理系统{% endblock %}
{% block content %}
<div class="page-header">
    <h1>💳 工资发放</h1>
</div>
<div class="card">
    <div class="card-header"><h2>员工：{{ payroll.employee_name }} ({{ payroll.employee_no }})</h2></div>
    <div class="card-body">
        <form method="POST">
            <div class="form-group">
                <label>应发金额</label>
                <input type="text" value="¥{{ '%.2f'|format(payroll.total_salary) }}" class="form-input" readonly>
            </div>
            <div class="form-group">
                <label>银行信息</label>
                <div style="padding: var(--space-12); background: var(--gray-100); border-radius: var(--radius-md);">
                    <div>卡号：{{ employee.bank_account_number or '未录入' }}</div>
                    <div>开户行：{{ employee.bank_name or '未录入' }}</div>
                    <div>户名：{{ employee.account_holder_name or '未录入' }}</div>
                </div>
            </div>
            <div class="form-group">
                <label>发放方式 *</label>
                <select name="payment_method" class="form-select" required>
                    <option value="">请选择</option>
                    {% if employee.account_holder_name == employee.name %}
                    <option value="bank_transfer">银行转账</option>
                    {% endif %}
                    <option value="cash">现金</option>
                    <option value="other">其他</option>
                </select>
            </div>
            <div class="form-group">
                <label>发放日期 *</label>
                <input type="date" name="payment_date" class="form-input" value="{{ now.strftime('%Y-%m-%d') }}" required>
            </div>
            <div class="form-group">
                <label>转账凭证号</label>
                <input type="text" name="payment_reference" class="form-input">
            </div>
            <div class="form-group">
                <label>备注</label>
                <textarea name="notes" class="form-input" rows="3"></textarea>
            </div>
            <div style="display: flex; gap: var(--space-12);">
                <button type="submit" class="btn btn-success">确认发放</button>
                <a href="{{ url_for('finance.dashboard') }}" class="btn btn-secondary">返回</a>
            </div>
        </form>
    </div>
</div>
{% endblock %}
''',

    # 8. 发放历史
    'finance/payment_history.html': '''{% extends "base.html" %}
{% block title %}发放历史 - 呼叫中心管理系统{% endblock %}
{% block content %}
<div class="page-header">
    <h1>📋 发放历史</h1>
</div>
<div class="card">
    <div class="card-header">
        <h2>{{ year_month }}月</h2>
        <form method="GET" style="display: inline-block;">
            <input type="month" name="year_month" value="{{ year_month }}" class="form-input" onchange="this.form.submit()">
            <select name="status" class="form-select" onchange="this.form.submit()">
                <option value="">全部状态</option>
                <option value="paid" {% if status_filter=='paid' %}selected{% endif %}>已发放</option>
                <option value="failed" {% if status_filter=='failed' %}selected{% endif %}>失败</option>
            </select>
        </form>
    </div>
    <div class="card-body">
        {% if records %}
        <table class="table">
            <thead>
                <tr>
                    <th>工号</th><th>姓名</th><th>金额</th><th>发放方式</th><th>发放日期</th><th>状态</th>
                </tr>
            </thead>
            <tbody>
                {% for r in records %}
                <tr>
                    <td>{{ r.employee_no }}</td>
                    <td>{{ r.employee_name }}</td>
                    <td>¥{{ "%.2f"|format(r.total_salary) }}</td>
                    <td>
                        {% if r.payment_method == 'bank_transfer' %}银行转账
                        {% elif r.payment_method == 'cash' %}现金
                        {% else %}{{ r.payment_method }}
                        {% endif %}
                    </td>
                    <td>{{ r.payment_date }}</td>
                    <td>
                        {% if r.status == 'paid' %}<span class="badge badge-success">已发放</span>
                        {% elif r.status == 'failed' %}<span class="badge badge-danger">失败</span>
                        {% else %}<span class="badge badge-warning">{{ r.status }}</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state"><p>暂无记录</p></div>
        {% endif %}
    </div>
</div>
{% endblock %}
''',

    # 9. 银行审核（财务）
    'finance/bank_audit.html': '''{% extends "base.html" %}
{% block title %}银行信息审核 - 呼叫中心管理系统{% endblock %}
{% block content %}
<div class="page-header">
    <h1>🏦 银行信息审核</h1>
</div>
<div class="card" style="margin-bottom: var(--space-24);">
    <div class="card-header"><h2>待审核</h2></div>
    <div class="card-body">
        {% if pending_verifications %}
        <table class="table">
            <thead>
                <tr>
                    <th>工号</th><th>姓名</th><th>团队</th><th>银行卡号</th><th>开户行</th><th>户名</th><th>操作</th>
                </tr>
            </thead>
            <tbody>
                {% for emp in pending_verifications %}
                <tr>
                    <td>{{ emp.employee_no }}</td>
                    <td>{{ emp.name }}</td>
                    <td>{{ emp.team }}</td>
                    <td>{{ emp.bank_account_number }}</td>
                    <td>{{ emp.bank_name }}</td>
                    <td>{{ emp.account_holder_name }}</td>
                    <td>
                        <form method="POST" action="{{ url_for('finance.verify_bank', employee_id=emp.id) }}" style="display: inline;">
                            <input type="hidden" name="action" value="approve">
                            <button type="submit" class="btn btn-sm btn-success">通过</button>
                        </form>
                        <button class="btn btn-sm btn-danger" onclick="rejectBank({{ emp.id }}, '{{ emp.name }}')">拒绝</button>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state"><p>暂无待审核</p></div>
        {% endif %}
    </div>
</div>
<div class="card">
    <div class="card-header"><h2>审核历史</h2></div>
    <div class="card-body">
        {% if audit_history %}
        <table class="table">
            <thead>
                <tr>
                    <th>工号</th><th>姓名</th><th>银行卡号</th><th>户名</th><th>状态</th><th>审核时间</th>
                </tr>
            </thead>
            <tbody>
                {% for emp in audit_history %}
                <tr>
                    <td>{{ emp.employee_no }}</td>
                    <td>{{ emp.name }}</td>
                    <td>{{ emp.bank_account_number }}</td>
                    <td>{{ emp.account_holder_name }}</td>
                    <td>
                        {% if emp.bank_info_status == 'verified' %}
                        <span class="badge badge-success">已通过</span>
                        {% else %}
                        <span class="badge badge-danger">已拒绝</span>
                        {% endif %}
                    </td>
                    <td>{{ emp.bank_verified_at }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state"><p>暂无历史</p></div>
        {% endif %}
    </div>
</div>
<script>
function rejectBank(id, name) {
    const reason = prompt(`拒绝 ${name} 的银行信息，请输入原因：`);
    if (reason) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/finance/bank_audit/${id}/verify`;
        form.innerHTML = `<input name="action" value="reject"><input name="notes" value="${reason}">`;
        document.body.appendChild(form);
        form.submit();
    }
}
</script>
{% endblock %}
''',
}

def create_all_templates():
    """创建所有模板"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base_dir, 'templates')
    
    print("开始创建所有剩余模板...")
    print("="*70)
    
    for template_path, content in TEMPLATES.items():
        full_path = os.path.join(templates_dir, template_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ {template_path}")
    
    print("="*70)
    print(f"✅ 完成！共创建 {len(TEMPLATES)} 个模板")
    print("\n模板清单：")
    print("  管理员 (5个): work_calendar, payroll_management, payroll_archive, ")
    print("              payroll_archive_detail, bank_verification")
    print("  财务 (4个): dashboard, payment, payment_history, bank_audit")
    print("\n加上之前的5个经理模板，共14个模板全部完成！")

if __name__ == '__main__':
    create_all_templates()



