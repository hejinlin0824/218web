from django.urls import path
from . import views

app_name = 'direct_messages'

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('chat/<int:user_id>/', views.chat_room, name='chat_room'),
    # 👇 新增：删除对话路由
    # 👇👇👇 修改开始：区分两个删除功能的路径前缀 👇👇👇
    # 1. 删除整个会话（临时对话）
    path('conversation/delete/<int:user_id>/', views.delete_conversation, name='delete_conversation'),
    
    # 2. 清空聊天记录（保留好友关系）
    path('history/delete/<int:user_id>/', views.delete_chat, name='delete_chat'),
    # 👆👆👆 修改结束 👆👆👆
    # 👇👇👇 新增这一行 👇👇👇
    path('send/', views.send_message, name='send_message'),
    # 👇👇👇 新增这一行 API 路由 👇👇👇
    path('api/get-new/<int:sender_id>/', views.get_new_messages, name='get_new_messages'),
]