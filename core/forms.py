# core/forms.py
from django import forms
from django.contrib.auth import get_user_model
from .models import LabClass

User = get_user_model()

class LabClassForm(forms.ModelForm):
    # 自定义多选字段，只列出未毕业的学生
    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(status='student').order_by('nickname', 'username'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='选择学生'
    )

    class Meta:
        model = LabClass
        fields = ['name', 'description', 'students']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class LabClassForm(forms.ModelForm):
    # 👇 关键：自定义学生选择字段
    # 1. 过滤条件：status='student' (只显示在读生)
    # 2. 排序：按昵称或用户名排序
    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(status='student').order_by('nickname', 'username'),
        widget=forms.CheckboxSelectMultiple, # 使用复选框界面
        required=False,
        label='选择班级成员'
    )

    class Meta:
        model = LabClass
        fields = ['name', 'description', 'students']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例如：2024级研究生组'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '简要描述班级方向...'}),
        }