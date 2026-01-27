from django.urls import path
from . import views

app_name = 'direct_messages'

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('chat/<int:user_id>/', views.chat_room, name='chat_room'),
    # 👇 新增：删除对话路由
    path('delete/<int:user_id>/', views.delete_conversation, name='delete_conversation'),
]