#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
折扣趋势分析器
基于阿里云账单CSV数据，分析最近6个月的折扣变化趋势
"""

import csv
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)


class DiscountTrendAnalyzer:
    """折扣趋势分析器"""
    
    def __init__(self, bill_data_dir: Optional[str] = None):
        """
        初始化折扣趋势分析器
        
        Args:
            bill_data_dir: 账单CSV文件目录，默认查找项目根目录下的账单文件夹
        """
        self.bill_data_dir = Path(bill_data_dir) if bill_data_dir else None
        self.cache_dir = Path.home() / ".cloudlens" / "discount_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def find_bill_directories(self, base_dir: str = ".") -> List[Path]:
        """
        查找账单CSV目录（支持多个账号的账单文件夹）
        
        Args:
            base_dir: 基础搜索目录
            
        Returns:
            账单目录列表
        """
        base_path = Path(base_dir)
        bill_dirs = []
        
        # 查找符合模式的目录：数字-账号名称/
        for item in base_path.iterdir():
            if item.is_dir() and any(csv_file.suffix == '.csv' for csv_file in item.glob('*.csv')):
                bill_dirs.append(item)
        
        return bill_dirs
    
    def parse_bill_csv(self, csv_path: Path) -> List[Dict]:
        """
        解析单个账单CSV文件
        
        Args:
            csv_path: CSV文件路径
            
        Returns:
            账单明细列表
        """
        records = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # 提取关键字段
                    try:
                        official_price = float(row.get('官网价', 0) or 0)
                        discount_amount = float(row.get('优惠金额', 0) or 0)
                        payable_amount = float(row.get('应付金额', 0) or 0)
                        final_amount = float(row.get('优惠后金额', 0) or 0)
                        
                        # 计算折扣率
                        discount_rate = 0.0
                        if official_price > 0:
                            discount_rate = (official_price - payable_amount) / official_price
                        
                        record = {
                            'billing_period': row.get('账期', '').strip(),
                            'product_code': row.get('产品Code', '').strip(),
                            'product_name': row.get('产品', '').strip(),
                            'instance_id': row.get('实例ID', '').strip(),
                            'instance_name': row.get('实例昵称', '').strip(),
                            'region': row.get('地域', '').strip(),
                            'billing_item': row.get('计费项', '').strip(),
                            'official_price': official_price,
                            'discount_amount': discount_amount,
                            'payable_amount': payable_amount,
                            'final_amount': final_amount,
                            'discount_rate': discount_rate,
                            'discount_name': row.get('优惠名称', '').strip(),
                            'single_product_discount': row.get('单品优惠', '').strip(),
                            'combo_discount': row.get('组合优惠', '').strip(),
                            'contract_no': row.get('合同编号', '').strip(),
                            'discount_type': row.get(' 优惠类型', '').strip(),  # 注意有空格
                            'discount_content': row.get('优惠内容', '').strip(),
                        }
                        
                        records.append(record)
                    except Exception as e:
                        # 跳过解析失败的行
                        continue
                        
        except Exception as e:
            logger.error(f"Failed to parse CSV {csv_path}: {e}")
        
        return records
    
    def aggregate_monthly_discounts(self, records: List[Dict]) -> Dict[str, Dict]:
        """
        按月聚合折扣数据
        
        Returns:
            {
                '2025-07': {
                    'total_official_price': float,  # 原价总额
                    'total_discount_amount': float,  # 折扣总额
                    'total_payable_amount': float,  # 应付总额
                    'average_discount_rate': float,  # 平均折扣率
                    'by_product': {...},  # 按产品聚合
                    'by_contract': {...},  # 按合同聚合
                }
            }
        """
        monthly_data = defaultdict(lambda: {
            'total_official_price': 0.0,
            'total_discount_amount': 0.0,
            'total_payable_amount': 0.0,
            'total_final_amount': 0.0,
            'record_count': 0,
            'by_product': defaultdict(lambda: {
                'official_price': 0.0,
                'discount_amount': 0.0,
                'payable_amount': 0.0,
                'discount_rate': 0.0,
                'record_count': 0,
            }),
            'by_contract': defaultdict(lambda: {
                'official_price': 0.0,
                'discount_amount': 0.0,
                'payable_amount': 0.0,
                'discount_rate': 0.0,
                'record_count': 0,
                'discount_name': '',
            }),
            'by_instance': defaultdict(lambda: {
                'instance_name': '',
                'product_name': '',
                'official_price': 0.0,
                'discount_amount': 0.0,
                'payable_amount': 0.0,
                'discount_rate': 0.0,
            }),
            'top_discounts': [],  # 最大折扣优惠
        })
        
        for record in records:
            period = record['billing_period']
            if not period:
                continue
            
            # 总体聚合
            monthly_data[period]['total_official_price'] += record['official_price']
            monthly_data[period]['total_discount_amount'] += record['discount_amount']
            monthly_data[period]['total_payable_amount'] += record['payable_amount']
            monthly_data[period]['total_final_amount'] += record['final_amount']
            monthly_data[period]['record_count'] += 1
            
            # 按产品聚合
            product = record['product_name'] or record['product_code']
            if product:
                monthly_data[period]['by_product'][product]['official_price'] += record['official_price']
                monthly_data[period]['by_product'][product]['discount_amount'] += record['discount_amount']
                monthly_data[period]['by_product'][product]['payable_amount'] += record['payable_amount']
                monthly_data[period]['by_product'][product]['record_count'] += 1
            
            # 按合同聚合
            contract = record['contract_no']
            if contract:
                monthly_data[period]['by_contract'][contract]['official_price'] += record['official_price']
                monthly_data[period]['by_contract'][contract]['discount_amount'] += record['discount_amount']
                monthly_data[period]['by_contract'][contract]['payable_amount'] += record['payable_amount']
                monthly_data[period]['by_contract'][contract]['record_count'] += 1
                if not monthly_data[period]['by_contract'][contract]['discount_name']:
                    monthly_data[period]['by_contract'][contract]['discount_name'] = record['discount_name']
            
            # 按实例聚合（只保存有折扣的）
            instance_id = record['instance_id']
            if instance_id and record['discount_amount'] > 0:
                monthly_data[period]['by_instance'][instance_id]['instance_name'] = record['instance_name']
                monthly_data[period]['by_instance'][instance_id]['product_name'] = record['product_name']
                monthly_data[period]['by_instance'][instance_id]['official_price'] += record['official_price']
                monthly_data[period]['by_instance'][instance_id]['discount_amount'] += record['discount_amount']
                monthly_data[period]['by_instance'][instance_id]['payable_amount'] += record['payable_amount']
        
        # 计算折扣率
        for period in monthly_data:
            # 总体折扣率
            if monthly_data[period]['total_official_price'] > 0:
                monthly_data[period]['average_discount_rate'] = (
                    monthly_data[period]['total_discount_amount'] / 
                    monthly_data[period]['total_official_price']
                )
            
            # 产品折扣率
            for product in monthly_data[period]['by_product']:
                product_data = monthly_data[period]['by_product'][product]
                if product_data['official_price'] > 0:
                    product_data['discount_rate'] = (
                        product_data['discount_amount'] / product_data['official_price']
                    )
            
            # 合同折扣率
            for contract in monthly_data[period]['by_contract']:
                contract_data = monthly_data[period]['by_contract'][contract]
                if contract_data['official_price'] > 0:
                    contract_data['discount_rate'] = (
                        contract_data['discount_amount'] / contract_data['official_price']
                    )
            
            # 实例折扣率
            for instance_id in monthly_data[period]['by_instance']:
                instance_data = monthly_data[period]['by_instance'][instance_id]
                if instance_data['official_price'] > 0:
                    instance_data['discount_rate'] = (
                        instance_data['discount_amount'] / instance_data['official_price']
                    )
        
        # 转换为普通dict（去除defaultdict）
        result = {}
        for period, data in monthly_data.items():
            result[period] = {
                'total_official_price': round(data['total_official_price'], 2),
                'total_discount_amount': round(data['total_discount_amount'], 2),
                'total_payable_amount': round(data['total_payable_amount'], 2),
                'total_final_amount': round(data['total_final_amount'], 2),
                'average_discount_rate': round(data['average_discount_rate'], 4),
                'record_count': data['record_count'],
                'by_product': dict(data['by_product']),
                'by_contract': dict(data['by_contract']),
                'by_instance': dict(data['by_instance']),
            }
        
        return result
    
    def analyze_discount_trend(
        self, 
        bill_dir: Path,
        months: int = 6,
        cache_hours: int = 24
    ) -> Dict:
        """
        分析折扣趋势（最近N个月）
        
        Args:
            bill_dir: 账单CSV目录
            months: 分析月数
            cache_hours: 缓存时长（小时）
            
        Returns:
            折扣趋势分析报告
        """
        # 检查缓存
        cache_file = self.cache_dir / f"{bill_dir.name}_discount_trend.json"
        if cache_file.exists():
            cache_age = (datetime.now().timestamp() - cache_file.stat().st_mtime) / 3600
            if cache_age < cache_hours:
                logger.info(f"Using cached discount trend data (age: {cache_age:.1f}h)")
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception:
                    pass
        
        # 查找并解析所有CSV文件
        csv_files = sorted(bill_dir.glob('*.csv'))
        if not csv_files:
            return {'error': 'No CSV files found in directory'}
        
        logger.info(f"Found {len(csv_files)} CSV files in {bill_dir}")
        
        all_records = []
        for csv_file in csv_files:
            logger.info(f"Parsing {csv_file.name}...")
            records = self.parse_bill_csv(csv_file)
            all_records.extend(records)
        
        logger.info(f"Total records parsed: {len(all_records)}")
        
        # 按月聚合
        monthly_aggregated = self.aggregate_monthly_discounts(all_records)
        
        # 排序月份（最近的在前）
        sorted_periods = sorted(monthly_aggregated.keys(), reverse=True)[:months]
        
        # 生成趋势分析
        trend_analysis = self._analyze_trends(monthly_aggregated, sorted_periods)
        
        # 生成产品级折扣分析
        product_analysis = self._analyze_product_discounts(monthly_aggregated, sorted_periods)
        
        # 生成合同级折扣分析
        contract_analysis = self._analyze_contract_discounts(monthly_aggregated, sorted_periods)
        
        # 生成实例级TOP折扣
        top_instance_discounts = self._analyze_top_instance_discounts(monthly_aggregated, sorted_periods)
        
        result = {
            'account_name': bill_dir.name.split('-')[0] if '-' in bill_dir.name else bill_dir.name,
            'analysis_periods': sorted_periods,
            'monthly_summary': {period: monthly_aggregated[period] for period in sorted_periods},
            'trend_analysis': trend_analysis,
            'product_analysis': product_analysis,
            'contract_analysis': contract_analysis,
            'top_instance_discounts': top_instance_discounts,
            'generated_at': datetime.now().isoformat(),
        }
        
        # 保存缓存
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
        
        return result
    
    def _analyze_trends(self, monthly_data: Dict, periods: List[str]) -> Dict:
        """
        分析折扣趋势变化
        
        Returns:
            趋势分析数据
        """
        if not periods or len(periods) < 2:
            return {'error': 'Insufficient data for trend analysis'}
        
        # 提取时间序列数据
        timeline = []
        for period in reversed(periods):  # 从旧到新
            if period in monthly_data:
                data = monthly_data[period]
                timeline.append({
                    'period': period,
                    'official_price': data['total_official_price'],
                    'discount_amount': data['total_discount_amount'],
                    'discount_rate': data['average_discount_rate'],
                    'payable_amount': data['total_payable_amount'],
                })
        
        # 计算变化趋势
        latest = timeline[-1]
        oldest = timeline[0]
        
        discount_rate_change = latest['discount_rate'] - oldest['discount_rate']
        discount_amount_change = latest['discount_amount'] - oldest['discount_amount']
        
        # 判断趋势
        trend_direction = '上升' if discount_rate_change > 0.01 else ('下降' if discount_rate_change < -0.01 else '平稳')
        
        # 计算平均折扣率
        avg_discount_rate = sum(t['discount_rate'] for t in timeline) / len(timeline)
        
        # 计算最大最小
        max_discount_rate = max(t['discount_rate'] for t in timeline)
        min_discount_rate = min(t['discount_rate'] for t in timeline)
        
        return {
            'timeline': timeline,
            'latest_period': latest['period'],
            'latest_discount_rate': round(latest['discount_rate'], 4),
            'discount_rate_change': round(discount_rate_change, 4),
            'discount_rate_change_pct': round(discount_rate_change * 100, 2),
            'discount_amount_change': round(discount_amount_change, 2),
            'trend_direction': trend_direction,
            'average_discount_rate': round(avg_discount_rate, 4),
            'max_discount_rate': round(max_discount_rate, 4),
            'min_discount_rate': round(min_discount_rate, 4),
            'total_savings_6m': round(sum(t['discount_amount'] for t in timeline), 2),
        }
    
    def _analyze_product_discounts(self, monthly_data: Dict, periods: List[str]) -> Dict:
        """
        分析产品级折扣趋势
        
        Returns:
            产品折扣分析
        """
        product_trends = defaultdict(lambda: {
            'periods': [],
            'discount_rates': [],
            'discount_amounts': [],
            'total_discount': 0.0,
        })
        
        for period in reversed(periods):
            if period not in monthly_data:
                continue
            
            for product, data in monthly_data[period]['by_product'].items():
                product_trends[product]['periods'].append(period)
                product_trends[product]['discount_rates'].append(data['discount_rate'])
                product_trends[product]['discount_amounts'].append(data['discount_amount'])
                product_trends[product]['total_discount'] += data['discount_amount']
        
        # 排序：按总折扣金额降序
        sorted_products = sorted(
            product_trends.items(),
            key=lambda x: x[1]['total_discount'],
            reverse=True
        )[:20]  # TOP 20产品
        
        result = {}
        for product, data in sorted_products:
            # 计算趋势
            if len(data['discount_rates']) >= 2:
                rate_change = data['discount_rates'][-1] - data['discount_rates'][0]
                trend = '上升' if rate_change > 0.01 else ('下降' if rate_change < -0.01 else '平稳')
            else:
                rate_change = 0
                trend = '数据不足'
            
            result[product] = {
                'total_discount': round(data['total_discount'], 2),
                'avg_discount_rate': round(sum(data['discount_rates']) / len(data['discount_rates']), 4) if data['discount_rates'] else 0,
                'latest_discount_rate': round(data['discount_rates'][-1], 4) if data['discount_rates'] else 0,
                'rate_change': round(rate_change, 4),
                'trend': trend,
                'periods': data['periods'],
                'discount_rates': [round(r, 4) for r in data['discount_rates']],
            }
        
        return result
    
    def _analyze_contract_discounts(self, monthly_data: Dict, periods: List[str]) -> Dict:
        """
        分析合同级折扣（商务折扣）
        
        Returns:
            合同折扣分析
        """
        contract_trends = defaultdict(lambda: {
            'periods': [],
            'discount_rates': [],
            'discount_amounts': [],
            'total_discount': 0.0,
            'discount_name': '',
        })
        
        for period in reversed(periods):
            if period not in monthly_data:
                continue
            
            for contract, data in monthly_data[period]['by_contract'].items():
                if not contract:
                    continue
                contract_trends[contract]['periods'].append(period)
                contract_trends[contract]['discount_rates'].append(data['discount_rate'])
                contract_trends[contract]['discount_amounts'].append(data['discount_amount'])
                contract_trends[contract]['total_discount'] += data['discount_amount']
                if not contract_trends[contract]['discount_name']:
                    contract_trends[contract]['discount_name'] = data['discount_name']
        
        # 排序：按总折扣金额降序
        sorted_contracts = sorted(
            contract_trends.items(),
            key=lambda x: x[1]['total_discount'],
            reverse=True
        )[:10]  # TOP 10合同
        
        result = {}
        for contract, data in sorted_contracts:
            result[contract] = {
                'discount_name': data['discount_name'],
                'total_discount': round(data['total_discount'], 2),
                'avg_discount_rate': round(sum(data['discount_rates']) / len(data['discount_rates']), 4) if data['discount_rates'] else 0,
                'latest_discount_rate': round(data['discount_rates'][-1], 4) if data['discount_rates'] else 0,
                'periods': data['periods'],
                'discount_amounts': [round(a, 2) for a in data['discount_amounts']],
            }
        
        return result
    
    def _analyze_top_instance_discounts(self, monthly_data: Dict, periods: List[str]) -> List[Dict]:
        """
        分析实例级TOP折扣（最近一个月）
        
        Returns:
            TOP折扣实例列表
        """
        if not periods:
            return []
        
        latest_period = periods[0]
        if latest_period not in monthly_data:
            return []
        
        instances = monthly_data[latest_period]['by_instance']
        
        # 排序：按折扣金额降序
        sorted_instances = sorted(
            instances.items(),
            key=lambda x: x[1]['discount_amount'],
            reverse=True
        )[:50]  # TOP 50实例
        
        result = []
        for instance_id, data in sorted_instances:
            if data['official_price'] > 0:
                discount_rate = data['discount_amount'] / data['official_price']
            else:
                discount_rate = 0
            
            result.append({
                'instance_id': instance_id,
                'instance_name': data['instance_name'],
                'product_name': data['product_name'],
                'official_price': round(data['official_price'], 2),
                'discount_amount': round(data['discount_amount'], 2),
                'payable_amount': round(data['payable_amount'], 2),
                'discount_rate': round(discount_rate, 4),
                'discount_pct': round(discount_rate * 100, 2),
            })
        
        return result
    
    def generate_discount_report(
        self,
        bill_dir: Path,
        output_format: str = 'html',
        output_path: Optional[str] = None
    ) -> str:
        """
        生成折扣趋势报告
        
        Args:
            bill_dir: 账单目录
            output_format: 输出格式（html/json/excel）
            output_path: 输出路径
            
        Returns:
            报告文件路径
        """
        analysis = self.analyze_discount_trend(bill_dir)
        
        if 'error' in analysis:
            logger.error(f"Analysis failed: {analysis['error']}")
            return ''
        
        if output_format == 'html':
            return self._generate_html_report(analysis, output_path)
        elif output_format == 'json':
            return self._generate_json_report(analysis, output_path)
        elif output_format == 'excel':
            return self._generate_excel_report(analysis, output_path)
        else:
            raise ValueError(f"Unsupported format: {output_format}")
    
    def _generate_html_report(self, analysis: Dict, output_path: Optional[str] = None) -> str:
        """生成HTML报告"""
        if not output_path:
            report_dir = Path.home() / "cloudlens_reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(report_dir / f"discount_trend_{timestamp}.html")
        
        trend = analysis['trend_analysis']
        product_analysis = analysis['product_analysis']
        contract_analysis = analysis['contract_analysis']
        top_instances = analysis['top_instance_discounts']
        
        # 准备图表数据
        chart_periods = trend['timeline']
        periods_labels = [t['period'] for t in chart_periods]
        discount_rates = [round(t['discount_rate'] * 100, 2) for t in chart_periods]
        official_prices = [t['official_price'] for t in chart_periods]
        discount_amounts = [t['discount_amount'] for t in chart_periods]
        
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CloudLens 折扣趋势分析报告</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f7fa;
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 28px;
        }}
        .header .meta {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 25px;
        }}
        .card h2 {{
            margin: 0 0 20px 0;
            color: #2c3e50;
            font-size: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        .stat-label {{
            color: #666;
            font-size: 14px;
        }}
        .stat-change {{
            font-size: 12px;
            margin-top: 5px;
        }}
        .stat-change.up {{ color: #10b981; }}
        .stat-change.down {{ color: #ef4444; }}
        .chart-container {{
            width: 100%;
            height: 400px;
            margin: 20px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}
        th {{
            background: #f9fafb;
            font-weight: 600;
            color: #374151;
        }}
        tr:hover {{
            background: #f9fafb;
        }}
        .trend-up {{ color: #10b981; font-weight: bold; }}
        .trend-down {{ color: #ef4444; font-weight: bold; }}
        .trend-stable {{ color: #6b7280; }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }}
        .badge-success {{ background: #d1fae5; color: #065f46; }}
        .badge-warning {{ background: #fef3c7; color: #92400e; }}
        .badge-danger {{ background: #fee2e2; color: #991b1b; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 折扣趋势分析报告</h1>
            <div class="meta">
                账号: {analysis['account_name']} | 
                分析周期: {', '.join(analysis['analysis_periods'])} | 
                生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
        
        <!-- 核心指标 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">最新折扣率</div>
                <div class="stat-value">{trend['latest_discount_rate']*100:.2f}%</div>
                <div class="stat-change {'up' if trend['discount_rate_change'] > 0 else 'down' if trend['discount_rate_change'] < 0 else ''}">
                    {trend['discount_rate_change_pct']:+.2f}% vs 首月
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-label">平均折扣率</div>
                <div class="stat-value">{trend['average_discount_rate']*100:.2f}%</div>
                <div class="stat-change">最近{len(analysis['analysis_periods'])}个月</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">折扣趋势</div>
                <div class="stat-value">{trend['trend_direction']}</div>
                <div class="stat-change">
                    范围: {trend['min_discount_rate']*100:.1f}% - {trend['max_discount_rate']*100:.1f}%
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-label">累计节省</div>
                <div class="stat-value">¥{trend['total_savings_6m']:,.0f}</div>
                <div class="stat-change">最近{len(analysis['analysis_periods'])}个月</div>
            </div>
        </div>
        
        <!-- 折扣率趋势图 -->
        <div class="card">
            <h2>📈 折扣率变化趋势</h2>
            <div id="discountRateTrend" class="chart-container"></div>
        </div>
        
        <!-- 折扣金额趋势图 -->
        <div class="card">
            <h2>💰 折扣金额变化趋势</h2>
            <div id="discountAmountTrend" class="chart-container"></div>
        </div>
        
        <!-- 产品折扣分析 -->
        <div class="card">
            <h2>🎯 产品折扣分析 (TOP 20)</h2>
            <table>
                <thead>
                    <tr>
                        <th>产品名称</th>
                        <th>累计折扣金额</th>
                        <th>平均折扣率</th>
                        <th>最新折扣率</th>
                        <th>折扣率变化</th>
                        <th>趋势</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for product, data in list(product_analysis.items())[:20]:
            trend_class = 'trend-up' if data['trend'] == '上升' else ('trend-down' if data['trend'] == '下降' else 'trend-stable')
            html_content += f"""
                    <tr>
                        <td><strong>{product}</strong></td>
                        <td>¥{data['total_discount']:,.2f}</td>
                        <td>{data['avg_discount_rate']*100:.2f}%</td>
                        <td>{data['latest_discount_rate']*100:.2f}%</td>
                        <td>{data['rate_change']*100:+.2f}%</td>
                        <td class="{trend_class}">{data['trend']}</td>
                    </tr>
"""
        
        html_content += """
                </tbody>
            </table>
        </div>
        
        <!-- 合同折扣分析 -->
        <div class="card">
            <h2>📄 合同折扣分析 (TOP 10)</h2>
            <table>
                <thead>
                    <tr>
                        <th>合同编号</th>
                        <th>优惠名称</th>
                        <th>累计折扣金额</th>
                        <th>平均折扣率</th>
                        <th>最新折扣率</th>
                        <th>覆盖月份</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for contract, data in list(contract_analysis.items())[:10]:
            html_content += f"""
                    <tr>
                        <td><code>{contract}</code></td>
                        <td>{data['discount_name']}</td>
                        <td>¥{data['total_discount']:,.2f}</td>
                        <td>{data['avg_discount_rate']*100:.2f}%</td>
                        <td>{data['latest_discount_rate']*100:.2f}%</td>
                        <td>{len(data['periods'])}个月</td>
                    </tr>
"""
        
        html_content += f"""
                </tbody>
            </table>
        </div>
        
        <!-- TOP折扣实例 -->
        <div class="card">
            <h2>🏆 折扣金额 TOP 50 实例（最近一个月）</h2>
            <table>
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>实例ID</th>
                        <th>实例名称</th>
                        <th>产品</th>
                        <th>官网价</th>
                        <th>折扣金额</th>
                        <th>折扣率</th>
                        <th>应付金额</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for rank, inst in enumerate(top_instances[:50], 1):
            badge_class = 'badge-success' if inst['discount_rate'] >= 0.5 else ('badge-warning' if inst['discount_rate'] >= 0.3 else 'badge-danger')
            html_content += f"""
                    <tr>
                        <td>{rank}</td>
                        <td><code>{inst['instance_id']}</code></td>
                        <td>{inst['instance_name'] or '-'}</td>
                        <td>{inst['product_name']}</td>
                        <td>¥{inst['official_price']:,.2f}</td>
                        <td>¥{inst['discount_amount']:,.2f}</td>
                        <td><span class="badge {badge_class}">{inst['discount_pct']:.1f}%</span></td>
                        <td>¥{inst['payable_amount']:,.2f}</td>
                    </tr>
"""
        
        html_content += """
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // 折扣率趋势图
        var discountRateChart = echarts.init(document.getElementById('discountRateTrend'));
        discountRateChart.setOption({
            title: { text: '折扣率变化趋势 (%)' },
            tooltip: { trigger: 'axis' },
            xAxis: { 
                type: 'category', 
                data: """ + json.dumps(periods_labels) + """
            },
            yAxis: { 
                type: 'value',
                name: '折扣率 (%)',
                axisLabel: { formatter: '{value}%' }
            },
            series: [{
                data: """ + json.dumps(discount_rates) + """,
                type: 'line',
                smooth: true,
                lineStyle: { width: 3, color: '#667eea' },
                areaStyle: { opacity: 0.2, color: '#667eea' },
                itemStyle: { color: '#667eea' },
                markLine: {
                    data: [{ type: 'average', name: '平均值' }]
                }
            }]
        });
        
        // 折扣金额趋势图
        var discountAmountChart = echarts.init(document.getElementById('discountAmountTrend'));
        discountAmountChart.setOption({
            title: { text: '折扣金额与官网价对比' },
            tooltip: { trigger: 'axis' },
            legend: { data: ['官网价', '折扣金额'] },
            xAxis: { 
                type: 'category', 
                data: """ + json.dumps(periods_labels) + """
            },
            yAxis: { 
                type: 'value',
                name: '金额 (¥)',
                axisLabel: { formatter: '¥{value}' }
            },
            series: [
                {
                    name: '官网价',
                    data: """ + json.dumps(official_prices) + """,
                    type: 'bar',
                    itemStyle: { color: '#93c5fd' }
                },
                {
                    name: '折扣金额',
                    data: """ + json.dumps(discount_amounts) + """,
                    type: 'bar',
                    itemStyle: { color: '#34d399' }
                }
            ]
        });
        
        window.onresize = function() {
            discountRateChart.resize();
            discountAmountChart.resize();
        };
    </script>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated: {output_path}")
        return output_path
    
    def _generate_json_report(self, analysis: Dict, output_path: Optional[str] = None) -> str:
        """生成JSON报告"""
        if not output_path:
            report_dir = Path.home() / "cloudlens_reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(report_dir / f"discount_trend_{timestamp}.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def _generate_excel_report(self, analysis: Dict, output_path: Optional[str] = None) -> str:
        """生成Excel报告"""
        try:
            import pandas as pd
        except ImportError:
            logger.warning("pandas not installed, skipping Excel report")
            return ''
        
        if not output_path:
            report_dir = Path.home() / "cloudlens_reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(report_dir / f"discount_trend_{timestamp}.xlsx")
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 趋势摘要
            trend = analysis['trend_analysis']
            summary_df = pd.DataFrame([{
                '指标': '最新折扣率',
                '数值': f"{trend['latest_discount_rate']*100:.2f}%"
            }, {
                '指标': '平均折扣率',
                '数值': f"{trend['average_discount_rate']*100:.2f}%"
            }, {
                '指标': '折扣率变化',
                '数值': f"{trend['discount_rate_change_pct']:+.2f}%"
            }, {
                '指标': '趋势方向',
                '数值': trend['trend_direction']
            }, {
                '指标': '累计节省',
                '数值': f"¥{trend['total_savings_6m']:,.2f}"
            }])
            summary_df.to_excel(writer, sheet_name='趋势摘要', index=False)
            
            # 月度明细
            timeline_df = pd.DataFrame(trend['timeline'])
            timeline_df.to_excel(writer, sheet_name='月度明细', index=False)
            
            # 产品折扣分析
            product_data = []
            for product, data in analysis['product_analysis'].items():
                product_data.append({
                    '产品名称': product,
                    '累计折扣金额': data['total_discount'],
                    '平均折扣率': f"{data['avg_discount_rate']*100:.2f}%",
                    '最新折扣率': f"{data['latest_discount_rate']*100:.2f}%",
                    '折扣率变化': f"{data['rate_change']*100:+.2f}%",
                    '趋势': data['trend'],
                })
            if product_data:
                product_df = pd.DataFrame(product_data)
                product_df.to_excel(writer, sheet_name='产品折扣分析', index=False)
            
            # TOP实例折扣
            top_inst_df = pd.DataFrame(analysis['top_instance_discounts'])
            if not top_inst_df.empty:
                top_inst_df.to_excel(writer, sheet_name='TOP50实例折扣', index=False)
        
        logger.info(f"Excel report generated: {output_path}")
        return output_path


def main():
    """测试主函数"""
    import sys
    
    analyzer = DiscountTrendAnalyzer()
    
    # 查找账单目录
    bill_dirs = analyzer.find_bill_directories()
    
    if not bill_dirs:
        print("未找到账单CSV目录")
        return
    
    print(f"找到 {len(bill_dirs)} 个账单目录:")
    for bill_dir in bill_dirs:
        print(f"  - {bill_dir}")
    
    # 分析第一个目录
    if bill_dirs:
        print(f"\n分析账单目录: {bill_dirs[0]}")
        result = analyzer.analyze_discount_trend(bill_dirs[0])
        
        if 'error' not in result:
            print("\n✅ 分析完成!")
            print(f"  账期: {', '.join(result['analysis_periods'])}")
            trend = result['trend_analysis']
            print(f"  最新折扣率: {trend['latest_discount_rate']*100:.2f}%")
            print(f"  平均折扣率: {trend['average_discount_rate']*100:.2f}%")
            print(f"  趋势方向: {trend['trend_direction']}")
            print(f"  累计节省: ¥{trend['total_savings_6m']:,.2f}")
            
            # 生成报告
            html_path = analyzer.generate_discount_report(bill_dirs[0], output_format='html')
            print(f"\n📊 HTML报告: {html_path}")
        else:
            print(f"\n❌ 分析失败: {result['error']}")


if __name__ == '__main__':
    main()


