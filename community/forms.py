from django import forms
from .models import Post
from .models import Post, Comment # 👈 记得导入 Comment

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content'] # 只让用户填这两个，作者自动填
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