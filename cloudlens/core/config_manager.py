#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器（支持环境变量替换）
"""

import json
import os
from pathlib import Path
from typing import Any, Dict


class ConfigManager:
    """统一配置管理器"""

    def __init__(self, config_file: str = "config.json"):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置（支持环境变量替换）"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")

        with open(self.config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        return self._replace_env_vars(config)

    def _replace_env_vars(self, obj: Any) -> Any:
        """递归替换环境变量 ${VAR_NAME}"""
        if isinstance(obj, dict):
            return {k: self._replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            var_name = obj[2:-1]
            value = os.getenv(var_name)
            if value is None:
                # 环境变量未设置，返回原值（允许为空）
                return obj
            return value
        return obj

    def get_tenant_config(self, tenant_name: str = None) -> Dict[str, Any]:
        """
        获取租户配置

        Args:
            tenant_name: 租户名称，None则使用default_tenant

        Returns:
            租户配置字典
        """
        if tenant_name is None:
            tenant_name = self.config.get("default_tenant")

        if not tenant_name:
            raise ValueError("未指定租户名称，且配置中没有default_tenant")

        tenants = self.config.get("tenants", {})
        if tenant_name not in tenants:
            raise ValueError(
                f"未找到租户配置: {tenant_name}，可用租户: {', '.join(tenants.keys())}"
            )

        return tenants[tenant_name]

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.config.get(key, default)

    def validate(self):
        """验证配置完整性"""
        required_fields = ["tenants"]
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"配置缺少必需字段: {field}")
