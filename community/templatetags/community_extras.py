import markdown
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import strip_tags

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