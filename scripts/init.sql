-- ============================================================
-- CloudLens MySQL 数据库初始化脚本
-- 用于Docker容器自动初始化
-- ============================================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS cloudlens CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE cloudlens;

-- 执行主schema文件（通过docker-entrypoint-initdb.d自动执行）
-- 这里只做数据库创建，表结构由migrations/init_mysql_schema.sql创建

SELECT 'Database cloudlens created successfully!' AS status;
