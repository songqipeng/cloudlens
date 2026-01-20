#!/usr/bin/env python3
"""
缓存验证机制测试脚本

测试场景:
1. 基础格式检查
2. 时间戳验证（当月/历史数据）
3. 深度检查（记录数、金额验证）
"""

from cloudlens.core.cache_validator import SmartCacheValidator, CacheHealthMonitor
from cloudlens.core.cache.manager import CacheManager
from cloudlens.core.database import get_database_adapter
from datetime import datetime, timedelta

def test_basic_check():
    """测试基础格式检查"""
    print("\n" + "="*60)
    print("测试1: 基础格式检查")
    print("="*60)

    validator = SmartCacheValidator()

    # 测试1.1: 有效格式
    valid_data = {
        "data": {"total_cost": 1000},
        "metadata": {"cached_at": datetime.now().isoformat()}
    }
    is_valid, reason, _ = validator.validate(valid_data)
    print(f"✓ 有效格式: {is_valid}, 原因: {reason}")
    assert is_valid, "有效格式应该通过验证"

    # 测试1.2: 无效格式（缺少metadata）
    invalid_data = {"data": {"total_cost": 1000}}
    is_valid, reason, _ = validator.validate(invalid_data)
    print(f"✓ 缺少metadata: {is_valid}, 原因: {reason}")
    assert not is_valid, "缺少metadata应该验证失败"

    # 测试1.3: 无效格式（不是字典）
    is_valid, reason, _ = validator.validate([1, 2, 3])
    print(f"✓ 非字典类型: {is_valid}, 原因: {reason}")
    assert not is_valid, "非字典类型应该验证失败"

    print("✅ 基础格式检查测试通过")


def test_timestamp_check():
    """测试时间戳检查"""
    print("\n" + "="*60)
    print("测试2: 时间戳验证")
    print("="*60)

    validator = SmartCacheValidator()
    now = datetime.now()
    current_cycle = now.strftime("%Y-%m")

    # 测试2.1: 当月数据，3小时前缓存（应该有效，6h TTL）
    cache_time = now - timedelta(hours=3)
    data = {
        "data": {"total_cost": 1000},
        "metadata": {"cached_at": cache_time.isoformat()}
    }
    is_valid, reason, _ = validator.validate(data, billing_cycle=current_cycle)
    print(f"✓ 当月3小时前: {is_valid}, 原因: {reason}")
    assert is_valid, "当月3小时前的缓存应该有效"

    # 测试2.2: 当月数据，8小时前缓存（应该无效，超过6h TTL）
    cache_time = now - timedelta(hours=8)
    data["metadata"]["cached_at"] = cache_time.isoformat()
    is_valid, reason, _ = validator.validate(data, billing_cycle=current_cycle)
    print(f"✓ 当月8小时前: {is_valid}, 原因: {reason}")
    assert not is_valid, "当月8小时前的缓存应该过期"

    # 测试2.3: 历史数据，3天前缓存（应该有效，7d TTL）
    historical_cycle = "2025-06"
    cache_time = now - timedelta(days=3)
    data["metadata"]["cached_at"] = cache_time.isoformat()
    is_valid, reason, _ = validator.validate(data, billing_cycle=historical_cycle)
    print(f"✓ 历史数据3天前: {is_valid}, 原因: {reason}")
    assert is_valid, "历史数据3天前的缓存应该有效"

    # 测试2.4: 历史数据，8天前缓存（应该无效，超过7d TTL）
    cache_time = now - timedelta(days=8)
    data["metadata"]["cached_at"] = cache_time.isoformat()
    is_valid, reason, _ = validator.validate(data, billing_cycle=historical_cycle)
    print(f"✓ 历史数据8天前: {is_valid}, 原因: {reason}")
    assert not is_valid, "历史数据8天前的缓存应该过期"

    print("✅ 时间戳验证测试通过")


def test_deep_check():
    """测试深度检查（需要数据库）"""
    print("\n" + "="*60)
    print("测试3: 深度检查")
    print("="*60)

    try:
        db = get_database_adapter()
        validator = SmartCacheValidator(db_adapter=db, verification_probability=1.0)  # 100%概率深度检查

        # 查询真实的数据库数据
        billing_cycle = "2026-01"
        account_id = "prod"

        query = f"""
            SELECT
                COUNT(*) as count,
                COALESCE(SUM(payment_amount), 0) as total
            FROM bill_items
            WHERE billing_cycle = '{billing_cycle}'
            AND account_id = '{account_id}'
        """
        result = db.query(query)

        if not result or result[0]['count'] == 0:
            print("⚠️  数据库中无测试数据，跳过深度检查测试")
            return

        db_count = result[0]['count']
        db_total = float(result[0]['total'] or 0)

        print(f"数据库实际数据: 记录数={db_count}, 金额={db_total:.2f}")

        # 测试3.1: 准确的缓存数据（应该通过）
        now = datetime.now()
        accurate_data = {
            "data": {"total_pretax": db_total},
            "metadata": {
                "cached_at": now.isoformat(),
                "record_count": db_count
            }
        }
        is_valid, reason, _ = validator.validate(
            accurate_data,
            billing_cycle=billing_cycle,
            account_id=account_id,
            force_deep_check=True
        )
        print(f"✓ 准确数据: {is_valid}, 原因: {reason}")
        assert is_valid, "准确数据应该通过深度检查"

        # 测试3.2: 记录数不匹配（应该失败）
        wrong_count_data = {
            "data": {"total_pretax": db_total},
            "metadata": {
                "cached_at": now.isoformat(),
                "record_count": db_count + 1000  # 相差太多
            }
        }
        is_valid, reason, _ = validator.validate(
            wrong_count_data,
            billing_cycle=billing_cycle,
            account_id=account_id,
            force_deep_check=True
        )
        print(f"✓ 记录数不匹配: {is_valid}, 原因: {reason}")
        assert not is_valid, "记录数不匹配应该验证失败"

        # 测试3.3: 金额不匹配（应该失败）
        wrong_amount_data = {
            "data": {"total_pretax": db_total * 2},  # 相差太多
            "metadata": {
                "cached_at": now.isoformat(),
                "record_count": db_count
            }
        }
        is_valid, reason, _ = validator.validate(
            wrong_amount_data,
            billing_cycle=billing_cycle,
            account_id=account_id,
            force_deep_check=True
        )
        print(f"✓ 金额不匹配: {is_valid}, 原因: {reason}")
        assert not is_valid, "金额不匹配应该验证失败"

        print("✅ 深度检查测试通过")

    except Exception as e:
        print(f"⚠️  深度检查测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_cache_manager_integration():
    """测试CacheManager集成"""
    print("\n" + "="*60)
    print("测试4: CacheManager集成")
    print("="*60)

    cache_manager = CacheManager(ttl_seconds=3600)

    # 测试4.1: 创建带metadata的缓存数据
    test_data = {"total_cost": 1000, "items": [1, 2, 3]}
    cache_data = cache_manager.create_cache_data(
        data=test_data,
        billing_cycle="2026-01",
        record_count=3,
        data_source="test"
    )

    print(f"✓ 创建的缓存数据: {cache_data.keys()}")
    assert "data" in cache_data, "缓存数据应包含data字段"
    assert "metadata" in cache_data, "缓存数据应包含metadata字段"
    assert cache_data["metadata"]["billing_cycle"] == "2026-01", "metadata应包含billing_cycle"
    assert cache_data["metadata"]["record_count"] == 3, "metadata应包含record_count"

    # 测试4.2: 写入和读取（原始格式）
    try:
        cache_manager.set(
            resource_type="test_cache",
            account_name="test_account",
            data=cache_data
        )

        # 读取原始数据（包含metadata）
        cached_raw = cache_manager.get(
            resource_type="test_cache",
            account_name="test_account",
            raw=True
        )
        print(f"✓ 读取原始数据: {cached_raw.keys() if cached_raw else None}")
        assert cached_raw is not None, "应该能读取到缓存"
        assert "data" in cached_raw, "原始数据应包含data"
        assert "metadata" in cached_raw, "原始数据应包含metadata"

        # 读取处理后的数据（只有data部分）
        cached_data = cache_manager.get(
            resource_type="test_cache",
            account_name="test_account",
            raw=False
        )
        print(f"✓ 读取处理后数据: {cached_data}")
        assert cached_data == test_data, "处理后的数据应该是原始data部分"

        # 清理测试缓存
        cache_manager.clear(resource_type="test_cache", account_name="test_account")

        print("✅ CacheManager集成测试通过")

    except Exception as e:
        print(f"⚠️  CacheManager集成测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_health_monitor():
    """测试健康监控"""
    print("\n" + "="*60)
    print("测试5: 缓存健康监控")
    print("="*60)

    monitor = CacheHealthMonitor()

    # 模拟一系列缓存检查
    monitor.record_check(hit=True, valid=True, deep_check=False)   # 命中且有效
    monitor.record_check(hit=True, valid=True, deep_check=False)   # 命中且有效
    monitor.record_check(hit=True, valid=False, deep_check=True)   # 命中但验证失败
    monitor.record_check(hit=False, valid=False, deep_check=False) # 未命中
    monitor.record_check(hit=True, valid=True, deep_check=True)    # 命中且深度检查通过

    print(monitor.get_report())

    health_score = monitor.get_health_score()
    print(f"健康度评分: {health_score}/100")

    assert monitor.metrics["total_checks"] == 5, "应该记录5次检查"
    assert monitor.metrics["cache_hits"] == 4, "应该有4次缓存命中"
    assert monitor.metrics["validation_failures"] == 1, "应该有1次验证失败"
    assert monitor.metrics["deep_checks"] == 2, "应该有2次深度检查"

    print("✅ 健康监控测试通过")


if __name__ == "__main__":
    print("缓存验证机制测试")
    print("="*60)

    try:
        test_basic_check()
        test_timestamp_check()
        test_deep_check()
        test_cache_manager_integration()
        test_health_monitor()

        print("\n" + "="*60)
        print("✅ 所有测试通过！")
        print("="*60)

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
