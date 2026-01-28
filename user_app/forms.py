from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, StudentWhitelist

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label='电子邮箱')
    
    # 注册时显式排除 'faculty'，只允许 新生 和 在读
    status = forms.ChoiceField(
        label='您的身份',
        choices=[('newbie', '🌱 新生 (默认)'), ('student', '🎓 在读')],
        initial='newbie',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_status'})
    )
    
    student_id = forms.CharField(
        label='学号',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_student_id', 'placeholder': '选择“在读”时必填'})
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'nickname', 'status', 'student_id')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        student_id = cleaned_data.get('student_id')

        if status == 'student':
            if not student_id:
                self.add_error('student_id', '选择“在读”身份必须填写学号。')
            else:
                if not StudentWhitelist.objects.filter(student_id=student_id).exists():
                    self.add_error('student_id', '认证失败：该学号不存在于白名单中，请联系管理员。')
                elif CustomUser.objects.filter(student_id=student_id).exists():
                    self.add_error('student_id', '该学号已被注册，请联系管理员核实。')
        
        if status == 'newbie':
            cleaned_data['student_id'] = None
            
        return cleaned_data

class ProfileUpdateForm(forms.ModelForm):
    """
    个人资料修改表单
    """
    class Meta:
        model = CustomUser
        # 👇 1. 在 fields 列表最后加上 'detailed_intro'
        fields = ('nickname', 'email', 'bio', 'avatar', 'status', 'student_id', 'detailed_intro')
        
        widgets = {
            'nickname': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': True}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '一句话简介...'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control', 'id': 'id_profile_status'}),
            'student_id': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_profile_student_id'}),
            # 👇 2. 增加详细介绍的组件配置
            'detailed_intro': forms.Textarea(attrs={
                'class': 'form-control font-monospace', 
                'rows': 8, 
                'placeholder': '在这里使用 Markdown 格式撰写您的详细简历、研究方向、发表论文等...\n\n例如：\n### 研究兴趣\n- 深度学习\n- 计算机视觉'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 👇👇👇 核心逻辑：过滤身份选项 👇👇👇
        # 1. 获取所有可选身份
        choices = list(CustomUser.STATUS_CHOICES)
        # 2. 过滤掉 'faculty' (导师)，普通人不能选
        filtered_choices = [c for c in choices if c[0] != 'faculty']
        
        # 3. 如果当前用户本身就是导师 (比如管理员在后台把他设为了导师)
        if self.instance.pk and self.instance.status == 'faculty':
            # 导师允许看到自己的身份，但不建议他随便改，或者你可以保留 faculty 选项让他能改回普通人
            # 这里我们选择：保留 faculty 选项，或者直接禁用修改
            # 为了简单，如果他是导师，我们就在选项里加上 faculty，否则不加
            pass 
        else:
            # 如果不是导师，那就绝对不能选 faculty
            self.fields['status'].choices = filtered_choices

    def clean_status(self):
        new_status = self.cleaned_data.get('status')
        current_user = self.instance
        
        # 👇 后端安全拦截：严禁普通用户将自己设为导师
        if new_status == 'faculty':
            if current_user.status != 'faculty': # 除非他本来就是导师
                raise forms.ValidationError("非法操作：导师身份仅能由管理员在后台设置。")
        
        return new_status

    def clean(self):
        cleaned_data = super().clean()
        new_status = cleaned_data.get('status')
        new_student_id = cleaned_data.get('student_id')
        current_user = self.instance
        old_status = current_user.status

        # 导师跳过后续验证
        if old_status == 'faculty' or new_status == 'faculty':
            return cleaned_data

        # 1. 毕业锁定逻辑
        if old_status == 'alumni':
            if new_status != 'alumni':
                self.add_error('status', '您已毕业，身份状态不可更改。')
            if new_student_id != current_user.student_id:
                self.add_error('student_id', '毕业后学号不可更改。')
            return cleaned_data

        # 2. 状态流转限制
        if old_status == 'newbie' and new_status == 'alumni':
            self.add_error('status', '新生不能直接改为毕业，请先认证为在读生。')
        if old_status == 'student' and new_status == 'newbie':
            self.add_error('status', '在读生不能回退为新生。')

        # 3. 学号验证
        if (old_status == 'newbie' and new_status == 'student') or \
           (old_status == 'student' and new_status == 'student' and new_student_id != current_user.student_id):
            if not new_student_id:
                self.add_error('student_id', '认证为在读生必须填写学号。')
            else:
                if not StudentWhitelist.objects.filter(student_id=new_student_id).exists():
                    self.add_error('student_id', '验证失败：学号不存在于学校白名单中。')
                elif CustomUser.objects.filter(student_id=new_student_id).exclude(pk=current_user.pk).exists():
                    self.add_error('student_id', '该学号已被其他用户绑定。')

        return cleaned_data