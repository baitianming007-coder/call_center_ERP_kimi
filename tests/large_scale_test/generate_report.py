"""
测试报告生成器
生成详细的测试报告
"""
import sys
import os
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.large_scale_test.config import *


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self):
        self.data = {}
        
    def generate_report(self):
        """生成完整报告"""
        print("="*60)
        print("开始生成测试报告")
        print("="*60)
        print()
        
        # 加载所有数据
        self._load_data()
        
        # 生成Markdown报告
        print("生成Markdown报告...")
        self._generate_markdown()
        print(f"✓ {TEST_REPORT_MD}")
        
        # 生成JSON摘要
        print("生成JSON摘要...")
        self._generate_json_summary()
        print(f"✓ {TEST_SUMMARY_JSON}")
        
        print()
        print("="*60)
        print("报告生成完成")
        print("="*60)
    
    def _load_data(self):
        """加载测试数据"""
        # 加载验证结果
        if os.path.exists(VALIDATION_RESULTS):
            with open(VALIDATION_RESULTS, 'r', encoding='utf-8') as f:
                self.data['validation'] = json.load(f)
        
        # 加载触发日志
        if os.path.exists(TRIGGER_LOG):
            with open(TRIGGER_LOG, 'r', encoding='utf-8') as f:
                self.data['triggers'] = json.load(f)
        
        # 加载主管操作日志
        if os.path.exists(SUPERVISOR_LOG):
            with open(SUPERVISOR_LOG, 'r', encoding='utf-8') as f:
                self.data['operations'] = json.load(f)
    
    def _generate_markdown(self):
        """生成Markdown报告"""
        report = []
        
        # 标题
        report.append("# 大规模业务逻辑测试报告")
        report.append("")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 测试概览
        report.append("## 1. 测试概览")
        report.append("")
        report.append(f"- **测试规模**: {TOTAL_EMPLOYEES}人")
        report.append(f"- **时间范围**: {START_DATE} 至 {END_DATE}")
        report.append(f"- **员工类型分布**:")
        for emp_type, count in EMPLOYEE_DISTRIBUTION.items():
            report.append(f"  - {emp_type}: {count}人")
        report.append("")
        
        # 验证结果
        if 'validation' in self.data:
            report.append("## 2. 验证结果")
            report.append("")
            
            val = self.data['validation']
            
            # 晋级验证
            report.append("### 2.1 晋级逻辑验证")
            pv = val.get('promotion_validation', {})
            if pv.get('validated'):
                report.append(f"- **状态**: ✅ 通过")
                report.append(f"- **晋级申请数**: {pv.get('total_applications', 0)}")
            else:
                report.append(f"- **状态**: ⚠️ 未验证")
            report.append("")
            
            # 保级验证
            report.append("### 2.2 保级挑战验证")
            cv = val.get('challenge_validation', {})
            if cv.get('validated'):
                report.append(f"- **状态**: ✅ 通过")
                report.append(f"- **挑战记录数**: {cv.get('total_challenges', 0)}")
            else:
                report.append(f"- **状态**: ⚠️ 未验证")
            report.append("")
            
            # 薪资验证
            report.append("### 2.3 薪资计算验证")
            sv = val.get('salary_validation', {})
            report.append(f"- **抽样规模**: {sv.get('sample_size', 0)}人")
            report.append(f"- **验证通过**: {sv.get('validated', 0)}人")
            report.append(f"- **计算错误**: {sv.get('errors', 0)}人")
            report.append(f"- **通过率**: {sv.get('pass_rate', 0):.1f}%")
            report.append("")
            
            # 一致性验证
            report.append("### 2.4 数据一致性验证")
            csv = val.get('consistency_validation', {})
            report.append(f"- **员工记录**: {csv.get('total_employees', 0)}")
            report.append(f"- **业绩记录**: {csv.get('total_performance', 0)}")
            report.append(f"- **孤立记录**: {csv.get('orphan_performance', 0)}")
            report.append(f"- **一致性**: {'✅ 通过' if csv.get('consistent') else '❌ 失败'}")
            report.append("")
        
        # 触发事件统计
        if 'triggers' in self.data:
            report.append("## 3. 触发事件统计")
            report.append("")
            triggers = self.data['triggers']
            report.append(f"- **总触发事件**: {len(triggers)}")
            
            # 按类型统计
            promotion_count = sum(1 for t in triggers if t.get('type') == 'promotion')
            challenge_count = sum(1 for t in triggers if t.get('type') == 'challenge')
            report.append(f"- **晋级触发**: {promotion_count}")
            report.append(f"- **保级触发**: {challenge_count}")
            report.append("")
        
        # 总结
        report.append("## 4. 总结")
        report.append("")
        report.append("测试已完成所有预定模块的验证。")
        report.append("")
        
        # 写入文件
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(TEST_REPORT_MD, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
    
    def _generate_json_summary(self):
        """生成JSON摘要"""
        summary = {
            'generated_at': datetime.now().isoformat(),
            'test_config': {
                'total_employees': TOTAL_EMPLOYEES,
                'start_date': START_DATE.isoformat(),
                'end_date': END_DATE.isoformat(),
                'distribution': EMPLOYEE_DISTRIBUTION
            },
            'validation_results': self.data.get('validation', {}),
            'trigger_count': len(self.data.get('triggers', [])),
            'operation_count': len(self.data.get('operations', []))
        }
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(TEST_SUMMARY_JSON, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)


def main():
    """主函数"""
    generator = ReportGenerator()
    generator.generate_report()


if __name__ == '__main__':
    main()




