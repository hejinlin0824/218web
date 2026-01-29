from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from .models import Task, TaskParticipant
from .tasks import auto_settle_expired_tasks
from core.models import LabClass

User = get_user_model()

class AutoSettleTasksTest(TestCase):
    def setUp(self):
        # 创建用户
        self.creator = User.objects.create_user(
            username='creator',
            email='creator@test.com',
            status='student',
            coins=100
        )
        
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            status='student',
            coins=0
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            status='student',
            coins=0
        )
        
        self.user3 = User.objects.create_user(
            username='user3',
            email='user3@test.com',
            status='student',
            coins=0
        )
        
        self.user4 = User.objects.create_user(
            username='user4',
            email='user4@test.com',
            status='student',
            coins=0
        )
        
        self.user5 = User.objects.create_user(
            username='user5',
            email='user5@test.com',
            status='student',
            coins=0
        )
        
        # 创建班级
        self.lab_class = LabClass.objects.create(
            name='测试班级',
            mentor=self.creator,
            description='测试班级描述'
        )
        self.lab_class.students.add(self.user1, self.user2, self.user3)
    
    def test_auto_settle_single_participant(self):
        """测试：单个参与者，悬赏给第一个人"""
        # 创建过期任务
        task = Task.objects.create(
            title='测试任务',
            content='测试内容',
            creator=self.creator,
            bounty=10,
            task_type='bounty',
            is_class_task=False,
            deadline=timezone.now() - timedelta(hours=1),
            status='in_progress'
        )
        
        # 创建参与者
        TaskParticipant.objects.create(
            task=task,
            user=self.user1,
            status='accepted'
        )
        
        # 执行自动结算
        result = auto_settle_expired_tasks()
        
        # 刷新数据
        task.refresh_from_db()
        self.user1.refresh_from_db()
        
        # 验证
        self.assertEqual(task.status, 'closed')
        self.assertEqual(self.user1.coins, 10)
        self.assertEqual(task.winner, self.user1)
        self.assertIn('自动结算了 1 个过期任务', result)
    
    def test_auto_settle_multiple_participants(self):
        """测试：多个参与者，悬赏给第一个人"""
        # 创建过期任务
        task = Task.objects.create(
            title='测试任务',
            content='测试内容',
            creator=self.creator,
            bounty=10,
            task_type='bounty',
            is_class_task=False,
            deadline=timezone.now() - timedelta(hours=1),
            status='in_progress'
        )
        
        # 创建参与者
        TaskParticipant.objects.create(
            task=task,
            user=self.user1,
            status='accepted'
        )
        TaskParticipant.objects.create(
            task=task,
            user=self.user2,
            status='accepted'
        )
        TaskParticipant.objects.create(
            task=task,
            user=self.user3,
            status='accepted'
        )
        
        # 执行自动结算
        result = auto_settle_expired_tasks()
        
        # 刷新数据
        task.refresh_from_db()
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        self.user3.refresh_from_db()
        
        # 验证：悬赏给第一个人
        self.assertEqual(task.status, 'closed')
        self.assertEqual(self.user1.coins, 10)
        self.assertEqual(self.user2.coins, 0)
        self.assertEqual(self.user3.coins, 0)
        self.assertEqual(task.winner, self.user1)
    
    def test_auto_settle_class_task_divisible(self):
        """测试：班级任务，悬赏可整除（10币给3人）"""
        # 创建过期班级任务
        task = Task.objects.create(
            title='班级任务',
            content='班级任务内容',
            creator=self.creator,
            bounty=10,
            task_type='bounty',
            is_class_task=True,
            deadline=timezone.now() - timedelta(hours=1),
            status='in_progress'
        )
        
        # 创建参与者（3人）
        TaskParticipant.objects.create(
            task=task,
            user=self.user1,
            status='accepted'
        )
        TaskParticipant.objects.create(
            task=task,
            user=self.user2,
            status='accepted'
        )
        TaskParticipant.objects.create(
            task=task,
            user=self.user3,
            status='accepted'
        )
        
        # 执行自动结算
        result = auto_settle_expired_tasks()
        
        # 刷新数据
        task.refresh_from_db()
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        self.user3.refresh_from_db()
        
        # 验证：每人3个币（10//3=3，余1）
        # 随机分配余数1给1个人
        total_coins = self.user1.coins + self.user2.coins + self.user3.coins
        self.assertEqual(task.status, 'closed')
        self.assertEqual(total_coins, 10)
        # 每个人至少3个币
        self.assertGreaterEqual(self.user1.coins, 3)
        self.assertGreaterEqual(self.user2.coins, 3)
        self.assertGreaterEqual(self.user3.coins, 3)
        # 总共只有一个人获得额外的1个币
        extra_coins = sum([
            1 if u.coins == 4 else 0 
            for u in [self.user1, self.user2, self.user3]
        ])
        self.assertEqual(extra_coins, 1)
    
    def test_auto_settle_class_task_remainder(self):
        """测试：班级任务，悬赏不可整除（4币给5人）"""
        # 创建过期班级任务
        task = Task.objects.create(
            title='班级任务',
            content='班级任务内容',
            creator=self.creator,
            bounty=4,
            task_type='bounty',
            is_class_task=True,
            deadline=timezone.now() - timedelta(hours=1),
            status='in_progress'
        )
        
        # 创建参与者（5人）
        TaskParticipant.objects.create(
            task=task,
            user=self.user1,
            status='accepted'
        )
        TaskParticipant.objects.create(
            task=task,
            user=self.user2,
            status='accepted'
        )
        TaskParticipant.objects.create(
            task=task,
            user=self.user3,
            status='accepted'
        )
        TaskParticipant.objects.create(
            task=task,
            user=self.user4,
            status='accepted'
        )
        TaskParticipant.objects.create(
            task=task,
            user=self.user5,
            status='accepted'
        )
        
        # 执行自动结算
        result = auto_settle_expired_tasks()
        
        # 刷新数据
        task.refresh_from_db()
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        self.user3.refresh_from_db()
        self.user4.refresh_from_db()
        self.user5.refresh_from_db()
        
        # 验证：4币给5人，4//5=0，余4
        # 4个人各得1个币，1个人得0个币
        total_coins = sum([u.coins for u in [self.user1, self.user2, self.user3, self.user4, self.user5]])
        self.assertEqual(task.status, 'closed')
        self.assertEqual(total_coins, 4)
        # 只有4个人有1个币，1个人0个币
        users_with_coins = [u for u in [self.user1, self.user2, self.user3, self.user4, self.user5] if u.coins == 1]
        self.assertEqual(len(users_with_coins), 4)
        users_without_coins = [u for u in [self.user1, self.user2, self.user3, self.user4, self.user5] if u.coins == 0]
        self.assertEqual(len(users_without_coins), 1)
    
    def test_auto_settle_class_task_zero_coins(self):
        """测试：班级任务，悬赏不足以分配（1币给3人）"""
        # 创建过期班级任务
        task = Task.objects.create(
            title='班级任务',
            content='班级任务内容',
            creator=self.creator,
            bounty=1,
            task_type='bounty',
            is_class_task=True,
            deadline=timezone.now() - timedelta(hours=1),
            status='in_progress'
        )
        
        # 创建参与者（3人）
        TaskParticipant.objects.create(
            task=task,
            user=self.user1,
            status='accepted'
        )
        TaskParticipant.objects.create(
            task=task,
            user=self.user2,
            status='accepted'
        )
        TaskParticipant.objects.create(
            task=task,
            user=self.user3,
            status='accepted'
        )
        
        # 执行自动结算
        result = auto_settle_expired_tasks()
        
        # 刷新数据
        task.refresh_from_db()
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        self.user3.refresh_from_db()
        
        # 验证：1币给3人，1//3=0，直接关闭任务，没人获得金币
        self.assertEqual(task.status, 'closed')
        self.assertEqual(self.user1.coins, 0)
        self.assertEqual(self.user2.coins, 0)
        self.assertEqual(self.user3.coins, 0)
    
    def test_auto_settle_no_bounty(self):
        """测试：无悬赏任务"""
        # 创建过期任务（无悬赏）
        task = Task.objects.create(
            title='测试任务',
            content='测试内容',
            creator=self.creator,
            bounty=0,
            task_type='bounty',
            is_class_task=False,
            deadline=timezone.now() - timedelta(hours=1),
            status='in_progress'
        )
        
        # 创建参与者
        TaskParticipant.objects.create(
            task=task,
            user=self.user1,
            status='accepted'
        )
        
        # 执行自动结算
        result = auto_settle_expired_tasks()
        
        # 刷新数据
        task.refresh_from_db()
        self.user1.refresh_from_db()
        
        # 验证：任务关闭，没人获得金币
        self.assertEqual(task.status, 'closed')
        self.assertEqual(self.user1.coins, 0)
    
    def test_auto_settle_no_participants(self):
        """测试：无参与者任务"""
        # 创建过期任务
        task = Task.objects.create(
            title='测试任务',
            content='测试内容',
            creator=self.creator,
            bounty=10,
            task_type='bounty',
            is_class_task=False,
            deadline=timezone.now() - timedelta(hours=1),
            status='open'
        )
        
        # 不创建参与者
        
        # 执行自动结算
        result = auto_settle_expired_tasks()
        
        # 刷新数据
        task.refresh_from_db()
        
        # 验证：任务关闭
        self.assertEqual(task.status, 'closed')
        self.assertIsNone(task.winner)
    
    def test_auto_settle_not_expired(self):
        """测试：未过期任务不结算"""
        # 创建未过期任务
        task = Task.objects.create(
            title='测试任务',
            content='测试内容',
            creator=self.creator,
            bounty=10,
            task_type='bounty',
            is_class_task=False,
            deadline=timezone.now() + timedelta(hours=1),
            status='in_progress'
        )
        
        # 创建参与者
        TaskParticipant.objects.create(
            task=task,
            user=self.user1,
            status='accepted'
        )
        
        # 执行自动结算
        result = auto_settle_expired_tasks()
        
        # 刷新数据
        task.refresh_from_db()
        self.user1.refresh_from_db()
        
        # 验证：任务未结算
        self.assertEqual(task.status, 'in_progress')
        self.assertEqual(self.user1.coins, 0)
        self.assertIn('自动结算了 0 个过期任务', result)
    
    def test_auto_settle_already_closed(self):
        """测试：已关闭任务不结算"""
        # 创建已关闭任务
        task = Task.objects.create(
            title='测试任务',
            content='测试内容',
            creator=self.creator,
            bounty=10,
            task_type='bounty',
            is_class_task=False,
            deadline=timezone.now() - timedelta(hours=1),
            status='closed'
        )
        
        # 创建参与者
        TaskParticipant.objects.create(
            task=task,
            user=self.user1,
            status='accepted'
        )
        
        # 执行自动结算
        result = auto_settle_expired_tasks()
        
        # 刷新数据
        task.refresh_from_db()
        self.user1.refresh_from_db()
        
        # 验证：任务保持关闭状态，没人获得金币
        self.assertEqual(task.status, 'closed')
        self.assertEqual(self.user1.coins, 0)
        self.assertIn('自动结算了 0 个过期任务', result)
