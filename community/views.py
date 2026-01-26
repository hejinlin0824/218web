from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.http import HttpResponseRedirect
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import Post, Comment
from .forms import PostForm, CommentForm
# 引入通知模型
from notifications.models import Notification

# 1. 帖子列表视图
class PostListView(ListView):
    """帖子列表页：支持搜索、筛选、聚合统计"""
    model = Post
    template_name = 'community/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        # 预加载作者信息，并统计评论数
        queryset = Post.objects.select_related('author').annotate(comment_count=Count('comments'))

        # 处理搜索
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(content__icontains=query))

        # 处理时间筛选
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
        return context

# 2. 发布帖子视图
class PostCreateView(LoginRequiredMixin, CreateView):
    """发布帖子页"""
    model = Post
    form_class = PostForm
    template_name = 'community/post_form.html'
    success_url = reverse_lazy('community:post_list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

# 3. 帖子详情视图 (核心逻辑)
def post_detail(request, pk):
    """帖子详情页：处理展示 + 评论 + 嵌套回复 + 通知"""
    post = get_object_or_404(Post, pk=pk)
    
    # 检查点赞状态
    is_liked = False
    if request.user.is_authenticated:
        if post.likes.filter(id=request.user.id).exists():
            is_liked = True
            
    # 处理评论/回复提交
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('user_app:login')
            
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            
            # === 处理嵌套回复逻辑 ===
            parent_id = request.POST.get('parent_id')
            notification_recipient = None # 记录该给谁发通知

            if parent_id:
                try:
                    # 获取用户点击“回复”的那条评论 (可能是爹，也可能是儿子)
                    target_comment = Comment.objects.get(id=parent_id)
                    
                    if target_comment.parent:
                        # Case A: 用户在回复一个“子评论” (无限套娃场景)
                        # 策略：扁平化处理。把新评论挂在“爷爷”下面，但在内容里 @那个人
                        comment.parent = target_comment.parent
                        comment.content = f"回复 @{target_comment.author.nickname or target_comment.author.username}: {comment.content}"
                        notification_recipient = target_comment.author
                    else:
                        # Case B: 用户直接回复“根评论”
                        comment.parent = target_comment
                        notification_recipient = target_comment.author

                except Comment.DoesNotExist:
                    pass # 如果找不到父评论，就当普通评论处理
            else:
                # Case C: 直接评论帖子
                if post.author != request.user:
                    notification_recipient = post.author

            # 先保存评论，生成 ID
            comment.save()

            # === 发送通知 ===
            if notification_recipient and notification_recipient != request.user:
                # 判断动作类型
                verb = 'reply' if parent_id else 'comment'
                
                Notification.objects.create(
                    recipient=notification_recipient,
                    actor=request.user,
                    verb=verb,
                    # 锚点定位到新生成的这条评论
                    target_url=reverse('community:post_detail', args=[pk]) + f"#comment-{comment.id}",
                    content=comment.content[:50] # 截取前50字
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

    # 只获取顶级评论 (parent=None)，子评论通过模板里的 comment.replies.all 获取
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