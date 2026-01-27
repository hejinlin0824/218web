from django.db import models
from django.conf import settings

class Notification(models.Model):
    CHOICES = (
        ('like', '点赞'),
        ('comment', '评论'),
        ('reply', '回复'),
        ('follow', '关注'), # 👈 新增这一行
        ('system', '系统通知')
    )
    
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', verbose_name='接收者')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='triggered_notifications', verbose_name='触发者')
    verb = models.CharField('动作', max_length=20, choices=CHOICES)
    target_url = models.CharField('跳转链接', max_length=255)
    content = models.TextField('消息摘要', blank=True, null=True)
    is_read = models.BooleanField('已读', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    is_read = models.BooleanField('已读', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.actor} {self.get_verb_display()} - {self.recipient}"