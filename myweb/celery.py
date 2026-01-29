# myweb/celery.py

import os
from celery import Celery
from celery.schedules import crontab # 👈 引入 crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myweb.settings')

app = Celery('myweb')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# 👇👇👇 新增定时任务配置 👇👇👇
app.conf.beat_schedule = {
    'check-unread-messages-every-minute': {
        'task': 'direct_messages.tasks.send_unread_message_reminders',
        'schedule': 60.0, # 每 60 秒运行一次
    },
    'auto-settle-expired-tasks-every-minute': {
        'task': 'tasks.tasks.auto_settle_expired_tasks',
        'schedule': 60.0, # 每 60 秒运行一次
    },
}