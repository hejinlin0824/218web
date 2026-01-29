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
    # 🔥🔥🔥 核心修复 1：强制清空该请求中的所有待显示消息 🔥🔥🔥
    # 这能防止之前的残留消息（比如 "From xxx..."）在刷新页面时跳出来
    storage = messages.get_messages(request)
    for _ in storage: 
        pass  # 迭代一次即视为“已读取/已消费”，Django 就不会再渲染它们了

    target_user = get_object_or_404(User, pk=user_id)
    current_user = request.user
    
    if request.method == 'POST':
        content = request.POST.get('content')
        
        # 👇👇👇 修改开始：更强健的 AJAX 检测 👇👇👇
        is_ajax = (
            request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            request.accepts('application/json')
        )
        # 👆👆👆 修改结束 👆👆👆

        if content and content.strip():
            msg = Message.objects.create(
                sender=current_user,
                recipient=target_user,
                content=content
            )
            
            # 👇👇👇 【修改点 1】修复通知跳转链接 👇👇👇
            Notification.objects.create(
                recipient=target_user,
                actor=current_user,
                verb='system', 
                # 🔴 原来是指向 chat_room (可能被你视为旧版)
                # target_url=reverse('direct_messages:chat_room', args=[current_user.id]),
                
                # 🟢 改为：指向 Inbox 页面，并带上 uid 参数，这样打开就是分栏视图并选中对方
                target_url=reverse('direct_messages:inbox') + f'?uid={current_user.id}',
                
                content=f"发来一条私信: {content[:30]}..."
            )
            # 👆👆👆 修改结束 👆👆👆
            # AJAX 请求返回 JSON
            if is_ajax:
                return JsonResponse({
                    'status': 'ok',
                    'id': msg.id,
                    'content': msg.content,
                    'timestamp': timezone.localtime(msg.timestamp).strftime('%H:%M'),
                    'avatar_url': current_user.avatar.url if current_user.avatar else None,
                    'username_char': current_user.username[0].upper()
                })
            
            # 非 AJAX 请求才重定向（刷新页面）
            return redirect('direct_messages:chat_room', user_id=user_id)

    # GET 请求逻辑
    messages_history = Message.objects.select_related('sender').filter(
        Q(sender=current_user, recipient=target_user) |
        Q(sender=target_user, recipient=current_user)
    ).order_by('timestamp')
    
    Message.objects.filter(sender=target_user, recipient=current_user, is_read=False).update(is_read=True)
    
    return render(request, 'direct_messages/chat_room.html', {
        'target_user': target_user,
        'messages': messages_history
    })

# 👇👇👇 修改开始：允许 GET 请求以配合前端链接 👇👇👇
@login_required
def delete_conversation(request, user_id):
    """
    删除对话 (从列表中移除)
    """
    # 获取消息存储对象（处理潜在的消息积压）
    storage = messages.get_messages(request)
    storage.used = True

    # 逻辑修改：不仅仅检查 POST，允许 GET 请求通过
    # 因为 inbox.html 中使用的是 <a> 标签链接，默认是 GET 请求
    current_user = request.user
    
    # 执行物理删除
    Message.objects.filter(
        Q(sender=current_user, recipient_id=user_id) |
        Q(sender_id=user_id, recipient=current_user)
    ).delete()
        
    return redirect('direct_messages:inbox')
# 👆👆👆 修改结束 👆👆👆

@login_required
def delete_chat(request, user_id):
    """删除聊天记录"""
    # 这里的逻辑本身支持 GET，不需要大改，但为了保险起见，清理一下
    target_user = get_object_or_404(User, pk=user_id)
    
    Message.objects.filter(
        Q(sender=request.user, recipient=target_user) | 
        Q(sender=target_user, recipient=request.user)
    ).delete()
    
    # 删除后，如果是临时会话，重定向回纯净的 inbox
    return redirect('direct_messages:inbox')

# 👇👇👇 修改开始：彻底去除弹窗代码 👇👇👇
@login_required
def send_message(request):
    """
    处理私信发送 (Inbox 页面的快速发送)
    """
    # 1. 清空消息存储，防止弹窗
    storage = messages.get_messages(request)
    for _ in storage:
        pass

    if request.method == 'POST':
        recipient_id = request.POST.get('recipient_id')
        content = request.POST.get('content')
        
        if recipient_id and content:
            recipient = get_object_or_404(User, pk=recipient_id)
            
            # 2. 创建消息记录
            Message.objects.create(
                sender=request.user,
                recipient=recipient,
                content=content
            )
            
            # 👇👇👇 【修改点 2】修复通知跳转链接 👇👇👇
            Notification.objects.create(
                recipient=recipient,
                actor=request.user,
                verb='system', 
                # 🟢 改为：指向 Inbox 页面，并自动选中发送者
                target_url=reverse('direct_messages:inbox') + f'?uid={request.user.id}',
                
                content=f"发来一条私信: {content[:30]}..."
            )
            # 👆👆👆 修改结束 👆👆👆
            return redirect(f"{reverse('direct_messages:inbox')}?uid={recipient_id}")
            
    return redirect('direct_messages:inbox')

@login_required
def get_new_messages(request, sender_id):
    sender = get_object_or_404(User, pk=sender_id)
    last_msg_id = request.GET.get('last_id', 0)
    
    # 转换为整数，防止报错
    try:
        last_msg_id = int(last_msg_id)
    except ValueError:
        last_msg_id = 0

    # 🔍 调试打印 (你可以看下终端输出了什么)
    # print(f"User {request.user} polling messages from {sender} after ID {last_msg_id}")

    # 查询条件：
    # 1. 发送者是 sender (对方)
    # 2. 接收者是 request.user (我)
    # 3. ID 大于前端传来的 last_id
    new_messages = Message.objects.filter(
        sender=sender,
        recipient=request.user,
        id__gt=last_msg_id
    ).order_by('timestamp')
    
    # 标记已读
    if new_messages.exists():
        new_messages.update(is_read=True)
    
    data = []
    for msg in new_messages:
        data.append({
            'id': msg.id,
            'content': msg.content,
            'timestamp': timezone.localtime(msg.timestamp).strftime('%H:%M'),
            'avatar_url': sender.avatar.url if sender.avatar else None,
            'username_char': sender.username[0].upper()
        })
        
    return JsonResponse({'messages': data})