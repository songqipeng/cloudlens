-- ============================================================
-- AI Chatbot 相关表
-- 包含：LLM配置、对话会话、对话消息
-- ============================================================

USE cloudlens;

-- LLM 配置表（存储各AI提供商的API密钥）
CREATE TABLE IF NOT EXISTS llm_configs (
    provider VARCHAR(50) PRIMARY KEY COMMENT 'LLM提供商(claude/openai/deepseek)',
    api_key_encrypted TEXT NOT NULL COMMENT '加密的API密钥',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='LLM配置表';

-- 对话会话表
CREATE TABLE IF NOT EXISTS chat_sessions (
    id VARCHAR(100) PRIMARY KEY COMMENT '会话ID（UUID）',
    user_id VARCHAR(100) COMMENT '用户ID（可选，用于多用户场景）',
    account_id VARCHAR(100) COMMENT '账号ID',
    title VARCHAR(500) COMMENT '会话标题（自动生成）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id) COMMENT '用户ID索引',
    INDEX idx_account_id (account_id) COMMENT '账号ID索引',
    INDEX idx_created_at (created_at) COMMENT '创建时间索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI对话会话表';

-- 对话消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id VARCHAR(100) PRIMARY KEY COMMENT '消息ID（UUID）',
    session_id VARCHAR(100) NOT NULL COMMENT '会话ID',
    role VARCHAR(20) NOT NULL COMMENT '角色（user/assistant/system）',
    content TEXT NOT NULL COMMENT '消息内容',
    metadata JSON COMMENT '元数据（JSON格式，存储token数、模型等信息）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id) COMMENT '会话ID索引',
    INDEX idx_created_at (created_at) COMMENT '创建时间索引',
    INDEX idx_role (role) COMMENT '角色索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI对话消息表';

SELECT 'Chatbot tables created successfully!' AS status;
