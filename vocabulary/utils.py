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
        "phase_6": {"name": "7天后",  "delta": timedelta(days=7),      "tolerance": timedelta(hours=24)}, 
        "phase_7": {"name": "15天后", "delta": timedelta(days=15),     "tolerance": timedelta(hours=24)},
    }

    @staticmethod
    def get_or_create_today_batch(user, book_id, target_count=60):
        # 1. 参数清洗
        safe_book_id = str(book_id).strip()
        print(f"DEBUG [1] Start: User={user}, Book={safe_book_id}", flush=True)  
        
        today = timezone.localdate()
        
        # 2. 获取或创建批次
        batch, created = EbbinghausBatch.objects.get_or_create(
            user=user,
            book_id=safe_book_id,
            study_date=today
        )
        print(f"DEBUG [2] Batch Created? {created}. ID={batch.id}", flush=True)

        current_count = batch.words.count()
        print(f"DEBUG [3] Current words in batch: {current_count}", flush=True)
        
        # 3. 如果没满，尝试填充
        if current_count < target_count:
            needed = target_count - current_count
            
            # [A] 排除计划中的
            scheduled_qs = EbbinghausBatch.objects.filter(
                user=user, 
                book_id=safe_book_id
            ).values_list('words__id', flat=True)
            scheduled_ids = list(scheduled_qs)
            
            # [B] 排除已掌握的 (status > 0)
            learned_qs = UserWordProgress.objects.filter(
                user=user,
                word__book_id=safe_book_id,
                status__gt=0 
            ).values_list('word__id', flat=True)
            learned_ids = list(learned_qs)

            print(f"DEBUG [4] Filters -> Scheduled: {len(scheduled_ids)}, Learned: {len(learned_ids)}", flush=True)

            # [C] 检查总库存 (关键!)
            total_stock = Word.objects.filter(book_id=safe_book_id).count()
            print(f"DEBUG [5] Total words in DB for '{safe_book_id}': {total_stock}", flush=True)

            if total_stock == 0:
                print("❌ CRITICAL: 数据库里这本书一个词都没有！请检查导入脚本或book_id。", flush=True)

            # [D] 执行筛选
            new_words_qs = Word.objects.filter(book_id=safe_book_id)\
                .exclude(id__in=scheduled_ids)\
                .exclude(id__in=learned_ids)
            
            final_count = new_words_qs.count()
            print(f"DEBUG [6] Available new words: {final_count}", flush=True)
            
            if final_count > 0:
                # 随机取词
                # 注意：如果数据量极大，order_by('?') 可能会慢，但在几千词级别没问题
                selected_words = list(new_words_qs.order_by('?')[:needed])
                batch.words.add(*selected_words)
                print(f"DEBUG [7] Added {len(selected_words)} words to batch.", flush=True)
            else:
                print("⚠️ WARNING: 没有新词可选了！", flush=True)
        
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