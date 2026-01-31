from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Count, Q 
from .models import Word, UserWordProgress
import json
import random

# ---------------------------------------------------
# 1. 页面视图
# ---------------------------------------------------

@login_required
def index(request):
    """单词本主页 - 统计所有等级进度"""
    user = request.user
    stats = {}
    
    # 🔥 修改点：扩充这里，支持所有 5 个等级
    ALL_LEVELS = ['CET4', 'CET6', 'KaoYan', 'TOEFL', 'IELTS']
    
    for level in ALL_LEVELS:
        total = Word.objects.filter(level=level).count()
        
        # 统计已学 (status > 0, 包含学习中和已掌握)
        learned_count = UserWordProgress.objects.filter(
            user=user, 
            word__level=level, 
            status__gt=0 
        ).count()
        
        # 统计已斩 (status = 2)
        mastered_count = UserWordProgress.objects.filter(
            user=user, 
            word__level=level, 
            status=2
        ).count()
        
        # 计算进度 (保留1位小数)
        if total > 0:
            progress = round((learned_count / total * 100), 1)
        else:
            progress = 0
        
        stats[level] = {
            'total': total,
            'learned': learned_count,
            'mastered': mastered_count,
            'progress': progress
        }
        
    return render(request, 'vocabulary/index.html', {'stats': stats})

@login_required
def practice(request):
    """拼写练习页面"""
    level = request.GET.get('level', 'CET4')
    return render(request, 'vocabulary/practice.html', {'level': level})

@login_required
def mistake_book(request):
    """错题本页面"""
    level = request.GET.get('level', 'CET4')
    mistakes = UserWordProgress.objects.filter(
        user=request.user, 
        is_mistake=True,
        word__level=level
    ).select_related('word').order_by('-mistake_count')
    
    return render(request, 'vocabulary/mistake_book.html', {
        'mistakes': mistakes, 
        'level': level
    })

# ---------------------------------------------------
# 2. API 接口
# ---------------------------------------------------

@login_required
def api_get_words(request):
    """API: 获取单词"""
    level = request.GET.get('level', 'CET4')
    
    try:
        count = int(request.GET.get('count', 10))
    except ValueError:
        count = 10
        
    mode = request.GET.get('mode', 'learn')
    
    user = request.user
    words_data = []
    
    if mode == 'review':
        # 复习错题
        progress_list = list(UserWordProgress.objects.filter(
            user=user, is_mistake=True, word__level=level
        ).select_related('word')[:50])
        
        random.shuffle(progress_list)
        selected = progress_list[:count]
        for p in selected:
            words_data.append(serialize_word(p.word))
            
    else:
        # 学习新词
        learned_ids = UserWordProgress.objects.filter(user=user).values_list('word_id', flat=True)
        new_words = Word.objects.filter(level=level).exclude(id__in=learned_ids).order_by('?')[:count]
        
        if new_words.exists():
            for w in new_words:
                words_data.append(serialize_word(w))
        else:
            # 没新词了，随机复习
            random_old = Word.objects.filter(level=level).order_by('?')[:count]
            for w in random_old:
                words_data.append(serialize_word(w))

    return JsonResponse({'status': 'ok', 'data': words_data})

def serialize_word(w):
    return {
        'id': w.id,
        'word': w.word,
        'phonetic': w.phonetic,
        'meaning': w.meaning,
        'example_en': w.example_en,
        'example_cn': w.example_cn,
        'audio_url': f"http://dict.youdao.com/dictvoice?audio={w.word}&type=0"
    }

@login_required
@require_POST
def api_submit_result(request):
    """提交结果"""
    data = json.loads(request.body)
    word = get_object_or_404(Word, pk=data.get('word_id'))
    p, created = UserWordProgress.objects.get_or_create(user=request.user, word=word)
    
    if data.get('is_correct'):
        if p.status == 0: 
            p.status = 1 
        request.user.earn_rewards(coins=1, growth=2)
    else:
        p.mistake_count += 1
        p.is_mistake = True
        p.status = 1 
    
    p.save()
    return JsonResponse({'status': 'ok'})

@login_required
@require_POST
def api_kill_word(request):
    """斩单词"""
    data = json.loads(request.body)
    p = get_object_or_404(UserWordProgress, user=request.user, word_id=data.get('word_id'))
    p.is_mistake = False
    p.status = 2
    p.save()
    return JsonResponse({'status': 'ok'})