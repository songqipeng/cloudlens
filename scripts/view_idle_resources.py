#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看所有租户当前的闲置资源汇总
"""

import json
import os
import sqlite3
from datetime import datetime
from glob import glob


def view_database_stats(db_file):
    """查看数据库统计信息"""
    if not os.path.exists(db_file):
        return None
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        stats = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            stats[table_name] = count
        
        conn.close()
        return stats
    except Exception as e:
        return {"error": str(e)}


def find_recent_reports():
    """查找最近的报告文件"""
    report_patterns = [
        "*_idle_report_*.xlsx",
        "*_idle_report_*.html",
        "*_network_resources_*.xlsx",
        "*_network_resources_*.html",
        "unbound_eips_*.xlsx",
    ]
    
    all_reports = []
    for pattern in report_patterns:
        files = glob(pattern)
        for f in files:
            stat = os.stat(f)
            all_reports.append({
                "file": f,
                "size": stat.st_size,
                "mtime": stat.st_mtime
            })
    
    # 按修改时间排序
    all_reports.sort(key=lambda x: x["mtime"], reverse=True)
    return all_reports


def main():
    """主函数"""
    print("="*80)
    print("📊 所有租户闲置资源汇总")
    print(f"📅 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 1. 查看数据库文件
    print("\n📦 数据库资源统计:")
    print("-"*80)
    
    db_files = {
        "ECS监控": "ecs_monitoring_data_fixed.db",
        "DNS监控": "dns_monitoring_data.db",
        "EIP监控": "eip_monitoring_data.db",
        "OSS监控": "oss_monitoring_data.db",
        "RDS监控": "rds_monitoring_data.db",
        "SLB监控": "slb_monitoring_data.db",
    }
    
    for name, db_file in db_files.items():
        if os.path.exists(db_file):
            stats = view_database_stats(db_file)
            if stats:
                print(f"\n{name} ({db_file}):")
                for table, count in stats.items():
                    print(f"  - {table}: {count} 条记录")
        else:
            print(f"\n{name}: ❌ 数据库文件不存在")
    
    # 2. 查看最近的报告文件
    print("\n" + "="*80)
    print("📄 最近生成的报告文件:")
    print("-"*80)
    
    reports = find_recent_reports()
    if reports:
        for i, report in enumerate(reports[:10], 1):  # 只显示最近10个
            file_name = report["file"]
            size_kb = report["size"] / 1024
            mtime = datetime.fromtimestamp(report["mtime"]).strftime('%Y-%m-%d %H:%M:%S')
            print(f"{i}. {file_name}")
            print(f"   大小: {size_kb:.2f} KB | 修改时间: {mtime}")
    else:
        print("未找到报告文件")
    
    # 3. 提示用户可以执行的操作
    print("\n" + "="*80)
    print("💡 查看详细报告的方法:")
    print("-"*80)
    print("1. 运行完整分析: python3 main.py [租户] cru all")
    print("2. 分析特定资源: python3 main.py [租户] cru [资源类型]")
    print("3. 网络资源分析: python3 main.py [租户] network")
    print("4. 查看所有租户: python3 main.py list-credentials")
    print("\n可用租户: ydzn, zmyc, cf")
    print("可用资源类型: ecs, rds, redis, oss, slb, eip, disk, dns, nas, ack等")
    print("="*80)


if __name__ == "__main__":
    main()
