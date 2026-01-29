from django.db import models
from django.conf import settings


User = settings.AUTH_USER_MODEL
# 1. 研究方向模型
class ResearchTopic(models.Model):
    title = models.CharField('方向名称', max_length=100)
    description = models.TextField('方向简介')
    icon = models.CharField('图标Emoji', max_length=10, default='🔬', help_text="例如: 🔬, 💻, 🧬")
    
    class Meta:
        verbose_name = '研究方向'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return self.title

# 3. 论文成果模型
class Publication(models.Model):
    title = models.CharField('论文标题', max_length=300)
    authors = models.CharField('作者列表', max_length=200, help_text="例如: Zhang San, Li Si, et al.")
    venue = models.CharField('发表刊物/会议', max_length=100, help_text="例如: CVPR 2025")
    year = models.IntegerField('发表年份', default=2026)
    link = models.URLField('论文链接', blank=True, help_text="跳转到 PDF 或 Arxiv")
    is_highlight = models.BooleanField('设为高亮/代表作', default=False)
    
    class Meta:
        verbose_name = '论文成果'
        verbose_name_plural = verbose_name
        ordering = ['-year', '-id'] # 按年份倒序排列
        
    def __str__(self):
        return f"[{self.year}] {self.title[:50]}..."

class LabClass(models.Model):
    """
    行政班级模型
    """
    name = models.CharField('班级名称', max_length=50, unique=True)
    mentor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='mentored_classes', 
        verbose_name='负责导师',
        limit_choices_to={'status': 'faculty'} # 仅导师可选
    )
    description = models.TextField('班级简介', blank=True)
    
    # 学生列表 (多对多)
    students = models.ManyToManyField(
        User, 
        related_name='lab_classes', 
        verbose_name='班级成员',
        blank=True,
        limit_choices_to={'status': 'student'} # 仅在读生可选
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '行政班级'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} (导师: {self.mentor.nickname or self.mentor.username})"