from django.urls import path
from . import views

app_name = 'vocabulary'

urlpatterns = [
    path('', views.index, name='index'), # 主页
    path('practice/', views.practice, name='practice'), # 练习页
    path('api/words/', views.api_get_words, name='api_get_words'), # API
]