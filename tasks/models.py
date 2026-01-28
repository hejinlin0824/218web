# tasks/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class Task(models.Model):
    STATUS_CHOICES = (
        ('open', '🔥 招募中'),        # 刚发布，等待人接受
        ('in_progress', '🚀 进行中'), # 有人接受了，正在做
        ('closed', '🏁 已结束'),      # 任务完成，已结算
    )
    # 👇👇👇 新增：任务类型 👇👇👇
    TYPE_CHOICES = (
        ('bounty', '💰 悬赏任务'),
        ('faculty', '🚨 导师指令'), # 优先级 Max
    )

    title = models.CharField('任务标题', max_length=100)
    content = models.TextField('任务详情 (支持Markdown)')
    
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tasks', verbose_name='发起人')
    bounty = models.PositiveIntegerField('悬赏金币', default=0, help_text='任务结束时将支付给贡献最大者')
    # 新增字段
    task_type = models.CharField('任务类型', max_length=10, choices=TYPE_CHOICES, default='bounty')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='open')
    deadline = models.DateTimeField('截止时间')
    
    # 获胜者 (任务结束时由发起人指定)
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_tasks', verbose_name='最终获胜者')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '悬赏任务'
        verbose_name_plural = verbose_name
        # 👇 修改排序：导师任务优先，然后按时间倒序
        ordering = ['-task_type', '-created_at']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title}"

    @property
    def is_overdue(self):
        """是否已过期"""
        return self.status != 'closed' and timezone.now() > self.deadline


class TaskParticipant(models.Model):
    """任务参与记录 (邀请/接受/拒绝/放弃)"""
    STATUS_CHOICES = (
        ('invited', '📩 待回应'),
        ('accepted', '✅ 已接受'), # 只有这个状态才会显示在日程里
        ('rejected', '🚫 已拒绝'),
        ('quit', '🏳️ 中途放弃'),
    )

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='participants', verbose_name='关联任务')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_participations', verbose_name='参与者')
    
    status = models.CharField('参与状态', max_length=20, choices=STATUS_CHOICES, default='invited')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '参与记录'
        verbose_name_plural = verbose_name
        unique_together = ('task', 'user') # 一个人对一个任务只能有一条记录

    def __str__(self):
        return f"{self.user} - {self.get_status_display()}"