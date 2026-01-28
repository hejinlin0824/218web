# direct_messages/tasks.py

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models import Count
from .models import Message

User = get_user_model()

@shared_task
def send_unread_message_reminders():
    """
    每隔一段时间运行：
    检查是否有超过15分钟未读的消息，且尚未发送邮件提醒。
    如果满足条件，汇总发给接收者，并标记消息为 'is_email_sent=True'。
    """
    now = timezone.now()
    # 15分钟前的时间点
    time_threshold = now - timedelta(minutes=15)
    
    # 1. 查询满足条件的消息：
    #    - 未读 (is_read=False)
    #    - 发送时间早于15分钟前 (timestamp__lte=time_threshold)
    #    - 还没发过邮件 (is_email_sent=False)
    unread_msgs = Message.objects.filter(
        is_read=False,
        is_email_sent=False,
        timestamp__lte=time_threshold
    ).select_related('sender', 'recipient')

    if not unread_msgs.exists():
        return "No unread messages to remind."

    # 2. 按接收者分组 (避免发多封邮件)
    # 格式: { recipient_id: [msg1, msg2, ...] }
    recipient_map = {}
    for msg in unread_msgs:
        if msg.recipient.email: # 只有有邮箱的用户才发
            if msg.recipient.id not in recipient_map:
                recipient_map[msg.recipient.id] = {
                    'user': msg.recipient,
                    'messages': []
                }
            recipient_map[msg.recipient.id]['messages'].append(msg)

    # 3. 遍历接收者发送邮件
    email_count = 0
    for uid, data in recipient_map.items():
        user = data['user']
        msgs = data['messages']
        msg_count = len(msgs)
        
        # 统计发送者 (例如: 张三(2), 李四(1))
        senders = {}
        for m in msgs:
            sender_name = m.sender.nickname or m.sender.username
            senders[sender_name] = senders.get(sender_name, 0) + 1
            
        sender_summary = ", ".join([f"{name}({count}条)" for name, count in senders.items()])

        # 构建邮件内容
        subject = f'【Web 218 实验室】您有 {msg_count} 条未读私信待查看'
        
        # 生成私信链接 (假设直接跳到收件箱)
        # 注意：在 Celery 中生成 URL 需要硬编码域名或使用 Sites 框架，这里简单处理
        inbox_url = "http://127.0.0.1:8000/messages/" # ⚠️ 生产环境请改为你的实际域名
        
        email_body = f"""
        你好 {user.nickname or user.username}：
        
        你在 Web 218 实验室收到了新的私信，已经超过 15 分钟未查看。
        
        待处理消息：{sender_summary}
        
        请点击下方链接查看消息：
        {inbox_url}
        
        (此邮件为系统自动发送，请勿回复)
        """
        
        try:
            send_mail(
                subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False
            )
            
            # 4. 标记这些消息为已发送提醒
            # 使用 bulk_update 优化性能虽然更好，但这里为了简单直接遍历保存
            # 或者 Message.objects.filter(id__in=[m.id for m in msgs]).update(is_email_sent=True)
            msg_ids = [m.id for m in msgs]
            Message.objects.filter(id__in=msg_ids).update(is_email_sent=True)
            
            email_count += 1
            print(f"✅ 已发送提醒邮件给 {user.username}")
            
        except Exception as e:
            print(f"❌ 发送邮件给 {user.username} 失败: {e}")

    return f"Sent {email_count} reminder emails."