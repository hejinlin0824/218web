from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # 这里的 name='intro' 将用于模板链接 {% url 'core:intro' %}
    path('intro/', views.lab_intro, name='intro'),
]