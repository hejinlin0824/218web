from django.db import models
from django.conf import settings
from .utils import EncryptionManager
import os
import uuid
# 👇👇👇 追加以下代码 👇👇👇
from django.db.models.signals import post_delete
from django.dispatch import receiver
import shutil

def project_file_path(instance, filename):
    """文件存储路径: innovation_projects/user_id/uuid/filename"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('innovation_projects', str(instance.user.id), str(instance.id), filename)

class LLMConfiguration(models.Model):
    """用户的大模型配置 (OneToOne)"""
    PROVIDER_CHOICES = (
        ('deepseek', 'DeepSeek (推荐)'),
        ('openai', 'OpenAI (GPT-4)'),
        ('anthropic', 'Claude'),
        ('custom', '自定义 (Compatible)'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='llm_config')
    provider = models.CharField('服务商', max_length=20, choices=PROVIDER_CHOICES, default='deepseek')
    base_url = models.CharField('Base URL', max_length=255, default='https://api.deepseek.com/v1', help_text="API 请求地址")
    model_name = models.CharField('模型名称', max_length=50, default='deepseek-chat', help_text="例如: gpt-4, deepseek-reasoner")
    
    # 存储加密后的 Key
    encrypted_api_key = models.CharField('API Key (加密)', max_length=500, blank=True)

    def set_api_key(self, raw_key):
        self.encrypted_api_key = EncryptionManager().encrypt(raw_key)

    def get_api_key(self):
        return EncryptionManager().decrypt(self.encrypted_api_key)

    def __str__(self):
        return f"{self.user.username} 的 LLM 配置"

    class Meta:
        verbose_name = "LLM 配置"
        verbose_name_plural = verbose_name

class InnovationProject(models.Model):
    """
    创新点生成项目 (核心状态机)
    """
    STATUS_CHOICES = (
        (0, '等待上传 Baseline'),
        (1, '正在解析 Baseline'),
        (2, '创新点 1 构思中'),
        (3, '创新点 2 构思中'),
        (4, '创新点 3 构思中'),
        (5, '实验设计中'),
        (6, '已完成'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='innovation_projects')
    title = models.CharField('项目名称', max_length=100, default="未命名创新项目")
    status = models.IntegerField('当前状态', choices=STATUS_CHOICES, default=0)
    
    # --- 文件存储区 ---
    # 1. 原始论文 PDF
    baseline_file = models.FileField('Baseline PDF', upload_to=project_file_path, null=True, blank=True)
    
    # 2. 中间产物 MD
    base_md_content = models.TextField('Baseline 总结 (MD)', blank=True) # 存数据库方便读取，也可存文件
    innov1_md_content = models.TextField('创新点 1 (MD)', blank=True)
    innov2_md_content = models.TextField('创新点 2 (MD)', blank=True)
    innov3_md_content = models.TextField('创新点 3 (MD)', blank=True)
    exp_md_content = models.TextField('实验设计 (MD)', blank=True)
    # 👇 新增字段：Token 消耗统计
    total_tokens_used = models.PositiveIntegerField('Token 总消耗', default=0)
    
    # 3. 最终产物
    final_report = models.FileField('最终报告 PDF', upload_to=project_file_path, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = "创新项目"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title

@receiver(post_delete, sender=InnovationProject)
def cleanup_project_files(sender, instance, **kwargs):
    """
    当项目被删除时，自动清理相关文件和文件夹
    """
    # 1. 删除 Baseline PDF 文件
    if instance.baseline_file:
        instance.baseline_file.delete(save=False)
        
    # 2. 删除最终报告 PDF 文件
    if instance.final_report:
        instance.final_report.delete(save=False)
        
    # 3. (可选) 彻底删除该项目的专属文件夹
    # 路径规则参考: innovation_projects/user_id/project_id/
    try:
        if instance.baseline_file:
            # 获取文件所在的目录 (即 project_id 目录)
            project_dir = os.path.dirname(instance.baseline_file.path)
            if os.path.exists(project_dir):
                shutil.rmtree(project_dir) # 递归删除文件夹及其内容
    except Exception as e:
        print(f"清理项目文件夹失败: {e}")

class ProjectChatHistory(models.Model):
    """
    项目专属的聊天记录 (实现会话记忆)
    """
    ROLE_CHOICES = (
        ('user', '用户'),
        ('assistant', 'AI'),
        ('system', '系统提示'),
    )
    
    project = models.ForeignKey(InnovationProject, on_delete=models.CASCADE, related_name='chat_history')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at'] # 按时间正序排列
        verbose_name = "项目聊天记录"
        verbose_name_plural = verbose_name