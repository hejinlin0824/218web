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
    检查是否有超过5分钟未读的消息，且尚未发送邮件提醒。
    如果满足条件，汇总发给接收者，并标记消息为 'is_email_sent=True'。

    优化：每个接收者+发送者组合只发一封邮件，避免重复。
    """
    now = timezone.now()
    # 5分钟前的时间点
    time_threshold = now - timedelta(minutes=5)
    
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

    # 2. 按接收者分组，再按发送者进一步分组
    # 格式: { recipient_id: { sender_id: [msg1, msg2, ...] } }
    recipient_sender_map = {}
    for msg in unread_msgs:
        if msg.recipient.email: # 只有有邮箱的用户才发
            if msg.recipient.id not in recipient_sender_map:
                recipient_sender_map[msg.recipient.id] = {
                    'user': msg.recipient,
                    'senders': {}
                }
            
            # 按发送者分组
            if msg.sender.id not in recipient_sender_map[msg.recipient.id]['senders']:
                recipient_sender_map[msg.recipient.id]['senders'][msg.sender.id] = {
                    'sender': msg.sender,
                    'messages': []
                }
            
            recipient_sender_map[msg.recipient.id]['senders'][msg.sender.id]['messages'].append(msg)

    # 3. 遍历接收者发送邮件（每个接收者只发一封）
    email_count = 0
    for uid, recipient_data in recipient_sender_map.items():
        user = recipient_data['user']
        senders_data = recipient_data['senders']
        
        # 统计所有消息数量
        total_msgs = sum(len(s_data['messages']) for s_data in senders_data.values())
        
        # 构建发送者汇总（按未读消息数量排序）
        sender_list = []
        for sender_id, s_data in senders_data.items():
            sender = s_data['sender']
            msg_count = len(s_data['messages'])
            sender_list.append((sender, msg_count))
        
        # 按消息数量降序排序
        sender_list.sort(key=lambda x: x[1], reverse=True)
        
        # 生成发送者列表文本
        sender_lines = []
        for sender, count in sender_list:
            sender_lines.append(f"  - {sender.nickname or sender.username}: {count} 条未读私信")
        sender_text = "\n".join(sender_lines)
        
        # 构建邮件内容
        subject = f'【Web 218 实验室】您有 {total_msgs} 条未读私信待查看'
        
        # 生成私信链接
        inbox_url = "http://127.0.0.1:8000/messages/" # ⚠️ 生产环境请改为你的实际域名
        
        email_body = f"""
你好 {user.nickname or user.username}：

你在 Web 218 实验室收到了新的私信，已经超过 5 分钟未查看。

未读私信详情：
{sender_text}

共计：{total_msgs} 条未读私信

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
            # 收集所有消息ID
            all_msg_ids = []
            for s_data in senders_data.values():
                all_msg_ids.extend([m.id for m in s_data['messages']])
            
            Message.objects.filter(id__in=all_msg_ids).update(is_email_sent=True)
            
            email_count += 1
            print(f"✅ 已发送提醒邮件给 {user.username}，汇总 {total_msgs} 条消息，来自 {len(sender_list)} 位发送者")
            
        except Exception as e:
            print(f"❌ 发送邮件给 {user.username} 失败: {e}")

    return f"Sent {email_count} reminder emails."