from django.urls import path
from . import views

app_name = 'npy_editor'

urlpatterns = [
    path('', views.editor_page, name='home'),
    path('api/upload/', views.upload_file, name='upload_file'),
    path('api/get_data/', views.get_chart_data, name='get_data'),
    path('api/update/', views.update_data, name='update_data'),
]