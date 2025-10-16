"""
数据库连接管理模块
"""
import sqlite3
import os
from flask import g
from config import Config


def get_db():
    """获取数据库连接"""
    if 'db' not in g:
        # 确保data目录存在
        os.makedirs(os.path.dirname(Config.DATABASE), exist_ok=True)
        
        g.db = sqlite3.connect(
            Config.DATABASE,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row  # 使结果可以通过列名访问
    return g.db


def close_db(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """初始化数据库表结构"""
    db = get_db()
    
    # 读取并执行 schema.sql
    with open('schema.sql', 'r', encoding='utf-8') as f:
        db.executescript(f.read())
    
    db.commit()


def query_db(query, args=(), one=False):
    """执行查询并返回结果"""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def execute_db(query, args=()):
    """执行更新/插入操作"""
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    return cur.lastrowid


