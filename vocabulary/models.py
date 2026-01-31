from django.db import models
from django.conf import settings

class Word(models.Model):
    # 👇 核心修改：删掉了 unique=True
    word = models.CharField('单词', max_length=100, db_index=True) 
    
    phonetic = models.CharField('音标', max_length=100, blank=True, null=True)
    meaning = models.TextField('释义')
    level = models.CharField('等级', max_length=10, choices=[
        ('CET4', '四级'), 
        ('CET6', '六级'),
        ('TOEFL', '托福'),   # 新增
        ('IELTS', '雅思'),   # 新增
        ('KaoYan', '考研')   # 新增
    ], db_index=True)
    
    # 既然允许重复，建议把 bookId 和 wordRank 也存进去，方便区分来源
    book_id = models.CharField('词书ID', max_length=50, blank=True, null=True)
    word_rank = models.IntegerField('排名', default=0)

    example_en = models.TextField('英文例句', blank=True, null=True)
    example_cn = models.TextField('例句翻译', blank=True, null=True)

    def __str__(self):
        return f"{self.word} ({self.id})"

class UserWordProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vocab_progress')
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    
    status = models.IntegerField('状态', default=0) 
    mistake_count = models.PositiveIntegerField('错误次数', default=0)
    is_mistake = models.BooleanField('是否在错题本', default=False)
    last_reviewed = models.DateTimeField('上次复习', auto_now=True)

    class Meta:
        unique_together = ('user', 'word')
        ordering = ['-last_reviewed']