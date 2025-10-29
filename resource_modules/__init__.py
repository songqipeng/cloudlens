#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resource_modules/__init__.py
资源分析模块包初始化文件
"""

__version__ = "1.0.0"
__author__ = "阿里云资源分析工具"

# 支持的资源类型
SUPPORTED_RESOURCES = [
    'ecs',      # 弹性计算服务
    'rds',      # 云数据库RDS
    'redis',    # 云数据库Redis
    'oss',      # 对象存储服务
    'slb',      # 负载均衡
    'eip',      # 弹性公网IP
    'nas',      # 文件存储NAS
    'ack',      # 容器服务Kubernetes版
    'eci',      # 弹性容器实例
    'emr',      # 大数据服务
    'arms',     # 应用监控
    'sls',      # 日志服务
]

# 资源类型描述
RESOURCE_DESCRIPTIONS = {
    'ecs': '弹性计算服务 - 云服务器实例',
    'rds': '云数据库RDS - 关系型数据库',
    'redis': '云数据库Redis - 缓存数据库',
    'oss': '对象存储服务 - 文件存储',
    'slb': '负载均衡 - 流量分发',
    'eip': '弹性公网IP - 公网访问',
    'nas': '文件存储NAS - 共享文件系统',
    'ack': '容器服务Kubernetes版 - 容器编排',
    'eci': '弹性容器实例 - 无服务器容器',
    'emr': '大数据服务 - 大数据计算',
    'arms': '应用监控 - 应用性能监控',
    'sls': '日志服务 - 日志收集分析',
}
