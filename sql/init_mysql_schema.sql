-- ============================================================
-- CloudLens MySQL 数据库表结构
-- 版本: 1.0
-- 创建时间: 2024-12-18
-- ============================================================

-- 使用cloudlens数据库
USE cloudlens;

-- ============================================================
-- 1. 资源缓存表
-- ============================================================
CREATE TABLE IF NOT EXISTS resource_cache (
    cache_key VARCHAR(255) PRIMARY KEY COMMENT '缓存键（MD5哈希）',
    resource_type VARCHAR(50) NOT NULL COMMENT '资源类型（ecs, rds, redis等）',
    account_name VARCHAR(100) NOT NULL COMMENT '账号名称',
    region VARCHAR(50) COMMENT '区域',
    data JSON NOT NULL COMMENT '缓存数据（JSON格式）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    expires_at TIMESTAMP NOT NULL COMMENT '过期时间',
    INDEX idx_resource_type_account (resource_type, account_name) COMMENT '资源类型和账号索引',
    INDEX idx_expires_at (expires_at) COMMENT '过期时间索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='资源查询缓存表';

-- ============================================================
-- 2. 账单明细表
-- ============================================================
CREATE TABLE IF NOT EXISTS bill_items (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    account_id VARCHAR(100) NOT NULL COMMENT '账号ID',
    billing_cycle VARCHAR(20) NOT NULL COMMENT '账期（格式：YYYY-MM）',
    
    -- 基础信息
    billing_date VARCHAR(20) COMMENT '账单日期',
    product_name VARCHAR(200) COMMENT '产品名称',
    product_code VARCHAR(50) COMMENT '产品代码',
    product_type VARCHAR(50) COMMENT '产品类型',
    subscription_type VARCHAR(50) COMMENT '订阅类型',
    
    -- 价格信息
    pricing_unit VARCHAR(50) COMMENT '计价单位',
    `usage` DECIMAL(15, 4) COMMENT '使用量',
    list_price DECIMAL(15, 4) COMMENT '列表价格',
    list_price_unit VARCHAR(50) COMMENT '列表价格单位',
    invoice_discount DECIMAL(15, 4) COMMENT '发票折扣',
    pretax_amount DECIMAL(15, 4) COMMENT '税前金额',
    
    -- 抵扣信息
    deducted_by_coupons DECIMAL(15, 4) COMMENT '优惠券抵扣',
    deducted_by_cash_coupons DECIMAL(15, 4) COMMENT '代金券抵扣',
    deducted_by_prepaid_card DECIMAL(15, 4) COMMENT '预付卡抵扣',
    payment_amount DECIMAL(15, 4) COMMENT '实付金额',
    outstanding_amount DECIMAL(15, 4) COMMENT '未付金额',
    currency VARCHAR(10) DEFAULT 'CNY' COMMENT '货币',
    
    -- 账号信息
    nick_name VARCHAR(200) COMMENT '昵称',
    resource_group VARCHAR(200) COMMENT '资源组',
    tag TEXT COMMENT '标签（JSON格式）',
    
    -- 实例信息
    instance_id VARCHAR(200) COMMENT '实例ID',
    instance_config TEXT COMMENT '实例配置',
    internet_ip VARCHAR(50) COMMENT '公网IP',
    intranet_ip VARCHAR(50) COMMENT '内网IP',
    region VARCHAR(50) COMMENT '区域',
    zone VARCHAR(50) COMMENT '可用区',
    
    -- 计费明细
    item VARCHAR(200) COMMENT '计费项',
    cost_unit VARCHAR(50) COMMENT '成本单位',
    billing_item VARCHAR(200) COMMENT '账单项',
    pip_code VARCHAR(50) COMMENT 'PIP代码',
    service_period VARCHAR(50) COMMENT '服务周期',
    service_period_unit VARCHAR(50) COMMENT '服务周期单位',
    
    -- 扩展字段（JSON格式）
    raw_data JSON COMMENT '原始数据（JSON格式）',
    
    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 唯一约束（防止重复插入）
    UNIQUE KEY uk_bill_items (account_id, billing_cycle, instance_id, billing_date, billing_item),
    
    -- 索引
    INDEX idx_account_cycle (account_id, billing_cycle) COMMENT '账号和账期索引',
    INDEX idx_billing_date (billing_date) COMMENT '账单日期索引',
    INDEX idx_product_code (product_code) COMMENT '产品代码索引',
    INDEX idx_instance_id (instance_id) COMMENT '实例ID索引',
    INDEX idx_region (region) COMMENT '区域索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='账单明细表';

-- ============================================================
-- 3. 仪表盘表
-- ============================================================
CREATE TABLE IF NOT EXISTS dashboards (
    id VARCHAR(100) PRIMARY KEY COMMENT '仪表盘ID（UUID）',
    name VARCHAR(200) NOT NULL COMMENT '仪表盘名称',
    description TEXT COMMENT '描述',
    layout VARCHAR(50) DEFAULT 'grid' COMMENT '布局类型',
    widgets JSON NOT NULL COMMENT '组件配置（JSON格式）',
    account_id VARCHAR(100) COMMENT '账号ID',
    is_shared TINYINT(1) DEFAULT 0 COMMENT '是否共享（0=否，1=是）',
    created_by VARCHAR(100) COMMENT '创建者',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_account_id (account_id) COMMENT '账号ID索引',
    INDEX idx_shared (is_shared) COMMENT '共享状态索引',
    INDEX idx_created_by (created_by) COMMENT '创建者索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='仪表盘表';

-- ============================================================
-- 4. 预算表
-- ============================================================
CREATE TABLE IF NOT EXISTS budgets (
    id VARCHAR(100) PRIMARY KEY COMMENT '预算ID（UUID）',
    name VARCHAR(200) NOT NULL COMMENT '预算名称',
    amount DECIMAL(15, 4) NOT NULL COMMENT '预算金额',
    period VARCHAR(50) NOT NULL COMMENT '周期（monthly, quarterly, yearly）',
    type VARCHAR(50) NOT NULL COMMENT '类型（total, by_service, by_tag）',
    start_date DATE NOT NULL COMMENT '开始日期',
    end_date DATE NOT NULL COMMENT '结束日期',
    tag_filter JSON COMMENT '标签过滤器（JSON格式）',
    service_filter JSON COMMENT '服务过滤器（JSON格式）',
    alerts JSON COMMENT '告警配置（JSON格式）',
    account_id VARCHAR(100) COMMENT '账号ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_account_id (account_id) COMMENT '账号ID索引',
    INDEX idx_period (period, start_date, end_date) COMMENT '周期和日期索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='预算表';

-- ============================================================
-- 5. 预算执行记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS budget_records (
    id VARCHAR(100) PRIMARY KEY COMMENT '记录ID（UUID）',
    budget_id VARCHAR(100) NOT NULL COMMENT '预算ID',
    date DATE NOT NULL COMMENT '日期',
    spent DECIMAL(15, 4) NOT NULL COMMENT '已花费金额',
    predicted DECIMAL(15, 4) COMMENT '预测金额',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (budget_id) REFERENCES budgets(id) ON DELETE CASCADE,
    UNIQUE KEY uk_budget_date (budget_id, date) COMMENT '预算和日期唯一约束',
    INDEX idx_budget_id (budget_id) COMMENT '预算ID索引',
    INDEX idx_date (date) COMMENT '日期索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='预算执行记录表';

-- ============================================================
-- 6. 预算告警记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS budget_alerts (
    id VARCHAR(100) PRIMARY KEY COMMENT '告警ID（UUID）',
    budget_id VARCHAR(100) NOT NULL COMMENT '预算ID',
    threshold DECIMAL(5, 2) NOT NULL COMMENT '阈值（百分比）',
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '触发时间',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态（pending, sent, resolved）',
    message TEXT COMMENT '告警消息',
    FOREIGN KEY (budget_id) REFERENCES budgets(id) ON DELETE CASCADE,
    INDEX idx_budget_id (budget_id) COMMENT '预算ID索引',
    INDEX idx_status (status) COMMENT '状态索引',
    INDEX idx_triggered_at (triggered_at) COMMENT '触发时间索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='预算告警记录表';

-- ============================================================
-- 7. 告警规则表
-- ============================================================
CREATE TABLE IF NOT EXISTS alert_rules (
    id VARCHAR(100) PRIMARY KEY COMMENT '规则ID（UUID）',
    name VARCHAR(200) NOT NULL COMMENT '规则名称',
    description TEXT COMMENT '描述',
    type VARCHAR(50) NOT NULL COMMENT '类型（cost, usage, idle等）',
    severity VARCHAR(20) NOT NULL COMMENT '严重程度（low, medium, high, critical）',
    enabled TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用（0=否，1=是）',
    condition_config JSON NOT NULL COMMENT '条件配置（JSON格式）',
    threshold DECIMAL(15, 4) COMMENT '阈值',
    metric VARCHAR(100) COMMENT '指标名称',
    account_id VARCHAR(100) COMMENT '账号ID',
    tag_filter JSON COMMENT '标签过滤器（JSON格式）',
    service_filter JSON COMMENT '服务过滤器（JSON格式）',
    notification_config JSON COMMENT '通知配置（JSON格式）',
    check_interval INT DEFAULT 60 COMMENT '检查间隔（秒）',
    cooldown_period INT DEFAULT 300 COMMENT '冷却期（秒）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_account_id (account_id) COMMENT '账号ID索引',
    INDEX idx_enabled (enabled) COMMENT '启用状态索引',
    INDEX idx_type (type) COMMENT '类型索引',
    INDEX idx_severity (severity) COMMENT '严重程度索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='告警规则表';

-- ============================================================
-- 8. 告警记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS alerts (
    id VARCHAR(100) PRIMARY KEY COMMENT '告警ID（UUID）',
    rule_id VARCHAR(100) COMMENT '规则ID（允许NULL，规则删除后保留告警记录）',
    rule_name VARCHAR(200) NOT NULL COMMENT '规则名称',
    severity VARCHAR(20) NOT NULL COMMENT '严重程度',
    status VARCHAR(20) NOT NULL DEFAULT 'triggered' COMMENT '状态（triggered, acknowledged, resolved, closed）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    message TEXT COMMENT '消息内容',
    metric_value DECIMAL(15, 4) COMMENT '指标值',
    threshold DECIMAL(15, 4) COMMENT '阈值',
    account_id VARCHAR(100) COMMENT '账号ID',
    resource_id VARCHAR(200) COMMENT '资源ID',
    resource_type VARCHAR(50) COMMENT '资源类型',
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '触发时间',
    acknowledged_at TIMESTAMP NULL COMMENT '确认时间',
    resolved_at TIMESTAMP NULL COMMENT '解决时间',
    resolved_by VARCHAR(100) COMMENT '解决者',
    notes TEXT COMMENT '备注',
    FOREIGN KEY (rule_id) REFERENCES alert_rules(id) ON DELETE SET NULL,
    INDEX idx_rule_id (rule_id) COMMENT '规则ID索引',
    INDEX idx_status (status) COMMENT '状态索引',
    INDEX idx_account_id (account_id) COMMENT '账号ID索引',
    INDEX idx_resource (resource_type, resource_id) COMMENT '资源索引',
    INDEX idx_triggered_at (triggered_at) COMMENT '触发时间索引',
    INDEX idx_severity (severity) COMMENT '严重程度索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='告警记录表';

-- ============================================================
-- 9. 虚拟标签表
-- ============================================================
CREATE TABLE IF NOT EXISTS virtual_tags (
    id VARCHAR(100) PRIMARY KEY COMMENT '标签ID（UUID）',
    name VARCHAR(200) NOT NULL COMMENT '标签名称',
    tag_key VARCHAR(100) NOT NULL COMMENT '标签键',
    tag_value VARCHAR(200) NOT NULL COMMENT '标签值',
    description TEXT COMMENT '描述',
    priority INT DEFAULT 0 COMMENT '优先级（数字越大优先级越高）',
    account_id VARCHAR(100) COMMENT '账号ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_account_id (account_id) COMMENT '账号ID索引',
    INDEX idx_tag_key (tag_key) COMMENT '标签键索引',
    INDEX idx_priority (priority) COMMENT '优先级索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='虚拟标签表';

-- ============================================================
-- 10. 标签规则表
-- ============================================================
CREATE TABLE IF NOT EXISTS tag_rules (
    id VARCHAR(100) PRIMARY KEY COMMENT '规则ID（UUID）',
    tag_id VARCHAR(100) NOT NULL COMMENT '标签ID',
    field VARCHAR(100) NOT NULL COMMENT '字段名',
    operator VARCHAR(20) NOT NULL COMMENT '操作符（equals, contains, starts_with, ends_with, regex等）',
    pattern VARCHAR(500) NOT NULL COMMENT '匹配模式',
    priority INT DEFAULT 0 COMMENT '优先级',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (tag_id) REFERENCES virtual_tags(id) ON DELETE CASCADE,
    INDEX idx_tag_id (tag_id) COMMENT '标签ID索引',
    INDEX idx_field (field) COMMENT '字段索引',
    INDEX idx_priority (priority) COMMENT '优先级索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='标签规则表';

-- ============================================================
-- 11. 标签匹配缓存表
-- ============================================================
CREATE TABLE IF NOT EXISTS tag_matches (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    tag_id VARCHAR(100) NOT NULL COMMENT '标签ID',
    resource_id VARCHAR(200) NOT NULL COMMENT '资源ID',
    resource_type VARCHAR(50) NOT NULL COMMENT '资源类型',
    account_id VARCHAR(100) NOT NULL COMMENT '账号ID',
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '匹配时间',
    FOREIGN KEY (tag_id) REFERENCES virtual_tags(id) ON DELETE CASCADE,
    UNIQUE KEY uk_tag_resource (tag_id, resource_id, resource_type, account_id) COMMENT '标签和资源唯一约束',
    INDEX idx_tag_id (tag_id) COMMENT '标签ID索引',
    INDEX idx_resource (resource_type, resource_id) COMMENT '资源索引',
    INDEX idx_account_id (account_id) COMMENT '账号ID索引',
    INDEX idx_matched_at (matched_at) COMMENT '匹配时间索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='标签匹配缓存表';

-- ============================================================
-- 12. 资源监控数据表（统一设计）
-- ============================================================
CREATE TABLE IF NOT EXISTS resource_monitoring_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    resource_type VARCHAR(50) NOT NULL COMMENT '资源类型（ecs, rds, redis等）',
    resource_id VARCHAR(200) NOT NULL COMMENT '资源ID',
    account_name VARCHAR(100) NOT NULL COMMENT '账号名称',
    region VARCHAR(50) COMMENT '区域',
    metric_name VARCHAR(100) NOT NULL COMMENT '指标名称',
    metric_value DECIMAL(15, 4) COMMENT '指标值',
    timestamp TIMESTAMP NOT NULL COMMENT '时间戳',
    metadata JSON COMMENT '元数据（JSON格式）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_resource (resource_type, resource_id) COMMENT '资源索引',
    INDEX idx_account (account_name) COMMENT '账号索引',
    INDEX idx_timestamp (timestamp) COMMENT '时间戳索引',
    INDEX idx_metric (metric_name, timestamp) COMMENT '指标和时间戳索引',
    INDEX idx_resource_metric_time (resource_type, resource_id, metric_name, timestamp) COMMENT '复合索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='资源监控数据表';

-- ============================================================
-- 13. 成本分配表（可选，如果需要）
-- ============================================================
CREATE TABLE IF NOT EXISTS cost_allocation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    account_id VARCHAR(100) NOT NULL COMMENT '账号ID',
    billing_cycle VARCHAR(20) NOT NULL COMMENT '账期',
    allocation_rule_id VARCHAR(100) COMMENT '分配规则ID',
    source_resource_id VARCHAR(200) COMMENT '源资源ID',
    target_resource_id VARCHAR(200) COMMENT '目标资源ID',
    allocated_cost DECIMAL(15, 4) NOT NULL COMMENT '分配成本',
    allocation_method VARCHAR(50) COMMENT '分配方法（proportional, fixed, custom）',
    allocation_metadata JSON COMMENT '分配元数据（JSON格式）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_account_cycle (account_id, billing_cycle) COMMENT '账号和账期索引',
    INDEX idx_source_resource (source_resource_id) COMMENT '源资源索引',
    INDEX idx_target_resource (target_resource_id) COMMENT '目标资源索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='成本分配表';

-- ============================================================
-- 完成
-- ============================================================
SELECT 'Database schema created successfully!' AS status;

