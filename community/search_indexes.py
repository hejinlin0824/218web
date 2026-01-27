from haystack import indexes
from .models import Post

class PostIndex(indexes.SearchIndex, indexes.Indexable):
    # document=True 表示这是主要搜索字段
    # use_template=True 表示具体的索引内容我们在一个 txt 模板里定义
    text = indexes.CharField(document=True, use_template=True)
    
    # 我们也可以索引其他字段用于过滤，比如作者、发布时间
    author = indexes.CharField(model_attr='author')
    pub_date = indexes.DateTimeField(model_attr='created_at')

    def get_model(self):
        return Post

    def index_queryset(self, using=None):
        """更新索引时使用的数据集"""
        return self.get_model().objects.all()