from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Notification
from django.http import JsonResponse

@login_required
def notification_list(request):
    """消息列表页 - 支持分页和一键已读"""
    all_notifications = request.user.notifications.all()
    total_count = all_notifications.count()

    # 获取显示数量参数（支持GET和POST）
    if request.method == 'POST' and 'current_limit' in request.POST:
        limit = int(request.POST.get('current_limit', 6))
    else:
        limit = int(request.GET.get('limit', 6))  # 默认显示6条

    # 处理一键已读
    if request.method == 'POST' and 'mark_all_read' in request.POST:
        count = request.user.notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, f"已将 {count} 条通知标记为已读")
        return redirect('notifications:list')

    # 处理点击"更多"
    if request.method == 'POST' and 'load_more' in request.POST:
        limit = limit + 5  # 每次多加载5条

    # 确保limit不超过总数
    if limit > total_count:
        limit = total_count

    # 分页显示
    notifications = all_notifications[:limit]
    has_more = limit < total_count

    context = {
        'notifications': notifications,
        'has_more': has_more,
        'current_limit': limit,
        'total_count': total_count
    }
    return render(request, 'notifications/list.html', context)

@login_required
def mark_read_and_redirect(request, pk):
    """点击消息 -> 标记已读 -> 跳转"""
    notice = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notice.is_read = True
    notice.save()
    return redirect(notice.target_url)

@login_required
def get_unread_count(request):
    """
    轻量级 API：仅返回未读消息数量
    供前端轮询使用
    """
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})
        
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'count': count})