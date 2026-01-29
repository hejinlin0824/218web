from django.contrib import admin
from .models import ResearchTopic, Publication, LabClass # 👈 引入 LabClass
from django.contrib.auth import get_user_model




User = get_user_model()
@admin.register(ResearchTopic)
class ResearchTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon')

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'venue', 'year', 'is_highlight')
    list_filter = ('year', 'venue', 'is_highlight')
    search_fields = ('title', 'authors')

@admin.register(LabClass)
class LabClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'mentor', 'student_count', 'created_at')
    search_fields = ('name', 'mentor__username', 'mentor__nickname')
    autocomplete_fields = ['mentor'] # 如果用户多，建议在 UserAdmin 开启 search_fields
    filter_horizontal = ('students',) # 方便的多选框界面

    def student_count(self, obj):
        return obj.students.count()
    student_count.short_description = '学生人数'

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # 后台也强制过滤，只显示在读学生
        if db_field.name == "students":
            kwargs["queryset"] = User.objects.filter(status='student')
        return super().formfield_for_manytomany(db_field, request, **kwargs)