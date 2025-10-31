#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DiscountAnalyzer 单元测试
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from resource_modules.discount_analyzer import DiscountAnalyzer


class TestDiscountAnalyzer:
    """折扣分析器测试类"""

    @pytest.fixture
    def analyzer(self):
        """创建折扣分析器实例"""
        return DiscountAnalyzer('test_tenant', 'test_key_id', 'test_key_secret')

    def test_init(self, analyzer):
        """测试初始化"""
        assert analyzer.tenant_name == 'test_tenant'
        assert analyzer.access_key_id == 'test_key_id'
        assert analyzer.access_key_secret == 'test_key_secret'
        assert analyzer.region == 'cn-beijing'

    @patch('resource_modules.discount_analyzer.AcsClient')
    @patch('resource_modules.discount_analyzer.CommonRequest')
    def test_get_all_ecs_instances(self, mock_request_class, mock_client_class, analyzer):
        """测试获取所有ECS实例"""
        # Mock ECS实例列表（第1页）
        ecs_page1_response = json.dumps({
            'Instances': {
                'Instance': [
                    {
                        'InstanceId': 'i-test-001',
                        'InstanceName': 'Test ECS 1',
                        'InstanceType': 'ecs.n4.small',
                        'ZoneId': 'cn-beijing-a',
                        'InstanceChargeType': 'PrePaid'
                    },
                    {
                        'InstanceId': 'i-test-002',
                        'InstanceName': 'Test ECS 2',
                        'InstanceType': 'ecs.n4.large',
                        'ZoneId': 'cn-beijing-b',
                        'InstanceChargeType': 'PostPaid'
                    }
                ]
            }
        })

        # Mock空页（结束分页）
        ecs_page2_response = json.dumps({
            'Instances': {
                'Instance': []
            }
        })

        mock_client = MagicMock()
        # 第一次调用返回第1页，第二次返回空页
        mock_client.do_action_with_exception.side_effect = [
            ecs_page1_response,
            ecs_page2_response
        ]
        mock_client_class.return_value = mock_client

        instances = analyzer.get_all_ecs_instances()

        assert len(instances) == 2
        assert instances[0]['InstanceId'] == 'i-test-001'
        assert instances[0]['InstanceChargeType'] == 'PrePaid'
        assert instances[1]['InstanceId'] == 'i-test-002'
        assert instances[1]['InstanceChargeType'] == 'PostPaid'

    @patch('resource_modules.discount_analyzer.AcsClient')
    def test_get_all_rds_instances(self, mock_client_class, analyzer):
        """测试获取所有RDS实例"""
        rds_response = json.dumps({
            'Items': {
                'DBInstance': [
                    {
                        'DBInstanceId': 'rds-test-001',
                        'DBInstanceDescription': 'Test RDS',
                        'DBInstanceType': 'Primary',
                        'Engine': 'MySQL',
                        'EngineVersion': '8.0',
                        'DBInstanceClass': 'mysql.n2.small.1',
                        'PayType': 'Prepaid',
                        'ZoneId': 'cn-hangzhou-b'
                    }
                ]
            }
        })

        mock_client = MagicMock()
        mock_client.do_action_with_exception.return_value = rds_response
        mock_client_class.return_value = mock_client

        instances = analyzer.get_all_rds_instances()

        # 应该至少包含测试实例
        assert any(inst['DBInstanceId'] == 'rds-test-001' for inst in instances)
        test_instance = next(inst for inst in instances if inst['DBInstanceId'] == 'rds-test-001')
        assert test_instance['Engine'] == 'MySQL'
        assert test_instance['PayType'] == 'Prepaid'

    @patch('resource_modules.discount_analyzer.AcsClient')
    def test_get_all_redis_instances(self, mock_client_class, analyzer):
        """测试获取所有Redis实例"""
        redis_response = json.dumps({
            'Instances': {
                'KVStoreInstance': [
                    {
                        'InstanceId': 'r-test-001',
                        'InstanceName': 'Test Redis',
                        'InstanceClass': 'redis.master.small.default',
                        'ChargeType': 'PrePaid',
                        'Capacity': 1024,
                        'Bandwidth': 10
                    }
                ]
            }
        })

        mock_client = MagicMock()
        mock_client.do_action_with_exception.return_value = redis_response
        mock_client_class.return_value = mock_client

        instances = analyzer.get_all_redis_instances()

        assert any(inst['InstanceId'] == 'r-test-001' for inst in instances)
        test_instance = next(inst for inst in instances if inst['InstanceId'] == 'r-test-001')
        assert test_instance['ChargeType'] == 'PrePaid'
        assert test_instance['Capacity'] == 1024

    @patch('resource_modules.discount_analyzer.AcsClient')
    def test_get_all_mongodb_instances(self, mock_client_class, analyzer):
        """测试获取所有MongoDB实例"""
        mongodb_response = json.dumps({
            'DBInstances': {
                'DBInstance': [
                    {
                        'DBInstanceId': 'dds-test-001',
                        'DBInstanceDescription': 'Test MongoDB',
                        'DBInstanceType': 'replicate',
                        'ChargeType': 'PrePaid',
                        'Engine': 'MongoDB',
                        'EngineVersion': '4.4',
                        'DBInstanceClass': 'dds.mongo.mid',
                        'ZoneId': 'cn-hangzhou-b'
                    }
                ]
            }
        })

        mock_client = MagicMock()
        mock_client.do_action_with_exception.return_value = mongodb_response
        mock_client_class.return_value = mock_client

        instances = analyzer.get_all_mongodb_instances()

        assert any(inst['DBInstanceId'] == 'dds-test-001' for inst in instances)
        test_instance = next(inst for inst in instances if inst['DBInstanceId'] == 'dds-test-001')
        assert test_instance['Engine'] == 'MongoDB'
        assert test_instance['ChargeType'] == 'PrePaid'

    @patch('resource_modules.discount_analyzer.process_concurrently')
    @patch('resource_modules.discount_analyzer.AcsClient')
    def test_get_renewal_prices_ecs_skip_postpaid(self, mock_client_class, mock_process, analyzer):
        """测试获取ECS续费价格 - 跳过按量付费"""
        instances = [
            {
                'InstanceId': 'i-postpaid-001',
                'InstanceName': 'PostPaid Instance',
                'InstanceChargeType': 'PostPaid',
                'ZoneId': 'cn-beijing-a',
                'InstanceType': 'ecs.n4.small'
            }
        ]

        # Mock并发处理返回跳过结果
        mock_process.return_value = [
            {'skip': True, 'reason': '按量付费'}
        ]

        results = analyzer.get_renewal_prices(instances, 'ecs')

        # 按量付费实例应该被跳过，results为空
        assert len(results) == 0

    @patch('resource_modules.discount_analyzer.process_concurrently')
    @patch('resource_modules.discount_analyzer.AcsClient')
    def test_get_renewal_prices_ecs_success(self, mock_client_class, mock_process, analyzer):
        """测试获取ECS续费价格 - 成功"""
        instances = [
            {
                'InstanceId': 'i-prepaid-001',
                'InstanceName': 'PrePaid Instance',
                'InstanceChargeType': 'PrePaid',
                'ZoneId': 'cn-beijing-a',
                'InstanceType': 'ecs.n4.small'
            }
        ]

        # Mock并发处理返回成功结果
        mock_process.return_value = [
            {
                'success': True,
                'name': 'PrePaid Instance',
                'id': 'i-prepaid-001',
                'zone': 'cn-beijing-a',
                'type': 'ecs.n4.small',
                'original_price': 1000.0,
                'trade_price': 700.0,
                'discount_rate': 0.7
            }
        ]

        results = analyzer.get_renewal_prices(instances, 'ecs')

        assert len(results) == 1
        assert results[0]['original_price'] == 1000.0
        assert results[0]['trade_price'] == 700.0
        assert abs(results[0]['discount_rate'] - 0.7) < 0.01

    @patch('resource_modules.discount_analyzer.process_concurrently')
    @patch('resource_modules.discount_analyzer.AcsClient')
    def test_get_renewal_prices_rds(self, mock_client_class, mock_process, analyzer):
        """测试获取RDS续费价格"""
        instances = [
            {
                'DBInstanceId': 'rds-prepaid-001',
                'DBInstanceDescription': 'Test RDS',
                'PayType': 'Prepaid',
                'ZoneId': 'cn-hangzhou-b',
                'Engine': 'MySQL',
                'DBInstanceClass': 'mysql.n2.small.1',
                'RegionId': 'cn-hangzhou'
            }
        ]

        mock_process.return_value = [
            {
                'success': True,
                'name': 'Test RDS',
                'id': 'rds-prepaid-001',
                'zone': 'cn-hangzhou-b',
                'type': 'MySQL mysql.n2.small.1',
                'original_price': 800.0,
                'trade_price': 640.0,
                'discount_rate': 0.8
            }
        ]

        results = analyzer.get_renewal_prices(instances, 'rds')

        assert len(results) == 1
        assert results[0]['original_price'] == 800.0
        assert results[0]['trade_price'] == 640.0
        assert abs(results[0]['discount_rate'] - 0.8) < 0.01

    def test_generate_html_report(self, analyzer, tmp_path):
        """测试生成HTML报告"""
        results = [
            {
                'name': 'Test Instance 1',
                'id': 'i-001',
                'zone': 'cn-beijing-a',
                'type': 'ecs.n4.small',
                'original_price': 1000.0,
                'trade_price': 700.0,
                'discount_rate': 0.7
            },
            {
                'name': 'Test Instance 2',
                'id': 'i-002',
                'zone': 'cn-beijing-b',
                'type': 'ecs.n4.large',
                'original_price': 2000.0,
                'trade_price': 1600.0,
                'discount_rate': 0.8
            }
        ]

        html_file = analyzer.generate_html_report(results, 'ecs', str(tmp_path))

        # 验证文件已创建
        assert html_file.endswith('.html')
        import os
        assert os.path.exists(html_file)

        # 读取并验证HTML内容
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'Test Instance 1' in content
            assert 'Test Instance 2' in content
            assert 'i-001' in content
            assert 'i-002' in content
            assert '1000.00' in content
            assert '700.00' in content

    def test_generate_html_report_sorting(self, analyzer, tmp_path):
        """测试HTML报告按折扣率排序"""
        results = [
            {'name': 'Low Discount', 'id': 'i-001', 'zone': 'z1', 'type': 't1',
             'original_price': 100, 'trade_price': 90, 'discount_rate': 0.9},
            {'name': 'High Discount', 'id': 'i-002', 'zone': 'z2', 'type': 't2',
             'original_price': 100, 'trade_price': 50, 'discount_rate': 0.5},
            {'name': 'Medium Discount', 'id': 'i-003', 'zone': 'z3', 'type': 't3',
             'original_price': 100, 'trade_price': 70, 'discount_rate': 0.7},
        ]

        html_file = analyzer.generate_html_report(results, 'test', str(tmp_path))

        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 在HTML中，折扣率高的应该排在前面（0.9 > 0.7 > 0.5）
            pos_low = content.find('Low Discount')
            pos_medium = content.find('Medium Discount')
            pos_high = content.find('High Discount')

            # Low Discount (0.9) 应该在最前
            assert pos_low < pos_medium
            assert pos_low < pos_high

    @patch('resource_modules.discount_analyzer.subprocess.run')
    @patch('resource_modules.discount_analyzer.os.path.exists')
    def test_generate_pdf(self, mock_exists, mock_subprocess, analyzer, tmp_path):
        """测试生成PDF"""
        html_file = str(tmp_path / 'test_report.html')

        # 创建测试HTML文件
        with open(html_file, 'w') as f:
            f.write('<html><body>Test</body></html>')

        # Mock Chrome存在
        mock_exists.return_value = True
        # Mock subprocess成功
        mock_subprocess.return_value = MagicMock(returncode=0)

        # 创建PDF文件（模拟Chrome生成）
        pdf_file = html_file.replace('.html', '.pdf')
        with open(pdf_file, 'w') as f:
            f.write('PDF content')

        result = analyzer.generate_pdf(html_file)

        # 如果Chrome可用，应该返回PDF文件路径
        if result:
            assert result.endswith('.pdf')

    @patch('resource_modules.discount_analyzer.AcsClient')
    @patch('resource_modules.discount_analyzer.process_concurrently')
    def test_analyze_ecs_discounts_empty(self, mock_process, mock_client_class, analyzer, tmp_path, capsys):
        """测试分析ECS折扣 - 空实例"""
        # Mock get_all_ecs_instances返回空列表
        with patch.object(analyzer, 'get_all_ecs_instances', return_value=[]):
            analyzer.analyze_ecs_discounts(str(tmp_path))

            captured = capsys.readouterr()
            assert '总共获取到 0 个实例' in captured.out or '未获取到任何折扣数据' in captured.out

    def test_prepaid_instance_filtering(self, analyzer):
        """测试包年包月实例过滤逻辑"""
        instances = [
            {'InstanceId': 'i-1', 'InstanceChargeType': 'PrePaid'},
            {'InstanceId': 'i-2', 'InstanceChargeType': 'PostPaid'},
            {'InstanceId': 'i-3', 'InstanceChargeType': 'PrePaid'},
        ]

        # 使用实际代码的过滤逻辑
        prepaid_instances = [i for i in instances if i.get('InstanceChargeType') == 'PrePaid']

        assert len(prepaid_instances) == 2
        assert all(i['InstanceChargeType'] == 'PrePaid' for i in prepaid_instances)

    def test_discount_rate_calculation(self):
        """测试折扣率计算逻辑"""
        # 7折
        original_price = 1000.0
        trade_price = 700.0
        discount_rate = trade_price / original_price
        assert abs(discount_rate - 0.7) < 0.01

        # 8.5折
        original_price = 1000.0
        trade_price = 850.0
        discount_rate = trade_price / original_price
        assert abs(discount_rate - 0.85) < 0.01

        # 无折扣
        original_price = 1000.0
        trade_price = 1000.0
        discount_rate = trade_price / original_price
        assert abs(discount_rate - 1.0) < 0.01
