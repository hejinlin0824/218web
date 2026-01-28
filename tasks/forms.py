# tasks/forms.py

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Task

User = get_user_model()

class TaskCreateForm(forms.ModelForm):
    # 使用 CheckboxSelectMultiple 以便前端自定义样式
    invitees = forms.ModelMultipleChoiceField(
        # 1. 过滤：排除新生 (newbie)，保留在读(student)、毕业(alumni)、导师(faculty)
        queryset=User.objects.exclude(status='newbie').order_by('-status', 'nickname', 'username'),
        widget=forms.CheckboxSelectMultiple, # 👈 改为复选框组件
        label='选择执行人',
        required=True
    )

    class Meta:
        model = Task
        fields = ['title', 'content', 'bounty', 'deadline', 'task_type'] # 加入 task_type
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '任务目标'}),
            'bounty': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'task_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 2. 只有导师才能选择 "导师指令"
        if self.user and self.user.status != 'faculty':
            # 普通人只能发悬赏，把 task_type 字段隐藏或锁定
            self.fields['task_type'].choices = [('bounty', '💰 悬赏任务')]
            self.fields['task_type'].initial = 'bounty'
            self.fields['task_type'].widget = forms.HiddenInput()
        
        # 注意：这里我们不再剔除 self.user.pk，允许选自己

    def clean(self):
        cleaned_data = super().clean()
        task_type = cleaned_data.get('task_type')
        bounty = cleaned_data.get('bounty')
        
        # 3. 导师指令强制无赏金
        if task_type == 'faculty':
            cleaned_data['bounty'] = 0
        elif self.user and bounty > self.user.coins:
            self.add_error('bounty', f"金币不足 (余额: {self.user.coins})")
            
        return cleaned_data

    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if deadline and deadline < timezone.now():
            raise forms.ValidationError("截止时间不能早于当前时间")
        return deadline