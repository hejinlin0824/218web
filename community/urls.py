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
    # 编辑与删除
    path('post/<int:pk>/edit/', views.PostUpdateView.as_view(), name='post_edit'),
    path('post/<int:pk>/delete/', views.PostDeleteView.as_view(), name='post_delete'),
    
    # 收藏相关
    path('post/<int:pk>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'),
    path('my-collections/', views.my_collections, name='my_collections'),
    # 👇👇👇 新增收藏夹路由
    path('collections/', views.my_collections, name='my_collections'),
    path('collections/delete/<int:pk>/', views.delete_collection, name='delete_collection'),
    path('post/<int:pk>/collect/', views.collect_post, name='collect_post'),
    # 👇 新增 API 路由
    path('api/manage-collection/', views.manage_collection_posts, name='manage_collection_posts'),
    path('api/create-collection/', views.api_create_collection, name='api_create_collection'), # 👈 新增这行
]