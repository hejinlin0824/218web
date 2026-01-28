from django.shortcuts import render
from news.models import Announcement
from community.models import Post
from django.db.models import Count
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

def index(request):
    """
    实验室门户主页
    """
    
    # 1. 获取实验室公告 (前 5 条)
    announcements = Announcement.objects.all().order_by('-is_top', '-created_at')[:5]
    
    # 2. 获取社区最新讨论 (前 6 条)
    recent_posts = Post.objects.select_related('author').annotate(
        comment_count=Count('comments')
    ).order_by('-created_at')[:6]

    # 3. 👇👇👇 新增：统计数据 👇👇👇
    total_users = User.objects.count() # 总人数
    total_posts = Post.objects.count() # 总帖子数
    
    # 计算在线人数 (简单逻辑：过去 30 分钟内登录过的用户算在线)
    # 注意：这依赖于 Django 默认的 last_login，它不是每次请求都更新，但也足够近似了
    time_threshold = timezone.now() - timedelta(minutes=30)
    online_users = User.objects.filter(last_login__gte=time_threshold).count()
    # 如果在线人数为0（比如重启后），至少显示1（你自己）
    if online_users == 0 and request.user.is_authenticated:
        online_users = 1

    context = {
        'announcements': announcements,
        'recent_posts': recent_posts,
        # 传递统计数据
        'stats': {
            'users': total_users,
            'posts': total_posts,
            'online': online_users
        }
    }
    
    return render(request, 'index.html', context)