#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账单数据获取器
通过阿里云BSS OpenAPI自动获取账单明细数据
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import csv

logger = logging.getLogger(__name__)


class BillFetcher:
    """阿里云账单数据获取器"""
    
    def __init__(
        self, 
        access_key_id: str, 
        access_key_secret: str, 
        region: str = "cn-hangzhou",
        use_database: bool = False,
        db_path: Optional[str] = None
    ):
        """
        初始化账单获取器
        
        Args:
            access_key_id: 阿里云AccessKeyId
            access_key_secret: 阿里云AccessKeySecret
            region: 区域，默认cn-hangzhou
            use_database: 是否使用数据库存储，默认False
            db_path: 数据库路径，None则使用默认路径
        """
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.region = region
        self.use_database = use_database
        self._client = None
        self._storage = None
        
        if use_database:
            from cloudlens.core.bill_storage import BillStorageManager
            # db_path参数已废弃，只使用MySQL
            self._storage = BillStorageManager()
    
    @property
    def client(self):
        """延迟初始化BSS OpenAPI客户端"""
        if self._client is None:
            try:
                from aliyunsdkcore.client import AcsClient
                self._client = AcsClient(
                    self.access_key_id,
                    self.access_key_secret,
                    self.region
                )
            except ImportError:
                raise ImportError(
                    "请安装阿里云BSS OpenAPI SDK: "
                    "pip install aliyun-python-sdk-core aliyun-python-sdk-bssopenapi"
                )
        return self._client
    
    def fetch_instance_bill(
        self,
        billing_cycle: str,
        max_records: Optional[int] = None,
        page_size: int = 300,
        billing_date: Optional[str] = None,
        granularity: Optional[str] = None
    ) -> List[Dict]:
        """
        获取实例账单明细（最详细的数据，类似CSV）

        Args:
            billing_cycle: 账期，格式：YYYY-MM（如：2025-12）
            max_records: 最大记录数，None表示获取所有
            page_size: 每页记录数，最大300
            billing_date: 账单日期，格式：YYYY-MM-DD（可选，用于按天查询）
            granularity: 查询粒度，可选值：DAILY（按天）、MONTHLY（按月，默认）

        Returns:
            账单明细列表
        """
        try:
            from aliyunsdkbssopenapi.request.v20171214 import QueryInstanceBillRequest
        except (ImportError, ModuleNotFoundError) as e:
            raise ImportError(
                "\n\n❌ 缺少阿里云账单API依赖包！\n"
                "   请运行以下命令安装：\n"
                "   pip install aliyun-python-sdk-bssopenapi\n"
            ) from e
        import json
        
        all_records = []
        page_num = 1
        total_count = 0
        
        if billing_date and granularity == "DAILY":
            logger.info(f"开始获取按天账单明细：账期={billing_cycle}, 日期={billing_date}")
        else:
            logger.info(f"开始获取账单明细：账期={billing_cycle}")
        
        while True:
            request = QueryInstanceBillRequest.QueryInstanceBillRequest()
            request.set_BillingCycle(billing_cycle)
            request.set_PageNum(page_num)
            request.set_PageSize(page_size)
            
            # 如果指定了按天查询，添加相应参数
            if granularity == "DAILY" and billing_date:
                request.set_Granularity("DAILY")
                request.set_BillingDate(billing_date)
            
            try:
                response = self.client.do_action_with_exception(request)
                result = json.loads(response)
                
                if not result.get("Success"):
                    error_msg = result.get("Message", "Unknown error")
                    logger.error(f"API调用失败: {error_msg}")
                    break
                
                data = result.get("Data", {})
                items = data.get("Items", {}).get("Item", [])
                
                if page_num == 1:
                    total_count = data.get("TotalCount", 0)
                    if billing_date:
                        logger.info(f"日期 {billing_date} 共有 {total_count} 条记录")
                    else:
                        logger.info(f"账期 {billing_cycle} 共有 {total_count} 条记录")
                
                if not items:
                    break
                
                all_records.extend(items)
                logger.info(f"已获取 {len(all_records)}/{total_count} 条记录")
                
                # 检查是否达到最大记录数
                if max_records and len(all_records) >= max_records:
                    all_records = all_records[:max_records]
                    logger.info(f"已达到最大记录数限制: {max_records}")
                    break
                
                # 检查是否还有更多数据
                if len(all_records) >= total_count:
                    break
                
                page_num += 1
                
                # API限流：避免调用过快
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"获取第 {page_num} 页数据失败: {str(e)}")
                break
        
        if billing_date:
            logger.info(f"日期 {billing_date} 共获取 {len(all_records)} 条记录")
        else:
            logger.info(f"账期 {billing_cycle} 共获取 {len(all_records)} 条记录")
        return all_records
    
    def fetch_daily_bills(
        self,
        start_date: str,
        end_date: str,
        max_records_per_day: Optional[int] = None
    ) -> Dict[str, List[Dict]]:
        """
        按天获取账单数据
        
        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            max_records_per_day: 每天最大记录数，None表示获取所有
            
        Returns:
            按日期分组的账单数据字典，key为日期（YYYY-MM-DD），value为账单列表
        """
        from datetime import datetime, timedelta
        
        daily_bills = {}
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        current_date = start
        while current_date <= end:
            date_str = current_date.strftime("%Y-%m-%d")
            billing_cycle = current_date.strftime("%Y-%m")
            
            logger.info(f"获取日期 {date_str} 的账单数据...")

            try:
                bills = self.fetch_instance_bill(
                    billing_cycle=billing_cycle,
                    billing_date=date_str,
                    granularity="DAILY",
                    max_records=max_records_per_day
                )
                daily_bills[date_str] = bills
                logger.info(f"日期 {date_str} 获取到 {len(bills)} 条记录")
            except (ImportError, ModuleNotFoundError) as e:
                # 依赖缺失错误，直接抛出，不要静默处理
                logger.error(f"获取日期 {date_str} 的账单失败: {str(e)}")
                raise
            except Exception as e:
                logger.warning(f"获取日期 {date_str} 的账单失败: {str(e)}")
                daily_bills[date_str] = []
            
            current_date += timedelta(days=1)
            
            # API限流：每天之间稍作延迟
            time.sleep(0.3)
        
        return daily_bills
    
    def fetch_bill_overview(self, billing_cycle: str) -> List[Dict]:
        """
        获取账单概览（按产品+计费方式聚合）

        Args:
            billing_cycle: 账期，格式：YYYY-MM

        Returns:
            账单概览列表
        """
        try:
            from aliyunsdkbssopenapi.request.v20171214 import QueryBillOverviewRequest
        except (ImportError, ModuleNotFoundError) as e:
            raise ImportError(
                "\n\n❌ 缺少阿里云账单API依赖包！\n"
                "   请运行以下命令安装：\n"
                "   pip install aliyun-python-sdk-bssopenapi\n"
            ) from e
        import json
        
        request = QueryBillOverviewRequest.QueryBillOverviewRequest()
        request.set_BillingCycle(billing_cycle)
        
        try:
            response = self.client.do_action_with_exception(request)
            result = json.loads(response)
            
            if result.get("Success"):
                items = result.get("Data", {}).get("Items", {}).get("Item", [])
                logger.info(f"获取账单概览成功：{len(items)} 条记录")
                return items
            else:
                logger.error(f"获取账单概览失败: {result.get('Message')}")
                return []
        except Exception as e:
            logger.error(f"获取账单概览异常: {str(e)}")
            return []
    
    def save_to_csv(
        self, 
        records: List[Dict], 
        output_path: Path,
        billing_cycle: str
    ):
        """
        保存账单数据到CSV文件（格式与阿里云控制台下载的一致）
        
        Args:
            records: 账单记录列表
            output_path: 输出文件路径
            billing_cycle: 账期
        """
        if not records:
            logger.warning("没有数据可保存")
            return
        
        # CSV字段映射（API字段 -> CSV字段）
        field_mapping = {
            'BillingDate': '账期',
            'ProductName': '产品',
            'ProductCode': '产品代码',
            'ProductType': '产品类型',
            'SubscriptionType': '计费方式',
            'PricingUnit': '计价单位',
            'Usage': '用量',
            'ListPrice': '官网价',
            'ListPriceUnit': '官网价单位',
            'InvoiceDiscount': '折扣',
            'PretaxAmount': '应付金额',
            'DeductedByCoupons': '代金券抵扣',
            'DeductedByCashCoupons': '现金券抵扣',
            'DeductedByPrepaidCard': '储值卡抵扣',
            'PaymentAmount': '实付金额',
            'OutstandingAmount': '未结算金额',
            'Currency': '币种',
            'NickName': '账号别名',
            'ResourceGroup': '资源组',
            'Tag': '标签',
            'InstanceID': '实例ID',
            'InstanceConfig': '实例配置',
            'InternetIP': '公网IP',
            'IntranetIP': '内网IP',
            'Region': '地域',
            'Zone': '可用区',
            'Item': '明细',
            'CostUnit': '成本单元',
            'BillingItem': '计费项',
            'PipCode': '商品编码',
            'ServicePeriod': '服务时长',
            'ServicePeriodUnit': '服务时长单位',
        }
        
        # 扩展字段（与折扣分析相关）
        extended_fields = ['优惠金额', '折扣率']
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            # 写入CSV头
            all_fields = list(field_mapping.values()) + extended_fields
            writer = csv.DictWriter(f, fieldnames=all_fields)
            writer.writeheader()
            
            # 写入数据
            for record in records:
                row = {}
                
                # 映射API字段到CSV字段
                for api_field, csv_field in field_mapping.items():
                    row[csv_field] = record.get(api_field, '')
                
                # 计算扩展字段
                try:
                    official_price = float(record.get('ListPrice', 0) or 0)
                    pretax_amount = float(record.get('PretaxAmount', 0) or 0)
                    
                    # 优惠金额 = 官网价 - 应付金额
                    discount_amount = max(0, official_price - pretax_amount)
                    row['优惠金额'] = f"{discount_amount:.2f}"
                    
                    # 折扣率 = 优惠金额 / 官网价
                    if official_price > 0:
                        discount_rate = discount_amount / official_price
                        row['折扣率'] = f"{discount_rate:.4f}"
                    else:
                        row['折扣率'] = "0"
                except:
                    row['优惠金额'] = "0"
                    row['折扣率'] = "0"
                
                writer.writerow(row)
        
        logger.info(f"已保存 {len(records)} 条记录到: {output_path}")
    
    def fetch_and_save_bills(
        self,
        start_month: str,
        end_month: str,
        output_dir: Optional[Path] = None,
        account_name: Optional[str] = None,
        account_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        批量获取并保存多个月份的账单
        
        Args:
            start_month: 开始月份，格式：YYYY-MM
            end_month: 结束月份，格式：YYYY-MM
            output_dir: 输出目录（CSV模式需要）
            account_name: 账号名称（用于文件夹命名）
            account_id: 账号ID（数据库模式需要）
            
        Returns:
            月份 -> 结果的映射（CSV路径或数据库记录数）
        """
        from dateutil.relativedelta import relativedelta
        
        start_date = datetime.strptime(start_month, "%Y-%m")
        end_date = datetime.strptime(end_month, "%Y-%m")
        
        # CSV模式：创建输出目录
        if not self.use_database and output_dir:
            if account_name:
                output_dir = output_dir / account_name
            output_dir.mkdir(parents=True, exist_ok=True)
        
        result = {}
        current_date = start_date
        total_records = 0
        
        logger.info(f"开始批量获取账单：{start_month} 至 {end_month}")
        logger.info(f"存储模式: {'数据库' if self.use_database else 'CSV文件'}")
        
        while current_date <= end_date:
            billing_cycle = current_date.strftime("%Y-%m")
            logger.info(f"\n{'='*60}")
            logger.info(f"处理账期: {billing_cycle}")
            logger.info(f"{'='*60}")
            
            # 按天获取账单数据（这样可以获取到BillingDate字段）
            all_records = []
            month_start = current_date
            month_end = (current_date + relativedelta(months=1)) - timedelta(days=1)
            day_date = month_start
            
            logger.info(f"开始按天获取账单数据：{month_start.strftime('%Y-%m-%d')} 至 {month_end.strftime('%Y-%m-%d')}")
            
            while day_date <= month_end and day_date <= datetime.now():
                date_str = day_date.strftime("%Y-%m-%d")
                try:
                    # 按天查询，使用DAILY粒度
                    daily_records = self.fetch_instance_bill(
                        billing_cycle=billing_cycle,
                        billing_date=date_str,
                        granularity="DAILY"
                    )
                    if daily_records:
                        all_records.extend(daily_records)
                        logger.info(f"日期 {date_str} 获取到 {len(daily_records)} 条记录")
                except Exception as e:
                    logger.warning(f"获取日期 {date_str} 的账单失败: {str(e)}")
                
                day_date += timedelta(days=1)
                # API限流：每天之间稍作延迟
                time.sleep(0.3)
            
            if all_records:
                total_records += len(all_records)
                logger.info(f"账期 {billing_cycle} 共获取 {len(all_records)} 条记录")
                
                if self.use_database:
                    # 数据库模式：保存到数据库
                    if not account_id:
                        account_id = account_name or self.access_key_id[:10]
                    
                    inserted, skipped = self._storage.insert_bill_items(
                        account_id=account_id,
                        billing_cycle=billing_cycle,
                        items=all_records
                    )
                    result[billing_cycle] = {'inserted': inserted, 'skipped': skipped}
                    
                else:
                    # CSV模式：保存到CSV
                    csv_filename = f"{account_name or 'bill'}-{billing_cycle}-detail.csv"
                    csv_path = output_dir / csv_filename
                    self.save_to_csv(all_records, csv_path, billing_cycle)
                    result[billing_cycle] = csv_path
            else:
                logger.warning(f"账期 {billing_cycle} 没有数据")
            
            # 移动到下个月
            current_date += relativedelta(months=1)
            
            # API限流
            time.sleep(1)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"批量获取完成！")
        logger.info(f"总账期数: {len(result)}")
        logger.info(f"总记录数: {total_records:,}")
        if self.use_database:
            logger.info(f"数据库路径: {self._storage.db_path}")
        else:
            logger.info(f"文件保存在: {output_dir}")
        logger.info(f"{'='*60}")
        
        return result
    
    def fetch_historical_bills(
        self,
        account_id: str,
        end_month: Optional[str] = None,
        earliest_year: int = 2020
    ) -> Tuple[int, int]:
        """
        获取历史所有账单（尽可能多，数据库模式）
        
        Args:
            account_id: 账号ID
            end_month: 结束月份，默认当前月
            earliest_year: 最早年份，默认2020
            
        Returns:
            (总插入数, 总跳过数)
        """
        if not self.use_database:
            raise ValueError("此功能仅在数据库模式下可用")
        
        if not end_month:
            end_month = datetime.now().strftime("%Y-%m")
        
        # 从最早年份开始尝试
        start_month = f"{earliest_year}-01"
        
        logger.info(f"开始获取历史账单：{start_month} 至 {end_month}")
        logger.info(f"这可能需要较长时间，请耐心等待...")
        
        total_inserted = 0
        total_skipped = 0
        
        result = self.fetch_and_save_bills(
            start_month=start_month,
            end_month=end_month,
            account_id=account_id
        )
        
        for cycle, stats in result.items():
            if isinstance(stats, dict):
                total_inserted += stats.get('inserted', 0)
                total_skipped += stats.get('skipped', 0)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"历史账单获取完成！")
        logger.info(f"总插入: {total_inserted:,} 条")
        logger.info(f"总跳过: {total_skipped:,} 条（已存在）")
        logger.info(f"{'='*60}")
        
        return total_inserted, total_skipped


def main():
    """测试用例"""
    import os
    
    # 从环境变量获取密钥（生产环境应该从config.json或Keyring获取）
    access_key_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    
    if not access_key_id or not access_key_secret:
        print("❌ 请设置环境变量：")
        print("   export ALIBABA_CLOUD_ACCESS_KEY_ID='your_key_id'")
        print("   export ALIBABA_CLOUD_ACCESS_KEY_SECRET='your_key_secret'")
        return
    
    # 创建获取器
    fetcher = BillFetcher(access_key_id, access_key_secret)
    
    # 获取最近3个月的账单
    end_month = datetime.now().strftime("%Y-%m")
    start_month = (datetime.now() - timedelta(days=90)).strftime("%Y-%m")
    
    output_dir = Path("./bills_data")
    
    fetcher.fetch_and_save_bills(
        start_month=start_month,
        end_month=end_month,
        output_dir=output_dir,
        account_name="auto_fetched"
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()







