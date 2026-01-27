from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Message
from django.urls import reverse
from notifications.models import Notification
from django.contrib import messages 

from django.http import JsonResponse # 👈 新增引入
from django.utils import timezone # 👈 用于格式化时间

User = get_user_model()

@login_required
def inbox(request):
    """私信列表页 - 性能优化版"""
    # 🧹 清理旧弹窗缓存
    storage = messages.get_messages(request)
    storage.used = True
    
    user = request.user
    
    # 🚀 算法优化：不再查询所有历史消息，而是尽量减少 Python 层面的循环
    # 获取所有涉及的消息，按时间倒序
    all_messages = Message.objects.select_related('sender', 'recipient').filter(
        Q(sender=user) | Q(recipient=user)
    ).order_by('-timestamp')

    conversations = []
    seen_users = set()

    # 这里的循环虽然看起来还是遍历，但在 Python 中 Set 的查找极快
    # 只要拿到最新的消息，就跳过该用户的后续旧消息
    for msg in all_messages:
        other_user_id = msg.recipient_id if msg.sender_id == user.id else msg.sender_id
        
        if other_user_id not in seen_users:
            conversations.append(msg)
            seen_users.add(other_user_id)

    return render(request, 'direct_messages/inbox.html', {'conversations': conversations})

@login_required
def chat_room(request, user_id):
    """聊天室 (支持 AJAX)"""
    storage = messages.get_messages(request)
    storage.used = True

    target_user = get_object_or_404(User, pk=user_id)
    current_user = request.user
    
    if request.method == 'POST':
        content = request.POST.get('content')
        
        # 判断是否为 AJAX 请求 (Fetch API 会带这个头，或者我们自己手动带)
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if content and content.strip():
            msg = Message.objects.create(
                sender=current_user,
                recipient=target_user,
                content=content
            )
            
            # 创建通知 (逻辑不变)
            Notification.objects.create(
                recipient=target_user,
                actor=current_user,
                verb='system', 
                target_url=reverse('direct_messages:chat_room', args=[current_user.id]),
                content=f"发来一条私信: {content[:30]}..."
            )

            # 👇👇👇 核心修改：如果是 AJAX，返回 JSON 👇👇👇
            if is_ajax:
                return JsonResponse({
                    'status': 'ok',
                    'content': msg.content,
                    'timestamp': timezone.localtime(msg.timestamp).strftime('%H:%M'), # 返回格式化好的时间
                    'avatar_url': current_user.avatar.url if current_user.avatar else None,
                    'username_char': current_user.username[0].upper()
                })
            
            # 如果不是 AJAX (比如 JS 挂了)，回退到老办法
            return redirect('direct_messages:chat_room', user_id=user_id)

    # GET 请求逻辑不变
    messages_history = Message.objects.select_related('sender').filter(
        Q(sender=current_user, recipient=target_user) |
        Q(sender=target_user, recipient=current_user)
    ).order_by('timestamp')
    
    Message.objects.filter(sender=target_user, recipient=current_user, is_read=False).update(is_read=True)
    
    return render(request, 'direct_messages/chat_room.html', {
        'target_user': target_user,
        'messages': messages_history
    })

@login_required
def delete_conversation(request, user_id):
    """删除对话"""
    storage = messages.get_messages(request)
    storage.used = True

    if request.method == 'POST':
        # 直接使用 ID 进行删除，不需要先查 User 对象，省一次数据库查询
        current_user = request.user
        
        Message.objects.filter(
            Q(sender=current_user, recipient_id=user_id) |
            Q(sender_id=user_id, recipient=current_user)
        ).delete()
        
    return redirect('direct_messages:inbox')