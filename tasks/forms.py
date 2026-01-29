# tasks/forms.py

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Task
from core.models import LabClass  # 👈 必须引入班级模型

User = get_user_model()

class TaskCreateForm(forms.ModelForm):
    # 1. 个人选择字段 (保留原有逻辑，过滤掉新生)
    # 使用 CheckboxSelectMultiple 以便前端自定义样式
    invitees = forms.ModelMultipleChoiceField(
        queryset=User.objects.exclude(status='newbie').order_by('-status', 'nickname', 'username'),
        widget=forms.CheckboxSelectMultiple, 
        label='选择执行人 (个人)',
        required=True # 默认必填，但在 __init__ 中对导师改为 False
    )

    # 2. 👇 新增：班级选择字段 (用于导师一键群发)
    target_class = forms.ModelChoiceField(
        queryset=LabClass.objects.none(), # 初始化为空，在 __init__ 中动态加载
        required=False, # 默认非必填
        label='🏫 发送给班级 (强制指派)',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='选择班级后，班级内所有成员将自动加入任务并强制接受。'
    )

    class Meta:
        model = Task
        # 注意：invitees 和 target_class 不是 Task 模型的字段，所以不需要写在 Meta fields 里
        # 它们是表单扩展字段，我们在 View 中处理它们的逻辑
        fields = ['title', 'content', 'bounty', 'deadline', 'task_type'] 
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '任务目标'}),
            'bounty': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'id': 'id_bounty'}),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'task_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_task_type'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 核心逻辑：根据用户身份调整表单
        if self.user:
            if self.user.status == 'faculty':
                # === 导师视图 ===
                # 1. 加载该导师管理的班级
                self.fields['target_class'].queryset = LabClass.objects.filter(mentor=self.user)
                
                # 2. "个人选择"改为非必填 (因为导师可能只选班级)
                self.fields['invitees'].required = False
                
            else:
                # === 普通用户/学生视图 ===
                # 1. 隐藏班级选择
                self.fields['target_class'].widget = forms.HiddenInput()
                
                # 2. 锁定任务类型为悬赏 (不能发导师指令)
                self.fields['task_type'].choices = [('bounty', '💰 悬赏任务')]
                self.fields['task_type'].initial = 'bounty'
                self.fields['task_type'].widget = forms.HiddenInput() # 直接隐藏，默认悬赏

    def clean(self):
        cleaned_data = super().clean()
        task_type = cleaned_data.get('task_type')
        bounty = cleaned_data.get('bounty')
        target_class = cleaned_data.get('target_class')
        invitees = cleaned_data.get('invitees')
        
        # 1. 校验参与者：必须至少选一个人 或者 选一个班级
        if not invitees and not target_class:
            # 如果是导师，提示选人或班级
            if self.user.status == 'faculty':
                raise forms.ValidationError("请至少选择一个【执行人】或者一个【班级】。")
            else:
                # 普通用户只有 invitees 字段可见
                self.add_error('invitees', "请至少选择一个执行人。")

        # 2. 导师指令强制无赏金
        if task_type == 'faculty':
            cleaned_data['bounty'] = 0
            
        # 3. 余额校验 (仅针对普通悬赏)
        elif self.user and bounty > 0:
            if bounty > self.user.coins:
                self.add_error('bounty', f"金币不足 (余额: {self.user.coins})")
            
        return cleaned_data

    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if deadline and deadline < timezone.now():
            raise forms.ValidationError("截止时间不能早于当前时间")
        return deadline