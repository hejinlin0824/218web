# cyber_fortune/urls.py
from django.urls import path
from . import views

app_name = 'cyber_fortune'

urlpatterns = [
    path('', views.fortune_index, name='index'),               
    path('init/', views.init_profile, name='init_profile'),    
    path('api/draw/', views.draw_blessing, name='draw_blessing'), 
    path('api/muyu/click/', views.click_muyu, name='click_muyu'), # 木鱼接口
]