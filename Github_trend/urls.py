from django.urls import path
from . import views

app_name = 'Github_trend'  # 命名空间

urlpatterns = [
    path('', views.index, name='index'),
]