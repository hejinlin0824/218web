from celery import shared_task
from .models import Notification
from django.contrib.auth import get_user_model
import time

User = get_user_model()

@shared_task
def send_system_notification(user_id, message):
    """
    模拟一个耗时的系统通知发送任务
    """
    # 模拟耗时操作 (例如网络请求或复杂计算)
    print(f"正在准备给用户 {user_id} 发送通知...")
    time.sleep(5)  # 假装忙了5秒
    
    try:
        user = User.objects.get(pk=user_id)
        Notification.objects.create(
            recipient=user,
            actor=user, # 系统通知暂时用自己当触发者，或者专门建个系统账号
            verb='system', # 你需要在 Notification model 的 choices 里加一个 'system'
            target_url='/',
            content=f"[系统消息] {message}"
        )
        print(f"通知已发送给 {user.username}！")
        return "Success"
    except User.DoesNotExist:
        print("用户不存在")
        return "Failed"