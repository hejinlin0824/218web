from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

# 继承 Django 原生的 UserAdmin，这样我们就不用自己写一堆界面代码
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    # 创建用户页的字段
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('自定义信息', {'fields': ('nickname', 'email', 'bio')}),
    )
    
    # 列表页显示的字段 (增加了 nickname, email_verified)
    list_display = ['username', 'email', 'nickname', 'email_verified', 'is_staff']
    
    # 编辑页的字段分类
    fieldsets = UserAdmin.fieldsets + (
        ('自定义信息', {'fields': ('nickname', 'bio', 'avatar', 'email_verified')}),
    )
    
    

# 注册到 Admin
admin.site.register(CustomUser, CustomUserAdmin)