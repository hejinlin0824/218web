from django.urls import path
from django.contrib.auth import views as auth_views # 👈 引入内置视图
from . import views
from django.urls import reverse_lazy

app_name = 'user_app'

urlpatterns = [
    path('register/', views.register, name='register'),

    # 👇 新增：登录路由
    # template_name 参数告诉 Django 去哪里找我们的登录页面
    path('login/', auth_views.LoginView.as_view(template_name='user_app/login.html'), name='login'),

    # 👇 新增：登出路由
    # next_page 参数告诉 Django 登出后跳去哪里（这里设为登录页）
    path('logout/', auth_views.LogoutView.as_view(next_page='user_app:login'), name='logout'),
    # 👇 新增
    path('profile/', views.profile, name='profile'),

    # 👇 密码重置流程 (4步曲)
    
    # 1. 填写邮箱页面
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='user_app/password_reset.html',
             email_template_name='user_app/password_reset_email.html',
             success_url=reverse_lazy('user_app:password_reset_done')
         ),
         name='password_reset'),

    # 2. 邮件发送成功提示页
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='user_app/password_reset_done.html'
         ),
         name='password_reset_done'),

    # 3. 点击邮件链接后的重置密码页 (核心)
    # <uidb64> 和 <token> 是 Django 生成的安全令牌
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='user_app/password_reset_confirm.html',
             success_url=reverse_lazy('user_app:password_reset_complete')
         ),
         name='password_reset_confirm'),

    # 4. 修改完成提示页
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='user_app/password_reset_complete.html'
         ),
         name='password_reset_complete'),

    # 👇 新增：公开主页
    path('profile/<int:pk>/', views.public_profile, name='public_profile'),
    
    # 👇 新增：关注动作
    path('profile/<int:pk>/follow/', views.follow_user, name='follow_user'),
    # 👇 新增：查看关注列表
    path('profile/<int:pk>/following/', views.following_list, name='following_list'),
    
    # 👇 新增：查看粉丝列表
    path('profile/<int:pk>/followers/', views.followers_list, name='followers_list'),
]