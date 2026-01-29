# AGENTS.md - 智能编码指南

## 项目概述
Django 6.0.1 Web 应用，包含 8 个应用：`core`, `user_app`, `Github_trend`, `community`, `notifications`, `news`, `direct_messages`, `haystack`（全文检索）

## 🚀 构建和启动命令

### 启动三个必要服务
```bash
# 终端1：启动Django开发服务器
python manage.py runserver

# 终端2：启动Celery Worker（执行异步任务）
celery -A myweb worker -l info

# 终端3：启动Celery Beat（定时任务调度器）
celery -A myweb beat -l info
```

### 运行测试
```bash
# 运行所有测试
python manage.py test

# 运行指定应用测试
python manage.py test user_app
python manage.py test core
python manage.py test community
python manage.py test tasks
python manage.py test direct_messages
python manage.py test notifications

# 运行单个测试（完整路径）
python manage.py test user_app.tests.YourTestCase.test_method_name

# 详细输出模式
python manage.py test --verbosity=2

# 调试单个测试（遇到错误时进入 pdb）
python manage.py test --debug-mode

# 运行指定测试文件
python manage.py test user_app.tests
```

### 开发命令
```bash
# 创建迁移
python manage.py makemigrations [app_name]

# 应用迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# Django Shell
python manage.py shell

# 搜索索引重建（Haystack）
python manage.py rebuild_index

# 查看SQL（调试用）
python manage.py sqlmigrate [app_name] [migration_number]
```

## 📐 代码风格指南

### Imports（导入顺序）
```python
# 1. 标准库
import os
import uuid
from datetime import timedelta

# 2. 第三方库
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.utils import timezone

# 3. 本地导入
from .models import CustomUser, Task
from .forms import TaskCreateForm
from notifications.models import Notification
```

### 命名规范
- **类名**: PascalCase (`CustomUser`, `EmailBackend`, `GitHubService`, `PostListView`)
- **函数/方法**: snake_case (`user_avatar_path`, `register`, `get_unread_count`)
- **变量**: snake_case (`cache_key`, `repos`, `language`)
- **常量**: UPPER_SNAKE_CASE (`API_URL`, `CACHES`, `TIMEOUT`)
- **模型类**: PascalCase，Meta类使用中文 `verbose_name`
- **URL名称**: lowercase_with_underscores (`password_reset_confirm`, `task_detail`)

### 文件上传模式（UUID重命名）
```python
import uuid
import os

def upload_path(instance, filename):
    """生成唯一文件名，防止冲突"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', filename)
```

### 认证与视图
- **自定义用户模型**: `user_app.CustomUser`（继承自 AbstractUser）
- **自定义认证后端**: `user_app.authentication.EmailBackend` - 支持用户名或邮箱登录
- **权限装饰器**: 使用 `@login_required` 保护视图
- **消息提示**: 使用 `messages.success()`/`messages.error()` 提供用户反馈
- **Post/Redirect/Get模式**: 防止表单重复提交
- **返回**: 使用 `render()` 返回模板，传递 context 字典

### 表单与URL
- **表单**: 继承 Django Forms，在 Meta 中设置 `fields`，在 `__init__` 中添加 Bootstrap 类
- **URLs**: 使用 `app_name` 命名空间，类视图中使用 `reverse_lazy()`
- **路由**: 使用 `path()` 配置命名路由

### 模型设计
```python
class Task(models.Model):
    """任务模型"""
    title = models.CharField('任务标题', max_length=100)
    content = models.TextField('任务详情')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='发起人')
    is_active = models.BooleanField('是否启用', default=True)
    
    class Meta:
        verbose_name = '任务'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"[{self.get_status_display()}] {self.title}"
```

### 错误处理
```python
# 外部API调用
try:
    response = requests.get(api_url)
    response.raise_for_status()
    data = response.json()
except requests.RequestException as e:
    print(f"API请求失败: {e}")
    return []

# 数据库查询
try:
    user = User.objects.get(pk=user_id)
except User.DoesNotExist:
    return None
except User.MultipleObjectsReturned:
    # 使用 first() 避免异常
    return User.objects.filter(pk=user_id).first()
```

### 缓存使用
```python
from django.core.cache import cache

# 生成唯一缓存键
cache_key = f"trends_{language}_{period}_{page}"

# 检查缓存
data = cache.get(cache_key)
if data:
    return data

# 执行昂贵操作
data = fetch_from_api()

# 存入缓存（TTL: 300秒 = 5分钟）
cache.set(cache_key, data, 300)
return data
```

### 环境变量
```python
from dotenv import load_dotenv
import os

load_dotenv()

# 获取环境变量
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
```

### 数据库查询
```python
# 使用 get_user_model() 而非直接导入 User
from django.contrib.auth import get_user_model
User = get_user_model()

# 使用 Q 对象进行 OR 查询
users = User.objects.filter(
    Q(username__icontains=query) | 
    Q(email__icontains=query) |
    Q(nickname__icontains=query)
)

# 使用 select_related/prefetch_related 避免N+1查询
tasks = Task.objects.select_related('creator').prefetch_related('participants')

# 排序
users = User.objects.filter(...).order_by('-created_at')
```

### 权限系统
```python
# 用户身份判断
user = request.user
if user.status in ['student', 'alumni', 'faculty']:
    # 允许的操作
    pass

# 权限检查
if not user.can_publish_tasks():
    messages.error(request, "权限不足")
    return redirect('home')

# 检查好友关系
if target_user in user.get_friends():
    # 已是好友
    pass
```

### 奖励系统
```python
# 增加奖励
user.earn_rewards(coins=10, growth=50)

# 扣除金币
user.deduct_coins(amount=100)

# 接收金币（任务结算）
user.receive_coins(bounty=500)
```

### 邮件发送
```python
from django.core.mail import send_mail

# 异步发送邮件（使用线程）
import threading
def send_email_thread(subject, message, recipient_list):
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list, fail_silently=True)

threading.Thread(target=send_email_thread, args=(subject, message, [email])).start()
```

### 注释规范
- 使用中文注释
- 使用 emoji 标记重要内容（👈 重要注意，👇 新增开始，👆 新增结束）
- 注释简洁，说明"为什么"而非"是什么"
- 函数使用 docstring：`"""函数功能描述"""`

### 模板与Admin
```python
# 模板：模板在根目录的 templates/ 下
return render(request, 'user_app/profile.html', {'user': user})

# Admin：继承 UserAdmin，自定义 fieldsets
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'nickname', 'status', 'coins', 'level']
    fieldsets = UserAdmin.fieldsets + (
        ('扩展信息', {'fields': ('nickname', 'bio', 'avatar', 'student_id')}),
    )
```

### 响应式设计
- 移动端优先设计
- 使用 Bootstrap 栅格系统
- 断点：768px（平板）、375px（小屏手机）
- 移动端隐藏滚动条，使用 `overflow-y: auto`

### 动态功能
```javascript
// 动态倒计时
function updateTimer() {
    const distance = deadline - now;
    const days = Math.floor(distance / (1000 * 60 * 60 * 24));
    const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((distance % (1000 * 60)) / 1000);
    timer.innerHTML = `${days}天 ${hours}时 ${minutes}分 ${seconds}秒`;
}
setInterval(updateTimer, 1000);
```

## ⚙️ 配置说明
- Settings 模块: `myweb.settings`
- 数据库: SQLite3（开发），PostgreSQL（生产）
- 语言: `zh-hans`（简体中文）
- 时区: `Asia/Shanghai`（北京时间）
- Debug 模式: `True`（生产环境改为 False）
- 静态文件: `static/` 目录
- 媒体文件: `media/` 目录（用户上传）

## 🔄 特殊模式
- **邮箱作为用户名**: 自定义后端支持用户名或邮箱登录
- **UUID文件上传**: 防止用户头像命名冲突
- **缓存层**: 减少 GitHub API 调用
- **自定义用户模型**: 继承 AbstractUser，扩展字段（nickname, bio, avatar, email_verified）
- **服务层模式**: 提取外部 API 逻辑到服务类（如 `GitHubService`）
- **类视图**: 使用 `as_view()` 配合类视图，传递 `template_name` 参数

## 🧪 测试规范
- 每个 app 应有 `tests.py` 文件
- 使用 Django 的 `TestCase` 类
- 测试命名: `test_<功能>_<场景>`
- 使用 `setUp()` 创建测试数据
- 断言清晰，使用有意义的消息

## 🔒 安全规范
- 永远不要提交 `.env` 文件或敏感信息
- 使用 `@login_required` 保护需要认证的视图
- 验证用户权限（如 `request.user == task.creator`）
- 使用 `transaction.atomic()` 确保数据一致性
- 使用 `get_object_or_404()` 处理 404

## 📧 Celery 异步任务
- 使用 `@shared_task` 装饰器定义任务
- 配置 Redis 作为 broker（默认 `redis://127.0.0.1:6379/0`）
- 使用 `get_user_model()` 获取 User 模型
- 任务中使用 try-except 处理异常，返回 "Success" 或 "Failed"
- 邮件发送使用异步任务

## 🔍 Haystack 全文检索
- 使用 Whoosh 引擎，索引存储在 `whoosh_index/` 目录
- 创建 `search_indexes.py` 定义索引类
- 使用 `use_template=True` 从模板文件读取索引内容
- 运行 `python manage.py rebuild_index` 重建搜索索引
- 使用 `HAYSTACK_SIGNAL_PROCESSOR` 自动更新索引
