#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级折扣分析器 - Phase 1/2/3
支持多维度深度分析
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import statistics

# 移除sqlite3导入，改用数据库抽象层

logger = logging.getLogger(__name__)


class AdvancedDiscountAnalyzer:
    """高级折扣分析器"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化分析器
        
        Args:
            db_path: 数据库路径（仅SQLite使用），默认使用~/.cloudlens/bills.db
        """
        from cloudlens.core.bill_storage import BillStorageManager
        self.storage = BillStorageManager(db_path)
        self.db = self.storage.db  # 使用数据库抽象层
        self.db_type = self.storage.db_type
    
    def _get_placeholder(self) -> str:
        """获取SQL占位符"""
        return "?" if self.db_type == "sqlite" else "%s"
    
    def _query_db(self, sql: str, params: Optional[Tuple] = None) -> List:
        """执行数据库查询（统一接口）"""
        # 替换占位符
        placeholder = self._get_placeholder()
        sql = sql.replace("?", placeholder) if self.db_type == "mysql" else sql
        return self.db.query(sql, params)
    
    # ==================== Phase 1: 核心分析功能 ====================
    
    def get_quarterly_comparison(
        self,
        account_id: str,
        quarters: int = 8,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        季度对比分析
        
        Args:
            account_id: 账号ID
            quarters: 分析季度数
            start_date: 开始日期 (YYYY-MM格式)
            end_date: 结束日期 (YYYY-MM格式)
            
        Returns:
            季度对比数据
        """
        logger.info(f"开始季度对比分析，账号={account_id}, 季度数={quarters}, 时间范围={start_date}~{end_date}")
        
        try:
            # 构建时间过滤条件
            placeholder = self._get_placeholder()
            time_filter = ""
            params = [account_id]
            if start_date:
                time_filter += f" AND billing_cycle >= {placeholder}"
                params.append(start_date)
            if end_date:
                time_filter += f" AND billing_cycle <= {placeholder}"
                params.append(end_date)
            
            params.append(quarters)
            
            # 使用数据库抽象层查询
            # MySQL使用CAST(... AS UNSIGNED)，SQLite使用CAST(... AS INT)
            cast_expr = "CAST(SUBSTR(billing_cycle, 6, 2) AS UNSIGNED)" if self.db_type == "mysql" else "CAST(SUBSTR(billing_cycle, 6, 2) AS INT)"
            rows = self._query_db(f"""
                SELECT 
                    SUBSTR(billing_cycle, 1, 4) as year,
                    CASE 
                        WHEN {cast_expr} <= 3 THEN 'Q1'
                        WHEN {cast_expr} <= 6 THEN 'Q2'
                        WHEN {cast_expr} <= 9 THEN 'Q3'
                        ELSE 'Q4'
                    END as quarter,
                    SUM(pretax_amount + invoice_discount) as total_original,
                    SUM(pretax_amount) as total_paid,
                    SUM(invoice_discount) as total_discount,
                    CASE 
                        WHEN SUM(pretax_amount + invoice_discount) > 0 
                        THEN (SUM(invoice_discount) / SUM(pretax_amount + invoice_discount))
                        ELSE 0 
                    END as avg_discount_rate,
                    COUNT(DISTINCT billing_cycle) as month_count
                FROM bill_items
                WHERE account_id = {placeholder} {time_filter}
                GROUP BY year, quarter
                ORDER BY year DESC, 
                    CASE quarter 
                        WHEN 'Q1' THEN 1 
                        WHEN 'Q2' THEN 2 
                        WHEN 'Q3' THEN 3 
                        WHEN 'Q4' THEN 4 
                    END DESC
                LIMIT {placeholder}
            """, tuple(params))
            
            quarterly_data = []
            for row in rows:
                # 处理字典格式的结果（MySQL）或元组格式（SQLite）
                if isinstance(row, dict):
                    quarterly_data.append({
                        'year': row['year'],
                        'quarter': row['quarter'],
                        'period': f"{row['year']}-{row['quarter']}",
                        'total_original': float(row['total_original'] or 0),
                        'total_paid': float(row['total_paid'] or 0),
                        'total_discount': float(row['total_discount'] or 0),
                        'avg_discount_rate': float(row['avg_discount_rate'] or 0),
                        'month_count': int(row['month_count'] or 0)
                    })
                else:
                    # SQLite返回元组
                    quarterly_data.append({
                        'year': row[0],
                        'quarter': row[1],
                        'period': f"{row[0]}-{row[1]}",
                        'total_original': float(row[2] or 0),
                        'total_paid': float(row[3] or 0),
                        'total_discount': float(row[4] or 0),
                        'avg_discount_rate': float(row[5] or 0),
                        'month_count': int(row[6] or 0)
                    })
            
            quarterly_data.reverse()  # 按时间正序
            
            # 计算环比变化
            for i in range(1, len(quarterly_data)):
                prev = quarterly_data[i-1]
                curr = quarterly_data[i]
                
                if prev['avg_discount_rate'] > 0:
                    curr['rate_change'] = (
                        (curr['avg_discount_rate'] - prev['avg_discount_rate']) / 
                        prev['avg_discount_rate'] * 100
                    )
                else:
                    curr['rate_change'] = 0
            
            if quarterly_data:
                quarterly_data[0]['rate_change'] = 0
            
            return {
                'success': True,
                'quarters': quarterly_data,
                'total_quarters': len(quarterly_data)
            }
        
        except Exception as e:
            logger.error(f"季度对比分析失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def get_yearly_comparison(
        self,
        account_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        年度对比分析
        
        Args:
            account_id: 账号ID
            start_date: 开始日期 (YYYY-MM格式)
            end_date: 结束日期 (YYYY-MM格式)
            
        Returns:
            年度对比数据
        """
        logger.info(f"开始年度对比分析，账号={account_id}, 时间范围={start_date}~{end_date}")
        
        try:
            # 构建时间过滤条件
            placeholder = self._get_placeholder()
            time_filter = ""
            params = [account_id]
            if start_date:
                time_filter += f" AND billing_cycle >= {placeholder}"
                params.append(start_date)
            if end_date:
                time_filter += f" AND billing_cycle <= {placeholder}"
                params.append(end_date)
            
            # 年度总览
            rows = self._query_db(f"""
                SELECT 
                    SUBSTR(billing_cycle, 1, 4) as year,
                    COUNT(DISTINCT billing_cycle) as month_count,
                    SUM(pretax_amount + invoice_discount) as total_original,
                    SUM(pretax_amount) as total_paid,
                    SUM(invoice_discount) as total_discount,
                    CASE 
                        WHEN SUM(pretax_amount + invoice_discount) > 0 
                        THEN (SUM(invoice_discount) / SUM(pretax_amount + invoice_discount))
                        ELSE 0 
                    END as avg_discount_rate
                FROM bill_items
                WHERE account_id = {placeholder} {time_filter}
                GROUP BY year
                ORDER BY year
            """, tuple(params))
            
            yearly_data = []
            for row in rows:
                # 处理字典格式的结果（MySQL）或元组格式（SQLite）
                if isinstance(row, dict):
                    yearly_data.append({
                        'year': row['year'],
                        'month_count': int(row['month_count'] or 0),
                        'total_original': float(row['total_original'] or 0),
                        'total_paid': float(row['total_paid'] or 0),
                        'total_discount': float(row['total_discount'] or 0),
                        'avg_discount_rate': float(row['avg_discount_rate'] or 0)
                    })
                else:
                    # SQLite返回元组
                    yearly_data.append({
                        'year': row[0],
                        'month_count': int(row[1] or 0),
                        'total_original': float(row[2] or 0),
                        'total_paid': float(row[3] or 0),
                        'total_discount': float(row[4] or 0),
                        'avg_discount_rate': float(row[5] or 0)
                    })
            
            # 计算同比变化
            for i in range(1, len(yearly_data)):
                prev = yearly_data[i-1]
                curr = yearly_data[i]
                
                curr['yoy_consumption_growth'] = (
                    (curr['total_paid'] - prev['total_paid']) / prev['total_paid'] * 100
                    if prev['total_paid'] > 0 else 0
                )
                curr['yoy_discount_growth'] = (
                    (curr['total_discount'] - prev['total_discount']) / prev['total_discount'] * 100
                    if prev['total_discount'] > 0 else 0
                )
                curr['yoy_rate_change'] = (
                    (curr['avg_discount_rate'] - prev['avg_discount_rate']) / prev['avg_discount_rate'] * 100
                    if prev['avg_discount_rate'] > 0 else 0
                )
            
            if yearly_data:
                yearly_data[0]['yoy_consumption_growth'] = 0
                yearly_data[0]['yoy_discount_growth'] = 0
                yearly_data[0]['yoy_rate_change'] = 0
            
            return {
                'success': True,
                'years': yearly_data,
                'total_years': len(yearly_data)
            }
        
        except Exception as e:
            logger.error(f"年度对比分析失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def get_product_discount_trends(
        self,
        account_id: str,
        months: int = 19,
        top_n: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        产品折扣趋势分析（每个产品的月度折扣变化）
        
        Args:
            account_id: 账号ID
            months: 分析月数
            top_n: TOP N产品
            start_date: 开始日期 (YYYY-MM格式)
            end_date: 结束日期 (YYYY-MM格式)
            
        Returns:
            产品趋势数据
        """
        logger.info(f"开始产品折扣趋势分析，账号={account_id}, 月数={months}, TOP={top_n}, 时间范围={start_date}~{end_date}")
        
        try:
            # 构建时间过滤条件
            placeholder = self._get_placeholder()
            time_filter = ""
            params = [account_id]
            if start_date:
                time_filter += f" AND billing_cycle >= {placeholder}"
                params.append(start_date)
            if end_date:
                time_filter += f" AND billing_cycle <= {placeholder}"
                params.append(end_date)
            
            params.append(top_n)
            
            # 先获取TOP N产品（按消费金额）
            rows = self._query_db(f"""
                SELECT 
                    product_name,
                    SUM(pretax_amount) as total_paid
                FROM bill_items
                WHERE account_id = {placeholder}
                    AND product_name != ''
                    {time_filter}
                GROUP BY product_name
                ORDER BY total_paid DESC
                LIMIT {placeholder}
            """, tuple(params))
            
            top_products = [row['product_name'] if isinstance(row, dict) else row[0] for row in rows]
            
            if not top_products:
                return {'success': False, 'error': f'没有产品数据 (account_id={account_id})'}
            
            # 获取这些产品的月度趋势
            placeholders = ','.join([placeholder for _ in top_products])
            
            # 重建时间过滤条件和参数
            time_filter2 = ""
            params2 = [account_id]
            if start_date:
                time_filter2 += f" AND billing_cycle >= {placeholder}"
                params2.append(start_date)
            if end_date:
                time_filter2 += f" AND billing_cycle <= {placeholder}"
                params2.append(end_date)
            
            query = f"""
                SELECT 
                    product_name,
                    billing_cycle,
                    SUM(pretax_amount + invoice_discount) as official_price,
                    SUM(pretax_amount) as paid_amount,
                    SUM(invoice_discount) as discount_amount,
                    CASE 
                        WHEN SUM(pretax_amount + invoice_discount) > 0 
                        THEN (SUM(invoice_discount) / SUM(pretax_amount + invoice_discount))
                        ELSE 0 
                    END as discount_rate,
                    COUNT(*) as record_count,
                    COUNT(DISTINCT instance_id) as instance_count
                FROM bill_items
                WHERE account_id = {placeholder} 
                    {time_filter2}
                    AND product_name IN ({placeholders})
                GROUP BY product_name, billing_cycle
                ORDER BY product_name, billing_cycle
            """
            
            rows2 = self._query_db(query, tuple(params2 + top_products))
            
            # 按产品分组
            product_trends = defaultdict(list)
            for row in rows2:
                # 处理字典格式的结果（MySQL）或元组格式（SQLite）
                if isinstance(row, dict):
                    product_trends[row['product_name']].append({
                        'month': row['billing_cycle'],
                        'official_price': float(row['official_price'] or 0),
                        'paid_amount': float(row['paid_amount'] or 0),
                        'discount_amount': float(row['discount_amount'] or 0),
                        'discount_rate': float(row['discount_rate'] or 0),
                        'record_count': int(row['record_count'] or 0),
                        'instance_count': int(row['instance_count'] or 0)
                    })
                else:
                    product_trends[row[0]].append({
                        'month': row[1],
                        'official_price': float(row[2] or 0),
                        'paid_amount': float(row[3] or 0),
                        'discount_amount': float(row[4] or 0),
                        'discount_rate': float(row[5] or 0),
                        'record_count': int(row[6] or 0),
                        'instance_count': int(row[7] or 0)
                    })
            
            # 计算每个产品的统计指标
            product_stats = []
            for product_name, trends in product_trends.items():
                discount_rates = [t['discount_rate'] for t in trends]
                
                # 计算波动率（标准差）
                volatility = statistics.stdev(discount_rates) if len(discount_rates) > 1 else 0
                
                # 计算趋势（首尾对比）
                if len(trends) >= 2:
                    first_rate = trends[0]['discount_rate']
                    last_rate = trends[-1]['discount_rate']
                    trend_change = ((last_rate - first_rate) / first_rate * 100) if first_rate > 0 else 0
                else:
                    trend_change = 0
                
                product_stats.append({
                    'product_name': product_name,
                    'trends': trends,
                    'avg_discount_rate': sum(discount_rates) / len(discount_rates),
                    'min_discount_rate': min(discount_rates),
                    'max_discount_rate': max(discount_rates),
                    'volatility': volatility,
                    'trend_change_pct': trend_change,
                    'total_consumption': sum(t['paid_amount'] for t in trends),
                    'total_discount': sum(t['discount_amount'] for t in trends)
                })
            
            # 按总消费排序
            product_stats.sort(key=lambda x: x['total_consumption'], reverse=True)
            
            return {
                'success': True,
                'products': product_stats,
                'total_products': len(product_stats)
            }
        
        except Exception as e:
            logger.error(f"产品趋势分析失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def get_region_discount_ranking(
        self,
        account_id: str,
        months: int = 19,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        区域折扣排行分析
        
        Args:
            account_id: 账号ID
            months: 分析月数
            start_date: 开始日期 (YYYY-MM格式)
            end_date: 结束日期 (YYYY-MM格式)
            
        Returns:
            区域排行数据
        """
        logger.info(f"开始区域折扣排行分析，账号={account_id}, 月数={months}, 时间范围={start_date}~{end_date}")
        
        try:
            # 构建时间过滤条件
            placeholder = self._get_placeholder()
            time_filter = ""
            params = [account_id]
            if start_date:
                time_filter += f" AND billing_cycle >= {placeholder}"
                params.append(start_date)
            if end_date:
                time_filter += f" AND billing_cycle <= {placeholder}"
                params.append(end_date)
            
            rows = self._query_db(f"""
                SELECT 
                    region,
                    SUM(pretax_amount + invoice_discount) as total_original,
                    SUM(pretax_amount) as total_paid,
                    SUM(invoice_discount) as total_discount,
                    CASE 
                        WHEN SUM(pretax_amount + invoice_discount) > 0 
                        THEN (SUM(invoice_discount) / SUM(pretax_amount + invoice_discount))
                        ELSE 0 
                    END as avg_discount_rate,
                    COUNT(DISTINCT instance_id) as instance_count,
                    COUNT(DISTINCT product_name) as product_count,
                    COUNT(DISTINCT billing_cycle) as month_count
                FROM bill_items
                WHERE account_id = {placeholder}
                    AND region != ''
                    {time_filter}
                GROUP BY region
                ORDER BY total_paid DESC
            """, tuple(params))
            
            regions = []
            for row in rows:
                # 处理字典格式的结果（MySQL）或元组格式（SQLite）
                if isinstance(row, dict):
                    regions.append({
                        'region': row['region'],
                        'region_name': self._get_region_name(row['region']),
                        'total_original': float(row['total_original'] or 0),
                        'total_paid': float(row['total_paid'] or 0),
                        'total_discount': float(row['total_discount'] or 0),
                        'avg_discount_rate': float(row['avg_discount_rate'] or 0),
                        'instance_count': int(row['instance_count'] or 0),
                        'product_count': int(row['product_count'] or 0),
                        'month_count': int(row['month_count'] or 0),
                        'consumption_percentage': 0  # 将在后面计算
                    })
                else:
                    regions.append({
                        'region': row[0],
                        'region_name': self._get_region_name(row[0]),
                        'total_original': float(row[1] or 0),
                        'total_paid': float(row[2] or 0),
                        'total_discount': float(row[3] or 0),
                        'avg_discount_rate': float(row[4] or 0),
                        'instance_count': int(row[5] or 0),
                        'product_count': int(row[6] or 0),
                        'month_count': int(row[7] or 0),
                        'consumption_percentage': 0  # 将在后面计算
                    })
            
            # 计算消费占比
            total_consumption = sum(r['total_paid'] for r in regions)
            for r in regions:
                r['consumption_percentage'] = (
                    r['total_paid'] / total_consumption * 100 if total_consumption > 0 else 0
                )
            
            return {
                'success': True,
                'regions': regions,
                'total_regions': len(regions)
            }
        
        except Exception as e:
            logger.error(f"区域排行分析失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def get_subscription_type_comparison(
        self,
        account_id: str,
        months: int = 19,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        计费方式对比分析（包年包月 vs 按量付费）
        
        Args:
            account_id: 账号ID
            months: 分析月数
            start_date: 开始日期 (YYYY-MM格式)
            end_date: 结束日期 (YYYY-MM格式)
            
        Returns:
            计费方式对比数据
        """
        logger.info(f"开始计费方式对比分析，账号={account_id}, 月数={months}, 时间范围={start_date}~{end_date}")
        
        try:
            # 构建时间过滤条件
            placeholder = self._get_placeholder()
            time_filter = ""
            params = [account_id]
            if start_date:
                time_filter += f" AND billing_cycle >= {placeholder}"
                params.append(start_date)
            if end_date:
                time_filter += f" AND billing_cycle <= {placeholder}"
                params.append(end_date)
            
            # 总体对比
            rows = self._query_db(f"""
                SELECT 
                    subscription_type,
                    SUM(pretax_amount + invoice_discount) as total_original,
                    SUM(pretax_amount) as total_paid,
                    SUM(invoice_discount) as total_discount,
                    CASE 
                        WHEN SUM(pretax_amount + invoice_discount) > 0 
                        THEN (SUM(invoice_discount) / SUM(pretax_amount + invoice_discount))
                        ELSE 0 
                    END as avg_discount_rate,
                    COUNT(DISTINCT instance_id) as instance_count,
                    AVG(pretax_amount) as avg_instance_cost
                FROM bill_items
                WHERE account_id = {placeholder}
                    AND subscription_type IN ('Subscription', 'PayAsYouGo')
                    {time_filter}
                GROUP BY subscription_type
            """, tuple(params))
            
            subscription_types = {}
            for row in rows:
                # 处理字典格式的结果（MySQL）或元组格式（SQLite）
                if isinstance(row, dict):
                    sub_type = row['subscription_type']
                    type_name = '包年包月' if sub_type == 'Subscription' else '按量付费'
                    
                    subscription_types[sub_type] = {
                        'type': sub_type,
                        'type_name': type_name,
                        'total_original': float(row['total_original'] or 0),
                        'total_paid': float(row['total_paid'] or 0),
                        'total_discount': float(row['total_discount'] or 0),
                        'avg_discount_rate': float(row['avg_discount_rate'] or 0),
                        'instance_count': int(row['instance_count'] or 0),
                        'avg_instance_cost': float(row['avg_instance_cost'] or 0)
                    }
                else:
                    sub_type = row[0]
                    type_name = '包年包月' if sub_type == 'Subscription' else '按量付费'
                    
                    subscription_types[sub_type] = {
                        'type': sub_type,
                        'type_name': type_name,
                        'total_original': float(row[1] or 0),
                        'total_paid': float(row[2] or 0),
                        'total_discount': float(row[3] or 0),
                        'avg_discount_rate': float(row[4] or 0),
                        'instance_count': int(row[5] or 0),
                        'avg_instance_cost': float(row[6] or 0)
                    }
            
            # 计算占比
            total_consumption = sum(s['total_paid'] for s in subscription_types.values())
            for sub in subscription_types.values():
                sub['consumption_percentage'] = (
                    sub['total_paid'] / total_consumption * 100 if total_consumption > 0 else 0
                )
            
            # 计算折扣率差异
            if 'Subscription' in subscription_types and 'PayAsYouGo' in subscription_types:
                rate_diff = (
                    subscription_types['Subscription']['avg_discount_rate'] - 
                    subscription_types['PayAsYouGo']['avg_discount_rate']
                )
            else:
                rate_diff = 0
            
            # 月度趋势
            placeholder = self._get_placeholder()
            rows2 = self._query_db(f"""
                SELECT 
                    billing_cycle,
                    subscription_type,
                    SUM(pretax_amount) as total_paid,
                    CASE 
                        WHEN SUM(pretax_amount + invoice_discount) > 0 
                        THEN (SUM(invoice_discount) / SUM(pretax_amount + invoice_discount))
                        ELSE 0 
                    END as avg_discount_rate
                FROM bill_items
                WHERE account_id = {placeholder}
                    AND subscription_type IN ('Subscription', 'PayAsYouGo')
                GROUP BY billing_cycle, subscription_type
                ORDER BY billing_cycle, subscription_type
            """, (account_id,))
            
            monthly_trends = defaultdict(lambda: defaultdict(dict))
            for row in rows2:
                # 处理字典格式的结果（MySQL）或元组格式（SQLite）
                if isinstance(row, dict):
                    month = row['billing_cycle']
                    sub_type = row['subscription_type']
                    monthly_trends[month][sub_type] = {
                        'total_paid': float(row['total_paid'] or 0),
                        'discount_rate': float(row['avg_discount_rate'] or 0)
                    }
                else:
                    month = row[0]
                    sub_type = row[1]
                    monthly_trends[month][sub_type] = {
                        'total_paid': float(row[2] or 0),
                        'discount_rate': float(row[3] or 0)
                    }
            
            # 转换为列表格式
            monthly_data = []
            for month in sorted(monthly_trends.keys()):
                month_data = {
                    'month': month,
                    'subscription': monthly_trends[month].get('Subscription', {}),
                    'pay_as_you_go': monthly_trends[month].get('PayAsYouGo', {})
                }
                monthly_data.append(month_data)
            
            return {
                'success': True,
                'subscription_types': subscription_types,
                'rate_difference': rate_diff,
                'monthly_trends': monthly_data
            }
        
        except Exception as e:
            logger.error(f"计费方式对比分析失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def get_optimization_suggestions(
        self,
        account_id: str,
        min_running_months: int = 6,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        优化建议：识别长期运行的按量付费实例
        
        Args:
            account_id: 账号ID
            min_running_months: 最少运行月数
            start_date: 开始日期 (YYYY-MM格式)
            end_date: 结束日期 (YYYY-MM格式)
            
        Returns:
            优化建议列表
        """
        logger.info(f"开始生成优化建议，账号={account_id}, 时间范围={start_date}~{end_date}")
        
        try:
            # 构建时间过滤条件
            placeholder = self._get_placeholder()
            time_filter = ""
            params = [account_id]
            if start_date:
                time_filter += f" AND billing_cycle >= {placeholder}"
                params.append(start_date)
            if end_date:
                time_filter += f" AND billing_cycle <= {placeholder}"
                params.append(end_date)
            
            params.append(min_running_months)
            
            rows = self._query_db(f"""
                SELECT 
                    instance_id,
                    product_name,
                    region,
                    MIN(billing_cycle) as first_month,
                    MAX(billing_cycle) as last_month,
                    COUNT(DISTINCT billing_cycle) as running_months,
                    SUM(pretax_amount) as total_cost,
                    AVG(pretax_amount) as avg_monthly_cost,
                    AVG(CASE 
                        WHEN (pretax_amount + invoice_discount) > 0 
                        THEN (invoice_discount / (pretax_amount + invoice_discount))
                        ELSE 0 
                    END) as avg_discount_rate
                FROM bill_items
                WHERE account_id = {placeholder}
                    AND subscription_type = 'PayAsYouGo'
                    AND instance_id != ''
                    {time_filter}
                GROUP BY instance_id, product_name, region
                HAVING running_months >= {placeholder}
                ORDER BY total_cost DESC
                LIMIT 50
            """, tuple(params))
            
            suggestions = []
            for row in rows:
                # 处理字典格式的结果（MySQL）或元组格式（SQLite）
                if isinstance(row, dict):
                    current_rate = float(row['avg_discount_rate'] or 0)
                    total_cost = float(row['total_cost'] or 0)
                    estimated_subscription_rate = min(current_rate + 0.13, 0.70)
                    potential_savings = total_cost * (estimated_subscription_rate - current_rate)
                    
                    suggestions.append({
                        'instance_id': row['instance_id'],
                        'product_name': row['product_name'],
                        'region': row['region'],
                        'region_name': self._get_region_name(row['region']),
                        'first_month': row['first_month'],
                        'last_month': row['last_month'],
                        'running_months': int(row['running_months'] or 0),
                        'total_cost': total_cost,
                        'avg_monthly_cost': float(row['avg_monthly_cost'] or 0),
                        'current_discount_rate': current_rate,
                        'estimated_subscription_rate': estimated_subscription_rate,
                        'annual_potential_savings': potential_savings,
                        'suggestion': f"建议转为包年包月，预计年节省 ¥{potential_savings:,.0f}"
                    })
                else:
                    # SQLite返回元组
                    current_rate = float(row[8] or 0)
                    estimated_subscription_rate = min(current_rate + 0.13, 0.70)
                    potential_savings = float(row[6] or 0) * (estimated_subscription_rate - current_rate)
                    
                    suggestions.append({
                        'instance_id': row[0],
                        'product_name': row[1],
                        'region': row[2],
                        'region_name': self._get_region_name(row[2]),
                        'first_month': row[3],
                        'last_month': row[4],
                        'running_months': int(row[5] or 0),
                        'total_cost': float(row[6] or 0),
                        'avg_monthly_cost': float(row[7] or 0),
                        'current_discount_rate': current_rate,
                        'estimated_subscription_rate': estimated_subscription_rate,
                        'annual_potential_savings': potential_savings,
                        'suggestion': f"建议转为包年包月，预计年节省 ¥{potential_savings:,.0f}"
                    })
            
            # 计算总节省潜力
            total_potential_savings = sum(s['annual_potential_savings'] for s in suggestions)
            
            return {
                'success': True,
                'suggestions': suggestions,
                'total_suggestions': len(suggestions),
                'total_potential_savings': total_potential_savings
            }
        
        except Exception as e:
            logger.error(f"生成优化建议失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def detect_anomalies(
        self,
        account_id: str,
        months: int = 19,
        threshold: float = 0.10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        异常检测：识别折扣率波动异常的月份
        
        Args:
            account_id: 账号ID
            months: 分析月数
            threshold: 异常阈值（默认10%）
            start_date: 开始日期 (YYYY-MM格式)
            end_date: 结束日期 (YYYY-MM格式)
            
        Returns:
            异常检测结果
        """
        logger.info(f"开始异常检测，账号={account_id}, 阈值={threshold*100}%, 时间范围={start_date}~{end_date}")
        
        try:
            # 构建时间过滤条件
            placeholder = self._get_placeholder()
            time_filter = ""
            params = [account_id]
            if start_date:
                time_filter += f" AND billing_cycle >= {placeholder}"
                params.append(start_date)
            if end_date:
                time_filter += f" AND billing_cycle <= {placeholder}"
                params.append(end_date)
            
            # 获取月度折扣率
            rows = self._query_db(f"""
                SELECT 
                    billing_cycle,
                    SUM(pretax_amount + invoice_discount) as official_price,
                    SUM(pretax_amount) as actual_amount,
                    SUM(invoice_discount) as discount_amount,
                    CASE 
                        WHEN SUM(pretax_amount + invoice_discount) > 0 
                        THEN (SUM(invoice_discount) / SUM(pretax_amount + invoice_discount))
                        ELSE 0 
                    END as discount_rate
                FROM bill_items
                WHERE account_id = {placeholder} {time_filter}
                GROUP BY billing_cycle
                ORDER BY billing_cycle
            """, tuple(params))
            
            monthly_data = []
            for row in rows:
                # 处理字典格式的结果（MySQL）或元组格式（SQLite）
                if isinstance(row, dict):
                    monthly_data.append({
                        'month': row['billing_cycle'],
                        'official_price': float(row['official_price'] or 0),
                        'actual_amount': float(row['actual_amount'] or 0),
                        'discount_amount': float(row['discount_amount'] or 0),
                        'discount_rate': float(row['discount_rate'] or 0)
                    })
                else:
                    monthly_data.append({
                        'month': row[0],
                        'official_price': float(row[1] or 0),
                        'actual_amount': float(row[2] or 0),
                        'discount_amount': float(row[3] or 0),
                        'discount_rate': float(row[4] or 0)
                    })
            
            # 检测异常
            anomalies = []
            for i in range(1, len(monthly_data)):
                prev = monthly_data[i-1]
                curr = monthly_data[i]
                
                # 环比变化
                if prev['discount_rate'] > 0:
                    rate_change = (curr['discount_rate'] - prev['discount_rate']) / prev['discount_rate']
                    
                    if abs(rate_change) >= threshold:
                        anomaly_type = '折扣率突增' if rate_change > 0 else '折扣率突降'
                        severity = '严重' if abs(rate_change) >= 0.20 else '警告'
                        
                        anomalies.append({
                            'month': curr['month'],
                            'prev_month': prev['month'],
                            'current_rate': curr['discount_rate'],
                            'prev_rate': prev['discount_rate'],
                            'change_pct': rate_change * 100,
                            'anomaly_type': anomaly_type,
                            'severity': severity,
                            'description': f"{curr['month']}折扣率为{curr['discount_rate']*100:.1f}%，"
                                         f"较上月{prev['discount_rate']*100:.1f}%变化{rate_change*100:+.1f}%"
                        })
            
            return {
                'success': True,
                'anomalies': anomalies,
                'total_anomalies': len(anomalies),
                'threshold': threshold
            }
        
        except Exception as e:
            logger.error(f"异常检测失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    # ==================== Phase 2: 交叉维度分析 ====================
    
    def get_product_region_matrix(
        self,
        account_id: str,
        top_products: int = 10,
        top_regions: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        产品 × 区域交叉分析矩阵
        
        Args:
            account_id: 账号ID
            top_products: TOP N产品
            top_regions: TOP N区域
            start_date: 开始日期 (YYYY-MM格式)
            end_date: 结束日期 (YYYY-MM格式)
            
        Returns:
            交叉分析矩阵
        """
        logger.info(f"开始产品×区域交叉分析，时间范围={start_date}~{end_date}")
        
        try:
            # 构建时间过滤条件
            placeholder = self._get_placeholder()
            time_filter = ""
            params = [account_id]
            if start_date:
                time_filter += f" AND billing_cycle >= {placeholder}"
                params.append(start_date)
            if end_date:
                time_filter += f" AND billing_cycle <= {placeholder}"
                params.append(end_date)
            
            params.append(top_products)
            
            # 获取TOP产品和区域
            rows1 = self._query_db(f"""
                SELECT product_name, SUM(pretax_amount) as total
                FROM bill_items
                WHERE account_id = {placeholder} {time_filter}
                GROUP BY product_name
                ORDER BY total DESC
                LIMIT {placeholder}
            """, tuple(params))
            products = [row['product_name'] if isinstance(row, dict) else row[0] for row in rows1]
            
            # 重建参数
            params2 = [account_id]
            if start_date:
                params2.append(start_date)
            if end_date:
                params2.append(end_date)
            params2.append(top_regions)
            
            rows2 = self._query_db(f"""
                SELECT region, SUM(pretax_amount) as total
                FROM bill_items
                WHERE account_id = {placeholder} AND region != '' {time_filter}
                GROUP BY region
                ORDER BY total DESC
                LIMIT {placeholder}
            """, tuple(params2))
            regions = [row['region'] if isinstance(row, dict) else row[0] for row in rows2]
            
            # 重建时间过滤（不需要附加限制）
            time_filter3 = ""
            if start_date:
                time_filter3 += f" AND billing_cycle >= {placeholder}"
            if end_date:
                time_filter3 += f" AND billing_cycle <= {placeholder}"
            
            # 获取交叉数据
            matrix = {}
            for product in products:
                matrix[product] = {}
                for region in regions:
                    params3 = [account_id]
                    if start_date:
                        params3.append(start_date)
                    if end_date:
                        params3.append(end_date)
                    params3.extend([product, region])
                    
                    rows3 = self._query_db(f"""
                        SELECT 
                            CASE 
                                WHEN SUM(pretax_amount + invoice_discount) > 0 
                                THEN (SUM(invoice_discount) / SUM(pretax_amount + invoice_discount))
                                ELSE 0 
                            END as discount_rate,
                            SUM(pretax_amount) as total_paid
                        FROM bill_items
                        WHERE account_id = {placeholder}
                            {time_filter3}
                            AND product_name = {placeholder}
                            AND region = {placeholder}
                        GROUP BY product_name, region
                    """, tuple(params3))
                    
                    if rows3:
                        row = rows3[0]
                        if isinstance(row, dict):
                            matrix[product][region] = {
                                'discount_rate': float(row['discount_rate'] or 0),
                                'total_paid': float(row['total_paid'] or 0)
                            }
                        else:
                            matrix[product][region] = {
                                'discount_rate': float(row[0] or 0),
                                'total_paid': float(row[1] or 0)
                            }
                    else:
                        matrix[product][region] = {
                            'discount_rate': 0,
                            'total_paid': 0
                        }
            
            return {
                'success': True,
                'products': products,
                'regions': [{'code': r, 'name': self._get_region_name(r)} for r in regions],
                'matrix': matrix
            }
        
        except Exception as e:
            logger.error(f"产品×区域矩阵分析失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def get_moving_average(
        self,
        account_id: str,
        window_sizes: List[int] = [3, 6, 12],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        移动平均分析（平滑趋势）
        
        Args:
            account_id: 账号ID
            window_sizes: 窗口大小列表
            start_date: 开始日期 (YYYY-MM格式)
            end_date: 结束日期 (YYYY-MM格式)
            
        Returns:
            移动平均数据
        """
        logger.info(f"开始移动平均分析，窗口={window_sizes}, 时间范围={start_date}~{end_date}")
        
        try:
            # 构建时间过滤条件
            placeholder = self._get_placeholder()
            time_filter = ""
            params = [account_id]
            if start_date:
                time_filter += f" AND billing_cycle >= {placeholder}"
                params.append(start_date)
            if end_date:
                time_filter += f" AND billing_cycle <= {placeholder}"
                params.append(end_date)
            
            # 获取月度折扣率
            rows = self._query_db(f"""
                SELECT 
                    billing_cycle,
                    CASE 
                        WHEN SUM(pretax_amount + invoice_discount) > 0 
                        THEN (SUM(invoice_discount) / SUM(pretax_amount + invoice_discount))
                        ELSE 0 
                    END as discount_rate
                FROM bill_items
                WHERE account_id = {placeholder} {time_filter}
                GROUP BY billing_cycle
                ORDER BY billing_cycle
            """, tuple(params))
            
            monthly_rates = [
                (row['billing_cycle'] if isinstance(row, dict) else row[0], 
                 float(row['discount_rate'] or 0) if isinstance(row, dict) else float(row[1] or 0))
                for row in rows
            ]
            
            # 计算移动平均
            moving_averages = {}
            for window in window_sizes:
                ma_data = []
                for i in range(len(monthly_rates)):
                    if i < window - 1:
                        ma_data.append({
                            'month': monthly_rates[i][0],
                            'ma': None
                        })
                    else:
                        window_data = monthly_rates[i-window+1:i+1]
                        ma_value = sum(r[1] for r in window_data) / window
                        ma_data.append({
                            'month': monthly_rates[i][0],
                            'ma': ma_value,
                            'original': monthly_rates[i][1]
                        })
                
                moving_averages[f'ma_{window}'] = ma_data
            
            return {
                'success': True,
                'moving_averages': moving_averages,
                'original_data': [{'month': m, 'rate': r} for m, r in monthly_rates]
            }
        
        except Exception as e:
            logger.error(f"移动平均分析失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def get_cumulative_discount(
        self,
        account_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        累计折扣金额分析
        
        Args:
            account_id: 账号ID
            start_date: 开始日期 (YYYY-MM格式)
            end_date: 结束日期 (YYYY-MM格式)
            
        Returns:
            累计折扣数据
        """
        logger.info(f"开始累计折扣分析，时间范围={start_date}~{end_date}")
        
        try:
            # 构建时间过滤条件
            placeholder = self._get_placeholder()
            time_filter = ""
            params = [account_id]
            if start_date:
                time_filter += f" AND billing_cycle >= {placeholder}"
                params.append(start_date)
            if end_date:
                time_filter += f" AND billing_cycle <= {placeholder}"
                params.append(end_date)
            
            rows = self._query_db(f"""
                SELECT 
                    billing_cycle,
                    SUM(invoice_discount) as discount_amount
                FROM bill_items
                WHERE account_id = {placeholder} {time_filter}
                GROUP BY billing_cycle
                ORDER BY billing_cycle
            """, tuple(params))
            
            cumulative_data = []
            cumulative_total = 0
            
            for row in rows:
                # 处理字典格式的结果（MySQL）或元组格式（SQLite）
                if isinstance(row, dict):
                    monthly_discount = float(row['discount_amount'] or 0)
                else:
                    monthly_discount = float(row[1] or 0)
                
                cumulative_total += monthly_discount
                month = row['billing_cycle'] if isinstance(row, dict) else row[0]
                cumulative_data.append({
                    'month': month,
                    'monthly_discount': monthly_discount,
                    'cumulative_discount': cumulative_total
                })
            
            return {
                'success': True,
                'cumulative_data': cumulative_data,
                'total_discount': cumulative_total
            }
        
        except Exception as e:
            logger.error(f"累计折扣分析失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def get_instance_lifecycle_analysis(
        self,
        account_id: str,
        top_n: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        实例生命周期分析
        
        分析每个实例的生命周期折扣变化
        
        Args:
            account_id: 账号ID
            top_n: TOP N实例
            start_date: 开始日期 (YYYY-MM格式)
            end_date: 结束日期 (YYYY-MM格式)
            
        Returns:
            实例生命周期数据
        """
        logger.info(f"开始实例生命周期分析，时间范围={start_date}~{end_date}")
        
        try:
            # 构建时间过滤条件
            placeholder = self._get_placeholder()
            time_filter = ""
            params = [account_id]
            if start_date:
                time_filter += f" AND billing_cycle >= {placeholder}"
                params.append(start_date)
            if end_date:
                time_filter += f" AND billing_cycle <= {placeholder}"
                params.append(end_date)
            
            params.append(top_n)
            
            # 获取TOP N实例（按总消费）
            rows = self._query_db(f"""
                SELECT 
                    instance_id,
                    product_name,
                    region,
                    subscription_type,
                    MIN(billing_cycle) as first_month,
                    MAX(billing_cycle) as last_month,
                    COUNT(DISTINCT billing_cycle) as lifecycle_months,
                    SUM(pretax_amount) as total_cost,
                    SUM(invoice_discount) as total_discount,
                    AVG(CASE 
                        WHEN (pretax_amount + invoice_discount) > 0 
                        THEN (invoice_discount / (pretax_amount + invoice_discount))
                        ELSE 0 
                    END) as avg_discount_rate
                FROM bill_items
                WHERE account_id = {placeholder}
                    AND instance_id != ''
                    {time_filter}
                GROUP BY instance_id, product_name, region, subscription_type
                ORDER BY total_cost DESC
                LIMIT {placeholder}
            """, tuple(params))
            
            instances = []
            for row in rows:
                # 处理字典格式的结果（MySQL）或元组格式（SQLite）
                if isinstance(row, dict):
                    instance_id = row['instance_id']
                else:
                    instance_id = row[0]
                
                # 重建时间过滤
                time_filter2 = ""
                params2 = [account_id, instance_id]
                if start_date:
                    time_filter2 += f" AND billing_cycle >= {placeholder}"
                    params2.append(start_date)
                if end_date:
                    time_filter2 += f" AND billing_cycle <= {placeholder}"
                    params2.append(end_date)
                
                # 获取该实例的月度折扣趋势
                trend_rows = self._query_db(f"""
                    SELECT 
                        billing_cycle,
                        SUM(pretax_amount) as monthly_cost,
                        CASE 
                            WHEN SUM(pretax_amount + invoice_discount) > 0 
                            THEN (SUM(invoice_discount) / SUM(pretax_amount + invoice_discount))
                            ELSE 0 
                        END as discount_rate
                    FROM bill_items
                    WHERE account_id = {placeholder} AND instance_id = {placeholder} {time_filter2}
                    GROUP BY billing_cycle
                    ORDER BY billing_cycle
                """, tuple(params2))
                
                monthly_trends = []
                for trend_row in trend_rows:
                    # 处理字典格式的结果（MySQL）或元组格式（SQLite）
                    if isinstance(trend_row, dict):
                        monthly_trends.append({
                            'month': trend_row['billing_cycle'],
                            'monthly_cost': float(trend_row['monthly_cost'] or 0),
                            'discount_rate': float(trend_row['discount_rate'] or 0)
                        })
                    else:
                        monthly_trends.append({
                            'month': trend_row[0],
                            'monthly_cost': float(trend_row[1] or 0),
                            'discount_rate': float(trend_row[2] or 0)
                        })
                
                # 处理字典格式的结果（MySQL）或元组格式（SQLite）
                if isinstance(row, dict):
                    instances.append({
                        'instance_id': instance_id,
                        'product_name': row['product_name'],
                        'region': row['region'],
                        'region_name': self._get_region_name(row['region']),
                        'subscription_type': row['subscription_type'],
                        'first_month': row['first_month'],
                        'last_month': row['last_month'],
                        'lifecycle_months': int(row['lifecycle_months'] or 0),
                        'total_cost': float(row['total_cost'] or 0),
                        'total_discount': float(row['total_discount'] or 0),
                        'avg_discount_rate': float(row['avg_discount_rate'] or 0),
                        'monthly_trends': monthly_trends
                    })
                else:
                    instances.append({
                        'instance_id': instance_id,
                        'product_name': row[1],
                        'region': row[2],
                        'region_name': self._get_region_name(row[2]),
                        'subscription_type': row[3],
                        'first_month': row[4],
                        'last_month': row[5],
                        'lifecycle_months': int(row[6] or 0),
                        'total_cost': float(row[7] or 0),
                        'total_discount': float(row[8] or 0),
                        'avg_discount_rate': float(row[9] or 0),
                        'monthly_trends': monthly_trends
                    })
            
            return {
                'success': True,
                'instances': instances,
                'total_instances': len(instances)
            }
        
        except Exception as e:
            logger.error(f"实例生命周期分析失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    # ==================== Phase 3: 智能分析功能 ====================
    
    def generate_insights(
        self,
        account_id: str
    ) -> Dict:
        """
        智能洞察生成（基于规则的分析）
        
        Args:
            account_id: 账号ID
            
        Returns:
            智能洞察数据
        """
        logger.info(f"开始生成智能洞察")
        
        try:
            insights = []
            
            # 获取各类分析数据
            quarterly = self.get_quarterly_comparison(account_id, quarters=4)
            products = self.get_product_discount_trends(account_id, months=19, top_n=20)
            regions = self.get_region_discount_ranking(account_id)
            subscription = self.get_subscription_type_comparison(account_id)
            suggestions = self.get_optimization_suggestions(account_id)
            anomalies = self.detect_anomalies(account_id)
            
            # 洞察1: 折扣趋势
            if quarterly['success'] and len(quarterly['quarters']) >= 2:
                latest = quarterly['quarters'][-1]
                prev = quarterly['quarters'][-2]
                change = latest['avg_discount_rate'] - prev['avg_discount_rate']
                insights.append({
                    'category': '趋势分析',
                    'level': 'info' if change >= 0 else 'warning',
                    'title': '季度折扣率' + ('上升' if change >= 0 else '下降'),
                    'description': f"最新季度{latest['period']}折扣率为{latest['avg_discount_rate']*100:.1f}%，较上季度{change*100:+.1f}%",
                    'recommendation': '持续优化' if change >= 0 else '需要与商务团队沟通合同续约'
                })
            
            # 洞察2: TOP产品分析
            if products['success'] and products['products']:
                top_product = products['products'][0]
                insights.append({
                    'category': '产品分析',
                    'level': 'success',
                    'title': f"最大消费产品: {top_product['product_name']}",
                    'description': f"消费{top_product['total_consumption']:,.0f}元，平均折扣率{top_product['avg_discount_rate']*100:.1f}%",
                    'recommendation': '保持当前折扣策略'
                })
                
                # 找出折扣率最低的产品
                lowest_discount_product = min(products['products'], key=lambda x: x['avg_discount_rate'])
                if lowest_discount_product['avg_discount_rate'] < 0.40:
                    insights.append({
                        'category': '产品分析',
                        'level': 'warning',
                        'title': f"低折扣产品: {lowest_discount_product['product_name']}",
                        'description': f"折扣率仅{lowest_discount_product['avg_discount_rate']*100:.1f}%",
                        'recommendation': '建议与商务沟通提升该产品折扣率'
                    })
            
            # 洞察3: 优化机会
            if suggestions['success'] and suggestions['total_suggestions'] > 0:
                savings = suggestions['total_potential_savings']
                insights.append({
                    'category': '优化机会',
                    'level': 'success',
                    'title': f"发现{suggestions['total_suggestions']}个优化机会",
                    'description': f"转为包年包月可年节省{savings:,.0f}元",
                    'recommendation': '优先转换运行时间长、成本高的实例'
                })
            
            # 洞察4: 异常检测
            if anomalies['success'] and anomalies['total_anomalies'] > 0:
                insights.append({
                    'category': '异常检测',
                    'level': 'warning',
                    'title': f"检测到{anomalies['total_anomalies']}个异常月份",
                    'description': '折扣率波动超过阈值',
                    'recommendation': '查看异常月份的大额订单或合同变更'
                })
            
            # 洞察5: 计费方式对比
            if subscription['success']:
                rate_diff = subscription['rate_difference']
                if rate_diff > 0.10:
                    insights.append({
                        'category': '计费优化',
                        'level': 'info',
                        'title': f"包年包月折扣率优势{rate_diff*100:.1f}%",
                        'description': '包年包月折扣率显著高于按量付费',
                        'recommendation': '评估长期运行资源，转为包年包月'
                    })
            
            return {
                'success': True,
                'insights': insights,
                'total_insights': len(insights),
                'generated_at': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"智能洞察生成失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def export_to_csv(
        self,
        account_id: str,
        export_type: str = 'all'
    ) -> Dict:
        """
        导出数据为CSV
        
        Args:
            account_id: 账号ID
            export_type: 导出类型 (all, products, regions, instances)
            
        Returns:
            CSV数据字符串
        """
        import io
        import csv
        
        logger.info(f"开始导出CSV，类型={export_type}")
        
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            
            if export_type in ['all', 'products']:
                # 导出产品数据
                products = self.get_product_discount_trends(account_id, months=19, top_n=50)
                if products['success']:
                    writer.writerow(['产品折扣分析'])
                    writer.writerow(['产品名称', '总消费', '总折扣', '平均折扣率', '波动率', '趋势变化'])
                    for p in products['products']:
                        writer.writerow([
                            p['product_name'],
                            f"{p['total_consumption']:.2f}",
                            f"{p['total_discount']:.2f}",
                            f"{p['avg_discount_rate']*100:.2f}%",
                            f"{p['volatility']*100:.2f}%",
                            f"{p['trend_change_pct']:+.2f}%"
                        ])
                    writer.writerow([])
            
            if export_type in ['all', 'regions']:
                # 导出区域数据
                regions = self.get_region_discount_ranking(account_id)
                if regions['success']:
                    writer.writerow(['区域折扣分析'])
                    writer.writerow(['区域', '消费金额', '折扣金额', '折扣率', '实例数'])
                    for r in regions['regions']:
                        writer.writerow([
                            r['region_name'],
                            f"{r['total_paid']:.2f}",
                            f"{r['total_discount']:.2f}",
                            f"{r['avg_discount_rate']*100:.2f}%",
                            r['instance_count']
                        ])
                    writer.writerow([])
            
            if export_type in ['all', 'instances']:
                # 导出实例优化建议
                suggestions = self.get_optimization_suggestions(account_id)
                if suggestions['success']:
                    writer.writerow(['实例优化建议'])
                    writer.writerow(['实例ID', '产品', '区域', '运行月数', '总成本', '当前折扣率', '预计折扣率', '年节省'])
                    for s in suggestions['suggestions'][:100]:
                        writer.writerow([
                            s['instance_id'],
                            s['product_name'],
                            s['region_name'],
                            s['running_months'],
                            f"{s['total_cost']:.2f}",
                            f"{s['current_discount_rate']*100:.2f}%",
                            f"{s['estimated_subscription_rate']*100:.2f}%",
                            f"{s['annual_potential_savings']:.2f}"
                        ])
            
            csv_content = output.getvalue()
            output.close()
            
            return {
                'success': True,
                'csv_content': csv_content,
                'export_type': export_type
            }
        
        except Exception as e:
            logger.error(f"CSV导出失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # ==================== 辅助方法 ====================
    
    def _get_region_name(self, region_code: str) -> str:
        """获取区域中文名称"""
        region_names = {
            'cn-shanghai': '华东2(上海)',
            'cn-beijing': '华北2(北京)',
            'cn-shenzhen': '华南1(深圳)',
            'cn-hangzhou': '华东1(杭州)',
            'cn-qingdao': '华北1(青岛)',
            'cn-zhangjiakou': '华北3(张家口)',
            'cn-huhehaote': '华北5(呼和浩特)',
            'cn-chengdu': '西南1(成都)',
            'cn-hongkong': '香港',
            'ap-southeast-1': '新加坡',
            'ap-southeast-2': '悉尼',
            'ap-southeast-3': '吉隆坡',
            'ap-southeast-5': '雅加达',
            'ap-northeast-1': '东京',
            'us-west-1': '美国西部1(硅谷)',
            'us-east-1': '美国东部1(弗吉尼亚)',
            'eu-central-1': '欧洲中部1(法兰克福)'
        }
        return region_names.get(region_code, region_code)


def main():
    """测试用例"""
    import os
    
    db_path = os.path.expanduser("~/.cloudlens/bills.db")
    analyzer = AdvancedDiscountAnalyzer(db_path)
    
    account_id = "LTAI5tECY4-ydzn"
    
    print("\n=== 测试1: 季度对比 ===")
    result = analyzer.get_quarterly_comparison(account_id, quarters=8)
    if result['success']:
        for q in result['quarters']:
            print(f"{q['period']}: 折扣率{q['avg_discount_rate']*100:.1f}%, "
                  f"节省¥{q['total_discount']:,.0f}, "
                  f"环比{q.get('rate_change', 0):+.1f}%")
    
    print("\n=== 测试2: 产品折扣趋势 ===")
    result = analyzer.get_product_discount_trends(account_id, months=19, top_n=5)
    if result['success']:
        for p in result['products'][:3]:
            print(f"{p['product_name']}: 平均折扣率{p['avg_discount_rate']*100:.1f}%, "
                  f"波动率{p['volatility']*100:.1f}%, "
                  f"趋势{p['trend_change_pct']:+.1f}%")
    
    print("\n=== 测试3: 优化建议 ===")
    result = analyzer.get_optimization_suggestions(account_id)
    if result['success']:
        print(f"找到{result['total_suggestions']}个优化机会")
        print(f"总节省潜力: ¥{result['total_potential_savings']:,.0f}/年")
        for s in result['suggestions'][:3]:
            print(f"  - {s['instance_id']}: {s['suggestion']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()






