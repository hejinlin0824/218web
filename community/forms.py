from django import forms
from .models import Post, Comment, Tag, Collection # 👈 引入 Collection

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
        # 👇 增加 'visibility'
        fields = ['title', 'tags', 'content', 'visibility'] 
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入标题'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            # 👇 美化下拉框
            'visibility': forms.Select(attrs={'class': 'form-select'}),
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

# 👇👇👇 新增：收藏夹表单
class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ['name', 'description', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例如：深度学习资料'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '可选：描述这个收藏夹的内容'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ['name', 'description', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '收藏夹名称 (如: 深度学习必读)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '简介 (可选)'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_public': '公开此收藏夹'
        }