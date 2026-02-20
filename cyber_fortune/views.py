# cyber_fortune/views.py
import random
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import FortuneProfile, DailyBlessing
from .forms import FortuneProfileForm

# === 赛博话术库 ===
def get_fortune_text(score):
    if score >= 85:
        return random.choice([
            "【紫气东来】今日算力惊人，Bug 自动退散！实验一次成功，论文一投就中！",
            "【欧气爆棚】量子波动与你同频，今天写代码必定如有神助，简直是天选之子！",
            "【算力觉醒】灵感如泉涌！今天适合开启新项目或攻克核心难题，绝对顺风顺水。"
        ])
    elif score >= 50:
        return random.choice([
            "【潜龙在渊】运势平稳且绵长，适合攻克难题。今日流下的汗水，都在转化为明日的顶级 Paper。",
            "【稳中向好】服务器运行平稳，脑电波状态良好。按部就班地推进任务，定有收获。",
            "【星轨顺行】一切都在预料之中发展。适合整理思路、复习单词或优化现有代码。"
        ])
    else:
        return random.choice([
            "【否极泰来】系统检测到你的低谷期已结束！宇宙正在为你积攒一个巨大的 Surprise，好运即将触底大反弹！",
            "【蓄力状态】当前处于气运充能期。今天适宜养精蓄锐、读读文献，不要和 Bug 死磕，大招马上就绪！",
            "【触底反弹】根据赛博玄学定律，气运值的低谷往往伴随着灵感的爆发。放轻松，今天适合做一些创造性的思考！"
        ])

# === 赛博老黄历 (每日全服统一) ===
def get_cyber_almanac():
    today_seed = timezone.localdate().toordinal()
    random.seed(today_seed) # 用日期做种子，保证全天不变，全服统一
    
    good_pool = ["提交 PR", "跑模型", "写文档", "重构代码", "带薪摸鱼", "喝咖啡", "请教导师", "读 Paper"]
    bad_pool = ["删库", "拔电源", "强制重启", "发布新版", "与 PM 争论", "熬夜肝代码", "随便 Git Push"]
    
    good = random.sample(good_pool, 2)
    bad = random.sample(bad_pool, 2)
    
    # 恢复随机种子以免影响其他功能
    random.seed()
    return {"good": good, "bad": bad}

# === MBTI 专属运势 ===
def get_mbti_fortune(mbti_type):
    today_seed = timezone.localdate().toordinal()
    # 结合日期和MBTI做种子，每天不同，各MBTI不同
    random.seed(today_seed + sum(ord(c) for c in mbti_type))
    
    tips = [
        f"{mbti_type} 的你今天直觉敏锐，适合解决纠缠已久的逻辑 Bug。",
        f"发挥 {mbti_type} 的特长，今天在团队沟通中你将扮演关键的破局者。",
        f"宇宙频率提示 {mbti_type}，今天换个背景音乐，代码产出率提升 200%。",
        f"作为 {mbti_type}，今天的你容易陷入细节陷阱，记得适时跳出来看全局架构。"
    ]
    tip = random.choice(tips)
    random.seed()
    return tip

# === 星座计算器 ===
def get_zodiac(date):
    month, day = date.month, date.day
    zodiacs = [(1, 20, '水瓶座'), (2, 19, '双鱼座'), (3, 21, '白羊座'), (4, 20, '金牛座'),
               (5, 21, '双子座'), (6, 22, '巨蟹座'), (7, 23, '狮子座'), (8, 23, '处女座'),
               (9, 23, '天秤座'), (10, 24, '天蝎座'), (11, 23, '射手座'), (12, 22, '摩羯座')]
    for m, d, name in zodiacs:
        if month == m and day >= d: return name
        elif month == m + 1 and day < zodiacs[(month) % 12][1]: return name
    return '摩羯座'

# === 视图：祈福大厅 ===
@login_required
def fortune_index(request):
    if not hasattr(request.user, 'fortune_profile'):
        return redirect('cyber_fortune:init_profile')
    
    profile = request.user.fortune_profile
    current_month = timezone.now().strftime('%Y-%m')
    if profile.last_reset_month != current_month:
        profile.monthly_luck_score = 0
        profile.last_reset_month = current_month
        profile.save(update_fields=['monthly_luck_score', 'last_reset_month'])

    today = timezone.localdate()
    today_blessing = request.user.blessings.filter(bless_date=today).first()
    
    context = {
        'profile': profile,
        'today_blessing': today_blessing,
        'almanac': get_cyber_almanac(),
        'mbti_tip': get_mbti_fortune(profile.mbti)
    }
    return render(request, 'cyber_fortune/index.html', context)

# === 视图：初始化档案 ===
@login_required
def init_profile(request):
    if hasattr(request.user, 'fortune_profile'):
        return redirect('cyber_fortune:index')
        
    if request.method == 'POST':
        form = FortuneProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.zodiac = get_zodiac(profile.birth_date)
            profile.last_reset_month = timezone.now().strftime('%Y-%m')
            profile.save()
            return redirect('cyber_fortune:index')
    else:
        form = FortuneProfileForm()
    return render(request, 'cyber_fortune/init.html', {'form': form})

# === API：执行抽卡/祈福 ===
@login_required
def draw_blessing(request):
    if request.method != 'POST': return JsonResponse({'status': 'error'})
    if not hasattr(request.user, 'fortune_profile'): return JsonResponse({'status': 'error'})

    today = timezone.localdate()
    if request.user.blessings.filter(bless_date=today).exists():
        return JsonResponse({'status': 'error', 'msg': '今日已注入算力！'})

    score = random.randint(1, 100)
    fortune_text = get_fortune_text(score)

    DailyBlessing.objects.create(user=request.user, bless_date=today, score=score, fortune_text=fortune_text)

    profile = request.user.fortune_profile
    profile.monthly_luck_score += score
    profile.save(update_fields=['monthly_luck_score'])
    
    # 日常祈福给大奖励
    request.user.earn_rewards(coins=1, growth=2)

    return JsonResponse({'status': 'ok', 'score': score, 'text': fortune_text, 'total_monthly': profile.monthly_luck_score})

# === API：敲击木鱼 ===
@login_required
def click_muyu(request):
    if request.method != 'POST': return JsonResponse({'status': 'error'})
    profile = getattr(request.user, 'fortune_profile', None)
    if not profile: return JsonResponse({'status': 'error'})

    profile.muyu_clicks += 1
    profile.monthly_luck_score += 1 # 敲一次，月度气运+1
    profile.save(update_fields=['muyu_clicks', 'monthly_luck_score'])
    
    # 木鱼微奖励机制（每敲10下给点经验，防止滥刷，也可以不给）
    if profile.muyu_clicks % 20 == 0:
        request.user.earn_rewards(coins=0, growth=1)

    return JsonResponse({
        'status': 'ok', 
        'total_clicks': profile.muyu_clicks, 
        'total_monthly': profile.monthly_luck_score
    })