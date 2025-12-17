#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账单数据存储管理器
使用SQLite存储账单明细数据，支持增量更新和全量查询
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json

logger = logging.getLogger(__name__)


class BillStorageManager:
    """账单数据存储管理器"""
    
    # 数据库schema版本
    SCHEMA_VERSION = 1
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化存储管理器
        
        Args:
            db_path: 数据库文件路径，默认使用~/.cloudlens/bills.db
        """
        if db_path is None:
            db_dir = Path.home() / ".cloudlens"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "bills.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 创建账单明细表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bill_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    billing_cycle TEXT NOT NULL,
                    
                    -- 基础信息
                    billing_date TEXT,
                    product_name TEXT,
                    product_code TEXT,
                    product_type TEXT,
                    subscription_type TEXT,
                    
                    -- 价格信息
                    pricing_unit TEXT,
                    usage REAL,
                    list_price REAL,
                    list_price_unit TEXT,
                    invoice_discount REAL,
                    pretax_amount REAL,
                    
                    -- 抵扣信息
                    deducted_by_coupons REAL,
                    deducted_by_cash_coupons REAL,
                    deducted_by_prepaid_card REAL,
                    payment_amount REAL,
                    outstanding_amount REAL,
                    currency TEXT,
                    
                    -- 账号信息
                    nick_name TEXT,
                    resource_group TEXT,
                    tag TEXT,
                    
                    -- 实例信息
                    instance_id TEXT,
                    instance_config TEXT,
                    internet_ip TEXT,
                    intranet_ip TEXT,
                    region TEXT,
                    zone TEXT,
                    
                    -- 计费明细
                    item TEXT,
                    cost_unit TEXT,
                    billing_item TEXT,
                    pip_code TEXT,
                    service_period TEXT,
                    service_period_unit TEXT,
                    
                    -- 扩展字段（JSON格式）
                    raw_data TEXT,
                    
                    -- 元数据
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- 唯一约束（防止重复插入）
                    UNIQUE(account_id, billing_cycle, instance_id, billing_date, billing_item)
                )
            """)
            
            # 创建索引（优化查询性能）
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bill_items_account_cycle 
                ON bill_items(account_id, billing_cycle)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bill_items_billing_date 
                ON bill_items(billing_date)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bill_items_product 
                ON bill_items(product_name)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bill_items_instance 
                ON bill_items(instance_id)
            """)
            
            # 添加复合索引（优化常用查询组合）
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bill_items_account_date 
                ON bill_items(account_id, billing_date)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bill_items_product_date 
                ON bill_items(product_code, billing_date)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bill_items_account_product 
                ON bill_items(account_id, product_code)
            """)
            
            # 优化折扣分析查询
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bill_items_subscription 
                ON bill_items(subscription_type, billing_date)
            """)
            
            # 创建账期统计表（快速查询用）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS billing_cycles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    billing_cycle TEXT NOT NULL,
                    record_count INTEGER DEFAULT 0,
                    total_amount REAL DEFAULT 0,
                    discount_amount REAL DEFAULT 0,
                    discount_rate REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(account_id, billing_cycle)
                )
            """)
            
            # 创建元数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 设置schema版本
            cursor.execute("""
                INSERT OR REPLACE INTO metadata (key, value) 
                VALUES ('schema_version', ?)
            """, (str(self.SCHEMA_VERSION),))
            
            conn.commit()
            logger.info(f"数据库初始化完成: {self.db_path}")
        
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库初始化失败: {str(e)}")
            raise
        finally:
            conn.close()
    
    def insert_bill_items(
        self, 
        account_id: str,
        billing_cycle: str,
        items: List[Dict]
    ) -> Tuple[int, int]:
        """
        批量插入账单明细
        
        Args:
            account_id: 账号ID
            billing_cycle: 账期（YYYY-MM）
            items: 账单明细列表
            
        Returns:
            (插入数量, 跳过数量)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        inserted = 0
        skipped = 0
        
        try:
            for item in items:
                try:
                    # 提取核心字段
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
                        item.get('Tag', ''),
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
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO bill_items (
                            account_id, billing_cycle, billing_date,
                            product_name, product_code, product_type, subscription_type,
                            pricing_unit, usage, list_price, list_price_unit,
                            invoice_discount, pretax_amount,
                            deducted_by_coupons, deducted_by_cash_coupons,
                            deducted_by_prepaid_card, payment_amount,
                            outstanding_amount, currency,
                            nick_name, resource_group, tag,
                            instance_id, instance_config, internet_ip, intranet_ip,
                            region, zone, item, cost_unit, billing_item,
                            pip_code, service_period, service_period_unit,
                            raw_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, values)
                    
                    if cursor.rowcount > 0:
                        inserted += 1
                    else:
                        skipped += 1
                
                except Exception as e:
                    logger.warning(f"插入账单明细失败: {str(e)}")
                    skipped += 1
            
            # 更新账期统计
            self._update_billing_cycle_stats(cursor, account_id, billing_cycle)
            
            conn.commit()
            logger.info(f"账期 {billing_cycle} 插入 {inserted} 条，跳过 {skipped} 条")
            
            return inserted, skipped
        
        except Exception as e:
            conn.rollback()
            logger.error(f"批量插入失败: {str(e)}")
            raise
        finally:
            conn.close()
    
    def _update_billing_cycle_stats(
        self, 
        cursor: sqlite3.Cursor,
        account_id: str,
        billing_cycle: str
    ):
        """更新账期统计信息"""
        # 查询统计数据
        cursor.execute("""
            SELECT 
                COUNT(*) as count,
                SUM(pretax_amount) as total,
                SUM(list_price - pretax_amount) as discount,
                CASE 
                    WHEN SUM(list_price) > 0 
                    THEN (SUM(list_price - pretax_amount) / SUM(list_price))
                    ELSE 0 
                END as rate
            FROM bill_items
            WHERE account_id = ? AND billing_cycle = ?
        """, (account_id, billing_cycle))
        
        stats = cursor.fetchone()
        
        # 插入或更新统计
        cursor.execute("""
            INSERT OR REPLACE INTO billing_cycles (
                account_id, billing_cycle, 
                record_count, total_amount, discount_amount, discount_rate,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (account_id, billing_cycle, stats[0], stats[1] or 0, stats[2] or 0, stats[3] or 0))
    
    def get_billing_cycles(self, account_id: str) -> List[Dict]:
        """
        获取账号的所有账期列表
        
        Args:
            account_id: 账号ID
            
        Returns:
            账期列表，按时间倒序
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    billing_cycle,
                    record_count,
                    total_amount,
                    discount_amount,
                    discount_rate,
                    created_at
                FROM billing_cycles
                WHERE account_id = ?
                ORDER BY billing_cycle DESC
            """, (account_id,))
            
            rows = cursor.fetchall()
            
            return [{
                'billing_cycle': row[0],
                'record_count': row[1],
                'total_amount': row[2],
                'discount_amount': row[3],
                'discount_rate': row[4],
                'created_at': row[5]
            } for row in rows]
        
        finally:
            conn.close()
    
    def get_bill_items(
        self,
        account_id: str,
        start_cycle: Optional[str] = None,
        end_cycle: Optional[str] = None,
        product_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        查询账单明细
        
        Args:
            account_id: 账号ID
            start_cycle: 开始账期（YYYY-MM）
            end_cycle: 结束账期（YYYY-MM）
            product_name: 产品名称过滤
            limit: 限制返回数量
            
        Returns:
            账单明细列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 构建查询条件
            conditions = ["account_id = ?"]
            params = [account_id]
            
            if start_cycle:
                conditions.append("billing_cycle >= ?")
                params.append(start_cycle)
            
            if end_cycle:
                conditions.append("billing_cycle <= ?")
                params.append(end_cycle)
            
            if product_name:
                conditions.append("product_name = ?")
                params.append(product_name)
            
            where_clause = " AND ".join(conditions)
            
            # 构建SQL
            sql = f"""
                SELECT * FROM bill_items
                WHERE {where_clause}
                ORDER BY billing_date DESC
            """
            
            if limit:
                sql += f" LIMIT {limit}"
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # 转换为字典列表
            return [dict(row) for row in rows]
        
        finally:
            conn.close()
    
    def get_discount_analysis_data(
        self,
        account_id: str,
        months: int = 6
    ) -> Dict:
        """
        获取折扣分析所需的数据（优化版，直接聚合）
        
        Args:
            account_id: 账号ID
            months: 分析月数
            
        Returns:
            折扣分析数据
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取最近N个月的账期
            cursor.execute("""
                SELECT DISTINCT billing_cycle
                FROM bill_items
                WHERE account_id = ?
                ORDER BY billing_cycle DESC
                LIMIT ?
            """, (account_id, months))
            
            cycles = [row[0] for row in cursor.fetchall()]
            
            if not cycles:
                return {'cycles': [], 'monthly': [], 'products': [], 'instances': []}
            
            start_cycle = cycles[-1] if cycles else None
            end_cycle = cycles[0] if cycles else None
            
            # 月度趋势
            # 原价 = pretax_amount + invoice_discount（阿里云API不提供list_price）
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
                WHERE account_id = ? AND billing_cycle BETWEEN ? AND ?
                GROUP BY billing_cycle
                ORDER BY billing_cycle
            """, (account_id, start_cycle, end_cycle))
            
            monthly = [{
                'month': row[0],
                'official_price': row[1],
                'actual_amount': row[2],
                'discount_amount': row[3],
                'discount_rate': row[4]
            } for row in cursor.fetchall()]
            
            # 产品维度
            cursor.execute("""
                SELECT
                    product_name,
                    SUM(pretax_amount + invoice_discount) as official_price,
                    SUM(pretax_amount) as actual_amount,
                    SUM(invoice_discount) as discount_amount,
                    CASE
                        WHEN SUM(pretax_amount + invoice_discount) > 0
                        THEN (SUM(invoice_discount) / SUM(pretax_amount + invoice_discount))
                        ELSE 0
                    END as discount_rate
                FROM bill_items
                WHERE account_id = ? AND billing_cycle BETWEEN ? AND ?
                GROUP BY product_name
                ORDER BY discount_amount DESC
                LIMIT 50
            """, (account_id, start_cycle, end_cycle))
            
            products = [{
                'product': row[0],
                'official_price': row[1],
                'actual_amount': row[2],
                'discount_amount': row[3],
                'discount_rate': row[4]
            } for row in cursor.fetchall()]
            
            # 实例维度（TOP 50）
            cursor.execute("""
                SELECT
                    instance_id,
                    product_name,
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
                    AND billing_cycle BETWEEN ? AND ?
                    AND instance_id != ''
                GROUP BY instance_id, product_name
                ORDER BY discount_amount DESC
                LIMIT 50
            """, (account_id, start_cycle, end_cycle))
            
            instances = [{
                'instance_id': row[0],
                'product': row[1],
                'official_price': row[2],
                'actual_amount': row[3],
                'discount_amount': row[4],
                'discount_rate': row[5]
            } for row in cursor.fetchall()]
            
            return {
                'cycles': cycles,
                'monthly': monthly,
                'products': products,
                'instances': instances,
                'start_cycle': start_cycle,
                'end_cycle': end_cycle
            }
        
        finally:
            conn.close()
    
    def get_storage_stats(self) -> Dict:
        """获取存储统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 总记录数
            cursor.execute("SELECT COUNT(*) FROM bill_items")
            total_records = cursor.fetchone()[0]
            
            # 账号数
            cursor.execute("SELECT COUNT(DISTINCT account_id) FROM bill_items")
            account_count = cursor.fetchone()[0]
            
            # 账期数
            cursor.execute("SELECT COUNT(DISTINCT billing_cycle) FROM bill_items")
            cycle_count = cursor.fetchone()[0]
            
            # 数据库文件大小
            db_size = Path(self.db_path).stat().st_size
            
            # 最早和最晚账期
            cursor.execute("SELECT MIN(billing_cycle), MAX(billing_cycle) FROM bill_items")
            min_cycle, max_cycle = cursor.fetchone()
            
            return {
                'total_records': total_records,
                'account_count': account_count,
                'cycle_count': cycle_count,
                'db_size_mb': db_size / 1024 / 1024,
                'min_cycle': min_cycle,
                'max_cycle': max_cycle,
                'db_path': self.db_path
            }
        
        finally:
            conn.close()


def main():
    """测试用例"""
    storage = BillStorageManager()
    
    # 显示统计信息
    stats = storage.get_storage_stats()
    print("\n=== 数据库统计 ===")
    print(f"总记录数: {stats['total_records']:,}")
    print(f"账号数: {stats['account_count']}")
    print(f"账期数: {stats['cycle_count']}")
    print(f"数据库大小: {stats['db_size_mb']:.2f} MB")
    print(f"时间范围: {stats['min_cycle']} 至 {stats['max_cycle']}")
    print(f"数据库路径: {stats['db_path']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

