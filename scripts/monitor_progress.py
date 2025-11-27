#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控分析进度并显示实时状态
"""

import os
import time
import glob
from datetime import datetime


def check_latest_reports():
    """检查最新生成的报告"""
    report_files = glob.glob("*_idle_report_*.xlsx") + glob.glob("*_idle_report_*.html")
    
    if not report_files:
        return []
    
    # 按修改时间排序
    reports = []
    for f in report_files:
        stat = os.stat(f)
        reports.append({
            'file': f,
            'mtime': stat.st_mtime,
            'size': stat.st_size,
            'time_str': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    reports.sort(key=lambda x: x['mtime'], reverse=True)
    return reports


def check_log_files():
    """检查日志文件"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        return None
    
    log_files = glob.glob(os.path.join(log_dir, "*.log"))
    if not log_files:
        return None
    
    latest_log = max(log_files, key=os.path.getmtime)
    return latest_log


def main():
    """主函数"""
    print("="*80)
    print("🔍 分析任务进度监控")
    print(f"📅 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 检查后台进程
    print("\n📋 检查后台进程...")
    exit_code = os.system("ps aux | grep 'analyze_all_tenants.py' | grep -v grep > /dev/null 2>&1")
    
    if exit_code == 0:
        print("✅ 分析任务正在运行中")
        
        # 获取进程信息
        os.system("ps aux | grep 'analyze_all_tenants.py' | grep -v grep | awk '{print \"  进程ID: \" $2 \", CPU: \" $3 \"%, 内存: \" $4 \"%, 运行时间: \" $10}'")
    else:
        print("❌ 分析任务未在运行")
    
    # 检查最新报告
    print("\n" + "="*80)
    print("📄 最新生成的报告 (Top 10):")
    print("="*80)
    
    reports = check_latest_reports()
    if reports:
        for i, report in enumerate(reports[:10], 1):
            size_kb = report['size'] / 1024
            # 提取租户名称
            tenant = report['file'].split('_')[0]
            resource_type = report['file'].split('_')[1] if len(report['file'].split('_')) > 1 else 'unknown'
            
            print(f"\n{i}. {report['file']}")
            print(f"   租户: {tenant} | 类型: {resource_type}")
            print(f"   时间: {report['time_str']} | 大小: {size_kb:.2f} KB")
    else:
        print("未找到报告文件")
    
    # 检查日志
    print("\n" + "="*80)
    print("📝 最新日志信息:")
    print("="*80)
    
    latest_log = check_log_files()
    if latest_log:
        print(f"\n日志文件: {latest_log}")
        print(f"最后修改: {datetime.fromtimestamp(os.path.getmtime(latest_log)).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 显示最后几行日志
        print("\n最近日志内容 (最后20行):")
        print("-"*80)
        try:
            with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(line.rstrip())
        except Exception as e:
            print(f"无法读取日志: {e}")
    else:
        print("未找到日志文件")
    
    # 建议
    print("\n" + "="*80)
    print("💡 操作建议:")
    print("="*80)
    print("""
1. 查看更详细的实时日志:
   tail -f logs/aliyunidle.log

2. 如果任务卡住,可以终止后重新运行:
   pkill -f analyze_all_tenants.py
   python3 analyze_all_tenants.py

3. 查看已生成的报告:
   ls -lht *_idle_report_* | head -20

4. 单独分析特定租户(更快):
   python3 main.py ydzn cru ecs
   python3 main.py zmyc cru rds
""")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
