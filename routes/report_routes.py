"""
高级报表路由
"""
from flask import Blueprint, render_template, request, jsonify
from datetime import datetime, timedelta
from core.auth import login_required, role_required, get_current_user, get_user_team
from core.database import query_db
from config import Config
import json

bp = Blueprint('reports', __name__, url_prefix='/reports')


@bp.route('/team_comparison')
@login_required
@role_required('admin')
def team_comparison():
    """团队对比报表"""
    year_month = request.args.get('year_month', datetime.now().strftime('%Y-%m'))
    
    # 获取所有团队
    teams = query_db('SELECT DISTINCT team FROM employees WHERE is_active = 1 ORDER BY team')
    
    # 计算每个团队的数据
    team_data = []
    for team_row in teams:
        team_name = team_row['team']
        
        # 人员统计
        staff_stats = query_db('''
            SELECT status, COUNT(*) as count
            FROM employees
            WHERE team = ? AND is_active = 1
            GROUP BY status
        ''', (team_name,))
        
        stats_dict = {s['status']: s['count'] for s in staff_stats}
        total_staff = sum(stats_dict.values())
        
        # 本月业绩
        month_perf = query_db('''
            SELECT 
                COUNT(DISTINCT e.id) as active_employees,
                SUM(p.orders_count) as total_orders,
                SUM(p.commission) as total_commission,
                AVG(p.orders_count) as avg_orders
            FROM employees e
            LEFT JOIN performance p ON e.id = p.employee_id 
                AND strftime('%Y-%m', p.work_date) = ?
            WHERE e.team = ? AND e.is_active = 1
        ''', (year_month, team_name), one=True)
        
        # 收入成本
        revenue = (month_perf['total_orders'] or 0) * Config.REVENUE_PER_ORDER
        cost = month_perf['total_commission'] or 0
        profit = revenue - cost
        
        team_data.append({
            'team': team_name,
            'total_staff': total_staff,
            'a_count': stats_dict.get('A', 0),
            'b_count': stats_dict.get('B', 0),
            'c_count': stats_dict.get('C', 0),
            'trainee_count': stats_dict.get('trainee', 0),
            'active_employees': month_perf['active_employees'] or 0,
            'total_orders': month_perf['total_orders'] or 0,
            'avg_orders': round(month_perf['avg_orders'] or 0, 1),
            'total_commission': month_perf['total_commission'] or 0,
            'revenue': revenue,
            'cost': cost,
            'profit': profit,
            'profit_margin': round(profit / revenue * 100, 1) if revenue > 0 else 0
        })
    
    return render_template('reports/team_comparison.html',
                         team_data=team_data,
                         year_month=year_month,
                         user=get_current_user())


@bp.route('/employee_ranking')
@login_required
@role_required('manager', 'admin')
def employee_ranking():
    """员工业绩排行榜"""
    user = get_current_user()
    team = get_user_team(user)
    
    year_month = request.args.get('year_month', datetime.now().strftime('%Y-%m'))
    rank_type = request.args.get('type', 'orders')  # orders, commission, valid_days
    
    # 构建查询
    query = '''
        SELECT 
            e.id,
            e.employee_no,
            e.name,
            e.team,
            e.status,
            COUNT(DISTINCT p.work_date) as work_days,
            SUM(CASE WHEN p.is_valid_workday = 1 THEN 1 ELSE 0 END) as valid_days,
            SUM(p.orders_count) as total_orders,
            SUM(p.commission) as total_commission,
            ROUND(AVG(p.orders_count), 1) as avg_orders
        FROM employees e
        LEFT JOIN performance p ON e.id = p.employee_id 
            AND strftime('%Y-%m', p.work_date) = ?
        WHERE e.is_active = 1
    '''
    params = [year_month]
    
    if team:
        query += ' AND e.team = ?'
        params.append(team)
    
    query += ' GROUP BY e.id'
    
    # 排序
    if rank_type == 'orders':
        query += ' ORDER BY total_orders DESC'
    elif rank_type == 'commission':
        query += ' ORDER BY total_commission DESC'
    elif rank_type == 'valid_days':
        query += ' ORDER BY valid_days DESC'
    
    query += ' LIMIT 50'
    
    rankings = query_db(query, params)
    
    # 添加排名
    for idx, rank in enumerate(rankings, 1):
        rank['rank'] = idx
    
    return render_template('reports/employee_ranking.html',
                         rankings=rankings,
                         year_month=year_month,
                         rank_type=rank_type,
                         user=user)


@bp.route('/trend_analysis')
@login_required
@role_required('manager', 'admin')
def trend_analysis():
    """趋势分析报表"""
    user = get_current_user()
    team = get_user_team(user)
    
    # 获取最近12个月的数据
    months = []
    data_points = []
    
    today = datetime.now().date()
    
    for i in range(11, -1, -1):
        month_date = today - timedelta(days=30*i)
        year_month = month_date.strftime('%Y-%m')
        months.append(year_month)
        
        # 查询该月数据
        query = '''
            SELECT 
                COUNT(DISTINCT e.id) as active_count,
                SUM(p.orders_count) as total_orders,
                SUM(p.commission) as total_commission
            FROM employees e
            LEFT JOIN performance p ON e.id = p.employee_id 
                AND strftime('%Y-%m', p.work_date) = ?
            WHERE e.is_active = 1
        '''
        params = [year_month]
        
        if team:
            query += ' AND e.team = ?'
            params.append(team)
        
        result = query_db(query, params, one=True)
        
        orders = result['total_orders'] or 0
        commission = result['total_commission'] or 0
        revenue = orders * Config.REVENUE_PER_ORDER
        
        data_points.append({
            'month': year_month,
            'active_count': result['active_count'] or 0,
            'orders': orders,
            'commission': commission,
            'revenue': revenue,
            'profit': revenue - commission
        })
    
    return render_template('reports/trend_analysis.html',
                         data_points=data_points,
                         user=user)


@bp.route('/status_flow')
@login_required
@role_required('manager', 'admin')
def status_flow():
    """状态流转分析"""
    user = get_current_user()
    team = get_user_team(user)
    
    # 获取时间范围
    days = int(request.args.get('days', 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # 状态流转统计
    query = '''
        SELECT 
            sh.from_status,
            sh.to_status,
            COUNT(*) as count,
            AVG(sh.days_in_status) as avg_days
        FROM status_history sh
        JOIN employees e ON sh.employee_id = e.id
        WHERE sh.change_date >= ? AND sh.change_date <= ?
    '''
    params = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
    
    if team:
        query += ' AND e.team = ?'
        params.append(team)
    
    query += ' GROUP BY sh.from_status, sh.to_status ORDER BY count DESC'
    
    flow_data = query_db(query, params)
    
    # 当前状态分布
    status_query = '''
        SELECT status, COUNT(*) as count
        FROM employees
        WHERE is_active = 1
    '''
    status_params = []
    
    if team:
        status_query += ' AND team = ?'
        status_params.append(team)
    
    status_query += ' GROUP BY status'
    
    current_status = query_db(status_query, status_params)
    
    return render_template('reports/status_flow.html',
                         flow_data=flow_data,
                         current_status=current_status,
                         days=days,
                         user=user)


@bp.route('/performance_heatmap')
@login_required
@role_required('manager', 'admin')
def performance_heatmap():
    """业绩热力图"""
    user = get_current_user()
    team = get_user_team(user)
    
    year_month = request.args.get('year_month', datetime.now().strftime('%Y-%m'))
    
    # 获取该月所有日期的业绩数据
    query = '''
        SELECT 
            p.work_date,
            COUNT(DISTINCT p.employee_id) as employee_count,
            SUM(p.orders_count) as total_orders,
            AVG(p.orders_count) as avg_orders
        FROM performance p
        JOIN employees e ON p.employee_id = e.id
        WHERE strftime('%Y-%m', p.work_date) = ?
    '''
    params = [year_month]
    
    if team:
        query += ' AND e.team = ?'
        params.append(team)
    
    query += ' GROUP BY p.work_date ORDER BY p.work_date'
    
    daily_data = query_db(query, params)
    
    # 按星期几统计
    weekday_stats = {i: {'count': 0, 'orders': 0} for i in range(7)}
    
    for record in daily_data:
        date_obj = datetime.strptime(record['work_date'], '%Y-%m-%d')
        weekday = date_obj.weekday()
        weekday_stats[weekday]['count'] += 1
        weekday_stats[weekday]['orders'] += record['total_orders'] or 0
    
    weekday_labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    weekday_data = [
        {
            'day': weekday_labels[i],
            'avg_orders': round(weekday_stats[i]['orders'] / weekday_stats[i]['count'], 1) if weekday_stats[i]['count'] > 0 else 0
        }
        for i in range(7)
    ]
    
    return render_template('reports/performance_heatmap.html',
                         daily_data=daily_data,
                         weekday_data=weekday_data,
                         year_month=year_month,
                         user=user)


@bp.route('/performance_analysis')
@login_required
@role_required('manager', 'admin')
def performance_analysis():
    """P3-2: 业绩分析"""
    period = request.args.get('period', 'week')
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    end_date = datetime.strptime(date, '%Y-%m-%d').date()
    days = {'day': 1, 'week': 7, 'month': 30}[period]
    start_date = end_date - timedelta(days=days-1)
    
    trend_data = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        perf = query_db('SELECT SUM(orders) as orders, SUM(commission) as commission FROM performance WHERE date = ?', (d,), one=True)
        trend_data.append({'date': d.strftime('%m-%d'), 'orders': perf['orders'] or 0, 'commission': float(perf['commission'] or 0)})
    
    team_data = query_db('SELECT e.team, SUM(p.orders) as orders FROM performance p JOIN employees e ON p.employee_id = e.id WHERE p.date BETWEEN ? AND ? GROUP BY e.team', (start_date, end_date))
    
    return render_template('reports/performance_analysis.html', date=date, period=period, trend_data=trend_data, team_data=[dict(t) for t in team_data], data=trend_data)


@bp.route('/salary_analysis')
@login_required
@role_required('admin')
def salary_analysis():
    """P3-3: 薪资分析"""
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    
    stats = query_db('''
        SELECT COUNT(*) as cnt, SUM(total_salary) as total, 
               SUM(base_salary) as base, SUM(commission) as comm,
               SUM(performance_bonus) as bonus
        FROM payroll WHERE year_month = ?
    ''', (month,), one=True)
    
    return render_template('reports/salary_analysis.html',
        month=month,
        total_salary=stats['total'] or 0,
        avg_salary=round((stats['total'] or 0) / max(stats['cnt'] or 1, 1), 2),
        count=stats['cnt'] or 0,
        base_total=stats['base'] or 0,
        commission_total=stats['comm'] or 0,
        bonus_total=stats['bonus'] or 0)



