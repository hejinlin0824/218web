from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('read/<int:pk>/', views.mark_read_and_redirect, name='read_and_redirect'),
    # 👇 新增 API 路由
    path('api/unread-count/', views.get_unread_count, name='api_unread_count'),
]