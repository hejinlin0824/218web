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
    # 👇👇👇 新增：可见性设置
    VISIBILITY_CHOICES = (
        ('public', '🌍 公开'),
        ('private', '🔒 仅自己可见'),
    )
    visibility = models.CharField('可见性', max_length=10, choices=VISIBILITY_CHOICES, default='public')
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

# 👇👇👇 新增：收藏夹模型
class Collection(models.Model):
    """用户创建的收藏夹"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='collections', verbose_name='创建者')
    name = models.CharField('收藏夹名称', max_length=50)
    description = models.TextField('描述', blank=True)
    posts = models.ManyToManyField(Post, related_name='collected_in', blank=True, verbose_name='收藏的帖子')
    is_public = models.BooleanField('是否公开收藏夹', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '收藏夹'
        verbose_name_plural = verbose_name
        unique_together = ('user', 'name') # 同一个用户不能有两个同名收藏夹

    def __str__(self):
        return f"{self.user.username} 的收藏夹: {self.name}"