from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.urls import reverse_lazy

app_name = 'user_app'

urlpatterns = [
    path('register/', views.register, name='register'),

    path('activation-sent/', views.activation_sent, name='activation_sent'),

    # 👇 修改：只需要接收一个 token 即可，不需要 uidb64 了
    path('activate/<str:token>/', views.activate, name='activate'),

    # 登录/登出 (保持不变)
    path('login/', auth_views.LoginView.as_view(template_name='user_app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='user_app:login'), name='logout'),
    
    path('profile/', views.profile, name='profile'),

    # 密码重置 (保持不变)
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='user_app/password_reset.html',
             email_template_name='user_app/password_reset_email.html',
             success_url=reverse_lazy('user_app:password_reset_done')
         ),
         name='password_reset'),

    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='user_app/password_reset_done.html'
         ),
         name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='user_app/password_reset_confirm.html',
             success_url=reverse_lazy('user_app:password_reset_complete')
         ),
         name='password_reset_confirm'),

    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='user_app/password_reset_complete.html'
         ),
         name='password_reset_complete'),

    # 社交功能 (保持不变)
    path('profile/<int:pk>/', views.public_profile, name='public_profile'),
    path('profile/<int:pk>/follow/', views.follow_user, name='follow_user'),
    path('profile/<int:pk>/following/', views.following_list, name='following_list'),
    path('profile/<int:pk>/followers/', views.followers_list, name='followers_list'),
    path('search/', views.search_users, name='search_users'),
    path('add-friend/<int:user_id>/', views.add_friend, name='add_friend'),
    path('requests/', views.friend_requests, name='friend_requests'),
    path('handle-request/<int:request_id>/<str:action>/', views.handle_friend_request, name='handle_request'),
    # 👇 新增这一行
    path('delete-friend/<int:user_id>/', views.delete_friend, name='delete_friend'),
]