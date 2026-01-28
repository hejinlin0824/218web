# tasks/tasks.py

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Task

User = get_user_model()

@shared_task
def send_task_invitation_emails(task_id, user_ids):
    """
    异步发送任务邀请邮件
    """
    try:
        task = Task.objects.get(pk=task_id)
        users = User.objects.filter(id__in=user_ids)
        
        # 批量发送或循环发送（为了简单，这里循环发，量大建议用 send_mass_mail）
        count = 0
        for user in users:
            if not user.email:
                continue
                
            subject = f"【Web 218 实验室】您收到一个新的悬赏任务邀请：{task.title}"
            message = f"""
            你好 {user.nickname or user.username}：
            
            {task.creator.nickname or task.creator.username} 邀请你参加任务：
            
            ------------------------------------------------
            任务标题：{task.title}
            悬赏金币：🪙 {task.bounty}
            截止时间：{task.deadline.strftime('%Y-%m-%d %H:%M')}
            ------------------------------------------------
            
            请登录实验室查看详情并选择接受或拒绝。
            """
            
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
            count += 1
            
        return f"Successfully sent {count} invitation emails."
    
    except Task.DoesNotExist:
        return "Task not found."