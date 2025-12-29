-- ============================================================
-- Migration: 001 - Remove deprecated budget_records table
-- Description: 删除已废弃的budget_records表，该表数据不准确且已不再使用
-- Author: CloudLens Team
-- Date: 2024-12-29
-- ============================================================

USE cloudlens;

-- ============================================================
-- UP Migration: 删除废弃表
-- ============================================================

-- 1. 备份现有数据（可选，如需保留历史数据）
CREATE TABLE IF NOT EXISTS budget_records_backup_20241229 AS
SELECT * FROM budget_records;

SELECT CONCAT('Backed up ', COUNT(*), ' records from budget_records') AS backup_info
FROM budget_records;

-- 2. 删除废弃表
DROP TABLE IF EXISTS budget_records;

SELECT 'budget_records table dropped successfully' AS status;

-- 3. 创建或更新schema_migrations表
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INT PRIMARY KEY COMMENT '迁移版本号',
    name VARCHAR(255) NOT NULL COMMENT '迁移名称',
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '应用时间',
    description TEXT COMMENT '迁移描述'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据库迁移版本记录表';

-- 4. 记录迁移版本
INSERT INTO schema_migrations (version, name, description)
VALUES (
    1,
    '001_remove_budget_records',
    'Remove deprecated budget_records table which contains inaccurate data and is no longer used'
)
ON DUPLICATE KEY UPDATE
    applied_at = CURRENT_TIMESTAMP;

SELECT * FROM schema_migrations;

-- ============================================================
-- DOWN Migration: 回滚操作（恢复表结构，不含数据）
-- ============================================================

-- 如需回滚，执行以下SQL：
/*
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='预算执行记录表（已废弃）';

-- 如果需要恢复数据
INSERT INTO budget_records SELECT * FROM budget_records_backup_20241229;

-- 删除迁移记录
DELETE FROM schema_migrations WHERE version = 1;
*/

-- ============================================================
-- 验证
-- ============================================================

-- 验证表已删除
SELECT
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS: budget_records table successfully removed'
        ELSE 'FAIL: budget_records table still exists'
    END AS verification_result
FROM information_schema.tables
WHERE table_schema = 'cloudlens'
  AND table_name = 'budget_records';

-- 验证备份表存在
SELECT
    CASE
        WHEN COUNT(*) > 0 THEN 'PASS: Backup table exists'
        ELSE 'WARNING: Backup table not found'
    END AS backup_verification
FROM information_schema.tables
WHERE table_schema = 'cloudlens'
  AND table_name = 'budget_records_backup_20241229';

-- ============================================================
-- 完成
-- ============================================================
SELECT 'Migration 001 completed successfully!' AS status;
