from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
import os

def user_avatar_path(instance, filename):
    # 获取文件扩展名 (例如 .jpg)
    ext = filename.split('.')[-1]
    # 使用 UUID 生成唯一文件名 (例如 550e8400-e29b....jpg)
    filename = f'{uuid.uuid4()}.{ext}'
    # 返回路径: avatars/uuid.jpg
    return os.path.join('avatars', filename)

class CustomUser(AbstractUser):
    # 覆盖原生 email，改为唯一且必填
    email = models.EmailField(unique=True, verbose_name='邮箱地址')
    
    # 新增字段
    nickname = models.CharField(max_length=50, blank=True, verbose_name='昵称')
    bio = models.TextField(max_length=500, blank=True, verbose_name='个人简介')
    avatar = models.ImageField(upload_to=user_avatar_path, blank=True, null=True, verbose_name='头像')
    
    # 业务字段：记录是否验证了邮箱
    email_verified = models.BooleanField(default=False, verbose_name='邮箱已验证')
    # 👇 新增：关注系统
    # symmetrical=False 很关键：我关注你，你不一定关注我（微博模式，而不是微信好友模式）
    # related_name='followers': 反向查询名字，查询 user.followers.all() 就能知道谁关注了我
    following = models.ManyToManyField(
        'self', 
        symmetrical=False, 
        related_name='followers', 
        blank=True,
        verbose_name='关注的人'
    )
    class Meta:
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username