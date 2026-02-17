from django.db import models
from django.conf import settings
from django.utils import timezone
import json

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

# 👇👇👇 【新增】艾宾浩斯每日批次模型 👇👇👇
class EbbinghausBatch(models.Model):
    """
    艾宾浩斯每日学习批次
    核心逻辑：每天、每本词书生成一个批次，包含固定数量(如60)的单词。
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ebbinghaus_batches')
    book_id = models.CharField('词书ID', max_length=50, db_index=True) # 例如 'CET4', 'TOEFL'
    study_date = models.DateField('学习日期', default=timezone.now, db_index=True)
    
    # 这一批次包含的单词
    words = models.ManyToManyField('Word', related_name='batches', verbose_name='包含单词')
    
    # 核心字段：首次完成时间 (基准时间)
    first_completed_at = models.DateTimeField('首次完成时间', null=True, blank=True)
    
    # 核心字段：复习状态矩阵 (JSON)
    # 存储结构:
    # {
    #    "phase_1": {"due": "iso_time", "done": bool, "notified": bool},
    #    "phase_2": ...
    # }
    review_status = models.JSONField('复习状态矩阵', default=dict, blank=True)
    
    # 防刷字段：总复习次数 (只要完成一次复习流程就+1，无论是否在艾宾浩斯节点上)
    total_review_count = models.PositiveIntegerField('累计复习次数', default=0)

    class Meta:
        verbose_name = '艾宾浩斯批次'
        verbose_name_plural = verbose_name
        # 联合唯一索引：确保同一用户、同一本书、同一天只有一个批次
        unique_together = ('user', 'book_id', 'study_date') 
        ordering = ['-study_date']

    def __str__(self):
        return f"{self.user} - {self.book_id} - {self.study_date}"