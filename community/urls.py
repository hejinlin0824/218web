from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    # 社区首页 (列表)
    path('', views.PostListView.as_view(), name='post_list'),
    
    # 发布新帖
    path('create/', views.PostCreateView.as_view(), name='post_create'),
    # 👇 新增：详情页路由，<int:pk> 代表接收整数类型的 ID
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/<int:pk>/like/', views.like_post, name='like_post'),
    path('upload/image/', views.upload_image, name='upload_image'), # 👈 新增
]