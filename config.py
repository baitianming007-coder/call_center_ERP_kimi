"""
配置文件
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'call-center-secret-key-change-in-production'
    
    # 数据库配置
    DATABASE = os.path.join(BASE_DIR, 'data', 'callcenter.db')
    
    # Session 配置
    SESSION_COOKIE_NAME = 'callcenter_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 7200  # 2小时
    
    # 业务配置
    REVENUE_PER_ORDER = 170  # 收入单价：170元/单
    
    # 加密密钥（用于敏感信息加密）
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or b'call-center-encryption-key-32b!'
    
    # 分页配置
    PAGE_SIZE = 20
    
    # 日志配置
    LOG_LEVEL = 'INFO'


