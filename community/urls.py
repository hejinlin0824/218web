from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    # 社区首页 (列表)
    path('', views.PostListView.as_view(), name='post_list'),
    
    # 发布新帖
    path('create/', views.PostCreateView.as_view(), name='post_create'),
    
    # 帖子详情页
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    
    # 帖子点赞 (Toggle)
    path('post/<int:pk>/like/', views.like_post, name='like_post'),
    
    # 评论点赞 (Toggle) - 新增
    path('comment/<int:pk>/like/', views.like_comment, name='like_comment'),
    
    # 图片上传 (Vditor编辑器用)
    path('upload/image/', views.upload_image, name='upload_image'),
]