from django.db import models
from django.conf import settings

class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='sent_messages',
        verbose_name='发送者'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='received_messages',
        verbose_name='接收者'
    )
    content = models.TextField('内容')
    timestamp = models.DateTimeField('发送时间', auto_now_add=True)
    is_read = models.BooleanField('已读', default=False)
    
    # 👇👇👇 新增字段：是否已发送邮件提醒 👇👇👇
    is_email_sent = models.BooleanField('已发送邮件提醒', default=False)

    class Meta:
        ordering = ['timestamp']
        verbose_name = '私信'
        verbose_name_plural = verbose_name

    def __str__(self):
        # 修改这里以避免之前的弹窗格式问题，只返回简单描述
        return f"Message {self.id}"