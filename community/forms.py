from django import forms
from .models import Post, Comment, Tag

class PostForm(forms.ModelForm):
    # 自定义标签字段的显示方式
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=forms.CheckboxSelectMultiple, # 使用复选框，比下拉多选更直观
        required=False,
        label='选择标签'
    )

    class Meta:
        model = Post
        fields = ['title', 'tags', 'content'] # 👈 确保 tags 在这里
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入标题'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': '请输入内容...'}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': '写下你的评论...'
            }),
        }