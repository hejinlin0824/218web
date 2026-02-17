from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from .models import EbbinghausBatch
from .utils import EbbinghausManager

@shared_task
def check_ebbinghaus_notifications():
    """
    定时任务：检查艾宾浩斯复习节点
    频率：建议每 5 分钟运行一次
    """
    now = timezone.now()
    # 提前提醒的时间窗口：5分钟后到期的，或者已经过期的(但没发邮件的)
    notify_threshold = now + timedelta(minutes=5)
    
    # 1. 筛选开启了提醒的用户的所有批次
    # 使用 select_related 预加载用户数据，减少数据库查询
    batches = EbbinghausBatch.objects.filter(
        user__enable_ebbinghaus=True
    ).select_related('user')

    email_count = 0
    
    for batch in batches:
        is_changed = False # 标记是否需要保存数据库
        status = batch.review_status
        
        # 2. 遍历该批次的所有阶段
        # 按照 phase_1, phase_2... 顺序检查
        for key, node in status.items():
            # 如果该节点未完成 且 未发送过通知
            if not node['done'] and not node.get('notified', False):
                
                due_time = timezone.datetime.fromisoformat(node['due'])
                
                # 3. 判定时间：如果 (当前时间 + 5分钟) >= 应复习时间
                # 意味着：要么快到了(5分钟内)，要么已经过了
                if notify_threshold >= due_time:
                    
                    # 发送邮件
                    user_email = batch.user.email
                    if user_email:
                        try:
                            send_review_email(batch, node['name'])
                            
                            # 4. 标记为已通知
                            status[key]['notified'] = True
                            is_changed = True
                            email_count += 1
                            
                        except Exception as e:
                            print(f"Error sending email to {batch.user.username}: {e}")
        
        # 只有当数据发生变化时才写入数据库，减轻压力
        if is_changed:
            batch.save(update_fields=['review_status'])

    return f"Checked Ebbinghaus batches. Sent {email_count} emails."

def send_review_email(batch, phase_name):
    """
    发送单封提醒邮件
    """
    subject = f"【记忆提醒】⏰ 你的单词复习时间到了！"
    
    # 构建复习页面的绝对路径 (需要你的 settings.ALLOWED_HOSTS 配置正确)
    # 这里我们硬编码或者使用 request.build_absolute_uri 的替代方案
    # 在 Celery 中无法获取 request，通常建议在 settings 里配置 SITE_URL
    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000') 
    plan_url = f"{site_url}{reverse('vocabulary:plan')}"
    
    message = f"""
    你好 {batch.user.nickname or batch.user.username}：

    根据艾宾浩斯遗忘曲线，现在是复习单词的最佳时机！

    📚 词书：{batch.book_id}
    📅 学习日期：{batch.study_date}
    ⏳ 复习节点：{phase_name}

    请点击下方链接开始复习，点亮你的记忆曲线：
    {plan_url}

    (如果不复习，这批单词可能就要忘记了哦！)
    
    -------------------------
    Web 218 DSSG Lab
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [batch.user.email],
        fail_silently=False,
    )