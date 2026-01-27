-- ============================================================
-- CloudLens MySQL 性能优化索引
-- 用于优化折扣分析等大数据量查询
-- ============================================================

USE cloudlens;

-- 复合索引：优化季度/年度分析查询
-- 这个索引覆盖了 account_id + billing_cycle 的筛选和聚合
ALTER TABLE bill_items ADD INDEX idx_bill_quarterly_analysis (account_id, billing_cycle, pretax_amount, invoice_discount);

-- 复合索引：优化产品趋势分析
ALTER TABLE bill_items ADD INDEX idx_bill_product_analysis (account_id, product_name, billing_cycle);

-- 复合索引：优化区域分析
ALTER TABLE bill_items ADD INDEX idx_bill_region_analysis (account_id, region, billing_cycle);

-- 复合索引：优化订阅类型分析
ALTER TABLE bill_items ADD INDEX idx_bill_subscription_analysis (account_id, subscription_type, billing_cycle);

-- 复合索引：优化实例生命周期分析
ALTER TABLE bill_items ADD INDEX idx_bill_instance_lifecycle (account_id, instance_id, billing_cycle);

SELECT 'Performance indexes added successfully!' AS status;
