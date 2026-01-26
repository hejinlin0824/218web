from django.contrib import messages
from .forms import RegisterForm
# 引入通知模型
from notifications.models import Notification
from django.contrib.auth.decorators import login_required # 👈 引入装饰器
from .forms import RegisterForm, ProfileUpdateForm # 👈 引入新 Form

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.urls import reverse

from .forms import ProfileUpdateForm # 确保引入的是 forms.py 里写的类名

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # 暂时先设为激活状态，等下个阶段做完邮件验证再改为 False
            user.is_active = True 
            user.save()
            
            # 发送成功消息（Flash Message）
            messages.success(request, f'账号 {user.username} 注册成功！请登录。')
            return redirect('user_app:login') 
    else:
        form = RegisterForm()
    
    return render(request, 'user_app/register.html', {'form': form})


@login_required
def profile(request):
    """个人中心：查看数据 + 修改资料"""
    if request.method == 'POST':
        # ⚠️ 必须包含 request.FILES 才能上传图片
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '个人资料已更新！')
            return redirect('user_app:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    context = {
        'form': form,
        # 虽然模板里可以直接用 request.user，但有时候显式传 user 也是好习惯
        'user': request.user 
    }
    return render(request, 'user_app/profile.html', context)


User = get_user_model()
@login_required
def public_profile(request, pk):
    """公开的用户主页 (只读)"""
    target_user = get_object_or_404(User, pk=pk)
    
    # 获取该用户发布的所有帖子 (按时间倒序)
    user_posts = target_user.posts.all().order_by('-created_at')
    
    # 判断当前登录用户是否已关注他
    is_following = False
    if request.user.is_authenticated and request.user != target_user:
        if request.user.following.filter(id=target_user.id).exists():
            is_following = True

    context = {
        'target_user': target_user,
        'user_posts': user_posts,
        'is_following': is_following,
        'followers_count': target_user.followers.count(),
        'following_count': target_user.following.count(),
    }
    return render(request, 'user_app/public_profile.html', context)

@login_required
def follow_user(request, pk):
    """关注/取关 逻辑"""
    target_user = get_object_or_404(User, pk=pk)
    
    if target_user == request.user:
        return redirect('user_app:public_profile', pk=pk)

    if request.user.following.filter(id=target_user.id).exists():
        request.user.following.remove(target_user)
    else:
        request.user.following.add(target_user)
        
        # 🔔 发送通知
        Notification.objects.create(
            recipient=target_user,
            actor=request.user,
            verb='follow', # 👈 修正这里：从 'like' 改为 'follow'
            target_url=reverse('user_app:public_profile', args=[request.user.pk]),
            content='关注了你'
        )

    return HttpResponseRedirect(reverse('user_app:public_profile', args=[pk]))
@login_required
def following_list(request, pk):
    """查看某人关注的人列表"""
    target_user = get_object_or_404(User, pk=pk)
    # 获取该用户关注的所有人
    users = target_user.following.all()
    
    context = {
        'title': f"{target_user.nickname or target_user.username} 关注的人",
        'user_list': users
    }
    return render(request, 'user_app/follow_list.html', context)
@login_required
def followers_list(request, pk):
    """查看某人的粉丝列表"""
    target_user = get_object_or_404(User, pk=pk)
    # 获取关注该用户的所有人 (利用 related_name='followers')
    users = target_user.followers.all()
    
    context = {
        'title': f"{target_user.nickname or target_user.username} 的粉丝",
        'user_list': users
    }
    return render(request, 'user_app/follow_list.html', context)