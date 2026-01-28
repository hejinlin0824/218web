from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, StudentWhitelist

# 注册学号白名单
@admin.register(StudentWhitelist)
class StudentWhitelistAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'name')
    search_fields = ('student_id', 'name')

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    add_fieldsets = UserAdmin.add_fieldsets + (
        # 将成长值相关字段添加到“新增用户”页面（如果需要的话）
        ('自定义信息', {'fields': ('nickname', 'email', 'bio', 'status', 'student_id')}),
    )
    
    # 列表页显示的字段
    list_display = ['username', 'email', 'nickname', 'level', 'growth', 'coins', 'status', 'student_id']
    
    # 编辑页的字段分类
    fieldsets = UserAdmin.fieldsets + (
        ('自定义信息', {'fields': ('nickname', 'bio', 'avatar', 'email_verified', 'status', 'student_id')}),
        ('成长体系 (Gamification)', {'fields': ('level', 'growth', 'coins')}),
    )
    
    # 设置 level 为只读，强制管理员通过修改 growth 来调整等级 (可选，或者允许修改但会被 save_model 覆盖)
    readonly_fields = ('level',) 

    def save_model(self, request, obj, form, change):
        """
        重写保存逻辑：
        当管理员在后台手动修改成长值(growth)时，自动重新计算等级(level)
        公式: Level = 1 + (growth // 100)
        """
        # 自动计算等级
        if obj.growth is not None:
            obj.level = 1 + (obj.growth // 100)
        
        # 调用父类保存方法写入数据库
        super().save_model(request, obj, form, change)

admin.site.register(CustomUser, CustomUserAdmin)