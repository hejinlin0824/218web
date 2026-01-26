from django.shortcuts import render
from django.core.cache import cache
from .services import github_service

def index(request):
    # 1. 获取筛选参数 (设置默认值)
    language = request.GET.get('lang', 'python')
    period = request.GET.get('period', 'weekly') # daily, weekly, monthly
    page = int(request.GET.get('page', 1))
    
    # 2. 生成唯一的缓存 Key
    # 例如: trends_python_weekly_1
    cache_key = f"trends_{language}_{period}_{page}"
    
    # 3. 查缓存
    repos = cache.get(cache_key)
    
    if repos:
        print(f"✅ 命中缓存: {cache_key}")
    else:
        print(f"⚡ 缓存未命中，请求 API...")
        repos = github_service.fetch_trends(language, period, page)
        # 存缓存，5分钟有效
        if repos:
            cache.set(cache_key, repos, 300)
    
    # 4. 定义预设的语言列表 (用于下拉菜单)
    # 你可以在这里随意添加你喜欢的语言
    language_options = [
        'python', 'javascript', 'go', 'java', 'c++', 
        'rust', 'typescript', 'html', 'css', 'all'
    ]

    context = {
        'repos': repos,
        # 把当前的筛选状态传回前端，用于回显
        'current_lang': language,
        'current_period': period,
        'current_page': page,
        'language_options': language_options,
        # 计算下一页和上一页
        'next_page': page + 1,
        'prev_page': page - 1 if page > 1 else None,
    }
    return render(request, 'Github_trend/index.html', context)