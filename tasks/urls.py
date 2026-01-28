# tasks/urls.py

from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('create/', views.task_create, name='task_create'),
    path('my/', views.my_tasks, name='my_tasks'),
    path('<int:pk>/', views.task_detail, name='task_detail'),
    
    # 处理邀请动作: accept, reject, quit
    path('<int:pk>/handle/<str:action>/', views.handle_invite, name='handle_invite'),
    
    # 结算
    path('<int:pk>/settle/', views.settle_task, name='settle_task'),
    # 👇 新增这一行
    path('<int:pk>/delete/', views.task_delete, name='task_delete'),
]