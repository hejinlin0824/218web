from news.models import Announcement
from community.models import Post
from django.db.models import Count
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from tasks.models import TaskParticipant # 👈 引入模型

# 👇 引入新模型
from .models import ResearchTopic, Publication

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import LabClass
from .forms import LabClassForm


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

    # 👇👇👇 新增：日程提醒逻辑 👇👇👇
    my_todos = []
    if request.user.is_authenticated:
        # 获取用户状态为 'accepted' 且任务本身未结束 (open 或 in_progress) 的记录
        my_todos = TaskParticipant.objects.filter(
            user=request.user,
            status='accepted',
            task__status__in=['open', 'in_progress']
        ).select_related('task', 'task__creator').order_by('task__deadline')
    # 👆👆👆 新增结束 👆👆👆


    context = {
        'announcements': announcements,
        'recent_posts': recent_posts,
        'stats': {
            'users': total_users,
            'posts': total_posts,
            'online': online_users
        },
        'my_todos': my_todos, # 👈 把这个传给模板
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

@login_required
def my_classes(request):
    """导师：我的班级列表"""
    # 权限检查
    if request.user.status != 'faculty' and not request.user.is_staff:
        messages.error(request, "权限不足：仅导师可管理班级")
        return redirect('home')

    classes = LabClass.objects.filter(mentor=request.user)
    return render(request, 'core/class_list.html', {'classes': classes})

@login_required
def class_create(request):
    """导师：创建班级"""
    if request.user.status != 'faculty':
        return redirect('home')

    if request.method == 'POST':
        form = LabClassForm(request.POST)
        if form.is_valid():
            lab_class = form.save(commit=False)
            lab_class.mentor = request.user
            lab_class.save()
            # 保存多对多关系 (学生)
            form.save_m2m() 
            messages.success(request, f"班级 {lab_class.name} 创建成功！")
            return redirect('core:my_classes')
    else:
        form = LabClassForm()

    return render(request, 'core/class_form.html', {'form': form, 'title': '创建班级'})

@login_required
def class_edit(request, pk):
    """导师：编辑班级/管理成员"""
    lab_class = get_object_or_404(LabClass, pk=pk, mentor=request.user)

    if request.method == 'POST':
        form = LabClassForm(request.POST, instance=lab_class)
        if form.is_valid():
            form.save()
            messages.success(request, "班级信息已更新（成员变动已自动生效）")
            return redirect('core:my_classes')
    else:
        form = LabClassForm(instance=lab_class)

    return render(request, 'core/class_form.html', {'form': form, 'title': f'管理班级: {lab_class.name}'})

@login_required
def class_delete(request, pk):
    """导师：解散班级"""
    lab_class = get_object_or_404(LabClass, pk=pk, mentor=request.user)
    lab_class.delete()
    messages.success(request, "班级已解散")
    return redirect('core:my_classes')

# ==========================================
# 🎓 导师班级管理视图
# ==========================================

@login_required
def class_management(request):
    """
    班级管理列表页 (导师控制台)
    """
    # 1. 权限拦截：非导师滚回主页
    if request.user.status != 'faculty':
        messages.error(request, "你无权操作：该功能仅限导师使用。")
        return redirect('home')

    # 2. 获取该导师名下的所有班级
    my_classes = LabClass.objects.filter(mentor=request.user)
    
    return render(request, 'core/class_list.html', {
        'classes': my_classes
    })

@login_required
def class_create_or_edit(request, pk=None):
    """
    创建或编辑班级 (二合一视图)
    """
    # 1. 权限拦截
    if request.user.status != 'faculty':
        messages.error(request, "你无权操作。")
        return redirect('home')

    # 2. 判断是新建还是编辑
    if pk:
        # 编辑模式：必须确保这个班级是当前用户创建的
        instance = get_object_or_404(LabClass, pk=pk, mentor=request.user)
        title = f"编辑班级: {instance.name}"
    else:
        # 新建模式
        instance = None
        title = "创建新班级"

    if request.method == 'POST':
        form = LabClassForm(request.POST, instance=instance)
        if form.is_valid():
            lab_class = form.save(commit=False)
            lab_class.mentor = request.user # 强制绑定当前导师
            lab_class.save()
            
            # 保存多对多字段(学生列表)
            form.save_m2m()
            
            messages.success(request, f"班级“{lab_class.name}”保存成功！成员名单已更新。")
            return redirect('core:class_management')
    else:
        form = LabClassForm(instance=instance)

    return render(request, 'core/class_form.html', {
        'form': form,
        'title': title
    })

@login_required
def class_delete(request, pk):
    """
    解散班级
    """
    # 1. 权限拦截
    if request.user.status != 'faculty':
        messages.error(request, "你无权操作。")
        return redirect('home')

    # 2. 获取对象并校验权限
    lab_class = get_object_or_404(LabClass, pk=pk, mentor=request.user)
    
    # 3. 执行删除
    name = lab_class.name
    lab_class.delete()
    
    messages.success(request, f"班级“{name}”已成功解散。")
    return redirect('core:class_management')