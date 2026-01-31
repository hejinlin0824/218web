from django.urls import path
from . import views

app_name = 'vocabulary'

urlpatterns = [
    path('', views.index, name='index'), # 主页
    path('practice/', views.practice, name='practice'), # 练习页
    path('api/words/', views.api_get_words, name='api_get_words'), # API
    path('mistake-book/', views.mistake_book, name='mistake_book'),
    path('api/submit/', views.api_submit_result, name='api_submit_result'),
    path('api/kill/', views.api_kill_word, name='api_kill_word'),
]