# cyber_fortune/forms.py
from django import forms
from .models import FortuneProfile

MBTI_CHOICES = [
    ('INTJ', 'INTJ (建筑师)'), ('INTP', 'INTP (逻辑学家)'), ('ENTJ', 'ENTJ (指挥官)'), ('ENTP', 'ENTP (辩论家)'),
    ('INFJ', 'INFJ (提倡者)'), ('INFP', 'INFP (调停者)'), ('ENFJ', 'ENFJ (主人公)'), ('ENFP', 'ENFP (竞选者)'),
    ('ISTJ', 'ISTJ (物流师)'), ('ISFJ', 'ISFJ (守卫者)'), ('ESTJ', 'ESTJ (总经理)'), ('ESFJ', 'ESFJ (执政官)'),
    ('ISTP', 'ISTP (鉴赏家)'), ('ISFP', 'ISFP (探险家)'), ('ESTP', 'ESTP (企业家)'), ('ESFP', 'ESFP (表演者)'),
]

class FortuneProfileForm(forms.ModelForm):
    mbti = forms.ChoiceField(choices=MBTI_CHOICES, label='MBTI 初始设定', widget=forms.Select(attrs={'class': 'form-select cyber-input'}))
    
    class Meta:
        model = FortuneProfile
        fields = ['birth_date', 'mbti']
        widgets = {
            'birth_date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control form-control-lg cyber-input',
                'required': 'required'
            })
        }
        labels = {
            'birth_date': '降生参数 (出生日期)'
        }