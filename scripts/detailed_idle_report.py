#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于当前数据库生成所有租户闲置资源详细报告
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
        return {"tenants": {"ydzn": {"display_name": "羊小咩数科"}, "zmyc": {"display_name": "ZMYC"}, "cf": {"display_name": "CF租户"}}}


def analyze_ecs_metrics():
    """分析ECS监控指标"""
    db_file = "ecs_monitoring_data_fixed.db"
    if not os.path.exists(db_file):
        return []
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 查询每个实例的CPU平均使用率(如果有CPUUtilization指标)
        query = """
        SELECT 
            i.instance_id,
            i.instance_name,
            i.instance_type,
            i.region,
            i.status,
            m.metric_name,
            AVG(m.metric_value) as avg_value,
            COUNT(*) as data_points
        FROM instances i
        LEFT JOIN monitoring_data m ON i.instance_id = m.instance_id
        WHERE m.timestamp >= datetime('now', '-7 days')
          AND m.metric_name IN ('CPUUtilization', 'cpu_idle', 'cpu.total')
        GROUP BY i.instance_id, m.metric_name
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # 按实例ID分组统计
        instance_metrics = defaultdict(lambda: {"metrics": {}, "info": {}})
        
        for row in results:
            instance_id = row[0]
            instance_metrics[instance_id]["info"] = {
                "instance_id": row[0],
                "instance_name": row[1] or "未命名",
                "instance_type": row[2],
                "region": row[3],
                "status": row[4]
            }
            instance_metrics[instance_id]["metrics"][row[5]] = {
                "avg_value": round(row[6], 2),
                "data_points": row[7]
            }
        
        # 也查询没有监控数据的实例
        cursor.execute("""
            SELECT instance_id, instance_name, instance_type, region, status
            FROM instances
            WHERE instance_id NOT IN (
                SELECT DISTINCT instance_id 
                FROM monitoring_data 
                WHERE timestamp >= datetime('now', '-7 days')
            )
        """)
        
        no_metrics = cursor.fetchall()
        
        conn.close()
        
        return instance_metrics, no_metrics
        
    except Exception as e:
        print(f"❌ 查询ECS数据出错: {e}")
        import traceback
        traceback.print_exc()
        return {}, []


def analyze_rds_metrics():
    """分析RDS监控指标"""
    db_file = "rds_monitoring_data.db"
    if not os.path.exists(db_file):
        return []
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 查询RDS实例及其监控数据
        query = """
        SELECT 
            i.instance_id,
            i.instance_name,
            i.engine,
            i.engine_version,
            i.region,
            i.status,
            m.metric_name,
            AVG(m.metric_value) as avg_value,
            COUNT(*) as data_points
        FROM rds_instances i
        LEFT JOIN rds_monitoring_data m ON i.instance_id = m.instance_id
        WHERE m.timestamp >= unixepoch('now', '-7 days')
          AND m.metric_name IN ('CPUUtilization', 'ConnectionUsage', 'ActiveConnections')
        GROUP BY i.instance_id, m.metric_name
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        instance_metrics = defaultdict(lambda: {"metrics": {}, "info": {}})
        
        for row in results:
            instance_id = row[0]
            instance_metrics[instance_id]["info"] = {
                "instance_id": row[0],
                "instance_name": row[1] or "未命名",
                "engine": f"{row[2]} {row[3]}",
                "region": row[4],
                "status": row[5]
            }
            instance_metrics[instance_id]["metrics"][row[6]] = {
                "avg_value": round(row[7], 2),
                "data_points": row[8]
            }
        
        conn.close()
        
        return instance_metrics
        
    except Exception as e:
        print(f"❌ 查询RDS数据出错: {e}")
        import traceback
        traceback.print_exc()
        return {}


def generate_detailed_report():
    """生成详细报告"""
    print("="*100)
    print("📊 所有租户闲置资源详细分析报告")
    print(f"📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*100)
    
    config = load_config()
    tenants = config.get("tenants", {})
    
    print(f"\n🏢 已配置租户 ({len(tenants)} 个):")
    for tenant_name, tenant_config in tenants.items():
        display_name = tenant_config.get("display_name", tenant_name)
        print(f"  • {display_name} ({tenant_name})")
    
    # 资源总量统计
    print("\n" + "="*100)
    print("📦 资源总量统计")
    print("="*100)
    
    db_stats = {
        "ECS实例": ("ecs_monitoring_data_fixed.db", "SELECT COUNT(*) FROM instances"),
        "RDS实例": ("rds_monitoring_data.db", "SELECT COUNT(*) FROM rds_instances"),
        "SLB实例": ("slb_monitoring_data.db", "SELECT COUNT(*) FROM slb_instances"),
        "DNS域名": ("dns_monitoring_data.db", "SELECT COUNT(*) FROM dns_domains"),
        "DNS记录": ("dns_monitoring_data.db", "SELECT COUNT(*) FROM dns_records"),
    }
    
    total_resources = {}
    for resource_type, (db_file, query) in db_stats.items():
        if os.path.exists(db_file):
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute(query)
                count = cursor.fetchone()[0]
                total_resources[resource_type] = count
                conn.close()
            except:
                total_resources[resource_type] = 0
        else:
            total_resources[resource_type] = 0
    
    for resource_type, count in total_resources.items():
        print(f"  {resource_type:<15s}: {count:>6d} 个")
    
    # ECS详细分析
    print("\n" + "="*100)
    print("🖥️  ECS实例详细分析 (过去7天监控数据)")
    print("="*100)
    
    ecs_metrics, ecs_no_metrics = analyze_ecs_metrics()
    
    if ecs_metrics:
        print(f"\n有监控数据的实例: {len(ecs_metrics)} 个")
        print("-"*100)
        
        # 统计低使用率实例
        low_cpu_instances = []
        for instance_id, data in ecs_metrics.items():
            info = data["info"]
            metrics = data["metrics"]
            
            # 查找CPU相关指标
            cpu_value = None
            for metric_name in ['CPUUtilization', 'cpu_idle', 'cpu.total']:
                if metric_name in metrics:
                    cpu_value = metrics[metric_name]["avg_value"]
                    break
            
            if cpu_value is not None and cpu_value < 10:
                low_cpu_instances.append({
                    **info,
                    "cpu_avg": cpu_value,
                    "metrics": metrics
                })
        
        if low_cpu_instances:
            print(f"\n🔴 低CPU使用率实例 (CPU < 10%): {len(low_cpu_instances)} 个")
            print(f"{'实例名称':<30s} {'实例ID':<20s} {'类型':<15s} {'地域':<15s} {'平均CPU%':<10s}")
            print("-"*100)
            for inst in low_cpu_instances[:20]:  # 只显示前20个
                print(f"{inst['instance_name'][:29]:<30s} "
                      f"{inst['instance_id'][:19]:<20s} "
                      f"{inst['instance_type'][:14]:<15s} "
                      f"{inst['region'][:14]:<15s} "
                      f"{inst['cpu_avg']:>9.2f}%")
            
            if len(low_cpu_instances) > 20:
                print(f"... 还有 {len(low_cpu_instances) - 20} 个实例未显示")
        else:
            print("\n✅ 未发现明显低CPU使用率实例")
    
    if ecs_no_metrics:
        print(f"\n⚠️  无监控数据的实例: {len(ecs_no_metrics)} 个")
        print("-"*100)
        print(f"{'实例名称':<30s} {'实例ID':<20s} {'类型':<15s} {'地域':<15s} {'状态':<10s}")
        print("-"*100)
        for row in ecs_no_metrics[:20]:  # 只显示前20个
            print(f"{(row[1] or '未命名')[:29]:<30s} "
                  f"{row[0][:19]:<20s} "
                  f"{row[2][:14]:<15s} "
                  f"{row[3][:14]:<15s} "
                  f"{row[4]:<10s}")
        
        if len(ecs_no_metrics) > 20:
            print(f"... 还有 {len(ecs_no_metrics) - 20} 个实例未显示")
    
    # RDS详细分析
    print("\n" + "="*100)
    print("🗄️  RDS实例详细分析 (过去7天监控数据)")
    print("="*100)
    
    rds_metrics = analyze_rds_metrics()
    
    if rds_metrics:
        print(f"\n有监控数据的实例: {len(rds_metrics)} 个")
        print("-"*100)
        
        # 统计低使用率实例
        low_util_instances = []
        for instance_id, data in rds_metrics.items():
            info = data["info"]
            metrics = data["metrics"]
            
            cpu_value = metrics.get("CPUUtilization", {}).get("avg_value")
            conn_value = metrics.get("ActiveConnections", {}).get("avg_value", metrics.get("ConnectionUsage", {}).get("avg_value"))
            
            if (cpu_value is not None and cpu_value < 10) or (conn_value is not None and conn_value < 5):
                low_util_instances.append({
                    **info,
                    "cpu_avg": cpu_value,
                    "conn_avg": conn_value,
                    "metrics": metrics
                })
        
        if low_util_instances:
            print(f"\n🔴 低使用率RDS实例: {len(low_util_instances)} 个")
            print(f"{'实例名称':<30s} {'引擎':<20s} {'地域':<15s} {'CPU%':<10s} {'连接数':<10s}")
            print("-"*100)
            for inst in low_util_instances[:20]:
                cpu_str = f"{inst['cpu_avg']:.2f}" if inst['cpu_avg'] is not None else "N/A"
                conn_str = f"{inst['conn_avg']:.2f}" if inst['conn_avg'] is not None else "N/A"
                print(f"{inst['instance_name'][:29]:<30s} "
                      f"{inst['engine'][:19]:<20s} "
                      f"{inst['region'][:14]:<15s} "
                      f"{cpu_str:<10s} "
                      f"{conn_str:<10s}")
            
            if len(low_util_instances) > 20:
                print(f"... 还有 {len(low_util_instances) - 20} 个实例未显示")
        else:
            print("\n✅ 未发现明显低使用率实例")
    else:
        print("\n💡 无监控数据,建议运行完整分析")
    
    # 建议
    print("\n" + "="*100)
    print("💡 优化建议")
    print("="*100)
    print("""
1. 🔍 定期监控: 建立定期分析机制,每周查看资源使用情况
   
2. 💰 成本优化:
   - 低CPU使用率ECS: 考虑降配或释放
   - 低连接数RDS: 评估是否可以合并或缩容
   - 无监控数据实例: 可能是停机或配置问题
   
3. 🛠️ 运行完整分析:
   - 所有租户: python3 analyze_all_tenants.py
   - 单个租户: python3 main.py [租户名] cru all
   - 特定资源: python3 main.py [租户名] cru [资源类型]
   
4. 📊 查看详细报告:
   - 磁盘分析: python3 main.py [租户名] cru disk
   - 网络资源: python3 main.py [租户名] network
   - 费用分析: python3 main.py [租户名] cost
""")
    
    print("="*100)
    print("✅ 报告生成完成")
    print("="*100)


if __name__ == "__main__":
    generate_detailed_report()
