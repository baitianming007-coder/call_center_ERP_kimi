"""
P3-11: 简单缓存实现
使用functools.lru_cache
"""
from functools import lru_cache
from datetime import datetime

@lru_cache(maxsize=100)
def cached_query(query_key, timestamp_hour):
    """缓存查询结果（按小时）"""
    pass

def get_cache_key():
    """获取当前小时的缓存键"""
    return datetime.now().strftime('%Y%m%d%H')

# 清除缓存
def clear_cache():
    cached_query.cache_clear()

