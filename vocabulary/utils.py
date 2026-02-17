from django.utils import timezone
from datetime import timedelta
from .models import EbbinghausBatch, Word, UserWordProgress

class EbbinghausManager:
    """
    艾宾浩斯遗忘曲线管理器 (业务逻辑层)
    """
    
    # 定义复习周期配置
    CYCLES = {
        "phase_1": {"name": "30分钟", "delta": timedelta(minutes=30), "tolerance": timedelta(minutes=15)},
        "phase_2": {"name": "12小时", "delta": timedelta(hours=12),   "tolerance": timedelta(hours=2)},
        "phase_3": {"name": "1天后",  "delta": timedelta(days=1),     "tolerance": timedelta(hours=12)},
        "phase_4": {"name": "2天后",  "delta": timedelta(days=2),     "tolerance": timedelta(hours=12)},
        "phase_5": {"name": "4天后",  "delta": timedelta(days=4),     "tolerance": timedelta(hours=12)},
        "phase_6": {"name": "7天后",  "delta": timedelta(days=7),     "tolerance": timedelta(days=24)},
        "phase_7": {"name": "15天后", "delta": timedelta(days=15),    "tolerance": timedelta(days=24)},
    }

    @staticmethod
    def get_or_create_today_batch(user, book_id, target_count=60):
        """
        获取或创建今日的学习批次
        """
        # 1. 参数清洗，防止有空格导致查不到
        safe_book_id = str(book_id).strip()
        
        today = timezone.localdate()
        
        # 2. 获取或创建批次
        batch, created = EbbinghausBatch.objects.get_or_create(
            user=user,
            book_id=safe_book_id,
            study_date=today
        )
        
        current_count = batch.words.count()
        print(f"\n[DEBUG Utils] Batch ID: {batch.id}, User: {user}, Book: '{safe_book_id}', Date: {today}")
        print(f"[DEBUG Utils] Current Words in Batch: {current_count}, Target: {target_count}")
        
        # 3. 如果没满，需要填充新词
        if current_count < target_count:
            needed = target_count - current_count
            
            # [A] 找出该用户、该本词书、所有历史批次中已经存在的单词ID
            used_word_ids = list(EbbinghausBatch.objects.filter(
                user=user, 
                book_id=safe_book_id
            ).values_list('words__id', flat=True))
            
            # [B] 查询新词
            # 这里的 filter 必须和 shell 里验证过的条件一致
            new_words_qs = Word.objects.filter(book_id=safe_book_id)\
                .exclude(id__in=used_word_ids)
            
            # 打印库存情况
            total_available = new_words_qs.count()
            print(f"[DEBUG Utils] Searching Word table for book_id='{safe_book_id}'")
            print(f"[DEBUG Utils] Words already learned/scheduled: {len(used_word_ids)}")
            print(f"[DEBUG Utils] Available new words to pick from: {total_available}")
            
            if total_available > 0:
                # 随机选取 needed 个
                selected_words = list(new_words_qs.order_by('?')[:needed])
                batch.words.add(*selected_words)
                print(f"[DEBUG Utils] Successfully added {len(selected_words)} new words to batch.")
            else:
                print(f"[DEBUG Utils] ⚠️ CRITICAL: No new words found for book_id='{safe_book_id}'!")
                # 尝试查询一下总数，看是不是 book_id 对不上
                total_in_db = Word.objects.filter(book_id=safe_book_id).count()
                print(f"[DEBUG Utils] Total words in DB with book_id='{safe_book_id}': {total_in_db}")

        return batch

    @staticmethod
    def init_schedule(batch, completion_time):
        schedule = {}
        for key, config in EbbinghausManager.CYCLES.items():
            due_time = completion_time + config['delta']
            schedule[key] = {
                "name": config['name'],
                "due": due_time.isoformat(),
                "done": False,
                "done_at": None,
                "notified": False
            }
        return schedule

    @staticmethod
    def check_and_update_status(batch):
        batch.total_review_count += 1
        now = timezone.now()
        
        if not batch.first_completed_at:
            batch.first_completed_at = now
            batch.review_status = EbbinghausManager.init_schedule(batch, now)
            batch.save()
            return True, "🎉 首次记忆完成！计划表已生成。", batch.review_status['phase_1']['due']

        status = batch.review_status
        target_phase = None
        
        sorted_keys = sorted(EbbinghausManager.CYCLES.keys(), key=lambda x: int(x.split('_')[1]))
        
        for key in sorted_keys:
            node = status.get(key)
            if node and not node['done']:
                target_phase = key
                break
        
        if not target_phase:
            batch.save()
            return False, "💪 所有计划节点已完成！", None

        node_config = EbbinghausManager.CYCLES[target_phase]
        node_data = status[target_phase]
        
        due_time = timezone.datetime.fromisoformat(node_data['due'])
        tolerance = node_config['tolerance']
        
        if now >= (due_time - tolerance):
            status[target_phase]['done'] = True
            status[target_phase]['done_at'] = now.isoformat()
            batch.save()
            
            next_due = None
            try:
                curr_idx = sorted_keys.index(target_phase)
                if curr_idx + 1 < len(sorted_keys):
                    next_key = sorted_keys[curr_idx + 1]
                    next_due = status[next_key]['due']
            except ValueError:
                pass
                
            return True, f"✅ 完成【{node_config['name']}】节点！", next_due
        else:
            batch.save()
            time_left = due_time - now
            hours = int(time_left.total_seconds() / 3600)
            return False, f"⚡️ 精神可嘉！但距离【{node_config['name']}】还有 {hours} 小时。", None