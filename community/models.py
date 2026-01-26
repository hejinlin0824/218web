from django.db import models
from django.conf import settings # 最佳实践：引用 User 模型要用 settings.AUTH_USER_MODEL

class Post(models.Model):
    """帖子模型"""
    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容') # 暂时用纯文本，后续我们在前端加 Markdown 渲染
    
    # 作者：级联删除，如果用户被删，他的帖子也全删
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='posts', 
        verbose_name='作者'
    )
    
    # 点赞：多对多关系。blank=True 表示允许没人点赞
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='liked_posts', 
        blank=True, 
        verbose_name='点赞用户'
    )
    
    views = models.PositiveIntegerField('浏览量', default=0)
    created_at = models.DateTimeField('发布时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '帖子'
        verbose_name_plural = verbose_name
        ordering = ['-created_at'] # 默认按时间倒序

    def __str__(self):
        return self.title

    # 辅助方法：统计点赞数
    def total_likes(self):
        return self.likes.count()


class Comment(models.Model):
    """评论模型"""
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        related_name='comments', # 以后用 post.comments.all() 就能拿到所有评论
        verbose_name='所属帖子'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name='评论者'
    )
    content = models.TextField('评论内容')
    created_at = models.DateTimeField('评论时间', auto_now_add=True)
    # 👇 新增：父评论 (用于盖楼回复)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    class Meta:
        verbose_name = '评论'
        verbose_name_plural = verbose_name
        ordering = ['created_at'] # 评论通常是按时间正序，楼层盖楼

    def __str__(self):
        return f'{self.author} 评论了 {self.post}'