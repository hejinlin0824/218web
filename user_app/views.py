from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model, login
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
import threading
from django.db.models import Q
import uuid # 👈 用于生成随机Token
from django.core.cache import cache # 👈 引入缓存
from django.contrib.auth.hashers import make_password # 👈 用于手动加密密码
from django.core.mail import send_mail # 👈 引入发邮件模块
from django.conf import settings         # 👈 引入设置

from django.contrib.sites.shortcuts import get_current_site
from .forms import RegisterForm, ProfileUpdateForm
from notifications.models import Notification
# 👇👇👇 必须补全这一行导入 👇👇👇
from .models import CustomUser, Friendship 
# 👆👆👆 之前可能漏了 CustomUser 👆👆👆
from .models import CustomUser, Friendship

User = get_user_model()

# ==========================================
# 📧 邮件发送辅助函数
# ==========================================

def send_email_thread(subject, message, recipient_list):
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
    except Exception as e:
        print(f"邮件发送失败: {e}")

def send_activation_email(request, email, token, username):
    """
    发送账户激活邮件
    注意：这里不再接收 user 对象，而是直接接收 email 和 username
    """
    current_site = get_current_site(request)
    email_subject = '【重要】请激活您的 Web 218 实验室账号'
    
    # 构建新的激活链接 (只带 token)
    activation_link = reverse('user_app:activate', kwargs={'token': token})
    activation_url = f"http://{current_site.domain}{activation_link}"
    
    email_message = f"""
    您好 {username}，

    感谢注册 Web 218 实验室！
    
    您的账号尚未创建，请点击下方链接完成最后一步验证并写入数据库：
    {activation_url}

    (链接 24 小时内有效)
    """
    
    threading.Thread(
        target=send_email_thread,
        args=(email_subject, email_message, [email])
    ).start()

def send_welcome_email(user):
    """发送欢迎邮件 (写入数据库成功后触发)"""
    subject = '🎉 注册成功！欢迎加入 Web 218 实验室'
    message = f"""
    你好，{user.username}！

    欢迎加入！您的账号已正式创建。
    
    下一步：请完善您的个人资料，上传头像，让大家认识你。

    祝好，
    Web 218 团队
    """
    threading.Thread(
        target=send_email_thread,
        args=(subject, message, [user.email])
    ).start()

# ==========================================
# 👤 视图函数
# ==========================================

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # 1. 获取清洗后的数据
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            raw_password = form.cleaned_data['password1'] 
            nickname = form.cleaned_data.get('nickname', '')
            # 👇 获取新加的字段
            status = form.cleaned_data.get('status')
            student_id = form.cleaned_data.get('student_id')

            # 2. 再次检查数据库中是否已存在
            if User.objects.filter(email=email).exists():
                messages.error(request, '该邮箱已被注册。')
                return render(request, 'user_app/register.html', {'form': form})
            
            if User.objects.filter(username=username).exists():
                messages.error(request, '该用户名已被占用。')
                return render(request, 'user_app/register.html', {'form': form})

            # 3. 生成随机 Token
            token = uuid.uuid4().hex

            # 4. 打包用户数据
            user_data = {
                'username': username,
                'email': email,
                'password': make_password(raw_password),
                'nickname': nickname,
                # 👇 将身份和学号打包进缓存
                'status': status,
                'student_id': student_id,
                'is_active': True,
                'email_verified': True
            }

            # 5. 存入缓存
            cache.set(f'reg_token_{token}', user_data, 86400)

            # 6. 发送验证邮件
            send_activation_email(request, email, token, username)
            
            return redirect('user_app:activation_sent')
    else:
        form = RegisterForm()
    
    return render(request, 'user_app/register.html', {'form': form})

def activation_sent(request):
    """提示去收邮件"""
    return render(request, 'user_app/activation_sent.html')

def activate(request, token):
    """
    处理激活链接
    逻辑：从缓存读取数据 -> 写入数据库 -> 自动登录
    """
    # 1. 从缓存获取数据
    cache_key = f'reg_token_{token}'
    user_data = cache.get(cache_key)

    if user_data:
        # 再次检查用户名是否在等待期间被抢注 (虽然概率极低)
        if User.objects.filter(username=user_data['username']).exists():
            messages.error(request, '注册链接已失效，用户名已被占用，请重新注册。')
            return redirect('user_app:register')

        # 2. 写入数据库
        user = User.objects.create(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data['password'],
            nickname=user_data.get('nickname', ''),
            # 👇 写入状态和学号
            status=user_data.get('status', 'newbie'),
            student_id=user_data.get('student_id'),
            is_active=True,
            email_verified=True
        )
        
        # 3. 删除缓存，防止二次点击报错
        cache.delete(cache_key)

        # 4. 自动登录
        login(request, user, backend='user_app.authentication.EmailBackend')
        
        # 5. 发送欢迎邮件
        send_welcome_email(user)
        
        messages.success(request, '账号验证成功！欢迎加入。')
        return redirect('user_app:profile')
    else:
        # 缓存中找不到 (过期或无效)
        return render(request, 'user_app/activation_invalid.html')

@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '个人资料已更新！')
            return redirect('user_app:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    context = {
        'form': form,
        'user': request.user 
    }
    return render(request, 'user_app/profile.html', context)

@login_required
def public_profile(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    user_posts = target_user.posts.all().order_by('-created_at')
    
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
    target_user = get_object_or_404(User, pk=pk)
    
    if target_user == request.user:
        return redirect('user_app:public_profile', pk=pk)

    if request.user.following.filter(id=target_user.id).exists():
        request.user.following.remove(target_user)
    else:
        request.user.following.add(target_user)
        Notification.objects.create(
            recipient=target_user,
            actor=request.user,
            verb='follow', 
            target_url=reverse('user_app:public_profile', args=[request.user.pk]),
            content='关注了你'
        )

    return HttpResponseRedirect(reverse('user_app:public_profile', args=[pk]))

@login_required
def following_list(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    users = target_user.following.all()
    context = {'title': f"{target_user.nickname or target_user.username} 关注的人", 'user_list': users}
    return render(request, 'user_app/follow_list.html', context)

@login_required
def followers_list(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    users = target_user.followers.all()
    context = {'title': f"{target_user.nickname or target_user.username} 的粉丝", 'user_list': users}
    return render(request, 'user_app/follow_list.html', context)


# 1. 搜索用户视图
@login_required
def search_users(request):
    # 👇👇👇 新增：权限拦截逻辑 👇👇👇
    # 定义允许搜索的身份列表：在读、毕业、导师
    allowed_status = ['student', 'alumni', 'faculty']
    
    # 如果用户身份不在允许列表中 (即 newbie 新生)
    if request.user.status not in allowed_status:
        messages.warning(request, "录取后可以使用")
        # 拦截后跳转回个人中心或大厅
        return redirect('user_app:profile') 
    # 👆👆👆 新增结束 👆👆👆

    query = request.GET.get('q', '')
    users = []
    
    if query:
        # 搜索逻辑：排除自己，搜索用户名、昵称或学号
        # 注意：这里我们允许搜到任何人，但只有特定身份的人能发起搜索
        users = CustomUser.objects.filter(
            Q(username__icontains=query) | 
            Q(nickname__icontains=query) |
            Q(student_id__icontains=query)
        ).exclude(pk=request.user.pk)

    return render(request, 'user_app/search_users.html', {'users': users, 'query': query})

# 2. 发送好友请求
# 2. 发送好友请求
@login_required
def add_friend(request, user_id):
    target_user = get_object_or_404(CustomUser, pk=user_id)
    
    if request.user.status == 'newbie':
        messages.error(request, "权限不足。")
        return redirect('user_app:profile')

    existing_relation = Friendship.objects.filter(
        Q(from_user=request.user, to_user=target_user) |
        Q(from_user=target_user, to_user=request.user)
    ).first()

    if existing_relation:
        if existing_relation.status == 'accepted':
            messages.info(request, "你们已经是好友了。")
        elif existing_relation.status == 'pending':
            messages.info(request, "请求已发送，请等待对方通过。")
    else:
        Friendship.objects.create(from_user=request.user, to_user=target_user)
        messages.success(request, f"已向 {target_user.nickname or target_user.username} 发送好友请求。")
        
        # 👇👇👇 修改通知逻辑：使用 'friend_request' 👇👇👇
        Notification.objects.create(
            recipient=target_user,
            actor=request.user,
            verb='friend_request', # 使用新类型
            target_url=reverse('user_app:friend_requests'),
            content='请求添加你为好友'
        )
        
        # 👇👇👇 2. 发送系统邮件 👇👇👇
        if target_user.email:
            try:
                # 生成完整的审批链接 (例如: http://yourdomain.com/users/requests/)
                approval_url = request.build_absolute_uri(reverse('user_app:friend_requests'))
                
                subject = f'[Web 218 实验室-好友申请] {request.user.nickname or request.user.username} 请求添加您为好友'
                
                message = f"""
                你好 {target_user.nickname or target_user.username}:

                {request.user.nickname or request.user.username} (身份: {request.user.get_status_display()}) 请求添加你为好友。

                点击下方链接前往处理请求：
                {approval_url}


                -------------------------
                Web 218 DSSG Lab Center
                218 大王发
                """
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [target_user.email],
                    fail_silently=True, # 如果发不出去不报错，防止影响页面跳转
                )
            except Exception as e:
                print(f"邮件发送失败: {e}")
        # 👆👆👆 邮件发送结束 👆👆👆

    return redirect('user_app:search_users')

# 3. 查看好友请求列表
@login_required
def friend_requests(request):
    # 我收到的所有 pending 请求
    requests = Friendship.objects.filter(to_user=request.user, status='pending')
    return render(request, 'user_app/friend_requests.html', {'requests': requests})

# 4. 处理请求 (接受/拒绝)
# 4. 处理请求
@login_required
def handle_friend_request(request, request_id, action):
    friendship = get_object_or_404(Friendship, pk=request_id, to_user=request.user)
    
    if action == 'accept':
        friendship.status = 'accepted'
        friendship.save()
        
        # 👇👇👇 新增：通过好友后，自动互相关注 👇👇👇
        # 1. 我关注他
        request.user.following.add(friendship.from_user)
        # 2. 他关注我
        friendship.from_user.following.add(request.user)
        # 👆👆👆 新增结束 👆👆👆
        
        messages.success(request, f"已添加 {friendship.from_user.nickname} 为好友，并已互相关注！")
        
        # 发送通知
        Notification.objects.create(
            recipient=friendship.from_user,
            actor=request.user,
            verb='friend_accept',
            target_url=reverse('user_app:public_profile', args=[request.user.pk]),
            content='通过了你的好友请求'
        )
        
    elif action == 'reject':
        friendship.delete()
        messages.info(request, "已拒绝该请求。")
        
        Notification.objects.create(
            recipient=friendship.from_user,
            actor=request.user,
            verb='friend_reject',
            target_url='#',
            content='拒绝了你的好友请求'
        )
        
    return redirect('user_app:friend_requests')

    # 2. 新增：删除好友视图
@login_required
def delete_friend(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    
    # 查找好友关系 (无论是谁发起的)
    Friendship.objects.filter(
        Q(from_user=request.user, to_user=target_user) | 
        Q(from_user=target_user, to_user=request.user)
    ).delete()
    
    # 👇👇👇 可选：删除好友后，是否自动取关？ 👇👇👇
    # 通常逻辑是：删好友 = 绝交 = 互相取关
    request.user.following.remove(target_user)
    target_user.following.remove(request.user)
    
    messages.success(request, f"已解除与 {target_user.nickname or target_user.username} 的好友关系。")
    
    # 哪里来的回哪里，或者回主页
    return redirect('user_app:public_profile', pk=user_id)