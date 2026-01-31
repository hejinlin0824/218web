import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from vocabulary.models import Word

class Command(BaseCommand):
    help = '导入 CET4/CET6 单词数据'

    def handle(self, *args, **kwargs):
        # 你的数据文件夹路径
        data_root = os.path.join(settings.BASE_DIR, 'data')
        
        # 定义要遍历的目录和对应的等级标记
        tasks = [
            ('CET4', 'CET4'),
            ('CET6', 'CET6')
        ]

        for folder_name, level_tag in tasks:
            folder_path = os.path.join(data_root, folder_name)
            
            if not os.path.exists(folder_path):
                self.stdout.write(self.style.WARNING(f'文件夹不存在，跳过: {folder_path}'))
                continue

            self.stdout.write(f'🚀 开始扫描 {folder_name} ...')
            
            # 获取该目录下所有json文件
            json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
            
            total_count = 0
            new_objects = []

            for json_file in json_files:
                file_path = os.path.join(folder_path, json_file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        # 遍历文件中的每一个单词对象
                        for item in data:
                            try:
                                # 1. 提取单词拼写 (headWord)
                                word_text = item.get('headWord')
                                if not word_text:
                                    continue
                                
                                # 2. 根据你的结构深入提取内容
                                # 结构: item -> content -> word -> content
                                word_content = item.get('content', {}).get('word', {}).get('content', {})
                                
                                # 3. 提取音标 (usphone)
                                # 你的需求：words[0]["content"]["word"]["content"]["usphone"]
                                phone = word_content.get('usphone')
                                if not phone:
                                    # 如果没有美音，尝试取英音作为备选
                                    phone = word_content.get('ukphone', '')
                                
                                # 格式化音标，加上 //
                                if phone and not phone.startswith('/'):
                                    phone = f"/{phone}/"

                                # 4. 提取释义 (trans)
                                # trans 通常是一个列表: [{"pos": "n.", "tranCn": "苹果"}, ...]
                                trans_list = word_content.get('trans', [])
                                trans_str_list = []
                                for t in trans_list:
                                    pos = t.get('pos', '')      # 词性
                                    cn = t.get('tranCn', '')    # 中文
                                    trans_str_list.append(f"{pos} {cn}")
                                
                                meaning_str = "；".join(trans_str_list)

                                # 5. 存入待创建列表 (先去重)
                                # 为了性能，我们这里只做简单去重，通过数据库的 unique=True 保证最终唯一性
                                # 或者先查询是否存在
                                if not Word.objects.filter(word=word_text).exists():
                                    new_objects.append(Word(
                                        word=word_text,
                                        phonetic=phone,
                                        meaning=meaning_str,
                                        level=level_tag
                                    ))
                                    total_count += 1

                            except Exception as e:
                                print(f"解析单词出错: {word_text} - {e}")
                                continue

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'读取文件失败 {json_file}: {e}'))

            # 批量写入数据库 (每积累 1000 个写入一次，防止内存溢出)
            if new_objects:
                Word.objects.bulk_create(new_objects, ignore_conflicts=True)
                self.stdout.write(self.style.SUCCESS(f'✅ {level_tag}: 成功导入 {len(new_objects)} 个新单词'))
            else:
                self.stdout.write(f'{level_tag}: 没有新单词需要导入')

        self.stdout.write(self.style.SUCCESS('🎉 所有数据处理完毕！'))