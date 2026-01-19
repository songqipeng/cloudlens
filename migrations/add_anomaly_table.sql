-- ============================================================
-- 成本异常检测表
-- ============================================================

USE cloudlens;

CREATE TABLE IF NOT EXISTS cost_anomalies (
    id VARCHAR(200) PRIMARY KEY COMMENT '异常ID（account_id-date）',
    account_id VARCHAR(100) NOT NULL COMMENT '账号ID',
    date VARCHAR(20) NOT NULL COMMENT '日期（YYYY-MM-DD）',
    current_cost DECIMAL(15, 4) NOT NULL COMMENT '当前成本',
    baseline_cost DECIMAL(15, 4) NOT NULL COMMENT '基线成本',
    deviation_pct DECIMAL(10, 2) NOT NULL COMMENT '偏差百分比',
    severity VARCHAR(20) NOT NULL COMMENT '严重程度（low/medium/high/critical）',
    root_cause TEXT COMMENT '根因分析',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_account_id (account_id) COMMENT '账号ID索引',
    INDEX idx_date (date) COMMENT '日期索引',
    INDEX idx_severity (severity) COMMENT '严重程度索引',
    INDEX idx_account_date (account_id, date) COMMENT '账号和日期复合索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='成本异常检测表';

SELECT 'Cost anomalies table created successfully!' AS status;
