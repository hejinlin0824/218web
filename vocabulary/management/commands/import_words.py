import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
# 👇 引入 EbbinghausBatch 以便清理旧数据
from vocabulary.models import Word, UserWordProgress, EbbinghausBatch

class Command(BaseCommand):
    help = '暴力导入所有单词 (纯写入模式，不查重)'

    def handle(self, *args, **kwargs):
        # ==========================================
        # 1. 暴力清空旧数据 (防止数据爆炸)
        # ==========================================
        self.stdout.write(self.style.WARNING('正在清空旧数据...'))
        
        # 👇 新增：先清理艾宾浩斯批次，防止外键冲突
        EbbinghausBatch.objects.all().delete()
        
        UserWordProgress.objects.all().delete()
        Word.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('旧数据已清空，准备开始全新的导入。'))

        data_root = os.path.join(settings.BASE_DIR, 'data')
        
        # 文件夹名 -> 数据库Tag (level_tag)
        tasks = [
            ('CET4', 'CET4'),
            ('CET6', 'CET6'),
            ('托福', 'TOEFL'),
            ('TOEFL', 'TOEFL'), # 容错
            ('IELTS', 'IELTS'),
            ('雅思', 'IELTS'),   # 容错
            ('考研', 'KaoYan'),
            ('KaoYan', 'KaoYan') # 容错
        ]

        # 用于记录已处理过的文件夹，防止重复处理
        processed_paths = set()

        for folder_name, level_tag in tasks:
            folder_path = os.path.join(data_root, folder_name)
            
            # 路径检查与去重
            if not os.path.exists(folder_path):
                continue
            
            # 获取绝对路径进行去重判断，防止不同写法指向同一目录重复导入
            abs_path = os.path.abspath(folder_path)
            if abs_path in processed_paths:
                continue
            processed_paths.add(abs_path)

            self.stdout.write(f'🚀 正在扫描 {level_tag} (目录: {folder_name}) ...')
            
            json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
            json_files.sort()

            total_inserted = 0
            batch_list = [] # 批量插入缓存池

            for json_file in json_files:
                file_path = os.path.join(folder_path, json_file)
                # self.stdout.write(f'   📄 读取: {json_file}') # 注释掉减少刷屏
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data_list = json.load(f)
                        
                        for item in data_list:
                            word_text = item.get('headWord')
                            if not word_text: continue

                            # --- 数据提取逻辑 (保持你原版不动) ---
                            # book_id = item.get('bookId', '') # ❌ 原版这里可能获取为空
                            
                            word_rank = item.get('wordRank', 0)
                            word_content = item.get('content', {}).get('word', {}).get('content', {})
                            
                            # 音标
                            phone = word_content.get('usphone') or word_content.get('phone') or word_content.get('ukphone') or ""
                            if phone and not phone.strip().startswith('/'):
                                phone = f"/{phone.strip()}/"
                            
                            # 释义
                            trans_list = word_content.get('trans', [])
                            trans_arr = []
                            for t in trans_list:
                                pos = t.get('pos', '')
                                cn = t.get('tranCn', '')
                                if cn: trans_arr.append(f"{pos} {cn}")
                            meaning_str = "；".join(trans_arr)

                            # 例句
                            ex_en, ex_cn = "", ""
                            sentence_module = word_content.get('sentence', {})
                            if sentence_module:
                                sents = sentence_module.get('sentences', [])
                                if sents and len(sents) > 0:
                                    ex_en = sents[0].get('sContent', '')
                                    ex_cn = sents[0].get('sCn', '')

                            # --- 核心修改：直接实例化对象 ---
                            word_obj = Word(
                                word=word_text,
                                phonetic=phone,
                                meaning=meaning_str,
                                level=level_tag,   # 保持原版，用 tasks 里的 tag
                                
                                # 🔥🔥🔥 关键修改点 🔥🔥🔥
                                # 强制将 book_id 设置为 level_tag (如 'CET4')
                                # 确保网页点击 CET4 时能找到数据
                                book_id=level_tag, 
                                
                                word_rank=word_rank,
                                example_en=ex_en,
                                example_cn=ex_cn
                            )
                            batch_list.append(word_obj)

                            # 每 5000 个写入一次
                            if len(batch_list) >= 5000:
                                Word.objects.bulk_create(batch_list)
                                total_inserted += len(batch_list)
                                batch_list = [] # 清空池子
                                self.stdout.write(f'       ...已写入 {total_inserted} 条')

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ 错误 {json_file}: {e}'))

            # 处理剩余的
            if batch_list:
                Word.objects.bulk_create(batch_list)
                total_inserted += len(batch_list)
            
            self.stdout.write(self.style.SUCCESS(f'✅ {level_tag} 导入完成，共 {total_inserted} 个'))

        self.stdout.write(self.style.SUCCESS('🎉 所有数据全部暴力导入完成！'))