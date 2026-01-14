"""
Public IP Security Scanner
对公网IP进行基础安全检测
"""

import logging
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("SecurityScanner")


class PublicIPScanner:
    """公网IP安全扫描器"""

    # 常见端口及其风险等级
    COMMON_PORTS = {
        22: {"service": "SSH", "risk": "HIGH", "desc": "SSH 远程登录端口"},
        23: {"service": "Telnet", "risk": "CRITICAL", "desc": "Telnet 明文传输"},
        80: {"service": "HTTP", "risk": "LOW", "desc": "HTTP Web服务"},
        443: {"service": "HTTPS", "risk": "LOW", "desc": "HTTPS Web服务"},
        3306: {"service": "MySQL", "risk": "CRITICAL", "desc": "MySQL 数据库"},
        3389: {"service": "RDP", "risk": "HIGH", "desc": "Windows 远程桌面"},
        5432: {"service": "PostgreSQL", "risk": "CRITICAL", "desc": "PostgreSQL 数据库"},
        6379: {"service": "Redis", "risk": "CRITICAL", "desc": "Redis 缓存"},
        27017: {"service": "MongoDB", "risk": "CRITICAL", "desc": "MongoDB 数据库"},
        1433: {"service": "MSSQL", "risk": "CRITICAL", "desc": "MSSQL 数据库"},
        21: {"service": "FTP", "risk": "HIGH", "desc": "FTP 文件传输"},
        25: {"service": "SMTP", "risk": "MEDIUM", "desc": "SMTP 邮件"},
        8080: {"service": "HTTP-Proxy", "risk": "MEDIUM", "desc": "HTTP 代理"},
    }

    @staticmethod
    def scan_port(ip: str, port: int, timeout: float = 2.0) -> bool:
        """
        扫描单个端口

        Args:
            ip: IP地址
            port: 端口号
            timeout: 超时时间（秒）

        Returns:
            端口是否开放
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                return result == 0
        except Exception as e:
            logger.debug(f"Port scan error for {ip}:{port} - {e}")
            return False

    @staticmethod
    def check_ssl_certificate(ip: str, port: int = 443) -> Optional[Dict]:
        """
        检查 SSL 证书

        Returns:
            证书信息字典或 None
        """
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with socket.create_connection((ip, port), timeout=3) as sock:
                with context.wrap_socket(sock, server_hostname=ip) as ssock:
                    cert = ssock.getpeercert()

                    # 提取证书信息
                    not_after = cert.get("notAfter")
                    if not_after:
                        expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                        days_to_expiry = (expiry - datetime.now()).days
                    else:
                        days_to_expiry = None

                    return {
                        "issuer": dict(x[0] for x in cert.get("issuer", [])),
                        "subject": dict(x[0] for x in cert.get("subject", [])),
                        "expiry_date": not_after,
                        "days_to_expiry": days_to_expiry,
                        "version": cert.get("version"),
                    }
        except Exception as e:
            logger.debug(f"SSL check error for {ip}:{port} - {e}")
            return None

    @staticmethod
    def grab_banner(ip: str, port: int, timeout: float = 2.0) -> Optional[str]:
        """
        获取端口服务Banner信息
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                sock.connect((ip, port))

                # 发送不同的探测包
                if port in [80, 443, 8080]:
                    msg = b"HEAD / HTTP/1.0\r\n\r\n"
                else:
                    msg = b"\r\n"

                sock.send(msg)
                banner = sock.recv(1024).decode("utf-8", errors="ignore").strip()
                return banner
        except Exception:
            return None

    @staticmethod
    def identify_service_version(banner: str, port: int) -> Dict:
        """
        从Banner中识别服务和版本
        """
        info = {"product": None, "version": None, "raw": banner}

        if not banner:
            return info

        import re

        # SSH
        if "SSH-" in banner:
            info["product"] = "OpenSSH"
            # Example: SSH-2.0-OpenSSH_7.4
            match = re.search(r"OpenSSH_([\d\.]+)", banner)
            if match:
                info["version"] = match.group(1)

        # HTTP Server Header
        elif "Server:" in banner:
            # Example: Server: nginx/1.14.0
            match = re.search(r"Server:\s*([^\s/]+)(?:/([\d\.]+))?", banner, re.IGNORECASE)
            if match:
                info["product"] = match.group(1)  # e.g. nginx
                if match.group(2):
                    info["version"] = match.group(2)

        return info

    @classmethod
    def scan_ip(cls, ip: str, ports: List[int] = None, check_ssl: bool = True) -> Dict:
        """
        扫描一个IP地址

        Args:
            ip: IP地址或域名
            ports: 要扫描的端口列表（None = 扫描所有常见端口）
            check_ssl: 是否检查SSL证书

        Returns:
            扫描结果字典
        """
        from cloudlens.core.cve_matcher import CVEMatcher

        if ports is None:
            ports = list(cls.COMMON_PORTS.keys())

        open_ports = []
        high_risk_ports = []
        cve_findings = []

        # 并发扫描端口
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_port = {executor.submit(cls.scan_port, ip, port): port for port in ports}

            for future in as_completed(future_to_port):
                port = future_to_port[future]
                try:
                    if future.result():
                        port_info = cls.COMMON_PORTS.get(port, {})

                        # Banner Grabbing & CVE Check
                        banner = cls.grab_banner(ip, port)
                        service_info = cls.identify_service_version(banner, port)

                        # Match CVEs
                        if service_info["product"] and service_info["version"]:
                            # Normalize product name (e.g. nginx -> Nginx)
                            product_map = {
                                "nginx": "Nginx",
                                "apache": "Apache",
                                "OpenSSH": "OpenSSH",
                            }
                            product = product_map.get(
                                service_info["product"].lower(), service_info["product"]
                            )

                            vulns = CVEMatcher.match(product, service_info["version"])
                            for v in vulns:
                                cve_findings.append(
                                    {
                                        "cve_id": v["id"],
                                        "severity": v["severity"],
                                        "product": product,
                                        "version": service_info["version"],
                                        "description": v["description"],
                                        "port": port,
                                    }
                                )

                        open_ports.append(
                            {
                                "port": port,
                                "service": port_info.get("service", "Unknown"),
                                "risk": port_info.get("risk", "MEDIUM"),
                                "desc": port_info.get("desc", ""),
                                "banner": banner[:50] if banner else None,  # Truncate long banners
                                "version_info": service_info if service_info["product"] else None,
                            }
                        )

                        # 记录高危端口
                        if port_info.get("risk") in ["HIGH", "CRITICAL"]:
                            high_risk_ports.append(port)
                except Exception as e:
                    logger.error(f"Error scanning port {port}: {e}")

        # SSL 证书检查
        ssl_info = None
        if check_ssl and 443 in [p["port"] for p in open_ports]:
            ssl_info = cls.check_ssl_certificate(ip)

        # 风险评估
        risk_level = "LOW"
        if cve_findings:
            # If any CRITICAL CVE found
            if any(c["severity"] == "CRITICAL" for c in cve_findings):
                risk_level = "CRITICAL"
            else:
                risk_level = "HIGH"
        elif high_risk_ports:
            risk_level = "CRITICAL" if len(high_risk_ports) >= 2 else "HIGH"
        elif len(open_ports) > 5:
            risk_level = "MEDIUM"

        return {
            "ip": ip,
            "open_ports": open_ports,
            "high_risk_ports": high_risk_ports,
            "cve_findings": cve_findings,
            "ssl_info": ssl_info,
            "risk_level": risk_level,
            "scan_time": datetime.now().isoformat(),
        }

    @classmethod
    def generate_recommendations(cls, scan_result: Dict) -> List[str]:
        """
        生成安全建议
        """
        recommendations = []

        open_ports = scan_result.get("open_ports", [])
        high_risk_ports = scan_result.get("high_risk_ports", [])
        cve_findings = scan_result.get("cve_findings", [])
        ssl_info = scan_result.get("ssl_info")

        # CVE 建议
        if cve_findings:
            recommendations.append(f"🚨 发现 {len(cve_findings)} 个潜在漏洞 (CVE):")
            for cve in cve_findings:
                recommendations.append(
                    f"  • [{cve['severity']}] {cve['product']} {cve['version']} -> {cve['cve_id']}: {cve['description']}"
                )
            recommendations.append("  👉 建议立即升级相关软件版本！")

        # 高危端口建议
        if high_risk_ports:
            recommendations.append(
                f"⚠️ 检测到 {len(high_risk_ports)} 个高危端口开放: {high_risk_ports}"
            )

            if 22 in high_risk_ports:
                recommendations.append("  • SSH (22): 建议修改默认端口, 使用密钥认证, 限制源IP")
            if 3389 in high_risk_ports:
                recommendations.append("  • RDP (3389): 建议使用VPN访问, 或修改默认端口")
            if 3306 in high_risk_ports or 6379 in high_risk_ports or 27017 in high_risk_ports:
                recommendations.append("  • 数据库端口: 严禁直接暴露公网! 应使用内网访问或VPN")

        # SSL 证书建议
        if ssl_info:
            days_to_expiry = ssl_info.get("days_to_expiry")
            if days_to_expiry is not None:
                if days_to_expiry < 0:
                    recommendations.append("🔴 SSL证书已过期!")
                elif days_to_expiry < 30:
                    recommendations.append(f"⚠️ SSL证书将在 {days_to_expiry} 天后过期, 请及时续期")

        # 端口过多建议
        if len(open_ports) > 10:
            recommendations.append(f"⚠️ 开放端口过多 ({len(open_ports)} 个), 建议关闭不必要的服务")

        if not recommendations:
            recommendations.append("✅ 暂未发现明显安全风险")

        return recommendations

    @staticmethod
    def get_report_path() -> str:
        """获取扫描报告保存路径"""
        import os

        home = os.path.expanduser("~")
        report_dir = os.path.join(home, ".cloudlens", "reports")
        os.makedirs(report_dir, exist_ok=True)
        return os.path.join(report_dir, "security_scan_latest.json")

    @classmethod
    def save_results(cls, results: List[Dict]):
        """保存扫描结果"""
        import json

        try:
            filepath = cls.get_report_path()
            data = {
                "scan_time": datetime.now().isoformat(),
                "results": results,
                "summary": {
                    "total_scanned": len(results),
                    "high_risk_count": sum(
                        1 for r in results if r["risk_level"] in ["HIGH", "CRITICAL"]
                    ),
                },
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Scan results saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save scan results: {e}")

    @classmethod
    def load_last_results(cls) -> Optional[Dict]:
        """加载上次扫描结果"""
        import json
        import os

        try:
            filepath = cls.get_report_path()
            if not os.path.exists(filepath):
                return None

            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load scan results: {e}")
            return None
