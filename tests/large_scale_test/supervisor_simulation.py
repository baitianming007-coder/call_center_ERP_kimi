"""
主管操作模拟脚本
模拟主管登录并执行审批操作
"""
import sys
import os
import random
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import requests
from tests.large_scale_test.config import *


BASE_URL = 'http://127.0.0.1:8080'


class SupervisorSimulator:
    """主管操作模拟器"""
    
    def __init__(self):
        self.sessions = {}  # 主管sessions
        self.operation_log = []
        
    def run_simulation(self):
        """执行主管操作模拟"""
        print("="*60)
        print("开始主管操作模拟")
        print("="*60)
        print()
        
        # 读取主管信息
        with open(EXPECTED_EVENTS_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
            supervisors = data.get('supervisors', [])
        
        # 为每个主管创建session
        print("步骤1: 主管登录...")
        for sup in supervisors:
            self._login_supervisor(sup)
        print(f"✓ {len(self.sessions)} 名主管已登录")
        print()
        
        # 处理晋级申请
        print("步骤2: 处理晋级申请...")
        self._process_promotions()
        print()
        
        # 处理保级挑战
        print("步骤3: 处理保级挑战...")
        self._process_challenges()
        print()
        
        # 保存操作日志
        self._save_log()
        
        print("="*60)
        print("主管操作模拟完成")
        print("="*60)
        print(f"总操作数: {len(self.operation_log)}")
        print(f"日志文件: {SUPERVISOR_LOG}")
    
    def _login_supervisor(self, supervisor: dict):
        """主管登录"""
        session = requests.Session()
        
        try:
            resp = session.post(f'{BASE_URL}/login', data={
                'username': supervisor['username'],
                'password': supervisor['password']
            }, timeout=5)
            
            if resp.status_code == 200:
                self.sessions[supervisor['username']] = session
                print(f"  ✓ {supervisor['username']} 登录成功")
            else:
                print(f"  ✗ {supervisor['username']} 登录失败")
        except Exception as e:
            print(f"  ✗ {supervisor['username']} 登录异常: {e}")
    
    def _process_promotions(self):
        """处理晋级申请"""
        if not self.sessions:
            print("  没有可用的主管session")
            return
        
        # 随机选择一个主管session
        session = list(self.sessions.values())[0]
        
        try:
            # 获取待处理的晋级申请
            resp = session.get(f'{BASE_URL}/manager/promotions', timeout=5)
            
            if resp.status_code == 200:
                # 简化处理：这里需要解析HTML或使用API
                # 实际应该从页面提取promotion_id并逐个处理
                print(f"  晋级申请页面访问成功")
                
                # 模拟操作分布
                operation_type = random.choices(
                    ['approve', 'reject', 'delay', 'ignore'],
                    weights=[0.80, 0.07, 0.10, 0.03]
                )[0]
                
                self.operation_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'type': 'promotion',
                    'operation': operation_type
                })
                
        except Exception as e:
            print(f"  处理晋级申请异常: {e}")
    
    def _process_challenges(self):
        """处理保级挑战"""
        if not self.sessions:
            print("  没有可用的主管session")
            return
        
        # 随机选择一个主管session
        session = list(self.sessions.values())[0]
        
        try:
            # 获取待处理的保级挑战
            resp = session.get(f'{BASE_URL}/manager/challenges', timeout=5)
            
            if resp.status_code == 200:
                print(f"  保级挑战页面访问成功")
                
                # 模拟操作
                self.operation_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'type': 'challenge',
                    'operation': 'decide'
                })
                
        except Exception as e:
            print(f"  处理保级挑战异常: {e}")
    
    def _save_log(self):
        """保存操作日志"""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(SUPERVISOR_LOG, 'w', encoding='utf-8') as f:
            json.dump(self.operation_log, f, ensure_ascii=False, indent=2)


def main():
    """主函数"""
    simulator = SupervisorSimulator()
    simulator.run_simulation()


if __name__ == '__main__':
    main()




