from django.shortcuts import render
from news.models import Announcement
from community.models import Post
from django.db.models import Count

def index(request):
    """
    实验室门户主页
    聚合展示：
    1. 实验室公告 (News)
    2. 社区最新讨论 (Community)
    """
    
    # 1. 获取实验室公告 (按置顶优先，然后按时间倒序，取前 5 条)
    announcements = Announcement.objects.all().order_by('-is_top', '-created_at')[:5]
    
    # 2. 获取社区最新讨论 (按时间倒序，取前 6 条)
    # 使用 select_related 预加载作者信息，防止 N+1 查询问题
    recent_posts = Post.objects.select_related('author').annotate(
        comment_count=Count('comments')
    ).order_by('-created_at')[:6]

    context = {
        'announcements': announcements,
        'recent_posts': recent_posts,
    }
    
    return render(request, 'index.html', context)