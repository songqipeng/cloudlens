#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速查看所有租户当前闲置资源摘要
从现有的报告文件和数据库中提取信息
"""

import os
import sqlite3
import json
from datetime import datetime
from collections import defaultdict


def load_config():
    """加载配置"""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except:
        return None


def get_database_summary():
    """获取数据库摘要信息"""
    summary = {}
    
    db_configs = [
        ("ECS", "ecs_monitoring_data_fixed.db", "instances"),
        ("RDS", "rds_monitoring_data.db", "rds_instances"),
        ("SLB", "slb_monitoring_data.db", "slb_instances"),
        ("DNS域名", "dns_monitoring_data.db", "dns_domains"),
        ("DNS记录", "dns_monitoring_data.db", "dns_records"),
    ]
    
    for name, db_file, table in db_configs:
        if os.path.exists(db_file):
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                summary[name] = count
                conn.close()
            except Exception as e:
                summary[name] = f"错误: {e}"
        else:
            summary[name] = "数据库不存在"
    
    return summary


def check_recent_reports():
    """检查最近的报告文件"""
    import glob
    
    report_patterns = {
        "磁盘闲置报告": "*_disk_idle_report_*.xlsx",
        "网络资源报告": "*_network_resources_*.xlsx",
        "未绑定EIP": "unbound_eips_*.xlsx",
    }
    
    recent_reports = {}
    
    for report_type, pattern in report_patterns.items():
        files = glob.glob(pattern)
        if files:
            # 获取最新的文件
            latest_file = max(files, key=os.path.getmtime)
            mtime = os.path.getmtime(latest_file)
            recent_reports[report_type] = {
                "file": latest_file,
                "time": datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S'),
                "size_kb": os.path.getsize(latest_file) / 1024
            }
    
    return recent_reports


def main():
    """主函数"""
    print("="*80)
    print("📊 所有租户闲置资源快速摘要")
    print(f"📅 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 1. 显示配置的租户
    config = load_config()
    if config:
        tenants = config.get("tenants", {})
        print(f"\n🏢 已配置的租户 ({len(tenants)} 个):")
        for tenant_name, tenant_config in tenants.items():
            display_name = tenant_config.get("display_name", tenant_name)
            print(f"  - {tenant_name}: {display_name}")
    
    # 2. 数据库资源统计
    print("\n" + "="*80)
    print("📦 数据库资源总量:")
    print("-"*80)
    
    db_summary = get_database_summary()
    for resource, count in db_summary.items():
        if isinstance(count, int):
            print(f"  {resource:12s}: {count:6d} 个")
        else:
            print(f"  {resource:12s}: {count}")
    
    # 3. 最近的报告文件
    print("\n" + "="*80)
    print("📄 最近生成的报告:")
    print("-"*80)
    
    recent_reports = check_recent_reports()
    if recent_reports:
        for report_type, info in recent_reports.items():
            print(f"\n  {report_type}:")
            print(f"    文件: {info['file']}")
            print(f"    时间: {info['time']}")
            print(f"    大小: {info['size_kb']:.2f} KB")
    else:
        print("  未找到最近的报告文件")
    
    # 4. 根据数据库推测闲置资源情况
    print("\n" + "="*80)
    print("💡 闲置资源分析建议:")
    print("-"*80)
    
    if os.path.exists("ecs_monitoring_data_fixed.db"):
        try:
            conn = sqlite3.connect("ecs_monitoring_data_fixed.db")
            cursor = conn.cursor()
            
            # 查找最近7天的监控数据
            cursor.execute("""
                SELECT COUNT(DISTINCT instance_id) 
                FROM monitoring_data 
                WHERE timestamp >= datetime('now', '-7 days')
            """)
            monitored_count = cursor.fetchone()[0]
            
            # 获取总实例数
            cursor.execute("SELECT COUNT(*) FROM instances")
            total_count = cursor.fetchone()[0]
            
            print(f"  ECS实例:")
            print(f"    总数: {total_count} 个")
            print(f"    有监控数据(近7天): {monitored_count} 个")
            
            # 查找低CPU使用率的实例
            cursor.execute("""
                SELECT COUNT(DISTINCT instance_id)
                FROM monitoring_data
                WHERE timestamp >= datetime('now', '-7 days')
                GROUP BY instance_id
                HAVING AVG(cpu_percent) < 10
            """)
            low_cpu_result = cursor.fetchone()
            low_cpu_count = low_cpu_result[0] if low_cpu_result else 0
            
            if low_cpu_count > 0:
                print(f"    🔴 疑似闲置(CPU<10%): {low_cpu_count} 个")
            else:
                print(f"    ✅ 未检测到明显闲置实例")
            
            conn.close()
        except Exception as e:
            print(f"  ECS分析失败: {e}")
    
    if os.path.exists("rds_monitoring_data.db"):
        try:
            conn = sqlite3.connect("rds_monitoring_data.db")
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM rds_instances")
            total_rds = cursor.fetchone()[0]
            
            print(f"\n  RDS实例:")
            print(f"    总数: {total_rds} 个")
            print(f"    💡 运行完整分析以获取利用率信息")
            
            conn.close()
        except Exception as e:
            print(f"  RDS分析失败: {e}")
    
    # 5. 操作建议
    print("\n" + "="*80)
    print("🚀 查看详细信息的命令:")
    print("="*80)
    print("\n  分析所有租户的所有资源:")
    print("    python3 analyze_all_tenants.py")
    print("\n  分析特定租户:")
    print("    python3 main.py ydzn cru all     # YDZN租户所有资源")
    print("    python3 main.py zmyc cru all     # ZMYC租户所有资源")
    print("    python3 main.py cf cru all       # CF租户所有资源")
    print("\n  分析特定资源类型:")
    print("    python3 main.py [租户] cru ecs   # ECS实例")
    print("    python3 main.py [租户] cru rds   # RDS数据库")
    print("    python3 main.py [租户] cru disk  # 磁盘")
    print("    python3 main.py [租户] network   # 网络资源")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
