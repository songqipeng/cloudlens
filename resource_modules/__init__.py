#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resource_modules/__init__.py
资源分析模块包初始化文件
"""

__version__ = "1.0.0"
__author__ = "阿里云资源分析工具"

# 支持的资源类型（已实现）
SUPPORTED_RESOURCES = [
    "ecs",  # 弹性计算服务 ✅
    "rds",  # 云数据库RDS ✅
    "redis",  # 云数据库Redis ✅
    "mongodb",  # 云数据库MongoDB ✅
    "clickhouse",  # 云数据库ClickHouse ✅
    "oss",  # 对象存储服务 ✅
    "slb",  # 负载均衡 ✅
    "eip",  # 弹性公网IP ✅
    "nas",  # 文件存储NAS ✅
    "ack",  # 容器服务Kubernetes版 ✅
    "eci",  # 弹性容器实例 ✅
    "polardb",  # 云原生数据库PolarDB ✅
    "disk",  # 云盘 ✅
]

# 计划中的资源类型
PLANNED_RESOURCES = [
    "vpn",  # VPN网关
    "nat",  # NAT网关
    "cdn",  # 内容分发网络
    "fc",  # 函数计算
    "analyticdb",  # 分析型数据库
    "emr",  # 大数据服务
    "arms",  # 应用监控
    "sls",  # 日志服务
]

# 资源类型描述
RESOURCE_DESCRIPTIONS = {
    # 已实现的资源类型
    "ecs": "弹性计算服务 - 云服务器实例",
    "rds": "云数据库RDS - 关系型数据库",
    "redis": "云数据库Redis - 缓存数据库",
    "mongodb": "云数据库MongoDB - 文档数据库",
    "clickhouse": "云数据库ClickHouse - 分析型数据库",
    "oss": "对象存储服务 - 文件存储",
    "slb": "负载均衡 - 流量分发",
    "eip": "弹性公网IP - 公网访问",
    "nas": "文件存储NAS - 共享文件系统",
    "ack": "容器服务Kubernetes版 - 容器编排",
    "eci": "弹性容器实例 - 无服务器容器",
    "polardb": "云原生数据库PolarDB - 分布式数据库",
    "disk": "云盘 - 块存储",
    # 计划中的资源类型
    "vpn": "VPN网关 - 虚拟专用网络",
    "nat": "NAT网关 - 网络地址转换",
    "cdn": "内容分发网络 - CDN加速",
    "fc": "函数计算 - Serverless函数",
    "analyticdb": "分析型数据库 - 实时分析",
    "emr": "大数据服务 - 大数据计算",
    "arms": "应用监控 - 应用性能监控",
    "sls": "日志服务 - 日志收集分析",
}

# 导入所有分析器模块以触发注册
from . import (
    ack_analyzer,
    cdn_analyzer,
    clickhouse_analyzer,
    cost_analyzer,
    discount_analyzer,
    disk_analyzer,
    dns_analyzer,
    eci_analyzer,
    ecs_analyzer,
    eip_analyzer,
    mongodb_analyzer,
    nas_analyzer,
    nat_analyzer,
    network_analyzer,
    oss_analyzer,
    polardb_analyzer,
    rds_analyzer,
    redis_analyzer,
    slb_analyzer,
    vpc_analyzer,
    vpn_analyzer,
)
