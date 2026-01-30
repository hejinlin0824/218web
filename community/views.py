from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.urls import reverse, reverse_lazy
from django.db.models import Count, Q
from django.contrib import messages  # 👈 之前报错缺少的导入
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from .models import Post, Comment, Tag, Collection
from .forms import PostForm, CommentForm, CollectionForm

# ==================================================
# 帖子相关视图
# ==================================================

class PostListView(ListView):
    """
    社区首页：支持标签筛选、搜索、时间筛选
    🔥 核心修复：只显示公开的帖子
    """
    model = Post
    template_name = 'community/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        # 1. 基础查询：只选公开的帖子
        # 即使是作者本人，在公共广场也不应该看到自己的私密贴（私密贴应在个人中心看）
        queryset = Post.objects.filter(visibility='public')\
            .select_related('author')\
            .prefetch_related('tags')\
            .annotate(comment_count=Count('comments'))

        # 2. 标签筛选
        tag_slug = self.request.GET.get('tag')
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)
            
        # 3. 关键词搜索 (仅搜索公开内容)
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(content__icontains=query))
            
        # 4. 时间筛选
        time_filter = self.request.GET.get('filter')
        if time_filter:
            from django.utils import timezone
            from datetime import timedelta
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
            try:
                context['current_tag'] = Tag.objects.get(slug=tag_slug)
            except Tag.DoesNotExist:
                pass
            
        context['all_tags'] = Tag.objects.all()
        return context

class PostCreateView(LoginRequiredMixin, CreateView):
    """发布帖子"""
    model = Post
    form_class = PostForm
    template_name = 'community/post_form.html'
    success_url = reverse_lazy('community:post_list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)
        # 🎉 奖励：发帖 (20成长值, 2金币)
        self.request.user.earn_rewards(coins=2, growth=20)
        return response

class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """编辑帖子"""
    model = Post
    form_class = PostForm
    template_name = 'community/post_form.html'
    
    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '编辑帖子'
        return context
        
    def get_success_url(self):
        return reverse('community:post_detail', args=[self.object.pk])

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """删除帖子"""
    model = Post
    template_name = 'community/post_confirm_delete.html'
    success_url = reverse_lazy('community:post_list')

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author or self.request.user.is_superuser

def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    # 🛑 安全拦截：如果是私密贴，且当前用户不是作者，直接抛出 403 异常
    if post.visibility == 'private':
        if not request.user.is_authenticated or request.user != post.author:
            raise PermissionDenied("该内容仅作者可见")

    # 浏览量统计 (Session 防刷)
    session_key = f'viewed_post_{post.pk}'
    if not request.session.get(session_key):
        post.views += 1
        post.save(update_fields=['views'])
        request.session[session_key] = True

    # === 👇👇👇 修改开始：增加关注状态检查 👇👇👇 ===
    is_liked = False
    is_collected = False
    is_following = False # 👈 新增变量
    user_collections = []

    if request.user.is_authenticated:
        # 1. 检查点赞
        if post.likes.filter(id=request.user.id).exists():
            is_liked = True
        
        # 2. 检查收藏
        user_collections = request.user.collections.all()
        if user_collections.filter(posts=post).exists():
            is_collected = True

        # 3. 检查关注 (包括好友自动互关的情况，因为好友也在 following 列表中)
        # 只要作者在我的关注列表中，is_following 就为 True
        if request.user != post.author:
            if request.user.following.filter(id=post.author.id).exists():
                is_following = True
    # === 👆👆👆 修改结束 👆👆👆 ===

    # 处理评论提交
    if request.method == 'POST' and 'content' in request.POST:
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
                if post.author != request.user:
                    notification_recipient = post.author

            comment.save()
            request.user.earn_rewards(coins=1, growth=5)

            # 发送通知
            from notifications.models import Notification
            if notification_recipient and notification_recipient != request.user:
                verb = 'reply' if parent_id else 'comment'
                Notification.objects.create(
                    recipient=notification_recipient,
                    actor=request.user,
                    verb=verb,
                    target_url=reverse('community:post_detail', args=[pk]) + f"#comment-{comment.id}",
                    content=comment.content[:50]
                )

            return redirect('community:post_detail', pk=pk)
    else:
        form = CommentForm()

    comments = post.comments.filter(parent=None).order_by('-created_at')

    context = {
        'post': post,
        'comments': comments,
        'form': form,
        'is_liked': is_liked,
        'is_collected': is_collected, # 👈 传递给模板
        'is_following': is_following, # 👈 记得把这个传入 context
        'user_collections': user_collections,
    }
    return render(request, 'community/post_detail.html', context)


# ==================================================
# 互动功能视图 (点赞/收藏)
# ==================================================

@login_required
def like_post(request, pk):
    """点赞帖子"""
    post = get_object_or_404(Post, pk=pk)
    
    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
        # 奖励逻辑
        if post.author != request.user:
            if not post.is_first_like_rewarded:
                post.author.earn_rewards(coins=5, growth=100)
                post.is_first_like_rewarded = True
                post.save(update_fields=['is_first_like_rewarded'])
            else:
                post.author.earn_rewards(coins=2, growth=10)
            
            # 通知
            from notifications.models import Notification
            Notification.objects.create(
                recipient=post.author,
                actor=request.user,
                verb='like',
                target_url=reverse('community:post_detail', args=[pk]),
                content='赞了你的帖子'
            )
        
    return redirect('community:post_detail', pk=pk)

@login_required
def like_comment(request, pk):
    """点赞评论"""
    comment = get_object_or_404(Comment, pk=pk)
    
    if comment.likes.filter(id=request.user.id).exists():
        comment.likes.remove(request.user)
    else:
        comment.likes.add(request.user)
        if comment.author != request.user:
            comment.author.earn_rewards(coins=1, growth=5)
            # 可选：通知
            
    return redirect(reverse('community:post_detail', args=[comment.post.pk]) + f"#comment-{comment.id}")

@login_required
def toggle_bookmark(request, pk):
    """
    快速收藏 (加入默认收藏夹)
    保留此功能作为快捷方式，或者兼容旧代码
    """
    post = get_object_or_404(Post, pk=pk)
    
    # 查找或创建默认收藏夹
    collection, created = Collection.objects.get_or_create(
        user=request.user,
        name="默认收藏夹"
    )
    
    if post in collection.posts.all():
        collection.posts.remove(post)
        messages.info(request, f"已从【{collection.name}】移除")
    else:
        collection.posts.add(post)
        if post.author != request.user:
            request.user.earn_rewards(coins=0, growth=2)
        messages.success(request, f"已加入【{collection.name}】")
        
    return redirect('community:post_detail', pk=pk)


# ==================================================
# 收藏夹管理视图 (修复 IntegrityError)
# ==================================================

@login_required
def my_collections(request):
    """
    查看和创建收藏夹
    """
    # 获取我的所有收藏夹
    collections = request.user.collections.annotate(post_count=Count('posts')).order_by('-updated_at')
    
    if request.method == 'POST':
        form = CollectionForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            
            # 🔥🔥🔥 核心修复：先检查是否存在同名收藏夹，防止 IntegrityError 崩溃 🔥🔥🔥
            if Collection.objects.filter(user=request.user, name=name).exists():
                # 方案 A: 添加表单错误（推荐，会在页面显示红字）
                form.add_error('name', f"您已经有一个名为“{name}”的收藏夹了，请换个名字。")
                # 方案 B: 也可以配合 messages 提示
                messages.error(request, "创建失败：收藏夹名称已重复。")
            else:
                # 名称不重复，安全保存
                col = form.save(commit=False)
                col.user = request.user
                col.save()
                messages.success(request, f"收藏夹【{col.name}】创建成功！")
                return redirect('community:my_collections')
    else:
        form = CollectionForm()

    return render(request, 'community/my_collections.html', {
        'collections': collections,
        'form': form
    })

@login_required
def delete_collection(request, pk):
    """删除收藏夹"""
    # 确保只能删除自己的
    collection = get_object_or_404(Collection, pk=pk, user=request.user)
    
    if request.method == 'POST':
        name = collection.name
        collection.delete()
        messages.success(request, f"收藏夹【{name}】已删除。")
        
    return redirect('community:my_collections')

@login_required
def collect_post(request, pk):
    """
    处理将帖子加入/移出指定收藏夹 (接收来自 Modal 的 POST 请求)
    """
    post = get_object_or_404(Post, pk=pk)
    
    if request.method == 'POST':
        # 获取用户选中的收藏夹 ID 列表 (checkbox)
        selected_ids = request.POST.getlist('collection_ids')
        
        # 1. 找出用户拥有的所有收藏夹
        user_cols = request.user.collections.all()
        
        # 2. 遍历处理 (批量添加/移除)
        added_count = 0
        
        for col in user_cols:
            # 如果该收藏夹被选中
            if str(col.id) in selected_ids:
                if post not in col.posts.all():
                    col.posts.add(post)
                    added_count += 1
            # 如果未被选中，但之前收藏了 -> 移除
            else:
                if post in col.posts.all():
                    col.posts.remove(post)
        
        messages.success(request, "收藏状态已更新")
        
        # 🎉 奖励：首次收藏他人帖子
        if added_count > 0 and post.author != request.user:
             request.user.earn_rewards(coins=0, growth=2)

    return redirect('community:post_detail', pk=pk)


# ==================================================
# 工具视图
# ==================================================

@login_required
def upload_image(request):
    """Vditor 图片上传"""
    if request.method == 'POST' and request.FILES.get('file[]'):
        file_obj = request.FILES.get('file[]')
        
        if not file_obj.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            return JsonResponse({'msg': '仅支持图片文件', 'code': 1})

        ext = file_obj.name.split('.')[-1]
        import uuid
        import time
        import os
        from django.conf import settings
        
        filename = f"{uuid.uuid4()}.{ext}"
        date_path = time.strftime("%Y%m")
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'posts', date_path)
        
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            
        file_path = os.path.join(upload_dir, filename)
        
        with open(file_path, 'wb+') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
                
        url = f"{settings.MEDIA_URL}posts/{date_path}/{filename}"
        
        return JsonResponse({
            "msg": "上传成功",
            "code": 0,
            "data": {
                "errFiles": [],
                "succMap": { file_obj.name: url }
            }
        })
        
    return JsonResponse({'msg': '上传失败', 'code': 1})

@login_required
@require_POST
def manage_collection_posts(request):
    """
    API: 管理收藏夹内的帖子 (批量删除 / 批量移动)
    """
    try:
        data = json.loads(request.body)
        action = data.get('action') # 'remove' or 'move'
        source_col_id = data.get('source_collection_id')
        post_ids = data.get('post_ids', [])
        target_col_id = data.get('target_collection_id') # 仅移动时需要

        # 1. 验证源收藏夹权限
        source_col = get_object_or_404(Collection, pk=source_col_id, user=request.user)
        
        # 2. 获取涉及的帖子
        posts_to_manage = Post.objects.filter(id__in=post_ids)
        
        if not posts_to_manage.exists():
            return JsonResponse({'status': 'error', 'msg': '未选择任何帖子'})

        if action == 'remove':
            # 批量移除
            source_col.posts.remove(*posts_to_manage)
            msg = f"已移除 {posts_to_manage.count()} 篇帖子"
            
        elif action == 'move':
            # 批量移动 (先加到新收藏夹，再从旧的移除)
            if not target_col_id:
                return JsonResponse({'status': 'error', 'msg': '目标收藏夹未指定'})
            
            target_col = get_object_or_404(Collection, pk=target_col_id, user=request.user)
            
            if source_col == target_col:
                return JsonResponse({'status': 'error', 'msg': '目标收藏夹不能与源收藏夹相同'})

            # 添加到新收藏夹
            target_col.posts.add(*posts_to_manage)
            # 从旧收藏夹移除
            source_col.posts.remove(*posts_to_manage)
            
            msg = f"已将 {posts_to_manage.count()} 篇帖子转移至【{target_col.name}】"
        
        else:
            return JsonResponse({'status': 'error', 'msg': '无效的操作'})

        return JsonResponse({'status': 'ok', 'msg': msg})

    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})

@login_required
@require_POST
def api_create_collection(request):
    """
    API: 快速创建收藏夹 (用于 Modal 内部)
    """
    try:
        data = json.loads(request.body)
        name = data.get('name')
        
        if not name:
            return JsonResponse({'status': 'error', 'msg': '名称不能为空'})
            
        if Collection.objects.filter(user=request.user, name=name).exists():
            return JsonResponse({'status': 'error', 'msg': '收藏夹名称已存在'})
            
        # 创建
        col = Collection.objects.create(
            user=request.user,
            name=name,
            is_public=True # 默认公开，或者你可以让前端传参
        )
        
        return JsonResponse({
            'status': 'ok',
            'collection': {
                'id': col.id,
                'name': col.name,
                'count': 0
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})