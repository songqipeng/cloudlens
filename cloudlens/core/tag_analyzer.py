"""
Tag Analyzer
标签治理分析器
"""

import logging
from collections import Counter
from typing import Dict, List

from cloudlens.models.resource import UnifiedResource

logger = logging.getLogger("TagAnalyzer")


class TagAnalyzer:
    """标签治理分析器"""

    @staticmethod
    def analyze_tag_coverage(resources: List[UnifiedResource]) -> Dict:
        """
        分析标签覆盖率

        Returns:
            统计结果字典
        """
        total = len(resources)
        if total == 0:
            return {"total": 0, "tagged": 0, "untagged": 0, "coverage_rate": 0}

        tagged = sum(1 for r in resources if r.tags)
        untagged = total - tagged

        return {
            "total": total,
            "tagged": tagged,
            "untagged": untagged,
            "coverage_rate": round(tagged / total * 100, 2),
            "untagged_resources": [r for r in resources if not r.tags],
        }

    @staticmethod
    def analyze_tag_keys(resources: List[UnifiedResource]) -> Dict:
        """
        分析标签键使用情况

        Returns:
            标签键统计
        """
        tag_keys = []
        for r in resources:
            if r.tags:
                tag_keys.extend(r.tags.keys())

        key_counter = Counter(tag_keys)

        return {
            "unique_keys": len(key_counter),
            "most_common": key_counter.most_common(10),
            "all_keys": list(key_counter.keys()),
        }

    @staticmethod
    def check_tag_naming_convention(
        resources: List[UnifiedResource], conventions: Dict = None
    ) -> List[Dict]:
        """
        检查标签命名规范

        Args:
            resources: 资源列表
            conventions: 命名规范，如 {"required_keys": ["env", "project"], "case": "lowercase"}

        Returns:
            违规资源列表
        """
        if conventions is None:
            conventions = {
                "required_keys": ["env", "project", "owner"],  # 必需的标签
                "case": "lowercase",  # 键名大小写规范
            }

        violations = []

        for r in resources:
            resource_violations = []

            # 检查必需标签
            if conventions.get("required_keys"):
                missing_keys = set(conventions["required_keys"]) - set(
                    r.tags.keys() if r.tags else []
                )
                if missing_keys:
                    resource_violations.append(f"缺少必需标签: {', '.join(missing_keys)}")

            # 检查大小写规范
            if r.tags and conventions.get("case") == "lowercase":
                uppercase_keys = [k for k in r.tags.keys() if k != k.lower()]
                if uppercase_keys:
                    resource_violations.append(f"标签键不是小写: {', '.join(uppercase_keys)}")

            if resource_violations:
                violations.append(
                    {
                        "resource_id": r.id,
                        "resource_name": r.name,
                        "violations": resource_violations,
                    }
                )

        return violations

    @staticmethod
    def suggest_tag_optimization(resources: List[UnifiedResource]) -> List[str]:
        """
        标签优化建议

        Returns:
            建议列表
        """
        suggestions = []

        coverage = TagAnalyzer.analyze_tag_coverage(resources)

        if coverage["coverage_rate"] < 50:
            suggestions.append(
                f"⚠️ 标签覆盖率仅{coverage['coverage_rate']}%，建议为所有资源添加标签以便管理"
            )

        if coverage["untagged"] > 0:
            suggestions.append(
                f"发现{coverage['untagged']}个无标签资源，建议至少添加 env, project, owner 标签"
            )

        tag_keys_info = TagAnalyzer.analyze_tag_keys(resources)
        if tag_keys_info["unique_keys"] > 20:
            suggestions.append(
                f"⚠️ 发现{tag_keys_info['unique_keys']}个不同的标签键，建议统一标签命名规范"
            )

        return suggestions
