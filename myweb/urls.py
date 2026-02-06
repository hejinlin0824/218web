"""
URL configuration for myweb project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include # 👈 记得导入 include
from django.conf import settings      # 👈 导入 settings
from django.conf.urls.static import static # 👈 导入 static
from core import views as core_views # 👈 导入我们刚写的 core 视图

urlpatterns = [
    path('', core_views.index, name='home'),
    path('admin/', admin.site.urls),
    # 包含 user_app 的路由
    path('users/', include('user_app.urls')), 
    # 👇 确保这一行指向你的 Github_trend
    path('trends/', include('Github_trend.urls')),
    path('community/', include('community.urls')), # 👈 新增
    path('notifications/', include('notifications.urls')),
    # 👇 新增：搜索路由
    path('search/', include('haystack.urls')),
    path('messages/', include('direct_messages.urls')), # 👈 新增
    path('lab/', include('core.urls')),      # 👈 新增这行，前缀设为 lab/
    # 👇👇👇 必须新增这一行 👇👇👇
    path('tasks/', include('tasks.urls', namespace='tasks')), 
    # 👆👆👆 注册 tasks 路由 👆👆👆
    # 👇👇👇 新增这一行 👇👇👇
    path('tools/npy/', include('npy_editor.urls', namespace='npy_editor')),
    # 👇 新增这一行
    path('vocab/', include('vocabulary.urls', namespace='vocabulary')),
    path('innovation/', include('innovation_agent.urls')), # 👈 新增
]

# 👇 这一段是让开发环境能访问上传的图片（头像）
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)