import requests
import os
import datetime

class GitHubService:
    API_URL = "https://api.github.com/search/repositories"
    
    def __init__(self):
        self.token = os.getenv('GITHUB_TOKEN')

    def get_headers(self):
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def fetch_trends(self, language='python', time_range='weekly', page=1):
        """
        支持分页和时间筛选的抓取函数
        :param language: 编程语言
        :param time_range: daily, weekly, monthly
        :param page: 页码
        """
        # 1. 计算日期范围
        days_map = {
            'daily': 1,
            'weekly': 7,
            'monthly': 30,
            'yearly': 365
        }
        days = days_map.get(time_range, 7) # 默认一周
        start_date = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        
        # 2. 构造查询语句
        # 如果 language 是 'all'，就不加 language 筛选
        if language == 'all':
            query = f"created:>{start_date}"
        else:
            query = f"created:>{start_date} language:{language}"

        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 12,  # 每页 12 个
            "page": page     # 动态页码
        }

        try:
            print(f"📡 API请求: Lang={language}, Time={time_range}, Page={page}")
            response = requests.get(
                self.API_URL, 
                headers=self.get_headers(), 
                params=params, 
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            items = data.get('items', [])
            
            clean_data = []
            for item in items:
                clean_data.append({
                    'name': item['name'],
                    'full_name': item['full_name'],
                    'description': item['description'],
                    'stars': item['stargazers_count'],
                    'url': item['html_url'],
                    'language': item['language'],
                    'avatar': item['owner']['avatar_url'],
                    'updated_at': item['updated_at'][:10] # 截取日期部分
                })
            
            return clean_data
            
        except requests.RequestException as e:
            print(f"❌ API 请求失败: {e}")
            return []

github_service = GitHubService()