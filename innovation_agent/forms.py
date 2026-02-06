from django import forms
from .models import LLMConfiguration

class LLMConfigForm(forms.ModelForm):
    # 显式声明 api_key 字段，因为 model 里存的是 encrypted_api_key
    api_key = forms.CharField(
        label="API Key",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'sk-...'}),
        required=True,
        help_text="您的 Key 将被加密存储，我们无法查看明文。"
    )

    class Meta:
        model = LLMConfiguration
        fields = ['provider', 'base_url', 'model_name']
        widgets = {
            'provider': forms.Select(attrs={'class': 'form-select'}),
            'base_url': forms.TextInput(attrs={'class': 'form-control'}),
            'model_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 回显逻辑
        if self.instance.pk and self.instance.encrypted_api_key:
            # 解密并填入 initial，这样用户进来能看到原来的 Key (或者你可以只显示部分)
            self.fields['api_key'].initial = self.instance.get_api_key()

    def save(self, commit=True):
        instance = super().save(commit=False)
        # 处理 API Key 加密
        raw_key = self.cleaned_data.get('api_key')
        if raw_key:
            instance.set_api_key(raw_key)
        if commit:
            instance.save()
        return instance