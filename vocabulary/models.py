from django.db import models
from django.conf import settings

class Word(models.Model):
    """
    单词库
    """
    LEVEL_CHOICES = (
        ('CET4', '英语四级'),
        ('CET6', '英语六级'),
    )

    # 核心字段
    word = models.CharField('单词', max_length=100, db_index=True, unique=True)
    phonetic = models.CharField('音标', max_length=100, blank=True, null=True)
    meaning = models.TextField('释义') # 也就是 trans，中文意思
    level = models.CharField('等级', max_length=10, choices=LEVEL_CHOICES, db_index=True)
    
    def __str__(self):
        return self.word

class UserWordProgress(models.Model):
    """
    用户背诵进度
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vocab_progress')
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    
    # 熟练度：0=没背过，1=认识，2=已掌握
    proficiency = models.IntegerField('熟练度', default=0)
    
    # 错题统计
    mistake_count = models.PositiveIntegerField('拼写错误次数', default=0)
    last_reviewed = models.DateTimeField('上次复习时间', auto_now=True)

    class Meta:
        unique_together = ('user', 'word') # 一个人对一个单词只有一条记录

    def __str__(self):
        return f"{self.user.username} - {self.word.word}"