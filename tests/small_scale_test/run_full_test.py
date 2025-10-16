#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小规模测试主控脚本
一键运行完整的测试流程
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入配置
from tests.small_scale_test.config import *


def print_header(title):
    """打印标题"""
    print("\n" + "="*70)
    print(f"{title}")
    print("="*70 + "\n")


def print_step(step_num, step_name):
    """打印步骤"""
    print(f"\n{'▶'*3} 步骤 {step_num}: {step_name}")
    print("-"*70)


def main():
    """主函数"""
    start_time = datetime.now()
    
    print_header("🚀 小规模核心功能测试")
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试周期: {START_DATE} ~ {END_DATE}")
    print(f"测试员工: {TOTAL_EMPLOYEES}人")
    
    results = {
        'success': [],
        'failed': []
    }
    
    # ========== 步骤1: 数据生成 ==========
    print_step(1, "数据生成")
    try:
        import subprocess
        step_start = time.time()
        result = subprocess.run(
            [sys.executable, 'tests/small_scale_test/generate_test_data.py'],
            capture_output=True,
            text=True
        )
        elapsed = time.time() - step_start
        
        if result.returncode == 0:
            print(f"✅ 数据生成成功 (耗时: {elapsed:.1f}秒)")
            results['success'].append('数据生成')
        else:
            print(f"❌ 数据生成失败")
            print(result.stderr)
            results['failed'].append('数据生成')
            return 1
    except Exception as e:
        print(f"❌ 数据生成异常: {str(e)}")
        results['failed'].append('数据生成')
        return 1
    
    # ========== 步骤2: 数据导入 ==========
    print_step(2, "数据导入")
    try:
        import subprocess
        step_start = time.time()
        result = subprocess.run(
            [sys.executable, 'tests/small_scale_test/import_test_data.py'],
            capture_output=True,
            text=True
        )
        elapsed = time.time() - step_start
        
        if result.returncode == 0:
            print(f"✅ 数据导入成功 (耗时: {elapsed:.1f}秒)")
            results['success'].append('数据导入')
        else:
            print(f"❌ 数据导入失败")
            print(result.stderr)
            results['failed'].append('数据导入')
            return 1
    except Exception as e:
        print(f"❌ 数据导入异常: {str(e)}")
        results['failed'].append('数据导入')
        return 1
    
    # ========== 步骤3: 工作日配置 ==========
    print_step(3, "工作日配置")
    try:
        import subprocess
        step_start = time.time()
        result = subprocess.run(
            [sys.executable, 'tests/small_scale_test/configure_workdays.py'],
            capture_output=True,
            text=True
        )
        elapsed = time.time() - step_start
        
        if result.returncode == 0:
            print(f"✅ 工作日配置成功 (耗时: {elapsed:.1f}秒)")
            results['success'].append('工作日配置')
        else:
            print(f"❌ 工作日配置失败")
            print(result.stderr)
            results['failed'].append('工作日配置')
            return 1
    except Exception as e:
        print(f"❌ 工作日配置异常: {str(e)}")
        results['failed'].append('工作日配置')
        return 1
    
    # ========== 步骤4: 业务逻辑触发 ==========
    print_step(4, "业务逻辑触发")
    try:
        import subprocess
        step_start = time.time()
        result = subprocess.run(
            [sys.executable, 'tests/small_scale_test/trigger_business_logic.py'],
            capture_output=True,
            text=True
        )
        elapsed = time.time() - step_start
        
        if result.returncode == 0:
            print(f"✅ 业务逻辑触发成功 (耗时: {elapsed:.1f}秒)")
            results['success'].append('业务逻辑触发')
        else:
            print(f"❌ 业务逻辑触发失败")
            results['failed'].append('业务逻辑触发')
    except Exception as e:
        print(f"❌ 业务逻辑触发异常: {str(e)}")
        results['failed'].append('业务逻辑触发')
    
    # ========== 步骤5: 数据验证 ==========
    print_step(5, "数据验证")
    try:
        import subprocess
        step_start = time.time()
        result = subprocess.run(
            [sys.executable, 'tests/small_scale_test/validate_results.py'],
            capture_output=True,
            text=True
        )
        elapsed = time.time() - step_start
        
        if result.returncode == 0:
            print(f"✅ 数据验证成功 (耗时: {elapsed:.1f}秒)")
            results['success'].append('数据验证')
        else:
            print(f"❌ 数据验证失败")
            results['failed'].append('数据验证')
    except Exception as e:
        print(f"❌ 数据验证异常: {str(e)}")
        results['failed'].append('数据验证')
    
    # ========== 步骤6: 报告生成 ==========
    print_step(6, "报告生成")
    try:
        import subprocess
        step_start = time.time()
        result = subprocess.run(
            [sys.executable, 'tests/small_scale_test/generate_report.py'],
            capture_output=True,
            text=True
        )
        elapsed = time.time() - step_start
        
        if result.returncode == 0:
            print(f"✅ 报告生成成功 (耗时: {elapsed:.1f}秒)")
            results['success'].append('报告生成')
        else:
            print(f"❌ 报告生成失败")
            results['failed'].append('报告生成')
    except Exception as e:
        print(f"❌ 报告生成异常: {str(e)}")
        results['failed'].append('报告生成')
    
    # ========== 汇总结果 ==========
    end_time = datetime.now()
    total_elapsed = (end_time - start_time).total_seconds()
    
    print_header("📊 测试执行总结")
    print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时: {total_elapsed:.1f}秒 ({total_elapsed/60:.1f}分钟)")
    print(f"\n✅ 成功步骤: {len(results['success'])}")
    for item in results['success']:
        print(f"   - {item}")
    
    if results['failed']:
        print(f"\n❌ 失败步骤: {len(results['failed'])}")
        for item in results['failed']:
            print(f"   - {item}")
    
    print("\n" + "="*70)
    print("🎯 当前进度: 基础数据准备完成")
    print("="*70)
    print("\n📋 下一步操作:")
    print("1. 完成剩余脚本开发 (trigger_business_logic.py等)")
    print("2. 或手动测试当前数据:")
    print("   - 访问: http://localhost:8080")
    print("   - 登录: admin / 123456")
    print("   - 查看: 员工列表、业绩数据")
    print("\n📁 相关文件:")
    print(f"   - 测试员工: {OUTPUT_DIR}/test_employees.csv")
    print(f"   - 业绩数据: {OUTPUT_DIR}/test_performance.csv")
    print(f"   - 进度报告: tests/small_scale_test/小规模测试进度报告.md")
    print("="*70 + "\n")
    
    return 0


if __name__ == '__main__':
    try:
        exit_code = main()
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试执行异常: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)

