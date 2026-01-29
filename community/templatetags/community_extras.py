import markdown
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter(name='md_to_text')
@stringfilter
def md_to_text(value):
    """
    将 Markdown 转换为纯文本，用于列表页摘要展示
    1. Markdown -> HTML
    2. HTML -> 去除标签的纯文本
    """
    if not value:
        return ""
    
    try:
        # 将 Markdown 转为 HTML
        html = markdown.markdown(value, extensions=['markdown.extensions.extra'])
        # 去除 HTML 标签，只留文本
        text = strip_tags(html)
        # 去除多余的空行和空格
        return " ".join(text.split())
    except Exception:
        return value

@register.filter(name='smart_time')
def smart_time(value):
    """
    智能时间显示：
    - 超过3天：显示完整日期（如：2026年1月29日）
    - 不超过3天：显示相对时间（如：1天3小时21分前）
    """
    if not value:
        return ""
    
    now = timezone.now()
    time_diff = now - value
    
    if time_diff >= timedelta(days=3):
        return value.strftime("%Y年%m月%d日")
    
    total_seconds = int(time_diff.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分")
    
    time_str = "".join(parts)
    return f"{time_str}前" if time_str else "刚刚"