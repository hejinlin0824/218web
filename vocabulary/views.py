from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Word
import random

def index(request):
    """单词本主页"""
    return render(request, 'vocabulary/index.html')

@login_required
def practice(request):
    """拼写练习页面"""
    level = request.GET.get('level', 'CET4') # 默认练 CET4
    return render(request, 'vocabulary/practice.html', {'level': level})

def api_get_words(request):
    """
    API: 获取随机单词
    URL: /vocabulary/api/words/?level=CET4&count=10
    """
    level = request.GET.get('level', 'CET4')
    count = int(request.GET.get('count', 10))
    
    # 随机获取单词 (order_by('?') 在大数据量下性能一般，但 1万词没问题)
    words = Word.objects.filter(level=level).order_by('?')[:count]
    
    data = []
    for w in words:
        data.append({
            'id': w.id,
            'word': w.word,
            'phonetic': w.phonetic,
            'meaning': w.meaning,
            # 有道发音接口，type=1 是英音，type=0 是美音
            'audio_url': f"http://dict.youdao.com/dictvoice?audio={w.word}&type=0"
        })
        
    return JsonResponse({'status': 'ok', 'data': data})