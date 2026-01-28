from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, StudentWhitelist

# 1. 注册学号白名单 (用于学生认证)
@admin.register(StudentWhitelist)
class StudentWhitelistAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'name')
    search_fields = ('student_id', 'name')

# 2. 自定义用户管理
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    
    # --- 列表页配置 ---
    # 在用户列表直接看到：身份、等级、成长值、学号
    list_display = ['username', 'email', 'nickname', 'status', 'level', 'growth', 'student_id', 'is_staff']
    list_filter = ('status', 'level', 'is_staff', 'is_active')
    search_fields = ('username', 'nickname', 'email', 'student_id')
    
    # --- 编辑页配置 (Fieldsets) ---
    # 这里定义了点击某个用户进去后，字段怎么分组显示
    fieldsets = UserAdmin.fieldsets + (
        ('自定义信息', {
            'fields': ('nickname', 'bio', 'avatar', 'email_verified', 'status', 'student_id')
        }),
        ('导师专属', {
            'fields': ('detailed_intro',), 
            'description': '仅当身份为"导师"时，此处的 Markdown 内容才会在前台展示。'
        }),
        ('成长体系 (Gamification)', {
            'fields': ('level', 'growth', 'coins')
        }),
    )
    
    # 设置 level 为只读，强制管理员通过修改 growth 来调整等级，保证数据一致性
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

# 注册 CustomUser
admin.site.register(CustomUser, CustomUserAdmin)