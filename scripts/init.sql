-- ============================================================
-- CloudLens MySQL 数据库初始化脚本
-- 用于Docker容器自动初始化
-- 此脚本会在MySQL容器首次启动时自动执行
-- ============================================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS cloudlens CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE cloudlens;

-- 注意：表结构由 migrations/init_mysql_schema.sql 创建
-- 此脚本只负责创建数据库，表结构会在容器启动后通过迁移脚本创建

-- 修改用户认证插件为 mysql_native_password，解决 caching_sha2_password 需要SSL连接的问题
ALTER USER 'cloudlens'@'%' IDENTIFIED WITH mysql_native_password BY 'cloudlens123';
FLUSH PRIVILEGES;

SELECT 'Database cloudlens created successfully!' AS status;
