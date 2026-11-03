-- 框架合同规则（多版本，按账号绑定）
CREATE TABLE IF NOT EXISTS framework_contracts (
    id VARCHAR(64) PRIMARY KEY,
    account_name VARCHAR(100) NOT NULL,
    title VARCHAR(255) DEFAULT NULL,
    contract_no VARCHAR(128) DEFAULT NULL,
    cloud_uid VARCHAR(64) DEFAULT NULL,
    effective_from DATE DEFAULT NULL,
    effective_to DATE DEFAULT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    priority INT NOT NULL DEFAULT 0,
    rules_json JSON NOT NULL,
    source_pdf_path VARCHAR(512) DEFAULT NULL,
    source_pdf_name VARCHAR(255) DEFAULT NULL,
    parse_meta_json JSON DEFAULT NULL,
    notes TEXT DEFAULT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_fc_account_status (account_name, status),
    INDEX idx_fc_dates (effective_from, effective_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
