from django.contrib import admin
from .models import Post, Comment, Tag

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'color')
    # 自动根据 name 生成 slug，方便操作
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'views', 'created_at')
    list_filter = ('created_at', 'author', 'tags') # 👈 侧边栏增加标签筛选
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'updated_at', 'views')
    # 在后台编辑帖子时，使用水平过滤器选择标签，体验更好
    filter_horizontal = ('tags',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created_at')
    list_filter = ('created_at',)