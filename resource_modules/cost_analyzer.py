#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
费用分析模块
分析租户的月度费用分布，识别费用占大头的资源和业务
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from utils.logger import get_logger
from utils.error_handler import ErrorHandler
from core.db_manager import DatabaseManager


class CostAnalyzer:
    """费用分析器"""
    
    def __init__(self, tenant_name: str, access_key_id: str, access_key_secret: str):
        self.tenant_name = tenant_name
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.logger = get_logger('cost_analyzer')
        # 尝试多个可能的数据库目录位置
        possible_dirs = [
            Path('.') / 'data' / 'db',
            Path('.'),
            Path('.') / tenant_name
        ]
        self.data_dir = None
        for dir_path in possible_dirs:
            if dir_path.exists():
                self.data_dir = dir_path
                break
        if not self.data_dir:
            self.data_dir = Path('.')
        
    def get_cost_from_database(self, resource_type: str) -> List[Dict]:
        """从数据库获取资源成本和实例信息"""
        db_files = [
            f'{resource_type}_monitoring_data.db',
            f'{resource_type}_monitoring_data_fixed.db',
            f'data/db/{resource_type}_monitoring_data.db'
        ]
        
        instances = []
        
        for db_file in db_files:
            # 尝试绝对路径和相对路径
            db_paths = [
                self.data_dir / db_file if self.data_dir else Path(db_file),
                Path(db_file)
            ]
            
            db_path = None
            for p in db_paths:
                if p.exists():
                    db_path = p
                    break
            
            if not db_path:
                continue
            
            try:
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 查询实例表
                table_name = f'{resource_type}_instances'
                try:
                    cursor.execute(f'SELECT * FROM {table_name}')
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        instances.append({
                            'resource_type': resource_type,
                            'instance_id': row.get('instance_id', ''),
                            'instance_name': row.get('instance_name', ''),
                            'instance_type': row.get('instance_type', ''),
                            'region': row.get('region', ''),
                            'status': row.get('status', ''),
                            'monthly_cost': row.get('monthly_cost', 0) or 0
                        })
                except sqlite3.OperationalError:
                    # 表不存在，尝试其他表名
                    pass
                
                conn.close()
            except Exception as e:
                self.logger.warning(f"读取{db_file}失败: {e}")
                continue
        
        return instances
    
    def get_cost_from_discount_analyzer(self, resource_type: str) -> List[Dict]:
        """从折扣分析器获取实际续费价格（更准确）"""
        try:
            from resource_modules.discount_analyzer import DiscountAnalyzer
            
            analyzer = DiscountAnalyzer(
                self.tenant_name,
                self.access_key_id,
                self.access_key_secret
            )
            
            # 获取包年包月实例的续费价格
            instances = []
            
            if resource_type == 'ecs':
                all_instances = analyzer.get_all_ecs_instances()
                prepaid = [i for i in all_instances if i.get('InstanceChargeType') == 'PrePaid']
                results = analyzer.get_renewal_prices(prepaid, 'ecs')
                for r in results:
                    instances.append({
                        'resource_type': 'ecs',
                        'instance_id': r.get('id', ''),
                        'instance_name': r.get('name', ''),
                        'instance_type': r.get('type', ''),
                        'region': '',
                        'status': '',
                        'monthly_cost': r.get('trade_price', 0)
                    })
            elif resource_type == 'rds':
                all_instances = analyzer.get_all_rds_instances()
                prepaid = [i for i in all_instances if i.get('PayType') == 'Prepaid']
                results = analyzer.get_renewal_prices(prepaid, 'rds')
                for r in results:
                    instances.append({
                        'resource_type': 'rds',
                        'instance_id': r.get('id', ''),
                        'instance_name': r.get('name', ''),
                        'instance_type': r.get('type', ''),
                        'region': '',
                        'status': '',
                        'monthly_cost': r.get('trade_price', 0)
                    })
            elif resource_type == 'redis':
                all_instances = analyzer.get_all_redis_instances()
                prepaid = [i for i in all_instances if i.get('ChargeType') == 'PrePaid']
                results = analyzer.get_renewal_prices(prepaid, 'redis')
                for r in results:
                    instances.append({
                        'resource_type': 'redis',
                        'instance_id': r.get('id', ''),
                        'instance_name': r.get('name', ''),
                        'instance_type': r.get('type', ''),
                        'region': '',
                        'status': '',
                        'monthly_cost': r.get('trade_price', 0)
                    })
            elif resource_type == 'mongodb':
                all_instances = analyzer.get_all_mongodb_instances()
                prepaid = [i for i in all_instances if i.get('ChargeType') == 'PrePaid']
                results = analyzer.get_renewal_prices(prepaid, 'mongodb')
                for r in results:
                    instances.append({
                        'resource_type': 'mongodb',
                        'instance_id': r.get('id', ''),
                        'instance_name': r.get('name', ''),
                        'instance_type': r.get('type', ''),
                        'region': '',
                        'status': '',
                        'monthly_cost': r.get('trade_price', 0)
                    })
            elif resource_type == 'clickhouse':
                all_instances = analyzer.get_all_clickhouse_instances()
                prepaid = [i for i in all_instances if i.get('PayType') == 'Prepaid']
                results = analyzer.get_renewal_prices(prepaid, 'clickhouse')
                for r in results:
                    instances.append({
                        'resource_type': 'clickhouse',
                        'instance_id': r.get('id', ''),
                        'instance_name': r.get('name', ''),
                        'instance_type': r.get('type', ''),
                        'region': '',
                        'status': '',
                        'monthly_cost': r.get('trade_price', 0)
                    })
            elif resource_type == 'nas':
                all_instances = analyzer.get_all_nas_file_systems()
                prepaid = [i for i in all_instances if i.get('ChargeType') in ['Prepaid', 'PrePaid']]
                results = analyzer.get_renewal_prices(prepaid, 'nas')
                for r in results:
                    instances.append({
                        'resource_type': 'nas',
                        'instance_id': r.get('id', ''),
                        'instance_name': r.get('name', ''),
                        'instance_type': r.get('type', ''),
                        'region': '',
                        'status': '',
                        'monthly_cost': r.get('trade_price', 0)
                    })
            elif resource_type == 'polardb':
                all_instances = analyzer.get_all_polardb_clusters()
                prepaid = [i for i in all_instances if i.get('PayType') == 'Prepaid']
                results = analyzer.get_renewal_prices(prepaid, 'polardb')
                for r in results:
                    instances.append({
                        'resource_type': 'polardb',
                        'instance_id': r.get('id', ''),
                        'instance_name': r.get('name', ''),
                        'instance_type': r.get('type', ''),
                        'region': '',
                        'status': '',
                        'monthly_cost': r.get('trade_price', 0)
                    })
            
            return instances
        except Exception as e:
            self.logger.warning(f"从折扣分析器获取{resource_type}成本失败: {e}")
            return []
    
    def get_all_costs(self) -> Dict[str, List[Dict]]:
        """获取所有资源类型的成本数据"""
        all_costs = {}
        
        # 支持包年包月的资源类型（优先使用折扣分析器的实际价格）
        prepaid_resources = ['ecs', 'rds', 'redis', 'mongodb', 'clickhouse', 'nas', 'polardb']
        
        # 按量付费的资源类型（从数据库获取估算成本）
        pay_as_you_go_resources = ['oss', 'slb', 'eip', 'ack', 'eci']
        
        self.logger.info("开始收集所有资源类型的成本数据...")
        
        # 先尝试从折扣分析器获取包年包月资源的实际价格
        for resource_type in prepaid_resources:
            self.logger.info(f"获取{resource_type.upper()}成本数据...")
            costs = self.get_cost_from_discount_analyzer(resource_type)
            if not costs:
                # 如果失败，从数据库获取
                costs = self.get_cost_from_database(resource_type)
            all_costs[resource_type] = costs
            self.logger.info(f"  {resource_type.upper()}: {len(costs)}个实例")
        
        # 从数据库获取按量付费资源的估算成本
        for resource_type in pay_as_you_go_resources:
            self.logger.info(f"获取{resource_type.upper()}成本数据...")
            costs = self.get_cost_from_database(resource_type)
            all_costs[resource_type] = costs
            self.logger.info(f"  {resource_type.upper()}: {len(costs)}个实例")
        
        return all_costs
    
    def analyze_cost_distribution(self) -> Dict:
        """分析费用分布"""
        all_costs = self.get_all_costs()
        
        # 汇总统计
        total_monthly_cost = 0
        resource_cost_summary = {}
        region_cost_summary = {}
        
        all_instances = []
        
        for resource_type, instances in all_costs.items():
            resource_total = sum(inst.get('monthly_cost', 0) for inst in instances)
            resource_cost_summary[resource_type.upper()] = {
                'count': len(instances),
                'total_cost': resource_total,
                'percentage': 0  # 稍后计算
            }
            total_monthly_cost += resource_total
            
            # 按区域汇总
            for inst in instances:
                region = inst.get('region', 'unknown')
                if region not in region_cost_summary:
                    region_cost_summary[region] = 0
                region_cost_summary[region] += inst.get('monthly_cost', 0)
            
            all_instances.extend(instances)
        
        # 计算百分比
        for resource_type in resource_cost_summary:
            if total_monthly_cost > 0:
                resource_cost_summary[resource_type]['percentage'] = \
                    (resource_cost_summary[resource_type]['total_cost'] / total_monthly_cost) * 100
        
        # 按费用排序
        sorted_resources = sorted(
            resource_cost_summary.items(),
            key=lambda x: x[1]['total_cost'],
            reverse=True
        )
        
        sorted_regions = sorted(
            region_cost_summary.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            'total_monthly_cost': total_monthly_cost,
            'total_instances': len(all_instances),
            'resource_cost_summary': dict(sorted_resources),
            'region_cost_summary': dict(sorted_regions),
            'all_instances': all_instances,
            'resource_cost_detail': resource_cost_summary
        }
    
    def generate_cost_report(self, output_base_dir: str = '.'):
        """生成费用分布报告"""
        self.logger.info("=" * 80)
        self.logger.info(f"💰 开始分析{self.tenant_name}的费用分布...")
        self.logger.info("=" * 80)
        
        analysis = self.analyze_cost_distribution()
        
        # 输出控制台报告
        self.print_cost_summary(analysis)
        
        # 生成HTML报告
        html_file = self.generate_html_report(analysis, output_base_dir)
        
        # 生成Excel报告
        excel_file = self.generate_excel_report(analysis, output_base_dir)
        
        self.logger.info(f"📊 HTML报告已生成: {html_file}")
        if excel_file:
            self.logger.info(f"📊 Excel报告已生成: {excel_file}")
        
        return {
            'html': html_file,
            'excel': excel_file,
            'analysis': analysis
        }
    
    def print_cost_summary(self, analysis: Dict):
        """打印费用汇总到控制台"""
        print("\n" + "=" * 80)
        print(f"💰 {self.tenant_name} 月度费用分布分析")
        print("=" * 80)
        
        print(f"\n📊 总体统计:")
        print(f"  • 总实例数: {analysis['total_instances']} 个")
        print(f"  • 月度总成本: ¥{analysis['total_monthly_cost']:,.2f}")
        print(f"  • 年度预估成本: ¥{analysis['total_monthly_cost'] * 12:,.2f}")
        
        print(f"\n📈 按资源类型分布（Top 10）:")
        print(f"{'排名':<6} {'资源类型':<15} {'实例数':<12} {'月度成本':<15} {'占比':<10}")
        print("-" * 65)
        
        sorted_resources = sorted(
            analysis['resource_cost_summary'].items(),
            key=lambda x: x[1]['total_cost'],
            reverse=True
        )[:10]
        
        for rank, (resource_type, data) in enumerate(sorted_resources, 1):
            print(f"{rank:<6} {resource_type:<15} {data['count']:<12} "
                  f"¥{data['total_cost']:>12,.2f}  {data['percentage']:>6.2f}%")
        
        print(f"\n🌍 按区域分布（Top 10）:")
        print(f"{'排名':<6} {'区域':<20} {'月度成本':<15} {'占比':<10}")
        print("-" * 50)
        
        sorted_regions = sorted(
            analysis['region_cost_summary'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        total_region_cost = sum(analysis['region_cost_summary'].values())
        
        for rank, (region, cost) in enumerate(sorted_regions, 1):
            percentage = (cost / total_region_cost * 100) if total_region_cost > 0 else 0
            print(f"{rank:<6} {region:<20} ¥{cost:>12,.2f}  {percentage:>6.2f}%")
        
        print("\n" + "=" * 80)
    
    def generate_html_report(self, analysis: Dict, output_base_dir: str) -> str:
        """生成HTML报告"""
        output_dir = Path(output_base_dir) / self.tenant_name / 'cost'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = output_dir / f'{self.tenant_name}_cost_distribution_{timestamp}.html'
        
        # 准备数据
        sorted_resources = sorted(
            analysis['resource_cost_summary'].items(),
            key=lambda x: x[1]['total_cost'],
            reverse=True
        )
        
        sorted_regions = sorted(
            analysis['region_cost_summary'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        total_region_cost = sum(analysis['region_cost_summary'].values())
        
        # 生成HTML
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.tenant_name} 月度费用分布分析</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #666;
            margin-top: 30px;
        }}
        .summary {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .summary-item {{
            display: inline-block;
            margin: 10px 20px;
            padding: 10px;
            background: white;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .summary-item strong {{
            color: #4CAF50;
            font-size: 1.2em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .cost-high {{
            color: #f44336;
            font-weight: bold;
        }}
        .cost-medium {{
            color: #ff9800;
        }}
        .cost-low {{
            color: #4CAF50;
        }}
        .percentage-bar {{
            background: #e0e0e0;
            border-radius: 10px;
            height: 20px;
            margin: 5px 0;
            overflow: hidden;
        }}
        .percentage-fill {{
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            height: 100%;
            border-radius: 10px;
            transition: width 0.3s;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>💰 {self.tenant_name} 月度费用分布分析报告</h1>
        <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary">
            <div class="summary-item">
                <strong>总实例数</strong><br>
                {analysis['total_instances']} 个
            </div>
            <div class="summary-item">
                <strong>月度总成本</strong><br>
                ¥{analysis['total_monthly_cost']:,.2f}
            </div>
            <div class="summary-item">
                <strong>年度预估成本</strong><br>
                ¥{analysis['total_monthly_cost'] * 12:,.2f}
            </div>
        </div>
        
        <h2>📈 按资源类型费用分布</h2>
        <table>
            <thead>
                <tr>
                    <th>排名</th>
                    <th>资源类型</th>
                    <th>实例数</th>
                    <th>月度成本</th>
                    <th>占比</th>
                    <th>可视化</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for rank, (resource_type, data) in enumerate(sorted_resources, 1):
            cost_class = 'cost-high' if data['percentage'] > 20 else ('cost-medium' if data['percentage'] > 10 else 'cost-low')
            html_content += f"""
                <tr>
                    <td>{rank}</td>
                    <td><strong>{resource_type}</strong></td>
                    <td>{data['count']}</td>
                    <td class="{cost_class}">¥{data['total_cost']:,.2f}</td>
                    <td>{data['percentage']:.2f}%</td>
                    <td>
                        <div class="percentage-bar">
                            <div class="percentage-fill" style="width: {data['percentage']}%"></div>
                        </div>
                    </td>
                </tr>
"""
        
        html_content += """
            </tbody>
        </table>
        
        <h2>🌍 按区域费用分布</h2>
        <table>
            <thead>
                <tr>
                    <th>排名</th>
                    <th>区域</th>
                    <th>月度成本</th>
                    <th>占比</th>
                    <th>可视化</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for rank, (region, cost) in enumerate(sorted_regions, 1):
            percentage = (cost / total_region_cost * 100) if total_region_cost > 0 else 0
            cost_class = 'cost-high' if percentage > 20 else ('cost-medium' if percentage > 10 else 'cost-low')
            html_content += f"""
                <tr>
                    <td>{rank}</td>
                    <td><strong>{region}</strong></td>
                    <td class="{cost_class}">¥{cost:,.2f}</td>
                    <td>{percentage:.2f}%</td>
                    <td>
                        <div class="percentage-bar">
                            <div class="percentage-fill" style="width: {percentage}%"></div>
                        </div>
                    </td>
                </tr>
"""
        
        html_content += """
            </tbody>
        </table>
        
        <h2>💡 费用优化建议</h2>
        <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <ul>
                <li><strong>重点关注资源:</strong> 费用占比超过20%的资源类型需要重点优化</li>
                <li><strong>区域优化:</strong> 考虑将资源集中在成本较低的区域</li>
                <li><strong>实例优化:</strong> 检查是否有闲置资源可以释放或降配</li>
                <li><strong>折扣分析:</strong> 建议运行折扣分析查看续费折扣情况</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(html_file)
    
    def generate_excel_report(self, analysis: Dict, output_base_dir: str) -> str:
        """生成Excel报告"""
        if not HAS_PANDAS:
            self.logger.warning("pandas未安装，跳过Excel报告生成")
            return ""
        
        output_dir = Path(output_base_dir) / self.tenant_name / 'cost'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_file = output_dir / f'{self.tenant_name}_cost_distribution_{timestamp}.xlsx'
        
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            # 按资源类型汇总
            resource_data = []
            for resource_type, data in analysis['resource_cost_summary'].items():
                resource_data.append({
                    '资源类型': resource_type,
                    '实例数': data['count'],
                    '月度成本(¥)': data['total_cost'],
                    '占比(%)': data['percentage']
                })
            
            df_resources = pd.DataFrame(resource_data)
            df_resources = df_resources.sort_values('月度成本(¥)', ascending=False)
            df_resources.to_excel(writer, sheet_name='按资源类型汇总', index=False)
            
            # 按区域汇总
            region_data = []
            total_region_cost = sum(analysis['region_cost_summary'].values())
            for region, cost in analysis['region_cost_summary'].items():
                percentage = (cost / total_region_cost * 100) if total_region_cost > 0 else 0
                region_data.append({
                    '区域': region,
                    '月度成本(¥)': cost,
                    '占比(%)': percentage
                })
            
            df_regions = pd.DataFrame(region_data)
            df_regions = df_regions.sort_values('月度成本(¥)', ascending=False)
            df_regions.to_excel(writer, sheet_name='按区域汇总', index=False)
            
            # 详细实例列表
            instance_data = []
            for inst in analysis['all_instances']:
                instance_data.append({
                    '资源类型': inst.get('resource_type', '').upper(),
                    '实例ID': inst.get('instance_id', ''),
                    '实例名称': inst.get('instance_name', ''),
                    '实例类型': inst.get('instance_type', ''),
                    '区域': inst.get('region', ''),
                    '状态': inst.get('status', ''),
                    '月度成本(¥)': inst.get('monthly_cost', 0)
                })
            
            if instance_data:
                df_instances = pd.DataFrame(instance_data)
                df_instances = df_instances.sort_values('月度成本(¥)', ascending=False)
                df_instances.to_excel(writer, sheet_name='实例明细', index=False)
        
        return str(excel_file)


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python cost_analyzer.py <tenant_name>")
        return
    
    tenant_name = sys.argv[1]
    
    # 加载配置
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ 配置文件 config.json 不存在")
        return
    
    tenants = config.get('tenants', {})
    if tenant_name not in tenants:
        print(f"❌ 未找到租户: {tenant_name}")
        return
    
    tenant_config = tenants[tenant_name]
    
    analyzer = CostAnalyzer(
        tenant_name,
        tenant_config['access_key_id'],
        tenant_config['access_key_secret']
    )
    
    analyzer.generate_cost_report()


if __name__ == "__main__":
    main()

