from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q,Max
from .models import Message
from django.urls import reverse
from notifications.models import Notification
from django.contrib import messages 
from user_app.models import Friendship # 引用 Friendship
from django.http import JsonResponse # 👈 新增引入
from django.utils import timezone # 👈 用于格式化时间
from django.urls import reverse
User = get_user_model()

@login_required
def inbox(request):
    user = request.user
    
    # 1. 获取所有好友列表
    # 查找所有 status='accepted' 的关系
    friend_relations = Friendship.objects.filter(
        Q(from_user=user) | Q(to_user=user),
        status='accepted'
    )
    
    friends_ids = set()
    friends_list = []
    
    for rel in friend_relations:
        friend = rel.to_user if rel.from_user == user else rel.from_user
        friends_ids.add(friend.id)
        # 顺便获取最后一条消息用于展示
        last_msg = Message.objects.filter(
            Q(sender=user, recipient=friend) | Q(sender=friend, recipient=user)
        ).order_by('-timestamp').first()
        
        friends_list.append({
            'user': friend,
            'last_msg': last_msg
        })
    
    # 2. 获取临时聊天列表 (有过消息往来，但不是好友)
    # 获取所有相关消息
    all_conversations = Message.objects.filter(
        Q(sender=user) | Q(recipient=user)
    ).values('sender', 'recipient').annotate(last_time=Max('timestamp')).order_by('-last_time')
    
    temp_chat_ids = set()
    temp_chat_list = []
    
    for convo in all_conversations:
        other_id = convo['recipient'] if convo['sender'] == user.id else convo['sender']
        
        # 核心逻辑：如果这个人不在好友列表里，且没被处理过，加入临时聊天
        if other_id not in friends_ids and other_id not in temp_chat_ids:
            temp_chat_ids.add(other_id)
            other_user = User.objects.get(pk=other_id)
            
            last_msg = Message.objects.filter(
                Q(sender=user, recipient=other_user) | Q(sender=other_user, recipient=user)
            ).order_by('-timestamp').first()
            
            temp_chat_list.append({
                'user': other_user,
                'last_msg': last_msg
            })

    # 处理选中聊天的逻辑 (和以前一样，或者是简单的 placeholder)
    active_user_id = request.GET.get('uid')
    active_user = None
    messages = []
    
    if active_user_id:
        active_user = get_object_or_404(User, pk=active_user_id)
        messages = Message.objects.filter(
            Q(sender=user, recipient=active_user) | Q(sender=active_user, recipient=user)
        ).order_by('timestamp')
        # 标记已读
        messages.filter(recipient=user, is_read=False).update(is_read=True)

    context = {
        'friends_list': friends_list,
        'temp_chat_list': temp_chat_list,
        'active_user': active_user,
        'messages': messages
    }
    return render(request, 'direct_messages/inbox.html', context)

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

@login_required
def delete_chat(request, user_id):
    """删除聊天记录"""
    target_user = get_object_or_404(User, pk=user_id)
    # 物理删除所有消息 (好友关系还在，所以是清空记录；非好友则相当于删除会话)
    Message.objects.filter(
        Q(sender=request.user, recipient=target_user) | 
        Q(sender=target_user, recipient=request.user)
    ).delete()
    
    return redirect('direct_messages:inbox')

@login_required
def send_message(request):
    """
    处理私信发送
    """
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient_id')
        content = request.POST.get('content')
        
        if recipient_id and content:
            recipient = get_object_or_404(User, pk=recipient_id)
            
            # 创建消息
            new_msg = Message.objects.create(
                sender=request.user,
                recipient=recipient,
                content=content
            )
            
            # 发送成功后，直接刷新页面，不需要任何弹窗
            return redirect(f"{reverse('direct_messages:inbox')}?uid={recipient_id}")
            
    return redirect('direct_messages:inbox')