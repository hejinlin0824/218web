from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Count
from django.utils import timezone
from django.db import transaction  # ✅ 必须导入，否则重置功能会报错
import json
import random  # ✅ 必须导入，用于打乱单词顺序

from .models import Word, UserWordProgress, EbbinghausBatch
from .utils import EbbinghausManager

# ---------------------------------------------------
# 1. 页面视图 (Page Views)
# ---------------------------------------------------

@login_required
def index(request):
    """
    单词本主页 - 统计所有等级进度
    """
    user = request.user
    stats = {}
    
    # 支持的词书列表
    ALL_LEVELS = ['CET4', 'CET6', 'KaoYan', 'TOEFL', 'IELTS']
    
    for level in ALL_LEVELS:
        total = Word.objects.filter(book_id=level).count()
        
        # 统计已学 (status > 0)
        learned_count = UserWordProgress.objects.filter(
            user=user, 
            word__book_id=level, 
            status__gt=0 
        ).count()
        
        # 统计已斩 (status = 2)
        mastered_count = UserWordProgress.objects.filter(
            user=user, 
            word__book_id=level, 
            status=2
        ).count()
        
        # 计算进度
        progress = round((learned_count / total * 100), 1) if total > 0 else 0
        
        stats[level] = {
            'total': total,
            'learned': learned_count,
            'mastered': mastered_count,
            'progress': progress
        }
        
    return render(request, 'vocabulary/index.html', {'stats': stats})

@login_required
def practice(request):
    """
    练习页面 (拼写/英译汉/汉译英)
    """
    return render(request, 'vocabulary/practice.html')

@login_required
def mistake_book(request):
    """
    错题本页面
    """
    level = request.GET.get('level', 'CET4')
    mistakes = UserWordProgress.objects.filter(
        user=request.user, 
        is_mistake=True,
        word__book_id=level 
    ).select_related('word').order_by('-mistake_count')
    
    return render(request, 'vocabulary/mistake_book.html', {
        'mistakes': mistakes, 
        'level': level
    })

@login_required
def ebbinghaus_plan(request):
    """
    【艾宾浩斯计划表】
    展示每日学习批次及其复习状态
    逻辑更新：
    1. 增加顺序锁：上一级未完成，下一级即使时间到了也不会变红（Active）。
    2. 允许额外复习：所有复习节点（Phase 1-7）无论状态如何，均标记为 clickable=True。
    """
    book_id = request.GET.get('book', 'CET4') # 默认看四级
    
    # 获取该用户、该书的所有批次，按日期倒序
    batches = EbbinghausBatch.objects.filter(
        user=request.user, 
        book_id=book_id
    ).order_by('-study_date')
    
    # 预处理数据给模板
    batch_list = []
    
    for b in batches:
        # 获取各阶段状态
        phases = []
        
        # --- 节点 0: 首次学习 ---
        # 只要 first_completed_at 有值，就代表首次背完了（哪怕是部分结算）
        first_done = True if b.first_completed_at else False
        
        phases.append({
            'label': '首次',
            'done': first_done,
            'active': False, # 首次不存在“待复习”状态，要么做完了要么没做
            'class': 'success' if first_done else 'secondary',
            'desc': b.first_completed_at.strftime('%m-%d %H:%M') if b.first_completed_at else '未完成',
            'clickable': False # 首次学习通常在 "Start Learning" 入口，这里不让点
        })
        
        # --- 节点 1-7: 复习节点 ---
        # 获取所有配置的 key 并排序 (phase_1, phase_2 ...)
        sorted_keys = sorted(EbbinghausManager.CYCLES.keys(), key=lambda x: int(x.split('_')[1]))
        
        # 🔒 顺序锁标记：只有当“前一个阶段”完成了，当前阶段才有资格变红
        previous_stage_done = first_done 

        for key in sorted_keys:
            node_config = EbbinghausManager.CYCLES[key]
            node_data = b.review_status.get(key, {})
            
            is_done = node_data.get('done', False)
            due_str = node_data.get('due')
            
            is_active = False # 是否应该显示为红色（待办）
            status_class = "secondary" # 默认灰色
            
            if is_done:
                # 状态：已完成 (绿)
                status_class = "success"
                previous_stage_done = True # 解锁下一级
            
            elif due_str:
                # 状态：未完成，检查时间
                due_time = timezone.datetime.fromisoformat(due_str)
                now = timezone.now()
                tolerance = node_config['tolerance']
                
                # 判定条件：前置任务完成 AND 当前时间进入窗口 (应复习时间 - 容差 <= 现在)
                if previous_stage_done and now >= (due_time - tolerance):
                    is_active = True
                    status_class = "danger" # 红色 (待办)
                else:
                    status_class = "secondary" # 灰色 (未到时间 或 前置未完成)
                
                # 当前未完成，阻断下一级的自动激活
                previous_stage_done = False
            
            else:
                # 状态：数据异常或未初始化
                status_class = "secondary"
                previous_stage_done = False

            phases.append({
                'label': node_config['name'],
                'done': is_done,
                'active': is_active,
                'class': status_class,
                'key': key,
                'desc': node_data.get('name'),
                'clickable': True # 🔥 关键：复习节点永远允许点击（哪怕是灰的，进去算额外复习）
            })
            
        batch_list.append({
            'id': b.id,
            'date': b.study_date,
            'word_count': b.words.count(),
            'total_reviews': b.total_review_count,
            'phases': phases
        })

    return render(request, 'vocabulary/ebbinghaus_plan.html', {
        'batches': batch_list,
        'current_book': book_id,
        'user_setting': request.user.enable_ebbinghaus
    })

@login_required
def batch_detail(request, batch_id):
    """
    【新增】批次详情页
    显示该批次的单词列表，以及 8 个节点的完成情况
    """
    batch = get_object_or_404(EbbinghausBatch, id=batch_id, user=request.user)
    
    # 1. 构造节点状态列表
    phases_status = []
    
    # 节点 0
    phases_status.append({
        'key': 'phase_0',
        'name': '首次',
        'done': True if batch.first_completed_at else False,
    })
    
    # 节点 1-7
    sorted_keys = sorted(EbbinghausManager.CYCLES.keys(), key=lambda x: int(x.split('_')[1]))
    for key in sorted_keys:
        node_config = EbbinghausManager.CYCLES[key]
        node_data = batch.review_status.get(key, {})
        
        phases_status.append({
            'key': key,
            'name': node_config['name'],
            'done': node_data.get('done', False),
        })

    # 2. 获取该批次的所有单词
    words = batch.words.all()

    return render(request, 'vocabulary/ebbinghaus_detail.html', {
        'batch': batch,
        'words': words,
        'phases_status': phases_status
    })

# ---------------------------------------------------
# 2. API 接口 (JSON Response)
# ---------------------------------------------------

@login_required
def api_get_words(request):
    # 👇👇👇 调试代码 START 👇👇👇
    print("\n========== API CALL RECEIVED ==========")
    print(f"User: {request.user.username}")
    print(f"Params: {request.GET}")
    # 👆👆👆 调试代码 END 👆👆👆
    
    mode = request.GET.get('mode', 'learn') 
    # 强制去除可能存在的空格
    book_id = request.GET.get('level', 'CET4').strip()
    
    user = request.user
    words_data = []
    
    if mode == 'review':
        # --- 复习模式：基于艾宾浩斯批次 ---
        batch_id = request.GET.get('batch_id')
        if batch_id:
            batch = get_object_or_404(EbbinghausBatch, id=batch_id, user=user)
            
            # 1. 获取单词 QuerySet 并转为 List
            words_qs = list(batch.words.all())
            
            # 2. 🔥 核心逻辑：强制打乱顺序
            random.shuffle(words_qs)
            
            for w in words_qs:
                words_data.append(serialize_word(w))
                
            return JsonResponse({
                'status': 'ok', 
                'data': words_data, 
                'batch_info': {
                    'id': batch.id, 
                    'count': len(words_qs)
                }
            })
        else:
             return JsonResponse({'status': 'error', 'msg': 'Missing batch_id'})

    else:
        # --- 学习模式：今日批次 ---
        count = int(request.GET.get('count', 60))
        
        # 调用 Manager 获取或创建今日批次
        batch = EbbinghausManager.get_or_create_today_batch(user, book_id, count)
        
        # 1. 获取单词 QuerySet 并转为 List
        words_qs = list(batch.words.all())
        
        # 2. 🔥 核心逻辑：强制打乱顺序
        # 即使是同一个批次，每次进来学习时顺序也会不同
        random.shuffle(words_qs)
        
        for w in words_qs:
            words_data.append(serialize_word(w))
            
        return JsonResponse({
            'status': 'ok', 
            'data': words_data,
            'batch_info': {
                'id': batch.id,
                'is_full': len(words_qs) >= count
            }
        })

@login_required
@require_POST
def api_finish_batch(request):
    """
    批次完成结算接口 (支持部分结算)
    """
    try:
        data = json.loads(request.body)
        batch_id = data.get('batch_id')
        # 👇 新增：获取前端传来的“已学单词ID列表”
        learned_ids = data.get('learned_ids', []) 
        
        if not batch_id:
            return JsonResponse({'status': 'error', 'msg': 'Missing batch_id'})
            
        batch = get_object_or_404(EbbinghausBatch, id=batch_id, user=request.user)
        
        # 👇👇👇 新增逻辑：处理中途退出的情况 👇👇👇
        # 如果前端传了 learned_ids，说明用户可能只学了一部分就想结算
        if learned_ids:
            # 1. 获取当前批次里的所有单词
            current_words = list(batch.words.values_list('id', flat=True))
            
            # 2. 找出那些“在批次里”但“不在已学列表”里的词 (即没背的词)
            # 注意：learned_ids 需要转 int
            learned_ids_int = [int(i) for i in learned_ids]
            unlearned_ids = [wid for wid in current_words if wid not in learned_ids_int]
            
            # 3. 将没背的词从批次中移除 (它们会回到词库池，下次被选出)
            if unlearned_ids:
                batch.words.remove(*unlearned_ids)
                print(f"用户中途结算：移除了 {len(unlearned_ids)} 个未背单词，保留 {len(learned_ids)} 个")

        # 调用 Manager 进行判定 (初始化复习表、标记首次完成)
        is_valid_checkin, msg, next_due = EbbinghausManager.check_and_update_status(batch)
        
        return JsonResponse({
            'status': 'ok',
            'valid_checkin': is_valid_checkin,
            'msg': msg,
            'next_due': next_due,
            'total_reviews': batch.total_review_count,
            'actual_count': batch.words.count() # 返回实际保留的数量
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})

@login_required
@require_POST
def api_reset_book_progress(request):
    """
    【新增】重置指定词书的学习进度
    """
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        
        if not book_id:
            return JsonResponse({'status': 'error', 'msg': 'Missing book_id'})
            
        # 使用事务确保删除操作的原子性
        with transaction.atomic():
            # 1. 删除该词书的艾宾浩斯批次
            EbbinghausBatch.objects.filter(
                user=request.user, 
                book_id=book_id
            ).delete()
            
            # 2. 删除该词书的单词学习进度 (UserWordProgress)
            # 注意：UserWordProgress 关联的是 Word，Word 里面有 book_id
            UserWordProgress.objects.filter(
                user=request.user, 
                word__book_id=book_id
            ).delete()
            
        return JsonResponse({'status': 'ok', 'msg': f'已重置 {book_id} 的所有进度'})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})

@login_required
@require_POST
def api_submit_result(request):
    """
    提交单个单词结果 (用于统计词频/错题)
    """
    try:
        data = json.loads(request.body)
        word_id = data.get('word_id')
        is_correct = data.get('is_correct')
        
        word = get_object_or_404(Word, pk=word_id)
        p, created = UserWordProgress.objects.get_or_create(user=request.user, word=word)
        
        if is_correct:
            if p.status == 0: 
                p.status = 1 
            # 答对奖励
            request.user.earn_rewards(coins=1, growth=2)
        else:
            p.mistake_count += 1
            p.is_mistake = True
            p.status = 1 
        
        p.save()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})

@login_required
@require_POST
def api_toggle_setting(request):
    """
    切换设置开关
    """
    try:
        data = json.loads(request.body)
        key = data.get('key')
        val = data.get('value')
        
        if key == 'ebbinghaus_notify':
            request.user.enable_ebbinghaus = val
            request.user.save()
            return JsonResponse({'status': 'ok'})
            
        return JsonResponse({'status': 'error', 'msg': 'Unknown setting key'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})

@login_required
@require_POST
def api_kill_word(request):
    """
    斩单词 (移出错题本并标记为已掌握)
    """
    try:
        data = json.loads(request.body)
        p = get_object_or_404(UserWordProgress, user=request.user, word_id=data.get('word_id'))
        p.is_mistake = False
        p.status = 2
        p.save()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})

# ---------------------------------------------------
# 辅助函数
# ---------------------------------------------------

def serialize_word(w):
    return {
        'id': w.id,
        'word': w.word,
        'phonetic': w.phonetic,
        'meaning': w.meaning,
        'example_en': w.example_en,
        'example_cn': w.example_cn,
        'audio_url': f"http://dict.youdao.com/dictvoice?audio={w.word}&type=0"
    }