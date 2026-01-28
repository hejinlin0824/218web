from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model

# 获取 User 模型
User = get_user_model()

from .models import Task, TaskParticipant
from .forms import TaskCreateForm
from .tasks import send_task_invitation_emails
from notifications.models import Notification

# 1. 发布任务
@login_required
def task_create(request):
    # 权限检查：在读、毕业、导师、管理员可发布
    if not request.user.can_publish_tasks():
        messages.error(request, "权限不足：仅在读成员、校友或导师可发布任务。")
        return redirect('home')

    if request.method == 'POST':
        form = TaskCreateForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    task = form.save(commit=False)
                    task.creator = request.user
                    
                    # --- 逻辑分支：导师指令 vs 普通悬赏 ---
                    if task.task_type == 'faculty':
                        # 导师任务：强制 0 金币，状态直接为“进行中”
                        task.bounty = 0 
                        task.status = 'in_progress' 
                    else:
                        # 普通任务：扣除金币，状态默认为“招募中”
                        if task.bounty > 0:
                            request.user.deduct_coins(task.bounty)
                        task.status = 'open'
                            
                    task.save()

                    # --- 处理参与者 ---
                    invitees = form.cleaned_data['invitees']
                    participant_list = []
                    recipient_ids = [] # 用于发邮件
                    
                    for user in invitees:
                        # 状态判定：导师任务直接 'accepted'，普通任务 'invited'
                        initial_status = 'accepted' if task.task_type == 'faculty' else 'invited'
                        
                        participant_list.append(
                            TaskParticipant(task=task, user=user, status=initial_status)
                        )
                        recipient_ids.append(user.id)
                        
                        # 构建通知文案
                        verb = 'task_invite'
                        if task.task_type == 'faculty':
                            content = f"🚨 [导师指令] 指派给你的任务：{task.title}"
                        else:
                            content = f"邀请你参与悬赏任务：{task.title}"
                        
                        # 发送站内信
                        Notification.objects.create(
                            recipient=user,
                            actor=request.user,
                            verb=verb,
                            target_url=reverse('tasks:task_detail', args=[task.id]),
                            content=content
                        )
                    
                    # 批量写入数据库
                    TaskParticipant.objects.bulk_create(participant_list)
                    
                    # 触发异步邮件任务
                    send_task_invitation_emails.delay(task.id, recipient_ids)

                msg_type = "导师指令" if task.task_type == 'faculty' else "悬赏任务"
                messages.success(request, f"{msg_type}发布成功！已通知 {len(invitees)} 位成员。")
                return redirect('tasks:my_tasks')

            except Exception as e:
                messages.error(request, f"发布失败：{e}")
    else:
        form = TaskCreateForm(user=request.user)

    return render(request, 'tasks/task_form.html', {'form': form})

# 2. 我的任务列表
@login_required
def my_tasks(request):
    # Tab 1: 我发布的
    created_tasks = Task.objects.filter(creator=request.user).order_by('-created_at')
    
    # Tab 2: 我参与的 (被邀请 或 已接受)
    # 按更新时间排序，最近互动的排前面
    my_participations = TaskParticipant.objects.filter(
        user=request.user
    ).exclude(status__in=['rejected', 'quit']).select_related('task', 'task__creator').order_by('-updated_at')

    return render(request, 'tasks/my_tasks.html', {
        'created_tasks': created_tasks,
        'my_participations': my_participations
    })

# 3. 任务详情页
@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    # 获取当前用户的参与状态 (如果是参与者)
    participant_record = TaskParticipant.objects.filter(task=task, user=request.user).first()
    
    # 如果是创建者，获取所有参与者列表 (用于展示进度和结算)
    all_participants = None
    if request.user == task.creator:
        all_participants = task.participants.select_related('user').all()

    return render(request, 'tasks/task_detail.html', {
        'task': task,
        'participant_record': participant_record, 
        'all_participants': all_participants,     
        'is_creator': request.user == task.creator
    })

# 4. 处理邀请 (接受/拒绝/放弃)
@login_required
def handle_invite(request, pk, action):
    task = get_object_or_404(Task, pk=pk)
    record = get_object_or_404(TaskParticipant, task=task, user=request.user)
    
    # 🛑 拦截：如果是导师任务，禁止拒绝或退出
    if task.task_type == 'faculty' and action in ['reject', 'quit']:
        messages.error(request, "导师指派的任务无法拒绝或放弃，请联系导师沟通。")
        return redirect('tasks:task_detail', pk=pk)
    
    if task.status == 'closed':
        messages.error(request, "任务已结束，无法操作。")
        return redirect('tasks:task_detail', pk=pk)

    if action == 'accept':
        record.status = 'accepted'
        record.save()
        
        # 如果普通任务还在 Open 状态，有人接受后自动转为 In_Progress
        if task.status == 'open':
            task.status = 'in_progress'
            task.save()
            
        messages.success(request, "您已接受该任务！它将出现在您的日程提醒中。")
        
        # 通知发起人
        Notification.objects.create(
            recipient=task.creator,
            actor=request.user,
            verb='task_accept',
            target_url=reverse('tasks:task_detail', args=[task.id]),
            content=f"接受了你的任务：{task.title}"
        )

    elif action == 'reject':
        record.status = 'rejected'
        record.save()
        messages.info(request, "您已拒绝该任务邀请。")
        
    elif action == 'quit':
        record.status = 'quit'
        record.save()
        messages.warning(request, "您已退出该任务。")

    return redirect('tasks:task_detail', pk=pk)

# 5. 结算任务 (仅创建者)
@login_required
def settle_task(request, pk):
    task = get_object_or_404(Task, pk=pk, creator=request.user)
    
    if request.method == 'POST':
        winner_id = request.POST.get('winner_id')
        
        try:
            with transaction.atomic():
                if winner_id:
                    winner = User.objects.get(pk=winner_id)
                    # 1. 转账赏金 (仅当有赏金时)
                    if task.bounty > 0:
                        winner.receive_coins(task.bounty)
                    
                    task.winner = winner
                    
                    # 2. 发送获奖通知
                    content = f"恭喜！你在任务中被选为 MVP，获得 {task.bounty} 金币！" if task.bounty > 0 else "恭喜！你在导师任务中被选为 MVP！"
                    
                    Notification.objects.create(
                        recipient=winner,
                        actor=request.user,
                        verb='task_settle',
                        target_url=reverse('tasks:task_detail', args=[task.id]),
                        content=content
                    )
                
                # 3. 关闭任务
                task.status = 'closed'
                task.save()
                
            messages.success(request, "任务已成功结算并关闭！")
            
        except Exception as e:
            messages.error(request, f"结算失败：{e}")
            
    return redirect('tasks:task_detail', pk=pk)

# 👇👇👇 新增：删除/撤销任务 👇👇👇
@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    # 1. 权限检查：只有发起人能删
    if request.user != task.creator:
        messages.error(request, "你没有权限删除此任务。")
        return redirect('tasks:task_detail', pk=pk)
    
    # 2. 状态检查：已结束的任务能否删除？
    # 策略：如果已经 Closed (钱已分发)，则只删数据不退款（或者禁止删除，看你需求）
    # 这里我们允许删除任何任务，但只对未结束的任务退款
    
    try:
        with transaction.atomic():
            # 如果任务还没结束，且有悬赏金，退款给发起人
            if task.status != 'closed' and task.bounty > 0:
                request.user.receive_coins(task.bounty)
                messages.success(request, f"任务已撤销，预扣的 {task.bounty} 金币已退还。")
            else:
                messages.success(request, "任务记录已删除。")
            
            # 物理删除
            task.delete()
            
    except Exception as e:
        messages.error(request, f"删除失败：{e}")
        return redirect('tasks:task_detail', pk=pk)
        
    return redirect('tasks:my_tasks')