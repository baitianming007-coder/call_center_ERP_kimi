#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速生成剩余前端模板
批量创建简化但功能完整的MVP版本
"""

import os

# 模板内容字典
TEMPLATES = {
    # 经理工作台 - 保级挑战
    'manager/challenges.html': '''{% extends "base.html" %}

{% block title %}保级挑战管理 - 呼叫中心管理系统{% endblock %}

{% block content %}
<div class="page-header">
    <h1>🏆 保级挑战管理</h1>
    <p style="color: var(--gray-600); margin-top: var(--space-8);">管理A级员工保级挑战流程</p>
</div>

<!-- 待处理预警 -->
<div class="card" style="margin-bottom: var(--space-24);">
    <div class="card-header">
        <h2>待处理降级预警</h2>
        <span class="badge badge-warning">{{ pending_challenges|length }}条</span>
    </div>
    <div class="card-body">
        {% if pending_challenges %}
        <table class="table">
            <thead>
                <tr>
                    <th>工号</th>
                    <th>姓名</th>
                    <th>团队</th>
                    <th>触发日期</th>
                    <th>出单数</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                {% for challenge in pending_challenges %}
                <tr>
                    <td>{{ challenge.employee_no }}</td>
                    <td>{{ challenge.employee_name }}</td>
                    <td><span class="badge badge-info">{{ challenge.team }}</span></td>
                    <td>{{ challenge.trigger_date }}</td>
                    <td><span class="badge badge-danger">{{ challenge.trigger_orders }}单</span></td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="openDecisionModal({{ challenge.id }}, '{{ challenge.employee_name }}')">
                            处理
                        </button>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state"><p>✓ 暂无待处理预警</p></div>
        {% endif %}
    </div>
</div>

<!-- 进行中挑战 -->
<div class="card" style="margin-bottom: var(--space-24);">
    <div class="card-header">
        <h2>进行中的保级挑战</h2>
    </div>
    <div class="card-body">
        {% if ongoing_challenges %}
        <table class="table">
            <thead>
                <tr>
                    <th>工号</th>
                    <th>姓名</th>
                    <th>挑战期</th>
                    <th>当前出单</th>
                    <th>目标</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                {% for challenge in ongoing_challenges %}
                <tr>
                    <td>{{ challenge.employee_no }}</td>
                    <td>{{ challenge.employee_name }}</td>
                    <td>{{ challenge.challenge_start_date }} 至 {{ challenge.challenge_end_date }}</td>
                    <td>{{ challenge.challenge_orders or 0 }}单</td>
                    <td>9单</td>
                    <td>
                        <form method="POST" action="{{ url_for('manager.finalize_challenge_action', challenge_id=challenge.id) }}" style="display: inline;">
                            <button type="submit" class="btn btn-sm btn-success">完成挑战</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state"><p>暂无进行中挑战</p></div>
        {% endif %}
    </div>
</div>

<!-- 历史记录 -->
<div class="card">
    <div class="card-header"><h2>历史记录</h2></div>
    <div class="card-body">
        {% if history_challenges %}
        <table class="table">
            <thead>
                <tr>
                    <th>工号</th>
                    <th>姓名</th>
                    <th>决策</th>
                    <th>结果</th>
                    <th>决策时间</th>
                </tr>
            </thead>
            <tbody>
                {% for challenge in history_challenges %}
                <tr>
                    <td>{{ challenge.employee_no }}</td>
                    <td>{{ challenge.employee_name }}</td>
                    <td>
                        {% if challenge.decision == 'downgrade' %}
                        <span class="badge badge-danger">直接降级</span>
                        {% elif challenge.decision == 'challenge' %}
                        <span class="badge badge-warning">保级挑战</span>
                        {% elif challenge.decision == 'cancelled' %}
                        <span class="badge badge-secondary">已取消</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if challenge.challenge_result == 'success' %}
                        <span class="badge badge-success">成功</span>
                        {% elif challenge.challenge_result == 'failed' %}
                        <span class="badge badge-danger">失败</span>
                        {% else %}
                        -
                        {% endif %}
                    </td>
                    <td>{{ challenge.decision_at }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state"><p>暂无历史记录</p></div>
        {% endif %}
    </div>
</div>

<!-- 决策弹窗 -->
<div id="decisionModal" class="modal" style="display: none;">
    <div class="modal-content">
        <div class="modal-header">
            <h3>保级挑战决策</h3>
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <form method="POST" id="decisionForm">
            <div class="modal-body">
                <p id="employeeInfo" style="margin-bottom: var(--space-16);"></p>
                <div class="form-group">
                    <label class="form-label">决策 *</label>
                    <select name="decision" class="form-select" required>
                        <option value="">请选择</option>
                        <option value="downgrade">直接降级</option>
                        <option value="challenge">启动保级挑战</option>
                        <option value="cancelled">取消预警</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">原因</label>
                    <textarea name="reason" class="form-input" rows="3"></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">取消</button>
                <button type="submit" class="btn btn-primary">提交决策</button>
            </div>
        </form>
    </div>
</div>

<script>
function openDecisionModal(id, name) {
    document.getElementById('employeeInfo').textContent = `员工：${name}`;
    document.getElementById('decisionForm').action = `/manager/challenges/${id}/decide`;
    document.getElementById('decisionModal').style.display = 'flex';
}
function closeModal() {
    document.getElementById('decisionModal').style.display = 'none';
}
document.getElementById('decisionModal').addEventListener('click', function(e) {
    if (e.target === this) closeModal();
});
</script>
{% endblock %}
''',

    # 经理工作台 - 工资查看
    'manager/payroll.html': '''{% extends "base.html" %}

{% block title %}团队工资查询 - 呼叫中心管理系统{% endblock %}

{% block content %}
<div class="page-header">
    <h1>💰 团队工资查询</h1>
    <p style="color: var(--gray-600); margin-top: var(--space-8);">查看本团队员工工资</p>
</div>

<div class="card">
    <div class="card-header">
        <h2>{{ team }}团队工资 - {{ year_month }}</h2>
        <form method="GET" style="display: inline-block; margin-left: var(--space-16);">
            <input type="month" name="year_month" value="{{ year_month }}" class="form-input" onchange="this.form.submit()">
        </form>
    </div>
    <div class="card-body">
        {% if payrolls %}
        <table class="table">
            <thead>
                <tr>
                    <th>工号</th>
                    <th>姓名</th>
                    <th>状态</th>
                    <th>底薪</th>
                    <th>全勤奖</th>
                    <th>绩效奖</th>
                    <th>提成</th>
                    <th>应发合计</th>
                    <th>发放状态</th>
                </tr>
            </thead>
            <tbody>
                {% for payroll in payrolls %}
                <tr>
                    <td>{{ payroll.employee_no }}</td>
                    <td>{{ payroll.employee_name }}</td>
                    <td><span class="badge">{{ payroll.status_at_time }}</span></td>
                    <td>¥{{ "%.2f"|format(payroll.base_salary) }}</td>
                    <td>¥{{ "%.2f"|format(payroll.attendance_bonus) }}</td>
                    <td>¥{{ "%.2f"|format(payroll.performance_bonus) }}</td>
                    <td>¥{{ "%.2f"|format(payroll.commission) }}</td>
                    <td><strong>¥{{ "%.2f"|format(payroll.total_salary) }}</strong></td>
                    <td>
                        {% if payroll.status == 'pending' %}
                        <span class="badge badge-warning">待确认</span>
                        {% elif payroll.status == 'confirmed' %}
                        <span class="badge badge-info">已确认</span>
                        {% elif payroll.status == 'paid' %}
                        <span class="badge badge-success">已发放</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state"><p>本月暂无工资记录</p></div>
        {% endif %}
    </div>
</div>
{% endblock %}
''',

    # 经理工作台 - 操作日志
    'manager/logs.html': '''{% extends "base.html" %}

{% block title %}操作日志 - 呼叫中心管理系统{% endblock %}

{% block content %}
<div class="page-header">
    <h1>📝 我的操作日志</h1>
    <p style="color: var(--gray-600); margin-top: var(--space-8);">查看个人操作记录</p>
</div>

<div class="card">
    <div class="card-header"><h2>最近操作记录</h2></div>
    <div class="card-body">
        {% if logs %}
        <table class="table">
            <thead>
                <tr>
                    <th>时间</th>
                    <th>操作类型</th>
                    <th>操作描述</th>
                    <th>目标员工</th>
                    <th>详情</th>
                </tr>
            </thead>
            <tbody>
                {% for log in logs %}
                <tr>
                    <td>{{ log.created_at_formatted }}</td>
                    <td><span class="badge badge-info">{{ log.operation_type }}</span></td>
                    <td>{{ log.description }}</td>
                    <td>{{ log.target_employee_name or '-' }}</td>
                    <td style="max-width: 300px; font-size: 0.9em;">{{ log.notes or '-' }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state"><p>暂无操作记录</p></div>
        {% endif %}
    </div>
</div>
{% endblock %}
''',
}

def create_templates():
    """创建所有模板文件"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base_dir, 'templates')
    
    created_count = 0
    for template_path, content in TEMPLATES.items():
        full_path = os.path.join(templates_dir, template_path)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # 写入文件
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ 已创建: {template_path}")
        created_count += 1
    
    print(f"\n总计创建了 {created_count} 个模板文件")
    return created_count

if __name__ == '__main__':
    print("开始批量创建模板...")
    print("="*60)
    count = create_templates()
    print("="*60)
    print(f"✅ 完成！已创建 {count} 个模板")



