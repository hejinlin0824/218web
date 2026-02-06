from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings
import json
import os
from django.utils.encoding import escape_uri_path # 👈 必须添加这一行，用于处理中文文件名

# 引入模型和服务
from .models import InnovationProject, LLMConfiguration
from .services import (
    generate_baseline_summary, 
    refine_innovation, 
    confirm_innovation, 
    generate_experiment_design
)
from .forms import LLMConfigForm  # 确保你创建了 forms.py

# ==========================================
# 1. 页面视图 (Page Views)
# ==========================================

@login_required
def llm_config(request):
    """用户配置 LLM 页面"""
    config, created = LLMConfiguration.objects.get_or_create(user=request.user)

    # 智能跳转：如果有 Key 且不是强制编辑模式，直接跳列表
    force_edit = request.GET.get('edit', 'false') == 'true'
    if request.method == 'GET' and not force_edit and config.encrypted_api_key:
        return redirect('innovation_agent:project_list')

    if request.method == 'POST':
        form = LLMConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            return redirect('innovation_agent:project_list') 
    else:
        form = LLMConfigForm(instance=config)

    return render(request, 'innovation_agent/config.html', {
        'form': form,
        'title': 'AI 模型配置',
        'is_edit_mode': bool(config.encrypted_api_key)
    })

@login_required
def project_list(request):
    """项目列表页"""
    if not LLMConfiguration.objects.filter(user=request.user).exists():
        return redirect('innovation_agent:config')
        
    projects = InnovationProject.objects.filter(user=request.user).order_by('-updated_at')
    return render(request, 'innovation_agent/project_list.html', {'projects': projects})

@login_required
def create_project(request):
    """新建项目"""
    if not LLMConfiguration.objects.filter(user=request.user).exists():
        return redirect('innovation_agent:config')
        
    project = InnovationProject.objects.create(
        user=request.user,
        title=f"创新项目 {request.user.innovation_projects.count() + 1}"
    )
    return redirect('innovation_agent:workspace', project_id=project.id)

@login_required
def workspace(request, project_id):
    """核心工作台"""
    project = get_object_or_404(InnovationProject, id=project_id, user=request.user)
    # 加载历史聊天记录
    chat_history = project.chat_history.all().order_by('created_at')
    
    context = {
        'project': project,
        'step': project.status,
        'chat_history': chat_history,
    }
    return render(request, 'innovation_agent/workspace.html', context)

# ==========================================
# 2. API 视图 (AJAX Endpoints)
# ==========================================

@login_required
@require_POST
def api_upload_baseline(request, project_id):
    """Step 1: 上传 PDF"""
    project = get_object_or_404(InnovationProject, id=project_id, user=request.user)
    
    if 'file' not in request.FILES:
        return JsonResponse({'status': 'error', 'msg': '未上传文件'})
        
    file = request.FILES['file']
    if not file.name.lower().endswith('.pdf'):
        return JsonResponse({'status': 'error', 'msg': '仅支持 PDF 文件'})
        
    project.baseline_file = file
    project.status = 1 # 状态更新为已上传
    project.save()
    
    return JsonResponse({'status': 'ok', 'msg': '上传成功'})

@login_required
@require_POST
def api_generate_base_summary(request, project_id):
    """Step 2: 生成 Baseline 总结"""
    try:
        summary = generate_baseline_summary(project_id, request.user)
        project = InnovationProject.objects.get(id=project_id)
        return JsonResponse({
            'status': 'ok', 
            'content': summary, 
            'tokens': project.total_tokens_used
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})

@login_required
@require_POST
def api_chat_innovation(request, project_id):
    """Step 3/4: 创新点对话 (核心交互)"""
    project = get_object_or_404(InnovationProject, id=project_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        user_idea = data.get('idea')
        # 根据当前状态判断是第几个创新点
        innov_index = project.status - 1 
        
        if innov_index not in [1, 2, 3]:
            return JsonResponse({'status': 'error', 'msg': '当前状态不支持创新点生成'})

        # 调用 Services (注意：这里返回的是字典，包含 is_draft 标志)
        result_data = refine_innovation(project.id, request.user, user_idea, innov_index)
        
        project.refresh_from_db()
        
        return JsonResponse({
            'status': 'ok', 
            'chat_content': result_data['chat_content'],   # 显示在聊天框的引导语
            'draft_content': result_data['draft_content'], # 如果有草稿，这里是 MD 内容
            'is_draft': result_data['is_draft'],           # 前端据此判断是否弹窗
            'tokens': project.total_tokens_used
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})

@login_required
@require_POST
def api_generate_experiment(request, project_id):
    """Step 5: 生成实验设计"""
    try:
        # 实验设计通常直接生成草稿
        result_data = generate_experiment_design(project_id, request.user)
        project = InnovationProject.objects.get(id=project_id)
        
        return JsonResponse({
            'status': 'ok',
            'chat_content': result_data['chat_content'],
            'draft_content': result_data['draft_content'],
            'is_draft': True, # 强制为草稿模式
            'tokens': project.total_tokens_used
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})

@login_required
@require_POST
def api_confirm_step(request, project_id):
    """通用确认接口：保存前端 Vditor 的最终内容并流转状态"""
    project = get_object_or_404(InnovationProject, id=project_id, user=request.user)
    try:
        data = json.loads(request.body)
        final_content = data.get('content')
        
        current_status = project.status
        # 允许确认的状态: 2(Innov1), 3(Innov2), 4(Innov3), 5(Exp)
        if current_status in [2, 3, 4, 5]:
            innov_index = current_status - 1
            
            # 1. 执行数据库更新 (Service 层会 save 到数据库)
            confirm_innovation(project.id, request.user, final_content, innov_index)
            
            # 🔥🔥🔥 核心修复：刷新 project 对象，获取数据库最新状态 🔥🔥🔥
            project.refresh_from_db()
            
            return JsonResponse({
                'status': 'ok', 
                'next_step': project.status, # 现在这里是更新后的状态 (例如 6)
                'msg': '内容已定稿并保存'
            })
            
        return JsonResponse({'status': 'error', 'msg': f'无效的状态流转 (当前状态: {current_status})'})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})

@login_required
def api_get_doc_content(request, project_id):
    """前端侧边栏点击时，获取文档内容"""
    project = get_object_or_404(InnovationProject, id=project_id, user=request.user)
    doc_type = request.GET.get('type')
    
    content = ""
    if doc_type == 'base':
        content = project.base_md_content
    elif doc_type == 'innov1':
        content = project.innov1_md_content
    elif doc_type == 'innov2':
        content = project.innov2_md_content
    elif doc_type == 'innov3':
        content = project.innov3_md_content
    elif doc_type == 'exp':
        content = project.exp_md_content
        
    return JsonResponse({'status': 'ok', 'content': content})

@login_required
def api_generate_pdf(request, project_id):
    # Phase 5 实现
    return HttpResponse("PDF Generation coming soon...", content_type="text/plain")

@login_required
@require_POST
def delete_project(request, project_id):
    project = get_object_or_404(InnovationProject, id=project_id, user=request.user)
    project.delete()
    return redirect('innovation_agent:project_list')

@login_required
def download_project_markdown(request, project_id):
    """
    功能：将分散的各个部分拼接成一份完整的 Markdown 报告并下载
    修复：解决中文乱码问题 (BOM + Charset)
    """
    project = get_object_or_404(InnovationProject, id=project_id, user=request.user)
    
    # 1. 拼接内容 (保持不变)
    full_content = f"""# {project.title} - Final Research Report
    Generated by Innovation Agent on {project.updated_at.strftime('%Y-%m-%d')}

    ---

    ## Part 1: Baseline Analysis
    {project.base_md_content or '(未生成)'}

    ---

    ## Part 2: Innovation Point 1
    {project.innov1_md_content or '(未生成)'}

    ---

    ## Part 3: Innovation Point 2
    {project.innov2_md_content or '(未生成)'}

    ---

    ## Part 4: Innovation Point 3
    {project.innov3_md_content or '(未生成)'}

    ---

    ## Part 5: Experimental Design
    {project.exp_md_content or '(未生成)'}
    """

    # 2. 🔥 核心修复：添加 BOM (\ufeff) 并指定 UTF-8 编码 🔥
    # Windows 记事本需要 BOM 才能正确识别 UTF-8 中文
    final_content = '\ufeff' + full_content
    
    response = HttpResponse(final_content, content_type='text/markdown; charset=utf-8')
    
    # 3. 🔥 核心修复：处理中文文件名 🔥
    filename = f"Final_Report_{project.title}.md"
    encoded_filename = escape_uri_path(filename)
    
    # 使用 RFC 5987 标准设置文件名，兼容各种浏览器
    response['Content-Disposition'] = f'attachment; filename="{encoded_filename}"; filename*=UTF-8\'\'{encoded_filename}'
    
    return response