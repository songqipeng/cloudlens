#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
折扣分析模块
"""

import json
import time
import re
import os
import subprocess
from datetime import datetime
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest


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
                            all_instances.append({
                                'InstanceId': inst.get('InstanceId', ''),
                                'InstanceName': inst.get('InstanceName', ''),
                                'InstanceClass': inst.get('InstanceClass', ''),
                                'InstanceType': inst.get('InstanceType', ''),
                                'ChargeType': inst.get('ChargeType', ''),
                                'RegionId': region
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
        """获取续费价格"""
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
                elif resource_type == 'redis':
                    # Redis使用KVStore API（使用通用域名）
                    request.set_domain('r-kvstore.aliyuncs.com')
                    request.set_version('2015-01-01')
                    request.set_action_name('DescribeRenewalPrice')
                    request.add_query_param('RegionId', region)
                    request.add_query_param('InstanceId', instance_id)
                    request.add_query_param('Period', 1)
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
                else:
                    # ECS
                    request.set_domain(f'ecs.{region}.aliyuncs.com')
                    request.set_version('2014-05-26')
                    request.set_action_name('DescribeRenewalPrice')
                    request.add_query_param('ResourceId', instance_id)
                    request.add_query_param('Period', 1)
                    request.add_query_param('PriceUnit', 'Month')
                
                request.set_method('POST')
                
                client = AcsClient(self.access_key_id, self.access_key_secret, region)
                
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
                    # Redis响应格式
                    if 'PriceInfo' in data:
                        if isinstance(data['PriceInfo'], dict) and 'Price' in data['PriceInfo']:
                            price_info = data['PriceInfo']['Price']
                        elif isinstance(data['PriceInfo'], dict):
                            price_info = data['PriceInfo']
                    if not price_info:
                        price_info = data.get('Price', {})
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
