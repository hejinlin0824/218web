from django.shortcuts import render
from news.models import Announcement
from community.models import Post
from django.db.models import Count
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

# 👇 引入新模型
from .models import ResearchTopic, Publication

User = get_user_model()

def index(request):
    """
    实验室门户主页 (原有的 index 视图保持不变)
    """
    announcements = Announcement.objects.all().order_by('-is_top', '-created_at')[:5]
    
    recent_posts = Post.objects.select_related('author').annotate(
        comment_count=Count('comments')
    ).order_by('-created_at')[:6]

    total_users = User.objects.count()
    total_posts = Post.objects.count()
    
    time_threshold = timezone.now() - timedelta(minutes=30)
    online_users = User.objects.filter(last_login__gte=time_threshold).count()
    if online_users == 0 and request.user.is_authenticated:
        online_users = 1

    context = {
        'announcements': announcements,
        'recent_posts': recent_posts,
        'stats': {
            'users': total_users,
            'posts': total_posts,
            'online': online_users
        }
    }
    
    return render(request, 'index.html', context)

# 👇👇👇 新增：实验室介绍视图 👇👇👇
def lab_intro(request):
    """
    实验室介绍页
    """
    topics = ResearchTopic.objects.all()
    
    # 1. 获取导师列表 (status='faculty')，按等级(level)倒序排列
    faculties = User.objects.filter(status='faculty').order_by('-level', '-date_joined')
    
    # 2. 获取在读组员
    students = User.objects.filter(status='student').order_by('-level', '-date_joined')
    
    publications = Publication.objects.all()
    
    context = {
        'topics': topics,
        'faculties': faculties, # 👈 传递新的导师列表
        'students': students,
        'publications': publications,
    }
    return render(request, 'core/intro.html', context)