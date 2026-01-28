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
    """
    社区首页：支持标签筛选、搜索、时间筛选
    """
    model = Post
    template_name = 'community/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        # 预加载作者和标签，统计评论数，防止 N+1 查询
        queryset = Post.objects.select_related('author').prefetch_related('tags').annotate(comment_count=Count('comments'))
        
        # 标签筛选
        tag_slug = self.request.GET.get('tag')
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)
            
        # 关键词搜索
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(content__icontains=query))
            
        # 时间筛选
        time_filter = self.request.GET.get('filter')
        now = timezone.now()
        if time_filter == 'today':
            queryset = queryset.filter(created_at__gte=now - timedelta(days=1))
        elif time_filter == 'week':
            queryset = queryset.filter(created_at__gte=now - timedelta(weeks=1))
        elif time_filter == 'month':
            queryset = queryset.filter(created_at__gte=now - timedelta(days=30))
            
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_filter'] = self.request.GET.get('filter', 'all')
        context['search_query'] = self.request.GET.get('q', '')
        
        tag_slug = self.request.GET.get('tag')
        if tag_slug:
            context['current_tag'] = get_object_or_404(Tag, slug=tag_slug)
            
        context['all_tags'] = Tag.objects.all()
        return context

# 2. 发布帖子视图
class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'community/post_form.html'
    success_url = reverse_lazy('community:post_list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)
        
        # 🎉 奖励机制：发帖
        # 奖励：20 成长值, 2 硬币
        self.request.user.earn_rewards(coins=2, growth=20)
        
        return response

# 3. 帖子详情视图 (包含评论逻辑)
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    # 检查当前用户是否已点赞帖子
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
                    # 扁平化处理：始终挂载到第一级评论下，但在内容中 @原作者
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

            # 🎉 奖励机制：主动评论
            # 奖励：5 成长值, 1 硬币
            request.user.earn_rewards(coins=1, growth=5)

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

# 4. 点赞帖子视图
@login_required
def like_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    if post.likes.filter(id=request.user.id).exists():
        # 取消点赞
        post.likes.remove(request.user)
        # 注意：取消点赞不扣除已获得的奖励，防止“负资产”体验
    else:
        # 添加点赞
        post.likes.add(request.user)
        
        # 🎉 奖励机制：被点赞
        # 只有当 点赞者 不是 作者本人 时才触发
        if post.author != request.user: 
            if not post.is_first_like_rewarded:
                # 🚀 首赞大奖：100 成长值, 5 硬币
                post.author.earn_rewards(coins=5, growth=100)
                # 标记已发放首赞奖励
                post.is_first_like_rewarded = True
                post.save(update_fields=['is_first_like_rewarded'])
            else:
                # 🐟 普通点赞：10 成长值, 2 硬币
                post.author.earn_rewards(coins=2, growth=10)

            # 发送通知
            Notification.objects.create(
                recipient=post.author,
                actor=request.user,
                verb='like',
                target_url=reverse('community:post_detail', args=[pk]),
                content='赞了你的帖子'
            )
        
    return HttpResponseRedirect(reverse('community:post_detail', args=[str(pk)]))

# 5. 点赞评论视图 (新增)
@login_required
def like_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    
    if comment.likes.filter(id=request.user.id).exists():
        comment.likes.remove(request.user)
    else:
        comment.likes.add(request.user)
        
        # 🎉 奖励机制：评论被点赞
        # 奖励：5 成长值, 1 硬币
        if comment.author != request.user:
            comment.author.earn_rewards(coins=1, growth=5)
            
            # (可选) 发通知：赞了你的评论
            Notification.objects.create(
                recipient=comment.author,
                actor=request.user,
                verb='like',
                target_url=reverse('community:post_detail', args=[comment.post.pk]) + f"#comment-{comment.id}",
                content='赞了你的评论'
            )
            
    # 跳回帖子详情页，并定位到该评论
    return HttpResponseRedirect(reverse('community:post_detail', args=[comment.post.pk]) + f"#comment-{comment.id}")

# 6. 图片上传视图 (Vditor 专用)
@login_required
@require_POST
def upload_image(request):
    if 'file[]' not in request.FILES:
        return JsonResponse({'msg': '没有检测到文件', 'code': 1})

    file_obj = request.FILES.get('file[]')
    
    # 后缀名校验
    if not file_obj.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
         return JsonResponse({'msg': '仅支持图片文件', 'code': 1})

    # 使用 UUID 重命名
    ext = file_obj.name.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    date_path = time.strftime("%Y%m")
    
    # 路径: media/posts/YYYYMM/uuid.ext
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'posts', date_path)
    
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    file_path = os.path.join(upload_dir, filename)
    
    with open(file_path, 'wb+') as f:
        for chunk in file_obj.chunks():
            f.write(chunk)
            
    url = f"{settings.MEDIA_URL}posts/{date_path}/{filename}"
    
    # 返回 Vditor 要求的 JSON 格式
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