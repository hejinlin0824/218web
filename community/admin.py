from django.contrib import admin
from .models import Post, Comment

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    # 后台列表显示哪些字段
    list_display = ('title', 'author', 'views', 'created_at')
    # 侧边栏筛选功能
    list_filter = ('created_at', 'author')
    # 搜索框
    search_fields = ('title', 'content')
    # 自动只读字段（防止手动改时间）
    readonly_fields = ('created_at', 'updated_at', 'views')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created_at')
    list_filter = ('created_at',)