#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
折扣分析器 - 数据库版本
从SQLite数据库读取账单数据进行分析
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DiscountAnalyzerDB:
    """折扣分析器（数据库版本）"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化分析器
        
        Args:
            db_path: 数据库路径，默认使用~/.cloudlens/bills.db
        """
        from cloudlens.core.bill_storage import BillStorageManager
        self.storage = BillStorageManager(db_path)
    
    def analyze_discount_trend(
        self,
        account_id: str,
        months: int = 6
    ) -> Dict:
        """
        分析折扣趋势（从数据库）
        
        Args:
            account_id: 账号ID
            months: 分析月数
            
        Returns:
            分析结果字典
        """
        logger.info(f"开始分析账号 {account_id} 最近 {months} 个月的折扣趋势")
        
        # 从数据库获取聚合数据
        data = self.storage.get_discount_analysis_data(account_id, months)
        
        if not data['monthly']:
            return {
                'success': False,
                'error': '没有找到账单数据'
            }
        
        # 计算趋势分析
        monthly_data = data['monthly']
        
        # 总体统计
        total_official = sum(m['official_price'] for m in monthly_data)
        total_discount = sum(m['discount_amount'] for m in monthly_data)
        avg_discount_rate = total_discount / total_official if total_official > 0 else 0
        
        # 最新折扣率
        latest_rate = monthly_data[-1]['discount_rate'] if monthly_data else 0
        
        # 趋势变化
        if len(monthly_data) >= 2:
            first_rate = monthly_data[0]['discount_rate']
            trend_change_pct = ((latest_rate - first_rate) / first_rate * 100) if first_rate > 0 else 0
            
            if trend_change_pct > 1:
                trend = "上升"
                trend_icon = "📈"
            elif trend_change_pct < -1:
                trend = "下降"
                trend_icon = "📉"
            else:
                trend = "平稳"
                trend_icon = "➡️"
        else:
            trend = "数据不足"
            trend_icon = "❓"
            trend_change_pct = 0
        
        # 产品维度TOP20
        products = data['products'][:20]
        
        # 实例维度TOP50
        instances = data['instances'][:50]
        
        # 合同分析（从raw_data中提取合同信息）
        contracts = self._analyze_contracts(account_id, data['start_cycle'], data['end_cycle'])
        
        return {
            'success': True,
            'account_id': account_id,
            'months': months,
            'start_cycle': data['start_cycle'],
            'end_cycle': data['end_cycle'],
            
            # 总体统计
            'summary': {
                'total_discount': total_discount,
                'avg_discount_rate': avg_discount_rate,
                'latest_discount_rate': latest_rate,
                'trend': trend,
                'trend_icon': trend_icon,
                'trend_change_pct': trend_change_pct
            },
            
            # 月度趋势
            'monthly_trend': monthly_data,
            
            # 产品维度
            'product_discounts': products,
            
            # 合同维度
            'contract_discounts': contracts,
            
            # 实例维度
            'instance_discounts': instances,
            
            # 元数据
            'metadata': {
                'analysis_time': datetime.now().isoformat(),
                'data_source': 'database',
                'db_path': self.storage.db_path
            }
        }
    
    def _analyze_contracts(
        self,
        account_id: str,
        start_cycle: str,
        end_cycle: str
    ) -> List[Dict]:
        """分析合同折扣（从raw_data提取）"""
        import json
        
        # 使用BillStorageManager的数据库抽象层
        try:
            # 从raw_data中提取合同信息
            rows = self.storage.db.query("""
                SELECT raw_data
                FROM bill_items
                WHERE account_id = ?
                    AND billing_cycle BETWEEN ? AND ?
                    AND raw_data LIKE '%ContractNo%'
                LIMIT 10000
            """, (account_id, start_cycle, end_cycle))
            
            contract_stats = {}
            
            for row in rows:
                try:
                    # 处理字典格式的结果（MySQL）或元组格式（SQLite）
                    raw_data = row['raw_data'] if isinstance(row, dict) else row[0]
                    data = json.loads(raw_data)
                    contract_no = data.get('ContractNo', '')
                    
                    if contract_no and contract_no != '':
                        if contract_no not in contract_stats:
                            contract_stats[contract_no] = {
                                'contract_no': contract_no,
                                'contract_name': data.get('ContractName', ''),
                                'official_price': 0,
                                'actual_amount': 0,
                                'discount_amount': 0
                            }
                        
                        official = float(data.get('ListPrice', 0) or 0)
                        actual = float(data.get('PretaxAmount', 0) or 0)
                        
                        contract_stats[contract_no]['official_price'] += official
                        contract_stats[contract_no]['actual_amount'] += actual
                        contract_stats[contract_no]['discount_amount'] += (official - actual)
                
                except:
                    continue
            
            # 计算折扣率并排序
            contracts = []
            for stats in contract_stats.values():
                if stats['official_price'] > 0:
                    stats['discount_rate'] = stats['discount_amount'] / stats['official_price']
                    contracts.append(stats)
            
            # 按折扣金额排序
            contracts.sort(key=lambda x: x['discount_amount'], reverse=True)
            
            return contracts[:10]  # TOP 10
        
        except Exception as e:
            logger.error(f"分析合同折扣失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []


def main():
    """测试用例"""
    analyzer = DiscountAnalyzerDB()
    
    # 分析ydzn账号
    result = analyzer.analyze_discount_trend(
        account_id="LTAI5tECY4-ydzn",
        months=12
    )
    
    if result['success']:
        summary = result['summary']
        print(f"\n=== 折扣分析结果 ===")
        print(f"账期: {result['start_cycle']} 至 {result['end_cycle']}")
        print(f"累计折扣: ¥{summary['total_discount']:,.2f}")
        print(f"平均折扣率: {summary['avg_discount_rate']*100:.2f}%")
        print(f"最新折扣率: {summary['latest_discount_rate']*100:.2f}%")
        print(f"折扣趋势: {summary['trend_icon']} {summary['trend']} {summary['trend_change_pct']:+.2f}%")
        
        print(f"\n=== TOP 5 产品折扣 ===")
        for i, p in enumerate(result['product_discounts'][:5], 1):
            print(f"{i}. {p['product']}: ¥{p['discount_amount']:,.2f} ({p['discount_rate']*100:.2f}%)")
    else:
        print(f"分析失败: {result.get('error')}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()






