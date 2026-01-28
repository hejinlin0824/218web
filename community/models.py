from django.db import models
from django.conf import settings

class Tag(models.Model):
    """标签模型 (仅管理员可操作)"""
    name = models.CharField('标签名', max_length=30, unique=True)
    # slug 用于 URL 过滤，比如 /community/?tag=python
    slug = models.SlugField('URL标识', max_length=30, unique=True, allow_unicode=True) 
    color = models.CharField('颜色代码', max_length=7, default='#6c757d', help_text="十六进制颜色，如 #FF0000")

    class Meta:
        verbose_name = '标签'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

class Post(models.Model):
    """帖子模型"""
    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容')
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='posts', 
        verbose_name='作者'
    )
    
    # 标签关联
    tags = models.ManyToManyField(
        Tag, 
        verbose_name='标签', 
        blank=True, # 允许不选标签
        related_name='posts'
    )
    
    # 点赞关联
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='liked_posts', 
        blank=True, 
        verbose_name='点赞用户'
    )
    
    # 成长值系统标记：是否已发放首赞奖励 (防止刷分)
    is_first_like_rewarded = models.BooleanField('已发放首赞奖励', default=False)

    views = models.PositiveIntegerField('浏览量', default=0)
    created_at = models.DateTimeField('发布时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '帖子'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def total_likes(self):
        return self.likes.count()

class Comment(models.Model):
    """评论模型"""
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        related_name='comments', 
        verbose_name='所属帖子'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name='评论者'
    )
    content = models.TextField('评论内容')
    created_at = models.DateTimeField('评论时间', auto_now_add=True)
    
    # 嵌套评论 (自关联)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    
    # 评论点赞关联 (新增)
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='liked_comments', 
        blank=True,
        verbose_name='点赞用户'
    )

    class Meta:
        verbose_name = '评论'
        verbose_name_plural = verbose_name
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author} 评论了 {self.post}'