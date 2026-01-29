from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('intro/', views.lab_intro, name='intro'),
    
    # 👇👇👇 新增班级管理路由 👇👇👇
    path('console/classes/', views.class_management, name='class_management'),
    path('console/classes/create/', views.class_create_or_edit, name='class_create'),
    path('console/classes/edit/<int:pk>/', views.class_create_or_edit, name='class_edit'),
    path('console/classes/delete/<int:pk>/', views.class_delete, name='class_delete'),
]