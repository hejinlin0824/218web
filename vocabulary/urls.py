from django.urls import path
from . import views

app_name = 'vocabulary'

urlpatterns = [
    path('', views.index, name='index'), 
    path('plan/', views.ebbinghaus_plan, name='plan'), # 👈 新增：艾宾浩斯计划页
    path('practice/', views.practice, name='practice'), 
    # 👇👇👇 新增：批次详情页 👇👇👇
    path('plan/<int:batch_id>/', views.batch_detail, name='batch_detail'),
    
    # APIs
    path('api/words/', views.api_get_words, name='api_get_words'),
    path('api/batch/finish/', views.api_finish_batch, name='api_finish_batch'), # 👈 新增：批次结算
    path('api/submit/', views.api_submit_result, name='api_submit_result'),
    path('api/kill/', views.api_kill_word, name='api_kill_word'), 
    path('api/setting/toggle/', views.api_toggle_setting, name='api_toggle_setting'), # 👈 新增：设置切换
    # 👇👇👇 新增：重置进度接口 👇👇👇
    path('api/book/reset/', views.api_reset_book_progress, name='api_reset_book_progress'),
    
    # Mistake book
    path('mistake-book/', views.mistake_book, name='mistake_book'),
]