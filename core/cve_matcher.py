"""
CVE Vulnerability Matcher
Matches service versions against known vulnerabilities
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger("CVEMatcher")


@dataclass
class Vulnerability:
    id: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    affected_versions: str  # e.g., "< 7.4", "1.10.0 - 1.14.0"


class CVEMatcher:
    """
    Matches detected software versions against a local database of common CVEs.
    Focuses on high-profile vulnerabilities in common cloud services.
    """

    # Common CVE Database
    # This is a curated list of high-impact vulnerabilities for common services
    VULNERABILITIES = {
        "OpenSSH": [
            Vulnerability(
                id="CVE-2018-15473",
                severity="MEDIUM",
                description="User Enumeration vulnerability allows guessing valid usernames",
                affected_versions="< 7.7",
            ),
            Vulnerability(
                id="CVE-2016-10009",
                severity="CRITICAL",
                description="Remote Code Execution via forwarded agent socket",
                affected_versions="< 7.4",
            ),
        ],
        "Nginx": [
            Vulnerability(
                id="CVE-2021-23017",
                severity="HIGH",
                description="Off-by-one error in DNS resolver allows potential RCE",
                affected_versions="0.6.18 - 1.20.0",
            ),
            Vulnerability(
                id="CVE-2019-9511",
                severity="HIGH",
                description="HTTP/2 'Data Dribble' Denial of Service",
                affected_versions="1.9.5 - 1.16.0",
            ),
        ],
        "Apache": [
            Vulnerability(
                id="CVE-2021-41773",
                severity="CRITICAL",
                description="Path traversal and file disclosure in Apache HTTP Server 2.4.49",
                affected_versions="= 2.4.49",
            ),
            Vulnerability(
                id="CVE-2021-42013",
                severity="CRITICAL",
                description="Path traversal and RCE in Apache HTTP Server 2.4.49/2.4.50",
                affected_versions="2.4.49 - 2.4.50",
            ),
        ],
        "Redis": [
            Vulnerability(
                id="CVE-2022-0543",
                severity="CRITICAL",
                description="Lua sandbox escape allowing Remote Code Execution",
                affected_versions="< 6.2.7",  # Simplified, actually affects Debian/Ubuntu packages specifically but good as a general warning
            )
        ],
    }

    @staticmethod
    def _parse_version(version_str: str) -> List[int]:
        """Parse version string into a list of integers for comparison"""
        # Extract the first sequence of numbers separated by dots
        match = re.search(r"(\d+(?:\.\d+)+)", version_str)
        if not match:
            return []

        try:
            return [int(x) for x in match.group(1).split(".")]
        except ValueError:
            return []

    @classmethod
    def _version_compare(cls, current: List[int], target: List[int]) -> int:
        """Compare two version lists. Returns 1 if current > target, -1 if <, 0 if ="""
        for i in range(max(len(current), len(target))):
            v1 = current[i] if i < len(current) else 0
            v2 = target[i] if i < len(target) else 0
            if v1 > v2:
                return 1
            if v1 < v2:
                return -1
        return 0

    @classmethod
    def _check_condition(cls, current_ver: List[int], condition: str) -> bool:
        """Check if version satisfies the condition (e.g., '< 7.4')"""
        parts = condition.split()
        if len(parts) == 2:
            op, target_str = parts
            target_ver = cls._parse_version(target_str)
            if not target_ver:
                return False

            cmp = cls._version_compare(current_ver, target_ver)

            if op == "<":
                return cmp < 0
            if op == "<=":
                return cmp <= 0
            if op == ">":
                return cmp > 0
            if op == ">=":
                return cmp >= 0
            if op == "=":
                return cmp == 0

        elif "-" in condition:
            # Range: "1.0 - 2.0"
            start_str, end_str = condition.split("-")
            start_ver = cls._parse_version(start_str.strip())
            end_ver = cls._parse_version(end_str.strip())

            if not start_ver or not end_ver:
                return False

            return (
                cls._version_compare(current_ver, start_ver) >= 0
                and cls._version_compare(current_ver, end_ver) <= 0
            )

        return False

    @classmethod
    def match(cls, product: str, version: str) -> List[Dict]:
        """
        Match a product version against known vulnerabilities

        Args:
            product: Product name (e.g., "OpenSSH", "Nginx")
            version: Version string (e.g., "7.4p1", "1.14.0")

        Returns:
            List of matching vulnerabilities
        """
        matches = []
        if not version or product not in cls.VULNERABILITIES:
            return matches

        current_ver = cls._parse_version(version)
        if not current_ver:
            return matches

        for vuln in cls.VULNERABILITIES[product]:
            if cls._check_condition(current_ver, vuln.affected_versions):
                matches.append(
                    {
                        "id": vuln.id,
                        "severity": vuln.severity,
                        "description": vuln.description,
                        "affected_versions": vuln.affected_versions,
                    }
                )

        return matches
