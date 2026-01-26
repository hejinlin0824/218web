from django.db import models

class Announcement(models.Model):
    title = models.CharField('公告标题', max_length=200)
    content = models.TextField('公告内容', help_text="支持 HTML 格式")
    is_top = models.BooleanField('置顶', default=False)
    created_at = models.DateTimeField('发布时间', auto_now_add=True)

    class Meta:
        verbose_name = '实验室公告'
        verbose_name_plural = verbose_name
        ordering = ['-is_top', '-created_at'] # 先看置顶，再看时间倒序

    def __str__(self):
        return self.title