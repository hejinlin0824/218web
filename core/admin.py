from django.contrib import admin
# 👇 删掉 Faculty 的引用
from .models import ResearchTopic, Publication
@admin.register(ResearchTopic)
class ResearchTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon')

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'venue', 'year', 'is_highlight')
    list_filter = ('year', 'venue', 'is_highlight')
    search_fields = ('title', 'authors')