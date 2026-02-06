#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账单数据存储管理器（MySQL版本）
使用数据库抽象层，支持SQLite和MySQL
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json

from cloudlens.core.database import DatabaseFactory, DatabaseAdapter
from cloudlens.core.performance import monitor_db_query

logger = logging.getLogger(__name__)


class BillStorageManager:
    """账单数据存储管理器（只支持MySQL，SQLite已废弃）"""
    
    # 数据库schema版本
    SCHEMA_VERSION = 1
    
    def __init__(self, db_path: Optional[str] = None, db_type: Optional[str] = None):
        """
        初始化存储管理器（只支持MySQL，SQLite已废弃）
        
        Args:
            db_path: 已废弃，不再使用
            db_type: 已废弃，只使用MySQL
        """
        # 只使用MySQL（SQLite已废弃）
        self.db_type = "mysql"
        self._db = None  # 内部存储适配器
        self.db_path = None
        
        self._init_database()
    
    @property
    def db(self) -> DatabaseAdapter:
        """获取数据库适配器（自动初始化）"""
        return self._get_db()

    def _get_db(self) -> DatabaseAdapter:
        """延迟获取数据库适配器"""
        if self._db is None:
            self._db = DatabaseFactory.create_adapter("mysql")
        return self._db
    
    def _get_placeholder(self) -> str:
        """获取SQL占位符（只支持MySQL）"""
        return "%s"  # MySQL使用%s
    
    def _quote_column(self, col: str) -> str:
        """引用列名（处理MySQL保留关键字）"""
        reserved = ['usage', 'key', 'order', 'group', 'select', 'table', 'index']
        if col.lower() in reserved:
            return f"`{col}`"
        return col
    
    def _init_database(self):
        """初始化数据库表结构（只支持MySQL）"""
        # MySQL表结构已在init_mysql_schema.sql中创建
        # 这里只检查表是否存在（延迟检查，避免导入时连接）
        pass  # 延迟到首次使用时检查
    
    def query(self, sql: str, params: tuple = None) -> List[Dict]:
        """
        执行SQL查询（公共接口）
        
        Args:
            sql: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        return self._get_db().query(sql, params)
    
    def query_one(self, sql: str, params: tuple = None) -> Optional[Dict]:
        """
        执行SQL查询并返回单条结果（公共接口）
        
        Args:
            sql: SQL查询语句
            params: 查询参数
            
        Returns:
            单条查询结果或None
        """
        return self._get_db().query_one(sql, params)
    
    def insert_bill_items(
        self, 
        account_id: str,
        billing_cycle: str,
        items: List[Dict]
    ) -> Tuple[int, int]:
        """
        批量插入账单明细（优化版本：使用executemany提升性能）
        
        Args:
            account_id: 账号ID
            billing_cycle: 账期（YYYY-MM）
            items: 账单明细列表
            
        Returns:
            (插入数量, 跳过数量)
        """
        if not items:
            return 0, 0
        
        placeholder = self._get_placeholder()
        inserted = 0
        skipped = 0
        
        try:
            self._get_db().begin_transaction()
            
            # 准备批量数据
            batch_size = 1000  # 每批插入1000条
            all_values = []
            
            for item in items:
                try:
                    values = (
                        account_id,
                        billing_cycle,
                        item.get('BillingDate', ''),
                        item.get('ProductName', ''),
                        item.get('ProductCode', ''),
                        item.get('ProductType', ''),
                        item.get('SubscriptionType', ''),
                        item.get('PricingUnit', ''),
                        float(item.get('Usage', 0) or 0),
                        float(item.get('ListPrice', 0) or 0),
                        item.get('ListPriceUnit', ''),
                        float(item.get('InvoiceDiscount', 0) or 0),
                        float(item.get('PretaxAmount', 0) or 0),
                        float(item.get('DeductedByCoupons', 0) or 0),
                        float(item.get('DeductedByCashCoupons', 0) or 0),
                        float(item.get('DeductedByPrepaidCard', 0) or 0),
                        float(item.get('PaymentAmount', 0) or 0),
                        float(item.get('OutstandingAmount', 0) or 0),
                        item.get('Currency', ''),
                        item.get('NickName', ''),
                        item.get('ResourceGroup', ''),
                        json.dumps(item.get('Tag', ''), ensure_ascii=False) if item.get('Tag') else None,
                        item.get('InstanceID', ''),
                        item.get('InstanceConfig', ''),
                        item.get('InternetIP', ''),
                        item.get('IntranetIP', ''),
                        item.get('Region', ''),
                        item.get('Zone', ''),
                        item.get('Item', ''),
                        item.get('CostUnit', ''),
                        item.get('BillingItem', ''),
                        item.get('PipCode', ''),
                        item.get('ServicePeriod', ''),
                        item.get('ServicePeriodUnit', ''),
                        json.dumps(item, ensure_ascii=False)
                    )
                    all_values.append(values)
                except Exception as e:
                    logger.warning(f"准备账单明细数据失败: {str(e)}")
                    skipped += 1
            
            # 批量插入
            if all_values:
                # 只使用MySQL（SQLite已废弃）
                # MySQL使用ON DUPLICATE KEY UPDATE
                sql = f"""
                    INSERT INTO bill_items (
                        account_id, billing_cycle, billing_date,
                        product_name, product_code, product_type, subscription_type,
                        pricing_unit, `usage`, list_price, list_price_unit,
                        invoice_discount, pretax_amount,
                        deducted_by_coupons, deducted_by_cash_coupons,
                        deducted_by_prepaid_card, payment_amount,
                        outstanding_amount, currency,
                        nick_name, resource_group, tag,
                        instance_id, instance_config, internet_ip, intranet_ip,
                        region, zone, item, cost_unit, billing_item,
                        pip_code, service_period, service_period_unit,
                        raw_data
                    ) VALUES ({', '.join([placeholder] * 35)})
                    ON DUPLICATE KEY UPDATE
                        updated_at = CURRENT_TIMESTAMP
                """
                
                # 分批执行（避免单次插入过多数据）
                for i in range(0, len(all_values), batch_size):
                    batch = all_values[i:i + batch_size]
                    try:
                        # 使用executemany批量插入（性能优化）
                        rows_affected = self._get_db().executemany(sql, batch)
                        inserted += rows_affected if rows_affected > 0 else len(batch)
                    except Exception as e:
                        logger.warning(f"批量插入失败（批次 {i//batch_size + 1}）: {str(e)}")
                        skipped += len(batch)
            
            self._get_db().commit()
            logger.info(f"账期 {billing_cycle} 批量插入 {inserted} 条，跳过 {skipped} 条")
            
            return inserted, skipped
        
        except Exception as e:
            self._get_db().rollback()
            logger.error(f"批量插入失败: {str(e)}")
            raise
    
    @monitor_db_query
    def query_bill_items(
        self,
        account_id: Optional[str] = None,
        billing_cycle: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        product_code: Optional[str] = None,
        instance_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        查询账单明细

        Args:
            account_id: 账号ID
            billing_cycle: 账期
            start_date: 开始日期
            end_date: 结束日期
            product_code: 产品代码
            instance_id: 实例ID
            limit: 限制返回数量

        Returns:
            账单明细列表
        """
        placeholder = self._get_placeholder()
        conditions = []
        params = []

        if account_id:
            conditions.append(f"account_id = {placeholder}")
            params.append(account_id)
        if billing_cycle:
            conditions.append(f"billing_cycle = {placeholder}")
            params.append(billing_cycle)
        if start_date:
            conditions.append(f"billing_date >= {placeholder}")
            params.append(start_date)
        if end_date:
            conditions.append(f"billing_date <= {placeholder}")
            params.append(end_date)
        if product_code:
            conditions.append(f"product_code = {placeholder}")
            params.append(product_code)
        if instance_id:
            conditions.append(f"instance_id = {placeholder}")
            params.append(instance_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 构建SQL（修复SQL注入风险）
        sql = f"SELECT * FROM bill_items WHERE {where_clause} ORDER BY billing_date DESC"
        if limit is not None:
            try:
                limit_int = int(limit)
                if limit_int > 0:
                    sql += f" LIMIT {limit_int}"
            except (ValueError, TypeError):
                logger.warning(f"Invalid limit value: {limit}, ignoring")

        return self._get_db().query(sql, tuple(params) if params else None)

    @monitor_db_query
    def get_discount_analysis_data(
        self,
        account_id: str,
        months: int = 6
    ) -> Dict:
        """
        获取折扣分析所需的聚合数据
        
        Args:
            account_id: 账号ID
            months: 分析月数
            
        Returns:
            包含月度趋势、产品分布、实例分布的字典
        """
        placeholder = self._get_placeholder()
        
        # 确定时间范围
        cycles_res = self.db.query(f"""
            SELECT DISTINCT billing_cycle 
            FROM bill_items 
            WHERE account_id = {placeholder}
            ORDER BY billing_cycle DESC
            LIMIT {placeholder}
        """, (account_id, months))
        
        if not cycles_res:
            return {
                'monthly': [],
                'products': [],
                'instances': [],
                'start_cycle': '',
                'end_cycle': ''
            }
        
        cycles = [r['billing_cycle'] for r in cycles_res]
        start_cycle = cycles[-1]
        end_cycle = cycles[0]
        
        # 1. 月度趋势聚合
        monthly_sql = f"""
            SELECT 
                billing_cycle as month,
                SUM(pretax_amount + invoice_discount) as official_price,
                SUM(invoice_discount) as discount_amount,
                SUM(pretax_amount) as actual_amount,
                CASE 
                    WHEN SUM(pretax_amount + invoice_discount) > 0 
                    THEN SUM(invoice_discount) / SUM(pretax_amount + invoice_discount)
                    ELSE 0 
                END as discount_rate
            FROM bill_items
            WHERE account_id = {placeholder}
              AND billing_cycle BETWEEN {placeholder} AND {placeholder}
            GROUP BY billing_cycle
            ORDER BY billing_cycle ASC
        """
        monthly_res = self.db.query(monthly_sql, (account_id, start_cycle, end_cycle))
        
        # 2. 产品分布聚合
        products_sql = f"""
            SELECT 
                product_name as product,
                SUM(invoice_discount) as discount_amount,
                CASE 
                    WHEN SUM(pretax_amount + invoice_discount) > 0 
                    THEN SUM(invoice_discount) / SUM(pretax_amount + invoice_discount)
                    ELSE 0 
                END as discount_rate
            FROM bill_items
            WHERE account_id = {placeholder}
              AND billing_cycle BETWEEN {placeholder} AND {placeholder}
            GROUP BY product_name
            ORDER BY discount_amount DESC
            LIMIT 20
        """
        products_res = self.db.query(products_sql, (account_id, start_cycle, end_cycle))
        
        # 3. 实例分布聚合
        instances_sql = f"""
            SELECT 
                instance_id,
                SUM(invoice_discount) as discount_amount,
                CASE 
                    WHEN SUM(pretax_amount + invoice_discount) > 0 
                    THEN SUM(invoice_discount) / SUM(pretax_amount + invoice_discount)
                    ELSE 0 
                END as discount_rate
            FROM bill_items
            WHERE account_id = {placeholder}
              AND billing_cycle BETWEEN {placeholder} AND {placeholder}
              AND instance_id != ''
            GROUP BY instance_id
            ORDER BY discount_amount DESC
            LIMIT 50
        """
        instances_res = self.db.query(instances_sql, (account_id, start_cycle, end_cycle))
        
        return {
            'monthly': monthly_res,
            'products': products_res,
            'instances': instances_res,
            'start_cycle': start_cycle,
            'end_cycle': end_cycle
        }

    def get_billing_cycles(self, account_id: str) -> List[Dict]:
        """
        获取指定账号的所有账期及统计信息

        Args:
            account_id: 账号ID

        Returns:
            账期列表，每个元素包含billing_cycle和record_count
        """
        placeholder = self._get_placeholder()

        try:
            sql = f"""
                SELECT
                    billing_cycle,
                    COUNT(*) as record_count
                FROM bill_items
                WHERE account_id = {placeholder}
                GROUP BY billing_cycle
                ORDER BY billing_cycle DESC
            """

            results = self._get_db().query(sql, (account_id,))
            return results if results else []
        except Exception as e:
            logger.error(f"获取账期列表失败: {str(e)}")
            return []

    def get_storage_stats(self) -> Dict:
        """获取存储统计信息"""
        placeholder = self._get_placeholder()

        # 总记录数
        total_result = self._get_db().query_one(f"SELECT COUNT(*) as count FROM bill_items")
        total_records = total_result['count'] if total_result else 0

        # 账号数
        account_result = self._get_db().query_one(f"SELECT COUNT(DISTINCT account_id) as count FROM bill_items")
        account_count = account_result['count'] if account_result else 0

        # 账期数
        cycle_result = self._get_db().query_one(f"SELECT COUNT(DISTINCT billing_cycle) as count FROM bill_items")
        cycle_count = cycle_result['count'] if cycle_result else 0

        # 时间范围
        min_result = self._get_db().query_one(f"SELECT MIN(billing_cycle) as min_cycle FROM bill_items")
        max_result = self._get_db().query_one(f"SELECT MAX(billing_cycle) as max_cycle FROM bill_items")

        # 数据库大小（MySQL）
        db_size_mb = 0.0
        try:
            if self.db_type == "mysql":
                # 查询MySQL数据库大小
                size_result = self._get_db().query_one("""
                    SELECT
                        ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as size_mb
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                    AND table_name = 'bill_items'
                """)
                db_size_mb = float(size_result.get('size_mb', 0) or 0) if size_result else 0.0
        except Exception as e:
            logger.warning(f"获取数据库大小失败: {str(e)}")
            db_size_mb = 0.0

        return {
            'total_records': total_records,
            'account_count': account_count,
            'cycle_count': cycle_count,
            'min_cycle': min_result.get('min_cycle') if min_result else None,
            'max_cycle': max_result.get('max_cycle') if max_result else None,
            'db_size_mb': db_size_mb,
            'db_path': self.db_path or "MySQL",
            'db_type': self.db_type
        }

    def get_discount_analysis_data(self, account_id: str, months: int = 19) -> Dict:
        """
        获取折扣分析数据
        
        Args:
            account_id: 账号ID
            months: 分析月数
            
        Returns:
            包含monthly和product数据的字典
        """
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        placeholder = self._get_placeholder()
        
        # 计算起始月份
        end_date = datetime.now()
        start_date = end_date - relativedelta(months=months)
        start_cycle = start_date.strftime("%Y-%m")
        
        try:
            # 按月聚合数据
            monthly_sql = f"""
                SELECT 
                    billing_cycle as month,
                    SUM(COALESCE(list_price, 0)) as official_price,
                    SUM(COALESCE(invoice_discount, 0)) as discount_amount,
                    SUM(COALESCE(pretax_amount, 0)) as actual_amount
                FROM bill_items
                WHERE account_id = {placeholder}
                AND billing_cycle >= {placeholder}
                GROUP BY billing_cycle
                ORDER BY billing_cycle ASC
            """
            
            monthly_results = self._get_db().query(monthly_sql, (account_id, start_cycle))
            
            # 计算折扣率
            monthly_data = []
            for row in monthly_results or []:
                official = float(row.get('official_price', 0) or 0)
                discount = float(row.get('discount_amount', 0) or 0)
                actual = float(row.get('actual_amount', 0) or 0)
                
                # 折扣计算逻辑优化：
                # 1. 如果 list_price > 0，直接用 list_price 作为官方价
                # 2. 如果 list_price = 0，用 (pretax_amount + invoice_discount) 作为官方价
                if official == 0:
                    official = actual + abs(discount)
                
                # 折扣率 = 折扣金额 / 官方价 * 100
                discount_rate = (abs(discount) / official * 100) if official > 0 else 0
                
                monthly_data.append({
                    'month': row['month'],
                    'official_price': official,
                    'discount_amount': abs(discount),
                    'actual_amount': actual,
                    'discount_rate': discount_rate
                })
            
            # 按产品聚合
            product_sql = f"""
                SELECT 
                    product_code,
                    product_name,
                    SUM(COALESCE(list_price, 0)) as official_price,
                    SUM(COALESCE(invoice_discount, 0)) as discount_amount,
                    SUM(COALESCE(pretax_amount, 0)) as actual_amount
                FROM bill_items
                WHERE account_id = {placeholder}
                AND billing_cycle >= {placeholder}
                GROUP BY product_code, product_name
                ORDER BY actual_amount DESC
            """
            
            product_results = self._get_db().query(product_sql, (account_id, start_cycle))
            
            # 转换为列表格式（按actual_amount降序）
            products_list = []
            for row in product_results or []:
                code = row.get('product_code', 'unknown')
                official = float(row.get('official_price', 0) or 0)
                discount = float(row.get('discount_amount', 0) or 0)
                actual = float(row.get('actual_amount', 0) or 0)
                
                # 折扣计算逻辑优化
                if official == 0:
                    official = actual + abs(discount)
                    
                discount_rate = (abs(discount) / official * 100) if official > 0 else 0
                
                products_list.append({
                    'product_code': code,
                    'product_name': row.get('product_name', code),
                    'official_price': official,
                    'discount_amount': abs(discount),
                    'actual_amount': actual,
                    'discount_rate': discount_rate
                })
            
            # 按实例聚合（Top 50）
            instance_sql = f"""
                SELECT 
                    instance_id,
                    product_code,
                    product_name,
                    nick_name,
                    SUM(COALESCE(list_price, 0)) as official_price,
                    SUM(COALESCE(invoice_discount, 0)) as discount_amount,
                    SUM(COALESCE(pretax_amount, 0)) as actual_amount
                FROM bill_items
                WHERE account_id = {placeholder}
                AND billing_cycle >= {placeholder}
                AND instance_id IS NOT NULL
                AND instance_id != ''
                GROUP BY instance_id, product_code, product_name, nick_name
                ORDER BY actual_amount DESC
                LIMIT 100
            """
            
            instance_results = self._get_db().query(instance_sql, (account_id, start_cycle))
            
            instances_list = []
            for row in instance_results or []:
                official = float(row.get('official_price', 0) or 0)
                discount = float(row.get('discount_amount', 0) or 0)
                actual = float(row.get('actual_amount', 0) or 0)
                
                # 折扣计算逻辑优化
                if official == 0:
                    official = actual + abs(discount)
                    
                discount_rate = (abs(discount) / official * 100) if official > 0 else 0
                
                instances_list.append({
                    'instance_id': row.get('instance_id', ''),
                    'product_code': row.get('product_code', ''),
                    'product_name': row.get('product_name', ''),
                    'nick_name': row.get('nick_name', ''),
                    'official_price': official,
                    'discount_amount': abs(discount),
                    'actual_amount': actual,
                    'discount_rate': discount_rate
                })
            
            # 计算结束月份
            end_cycle = end_date.strftime("%Y-%m")
            
            return {
                'monthly': monthly_data,
                'products': products_list,
                'instances': instances_list,
                'start_cycle': start_cycle,
                'end_cycle': end_cycle
            }
            
        except Exception as e:
            logger.error(f"获取折扣分析数据失败: {str(e)}")
            return {'monthly': [], 'products': [], 'instances': [], 'start_cycle': '', 'end_cycle': ''}





