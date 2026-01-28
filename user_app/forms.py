from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, StudentWhitelist

class RegisterForm(UserCreationForm):
    """注册表单"""
    email = forms.EmailField(required=True, label='电子邮箱')
    
    # 注册时允许选择 新生 或 在读 (不能选毕业)
    status = forms.ChoiceField(
        label='您的身份',
        choices=[('newbie', '🌱 新生 (默认)'), ('student', '🎓 在读')],
        initial='newbie',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_status'})
    )
    
    student_id = forms.CharField(
        label='学号',
        required=False, # 前端控制显示，后台逻辑判断是否必填
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

        # 逻辑：如果选择了“在读”，必须验证学号
        if status == 'student':
            if not student_id:
                self.add_error('student_id', '选择“在读”身份必须填写学号。')
            else:
                # 1. 验证是否在白名单中
                if not StudentWhitelist.objects.filter(student_id=student_id).exists():
                    self.add_error('student_id', '认证失败：该学号不存在于白名单中，请联系管理员。')
                
                # 2. 验证是否已被注册 (排除自己，但注册时肯定没有自己)
                elif CustomUser.objects.filter(student_id=student_id).exists():
                    self.add_error('student_id', '该学号已被注册，请联系管理员核实。')
        
        # 如果是新生，清空学号防止误填
        if status == 'newbie':
            cleaned_data['student_id'] = None
            
        return cleaned_data

class ProfileUpdateForm(forms.ModelForm):
    """
    个人资料修改表单
    包含复杂的状态流转逻辑
    """
    class Meta:
        model = CustomUser
        fields = ('nickname', 'email', 'bio', 'avatar', 'status', 'student_id')
        
        widgets = {
            'nickname': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': True}), # 邮箱不可改
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control', 'id': 'id_profile_status'}),
            'student_id': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_profile_student_id'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        new_status = cleaned_data.get('status')
        new_student_id = cleaned_data.get('student_id')
        
        # 获取用户当前的数据库状态 (self.instance)
        current_user = self.instance
        old_status = current_user.status

        # === 状态流转规则 ===
        
        # 1. 毕业 -> 任何状态：禁止修改
        if old_status == 'alumni':
            if new_status != 'alumni':
                self.add_error('status', '您已毕业，身份状态不可更改。')
            # 甚至不允许改学号
            if new_student_id != current_user.student_id:
                self.add_error('student_id', '毕业后学号不可更改。')
            return cleaned_data

        # 2. 新生 -> 毕业：禁止
        if old_status == 'newbie' and new_status == 'alumni':
            self.add_error('status', '新生不能直接改为毕业，请先认证为在读生。')

        # 3. 在读 -> 新生：禁止
        if old_status == 'student' and new_status == 'newbie':
            self.add_error('status', '在读生不能回退为新生。')

        # === 学号验证逻辑 ===
        
        # 情况A：新生 -> 在读 (需要验证学号)
        # 情况B：已经在读，但是想改学号 (也需要验证)
        if (old_status == 'newbie' and new_status == 'student') or \
           (old_status == 'student' and new_status == 'student' and new_student_id != current_user.student_id):
            
            if not new_student_id:
                self.add_error('student_id', '认证为在读生必须填写学号。')
            else:
                # 1. 查白名单
                if not StudentWhitelist.objects.filter(student_id=new_student_id).exists():
                    self.add_error('student_id', '验证失败：学号不存在于学校白名单中。')
                
                # 2. 查唯一性 (排除自己)
                elif CustomUser.objects.filter(student_id=new_student_id).exclude(pk=current_user.pk).exists():
                    self.add_error('student_id', '该学号已被其他用户绑定。')

        return cleaned_data