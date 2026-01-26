from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class EmailBackend(ModelBackend):
    """
    自定义认证后端：允许用户使用 邮箱 或 用户名 登录
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # 核心逻辑：去数据库查，username 等于传入值 OR email 等于传入值
            user = User.objects.get(Q(username=username) | Q(email=username))
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            # 万一（虽然我们设置了唯一）查到多个，为了安全拒绝登录
            return User.objects.filter(email=username).order_by('id').first()

        # 检查密码是否正确，以及用户是否被激活
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None