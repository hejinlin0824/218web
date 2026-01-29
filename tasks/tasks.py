# tasks/tasks.py

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.urls import reverse
import random

from .models import Task, TaskParticipant
from notifications.models import Notification

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


@shared_task
def auto_settle_expired_tasks():
    """
    自动结算过期任务
    每分钟运行一次，检查所有未结束但已过期的任务，自动结算
    """
    # 获取所有未结束且已过期的任务
    expired_tasks = Task.objects.filter(
        status__in=['open', 'in_progress'],
        deadline__lte=timezone.now()
    )
    
    settled_count = 0
    
    for task in expired_tasks:
        try:
            with transaction.atomic():
                # 获取已接受的参与者
                accepted_participants = task.participants.filter(status='accepted')
                
                if not accepted_participants.exists():
                    # 没有参与者，直接关闭任务
                    task.status = 'closed'
                    task.save()
                    settled_count += 1
                    continue
                
                if task.bounty == 0:
                    # 没有悬赏，直接关闭任务
                    task.status = 'closed'
                    task.save()
                    settled_count += 1
                    continue
                
                # 有悬赏，进行分配
                if task.is_class_task:
                    # 班级任务：平分给所有参与者（舍弃小数点）
                    total_bounty = task.bounty
                    participant_count = accepted_participants.count()
                    
                    # 每人应得金币（向下取整）
                    coins_per_person = total_bounty // participant_count
                    
                    # 将参与者列表转为列表，以便随机选择
                    participants_list = list(accepted_participants)
                    random.shuffle(participants_list)
                    
                    # 分配金币
                    recipients_count = 0
                    total_distributed = 0
                    
                    if coins_per_person > 0:
                        # 每人至少能分到1个币
                        remainder = total_bounty % participant_count
                        
                        for i, participant in enumerate(participants_list):
                            coins = coins_per_person
                            # 如果有余数且在前面，额外获得1个币
                            if remainder > 0 and i < remainder:
                                coins += 1
                            
                            if coins > 0:
                                participant.user.earn_rewards(coins=coins, growth=0)
                                recipients_count += 1
                                total_distributed += coins
                                
                                # 发送通知
                                Notification.objects.create(
                                    recipient=participant.user,
                                    actor=task.creator,
                                    verb='task_reward',
                                    target_url=reverse('tasks:task_detail', args=[task.id]),
                                    content=f"任务【{task.title}】已结束，你获得 {coins} 金币！"
                                )
                    else:
                        # 每人不到1个币
                        # 如果每人平均不到0.5个币，都不给
                        # 否则，随机选择total_bounty个人，每人给1个币
                        if total_bounty > 0:
                            # 计算每人平均金币（浮点数）
                            avg_coins = total_bounty / participant_count
                            if avg_coins < 0.5:
                                # 每人平均不到0.5个币，都不给
                                pass
                            else:
                                # 随机选择total_bounty个人，每人给1个币
                                num_recipients = min(total_bounty, participant_count)
                                for i in range(num_recipients):
                                    participant = participants_list[i]
                                    participant.user.earn_rewards(coins=1, growth=0)
                                    recipients_count += 1
                                    total_distributed += 1
                                    
                                    # 发送通知
                                    Notification.objects.create(
                                        recipient=participant.user,
                                        actor=task.creator,
                                        verb='task_reward',
                                        target_url=reverse('tasks:task_detail', args=[task.id]),
                                        content=f"任务【{task.title}】已结束，你获得 1 金币！"
                                    )
                    
                    # 标记第一个参与者为获胜者（如果有获得金币的人）
                    if recipients_count > 0:
                        task.winner = participants_list[0].user
                    
                else:
                    # 普通任务：赏金给第一个接受任务的人
                    first_participant = accepted_participants.first()
                    first_participant.user.earn_rewards(coins=task.bounty, growth=0)
                    
                    # 发送通知
                    Notification.objects.create(
                        recipient=first_participant.user,
                        actor=task.creator,
                        verb='task_reward',
                        target_url=reverse('tasks:task_detail', args=[task.id]),
                        content=f"任务【{task.title}】已结束，你获得 {task.bounty} 金币！"
                    )
                    
                    task.winner = first_participant.user
                
                # 关闭任务
                task.status = 'closed'
                task.save()
                settled_count += 1
                
        except Exception as e:
            print(f"自动结算任务 {task.id} 失败: {e}")
            continue
    
    return f"自动结算了 {settled_count} 个过期任务"