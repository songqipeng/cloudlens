#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
折扣分析模块
"""

import json
import time
import re
import os
import sys
import subprocess
from datetime import datetime
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from utils.concurrent_helper import process_concurrently


class DiscountAnalyzer:
    """折扣分析器"""
    
    def __init__(self, tenant_name, access_key_id, access_key_secret):
        """初始化"""
        self.tenant_name = tenant_name
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.region = 'cn-beijing'  # 可以根据需要扩展多区域
        self.client = AcsClient(access_key_id, access_key_secret, self.region)
    
    def get_all_ecs_instances(self):
        """获取所有ECS实例"""
        all_instances = []
        page_number = 1
        page_size = 100
        
        print(f"📊 获取{self.tenant_name}的ECS实例列表...")
        
        while True:
            try:
                request = CommonRequest()
                request.set_domain(f'ecs.{self.region}.aliyuncs.com')
                request.set_method('POST')
                request.set_version('2014-05-26')
                request.set_action_name('DescribeInstances')
                request.add_query_param('PageSize', page_size)
                request.add_query_param('PageNumber', page_number)
                
                response = self.client.do_action_with_exception(request)
                data = json.loads(response)
                
                if 'Instances' in data and 'Instance' in data['Instances']:
                    instances = data['Instances']['Instance']
                    if not isinstance(instances, list):
                        instances = [instances]
                    
                    if len(instances) == 0:
                        break
                    
                    all_instances.extend(instances)
                    print(f"  第{page_number}页: {len(instances)} 个实例")
                    page_number += 1
                    
                    if len(instances) < page_size:
                        break
                else:
                    break
                    
            except Exception as e:
                print(f'❌ 获取第{page_number}页失败: {e}')
                break
        
        print(f"✅ 总共获取到 {len(all_instances)} 个实例")
        return all_instances
    
    def get_all_rds_instances(self):
        """获取所有RDS实例"""
        from aliyunsdkrds.request.v20140815 import DescribeDBInstancesRequest
        
        all_instances = []
        regions = ['cn-beijing', 'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 
                   'cn-qingdao', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-chengdu',
                   'cn-hongkong', 'ap-southeast-1', 'us-east-1', 'eu-west-1']
        
        print(f"📊 获取{self.tenant_name}的RDS实例列表...")
        
        for region in regions:
            try:
                client = AcsClient(self.access_key_id, self.access_key_secret, region)
                request = DescribeDBInstancesRequest.DescribeDBInstancesRequest()
                request.set_PageSize(100)
                request.set_PageNumber(1)
                
                page_number = 1
                while True:
                    request.set_PageNumber(page_number)
                    response = client.do_action_with_exception(request)
                    data = json.loads(response)
                    
                    if 'Items' in data and 'DBInstance' in data['Items']:
                        instances = data['Items']['DBInstance']
                        if not isinstance(instances, list):
                            instances = [instances]
                        
                        if len(instances) == 0:
                            break
                        
                        for inst in instances:
                            all_instances.append({
                                'DBInstanceId': inst.get('DBInstanceId', ''),
                                'DBInstanceDescription': inst.get('DBInstanceDescription', ''),
                                'DBInstanceType': inst.get('DBInstanceType', ''),
                                'PayType': inst.get('PayType', ''),
                                'Engine': inst.get('Engine', ''),
                                'EngineVersion': inst.get('EngineVersion', ''),
                                'DBInstanceClass': inst.get('DBInstanceClass', ''),
                                'ZoneId': inst.get('ZoneId', ''),
                                'RegionId': region
                            })
                        
                        total_count = data.get('TotalRecordCount', 0)
                        if len(all_instances) >= total_count or len(instances) < 100:
                            break
                        
                        page_number += 1
                    else:
                        break
                        
            except Exception as e:
                # 某个区域失败，继续下一个
                continue
        
        print(f"✅ 总共获取到 {len(all_instances)} 个RDS实例")
        return all_instances
    
    def get_all_redis_instances(self):
        """获取所有Redis实例"""
        from aliyunsdkr_kvstore.request.v20150101 import DescribeInstancesRequest
        
        all_instances = []
        regions = ['cn-beijing', 'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 
                   'cn-qingdao', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-chengdu',
                   'cn-hongkong', 'ap-southeast-1', 'us-east-1', 'eu-west-1']
        
        print(f"📊 获取{self.tenant_name}的Redis实例列表...")
        
        for region in regions:
            try:
                client = AcsClient(self.access_key_id, self.access_key_secret, region)
                request = DescribeInstancesRequest.DescribeInstancesRequest()
                request.set_PageSize(100)
                request.set_PageNumber(1)
                
                page_number = 1
                while True:
                    request.set_PageNumber(page_number)
                    response = client.do_action_with_exception(request)
                    data = json.loads(response)
                    
                    if 'Instances' in data and 'KVStoreInstance' in data['Instances']:
                        instances = data['Instances']['KVStoreInstance']
                        if not isinstance(instances, list):
                            instances = [instances]
                        
                        if len(instances) == 0:
                            break
                        
                        for inst in instances:
                            # 获取节点信息（重要：用于正确计算价格）
                            # Redis/Tair实例价格与节点数量相关
                            all_instances.append({
                                'InstanceId': inst.get('InstanceId', ''),
                                'InstanceName': inst.get('InstanceName', ''),
                                'InstanceClass': inst.get('InstanceClass', ''),
                                'InstanceType': inst.get('InstanceType', ''),
                                'ChargeType': inst.get('ChargeType', ''),
                                'Capacity': inst.get('Capacity', 0),  # 容量
                                'Bandwidth': inst.get('Bandwidth', 0),  # 带宽
                                'RegionId': region,
                                # 节点相关字段（可能在不同字段名中）
                                'NodeType': inst.get('NodeType', 0) or inst.get('NodeNum', 0) or 0,  # 节点类型/数量
                                'ReplicaQuantity': inst.get('ReplicaQuantity', 0) or 0,  # 副本数
                            })
                        
                        total_count = data.get('TotalCount', 0)
                        if len(all_instances) >= total_count or len(instances) < 100:
                            break
                        
                        page_number += 1
                    else:
                        break
                        
            except Exception as e:
                # 某个区域失败，继续下一个
                continue
        
        print(f"✅ 总共获取到 {len(all_instances)} 个Redis实例")
        return all_instances
    
    def get_all_mongodb_instances(self):
        """获取所有MongoDB实例"""
        from aliyunsdkdds.request.v20151201 import DescribeDBInstancesRequest
        
        all_instances = []
        regions = ['cn-beijing', 'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 
                   'cn-qingdao', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-chengdu',
                   'cn-hongkong', 'ap-southeast-1', 'us-east-1', 'eu-west-1']
        
        print(f"📊 获取{self.tenant_name}的MongoDB实例列表...")
        
        for region in regions:
            try:
                client = AcsClient(self.access_key_id, self.access_key_secret, region)
                request = DescribeDBInstancesRequest.DescribeDBInstancesRequest()
                request.set_PageSize(100)
                request.set_PageNumber(1)
                
                page_number = 1
                while True:
                    request.set_PageNumber(page_number)
                    response = client.do_action_with_exception(request)
                    data = json.loads(response)
                    
                    if 'DBInstances' in data and 'DBInstance' in data['DBInstances']:
                        instances = data['DBInstances']['DBInstance']
                        if not isinstance(instances, list):
                            instances = [instances]
                        
                        if len(instances) == 0:
                            break
                        
                        for inst in instances:
                            all_instances.append({
                                'DBInstanceId': inst.get('DBInstanceId', ''),
                                'DBInstanceDescription': inst.get('DBInstanceDescription', ''),
                                'DBInstanceType': inst.get('DBInstanceType', ''),
                                'ChargeType': inst.get('ChargeType', ''),
                                'Engine': inst.get('Engine', ''),
                                'EngineVersion': inst.get('EngineVersion', ''),
                                'DBInstanceClass': inst.get('DBInstanceClass', ''),
                                'ZoneId': inst.get('ZoneId', ''),
                                'RegionId': region
                            })
                        
                        total_count = data.get('TotalRecordCount', 0)
                        if len(all_instances) >= total_count or len(instances) < 100:
                            break
                        
                        page_number += 1
                    else:
                        break
                        
            except Exception as e:
                # 某个区域失败，继续下一个
                continue
        
        print(f"✅ 总共获取到 {len(all_instances)} 个MongoDB实例")
        return all_instances
    
    def get_renewal_prices(self, instances, resource_type='ecs'):
        """获取续费价格（并发处理）"""
        total = len(instances)
        
        print(f"\n🔍 获取{resource_type.upper()}实例的续费价格...")
        
        if total == 0:
            return []
        
        # 定义单个实例处理函数（用于并发）
        def process_single_instance(instance_item):
            """处理单个实例的价格查询（用于并发）"""
            instance = instance_item
            try:
                if resource_type == 'ecs':
                    instance_id = instance.get('InstanceId', '')
                    instance_name = instance.get('InstanceName', '')
                    zone = instance.get('ZoneId', '')
                    instance_type = instance.get('InstanceType', '')
                    charge_type = instance.get('InstanceChargeType', '')
                    region = self.region
                elif resource_type == 'rds':
                    instance_id = instance.get('DBInstanceId', '')
                    instance_name = instance.get('DBInstanceDescription', '') or instance_id
                    zone = instance.get('ZoneId', '')
                    instance_type = f"{instance.get('Engine', '')} {instance.get('DBInstanceClass', '')}"
                    charge_type = instance.get('PayType', '')
                    region = instance.get('RegionId', self.region)
                elif resource_type == 'redis':
                    instance_id = instance.get('InstanceId', '')
                    instance_name = instance.get('InstanceName', '') or instance_id
                    zone = ''
                    instance_type = instance.get('InstanceClass', '')
                    charge_type = instance.get('ChargeType', '')
                    capacity = instance.get('Capacity', 0)
                    region = instance.get('RegionId', self.region)
                    # 获取节点信息（用于价格计算）
                    # 注意：API返回的可能是字符串（如"double"表示双节点）或整数
                    node_type_raw = instance.get('NodeType', 0) or instance.get('NodeNum', 0) or 0
                    replica_quantity_raw = instance.get('ReplicaQuantity', 0) or 0
                    
                    # 转换为整数，如果不是数字则处理特殊值
                    try:
                        if isinstance(node_type_raw, str):
                            # 处理字符串类型：如"double"表示2个节点，"single"表示1个节点
                            if node_type_raw.lower() == 'double' or node_type_raw == '2':
                                total_nodes = 2
                            elif node_type_raw.lower() == 'single' or node_type_raw == '1':
                                total_nodes = 1
                            else:
                                total_nodes = int(node_type_raw) if node_type_raw.isdigit() else 1
                        else:
                            node_type = int(node_type_raw) if node_type_raw else 0
                            total_nodes = node_type if node_type > 0 else 1
                    except (ValueError, AttributeError):
                        total_nodes = 1  # 默认单节点
                    
                    # 如果没有从NodeType获取到，尝试从ReplicaQuantity获取
                    if total_nodes == 1:
                        try:
                            replica_quantity = int(replica_quantity_raw) if replica_quantity_raw else 0
                            if replica_quantity > 0:
                                # 有副本数通常是主备架构，即2个节点（1主+1备）
                                total_nodes = 2
                        except (ValueError, AttributeError):
                            pass
                    
                    # 如果都没获取到，根据InstanceClass推断：redis.shard.small.2.ce中的".2."可能表示2个节点
                    if total_nodes == 1 and instance_type:
                        if '.2.' in instance_type or '_2_' in instance_type:
                            total_nodes = 2
                elif resource_type == 'mongodb':
                    instance_id = instance.get('DBInstanceId', '')
                    instance_name = instance.get('DBInstanceDescription', '') or instance_id
                    zone = instance.get('ZoneId', '')
                    instance_type = f"{instance.get('Engine', '')} {instance.get('DBInstanceClass', '')}"
                    charge_type = instance.get('ChargeType', '')
                    region = instance.get('RegionId', self.region)
                else:
                    instance_id = instance.get('InstanceId', '')
                    instance_name = instance.get('InstanceName', '')
                    zone = instance.get('ZoneId', '')
                    instance_type = instance.get('InstanceType', '')
                    charge_type = instance.get('InstanceChargeType', '')
                    region = self.region
                
                # 只处理包年包月实例
                if resource_type == 'rds':
                    if charge_type != 'Prepaid':
                        return {'skip': True, 'reason': '按量付费'}
                elif resource_type in ['redis', 'mongodb']:
                    if charge_type != 'PrePaid':
                        return {'skip': True, 'reason': '按量付费'}
                else:
                    if charge_type != 'PrePaid':
                        return {'skip': True, 'reason': '按量付费'}
                
                request = CommonRequest()
                client = AcsClient(self.access_key_id, self.access_key_secret, region)
                
                if resource_type == 'rds':
                    request.set_domain('rds.aliyuncs.com')
                    request.set_version('2014-08-15')
                    request.set_action_name('DescribeRenewalPrice')
                    request.add_query_param('RegionId', region)
                    request.add_query_param('DBInstanceId', instance_id)
                    request.add_query_param('Period', 1)
                    request.add_query_param('TimeType', 'Month')
                    request.add_query_param('UsedTime', 1)
                    request.set_method('POST')
                    response = client.do_action_with_exception(request)
                    data = json.loads(response)
                    
                elif resource_type == 'redis':
                    # Redis价格查询：尝试RENEW（续费）方式，失败则使用BUY（购买）方式
                    # 注意：BUY方式返回的可能是新购买价格，而不是续费价格
                    request.set_domain('r-kvstore.aliyuncs.com')
                    request.set_version('2015-01-01')
                    request.set_action_name('DescribePrice')
                    request.add_query_param('RegionId', region)
                    request.add_query_param('InstanceId', instance_id)
                    request.add_query_param('Period', 1)  # 1个月
                    request.add_query_param('Quantity', 1)
                    request.add_query_param('OrderType', 'RENEW')  # 优先使用续费方式
                    if capacity and capacity > 0:
                        request.add_query_param('Capacity', capacity)
                    request.set_method('POST')
                    
                    use_buy_price = False  # 标记是否使用了BUY方式
                    try:
                        response = client.do_action_with_exception(request)
                        data = json.loads(response)
                    except Exception as renew_error:
                        if 'CAN_NOT_FIND_SUBSCRIPTION' in str(renew_error) or '找不到订购信息' in str(renew_error):
                            # RENEW失败，改用BUY方式（某些实例可能需要使用BUY方式）
                            use_buy_price = True
                            request = CommonRequest()
                            request.set_domain('r-kvstore.aliyuncs.com')
                            request.set_version('2015-01-01')
                            request.set_action_name('DescribePrice')
                            request.set_method('POST')
                            request.add_query_param('RegionId', region)
                            request.add_query_param('InstanceId', instance_id)
                            request.add_query_param('OrderType', 'BUY')
                            request.add_query_param('Period', 1)
                            request.add_query_param('Quantity', 1)
                            if instance_type:
                                request.add_query_param('InstanceClass', instance_type)
                            response = client.do_action_with_exception(request)
                            data = json.loads(response)
                        else:
                            raise renew_error
                            
                elif resource_type == 'mongodb':
                    request.set_domain('dds.aliyuncs.com')
                    request.set_version('2015-12-01')
                    request.set_action_name('DescribeRenewalPrice')
                    request.add_query_param('RegionId', region)
                    request.add_query_param('DBInstanceId', instance_id)
                    request.add_query_param('Period', 1)
                    request.add_query_param('TimeType', 'Month')
                    request.add_query_param('UsedTime', 1)
                    request.set_method('POST')
                    response = client.do_action_with_exception(request)
                    data = json.loads(response)
                    
                else:
                    # ECS
                    request.set_domain(f'ecs.{region}.aliyuncs.com')
                    request.set_version('2014-05-26')
                    request.set_action_name('DescribeRenewalPrice')
                    request.add_query_param('ResourceId', instance_id)
                    request.add_query_param('Period', 1)
                    request.add_query_param('PriceUnit', 'Month')
                    request.set_method('POST')
                    response = client.do_action_with_exception(request)
                    data = json.loads(response)
                
                # 解析价格信息
                price_info = None
                if resource_type == 'rds':
                    if 'PriceInfo' in data:
                        if isinstance(data['PriceInfo'], dict) and 'Price' in data['PriceInfo']:
                            price_info = data['PriceInfo']['Price']
                        elif isinstance(data['PriceInfo'], dict):
                            price_info = data['PriceInfo']
                    if not price_info:
                        price_info = data.get('Price', {})
                elif resource_type == 'redis':
                    # Redis价格解析：优先从SubOrders中提取（更准确）
                    # 注意：BUY方式返回的价格可能与续费价格不同，需要特别处理
                    price_info = {}
                    
                    # 首先尝试从SubOrders中提取（推荐方式，因为包含详细的子订单信息）
                    if 'SubOrders' in data and 'SubOrder' in data['SubOrders']:
                        sub_orders = data['SubOrders']['SubOrder']
                        if not isinstance(sub_orders, list):
                            sub_orders = [sub_orders]
                        
                        total_trade = 0
                        total_original = 0
                        for sub_order in sub_orders:
                            # 从每个子订单中提取价格
                            # 注意：SubOrder中的字段名可能不同，尝试多个可能的名字
                            sub_trade = float(
                                sub_order.get('TradeAmount', 0) or 
                                sub_order.get('TradePrice', 0) or 
                                sub_order.get('Amount', 0) or 0
                            )
                            sub_original = float(
                                sub_order.get('OriginalAmount', 0) or 
                                sub_order.get('OriginalPrice', 0) or 
                                sub_order.get('ListPrice', 0) or 
                                sub_order.get('StandPrice', 0) or 0
                            )
                            
                            # Redis特殊处理：检查DepreciateInfo.ListPrice（可能包含基准价/官网目录价格）
                            # 根据阿里云文档，ListPrice可能包含官方定价
                            if 'DepreciateInfo' in sub_order and sub_original < 50:
                                depreciate_info = sub_order['DepreciateInfo']
                                list_price = float(depreciate_info.get('ListPrice', 0) or 0)
                                month_price = float(depreciate_info.get('MonthPrice', 0) or 0)
                                # 如果ListPrice大于当前原价，使用ListPrice作为基准价
                                if list_price > sub_original and list_price > 50:
                                    sub_original = list_price
                                # 或者使用MonthPrice
                                elif month_price > sub_original and month_price > 50:
                                    sub_original = month_price
                            
                            # Redis特殊处理：如果价格异常小（< 1），尝试从ModuleInstance中累加
                            # 因为某些情况下Order/SubOrder中的价格可能不准确
                            if sub_trade < 1 or sub_original < 1:
                                # 尝试从ModuleInstance中累加PricingModule的价格
                                if 'ModuleInstance' in sub_order and 'ModuleInstance' in sub_order['ModuleInstance']:
                                    modules = sub_order['ModuleInstance']['ModuleInstance']
                                    if not isinstance(modules, list):
                                        modules = [modules]
                                    
                                    module_trade = 0
                                    module_original = 0
                                    for module in modules:
                                        # 只累加计价模块（PricingModule=true）的价格
                                        if module.get('PricingModule', False):
                                            # 优先使用TotalProductFee作为原价，PayFee作为实付价
                                            # 如果TotalProductFee不存在，使用StandPrice
                                            module_pay = float(module.get('PayFee', 0) or 0)
                                            module_original_price = float(
                                                module.get('TotalProductFee', 0) or 
                                                module.get('StandPrice', 0) or 0
                                            )
                                            module_trade += module_pay
                                            module_original += module_original_price
                                    
                                    # 如果从ModuleInstance获取到价格，优先使用
                                    # 但需要检查：如果价格异常小（可能是部分组件），需要查找其他字段
                                    if module_trade > 0 and module_original > 0:
                                        # 如果累加的价格仍然很小（< 20），可能API返回不完整
                                        # 这种情况下，尝试从SubOrder的其他字段获取
                                        if module_trade < 20 or module_original < 20:
                                            # 检查SubOrder中的StandPrice或其他可能包含完整价格的字段
                                            sub_stand_price = float(sub_order.get('StandPrice', 0) or 0)
                                            if sub_stand_price > module_trade * 2:
                                                # StandPrice看起来更像完整价格
                                                sub_trade = sub_stand_price  # 暂时使用，待验证是否有折扣字段
                                                sub_original = sub_stand_price
                                            else:
                                                # 使用ModuleInstance累加的价格
                                                sub_trade = module_trade
                                                sub_original = module_original
                                        else:
                                            sub_trade = module_trade
                                            sub_original = module_original
                                    elif module_trade > 0:
                                        sub_trade = module_trade
                                    elif module_original > 0:
                                        sub_original = module_original
                            
                            total_trade += sub_trade
                            total_original += sub_original
                        
                        # 如果从SubOrders获取到了价格，优先使用
                        if total_trade > 0 and total_original > 0:
                            price_info['TradePrice'] = total_trade
                            price_info['OriginalPrice'] = total_original
                        # 如果只有OriginalPrice，也记录下来
                        elif total_original > 0:
                            price_info['OriginalPrice'] = total_original
                    
                    # 如果SubOrders没有完整的价格信息，从Order中提取
                    if (not price_info or price_info.get('TradePrice', 0) == 0 or price_info.get('OriginalPrice', 0) == 0) and 'Order' in data:
                        order = data['Order']
                        # 根据阿里云API文档：
                        # OriginalAmount: 原价（官网目录价格）
                        # TradeAmount: 实付价格（折扣后价格）
                        # StandPrice: 标准价格（可能是官网目录价格）
                        # 注意：由于"官网价格直降"活动，OriginalAmount可能已经是折扣后的价格
                        order_original = float(
                            order.get('StandPrice', 0) or  # 优先使用StandPrice（标准价）
                            order.get('OriginalAmount', 0) or 
                            order.get('OriginalPrice', 0) or 0
                        )
                        order_trade = float(order.get('TradeAmount', 0) or order.get('TradePrice', 0) or 0)
                        
                        # 如果StandPrice存在且大于其他价格，使用StandPrice作为基准价
                        stand_price = float(order.get('StandPrice', 0) or 0)
                        if stand_price > order_original and stand_price > 50:
                            order_original = stand_price
                        
                        # 如果Order中有数据
                        if order_original > 0 or order_trade > 0:
                            # 如果SubOrders没有数据，使用Order
                            if not price_info:
                                price_info['OriginalPrice'] = order_original
                                price_info['TradePrice'] = order_trade
                            # 补充缺失的字段
                            elif price_info.get('OriginalPrice', 0) == 0 and order_original > 0:
                                price_info['OriginalPrice'] = order_original
                            elif price_info.get('TradePrice', 0) == 0 and order_trade > 0:
                                price_info['TradePrice'] = order_trade
                    
                    # 如果还是没有，尝试其他字段
                    if not price_info or price_info.get('TradePrice', 0) == 0:
                        fallback_price = data.get('Price', {}) or data.get('PriceInfo', {})
                        if isinstance(fallback_price, dict) and (fallback_price.get('TradePrice') or fallback_price.get('OriginalPrice')):
                            if not price_info:
                                price_info = {}
                            if not price_info.get('TradePrice'):
                                price_info['TradePrice'] = float(fallback_price.get('TradePrice', 0) or 0)
                            if not price_info.get('OriginalPrice'):
                                price_info['OriginalPrice'] = float(fallback_price.get('OriginalPrice', 0) or 0)
                elif resource_type == 'mongodb':
                    if 'PriceInfo' in data:
                        if isinstance(data['PriceInfo'], dict) and 'Price' in data['PriceInfo']:
                            price_info = data['PriceInfo']['Price']
                        elif isinstance(data['PriceInfo'], dict):
                            price_info = data['PriceInfo']
                    if not price_info:
                        price_info = data.get('Price', {})
                else:
                    # ECS格式
                    if 'PriceInfo' in data and 'Price' in data['PriceInfo']:
                        price_info = data['PriceInfo']['Price']
                
                if price_info:
                    original_price = float(price_info.get('OriginalPrice', 0) or 0)
                    trade_price = float(price_info.get('TradePrice', 0) or 0)
                    
                    # Redis特殊处理：如果价格异常（折扣率小于0.15或大于1），可能是字段理解错误
                    # 根据用户反馈：实例r-2zechtvlc0dsrjn02o应该是5折，但算出了1折
                    # 关键发现：该实例有2个节点，API返回的可能是单节点价格
                    if resource_type == 'redis' and original_price > 0 and trade_price > 0:
                        # 检查是否需要根据节点数量调整价格
                        # 如果总节点数 > 1 且当前价格看起来是单节点价格（< 30），可能需要乘以节点数
                        if total_nodes > 1 and (original_price < 50 or trade_price < 50):
                            # 判断：如果价格明显偏低（单节点价格），尝试乘以节点数
                            # 16.1 * 2 = 32.2（还不完全对，但更接近）
                            # 或者76.98 / 16.1 ≈ 4.78，这个比例关系需要进一步研究
                            adjusted_original = original_price * total_nodes
                            adjusted_trade = trade_price * total_nodes
                            
                            # 如果调整后的价格更合理（在30-200范围内），使用调整后的价格
                            if 30 <= adjusted_original <= 200 and 20 <= adjusted_trade <= 150:
                                original_price = adjusted_original
                                trade_price = adjusted_trade
                        
                        temp_discount = trade_price / original_price if original_price > 0 else 0
                        
                        # 如果折扣率异常小于0.15（通常5折以上的折扣应该在0.15以上）
                        # 可能是字段含义错误，尝试交换验证
                        if temp_discount < 0.15:
                            # 尝试交换字段看看是否合理
                            swapped_discount = original_price / trade_price if trade_price > 0 else 0
                            # 如果交换后的折扣率在合理范围内（0.2-1.0），说明字段搞反了
                            if 0.2 <= swapped_discount <= 1.0:
                                # 字段搞反了，交换（修复1折变5折的问题）
                                original_price, trade_price = trade_price, original_price
                        # 如果折扣率大于1.1，说明字段肯定搞反了
                        elif temp_discount > 1.1:
                            # 直接交换
                            original_price, trade_price = trade_price, original_price
                    
                    if original_price > 0:
                        discount_rate = trade_price / original_price
                        
                        # 最终验证：折扣率应该在合理范围内（0.1到1.0之间）
                        if discount_rate < 0.01 or discount_rate > 1.0:
                            return {
                                'success': False, 
                                'error': f'价格异常: 原价={original_price}, 实付={trade_price}, 折扣={discount_rate:.2f}', 
                                'instance_name': instance_name
                            }
                        
                        return {
                            'success': True,
                            'name': instance_name,
                            'id': instance_id,
                            'zone': zone,
                            'type': instance_type,
                            'original_price': original_price,
                            'trade_price': trade_price,
                            'discount_rate': discount_rate
                        }
                    else:
                        return {'success': False, 'error': '无法获取价格信息', 'instance_name': instance_name}
                else:
                    return {'success': False, 'error': f'价格信息格式错误 (响应键: {list(data.keys())})', 'instance_name': instance_name}
                    
            except Exception as e:
                instance_name = instance.get('InstanceName', '') or instance.get('DBInstanceDescription', '') or instance.get('InstanceId', 'unknown')
                return {'success': False, 'error': str(e), 'instance_name': instance_name}
        
        # 并发处理
        print(f"🚀 并发查询价格（最多10个并发线程）...")
        
        def progress_callback(completed, total):
            progress_pct = completed / total * 100
            sys.stdout.write(f'\r📊 价格查询进度: {completed}/{total} ({progress_pct:.1f}%)')
            sys.stdout.flush()
        
        results_raw = process_concurrently(
            instances,
            process_single_instance,
            max_workers=10,
            description="价格查询",
            progress_callback=progress_callback
        )
        
        print()  # 换行
        
        # 整理结果
        results = []
        skip_count = 0
        success_count = 0
        fail_count = 0
        
        for result in results_raw:
            if result:
                if result.get('skip'):
                    skip_count += 1
                elif result.get('success'):
                    results.append({
                        'name': result['name'],
                        'id': result['id'],
                        'zone': result['zone'],
                        'type': result['type'],
                        'original_price': result['original_price'],
                        'trade_price': result['trade_price'],
                        'discount_rate': result['discount_rate']
                    })
                    success_count += 1
                    discount_text = f"{result['discount_rate']*100:.1f}% ({result['discount_rate']:.1f}折)"
                    print(f"  ✅ {result['name']}: {discount_text}")
                else:
                    fail_count += 1
                    instance_name = result.get('instance_name', 'unknown')
                    error = result.get('error', 'unknown error')
                    print(f"  ❌ {instance_name}: {error}")
        
        print(f"\n✅ 价格查询完成: 成功 {success_count} 个, 跳过 {skip_count} 个, 失败 {fail_count} 个")
        
        return results
    
    def get_renewal_prices_old(self, instances, resource_type='ecs'):
        """获取续费价格（旧版本，保留作为参考）"""
        results = []
        total = len(instances)
        
        print(f"\n🔍 获取{resource_type.upper()}实例的续费价格...")
        
        for i, instance in enumerate(instances, 1):
            if resource_type == 'ecs':
                instance_id = instance.get('InstanceId', '')
                instance_name = instance.get('InstanceName', '')
                zone = instance.get('ZoneId', '')
                instance_type = instance.get('InstanceType', '')
                charge_type = instance.get('InstanceChargeType', '')
                region = self.region
            elif resource_type == 'rds':
                instance_id = instance.get('DBInstanceId', '')
                instance_name = instance.get('DBInstanceDescription', '') or instance_id
                zone = instance.get('ZoneId', '')
                instance_type = f"{instance.get('Engine', '')} {instance.get('DBInstanceClass', '')}"
                charge_type = instance.get('PayType', '')
                region = instance.get('RegionId', self.region)
            elif resource_type == 'redis':
                instance_id = instance.get('InstanceId', '')
                instance_name = instance.get('InstanceName', '') or instance_id
                zone = ''  # Redis可能没有ZoneId
                instance_type = instance.get('InstanceClass', '')
                charge_type = instance.get('ChargeType', '')
                capacity = instance.get('Capacity', 0)
                region = instance.get('RegionId', self.region)
            elif resource_type == 'mongodb':
                instance_id = instance.get('DBInstanceId', '')
                instance_name = instance.get('DBInstanceDescription', '') or instance_id
                zone = instance.get('ZoneId', '')
                instance_type = f"{instance.get('Engine', '')} {instance.get('DBInstanceClass', '')}"
                charge_type = instance.get('ChargeType', '')
                region = instance.get('RegionId', self.region)
            else:
                # 其他资源类型可以在这里扩展
                instance_id = instance.get('InstanceId', '')
                instance_name = instance.get('InstanceName', '')
                zone = instance.get('ZoneId', '')
                instance_type = instance.get('InstanceType', '')
                charge_type = instance.get('InstanceChargeType', '')
                region = self.region
            
            print(f"[{i}/{total}] {instance_name} ({charge_type})", end=' ')
            
            # 只处理包年包月实例
            # RDS的PayType: Prepaid表示包年包月，Postpaid表示按量付费
            # ECS的InstanceChargeType: PrePaid表示包年包月
            # Redis/MongoDB的ChargeType: PrePaid表示包年包月
            if resource_type == 'rds':
                if charge_type != 'Prepaid':
                    print("⏭️  跳过（按量付费）")
                    continue
            elif resource_type in ['redis', 'mongodb']:
                if charge_type != 'PrePaid':
                    print("⏭️  跳过（按量付费）")
                    continue
            else:
                if charge_type != 'PrePaid':
                    print("⏭️  跳过（按量付费）")
                    continue
            
            try:
                request = CommonRequest()
                
                # 创建client（所有资源类型都需要）
                client = AcsClient(self.access_key_id, self.access_key_secret, region)
                
                if resource_type == 'rds':
                    # RDS使用通用域名
                    request.set_domain('rds.aliyuncs.com')
                    request.set_version('2014-08-15')
                    request.set_action_name('DescribeRenewalPrice')
                    request.add_query_param('RegionId', region)
                    request.add_query_param('DBInstanceId', instance_id)
                    request.add_query_param('Period', 1)
                    request.add_query_param('TimeType', 'Month')  # 时间单位：Month或Year
                    request.add_query_param('UsedTime', 1)  # 已使用月数
                    
                    request.set_method('POST')
                    response = client.do_action_with_exception(request)
                    data = json.loads(response)
                    
                elif resource_type == 'redis':
                    # Redis使用KVStore API查询续费价格
                    # 尝试两种方式：1) RENEW续费 2) BUY购买（如果续费失败）
                    request.set_domain('r-kvstore.aliyuncs.com')
                    request.set_version('2015-01-01')
                    request.set_action_name('DescribePrice')
                    request.add_query_param('RegionId', region)
                    request.add_query_param('InstanceId', instance_id)
                    request.add_query_param('Period', 1)  # 周期（月）
                    request.add_query_param('Quantity', 1)  # 数量
                    
                    # 首先尝试RENEW续费
                    request.add_query_param('OrderType', 'RENEW')
                    if capacity and capacity > 0:
                        request.add_query_param('Capacity', capacity)
                    
                    request.set_method('POST')
                    
                    try:
                        response = client.do_action_with_exception(request)
                        data = json.loads(response)
                    except Exception as renew_error:
                        # 如果RENEW失败，尝试使用BUY查询相同规格的价格
                        if 'CAN_NOT_FIND_SUBSCRIPTION' in str(renew_error) or '找不到订购信息' in str(renew_error):
                            # 创建新的request，使用BUY订单类型
                            request = CommonRequest()
                            request.set_domain('r-kvstore.aliyuncs.com')
                            request.set_version('2015-01-01')
                            request.set_action_name('DescribePrice')
                            request.set_method('POST')
                            request.add_query_param('RegionId', region)
                            request.add_query_param('InstanceId', instance_id)
                            request.add_query_param('OrderType', 'BUY')  # 购买订单
                            request.add_query_param('Period', 1)
                            request.add_query_param('Quantity', 1)
                            # BUY方式需要InstanceClass参数
                            if instance_type:
                                request.add_query_param('InstanceClass', instance_type)
                            response = client.do_action_with_exception(request)
                            data = json.loads(response)
                        else:
                            raise renew_error
                            
                elif resource_type == 'mongodb':
                    # MongoDB使用DDS API（使用通用域名）
                    request.set_domain('dds.aliyuncs.com')
                    request.set_version('2015-12-01')
                    request.set_action_name('DescribeRenewalPrice')
                    request.add_query_param('RegionId', region)
                    request.add_query_param('DBInstanceId', instance_id)
                    request.add_query_param('Period', 1)
                    request.add_query_param('TimeType', 'Month')
                    request.add_query_param('UsedTime', 1)
                    
                    request.set_method('POST')
                    response = client.do_action_with_exception(request)
                    data = json.loads(response)
                    
                else:
                    # ECS
                    request.set_domain(f'ecs.{region}.aliyuncs.com')
                    request.set_version('2014-05-26')
                    request.set_action_name('DescribeRenewalPrice')
                    request.add_query_param('ResourceId', instance_id)
                    request.add_query_param('Period', 1)
                    request.add_query_param('PriceUnit', 'Month')
                    
                    request.set_method('POST')
                    response = client.do_action_with_exception(request)
                    data = json.loads(response)
                
                # 不同资源类型的响应格式可能不同
                price_info = None
                if resource_type == 'rds':
                    # RDS响应格式
                    if 'PriceInfo' in data:
                        if isinstance(data['PriceInfo'], dict) and 'Price' in data['PriceInfo']:
                            price_info = data['PriceInfo']['Price']
                        elif isinstance(data['PriceInfo'], dict):
                            price_info = data['PriceInfo']
                    if not price_info:
                        price_info = data.get('Price', {})
                elif resource_type == 'redis':
                    # Redis响应格式（DescribePrice返回的结构不同）
                    # 响应包含: Order, SubOrders, Rules等
                    if 'Order' in data:
                        order = data['Order']
                        price_info = {}
                        # Order中可能包含OriginalPrice和TradePrice
                        price_info['OriginalPrice'] = order.get('OriginalAmount', 0) or order.get('OriginalPrice', 0) or 0
                        price_info['TradePrice'] = order.get('TradeAmount', 0) or order.get('TradePrice', 0) or 0
                        
                        # 如果没有，尝试从SubOrders中提取
                        if price_info['TradePrice'] == 0 and 'SubOrders' in data and 'SubOrder' in data['SubOrders']:
                            sub_orders = data['SubOrders']['SubOrder']
                            if not isinstance(sub_orders, list):
                                sub_orders = [sub_orders]
                            total_trade = 0
                            total_original = 0
                            for sub_order in sub_orders:
                                total_trade += float(sub_order.get('TradeAmount', 0) or 0)
                                total_original += float(sub_order.get('OriginalAmount', 0) or 0)
                            price_info['TradePrice'] = total_trade
                            price_info['OriginalPrice'] = total_original
                    else:
                        # 尝试其他可能的字段
                        price_info = data.get('Price', {}) or data.get('PriceInfo', {})
                elif resource_type == 'mongodb':
                    # MongoDB响应格式（类似RDS）
                    if 'PriceInfo' in data:
                        if isinstance(data['PriceInfo'], dict) and 'Price' in data['PriceInfo']:
                            price_info = data['PriceInfo']['Price']
                        elif isinstance(data['PriceInfo'], dict):
                            price_info = data['PriceInfo']
                    if not price_info:
                        price_info = data.get('Price', {})
                else:
                    # ECS格式
                    if 'PriceInfo' in data and 'Price' in data['PriceInfo']:
                        price_info = data['PriceInfo']['Price']
                
                if price_info:
                    original_price = float(price_info.get('OriginalPrice', 0) or 0)
                    trade_price = float(price_info.get('TradePrice', 0) or 0)
                    
                    if original_price > 0:
                        discount_rate = trade_price / original_price
                        discount_text = f"{discount_rate*100:.1f}% ({discount_rate:.1f}折)"
                        
                        results.append({
                            'name': instance_name,
                            'id': instance_id,
                            'zone': zone,
                            'type': instance_type,
                            'original_price': original_price,
                            'trade_price': trade_price,
                            'discount_rate': discount_rate
                        })
                        
                        print(f"✅ {discount_text}")
                    else:
                        print("❌ 无法获取价格信息")
                else:
                    print(f"❌ 价格信息格式错误 (响应键: {list(data.keys())})")
                    
            except Exception as e:
                print(f"❌ 获取价格失败: {e}")
            
            time.sleep(0.1)
        
        return results
    
    def generate_html_report(self, results, report_type='all', output_dir='.'):
        """生成HTML报告"""
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 按折扣率排序
        results_sorted = sorted(results, key=lambda x: x['discount_rate'], reverse=True)
        
        html_file = os.path.join(output_dir, f'{self.tenant_name}_discount_{report_type}_{now}.html')
        
        def esc(s):
            return (s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        
        html = []
        html.append('<!DOCTYPE html>')
        html.append('<html lang="zh-CN">')
        html.append('<head>')
        html.append('<meta charset="utf-8">')
        html.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
        html.append(f'<title>{self.tenant_name} - {report_type.upper()}续费折扣明细 - {now}</title>')
        html.append('<style>')
        html.append('body{font-family:system-ui, -apple-system, Segoe UI, Roboto, PingFang SC, Noto Sans CJK, Microsoft YaHei, Arial, sans-serif; margin:24px;}')
        html.append('h1{font-size:20px;margin:0 0 12px;} p{margin:6px 0 18px;color:#555;}')
        html.append('table{border-collapse:collapse;width:100%;table-layout:fixed;}')
        html.append('th,td{border:1px solid #e5e7eb;padding:8px 10px;font-size:13px;word-break:break-all;}')
        html.append('th{background:#f9fafb;text-align:left;}')
        html.append('tbody tr:nth-child(odd){background:#fcfcfd;}')
        html.append('tbody tr:hover{background:#f3f4f6;}')
        html.append('.num{text-align:right;}')
        html.append('.high-discount{background:#fef2f2;color:#dc2626;}')
        html.append('.low-discount{background:#f0f9ff;color:#2563eb;}')
        html.append('.muted{color:#6b7280;}')
        html.append('</style>')
        html.append('</head>')
        html.append('<body>')
        html.append(f'<h1>{self.tenant_name} - {report_type.upper()}续费折扣明细（按折扣从高到低）</h1>')
        html.append(f'<p class="muted">区域: {self.region} | 生成时间: {now} | 实例数: {len(results)}</p>')
        html.append('<table>')
        html.append('<thead><tr>')
        for col in ['实例名称','实例ID','可用区','实例类型','基准价(¥)','续费价(¥)','折扣']:
            html.append(f'<th>{col}</th>')
        html.append('</tr></thead>')
        html.append('<tbody>')
        
        for r in results_sorted:
            row_class = ''
            if r['discount_rate'] >= 0.8:
                row_class = 'high-discount'
            elif r['discount_rate'] <= 0.4:
                row_class = 'low-discount'
            
            html.append(f'<tr class="{row_class}">')
            html.append(f'<td>{esc(r["name"])}</td>')
            html.append(f'<td>{esc(r["id"])}</td>')
            html.append(f'<td>{esc(r["zone"])}</td>')
            html.append(f'<td>{esc(r["type"])}</td>')
            html.append(f'<td class="num">{r["original_price"]:.2f}</td>')
            html.append(f'<td class="num">{r["trade_price"]:.2f}</td>')
            html.append(f'<td>{r["discount_rate"]*100:.1f}% ({r["discount_rate"]:.1f}折)</td>')
            html.append('</tr>')
        
        html.append('</tbody></table>')
        html.append('</body></html>')
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html))
        
        return html_file
    
    def generate_pdf(self, html_file):
        """生成PDF文件"""
        pdf_file = html_file.replace('.html', '.pdf')
        # 确保PDF文件也在同一目录
        
        chrome_paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chromium.app/Contents/MacOS/Chromium',
            'google-chrome',
            'chromium',
            'chromium-browser'
        ]
        
        chrome_cmd = None
        for path in chrome_paths:
            if os.path.exists(path) or subprocess.run(['which', path.split('/')[-1]], 
                                                      capture_output=True).returncode == 0:
                chrome_cmd = path
                break
        
        if chrome_cmd:
            html_path = os.path.abspath(html_file)
            cmd = [
                chrome_cmd,
                '--headless',
                '--disable-gpu',
                '--no-pdf-header-footer',
                '--print-to-pdf=' + pdf_file,
                'file://' + html_path
            ]
            
            try:
                subprocess.run(cmd, capture_output=True, timeout=30)
                if os.path.exists(pdf_file):
                    return pdf_file
            except:
                pass
        
        return None
    
    def analyze_ecs_discounts(self, output_base_dir='.'):
        """分析ECS折扣"""
        print(f"🔍 开始分析{self.tenant_name}的ECS折扣...")
        print("=" * 80)
        
        # 创建输出目录结构
        output_dir = os.path.join(output_base_dir, self.tenant_name, "discount")
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 输出目录: {output_dir}")
        
        # 获取所有ECS实例
        instances = self.get_all_ecs_instances()
        
        # 筛选包年包月实例
        prepaid_instances = [i for i in instances if i.get('InstanceChargeType') == 'PrePaid']
        
        print(f"\n📋 计费方式分布:")
        print(f"• 包年包月 (PrePaid): {len(prepaid_instances)} 个")
        print(f"• 按量付费 (PostPaid): {len(instances) - len(prepaid_instances)} 个")
        
        # 获取续费价格
        results = self.get_renewal_prices(prepaid_instances, 'ecs')
        
        if not results:
            print("❌ 未获取到任何折扣数据")
            return
        
        # 生成HTML报告
        html_file = self.generate_html_report(results, 'ecs', output_dir)
        print(f"\n✅ HTML报告已生成: {html_file}")
        
        # 生成PDF报告
        pdf_file = self.generate_pdf(html_file)
        if pdf_file:
            print(f"✅ PDF报告已生成: {pdf_file}")
        
        # 显示统计信息
        print(f"\n📊 折扣统计:")
        print(f"• 总实例数: {len(results)} 个")
        if results:
            avg_discount = sum(r['discount_rate'] for r in results) / len(results)
            min_discount = min(r['discount_rate'] for r in results)
            max_discount = max(r['discount_rate'] for r in results)
            current_total = sum(r['trade_price'] for r in results)
            
            print(f"• 平均折扣: {avg_discount:.1f}折 ({avg_discount*100:.1f}%)")
            print(f"• 最低折扣: {min_discount:.1f}折 ({min_discount*100:.1f}%)")
            print(f"• 最高折扣: {max_discount:.1f}折 ({max_discount*100:.1f}%)")
            print(f"• 当前月总成本: ¥{current_total:,.2f}")
    
    def analyze_rds_discounts(self, output_base_dir='.'):
        """分析RDS折扣"""
        print(f"🔍 开始分析{self.tenant_name}的RDS折扣...")
        print("=" * 80)
        
        # 创建输出目录结构
        output_dir = os.path.join(output_base_dir, self.tenant_name, "discount")
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 输出目录: {output_dir}")
        
        # 获取所有RDS实例
        instances = self.get_all_rds_instances()
        
        # 筛选包年包月实例
        prepaid_instances = [i for i in instances if i.get('PayType') == 'Prepaid']
        
        print(f"\n📋 计费方式分布:")
        print(f"• 包年包月 (Prepaid): {len(prepaid_instances)} 个")
        print(f"• 按量付费 (Postpaid): {len(instances) - len(prepaid_instances)} 个")
        
        # 获取续费价格
        results = self.get_renewal_prices(prepaid_instances, 'rds')
        
        if not results:
            print("❌ 未获取到任何折扣数据")
            return
        
        # 生成HTML报告
        html_file = self.generate_html_report(results, 'rds', output_dir)
        print(f"\n✅ HTML报告已生成: {html_file}")
        
        # 生成PDF报告
        pdf_file = self.generate_pdf(html_file)
        if pdf_file:
            print(f"✅ PDF报告已生成: {pdf_file}")
        
        # 显示统计信息
        print(f"\n📊 折扣统计:")
        print(f"• 总实例数: {len(results)} 个")
        if results:
            avg_discount = sum(r['discount_rate'] for r in results) / len(results)
            min_discount = min(r['discount_rate'] for r in results)
            max_discount = max(r['discount_rate'] for r in results)
            current_total = sum(r['trade_price'] for r in results)
            
            print(f"• 平均折扣: {avg_discount:.1f}折 ({avg_discount*100:.1f}%)")
            print(f"• 最低折扣: {min_discount:.1f}折 ({min_discount*100:.1f}%)")
            print(f"• 最高折扣: {max_discount:.1f}折 ({max_discount*100:.1f}%)")
            print(f"• 当前月总成本: ¥{current_total:,.2f}")
    
    def analyze_redis_discounts(self, output_base_dir='.'):
        """分析Redis折扣"""
        print(f"🔍 开始分析{self.tenant_name}的Redis折扣...")
        print("=" * 80)
        
        # 创建输出目录结构
        output_dir = os.path.join(output_base_dir, self.tenant_name, "discount")
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 输出目录: {output_dir}")
        
        # 获取所有Redis实例
        instances = self.get_all_redis_instances()
        
        # 筛选包年包月实例
        prepaid_instances = [i for i in instances if i.get('ChargeType') == 'PrePaid']
        
        print(f"\n📋 计费方式分布:")
        print(f"• 包年包月 (PrePaid): {len(prepaid_instances)} 个")
        print(f"• 按量付费 (PostPaid): {len(instances) - len(prepaid_instances)} 个")
        
        if len(prepaid_instances) == 0:
            print("⚠️ 未找到包年包月Redis实例")
            return
        
        # 获取续费价格
        results = self.get_renewal_prices(prepaid_instances, 'redis')
        
        if not results:
            print("❌ 未获取到任何折扣数据")
            return
        
        # 生成HTML报告
        html_file = self.generate_html_report(results, 'redis', output_dir)
        print(f"\n✅ HTML报告已生成: {html_file}")
        
        # 生成PDF报告
        pdf_file = self.generate_pdf(html_file)
        if pdf_file:
            print(f"✅ PDF报告已生成: {pdf_file}")
        
        # 显示统计信息
        print(f"\n📊 折扣统计:")
        print(f"• 总实例数: {len(results)} 个")
        if results:
            avg_discount = sum(r['discount_rate'] for r in results) / len(results)
            min_discount = min(r['discount_rate'] for r in results)
            max_discount = max(r['discount_rate'] for r in results)
            current_total = sum(r['trade_price'] for r in results)
            
            print(f"• 平均折扣: {avg_discount:.1f}折 ({avg_discount*100:.1f}%)")
            print(f"• 最低折扣: {min_discount:.1f}折 ({min_discount*100:.1f}%)")
            print(f"• 最高折扣: {max_discount:.1f}折 ({max_discount*100:.1f}%)")
            print(f"• 当前月总成本: ¥{current_total:,.2f}")
    
    def analyze_mongodb_discounts(self, output_base_dir='.'):
        """分析MongoDB折扣"""
        print(f"🔍 开始分析{self.tenant_name}的MongoDB折扣...")
        print("=" * 80)
        
        # 创建输出目录结构
        output_dir = os.path.join(output_base_dir, self.tenant_name, "discount")
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 输出目录: {output_dir}")
        
        # 获取所有MongoDB实例
        instances = self.get_all_mongodb_instances()
        
        # 筛选包年包月实例
        prepaid_instances = [i for i in instances if i.get('ChargeType') == 'PrePaid']
        
        print(f"\n📋 计费方式分布:")
        print(f"• 包年包月 (PrePaid): {len(prepaid_instances)} 个")
        print(f"• 按量付费 (PostPaid): {len(instances) - len(prepaid_instances)} 个")
        
        if len(prepaid_instances) == 0:
            print("⚠️ 未找到包年包月MongoDB实例")
            return
        
        # 获取续费价格
        results = self.get_renewal_prices(prepaid_instances, 'mongodb')
        
        if not results:
            print("❌ 未获取到任何折扣数据")
            return
        
        # 生成HTML报告
        html_file = self.generate_html_report(results, 'mongodb', output_dir)
        print(f"\n✅ HTML报告已生成: {html_file}")
        
        # 生成PDF报告
        pdf_file = self.generate_pdf(html_file)
        if pdf_file:
            print(f"✅ PDF报告已生成: {pdf_file}")
        
        # 显示统计信息
        print(f"\n📊 折扣统计:")
        print(f"• 总实例数: {len(results)} 个")
        if results:
            avg_discount = sum(r['discount_rate'] for r in results) / len(results)
            min_discount = min(r['discount_rate'] for r in results)
            max_discount = max(r['discount_rate'] for r in results)
            current_total = sum(r['trade_price'] for r in results)
            
            print(f"• 平均折扣: {avg_discount:.1f}折 ({avg_discount*100:.1f}%)")
            print(f"• 最低折扣: {min_discount:.1f}折 ({min_discount*100:.1f}%)")
            print(f"• 最高折扣: {max_discount:.1f}折 ({max_discount*100:.1f}%)")
            print(f"• 当前月总成本: ¥{current_total:,.2f}")


def main():
    """主函数"""
    import sys
    import os
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 加载配置
    config_file = os.path.join(current_dir, 'config.json')
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    
    default_tenant = config_data.get('default_tenant', 'ydzn')
    tenants = config_data.get('tenants', {})
    
    # 获取命令行参数
    if len(sys.argv) < 2:
        print("使用方法: python -m discount_analyzer <tenant_name> [resource_type]")
        return
    
    tenant_name = sys.argv[1] if len(sys.argv) > 1 else default_tenant
    resource_type = sys.argv[2] if len(sys.argv) > 2 else 'ecs'
    
    if tenant_name not in tenants:
        print(f"❌ 未找到租户: {tenant_name}")
        return
    
    tenant_config = tenants[tenant_name]
    analyzer = DiscountAnalyzer(
        tenant_name,
        tenant_config['access_key_id'],
        tenant_config['access_key_secret']
    )
    
    if resource_type == 'ecs':
        analyzer.analyze_ecs_discounts()
    else:
        print(f"❌ 不支持的资源类型: {resource_type}")


if __name__ == "__main__":
    main()
