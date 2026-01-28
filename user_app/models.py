from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
import os
from django.conf import settings

def user_avatar_path(instance, filename):
    # 使用 UUID 生成唯一文件名 (例如 550e8400-e29b....jpg)
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4()}.{ext}'
    return os.path.join('avatars', filename)

# 学号白名单模型 (由管理员导入)
class StudentWhitelist(models.Model):
    student_id = models.CharField('学号', max_length=20, unique=True)
    name = models.CharField('真实姓名', max_length=50, blank=True, help_text="选填，用于管理员备注")
    
    class Meta:
        verbose_name = '学号白名单'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.student_id} ({self.name})"

# 自定义用户模型
class CustomUser(AbstractUser):
    # 定义身份状态常量
    STATUS_CHOICES = (
        ('newbie', '🌱 新生'),
        ('student', '🎓 在读'),
        ('alumni', '🏆 毕业'),
        ('faculty', '👨‍🏫 导师'), # 👈 新增这一行
    )

    # 基础信息
    email = models.EmailField(unique=True, verbose_name='邮箱地址')
    nickname = models.CharField(max_length=50, blank=True, verbose_name='昵称')
    bio = models.TextField(max_length=500, blank=True, verbose_name='个人简介')
    avatar = models.ImageField(upload_to=user_avatar_path, blank=True, null=True, verbose_name='头像')
    email_verified = models.BooleanField(default=False, verbose_name='邮箱已验证')
    # # 2. 新增：详细介绍 (Markdown)
    # detailed_intro = models.TextField('详细介绍 (Markdown)', blank=True, help_text="仅导师身份生效，支持 Markdown 语法")
    # 👇 修改这个字段的 help_text
    detailed_intro = models.TextField('详细介绍 (Markdown)', blank=True, help_text="支持 Markdown 语法。用于在实验室介绍页展示个人简历、研究兴趣等。")
    
    # 身份认证信息
    status = models.CharField('当前身份', max_length=10, choices=STATUS_CHOICES, default='newbie')
    student_id = models.CharField('学号', max_length=20, blank=True, null=True, unique=True, help_text="认证通过后绑定")

    # 社交关系
    following = models.ManyToManyField(
        'self', 
        symmetrical=False, 
        related_name='followers', 
        blank=True,
        verbose_name='关注的人'
    )

    # 成长体系 (Gamification)
    coins = models.PositiveIntegerField('硬币', default=0)
    growth = models.PositiveIntegerField('成长值', default=0)
    level = models.PositiveIntegerField('等级', default=1)

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username

    def earn_rewards(self, coins=0, growth=0):
        """
        增加硬币和成长值，并自动计算升级
        升级公式: 线性升级，每100成长值升1级
        """
        self.coins += coins
        self.growth += growth
        
        # 计算新等级 (100分一级: 0-99=Lv1, 100-199=Lv2)
        new_level = 1 + (self.growth // 100)
        
        if new_level > self.level:
            self.level = new_level
            # 这里可以扩展升级通知逻辑
        
        self.save()
    # 👇👇👇 新增这个属性 👇👇👇
    @property
    def level_progress(self):
        """
        计算当前等级的进度百分比 (0-100)
        假设每 100 成长值升 1 级
        """
        return self.growth % 100

    # 👇 新增 helper 方法：获取我的所有好友 (已同意的)
    def get_friends(self):
        # 查询 Friendship 表，状态为 accepted，且我是 from_user 或 to_user
        friendships = Friendship.objects.filter(
            models.Q(from_user=self) | models.Q(to_user=self),
            status='accepted'
        )
        friends = []
        for f in friendships:
            if f.from_user == self:
                friends.append(f.to_user)
            else:
                friends.append(f.from_user)
        return friends

    def is_friend_with(self, other_user):
        return Friendship.objects.filter(
            models.Q(from_user=self, to_user=other_user) | 
            models.Q(from_user=other_user, to_user=self),
            status='accepted'
        ).exists()

# 👇👇👇 新增：好友关系模型 👇👇👇
class Friendship(models.Model):
    STATUS_CHOICES = (
        ('pending', '等待验证'),
        ('accepted', '已添加'),
        ('rejected', '已拒绝'),
    )
    
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='friendship_creator', on_delete=models.CASCADE)
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='friendship_receiver', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('from_user', 'to_user') # 防止重复请求
        verbose_name = '好友关系'
        verbose_name_plural = verbose_name
        
    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({self.status})"