"""
账单Repository - 数据访问层
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from cloudlens.core.database import DatabaseFactory
from cloudlens.core.config import CloudAccount
from .base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)


class BillRepository(BaseRepository):
    """账单数据访问"""
    
    def __init__(self):
        super().__init__()
        self.db = DatabaseFactory.create_adapter("mysql")
    
    def get_billing_overview(
        self,
        account_config: CloudAccount,
        billing_cycle: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """从数据库获取账单概览"""
        try:
            if billing_cycle is None:
                billing_cycle = datetime.now().strftime("%Y-%m")
            
            # 构造account_id
            account_id = f"{account_config.access_key_id[:10]}-{account_config.name}"
            
            # 验证account_id是否存在
            account_result = self.db.query_one("""
                SELECT DISTINCT account_id
                FROM bill_items
                WHERE account_id = %s
                LIMIT 1
            """, (account_id,))
            
            if not account_result:
                # 尝试模糊匹配
                account_result = self.db.query_one("""
                    SELECT DISTINCT account_id
                    FROM bill_items
                    WHERE account_id LIKE %s
                    LIMIT 1
                """, (f"%{account_config.name}%",))
                
                if not account_result:
                    return None
                
                if isinstance(account_result, dict):
                    matched_account_id = account_result.get('account_id')
                else:
                    matched_account_id = account_result[0] if account_result else None
                
                if matched_account_id and matched_account_id != account_id:
                    account_id = matched_account_id
            
            # 按产品聚合
            product_results = self.db.query("""
                SELECT
                    product_name,
                    product_code,
                    subscription_type,
                    SUM(pretax_amount) as total_pretax
                FROM bill_items
                WHERE account_id = %s
                    AND billing_cycle = %s
                    AND pretax_amount IS NOT NULL
                GROUP BY product_name, product_code, subscription_type
            """, (account_id, billing_cycle))
            
            by_product: Dict[str, float] = {}
            by_product_name: Dict[str, str] = {}
            by_product_subscription: Dict[str, Dict[str, float]] = {}
            total = 0.0
            
            for row in product_results:
                if isinstance(row, dict):
                    product_name = row.get('product_name') or "unknown"
                    product_code = row.get('product_code') or "unknown"
                    subscription_type = row.get('subscription_type') or "Unknown"
                    pretax = float(row.get('total_pretax') or 0)
                else:
                    product_name = row[0] or "unknown"
                    product_code = row[1] or "unknown"
                    subscription_type = row[2] or "Unknown"
                    pretax = float(row[3] or 0)
                
                if pretax <= 0:
                    continue
                
                if product_code not in by_product_name:
                    by_product_name[product_code] = product_name
                
                by_product[product_code] = by_product.get(product_code, 0.0) + pretax
                by_product_subscription.setdefault(product_code, {})
                by_product_subscription[product_code][subscription_type] = (
                    by_product_subscription[product_code].get(subscription_type, 0.0) + pretax
                )
                
                total += pretax
            
            if len(by_product) == 0:
                return None
            
            return {
                "billing_cycle": billing_cycle,
                "total_pretax": round(total, 2),
                "by_product": {k: round(v, 2) for k, v in by_product.items()},
                "by_product_name": by_product_name,
                "by_product_subscription": {
                    code: {k: round(v, 2) for k, v in sub.items()}
                    for code, sub in by_product_subscription.items()
                },
                "data_source": "local_db"
            }
        except Exception as e:
            self.handle_error(e, "get_billing_overview")
            return None
