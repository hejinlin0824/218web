from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Notification

@login_required
def notification_list(request):
    """消息列表页"""
    notifications = request.user.notifications.all()
    # 一键已读 (可选，或者点击单个跳转时设为已读)
    # request.user.notifications.filter(is_read=False).update(is_read=True)
    
    return render(request, 'notifications/list.html', {'notifications': notifications})

@login_required
def mark_read_and_redirect(request, pk):
    """点击消息 -> 标记已读 -> 跳转"""
    notice = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notice.is_read = True
    notice.save()
    return redirect(notice.target_url)