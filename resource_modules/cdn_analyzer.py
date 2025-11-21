#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CDN内容分发网络资源分析模块
分析CDN域名的使用情况,提供优化建议
"""

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

from core.analyzer_registry import AnalyzerRegistry
from core.base_analyzer import BaseResourceAnalyzer
from utils.concurrent_helper import process_concurrently
from utils.error_handler import ErrorHandler
from utils.logger import get_logger


@AnalyzerRegistry.register("cdn", "CDN加速", "🚀")
class CDNAnalyzer(BaseResourceAnalyzer):
    """CDN资源分析器"""

    def __init__(self, access_key_id, access_key_secret, tenant_name=None):
        super().__init__(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            tenant_name=tenant_name or "default",
        )
        self.db_name = "cdn_monitoring_data.db"
        self.logger = get_logger("cdn_analyzer")
        self.init_database()

    def get_resource_type(self) -> str:
        return "cdn"

    def init_database(self):
        """初始化CDN数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS cdn_domains (
            domain_name TEXT PRIMARY KEY,
            cdn_type TEXT,
            domain_status TEXT,
            source_type TEXT,
            creation_time TEXT,
            traffic_30d REAL DEFAULT 0,
            requests_30d INTEGER DEFAULT 0,
            hit_rate REAL DEFAULT 0
        )
        """
        )

        conn.commit()
        conn.close()
        self.logger.info("CDN数据库初始化完成")

    def get_all_regions(self):
        """CDN是全局服务,返回全球"""
        return ["global"]

    def get_instances(self, region: str) -> List[Dict]:
        """获取CDN域名列表"""
        return self.get_cdn_domains()

    def get_cdn_domains(self):
        """获取CDN域名列表"""
        try:
            # CDN API使用不同的endpoint
            client = AcsClient(self.access_key_id, self.access_key_secret, "cn-hangzhou")
            request = CommonRequest()
            request.set_domain("cdn.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2018-05-10")
            request.set_action_name("DescribeUserDomains")
            request.add_query_param("PageSize", "50")
            request.add_query_param("PageNumber", "1")

            all_domains = []
            page_number = 1

            while True:
                request.add_query_param("PageNumber", str(page_number))
                response = client.do_action_with_exception(request)
                data = json.loads(response)

                if "Domains" in data and "PageData" in data["Domains"]:
                    domains = data["Domains"]["PageData"]

                    if not domains:
                        break

                    for domain in domains:
                        all_domains.append(
                            {
                                "DomainName": domain["DomainName"],
                                "CdnType": domain.get("CdnType", ""),
                                "DomainStatus": domain.get("DomainStatus", ""),
                                "SourceType": domain.get("SourceType", ""),
                                "GmtCreated": domain.get("GmtCreated", ""),
                                "GmtModified": domain.get("GmtModified", ""),
                            }
                        )

                    total_count = data.get("TotalCount", 0)
                    if len(all_domains) >= total_count:
                        break

                    page_number += 1
                else:
                    break

            return all_domains
        except Exception as e:
            self.logger.info(f"获取CDN域名失败: {str(e)}")
            return []

    def get_metrics(self, region: str, instance_id: str, days: int = 30) -> Dict:
        """获取CDN域名的监控数据"""
        domain_name = instance_id
        client = AcsClient(self.access_key_id, self.access_key_secret, "cn-hangzhou")
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        result = {}

        # 获取流量数据
        try:
            request = CommonRequest()
            request.set_domain("cdn.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2018-05-10")
            request.set_action_name("DescribeDomainBpsData")
            request.add_query_param("DomainName", domain_name)
            request.add_query_param("StartTime", start_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            request.add_query_param("EndTime", end_time.strftime("%Y-%m-%dT%H:%M:%SZ"))

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            if "BpsDataPerInterval" in data and "DataModule" in data["BpsDataPerInterval"]:
                bps_data = data["BpsDataPerInterval"]["DataModule"]
                if bps_data:
                    # 计算平均带宽和总流量
                    avg_bps = sum(float(d.get("Value", 0)) for d in bps_data) / len(bps_data)
                    # 估算总流量 (GB) = 平均带宽(bps) * 时间(秒) / 8 / 1024^3
                    total_traffic_gb = (avg_bps * days * 86400) / 8 / (1024 ** 3)
                    result["平均带宽(Mbps)"] = avg_bps / (1024 * 1024)
                    result["总流量(GB)"] = total_traffic_gb
                else:
                    result["平均带宽(Mbps)"] = 0
                    result["总流量(GB)"] = 0
            else:
                result["平均带宽(Mbps)"] = 0
                result["总流量(GB)"] = 0
        except Exception as e:
            self.logger.debug(f"获取带宽数据失败: {e}")
            result["平均带宽(Mbps)"] = 0
            result["总流量(GB)"] = 0

        # 获取访问量
        try:
            request = CommonRequest()
            request.set_domain("cdn.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2018-05-10")
            request.set_action_name("DescribeDomainPvData")
            request.add_query_param("DomainName", domain_name)
            request.add_query_param("StartTime", start_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            request.add_query_param("EndTime", end_time.strftime("%Y-%m-%dT%H:%M:%SZ"))

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            if "PvDataInterval" in data and "UsageData" in data["PvDataInterval"]:
                pv_data = data["PvDataInterval"]["UsageData"]
                total_pv = sum(int(d.get("Value", 0)) for d in pv_data)
                result["总访问量"] = total_pv
            else:
                result["总访问量"] = 0
        except Exception as e:
            self.logger.debug(f"获取访问量失败: {e}")
            result["总访问量"] = 0

        # 获取缓存命中率
        try:
            request = CommonRequest()
            request.set_domain("cdn.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2018-05-10")
            request.set_action_name("DescribeDomainHitRateData")
            request.add_query_param("DomainName", domain_name)
            request.add_query_param("StartTime", start_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            request.add_query_param("EndTime", end_time.strftime("%Y-%m-%dT%H:%M:%SZ"))

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            if "HitRateInterval" in data and "DataModule" in data["HitRateInterval"]:
                hit_data = data["HitRateInterval"]["DataModule"]
                if hit_data:
                    avg_hit_rate = sum(float(d.get("Value", 0)) for d in hit_data) / len(hit_data)
                    result["缓存命中率(%)"] = avg_hit_rate
                else:
                    result["缓存命中率(%)"] = 0
            else:
                result["缓存命中率(%)"] = 0
        except Exception as e:
            self.logger.debug(f"获取命中率失败: {e}")
            result["缓存命中率(%)"] = 0

        # 获取回源带宽
        try:
            request = CommonRequest()
            request.set_domain("cdn.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2018-05-10")
            request.set_action_name("DescribeDomainSrcBpsData")
            request.add_query_param("DomainName", domain_name)
            request.add_query_param("StartTime", start_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            request.add_query_param("EndTime", end_time.strftime("%Y-%m-%dT%H:%M:%SZ"))

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            if "SrcBpsDataPerInterval" in data and "DataModule" in data["SrcBpsDataPerInterval"]:
                src_bps_data = data["SrcBpsDataPerInterval"]["DataModule"]
                if src_bps_data:
                    avg_src_bps = sum(float(d.get("Value", 0)) for d in src_bps_data) / len(src_bps_data)
                    result["回源带宽(Mbps)"] = avg_src_bps / (1024 * 1024)
                else:
                    result["回源带宽(Mbps)"] = 0
            else:
                result["回源带宽(Mbps)"] = 0
        except Exception as e:
            self.logger.debug(f"获取回源带宽失败: {e}")
            result["回源带宽(Mbps)"] = 0

        # 计算回源比例
        total_bw = result.get("平均带宽(Mbps)", 0)
        src_bw = result.get("回源带宽(Mbps)", 0)
        if total_bw > 0:
            result["回源比例(%)"] = (src_bw / total_bw) * 100
        else:
            result["回源比例(%)"] = 0

        return result

    def is_idle(self, instance: Dict, metrics: Dict, thresholds: Dict = None) -> tuple:
        """判断CDN域名是否闲置"""
        if thresholds is None:
            thresholds = {
                "traffic_gb_min": 1,  # 30天流量 < 1GB
                "requests_min": 1000,  # 30天访问量 < 1000次
                "hit_rate_min": 50,  # 缓存命中率 < 50%
                "back_source_max": 80,  # 回源比例 > 80%
            }

        issues = []

        # 流量极低
        traffic = metrics.get("总流量(GB)", 0)
        if traffic < thresholds["traffic_gb_min"]:
            issues.append(f"30天流量({traffic:.2f}GB) < {thresholds['traffic_gb_min']}GB")

        # 访问量极低
        requests = metrics.get("总访问量", 0)
        if requests < thresholds["requests_min"]:
            issues.append(f"30天访问量({requests}) < {thresholds['requests_min']}")

        # 缓存命中率低
        hit_rate = metrics.get("缓存命中率(%)", 0)
        if hit_rate > 0 and hit_rate < thresholds["hit_rate_min"]:
            issues.append(f"缓存命中率({hit_rate:.1f}%) < {thresholds['hit_rate_min']}%")

        # 回源比例过高
        back_source = metrics.get("回源比例(%)", 0)
        if back_source > thresholds["back_source_max"]:
            issues.append(f"回源比例({back_source:.1f}%) > {thresholds['back_source_max']}%")

        # 域名状态
        domain_status = instance.get("DomainStatus", "")
        if domain_status in ["offline", "configure_failed"]:
            issues.append(f"域名状态异常: {domain_status}")

        return len(issues) > 0, issues

    def get_optimization_suggestions(self, instance: Dict, metrics: Dict) -> str:
        """获取优化建议"""
        suggestions = []

        traffic = metrics.get("总流量(GB)", 0)
        requests = metrics.get("总访问量", 0)
        hit_rate = metrics.get("缓存命中率(%)", 0)
        back_source = metrics.get("回源比例(%)", 0)

        if traffic < 0.1:
            suggestions.append("流量极低,建议评估是否需要保留CDN加速")

        if requests < 100:
            suggestions.append("访问量极低,建议删除闲置域名")

        if hit_rate < 50 and hit_rate > 0:
            suggestions.append(f"缓存命中率低({hit_rate:.1f}%),建议优化缓存配置")

        if back_source > 80:
            suggestions.append(f"回源比例过高({back_source:.1f}%),建议检查缓存规则")

        if not suggestions:
            suggestions.append("CDN使用正常")

        return "; ".join(suggestions)

    def analyze(self, regions=None, days=30):
        """分析资源"""
        self.analyze_cdn_domains()
        return []

    def generate_report(self, idle_instances):
        """生成报告"""
        pass

    def analyze_cdn_domains(self):
        """分析CDN域名"""
        self.logger.info("开始CDN资源分析...")

        domains = self.get_cdn_domains()

        if not domains:
            self.logger.warning("未发现任何CDN域名")
            return

        self.logger.info(f"总共获取到 {len(domains)} 个CDN域名")

        def process_single_domain(domain_item):
            domain = domain_item
            domain_name = domain["DomainName"]

            try:
                metrics = self.get_metrics("global", domain_name)
                has_issues, issues = self.is_idle(domain, metrics)
                optimization = self.get_optimization_suggestions(domain, metrics)

                domain["metrics"] = metrics
                domain["has_issues"] = has_issues
                domain["issues"] = issues
                domain["optimization"] = optimization

                return {"success": True, "domain": domain}
            except Exception as e:
                ErrorHandler.handle_instance_error(e, domain_name, "global", "CDN", continue_on_error=True)
                return {"success": False, "domain": domain, "error": str(e)}

        def progress_callback(completed, total):
            sys.stdout.write(f"\r📊 处理进度: {completed}/{total} ({completed/total*100:.1f}%)")
            sys.stdout.flush()

        processing_results = process_concurrently(
            domains, process_single_domain, max_workers=5, description="CDN分析", progress_callback=progress_callback
        )

        analyzed_domains = [r["domain"] for r in processing_results if r and r.get("success")]
        
        self.logger.info(f"\n处理完成: 成功 {len(analyzed_domains)} 个")
        self.generate_cdn_report(analyzed_domains)
        self.logger.info("CDN分析完成")

    def generate_cdn_report(self, domains):
        """生成CDN报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        problem_domains = [d for d in domains if d.get("has_issues", False)]

        self.logger.info(f"分析结果: 共 {len(domains)} 个CDN域名，其中 {len(problem_domains)} 个需要优化")

        if not problem_domains:
            self.logger.info("没有发现需要优化的CDN域名")
            return

        html_file = f"cdn_analysis_report_{timestamp}.html"
        excel_file = f"cdn_analysis_report_{timestamp}.xlsx"
        
        self.generate_html_report(problem_domains, html_file)
        self.generate_excel_report(problem_domains, excel_file)

        self.logger.info(f"📄 报告已生成: {html_file}, {excel_file}")

    def generate_html_report(self, problem_domains, filename):
        """生成HTML报告"""
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>CDN域名分析报告</title>
<style>body{{font-family:'Microsoft YaHei',Arial;margin:20px;background:#f5f5f5}}
.container{{max-width:1400px;margin:0 auto;background:white;padding:20px;border-radius:10px}}
h1{{color:#2c3e50;text-align:center;border-bottom:3px solid #e74c3c;padding-bottom:20px}}
table{{width:100%;border-collapse:collapse;margin:20px 0;font-size:14px}}
th,td{{border:1px solid #ddd;padding:10px;text-align:left}}
th{{background:#3498db;color:white}}tr:hover{{background:#e8f4f8}}</style>
</head><body><div class="container"><h1>🚀 CDN域名分析报告</h1>
<p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p><strong>需要优化的域名:</strong> {len(problem_domains)} 个</p>
<table><thead><tr><th>域名</th><th>类型</th><th>状态</th><th>流量(GB)</th><th>访问量</th><th>命中率%</th><th>回源率%</th><th>问题</th><th>建议</th></tr></thead><tbody>"""
        
        for domain in problem_domains:
            m = domain.get("metrics", {})
            html += f"""<tr><td>{domain['DomainName']}</td><td>{domain.get('CdnType','')}</td><td>{domain.get('DomainStatus','')}</td>
<td>{m.get('总流量(GB)',0):.2f}</td><td>{m.get('总访问量',0)}</td><td>{m.get('缓存命中率(%)',0):.1f}</td><td>{m.get('回源比例(%)',0):.1f}</td>
<td>{'; '.join(domain.get('issues',[]))}</td><td>{domain.get('optimization','')}</td></tr>"""
        
        html += "</tbody></table></div></body></html>"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)

    def generate_excel_report(self, problem_domains, filename):
        """生成Excel报告"""
        try:
            data = []
            for domain in problem_domains:
                m = domain.get("metrics", {})
                data.append({
                    "域名": domain["DomainName"],
                    "CDN类型": domain.get("CdnType", ""),
                    "域名状态": domain.get("DomainStatus", ""),
                    "源站类型": domain.get("SourceType", ""),
                    "30天流量(GB)": round(m.get("总流量(GB)", 0), 2),
                    "30天访问量": m.get("总访问量", 0),
                    "平均带宽(Mbps)": round(m.get("平均带宽(Mbps)", 0), 2),
                    "缓存命中率(%)": round(m.get("缓存命中率(%)", 0), 1),
                    "回源比例(%)": round(m.get("回源比例(%)", 0), 1),
                    "问题": "; ".join(domain.get("issues", [])),
                    "优化建议": domain.get("optimization", ""),
                })
            
            df = pd.DataFrame(data)
            df.to_excel(filename, index=False, engine="openpyxl")
        except ImportError:
            self.logger.warning("pandas未安装")


if __name__ == "__main__":
    pass
