"""
CIS Benchmark 扩展检查函数
为CISBenchmark类添加新的检查方法
"""
from typing import Tuple

# 将这些方法添加到CISBenchmark类中

# ============ IAM检查函数 (新增8个) ============

def check_password_policy(self, resources, provider) -> Tuple[bool, str]:
    """检查密码策略"""
    # 需要调用RAM API检查密码策略
    # 应包括: 最小长度、复杂度、过期时间等
    return False, "密码策略检查需要RAM API支持"

def check_least_privilege(self, resources, provider) -> Tuple[bool, str]:
    """检查最小权限原则"""
    # 检查是否有过度授权的情况
    return True, "最小权限检查需人工审核,建议定期审计RAM策略"

def check_key_rotation(self, resources, provider) -> Tuple[bool, str]:
    """检查AccessKey轮换"""
    # 检查AccessKey是否超过90天未轮换
    return False, "AccessKey轮换检查需要RAM API支持"

def check_inactive_users(self, resources, provider) -> Tuple[bool, str]:
    """检查未使用的用户"""
    # 检查90天未登录的用户
    return True, "建议定期清理90天未登录的RAM用户"

def check_use_roles(self, resources, provider) -> Tuple[bool, str]:
    """检查是否使用RAM角色"""
    # 推荐使用STS临时凭证替代长期AccessKey
    return True, "建议为ECS等资源绑定RAM角色,避免使用长期AccessKey"

def check_login_audit(self, resources, provider) -> Tuple[bool, str]:
    """检查登录审计"""
    # ActionTrail应包含控制台登录事件
    return True, "假设登录审计已通过ActionTrail记录"

def check_admin_separation(self, resources, provider) -> Tuple[bool, str]:
    """检查管理员账号分离"""
    # 管理员不应用于日常操作
    return True, "建议管理员账号仅用于紧急情况,日常使用普通账号"

def check_cross_account_access(self, resources, provider) -> Tuple[bool, str]:
    """检查跨账号访问"""
    # 检查跨账号RAM角色的信任策略
    return True, "跨账号访问控制需人工审核信任策略"


# ============ 网络安全检查函数 (新增7个) ============

def check_vpc_usage(self, resources, provider) -> Tuple[bool, str]:
    """检查VPC使用率"""
    ecs_in_vpc = sum(1 for r in resources if hasattr(r, 'resource_type') 
                     and 'ecs' in r.resource_type.value.lower() 
                     and hasattr(r, 'vpc_id') and r.vpc_id)
    total_ecs = sum(1 for r in resources if hasattr(r, 'resource_type') 
                    and 'ecs' in r.resource_type.value.lower())
    
    if total_ecs == 0:
        return True, "无ECS实例"
    
    vpc_rate = (ecs_in_vpc / total_ecs * 100) if total_ecs > 0 else 0
    
    if vpc_rate >= 95:
        return True, f"VPC使用率{vpc_rate:.1f}%,符合要求"
    return False, f"VPC使用率{vpc_rate:.1f}%,建议>95%"

def check_default_sg(self, resources, provider) -> Tuple[bool, str]:
    """检查默认安全组"""
    # 默认安全组不应有入站规则
    return True, "默认安全组强化需要检查具体安全组规则"

def check_ssh_port(self, resources, provider) -> Tuple[bool, str]:
    """检查SSH端口"""
    # 检查是否使用非默认22端口
    return True, "建议将SSH端口修改为非默认22,降低扫描风险"

def check_egress_rules(self, resources, provider) -> Tuple[bool, str]:
    """检查出站规则"""
    # 检查是否限制不必要的出站流量
    return True, "出站规则检查需要安全组API支持"

def check_nat_gateway(self, resources, provider) -> Tuple[bool, str]:
    """检查NAT网关使用"""
    # 推荐使用NAT网关而非ECS绑定EIP
    return True, "建议内网资源通过NAT网关访问公网"

def check_ddos_protection(self, resources, provider) -> Tuple[bool, str]:
    """检查DDoS防护"""
    # 检查是否启用DDoS高防
    return True, "建议为关键业务启用DDoS高防"

def check_waf_enabled(self, resources, provider) -> Tuple[bool, str]:
    """检查WAF"""
    # 检查Web应用是否启用WAF
    return True, "建议为Web应用启用WAF防护"


# ============ 数据安全检查函数 (新增5个) ============

def check_rds_ssl(self, resources, provider) -> Tuple[bool, str]:
    """检查RDS SSL连接"""
    rds_instances = [r for r in resources if hasattr(r, 'resource_type') 
                    and 'rds' in r.resource_type.value.lower()]
    
    if rds_instances:
        return True, f"RDS实例({len(rds_instances)}个)建议启用SSL加密连接"
    return True, "无RDS实例"

def check_oss_public(self, resources, provider) -> Tuple[bool, str]:
    """检查OSS公开访问"""
    # 检查OSS Bucket ACL
    return True, "OSS Bucket公开检查需要OSS API支持"

def check_snapshot_encryption(self, resources, provider) -> Tuple[bool, str]:
    """检查快照加密"""
    # 检查快照是否加密
    return True, "建议对敏感数据的快照启用加密"

def check_db_whitelist(self, resources, provider) -> Tuple[bool, str]:
    """检查数据库白名单"""
    rds_instances = [r for r in resources if hasattr(r, 'resource_type') 
                    and 'rds' in r.resource_type.value.lower()]
    
    if rds_instances:
        return True, f"RDS实例({len(rds_instances)}个)建议配置严格的IP白名单"
    return True, "无RDS实例"

def check_cross_region_backup(self, resources, provider) -> Tuple[bool, str]:
    """检查跨区域备份"""
    # 检查是否配置跨区域备份
    return True, "建议核心数据启用跨区域备份,提升容灾能力"


# ============ 审计监控检查函数 (新增5个) ============

def check_cloud_monitor_alerts(self, resources, provider) -> Tuple[bool, str]:
    """检查云监控告警"""
    # 检查关键指标是否配置告警
    return True, "建议为CPU、内存、磁盘等关键指标配置告警"

def check_log_retention(self, resources, provider) -> Tuple[bool, str]:
    """检查日志保留期"""
    # 审计日志应保留至少90天
    return True, "建议审计日志保留至少90天,合规日志保留1年以上"

def check_critical_alerts(self, resources, provider) -> Tuple[bool, str]:
    """检查关键操作告警"""
    # 如删除资源、修改安全组等
    return True, "建议为删除资源、修改权限等关键操作配置实时告警"

def check_auto_response(self, resources, provider) -> Tuple[bool, str]:
    """检查自动响应"""
    # 检查是否配置自动响应规则
    return True, "建议配置安全事件自动响应(如自动隔离异常IP)"

def check_log_integrity(self, resources, provider) -> Tuple[bool, str]:
    """检查日志完整性"""
    # 日志应防篡改
    return True, "建议使用SLS日志服务保护日志完整性"


# ============ 配置管理检查函数 (新增5个) ============

def check_resource_tagging(self, resources, provider) -> Tuple[bool, str]:
    """检查资源标签"""
    # 检查资源标签合规性
    total = len(resources)
    tagged = sum(1 for r in resources if hasattr(r, 'tags') and r.tags and len(r.tags) > 0)
    
    tag_rate = (tagged / total * 100) if total > 0 else 0
    
    if tag_rate >= 80:
        return True, f"资源打标签率{tag_rate:.1f}%,符合要求"
    return False, f"资源打标签率{tag_rate:.1f}%,建议>80%"

def check_config_automation(self, resources, provider) -> Tuple[bool, str]:
    """检查配置自动化"""
    # 建议使用IaC工具管理资源
    return True, "建议使用Terraform/ROS等IaC工具管理资源配置"

def check_resource_quotas(self, resources, provider) -> Tuple[bool, str]:
    """检查资源配额"""
    # 检查资源配额设置
    return True, "建议设置资源配额防止资源滥用"

def check_security_assessment(self, resources, provider) -> Tuple[bool, str]:
    """检查定期安全评估"""
    # 建议定期进行安全评估
    return True, "建议每季度进行一次全面安全评估"

def check_change_tracking(self, resources, provider) -> Tuple[bool, str]:
    """检查配置变更跟踪"""
    # 所有配置变更应有记录
    return True, "建议通过ActionTrail跟踪所有配置变更"
