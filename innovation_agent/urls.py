from django.urls import path
from . import views

app_name = 'innovation_agent'

urlpatterns = [
    # 1. 页面路由
    path('config/', views.llm_config, name='config'), # Phase 1 已存在
    path('projects/', views.project_list, name='project_list'), # 项目列表
    path('workspace/new/', views.create_project, name='create_project'), # 新建项目
    path('workspace/<uuid:project_id>/', views.workspace, name='workspace'), # 核心工作台
    
    # 2. AJAX API 路由 (用于异步交互)
    # Step 1: 上传 Baseline
    path('api/<uuid:project_id>/upload_baseline/', views.api_upload_baseline, name='api_upload_baseline'),
    
    # Step 2: 生成 Baseline 总结
    path('api/<uuid:project_id>/generate_base_summary/', views.api_generate_base_summary, name='api_generate_base_summary'),
    
    # Step 3/4: 创新点对话 (提交想法 -> AI分析)
    path('api/<uuid:project_id>/chat_innovation/', views.api_chat_innovation, name='api_chat_innovation'),
    
    # 通用: 确认当前步骤 (保存 MD -> 状态流转)
    path('api/<uuid:project_id>/confirm_step/', views.api_confirm_step, name='api_confirm_step'),
    
    # Step 5: 生成实验设计
    path('api/<uuid:project_id>/generate_experiment/', views.api_generate_experiment, name='api_generate_experiment'),
    
    # Step 6: 生成最终 PDF
    path('api/<uuid:project_id>/generate_pdf/', views.api_generate_pdf, name='api_generate_pdf'),
    path('projects/<uuid:project_id>/delete/', views.delete_project, name='delete_project'),
    path('api/<uuid:project_id>/get_doc/', views.api_get_doc_content, name='api_get_doc_content'),
    path('projects/<uuid:project_id>/download/', views.download_project_markdown, name='download_project'),
]