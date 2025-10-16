#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置工作日
将测试期间的所有周日设置为假期
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入配置
from tests.small_scale_test.config import *

# 设置日志
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s')


def configure_workdays():
    """配置工作日"""
    logger.info("正在配置工作日...")
    
    db_path = os.path.join(BASE_DIR, DB_PATH)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 收集所有周日
    sundays = []
    current = START_DATE
    while current <= END_DATE:
        if current.weekday() == 6:  # 周日
            sundays.append(current)
        current += timedelta(days=1)
    
    logger.info(f"  找到 {len(sundays)} 个周日需要配置")
    
    # 批量插入
    configured = 0
    for sunday in sundays:
        date_str = sunday.strftime('%Y-%m-%d')
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO work_calendar (
                    calendar_date, is_workday, day_type, notes,
                    configured_by, configured_name
                ) VALUES (?, 0, 'weekend', '测试配置-周日', 1, 'admin')
            ''', (date_str,))
            configured += 1
        except Exception as e:
            logger.warning(f"  配置 {date_str} 失败: {str(e)}")
    
    conn.commit()
    conn.close()
    
    logger.info(f"✓ 工作日配置完成：{configured} 个周日已设为假期")
    return configured


if __name__ == '__main__':
    configure_workdays()

