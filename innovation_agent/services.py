import fitz  # PyMuPDF
from openai import OpenAI
from django.conf import settings
from .models import LLMConfiguration, InnovationProject, ProjectChatHistory
from .utils import EncryptionManager
from .prompts import PromptManager
import logging
import re  # 👈 必须导入正则表达式库

logger = logging.getLogger(__name__)

class PDFProcessor:
    @staticmethod
    def extract_text(file_path):
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except Exception as e:
            logger.error(f"PDF Parse Error: {e}")
            raise ValueError(f"PDF 解析失败: {str(e)}")

class LLMService:
    def __init__(self, user):
        self.user = user
        self.config = self._get_config()
        self.client = self._init_client()

    def _get_config(self):
        try:
            return LLMConfiguration.objects.get(user=self.user)
        except LLMConfiguration.DoesNotExist:
            raise ValueError("请先在个人中心配置 AI 模型 API Key")

    def _init_client(self):
        raw_key = EncryptionManager().decrypt(self.config.encrypted_api_key)
        if not raw_key:
            raise ValueError("API Key 解密失败或未配置")
        return OpenAI(api_key=raw_key, base_url=self.config.base_url)

    def call_model(self, messages, project: InnovationProject = None):
        try:
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=0.7,
                stream=False
            )
            content = response.choices[0].message.content
            
            if response.usage and project:
                total_usage = response.usage.total_tokens
                project.total_tokens_used += total_usage
                project.save(update_fields=['total_tokens_used'])
                
            return content
        except Exception as e:
            logger.error(f"LLM Call Error: {e}")
            raise ValueError(f"AI 调用失败: {str(e)}，请检查 Key 或余额")

# ==========================================
# 业务逻辑封装
# ==========================================

def generate_baseline_summary(project_id, user):
    """Step 2: Baseline 总结 (直接生成，视为已定稿草稿)"""
    project = InnovationProject.objects.get(id=project_id, user=user)
    
    # 1. 解析 PDF
    pdf_path = project.baseline_file.path
    full_text = PDFProcessor.extract_text(pdf_path)
    
    ProjectChatHistory.objects.create(
        project=project, role='system',
        content=f"已解析 PDF ({len(full_text)}字符)，正在生成 Baseline 分析..."
    )

    # 2. 调用 AI
    prompt_content = PromptManager.get_baseline_prompt(full_text)
    messages = [{"role": "user", "content": prompt_content}]
    llm = LLMService(user)
    summary = llm.call_model(messages, project=project)
    
    # 3. 强制保存 (Baseline 不需要 Draft 协议，直接视为文档)
    project.base_md_content = summary
    project.status = 2 # 进 Innov 1
    project.save()
    
    ProjectChatHistory.objects.create(
        project=project, role='assistant',
        content="✅ **Baseline 分析完成**。\n\n请查看右侧文档。现在开始构思 **创新点 1**。"
    )
    
    return summary

def refine_innovation(project_id, user, user_idea, innov_index=1):
    """Step 3/4: 创新点构思 (核心：支持聊天 vs 草稿协议)"""
    project = InnovationProject.objects.get(id=project_id, user=user)
    
    # 1. 记录用户输入
    ProjectChatHistory.objects.create(project=project, role='user', content=user_idea)

    # 2. 准备上下文
    prev_innovs = ""
    if innov_index > 1: prev_innovs += f"\n--- Innov 1 ---\n{project.innov1_md_content}\n"
    if innov_index > 2: prev_innovs += f"\n--- Innov 2 ---\n{project.innov2_md_content}\n"
    if not prev_innovs: prev_innovs = "无"

    # 3. 调用 AI
    prompt = PromptManager.get_innovation_prompt(innov_index, project.base_md_content, prev_innovs, user_idea)
    llm = LLMService(user)
    raw_response = llm.call_model([{"role": "user", "content": prompt}], project=project)
    
    # 4. 🔥 解析 <DRAFT> 标签 🔥
    draft_match = re.search(r'<DRAFT>(.*?)</DRAFT>', raw_response, re.DOTALL)
    
    response_data = {
        'chat_content': raw_response, # 默认显示全部
        'draft_content': None,
        'is_draft': False
    }

    if draft_match:
        # A. 提取到草稿 -> 存库，前端弹窗
        draft_content = draft_match.group(1).strip()
        
        # 存入数据库对应字段 (作为草稿)
        if innov_index == 1: project.innov1_md_content = draft_content
        elif innov_index == 2: project.innov2_md_content = draft_content
        elif innov_index == 3: project.innov3_md_content = draft_content
        project.save()
        
        response_data['is_draft'] = True
        response_data['draft_content'] = draft_content
        
        # 聊天框只显示 <DRAFT> 之外的引导语
        chat_part = raw_response.replace(draft_match.group(0), "").strip()
        if not chat_part: chat_part = "已为你生成详细方案草稿，请在右侧查看。"
        response_data['chat_content'] = chat_part
        
    else:
        # B. 没提取到 -> 纯聊天模式
        response_data['is_draft'] = False
        # 不存库，只记录聊天历史
    
    # 5. 记录 AI 回复到历史
    ProjectChatHistory.objects.create(
        project=project, role='assistant',
        content=response_data['chat_content']
    )
    
    return response_data

def confirm_innovation(project_id, user, content, innov_index):
    """用户点击“定稿”时调用"""
    project = InnovationProject.objects.get(id=project_id, user=user)
    current_status = project.status
    
    # 更新对应字段 (虽然草稿已经存了，但这里是最终确认，可能在前端改过)
    if current_status == 2:
        project.innov1_md_content = content
        project.status = 3
    elif current_status == 3:
        project.innov2_md_content = content
        project.status = 4
    elif current_status == 4:
        project.innov3_md_content = content
        project.status = 5
    elif current_status == 5:
        project.exp_md_content = content
        project.status = 6
        
    project.save()

def generate_experiment_design(project_id, user):
    """Step 5: 实验设计 (通常包含 DRAFT)"""
    project = InnovationProject.objects.get(id=project_id, user=user)
    
    ProjectChatHistory.objects.create(project=project, role='user', content="生成实验设计")

    prompt = PromptManager.get_experiment_prompt(
        project.base_md_content, 
        project.innov1_md_content, 
        project.innov2_md_content, 
        project.innov3_md_content
    )
    
    llm = LLMService(user)
    raw_response = llm.call_model([{"role": "user", "content": prompt}], project=project)
    
    # 解析 DRAFT
    draft_match = re.search(r'<DRAFT>(.*?)</DRAFT>', raw_response, re.DOTALL)
    
    response_data = {
        'chat_content': raw_response,
        'draft_content': None,
        'is_draft': False
    }
    
    if draft_match:
        draft_content = draft_match.group(1).strip()
        project.exp_md_content = draft_content
        project.save() # 存草稿
        
        response_data['is_draft'] = True
        response_data['draft_content'] = draft_content
        
        chat_part = raw_response.replace(draft_match.group(0), "").strip()
        if not chat_part: chat_part = "实验方案已生成，请检查。"
        response_data['chat_content'] = chat_part
    
    ProjectChatHistory.objects.create(
        project=project, role='assistant',
        content=response_data['chat_content']
    )
    
    return response_data