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

from core.database import DatabaseFactory, DatabaseAdapter

logger = logging.getLogger(__name__)


class BillStorageManager:
    """账单数据存储管理器（支持SQLite和MySQL）"""
    
    # 数据库schema版本
    SCHEMA_VERSION = 1
    
    def __init__(self, db_path: Optional[str] = None, db_type: Optional[str] = None):
        """
        初始化存储管理器
        
        Args:
            db_path: 数据库文件路径（仅SQLite使用），默认使用~/.cloudlens/bills.db
            db_type: 数据库类型（'sqlite' 或 'mysql'），None则从环境变量读取
        """
        self.db_type = db_type or os.getenv("DB_TYPE", "mysql").lower()
        
        if self.db_type == "mysql":
            # MySQL使用数据库抽象层
            self.db = DatabaseFactory.create_adapter("mysql")
            self.db_path = None  # MySQL不使用文件路径
        else:
            # SQLite使用文件路径
            if db_path is None:
                db_dir = Path.home() / ".cloudlens"
                db_dir.mkdir(parents=True, exist_ok=True)
                db_path = str(db_dir / "bills.db")
            self.db_path = db_path
            self.db = DatabaseFactory.create_adapter("sqlite", db_path=db_path)
        
        self._init_database()
    
    def _get_placeholder(self) -> str:
        """获取SQL占位符"""
        return "%s" if self.db_type == "mysql" else "?"
    
    def _quote_column(self, col: str) -> str:
        """引用列名（处理MySQL保留关键字）"""
        reserved = ['usage', 'key', 'order', 'group', 'select', 'table', 'index']
        if col.lower() in reserved:
            return f"`{col}`"
        return col
    
    def _init_database(self):
        """初始化数据库表结构"""
        if self.db_type == "mysql":
            # MySQL表结构已在init_mysql_schema.sql中创建
            # 这里只检查表是否存在
            try:
                self.db.query("SELECT 1 FROM bill_items LIMIT 1")
                logger.info("MySQL账单表已存在")
            except Exception:
                logger.warning("MySQL账单表不存在，请先运行sql/init_mysql_schema.sql")
        else:
            # SQLite表结构
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS bill_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    billing_cycle TEXT NOT NULL,
                    billing_date TEXT,
                    product_name TEXT,
                    product_code TEXT,
                    product_type TEXT,
                    subscription_type TEXT,
                    pricing_unit TEXT,
                    usage REAL,
                    list_price REAL,
                    list_price_unit TEXT,
                    invoice_discount REAL,
                    pretax_amount REAL,
                    deducted_by_coupons REAL,
                    deducted_by_cash_coupons REAL,
                    deducted_by_prepaid_card REAL,
                    payment_amount REAL,
                    outstanding_amount REAL,
                    currency TEXT,
                    nick_name TEXT,
                    resource_group TEXT,
                    tag TEXT,
                    instance_id TEXT,
                    instance_config TEXT,
                    internet_ip TEXT,
                    intranet_ip TEXT,
                    region TEXT,
                    zone TEXT,
                    item TEXT,
                    cost_unit TEXT,
                    billing_item TEXT,
                    pip_code TEXT,
                    service_period TEXT,
                    service_period_unit TEXT,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(account_id, billing_cycle, instance_id, billing_date, billing_item)
                )
            """)
    
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
        placeholder = self._get_placeholder()
        inserted = 0
        skipped = 0
        
        try:
            self.db.begin_transaction()
            
            for item in items:
                try:
                    # 准备数据
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
                    
                    if self.db_type == "mysql":
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
                    else:
                        # SQLite使用INSERT OR IGNORE
                        sql = f"""
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
                            ) VALUES ({', '.join([placeholder] * 35)})
                        """
                    
                    cursor = self.db.execute(sql, values)
                    
                    # 检查是否插入成功
                    if hasattr(cursor, 'rowcount') and cursor.rowcount > 0:
                        inserted += 1
                    else:
                        skipped += 1
                
                except Exception as e:
                    logger.warning(f"插入账单明细失败: {str(e)}")
                    skipped += 1
            
            self.db.commit()
            logger.info(f"账期 {billing_cycle} 插入 {inserted} 条，跳过 {skipped} 条")
            
            return inserted, skipped
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"批量插入失败: {str(e)}")
            raise
    
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
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        sql = f"SELECT * FROM bill_items WHERE {where_clause} ORDER BY billing_date DESC {limit_clause}"
        
        return self.db.query(sql, tuple(params) if params else None)
    
    def get_storage_stats(self) -> Dict:
        """获取存储统计信息"""
        placeholder = self._get_placeholder()
        
        # 总记录数
        total_result = self.db.query_one(f"SELECT COUNT(*) as count FROM bill_items")
        total_records = total_result['count'] if total_result else 0
        
        # 账号数
        account_result = self.db.query_one(f"SELECT COUNT(DISTINCT account_id) as count FROM bill_items")
        account_count = account_result['count'] if account_result else 0
        
        # 账期数
        cycle_result = self.db.query_one(f"SELECT COUNT(DISTINCT billing_cycle) as count FROM bill_items")
        cycle_count = cycle_result['count'] if cycle_result else 0
        
        # 时间范围
        min_result = self.db.query_one(f"SELECT MIN(billing_cycle) as min_cycle FROM bill_items")
        max_result = self.db.query_one(f"SELECT MAX(billing_cycle) as max_cycle FROM bill_items")
        
        return {
            'total_records': total_records,
            'account_count': account_count,
            'cycle_count': cycle_count,
            'min_cycle': min_result.get('min_cycle') if min_result else None,
            'max_cycle': max_result.get('max_cycle') if max_result else None,
            'db_path': self.db_path or "MySQL",
            'db_type': self.db_type
        }



