"""
通知中心路由
"""
from flask import Blueprint, render_template, request, jsonify
from core.auth import login_required, role_required, get_current_user
from core.notifications import (
    get_user_notifications,
    get_unread_count,
    mark_as_read,
    mark_all_as_read,
    delete_notification,
    broadcast_announcement
)

bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@bp.route('/')
@login_required
def notification_center():
    """通知中心页面"""
    user = get_current_user()
    
    # 获取通知列表
    notifications = get_user_notifications(user['id'], limit=50)
    unread_count = get_unread_count(user['id'])
    
    return render_template('notifications/center.html',
                         notifications=notifications,
                         unread_count=unread_count,
                         user=user)


@bp.route('/api/count')
@login_required
def get_notification_count():
    """获取未读通知数量（API）"""
    user = get_current_user()
    count = get_unread_count(user['id'])
    
    return jsonify({'count': count})


@bp.route('/api/list')
@login_required
def get_notification_list():
    """获取通知列表（API）"""
    user = get_current_user()
    unread_only = request.args.get('unread', 'false') == 'true'
    
    notifications = get_user_notifications(user['id'], unread_only=unread_only)
    
    return jsonify({
        'notifications': [dict(n) for n in notifications],
        'unread_count': get_unread_count(user['id'])
    })


@bp.route('/api/read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """标记为已读"""
    user = get_current_user()
    
    try:
        mark_as_read(notification_id, user['id'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@bp.route('/api/read_all', methods=['POST'])
@login_required
def mark_all_read():
    """标记全部已读"""
    user = get_current_user()
    
    try:
        mark_all_as_read(user['id'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@bp.route('/api/delete/<int:notification_id>', methods=['POST'])
@login_required
def delete_notif(notification_id):
    """删除通知"""
    user = get_current_user()
    
    try:
        delete_notification(notification_id, user['id'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@bp.route('/admin/broadcast', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_broadcast():
    """管理员发布公告"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        target_role = request.form.get('target_role', '')
        
        if not title or not content:
            return jsonify({'success': False, 'message': '请填写完整信息'})
        
        try:
            broadcast_announcement(
                title,
                content,
                target_role if target_role else None
            )
            return jsonify({'success': True, 'message': '公告已发布'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'发布失败: {str(e)}'})
    
    return render_template('notifications/broadcast.html', user=get_current_user())



