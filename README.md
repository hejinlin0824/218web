# Web 218 DSSG Lab 实验室管理系统

## 📋 项目简介

这是一个基于 Django 6.0.1 开发的实验室综合管理系统，包含用户管理、社区论坛、任务悬赏、私信通知、学术展示等功能。

**技术栈：**
- Django 6.0.1 (Web框架)
- Celery + Redis (异步任务)
- Whoosh (全文检索)
- SQLite3 (开发数据库)
- Bootstrap 5 (前端框架)
- Vditor (Markdown编辑器)

## 🚀 快速启动

### 前置要求

1. Python 3.8+
2. Redis 服务器
3. 依赖包安装

```bash
# 安装依赖
pip install -r requirements.txt
```

### 环境配置

1. 复制并配置环境变量文件（`.env`）：

```env
# 邮件配置
EMAIL_HOST=smtp.qq.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@qq.com
EMAIL_HOST_PASSWORD=your_smtp_password

# Redis配置（用于Celery）
REDIS_URL=redis://127.0.0.1:6379/0
```

### 启动项目

项目需要**同时启动三个服务**：

```bash
# 终端1：启动Django开发服务器
python manage.py runserver

# 终端2：启动Celery Worker（执行异步任务）
celery -A myweb worker -l info

# 终端3：启动Celery Beat（定时任务调度器）
celery -A myweb beat -l info
```

### 访问地址

- 主页：http://127.0.0.1:8000/
- 管理后台：http://127.0.0.1:8000/admin/

## 📁 项目结构

```
218web/
├── myweb/                    # 项目配置目录
│   ├── settings.py           # Django配置文件
│   ├── urls.py               # 主路由配置
│   ├── celery.py             # Celery配置（定时任务）
│   ├── wsgi.py               # WSGI服务器配置
│   └── asgi.py               # ASGI服务器配置
│
├── templates/                # 全局模板目录
│   ├── base.html             # 基础模板
│   ├── index.html            # 主页模板
│   └── includes/             # 公共模板片段
│       └── side_nav.html     # 侧边栏导航
│
├── static/                   # 静态文件目录
├── media/                    # 媒体文件目录（用户上传）
│   ├── avatars/              # 用户头像
│   └── posts/                # 帖子图片
│
├── user_app/                 # 用户管理应用
├── community/                # 社区论坛应用
├── tasks/                    # 任务管理应用
├── direct_messages/          # 私信应用
├── notifications/            # 通知系统应用
├── news/                     # 新闻公告应用
├── Github_trend/             # GitHub趋势应用
├── core/                     # 核心功能应用
├── haystack/                 # 全文检索（第三方）
└── db.sqlite3                # SQLite数据库
```

## 📚 应用详细说明

### 1. user_app（用户管理）

**功能模块：用户注册、登录、个人资料、好友关系、权限管理**

#### 文件结构
```
user_app/
├── models.py                 # 用户模型
├── views.py                  # 视图函数
├── forms.py                  # 表单定义
├── urls.py                   # 路由配置
├── authentication.py         # 自定义认证后端
└── templates/user_app/       # 模板目录
```

#### models.py - 数据模型

**CustomUser（自定义用户模型）**
- 继承自 `AbstractUser`
- 扩展字段：
  - `nickname` - 昵称
  - `bio` - 个人简介
  - `avatar` - 头像（UUID命名）
  - `email_verified` - 邮箱是否已验证
  - `status` - 身份状态（newbie/student/alumni/faculty/admin）
  - `student_id` - 学号
  - `coins` - 金币（虚拟货币）
  - `growth` - 成长值（经验值）
  - `level` - 用户等级（根据成长值自动计算）
- 关系：
  - `following` - 关注的人
  - `followers` - 粉丝
  - `created_tasks` - 发布的任务
  - `won_tasks` - 获胜的任务
- 方法：
  - `can_publish_tasks()` - 判断是否可发布任务
  - `earn_rewards(coins, growth)` - 增加奖励
  - `deduct_coins(amount)` - 扣除金币
  - `receive_coins(amount)` - 接收金币

**Friendship（好友关系）**
- `from_user` - 发起人
- `to_user` - 接收人
- `status` - 状态（pending/accepted/rejected）
- `created_at` - 创建时间

#### views.py - 视图函数详解

**1. register（注册）**
- 功能：处理用户注册
- 流程：
  1. 验证表单数据
  2. 检查用户名和邮箱是否已存在
  3. 生成UUID token
  4. 将用户数据存入缓存（24小时有效）
  5. 发送激活邮件
  6. 重定向到激活等待页面
- 模板：`register.html`

**2. activation_sent（激活邮件已发送）**
- 功能：提示用户去邮箱查收邮件
- 模板：`activation_sent.html`

**3. activate（账户激活）**
- 功能：处理激活链接
- 流程：
  1. 从缓存读取用户数据
  2. 检查用户名是否被抢注
  3. 创建用户并写入数据库
  4. 删除缓存
  5. 自动登录
  6. 发送欢迎邮件
- 模板：`activation_invalid.html`（激活失败）

**4. profile（个人中心）**
- 功能：查看和编辑个人资料
- 方法：GET/POST
- 模板：`profile.html`

**5. public_profile（公开资料页）**
- 功能：查看他人的公开资料
- 显示：
  - 用户信息
  - 发布的帖子
  - 关注/粉丝数量
  - 是否已关注
- 模板：`public_profile.html`

**6. follow_user（关注/取消关注）**
- 功能：关注或取消关注用户
- 流程：
  1. 检查是否关注自己
  2. 切换关注状态
  3. 发送关注通知
- 权限：`@login_required`

**7. following_list（关注列表）**
- 功能：查看用户关注的人
- 权限：`@login_required`
- 模板：`follow_list.html`

**8. followers_list（粉丝列表）**
- 功能：查看用户的粉丝
- 权限：`@login_required`
- 模板：`follow_list.html`

**9. search_users（搜索用户）**
- 功能：搜索用户
- 搜索范围：用户名、昵称、学号
- 权限：`@login_required`
- 限制：仅学生、校友、导师可使用（newbie权限不足）
- 模板：`search_users.html`

**10. add_friend（添加好友）**
- 功能：发送好友请求
- 流程：
  1. 检查用户权限（newbie禁止）
  2. 检查是否已是好友或已发送请求
  3. 创建好友关系（pending状态）
  4. 发送站内通知
  5. 发送邮件提醒
- 权限：`@login_required`

**11. friend_requests（好友请求列表）**
- 功能：查看待处理的好友请求
- 权限：`@login_required`
- 模板：`friend_requests.html`

**12. handle_friend_request（处理好友请求）**
- 功能：接受或拒绝好友请求
- 流程：
  1. 接受：更新状态为accepted，自动互相关注，发送通知
  2. 拒绝：删除请求，发送通知
- 权限：`@login_required`

**13. delete_friend（删除好友）**
- 功能：解除好友关系
- 流程：
  1. 删除好友关系记录
  2. 自动互相取关
- 权限：`@login_required`

#### 辅助函数

**send_email_thread（邮件发送线程）**
- 功能：在独立线程中发送邮件
- 参数：subject, message, recipient_list

**send_activation_email（发送激活邮件）**
- 功能：发送账户激活邮件
- 参数：request, email, token, username
- 链接有效期：24小时

**send_welcome_email（发送欢迎邮件）**
- 功能：发送注册成功欢迎邮件
- 参数：user

---

### 2. community（社区论坛）

**功能模块：帖子发布、评论回复、点赞、标签、搜索**

#### 文件结构
```
community/
├── models.py                 # 帖子、评论、标签模型
├── views.py                  # 视图函数
├── forms.py                  # 表单定义
├── urls.py                   # 路由配置
├── templatetags/             # 自定义模板标签
│   └── community_extras.py   # Markdown处理、智能时间显示
└── templates/community/       # 模板目录
```

#### models.py - 数据模型

**Post（帖子）**
- `title` - 标题
- `content` - 内容（Markdown格式）
- `author` - 作者（外键）
- `views` - 浏览量
- `created_at` - 创建时间
- `updated_at` - 更新时间
- `is_first_like_rewarded` - 是否已发放首赞奖励
- 关系：
  - `likes` - 点赞用户
  - `comments` - 评论
  - `tags` - 标签（多对多）

**Comment（评论）**
- `content` - 评论内容
- `post` - 所属帖子（外键）
- `author` - 评论作者（外键）
- `parent` - 父评论（自关联，支持嵌套）
- `created_at` - 创建时间
- 关系：
  - `likes` - 点赞用户
  - `replies` - 回复（子评论）

**Tag（标签）**
- `name` - 标签名称
- `slug` - URL友好标识
- `color` - 标签颜色（用于前端显示）

#### views.py - 视图函数详解

**1. PostListView（帖子列表）**
- 类型：基于类的视图（ListView）
- 功能：显示帖子列表
- 支持筛选：
  - 标签筛选（`?tag=slug`）
  - 关键词搜索（`?q=keyword`）
  - 时间筛选（`?filter=today/week/month`）
- 分页：每页10条
- 优化：使用 `select_related` 和 `prefetch_related` 防止N+1查询
- 模板：`post_list.html`

**2. PostCreateView（发布帖子）**
- 类型：基于类的视图（CreateView）
- 功能：发布新帖子
- 奖励：发帖获得2金币、20成长值
- 权限：`LoginRequiredMixin`
- 模板：`post_form.html`

**3. post_detail（帖子详情）**
- 类型：函数视图
- 功能：显示帖子详情和评论
- 支持评论：
  - 直接评论帖子
  - 回复评论（自动@原评论作者）
- 奖励：评论获得1金币、5成长值
- 浏览量统计：使用Session防刷
- 模板：`post_detail.html`

**4. like_post（点赞帖子）**
- 功能：点赞或取消点赞帖子
- 奖励：
  - 首赞大奖：100成长值、5金币
  - 普通点赞：10成长值、2金币
- 通知：发送点赞通知
- 权限：`@login_required`

**5. like_comment（点赞评论）**
- 功能：点赞或取消点赞评论
- 奖励：5成长值、1金币
- 通知：发送点赞通知
- 权限：`@login_required`

**6. upload_image（图片上传）**
- 功能：上传帖子图片（Vditor专用）
- 返回：JSON格式（符合Vditor要求）
- 存储路径：`media/posts/YYYYMM/uuid.ext`
- 权限：`@login_required`, `@require_POST`

#### templatetags/community_extras.py

**md_to_text（Markdown转纯文本）**
- 功能：将Markdown内容转换为纯文本
- 用途：帖子列表页显示摘要

**smart_time（智能时间显示）**
- 功能：人性化时间显示
- 规则：
  - 超过3天：显示完整日期（如：2026年1月29日）
  - 不超过3天：显示相对时间（如：1天3小时21分前）

---

### 3. tasks（任务管理）

**功能模块：任务发布、任务参与、任务结算、导师指令**

#### 文件结构
```
tasks/
├── models.py                 # 任务、任务参与者模型
├── views.py                  # 视图函数
├── forms.py                  # 表单定义
├── urls.py                   # 路由配置
├── tasks.py                  # Celery异步任务
└── templates/tasks/          # 模板目录
```

#### models.py - 数据模型

**Task（任务）**
- `title` - 任务标题
- `content` - 任务详情（Markdown格式）
- `creator` - 发起人（外键）
- `bounty` - 悬赏金币
- `task_type` - 任务类型（bounty/faculty）
- `status` - 状态（open/in_progress/closed）
- `deadline` - 截止时间
- `winner` - 获胜者（外键）
- `created_at` - 创建时间
- `updated_at` - 更新时间
- 关系：
  - `participants` - 参与者
- 方法：
  - `is_overdue` - 是否已过期

**TaskParticipant（任务参与者）**
- `task` - 关联任务（外键）
- `user` - 参与者（外键）
- `status` - 参与状态（invited/accepted/rejected/quit）
- `updated_at` - 更新时间
- 唯一约束：(task, user)

#### views.py - 视图函数详解

**1. task_create（发布任务）**
- 功能：发布新任务
- 权限：仅在读成员、校友或导师可发布
- 任务类型：
  - **导师指令（faculty）**：
    - 强制0金币
    - 状态直接为"in_progress"
    - 参与者状态自动为"accepted"
  - **悬赏任务（bounty）**：
    - 扣除发起人金币
    - 状态默认为"open"
    - 参与者状态为"invited"
- 流程：
  1. 验证表单
  2. 使用事务确保数据一致性
  3. 扣除金币（普通任务）
  4. 创建任务记录
  5. 批量创建参与者记录
  6. 发送站内通知
  7. 触发异步邮件任务
- 模板：`task_form.html`

**2. my_tasks（我的任务）**
- 功能：显示我发布的和我参与的任务
- Tab1：我发布的任务
- Tab2：我参与的任务（accepted状态）
- 模板：`my_tasks.html`

**3. task_detail（任务详情）**
- 功能：显示任务详情
- 显示：
  - 任务信息
  - 参与者列表（仅创建者可见）
  - 倒计时（实时动态）
- 模板：`task_detail.html`

**4. handle_invite（处理邀请）**
- 功能：接受、拒绝、放弃任务
- 操作：
  - accept：接受任务，普通任务自动转为in_progress
  - reject：拒绝任务邀请
  - quit：退出任务
- 限制：导师任务不可拒绝或退出
- 通知：通知发起人

**5. settle_task（结算任务）**
- 功能：任务结束并结算赏金
- 权限：仅创建者可操作
- 流程：
  1. 选择MVP
  2. 转账赏金
  3. 发送通知
  4. 关闭任务

**6. task_delete（删除/撤销任务）**
- 功能：删除任务
- 权限：仅创建者可操作
- 退款：未结束的任务退款赏金

#### tasks.py - 异步任务

**send_task_invitation_emails（发送任务邀请邮件）**
- 功能：异步批量发送任务邀请邮件
- 参数：task_id, user_ids
- 触发：发布任务时自动触发

---

### 4. direct_messages（私信系统）

**功能模块：收件箱、聊天室、临时会话、私信提醒**

#### 文件结构
```
direct_messages/
├── models.py                 # 消息模型
├── views.py                  # 视图函数
├── urls.py                   # 路由配置
├── tasks.py                  # Celery异步任务
└── templates/direct_messages/ # 模板目录
```

#### models.py - 数据模型

**Message（私信）**
- `sender` - 发送者（外键）
- `recipient` - 接收者（外键）
- `content` - 消息内容
- `timestamp` - 发送时间
- `is_read` - 是否已读
- `is_email_sent` - 是否已发送邮件提醒

#### views.py - 视图函数详解

**1. inbox（收件箱）**
- 功能：显示消息收件箱
- 分为两部分：
  - 我的好友：显示已添加的好友
  - 临时会话：显示有过消息往来但不是好友的用户
- 显示最后一条消息
- 实时轮询更新消息
- 响应式设计：移动端只显示一个区域（联系人列表或聊天区域）
- 模板：`inbox.html`

**2. chat_room（聊天室）**
- 功能：单对一聊天界面
- 支持AJAX实时发送消息
- 自动轮询新消息（2秒一次）
- 实时滚动到底部
- 阻止全局消息弹窗
- 响应式设计：
  - 固定高度：`calc(100vh - 60px)`（移动端）
  - 聊天区域最大高度：`calc(100vh - 180px)`
  - 头部和底部sticky定位
  - 触摸优化
- 模板：`chat_room.html`

**3. delete_conversation（删除会话）**
- 功能：删除临时会话记录
- 方法：物理删除消息

**4. delete_chat（清空聊天）**
- 功能：清空好友聊天记录
- 方法：物理删除消息

**5. send_message（发送消息）**
- 功能：快速发送消息（Inbox页面）
- 发送站内通知
- 通知跳转到Inbox页面并选中发送者

**6. get_new_messages（获取新消息）**
- 功能：AJAX API，获取指定发送者的新消息
- 参数：last_id（当前页面最后一条消息ID）
- 返回：JSON格式的新消息列表

#### tasks.py - 异步任务

**send_unread_message_reminders（发送未读消息提醒）**
- 功能：每隔60秒检查一次
- 规则：超过15分钟未读的消息，发送邮件提醒
- 流程：
  1. 查找未读、未提醒、15分钟前的消息
  2. 按接收者分组
  3. 批量发送邮件
  4. 标记消息为已提醒
- 定时配置：每60秒运行一次

---

### 5. notifications（通知系统）

**功能模块：站内通知、未读提醒**

#### 文件结构
```
notifications/
├── models.py                 # 通知模型
├── views.py                  # 视图函数
├── urls.py                   # 路由配置
├── tasks.py                  # Celery异步任务
├── context_processors.py     # 上下文处理器（未读数）
└── templates/notifications/   # 模板目录
```

#### models.py - 数据模型

**Notification（通知）**
- `recipient` - 接收者（外键）
- `actor` - 触发者（外键）
- `verb` - 动作类型
  - like（点赞）
  - comment（评论）
  - reply（回复）
  - follow（关注）
  - system（系统通知）
  - friend_request（好友请求）
  - friend_accept（通过好友）
  - friend_reject（拒绝好友）
  - task_invite（任务邀请）
  - task_accept（接受任务）
  - task_reject（拒绝任务）
  - task_settle（任务结算）
- `target_url` - 跳转链接
- `content` - 消息摘要
- `is_read` - 是否已读
- `created_at` - 创建时间

#### views.py - 视图函数详解

**1. notification_list（通知列表）**
- 功能：显示所有通知
- 按时间倒序排列
- 模板：`list.html`

**2. mark_read_and_redirect（标记已读并跳转）**
- 功能：点击通知后标记为已读并跳转到目标页面
- 权限：`@login_required`

**3. get_unread_count（获取未读数）**
- 功能：轻量级API，返回未读通知数量
- 用途：前端轮询，实时更新导航栏红点
- 返回：JSON格式 `{"count": 5}`
- 轮询间隔：3秒

#### context_processors.py

**unread_count（未读数上下文）**
- 功能：在所有模板中可用的 `unread_notification_count` 变量
- 用途：显示导航栏通知红点

---

### 6. news（新闻公告）

**功能模块：发布公告**

#### 文件结构
```
news/
├── models.py                 # 公告模型
├── views.py                  # 视图函数（暂未实现）
├── urls.py                   # 路由配置
└── templates/news/           # 模板目录
```

#### models.py - 数据模型

**Announcement（公告）**
- `title` - 公告标题
- `content` - 公告内容（支持Markdown）
- `is_top` - 是否置顶
- `created_at` - 创建时间

---

### 7. Github_trend（GitHub趋势）

**功能模块：显示GitHub项目趋势**

#### 文件结构
```
Github_trend/
├── models.py                 # 暂无模型
├── views.py                  # 视图函数
├── urls.py                   # 路由配置
├── services.py               # GitHub API服务
└── templates/Github_trend/   # 模板目录
```

#### services.py - GitHub服务

**GitHubService（GitHub API服务）**
- 功能：调用GitHub API获取项目趋势
- 缓存：5分钟
- 筛选参数：
  - language（编程语言）
  - period（时间周期：daily/weekly/monthly）
  - page（分页）

#### views.py - 视图函数详解

**index（趋势列表）**
- 功能：显示GitHub项目趋势
- 支持筛选：
  - 编程语言
  - 时间周期
  - 分页
- 缓存策略：5分钟
- 模板：`index.html`

---

### 8. core（核心功能）

**功能模块：主页、实验室介绍**

#### 文件结构
```
core/
├── models.py                 # 研究方向、发表论文模型
├── views.py                  # 视图函数
├── urls.py                   # 路由配置
└── templates/core/           # 模板目录
```

#### models.py - 数据模型

**ResearchTopic（研究方向）**
- `name` - 研究方向名称
- `description` - 描述

**Publication（发表论文）**
- `title` - 论文标题
- `authors` - 作者
- `journal` - 期刊/会议
- `year` - 发表年份
- `link` - 论文链接

#### views.py - 视图函数详解

**1. index（主页）**
- 功能：实验室门户主页
- 显示：
  - 最新公告（前5条）
  - 最新帖子（前6条）
  - 统计数据（用户数、帖子数、在线人数）
  - 任务日程提醒（登录用户）
- 模板：`index.html`

**2. lab_intro（实验室介绍）**
- 功能：实验室介绍页
- 显示：
  - 研究方向
  - 导师列表
  - 学生列表
  - 发表论文
- 模板：`intro.html`

---

### 9. haystack（全文检索）

**功能模块：基于Whoosh的全文检索**

#### 配置
- 搜索引擎：Whoosh
- 索引存储：`whoosh_index/`
- 自动更新索引：启用

#### 使用方法
1. 创建搜索索引文件：`search_indexes.py`
2. 重建索引：`python manage.py rebuild_index`
3. 搜索页面：`/search/`

---

## ⚙️ 配置说明

### myweb/settings.py 核心配置

**时区设置**
```python
TIME_ZONE = 'Asia/Shanghai'  # 北京时间
```

**语言设置**
```python
LANGUAGE_CODE = 'zh-hans'  # 简体中文
```

**数据库**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

**邮件配置**
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
```

**Celery配置**
```python
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/1'
CELERY_TIMEZONE = TIME_ZONE
```

**Haystack配置**
```python
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join(BASE_DIR, 'whoosh_index'),
    },
}
```

### myweb/celery.py 定时任务配置

```python
app.conf.beat_schedule = {
    'check-unread-messages-every-minute': {
        'task': 'direct_messages.tasks.send_unread_message_reminders',
        'schedule': 60.0,  # 每60秒运行一次
    },
}
```

## 🔄 定时任务

### 当前运行的定时任务

1. **私信提醒邮件**
   - 任务：`direct_messages.tasks.send_unread_message_reminders`
   - 频率：每60秒
   - 功能：检查超过15分钟未读的私信，发送邮件提醒

2. **未读通知邮件**
   - 任务：`notifications.tasks.check_unread_notifications`
   - 频率：每60秒
   - 功能：检查超过15分钟未读的通知，发送邮件提醒

## 🎨 前端技术

### 框架和库
- Bootstrap 5.3.0（UI框架）
- Bootstrap Icons（图标）
- Vditor（Markdown编辑器）
- Animate.css（动画）

### 响应式设计
- 移动优先设计
- 断点：768px（平板）、375px（小屏手机）、500px（键盘弹出）
- 触摸优化

### 自定义功能
- 动态倒计时（实时更新）
- 智能时间显示
- 实时轮询更新（通知、私信）
- 消息滚动到底部

## 📝 常用命令

### Django管理命令

```bash
# 启动开发服务器
python manage.py runserver

# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# Django Shell
python manage.py shell

# 重建搜索索引
python manage.py rebuild_index

# 运行测试
python manage.py test
```

### Celery命令

```bash
# 启动Worker
celery -A myweb worker -l info

# 启动Beat
celery -A myweb beat -l info

# 同时启动Worker和Beat（开发用）
celery -A myweb worker -B -l info
```

## 🔒 权限系统

### 用户身份（status字段）
- `newbie` - 新生（未录取）
- `student` - 在读学生
- `alumni` - 毕业校友
- `faculty` - 导师
- `admin` - 管理员

### 权限矩阵
| 功能 | newbie | student | alumni | faculty |
|------|--------|---------|--------|---------|
| 浏览内容 | ✅ | ✅ | ✅ | ✅ |
| 发帖 | ✅ | ✅ | ✅ | ✅ |
| 评论 | ✅ | ✅ | ✅ | ✅ |
| 搜索用户 | ❌ | ✅ | ✅ | ✅ |
| 添加好友 | ❌ | ✅ | ✅ | ✅ |
| 发布任务 | ❌ | ✅ | ✅ | ✅ |
| 拒绝导师任务 | ❌ | ❌ | ❌ | ✅ |

## 💰 奖励系统

### 成长值获取
- 注册：默认100成长值
- 发帖：+20
- 评论：+5
- 首赞被赞：+100
- 普通被赞：+10
- 评论被赞：+5

### 金币获取
- 发帖：+2
- 评论：+1
- 首赞被赞：+5
- 普通被赞：+2
- 评论被赞：+1
- 任务结算：根据任务赏金

### 等级系统
- 根据成长值自动计算等级
- 公式：`level = growth // 100 + 1`

## 📧 邮件功能

### 邮件类型
1. **账户激活邮件** - 注册时发送
2. **欢迎邮件** - 激成功后发送
3. **好友请求邮件** - 发送好友请求时发送
4. **任务邀请邮件** - 任务发布时异步发送
5. **私信提醒邮件** - 超过15分钟未读自动发送
6. **通知提醒邮件** - 超过15分钟未读自动发送

### 邮件配置
- SMTP服务器：QQ邮箱（smtp.qq.com）
- 端口：587（TLS）
- 发件人：用户配置的邮箱

## 🌐 部署建议

### 生产环境配置
1. 使用PostgreSQL替代SQLite
2. 使用Nginx + Gunicorn
3. 配置HTTPS（Let's Encrypt）
4. 设置DEBUG=False
5. 配置ALLOWED_HOSTS
6. 使用Redis作为缓存和Celery broker
7. 配置静态文件收集（collectstatic）
8. 配置媒体文件存储（CDN或对象存储）

### 性能优化
1. 使用select_related和prefetch_related防止N+1查询
2. 使用缓存（LocMemCache开发，Redis生产）
3. 异步任务处理耗时操作
4. 分页显示列表数据
5. 压缩静态文件
6. 使用CDN加速静态资源

## 🐛 常见问题

### 问题1：Celery任务不执行
**解决方案：**
1. 检查Redis是否运行：`redis-cli ping`
2. 检查Celery Worker是否启动
3. 检查Celery Beat是否启动

### 问题2：邮件发送失败
**解决方案：**
1. 检查.env文件中的邮件配置
2. 确认SMTP授权码是否正确
3. 检查防火墙是否阻止了587端口
4. 查看Django日志中的错误信息

### 问题3：搜索索引不更新
**解决方案：**
1. 重建索引：`python manage.py rebuild_index`
2. 检查HAYSTACK_SIGNAL_PROCESSOR是否启用
3. 检查whoosh_index目录权限

### 问题4：移动端显示异常
**解决方案：**
1. 强制刷新浏览器缓存
2. 检查@media断点是否正确
3. 使用Chrome DevTools移动端模拟调试

## 📄 License

MIT License

## 👥 贡献

欢迎提交Issue和Pull Request！

---

**维护者：DSSG Lab Team**
**更新日期：2026-01-29**
