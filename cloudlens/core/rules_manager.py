import json
import os
from pathlib import Path
from typing import Dict, Any

class RulesManager:
    """策略规则管理器"""
    
    DEFAULT_RULES = {
        "version": "1.0",
        "idle_rules": {
            "ecs": {
                "cpu_threshold_percent": 5,
                "network_threshold_bytes_sec": 1000,
                "exclude_tags": ["k8s.io", "ack.aliyun.com"]
            },
            "rds": {
                "connection_threshold": 5,
                "exclude_tags": []
            },
            "redis": {
                 "connection_threshold": 5,
                 "exclude_tags": []
            }
        }
    }

    def __init__(self, config_dir: str = "~/.cloudlens"):
        self.config_dir = Path(os.path.expanduser(config_dir))
        self.rules_file = self.config_dir / "rules.json"
        
    def get_rules(self) -> Dict[str, Any]:
        """获取规则配置 (如果不存在则返回默认值)"""
        if not self.rules_file.exists():
            return self.DEFAULT_RULES
            
        try:
            with open(self.rules_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return self.DEFAULT_RULES
            
    def set_rules(self, rules: Dict[str, Any]):
        """保存规则配置"""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
        with open(self.rules_file, "w", encoding="utf-8") as f:
            json.dump(rules, f, indent=2, ensure_ascii=False)
            
    def update_idle_threshold(self, resource_type: str, key: str, value: Any):
        """更新特定闲置阈值"""
        rules = self.get_rules()
        if resource_type in rules["idle_rules"]:
            rules["idle_rules"][resource_type][key] = value
            self.set_rules(rules)
            
    def add_exclude_tag(self, resource_type: str, tag: str):
        """添加排除标签"""
        rules = self.get_rules()
        if resource_type in rules["idle_rules"]:
            tags = rules["idle_rules"][resource_type].get("exclude_tags", [])
            if tag not in tags:
                tags.append(tag)
                rules["idle_rules"][resource_type]["exclude_tags"] = tags
                self.set_rules(rules)
