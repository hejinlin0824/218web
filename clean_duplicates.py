import json
import os

def check_files():
    base_dir = './data/CET4'
    files = [f for f in os.listdir(base_dir) if f.endswith('.json')]
    files.sort()

    print(f"📂 正在检查 {base_dir} 下的文件...\n")
    
    all_words = set()
    
    for f_name in files:
        path = os.path.join(base_dir, f_name)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 提取该文件里的所有单词
        words_in_file = set()
        for item in data:
            if 'headWord' in item:
                words_in_file.add(item['headWord'])
        
        print(f"📄 文件: {f_name}")
        print(f"   - 包含单词数: {len(words_in_file)}")
        
        # 检查重叠
        overlap = words_in_file.intersection(all_words)
        print(f"   - 与之前文件的重复词数: {len(overlap)}")
        
        if len(overlap) == len(words_in_file):
            print("   ⚠️ 警告: 这个文件的内容可能被前面的文件完全覆盖了！")
            
        all_words.update(words_in_file)
        print("-" * 30)

    print(f"\n📊 实际不重复的单词总数: {len(all_words)}")

if __name__ == '__main__':
    check_files()