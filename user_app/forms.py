from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class RegisterForm(UserCreationForm):
    """注册表单"""
    email = forms.EmailField(required=True, label='电子邮箱')
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'nickname')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class ProfileUpdateForm(forms.ModelForm):
    """
    个人资料修改表单
    修复了格式问题，增加了占位符
    """
    class Meta:
        model = CustomUser
        fields = ('nickname', 'email', 'bio', 'avatar')
        
        # 使用 widgets 精确控制样式
        widgets = {
            'nickname': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '请输入你的昵称'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 
                'placeholder': 'example@email.com'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': '写一段话介绍你自己...'
            }),
            # 👇👇👇 关键修改在这里 👇👇👇
            # 原来是 forms.ClearableFileInput (带清除框)
            # 改为 forms.FileInput (不带清除框，只能上传新图替换)
            'avatar': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            # 👆👆👆 修改结束 👆👆👆
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 如果你想单独把 email 设为只读，可以在这里解开注释：
        self.fields['email'].widget.attrs['readonly'] = True