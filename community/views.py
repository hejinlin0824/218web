from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.http import HttpResponseRedirect, JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_POST
from django.conf import settings
import os
import uuid
import time

from .models import Post, Comment, Tag
from .forms import PostForm, CommentForm
from notifications.models import Notification

# 1. 帖子列表视图
class PostListView(ListView):
    """帖子列表页：支持搜索、筛选、聚合统计"""
    model = Post
    template_name = 'community/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        # 预加载作者和标签，防止 N+1 查询问题，同时统计评论数
        queryset = Post.objects.select_related('author').prefetch_related('tags').annotate(comment_count=Count('comments'))

        # 1. 标签筛选
        tag_slug = self.request.GET.get('tag')
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)

        # 2. 搜索 (这里保留本地简单搜索逻辑，虽然后端模板表单指向了 Haystack，但保留这个逻辑作为 fallback)
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(content__icontains=query))

        # 3. 时间筛选
        time_filter = self.request.GET.get('filter')
        now = timezone.now()
        if time_filter == 'today':
            queryset = queryset.filter(created_at__gte=now - timedelta(days=1))
        elif time_filter == 'week':
            queryset = queryset.filter(created_at__gte=now - timedelta(weeks=1))
        elif time_filter == 'month':
            queryset = queryset.filter(created_at__gte=now - timedelta(days=30))

        # 默认按时间倒序
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_filter'] = self.request.GET.get('filter', 'all')
        context['search_query'] = self.request.GET.get('q', '')
        
        # 传递当前选中的标签信息，用于UI提示
        tag_slug = self.request.GET.get('tag')
        if tag_slug:
            # 如果标签不存在，get_object_or_404 会自动抛出 404
            context['current_tag'] = get_object_or_404(Tag, slug=tag_slug)
            
        # 传递所有标签供侧边栏或其他地方使用 (可选)
        context['all_tags'] = Tag.objects.all()
        return context

# 2. 发布帖子视图
class PostCreateView(LoginRequiredMixin, CreateView):
    """发布帖子页"""
    model = Post
    form_class = PostForm
    template_name = 'community/post_form.html'
    success_url = reverse_lazy('community:post_list')

    def form_valid(self, form):
        # 自动将当前登录用户设为作者
        form.instance.author = self.request.user
        return super().form_valid(form)

# 3. 帖子详情视图
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    # 检查当前用户是否已点赞
    is_liked = False
    if request.user.is_authenticated:
        if post.likes.filter(id=request.user.id).exists():
            is_liked = True
            
    # 处理评论提交
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('user_app:login')
            
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            
            # 处理嵌套回复
            parent_id = request.POST.get('parent_id')
            notification_recipient = None

            if parent_id:
                try:
                    target_comment = Comment.objects.get(id=parent_id)
                    # 扁平化处理：如果回复的是子评论，则挂载到父评论下，但内容@原作者
                    if target_comment.parent:
                        comment.parent = target_comment.parent
                        comment.content = f"回复 @{target_comment.author.nickname or target_comment.author.username}: {comment.content}"
                        notification_recipient = target_comment.author
                    else:
                        comment.parent = target_comment
                        notification_recipient = target_comment.author
                except Comment.DoesNotExist:
                    pass
            else:
                # 如果是直接评论帖子，通知帖子作者
                if post.author != request.user:
                    notification_recipient = post.author

            comment.save()

            # 发送通知
            if notification_recipient and notification_recipient != request.user:
                verb = 'reply' if parent_id else 'comment'
                Notification.objects.create(
                    recipient=notification_recipient,
                    actor=request.user,
                    verb=verb,
                    # 锚点定位到新生成的评论
                    target_url=reverse('community:post_detail', args=[pk]) + f"#comment-{comment.id}",
                    content=comment.content[:50]
                )

            return redirect('community:post_detail', pk=pk)
            
    else:
        # GET 请求：增加浏览量 (Session 防刷)
        form = CommentForm()
        session_key = f'viewed_post_{post.pk}'
        if not request.session.get(session_key):
            post.views += 1
            post.save(update_fields=['views'])
            request.session[session_key] = True

    # 获取顶级评论
    comments = post.comments.filter(parent=None).order_by('-created_at')

    context = {
        'post': post,
        'comments': comments,
        'form': form,
        'is_liked': is_liked,
    }
    return render(request, 'community/post_detail.html', context)

# 4. 点赞视图
@login_required
def like_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
        # 发送点赞通知
        if post.author != request.user:
            Notification.objects.create(
                recipient=post.author,
                actor=request.user,
                verb='like',
                target_url=reverse('community:post_detail', args=[pk]),
                content='赞了你的帖子'
            )
        
    return HttpResponseRedirect(reverse('community:post_detail', args=[str(pk)]))

# 5. 图片上传视图 (Vditor 专用)
@login_required
@require_POST
def upload_image(request):
    if 'file[]' not in request.FILES:
        return JsonResponse({'msg': '没有检测到文件', 'code': 1})

    file_obj = request.FILES.get('file[]')
    
    # 简单的后缀名校验
    if not file_obj.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
         return JsonResponse({'msg': '仅支持图片文件', 'code': 1})

    # 使用 UUID 生成文件名
    ext = file_obj.name.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    date_path = time.strftime("%Y%m")
    # 存储路径: media/posts/YYYYMM/uuid.ext
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'posts', date_path)
    
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    file_path = os.path.join(upload_dir, filename)
    
    with open(file_path, 'wb+') as f:
        for chunk in file_obj.chunks():
            f.write(chunk)
            
    # 返回 URL
    url = f"{settings.MEDIA_URL}posts/{date_path}/{filename}"
    
    # Vditor 要求的数据格式
    return JsonResponse({
        "msg": "上传成功",
        "code": 0,
        "data": {
            "errFiles": [],
            "succMap": {
                file_obj.name: url
            }
        }
    })