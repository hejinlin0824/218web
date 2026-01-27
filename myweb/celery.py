import os
from celery import Celery

# 1. 设置默认的 Django settings 模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myweb.settings')

# 2. 创建 Celery 实例，名称通常就是项目名
app = Celery('myweb')

# 3. 从 Django 的 settings.py 中读取配置
# namespace='CELERY' 意味着在 settings.py 中，所有 Celery 相关的配置都要以 CELERY_ 开头
app.config_from_object('django.conf:settings', namespace='CELERY')

# 4. 自动发现所有已注册 app 下的 tasks.py 文件
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')