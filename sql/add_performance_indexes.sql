-- ============================================================
-- CloudLens 性能优化索引
-- 版本: 1.0
-- 创建时间: 2025-12-23
-- 说明: 添加性能优化索引，提升查询速度
-- ============================================================

USE cloudlens;

-- ============================================================
-- 1. bill_items 表性能优化索引
-- ============================================================

-- 复合索引：账号 + 账期（最常用查询）
-- 如果已存在 idx_account_cycle，先删除再创建（优化顺序）
DROP INDEX IF EXISTS idx_account_cycle ON bill_items;
CREATE INDEX idx_account_billing ON bill_items(account_id, billing_cycle) COMMENT '账号和账期复合索引（优化查询）';

-- 账单日期索引（已存在，但确保优化）
-- CREATE INDEX IF NOT EXISTS idx_billing_date ON bill_items(billing_date);

-- 产品代码索引（已存在，但确保优化）
-- CREATE INDEX IF NOT EXISTS idx_product_code ON bill_items(product_code);

-- 复合索引：账号 + 账单日期（时间范围查询）
CREATE INDEX IF NOT EXISTS idx_account_billing_date ON bill_items(account_id, billing_date) COMMENT '账号和账单日期复合索引';

-- 复合索引：账号 + 产品代码（产品维度分析）
CREATE INDEX IF NOT EXISTS idx_account_product ON bill_items(account_id, product_code) COMMENT '账号和产品代码复合索引';

-- 复合索引：账期 + 产品代码（产品趋势分析）
CREATE INDEX IF NOT EXISTS idx_cycle_product ON bill_items(billing_cycle, product_code) COMMENT '账期和产品代码复合索引';

-- ============================================================
-- 2. resource_cache 表性能优化索引
-- ============================================================

-- 复合索引：资源类型 + 账号名称（最常用查询）
-- 如果已存在 idx_resource_type_account，先删除再创建（优化顺序）
DROP INDEX IF EXISTS idx_resource_type_account ON resource_cache;
CREATE INDEX idx_cache_key ON resource_cache(resource_type, account_name) COMMENT '资源类型和账号复合索引（优化查询）';

-- 创建时间索引（已存在，但确保优化）
-- CREATE INDEX IF NOT EXISTS idx_expires_at ON resource_cache(expires_at);

-- 复合索引：账号 + 过期时间（清理过期缓存）
CREATE INDEX IF NOT EXISTS idx_account_expires ON resource_cache(account_name, expires_at) COMMENT '账号和过期时间复合索引';

-- ============================================================
-- 3. alerts 表性能优化索引
-- ============================================================

-- 复合索引：账号 + 状态（常用查询）
CREATE INDEX IF NOT EXISTS idx_account_status ON alerts(account_id, status) COMMENT '账号和状态复合索引';

-- 复合索引：账号 + 触发时间（时间范围查询）
CREATE INDEX IF NOT EXISTS idx_account_triggered ON alerts(account_id, triggered_at) COMMENT '账号和触发时间复合索引';

-- 复合索引：状态 + 严重程度（告警筛选）
CREATE INDEX IF NOT EXISTS idx_status_severity ON alerts(status, severity) COMMENT '状态和严重程度复合索引';

-- ============================================================
-- 4. budgets 表性能优化索引
-- ============================================================

-- 复合索引：账号 + 周期（常用查询）
CREATE INDEX IF NOT EXISTS idx_account_period ON budgets(account_id, period) COMMENT '账号和周期复合索引';

-- 复合索引：账号 + 开始日期 + 结束日期（日期范围查询）
CREATE INDEX IF NOT EXISTS idx_account_dates ON budgets(account_id, start_date, end_date) COMMENT '账号和日期范围复合索引';

-- ============================================================
-- 5. budget_records 表性能优化索引
-- ============================================================

-- 复合索引：预算ID + 日期（时间序列查询）
CREATE INDEX IF NOT EXISTS idx_budget_date_composite ON budget_records(budget_id, date) COMMENT '预算ID和日期复合索引';

-- ============================================================
-- 6. virtual_tags 表性能优化索引
-- ============================================================

-- 复合索引：账号 + 标签键（标签查询）
CREATE INDEX IF NOT EXISTS idx_account_tag_key ON virtual_tags(account_id, tag_key) COMMENT '账号和标签键复合索引';

-- ============================================================
-- 7. tag_matches 表性能优化索引
-- ============================================================

-- 复合索引：账号 + 资源类型 + 资源ID（资源查询）
CREATE INDEX IF NOT EXISTS idx_account_resource ON tag_matches(account_id, resource_type, resource_id) COMMENT '账号和资源复合索引';

-- ============================================================
-- 完成
-- ============================================================
SELECT 'Performance indexes added successfully!' AS status;

