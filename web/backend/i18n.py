"""
后端国际化翻译模块
提供中英文翻译支持
"""

from typing import Literal

Locale = Literal["zh", "en"]

# 翻译字典
TRANSLATIONS = {
    "zh": {
        "security": {
            "public_exposure": {
                "title": "公网暴露检测",
                "description_failed": "检测到有资源暴露在公网，存在安全风险",
                "description_passed": "未发现公网暴露的资源",
                "recommendation": "评估是否真的需要公网访问，配置安全组白名单限制访问源，考虑使用 NAT 网关或 SLB",
            },
            "stopped_instances": {
                "title": "停止实例检测",
                "description": "检测到长期停止的实例，仍产生磁盘费用",
                "recommendation": "评估这些实例是否还需要，如果不需要请及时释放以节省成本",
            },
            "tag_coverage": {
                "title": "标签覆盖率检查",
                "description_failed": "标签覆盖率不足，影响资源管理和成本分配",
                "description_passed": "标签覆盖率良好",
                "recommendation": "为所有资源添加必要的标签，建议至少包含：环境(env)、项目(project)、负责人(owner)",
            },
            "disk_encryption": {
                "title": "磁盘加密检查",
                "description_failed": "部分实例未启用磁盘加密，存在数据安全风险",
                "description_passed": "所有实例均已启用磁盘加密",
                "recommendation": "为所有实例启用磁盘加密以保护数据安全，符合合规要求",
            },
            "preemptible_instances": {
                "title": "抢占式实例检查",
                "description": "检测到抢占式实例，可能随时被释放",
                "recommendation": "评估业务是否适合使用抢占式实例，对于关键业务建议使用包年包月实例",
            },
            "eip_usage": {
                "title": "EIP使用情况检查",
                "description_failed": "检测到未绑定的EIP，产生不必要的费用",
                "description_passed": "EIP使用情况良好",
                "recommendation": "发现 {unbound} 个未绑定的EIP，建议释放以节省成本",
            },
            "score_deductions": {
                "public_exposure": "公网暴露 {count} 个资源",
                "stopped_instances": "长期停止 {count} 个实例",
                "tag_coverage": "标签覆盖率仅 {coverage}%",
                "disk_encryption": "磁盘加密率仅 {rate}%",
                "preemptible_instances": "抢占式实例 {count} 个",
                "eip_unbound": "未绑定EIP率 {rate}%",
            },
        },
        "optimization": {
            "idle_resources": {
                "category": "成本优化",
                "title": "闲置资源优化",
                "description": "发现 {count} 个闲置资源，CPU和内存利用率极低，建议释放或降配",
                "recommendation": "评估资源使用情况，如确实不需要可释放，如需保留可考虑降配以节省成本",
            },
            "stopped_instances": {
                "category": "成本优化",
                "title": "停止实例优化",
                "description": "发现 {count} 个长期停止的实例，仍产生磁盘费用",
                "recommendation": "评估是否需要这些实例，如不需要建议释放以节省磁盘费用",
            },
            "unbound_eips": {
                "category": "成本优化",
                "title": "未绑定EIP优化",
                "description": "发现 {count} 个未绑定的EIP，产生不必要的费用",
                "recommendation": "未绑定的EIP持续产生费用，建议释放以节省成本",
            },
            "missing_tags": {
                "category": "资源管理",
                "title": "标签完善",
                "description": "发现 {count} 个资源缺少标签，影响成本分摊和资源管理",
                "recommendation": "为资源添加标签（如：Environment、Project、Owner等）以便于成本分摊和资源管理",
            },
            "spec_downgrade": {
                "category": "成本优化",
                "title": "规格降配建议",
                "description": "发现 {count} 个实例可降配，资源利用率较低",
                "recommendation": "根据实际使用情况降配实例规格，可节省约30%成本",
            },
            "public_exposure": {
                "category": "安全优化",
                "title": "公网暴露优化",
                "description": "发现 {count} 个资源暴露在公网",
                "recommendation": "评估是否真的需要公网访问，配置安全组白名单",
            },
            "disk_encryption": {
                "category": "安全优化",
                "title": "磁盘加密优化",
                "description": "发现 {count} 个实例未启用磁盘加密",
                "recommendation": "为所有实例启用磁盘加密以保护数据安全，符合合规要求",
            },
        },
    },
    "en": {
        "security": {
            "public_exposure": {
                "title": "Public Exposure Detection",
                "description_failed": "Resources exposed to the public network detected, security risk exists",
                "description_passed": "No resources exposed to the public network found",
                "recommendation": "Evaluate if public network access is really needed, configure security group whitelist to limit access sources, consider using NAT gateway or SLB",
            },
            "stopped_instances": {
                "title": "Stopped Instances Detection",
                "description": "Long-term stopped instances detected, still incurring disk costs",
                "recommendation": "Evaluate if these instances are still needed, release them promptly if not needed to save costs",
            },
            "tag_coverage": {
                "title": "Tag Coverage Check",
                "description_failed": "Insufficient tag coverage, affecting resource management and cost allocation",
                "description_passed": "Tag coverage is good",
                "recommendation": "Add necessary tags to all resources, recommend at least: environment(env), project(project), owner(owner)",
            },
            "disk_encryption": {
                "title": "Disk Encryption Check",
                "description_failed": "Some instances do not have disk encryption enabled, data security risk exists",
                "description_passed": "All instances have disk encryption enabled",
                "recommendation": "Enable disk encryption for all instances to protect data security and meet compliance requirements",
            },
            "preemptible_instances": {
                "title": "Preemptible Instances Check",
                "description": "Preemptible instances detected, may be released at any time",
                "recommendation": "Evaluate if the business is suitable for preemptible instances, for critical business recommend using subscription instances",
            },
            "eip_usage": {
                "title": "EIP Usage Check",
                "description_failed": "Unbound EIPs detected, incurring unnecessary costs",
                "description_passed": "EIP usage is good",
                "recommendation": "Found {unbound} unbound EIPs, recommend releasing them to save costs",
            },
            "score_deductions": {
                "public_exposure": "Public exposure {count} resources",
                "stopped_instances": "Long-term stopped {count} instances",
                "tag_coverage": "Tag coverage only {coverage}%",
                "disk_encryption": "Disk encryption rate only {rate}%",
                "preemptible_instances": "Preemptible instances {count}",
                "eip_unbound": "Unbound EIP rate {rate}%",
            },
        },
        "optimization": {
            "idle_resources": {
                "category": "Cost Optimization",
                "title": "Idle Resources Optimization",
                "description": "Found {count} idle resources with extremely low CPU and memory utilization, recommend releasing or downgrading",
                "recommendation": "Evaluate resource usage, release if not needed, or consider downgrading to save costs if retention is required",
            },
            "stopped_instances": {
                "category": "Cost Optimization",
                "title": "Stopped Instances Optimization",
                "description": "Found {count} long-term stopped instances, still incurring disk costs",
                "recommendation": "Evaluate if these instances are still needed, release them to save disk costs if not needed",
            },
            "unbound_eips": {
                "category": "Cost Optimization",
                "title": "Unbound EIP Optimization",
                "description": "Found {count} unbound EIPs, incurring unnecessary costs",
                "recommendation": "Unbound EIPs continuously incur costs, recommend releasing them to save costs",
            },
            "missing_tags": {
                "category": "Resource Management",
                "title": "Tag Completion",
                "description": "Found {count} resources missing tags, affecting cost allocation and resource management",
                "recommendation": "Add tags to resources (e.g., Environment, Project, Owner) for cost allocation and resource management",
            },
            "spec_downgrade": {
                "category": "Cost Optimization",
                "title": "Spec Downgrade Suggestion",
                "description": "Found {count} instances can be downgraded, resource utilization is low",
                "recommendation": "Downgrade instance specifications based on actual usage, can save about 30% costs",
            },
            "public_exposure": {
                "category": "Security Optimization",
                "title": "Public Exposure Optimization",
                "description": "Found {count} resources exposed to the public network",
                "recommendation": "Evaluate if public network access is really needed, configure security group whitelist",
            },
            "disk_encryption": {
                "category": "Security Optimization",
                "title": "Disk Encryption Optimization",
                "description": "Found {count} instances do not have disk encryption enabled",
                "recommendation": "Enable disk encryption for all instances to protect data security and meet compliance requirements",
            },
        },
    },
}


def get_translation(key_path: str, locale: Locale = "zh", **kwargs) -> str:
    """
    获取翻译文本
    
    Args:
        locale: 语言代码 ("zh" 或 "en")
        key_path: 翻译键路径，用点号分隔，如 "security.public_exposure.title"
        **kwargs: 格式化参数
    
    Returns:
        翻译后的文本
    """
    if locale not in TRANSLATIONS:
        locale = "zh"  # 默认使用中文
    
    keys = key_path.split(".")
    value = TRANSLATIONS[locale]
    
    try:
        for key in keys:
            value = value[key]
        
        if isinstance(value, str):
            return value.format(**kwargs) if kwargs else value
        return str(value)
    except (KeyError, AttributeError):
        # 如果找不到翻译，返回键路径
        return key_path


def get_locale_from_request(request_headers: dict = None, query_params: dict = None) -> Locale:
    """
    从请求中获取语言设置
    
    Args:
        request_headers: 请求头字典
        query_params: 查询参数字典
    
    Returns:
        语言代码
    """
    # 优先从查询参数获取
    if query_params and "locale" in query_params:
        locale = query_params["locale"]
        if locale in ["zh", "en"]:
            return locale
    
    # 从 Accept-Language header 获取
    if request_headers:
        accept_language = request_headers.get("Accept-Language", "")
        if "en" in accept_language.lower():
            return "en"
    
    # 默认返回中文
    return "zh"




