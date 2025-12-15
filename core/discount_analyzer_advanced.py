#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级折扣分析器 - Phase 1/2/3
支持多维度深度分析
"""

import logging
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class AdvancedDiscountAnalyzer:
    """高级折扣分析器"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化分析器
        
        Args:
            db_path: 数据库路径，默认使用~/.cloudlens/bills.db
        """
        from core.bill_storage import BillStorageManager
        self.storage = BillStorageManager(db_path)
        self.db_path = self.storage.db_path
    
    # ==================== Phase 1: 核心分析功能 ====================
    
    def get_quarterly_comparison(
        self,
        account_id: str,
        quarters: int = 8
    ) -> Dict:
        """
        季度对比分析
        
        Args:
            account_id: 账号ID
            quarters: 分析季度数
            
        Returns:
            季度对比数据
        """
        logger.info(f"开始季度对比分析，账号={account_id}, 季度数={quarters}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    SUBSTR(billing_cycle, 1, 4) as year,
                    CASE 
                        WHEN CAST(SUBSTR(billing_cycle, 6, 2) AS INT) <= 3 THEN 'Q1'
                        WHEN CAST(SUBSTR(billing_cycle, 6, 2) AS INT) <= 6 THEN 'Q2'
                        WHEN CAST(SUBSTR(billing_cycle, 6, 2) AS INT) <= 9 THEN 'Q3'
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
                WHERE account_id = ?
                GROUP BY year, quarter
                ORDER BY year DESC, 
                    CASE quarter 
                        WHEN 'Q1' THEN 1 
                        WHEN 'Q2' THEN 2 
                        WHEN 'Q3' THEN 3 
                        WHEN 'Q4' THEN 4 
                    END DESC
                LIMIT ?
            """, (account_id, quarters))
            
            quarterly_data = []
            for row in cursor.fetchall():
                quarterly_data.append({
                    'year': row[0],
                    'quarter': row[1],
                    'period': f"{row[0]}-{row[1]}",
                    'total_original': row[2],
                    'total_paid': row[3],
                    'total_discount': row[4],
                    'avg_discount_rate': row[5],
                    'month_count': row[6]
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
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def get_yearly_comparison(
        self,
        account_id: str
    ) -> Dict:
        """
        年度对比分析
        
        Args:
            account_id: 账号ID
            
        Returns:
            年度对比数据
        """
        logger.info(f"开始年度对比分析，账号={account_id}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 年度总览
            cursor.execute("""
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
                WHERE account_id = ?
                GROUP BY year
                ORDER BY year
            """, (account_id,))
            
            yearly_data = []
            for row in cursor.fetchall():
                yearly_data.append({
                    'year': row[0],
                    'month_count': row[1],
                    'total_original': row[2],
                    'total_paid': row[3],
                    'total_discount': row[4],
                    'avg_discount_rate': row[5]
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
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def get_product_discount_trends(
        self,
        account_id: str,
        months: int = 19,
        top_n: int = 20
    ) -> Dict:
        """
        产品折扣趋势分析（每个产品的月度折扣变化）
        
        Args:
            account_id: 账号ID
            months: 分析月数
            top_n: TOP N产品
            
        Returns:
            产品趋势数据
        """
        logger.info(f"开始产品折扣趋势分析，账号={account_id}, 月数={months}, TOP={top_n}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 先获取TOP N产品（按消费金额）
            cursor.execute("""
                SELECT 
                    product_name,
                    SUM(pretax_amount) as total_paid
                FROM bill_items
                WHERE account_id = ?
                    AND product_name != ''
                GROUP BY product_name
                ORDER BY total_paid DESC
                LIMIT ?
            """, (account_id, top_n))
            
            top_products = [row[0] for row in cursor.fetchall()]
            
            if not top_products:
                return {'success': False, 'error': f'没有产品数据 (account_id={account_id})'}
            
            # 获取这些产品的月度趋势
            placeholders = ','.join(['?' for _ in top_products])
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
                WHERE account_id = ? 
                    AND product_name IN ({placeholders})
                GROUP BY product_name, billing_cycle
                ORDER BY product_name, billing_cycle
            """
            
            cursor.execute(query, [account_id] + top_products)
            
            # 按产品分组
            product_trends = defaultdict(list)
            for row in cursor.fetchall():
                product_trends[row[0]].append({
                    'month': row[1],
                    'official_price': row[2],
                    'paid_amount': row[3],
                    'discount_amount': row[4],
                    'discount_rate': row[5],
                    'record_count': row[6],
                    'instance_count': row[7]
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
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def get_region_discount_ranking(
        self,
        account_id: str,
        months: int = 19
    ) -> Dict:
        """
        区域折扣排行分析
        
        Args:
            account_id: 账号ID
            months: 分析月数
            
        Returns:
            区域排行数据
        """
        logger.info(f"开始区域折扣排行分析，账号={account_id}, 月数={months}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
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
                WHERE account_id = ?
                    AND region != ''
                GROUP BY region
                ORDER BY total_paid DESC
            """, (account_id,))
            
            regions = []
            for row in cursor.fetchall():
                regions.append({
                    'region': row[0],
                    'region_name': self._get_region_name(row[0]),
                    'total_original': row[1],
                    'total_paid': row[2],
                    'total_discount': row[3],
                    'avg_discount_rate': row[4],
                    'instance_count': row[5],
                    'product_count': row[6],
                    'month_count': row[7],
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
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def get_subscription_type_comparison(
        self,
        account_id: str,
        months: int = 19
    ) -> Dict:
        """
        计费方式对比分析（包年包月 vs 按量付费）
        
        Args:
            account_id: 账号ID
            months: 分析月数
            
        Returns:
            计费方式对比数据
        """
        logger.info(f"开始计费方式对比分析，账号={account_id}, 月数={months}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 总体对比
            cursor.execute("""
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
                WHERE account_id = ?
                    AND subscription_type IN ('Subscription', 'PayAsYouGo')
                GROUP BY subscription_type
            """, (account_id,))
            
            subscription_types = {}
            for row in cursor.fetchall():
                sub_type = row[0]
                type_name = '包年包月' if sub_type == 'Subscription' else '按量付费'
                
                subscription_types[sub_type] = {
                    'type': sub_type,
                    'type_name': type_name,
                    'total_original': row[1],
                    'total_paid': row[2],
                    'total_discount': row[3],
                    'avg_discount_rate': row[4],
                    'instance_count': row[5],
                    'avg_instance_cost': row[6]
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
            cursor.execute("""
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
                WHERE account_id = ?
                    AND subscription_type IN ('Subscription', 'PayAsYouGo')
                GROUP BY billing_cycle, subscription_type
                ORDER BY billing_cycle, subscription_type
            """, (account_id,))
            
            monthly_trends = defaultdict(lambda: defaultdict(dict))
            for row in cursor.fetchall():
                month = row[0]
                sub_type = row[1]
                monthly_trends[month][sub_type] = {
                    'total_paid': row[2],
                    'discount_rate': row[3]
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
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def get_optimization_suggestions(
        self,
        account_id: str,
        min_running_months: int = 6
    ) -> Dict:
        """
        优化建议：识别长期运行的按量付费实例
        
        Args:
            account_id: 账号ID
            min_running_months: 最少运行月数
            
        Returns:
            优化建议列表
        """
        logger.info(f"开始生成优化建议，账号={account_id}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
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
                WHERE account_id = ?
                    AND subscription_type = 'PayAsYouGo'
                    AND instance_id != ''
                GROUP BY instance_id, product_name, region
                HAVING running_months >= ?
                ORDER BY total_cost DESC
                LIMIT 50
            """, (account_id, min_running_months))
            
            suggestions = []
            for row in cursor.fetchall():
                current_rate = row[8]
                # 假设转包年包月可以提升10-15%折扣率
                estimated_subscription_rate = min(current_rate + 0.13, 0.70)
                potential_savings = row[6] * (estimated_subscription_rate - current_rate)
                
                suggestions.append({
                    'instance_id': row[0],
                    'product_name': row[1],
                    'region': row[2],
                    'region_name': self._get_region_name(row[2]),
                    'first_month': row[3],
                    'last_month': row[4],
                    'running_months': row[5],
                    'total_cost': row[6],
                    'avg_monthly_cost': row[7],
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
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def detect_anomalies(
        self,
        account_id: str,
        months: int = 19,
        threshold: float = 0.10
    ) -> Dict:
        """
        异常检测：识别折扣率波动异常的月份
        
        Args:
            account_id: 账号ID
            months: 分析月数
            threshold: 异常阈值（默认10%）
            
        Returns:
            异常检测结果
        """
        logger.info(f"开始异常检测，账号={account_id}, 阈值={threshold*100}%")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取月度折扣率
            cursor.execute("""
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
                WHERE account_id = ?
                GROUP BY billing_cycle
                ORDER BY billing_cycle
            """, (account_id,))
            
            monthly_data = []
            for row in cursor.fetchall():
                monthly_data.append({
                    'month': row[0],
                    'official_price': row[1],
                    'actual_amount': row[2],
                    'discount_amount': row[3],
                    'discount_rate': row[4]
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
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    # ==================== Phase 2: 交叉维度分析 ====================
    
    def get_product_region_matrix(
        self,
        account_id: str,
        top_products: int = 10,
        top_regions: int = 10
    ) -> Dict:
        """
        产品 × 区域交叉分析矩阵
        
        Args:
            account_id: 账号ID
            top_products: TOP N产品
            top_regions: TOP N区域
            
        Returns:
            交叉分析矩阵
        """
        logger.info(f"开始产品×区域交叉分析")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取TOP产品和区域
            cursor.execute("""
                SELECT product_name, SUM(pretax_amount) as total
                FROM bill_items
                WHERE account_id = ?
                GROUP BY product_name
                ORDER BY total DESC
                LIMIT ?
            """, (account_id, top_products))
            products = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("""
                SELECT region, SUM(pretax_amount) as total
                FROM bill_items
                WHERE account_id = ? AND region != ''
                GROUP BY region
                ORDER BY total DESC
                LIMIT ?
            """, (account_id, top_regions))
            regions = [row[0] for row in cursor.fetchall()]
            
            # 获取交叉数据
            matrix = {}
            for product in products:
                matrix[product] = {}
                for region in regions:
                    cursor.execute("""
                        SELECT 
                            CASE 
                                WHEN SUM(pretax_amount + invoice_discount) > 0 
                                THEN (SUM(invoice_discount) / SUM(pretax_amount + invoice_discount))
                                ELSE 0 
                            END as discount_rate,
                            SUM(pretax_amount) as total_paid
                        FROM bill_items
                        WHERE account_id = ?
                            AND product_name = ?
                            AND region = ?
                    """, (account_id, product, region))
                    
                    row = cursor.fetchone()
                    matrix[product][region] = {
                        'discount_rate': row[0] if row else 0,
                        'total_paid': row[1] if row else 0
                    }
            
            return {
                'success': True,
                'products': products,
                'regions': [{'code': r, 'name': self._get_region_name(r)} for r in regions],
                'matrix': matrix
            }
        
        except Exception as e:
            logger.error(f"产品×区域矩阵分析失败: {str(e)}")
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def get_moving_average(
        self,
        account_id: str,
        window_sizes: List[int] = [3, 6, 12]
    ) -> Dict:
        """
        移动平均分析（平滑趋势）
        
        Args:
            account_id: 账号ID
            window_sizes: 窗口大小列表
            
        Returns:
            移动平均数据
        """
        logger.info(f"开始移动平均分析，窗口={window_sizes}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取月度折扣率
            cursor.execute("""
                SELECT 
                    billing_cycle,
                    CASE 
                        WHEN SUM(pretax_amount + invoice_discount) > 0 
                        THEN (SUM(invoice_discount) / SUM(pretax_amount + invoice_discount))
                        ELSE 0 
                    END as discount_rate
                FROM bill_items
                WHERE account_id = ?
                GROUP BY billing_cycle
                ORDER BY billing_cycle
            """, (account_id,))
            
            monthly_rates = [(row[0], row[1]) for row in cursor.fetchall()]
            
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
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def get_cumulative_discount(
        self,
        account_id: str
    ) -> Dict:
        """
        累计折扣金额分析
        
        Args:
            account_id: 账号ID
            
        Returns:
            累计折扣数据
        """
        logger.info(f"开始累计折扣分析")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    billing_cycle,
                    SUM(invoice_discount) as discount_amount
                FROM bill_items
                WHERE account_id = ?
                GROUP BY billing_cycle
                ORDER BY billing_cycle
            """, (account_id,))
            
            cumulative_data = []
            cumulative_total = 0
            
            for row in cursor.fetchall():
                cumulative_total += row[1]
                cumulative_data.append({
                    'month': row[0],
                    'monthly_discount': row[1],
                    'cumulative_discount': cumulative_total
                })
            
            return {
                'success': True,
                'cumulative_data': cumulative_data,
                'total_discount': cumulative_total
            }
        
        except Exception as e:
            logger.error(f"累计折扣分析失败: {str(e)}")
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
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
