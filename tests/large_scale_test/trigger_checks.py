"""
触发检测脚本
按日期顺序检测晋级和保级触发事件
"""
import sys
import os
from datetime import date, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import app
from tests.large_scale_test.config import *
from tests.large_scale_test.utils import ProgressBar
from core.promotion_engine import check_all_employees_for_promotion
from core.challenge_engine import batch_check_challenges


class TriggerChecker:
    """触发事件检测器"""
    
    def __init__(self):
        self.trigger_log = []
        
    def run_checks(self):
        """执行所有日期的触发检测"""
        print("="*60)
        print("开始触发检测")
        print("="*60)
        print(f"检测时间范围: {START_DATE} - {END_DATE}")
        print()
        
        # 生成所有日期列表
        dates = []
        current = START_DATE
        while current <= END_DATE:
            dates.append(current)
            current += timedelta(days=1)
        
        print(f"总天数: {len(dates)}")
        progress = ProgressBar(len(dates), '检测进度')
        
        with app.app_context():
            for check_date in dates:
                self._check_single_date(check_date)
                progress.update()
        
        # 保存日志
        self._save_log()
        
        print("\n="*60)
        print("触发检测完成")
        print("="*60)
        print(f"总触发事件: {len(self.trigger_log)}")
        print(f"日志文件: {TRIGGER_LOG}")
    
    def _check_single_date(self, check_date: date):
        """检测单个日期的触发事件"""
        # 检测晋级（简化：只记录检测事件）
        try:
            check_all_employees_for_promotion()
            # 这个函数会自动创建晋级申请记录
            self.trigger_log.append({
                'date': check_date.isoformat(),
                'type': 'promotion_check',
                'action': 'executed'
            })
        except Exception as e:
            self.trigger_log.append({
                'date': check_date.isoformat(),
                'type': 'promotion_check',
                'action': 'error',
                'error': str(e)
            })
        
        # 检测降级/保级
        try:
            batch_check_challenges()
            # 这个函数会自动创建保级挑战记录
            self.trigger_log.append({
                'date': check_date.isoformat(),
                'type': 'challenge_check',
                'action': 'executed'
            })
        except Exception as e:
            self.trigger_log.append({
                'date': check_date.isoformat(),
                'type': 'challenge_check',
                'action': 'error',
                'error': str(e)
            })
    
    def _save_log(self):
        """保存触发日志"""
        import json
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(TRIGGER_LOG, 'w', encoding='utf-8') as f:
            json.dump(self.trigger_log, f, ensure_ascii=False, indent=2)


def main():
    """主函数"""
    checker = TriggerChecker()
    checker.run_checks()


if __name__ == '__main__':
    main()

