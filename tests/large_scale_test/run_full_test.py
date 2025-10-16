"""
主控脚本
一键执行完整的大规模业务逻辑测试
"""
import sys
import os
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.large_scale_test import data_generator, import_data, trigger_checks, supervisor_simulation, business_validator, generate_report


def print_banner(text):
    """打印横幅"""
    print("\n" + "="*60)
    print(text.center(60))
    print("="*60 + "\n")


def main():
    """主函数 - 执行完整测试流程"""
    start_time = time.time()
    
    print_banner("大规模业务逻辑测试 - 完整流程")
    
    try:
        # 阶段1：数据生成
        print_banner("阶段1/6: 数据生成")
        data_generator.main()
        
        # 阶段2：数据导入
        print_banner("阶段2/6: 数据导入")
        import_data.main()
        
        # 阶段3：触发检测
        print_banner("阶段3/6: 触发检测")
        trigger_checks.main()
        
        # 阶段4：主管操作模拟
        print_banner("阶段4/6: 主管操作模拟")
        supervisor_simulation.main()
        
        # 阶段5：业务验证
        print_banner("阶段5/6: 业务验证")
        business_validator.main()
        
        # 阶段6：报告生成
        print_banner("阶段6/6: 报告生成")
        generate_report.main()
        
        # 完成
        elapsed = time.time() - start_time
        print_banner("测试完成！")
        print(f"总耗时: {elapsed/60:.1f} 分钟")
        print(f"\n查看报告: tests/large_scale_test/output/test_report.md")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()




