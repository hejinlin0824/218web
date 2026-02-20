# cyber_fortune/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class FortuneProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='fortune_profile',
        verbose_name='所属用户'
    )
    birth_date = models.DateField('降生参数 (出生日期)')
    zodiac = models.CharField('赛博星象', max_length=20, blank=True)
    mbti = models.CharField('MBTI 人格', max_length=4, default='INTJ') # 新增 MBTI
    
    monthly_luck_score = models.PositiveIntegerField('本月累计气运池', default=0)
    muyu_clicks = models.PositiveIntegerField('累计敲击木鱼次数', default=0) # 新增木鱼统计
    last_reset_month = models.CharField('最后刷新月份', max_length=7, blank=True)

    class Meta:
        verbose_name = '祈福档案'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.username} 的赛博档案"


class DailyBlessing(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='blessings',
        verbose_name='祈福者'
    )
    bless_date = models.DateField('祈福日期', default=timezone.now)
    score = models.PositiveIntegerField('今日算力 (气运值)')
    fortune_text = models.CharField('赛博吉言', max_length=255)
    created_at = models.DateTimeField('记录生成时间', auto_now_add=True)

    class Meta:
        verbose_name = '每日祈福'
        verbose_name_plural = verbose_name
        unique_together = ('user', 'bless_date')
        ordering = ['-bless_date', '-created_at']