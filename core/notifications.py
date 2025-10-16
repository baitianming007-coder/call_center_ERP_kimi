"""
消息通知系统
"""
from datetime import datetime
from core.database import query_db, execute_db, get_db


class NotificationType:
    """通知类型"""
    SYSTEM = 'system'           # 系统通知
    STATUS_CHANGE = 'status_change'  # 状态变更通知
    SALARY = 'salary'           # 薪资通知
    PERFORMANCE = 'performance' # 业绩通知
    DISPUTE = 'dispute'         # 异议通知
    ANNOUNCEMENT = 'announcement' # 公告


def create_notification(user_id, title, content, notification_type=NotificationType.SYSTEM, link=None):
    """
    创建通知
    
    Args:
        user_id: 用户ID
        title: 标题
        content: 内容
        notification_type: 通知类型
        link: 相关链接
        
    Returns:
        int: 通知ID
    """
    return execute_db(
        '''INSERT INTO notifications 
           (user_id, title, content, type, link, is_read, created_at)
           VALUES (?, ?, ?, ?, ?, 0, datetime('now', 'localtime'))''',
        (user_id, title, content, notification_type, link)
    )


def get_user_notifications(user_id, limit=20, unread_only=False):
    """
    获取用户通知列表
    
    Args:
        user_id: 用户ID
        limit: 数量限制
        unread_only: 仅未读
        
    Returns:
        list: 通知列表
    """
    query = 'SELECT * FROM notifications WHERE user_id = ?'
    params = [user_id]
    
    if unread_only:
        query += ' AND is_read = 0'
    
    query += ' ORDER BY created_at DESC LIMIT ?'
    params.append(limit)
    
    return query_db(query, params)


def get_unread_count(user_id):
    """获取未读通知数量"""
    result = query_db(
        'SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0',
        (user_id,),
        one=True
    )
    return result['count'] if result else 0


def mark_as_read(notification_id, user_id):
    """标记为已读"""
    execute_db(
        'UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?',
        (notification_id, user_id)
    )


def mark_all_as_read(user_id):
    """标记全部为已读"""
    execute_db(
        'UPDATE notifications SET is_read = 1 WHERE user_id = ?',
        (user_id,)
    )


def delete_notification(notification_id, user_id):
    """删除通知"""
    execute_db(
        'DELETE FROM notifications WHERE id = ? AND user_id = ?',
        (notification_id, user_id)
    )


def notify_status_change(employee_id, old_status, new_status, reason):
    """
    状态变更通知
    
    Args:
        employee_id: 员工ID
        old_status: 旧状态
        new_status: 新状态
        reason: 变更原因
    """
    # 获取员工关联的用户
    user = query_db(
        'SELECT id, username FROM users WHERE employee_id = ?',
        (employee_id,),
        one=True
    )
    
    if not user:
        return
    
    status_map = {
        'trainee': '培训期',
        'C': 'C级',
        'B': 'B级',
        'A': 'A级',
        'eliminated': '已淘汰'
    }
    
    old_label = status_map.get(old_status, old_status)
    new_label = status_map.get(new_status, new_status)
    
    title = '状态变更通知'
    content = f'您的状态已从 {old_label} 变更为 {new_label}。原因：{reason}'
    
    create_notification(
        user['id'],
        title,
        content,
        NotificationType.STATUS_CHANGE,
        '/employee/profile'
    )


def notify_salary_ready(employee_id, year_month, total_salary):
    """
    薪资发放通知
    
    Args:
        employee_id: 员工ID
        year_month: 年月
        total_salary: 总薪资
    """
    user = query_db(
        'SELECT id FROM users WHERE employee_id = ?',
        (employee_id,),
        one=True
    )
    
    if not user:
        return
    
    title = f'{year_month} 月薪资已生成'
    content = f'您的 {year_month} 月薪资已生成，总额 ¥{total_salary:.2f}，请查看详情。'
    
    create_notification(
        user['id'],
        title,
        content,
        NotificationType.SALARY,
        '/employee/salary'
    )


def notify_dispute_response(employee_id, year_month, status, response):
    """
    异议回复通知
    
    Args:
        employee_id: 员工ID
        year_month: 年月
        status: 处理状态
        response: 回复内容
    """
    user = query_db(
        'SELECT id FROM users WHERE employee_id = ?',
        (employee_id,),
        one=True
    )
    
    if not user:
        return
    
    status_text = {'approved': '已通过', 'rejected': '已拒绝'}
    
    title = f'{year_month} 月薪资异议处理通知'
    content = f'您提交的薪资异议{status_text.get(status, status)}。管理员回复：{response}'
    
    create_notification(
        user['id'],
        title,
        content,
        NotificationType.DISPUTE,
        '/employee/salary'
    )


def broadcast_announcement(title, content, target_role=None):
    """
    发布公告（广播通知）
    
    Args:
        title: 公告标题
        content: 公告内容
        target_role: 目标角色（None=全部）
    """
    # 获取目标用户
    if target_role:
        users = query_db('SELECT id FROM users WHERE role = ?', (target_role,))
    else:
        users = query_db('SELECT id FROM users')
    
    # 批量创建通知
    db = get_db()
    for user in users:
        db.execute(
            '''INSERT INTO notifications 
               (user_id, title, content, type, is_read, created_at)
               VALUES (?, ?, ?, ?, 0, datetime('now', 'localtime'))''',
            (user['id'], title, content, NotificationType.ANNOUNCEMENT)
        )
    db.commit()



