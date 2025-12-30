from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
import logging

from web.backend.api_base import handle_api_error
from core.config import ConfigManager, CloudAccount
from web.backend.i18n import get_translation, get_locale_from_request, Locale
from core.context import ContextManager
from core.cache import CacheManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ==================== 辅助函数 ====================

def _get_provider_for_account(account: Optional[str] = None):
    """获取账号的Provider实例"""
    cm = ConfigManager()
    if not account:
        ctx = ContextManager()
        account = ctx.get_last_account()
    if not account:
        accounts = cm.list_accounts()
        if accounts:
            account = accounts[0].name
        else:
            raise HTTPException(status_code=404, detail="No accounts configured")

    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"Account '{account}' not found")

    from cli.utils import get_provider
    return get_provider(account_config), account


# ==================== 安全检查端点 ====================

@router.get("/security/overview")
def get_security_overview(
    account: Optional[str] = None, 
    force_refresh: bool = Query(False, description="强制刷新缓存"),
    locale: Optional[str] = Query("zh", description="语言设置: zh 或 en")
):
    """获取安全概览（带24小时缓存）"""
    # 获取语言设置
    lang: Locale = get_locale_from_request(
        request_headers=None,
        query_params={"locale": locale}
    )
    
    try:
        provider, account_name = _get_provider_for_account(account)
        
        # 初始化缓存管理器，TTL设置为24小时（86400秒）
        cache_manager = CacheManager(ttl_seconds=86400)
        
        # 尝试从缓存获取数据
        cached_result = None
        if not force_refresh:
            cached_result = cache_manager.get(resource_type="security_overview", account_name=account_name)
        
        # 如果缓存有效，由于包含翻译文本，如果是英文且缓存是中文，则需要刷新
        if cached_result is not None:
            if lang == "en":
                cached_result = None
            else:
                return {
                    "success": True,
                    "data": cached_result,
                    "cached": True,
                }
        
        from core.security_compliance import SecurityComplianceAnalyzer
        
        instances = provider.list_instances()
        rds_list = provider.list_rds()
        redis_list = provider.list_redis()
        all_resources = instances + rds_list + redis_list
        
        analyzer = SecurityComplianceAnalyzer()
        
        # 公网暴露检测
        exposed = analyzer.detect_public_exposure(all_resources)
        
        # 安全检查
        stopped = analyzer.check_stopped_instances(instances)
        tag_coverage, no_tags = analyzer.check_missing_tags(all_resources)
        
        # 磁盘加密检查
        encryption_info = analyzer.check_disk_encryption(instances)
        
        # 抢占式实例检查
        preemptible = analyzer.check_preemptible_instances(instances)
        
        # EIP使用情况
        eip_info = {"total": 0, "bound": 0, "unbound": 0, "unbound_rate": 0}
        try:
            eips = provider.list_eip() if hasattr(provider, 'list_eip') else (provider.list_eips() if hasattr(provider, 'list_eips') else [])
            if eips:
                eip_info = analyzer.analyze_eip_usage(eips)
        except:
            pass
        
        # 计算安全评分
        security_score = 100
        score_deductions = []
        
        if len(exposed) > 0:
            deduction = min(len(exposed) * 5, 30)
            security_score -= deduction
            score_deductions.append({
                "reason": get_translation("security.score_deductions.public_exposure", lang, count=len(exposed)),
                "deduction": deduction
            })
        
        if len(stopped) > 0:
            deduction = min(len(stopped) * 2, 20)
            security_score -= deduction
            score_deductions.append({
                "reason": get_translation("security.score_deductions.stopped_instances", lang, count=len(stopped)),
                "deduction": deduction
            })
        
        if tag_coverage < 80:
            deduction = 10 if tag_coverage < 50 else 5
            security_score -= deduction
            score_deductions.append({
                "reason": get_translation("security.score_deductions.tag_coverage", lang, coverage=tag_coverage),
                "deduction": deduction
            })
        
        if encryption_info.get("encryption_rate", 100) < 50:
            deduction = 15
            security_score -= deduction
            score_deductions.append({
                "reason": get_translation("security.score_deductions.disk_encryption", lang, rate=encryption_info.get('encryption_rate', 0)),
                "deduction": deduction
            })
        
        if len(preemptible) > 0:
            deduction = min(len(preemptible) * 3, 15)
            security_score -= deduction
            score_deductions.append({
                "reason": get_translation("security.score_deductions.preemptible_instances", lang, count=len(preemptible)),
                "deduction": deduction
            })
        
        if eip_info.get("unbound_rate", 0) > 20:
            deduction = 5
            security_score -= deduction
            score_deductions.append({
                "reason": get_translation("security.score_deductions.eip_unbound", lang, rate=eip_info.get('unbound_rate', 0)),
                "deduction": deduction
            })
        
        # 获取最新的公网扫描结果
        from core.security_scanner import PublicIPScanner
        last_scan = PublicIPScanner.load_last_results()
        scan_summary = {
            "last_scan_time": last_scan.get("scan_time") if last_scan else None,
            "total_scanned": last_scan.get("summary", {}).get("total_scanned", 0) if last_scan else 0,
            "high_risk_count": last_scan.get("summary", {}).get("high_risk_count", 0) if last_scan else 0,
        }
        
        # 如果有扫描出的漏洞，进一步扣分
        if scan_summary["high_risk_count"] > 0:
            deduction = min(scan_summary["high_risk_count"] * 10, 40)
            security_score -= deduction
            score_deductions.append({
                "reason": get_translation("security.score_deductions.deep_scan_vulnerabilities", lang, count=scan_summary["high_risk_count"]),
                "deduction": deduction
            })

        security_score = max(0, min(100, security_score))
        
        security_summary = {
            "exposed_count": len(exposed),
            "stopped_count": len(stopped),
            "tag_coverage_rate": tag_coverage,
            "encryption_rate": encryption_info.get("encryption_rate", 100),
            "preemptible_count": len(preemptible),
            "unbound_eip": eip_info.get("unbound", 0),
            "deep_scan_risk": scan_summary["high_risk_count"],
        }
        suggestions = analyzer.suggest_security_improvements(security_summary, locale=lang)
        
        result_data = {
            "security_score": security_score,
            "exposed_count": len(exposed),
            "stopped_count": len(stopped),
            "tag_coverage": tag_coverage,
            "missing_tags_count": len(no_tags),
            "alert_count": len(exposed) + len(stopped) + len(preemptible) + scan_summary["high_risk_count"],
            "encryption_rate": encryption_info.get("encryption_rate", 100),
            "encrypted_count": encryption_info.get("encrypted", 0),
            "unencrypted_count": encryption_info.get("unencrypted_count", 0),
            "preemptible_count": len(preemptible),
            "eip_total": eip_info.get("total", 0),
            "eip_bound": eip_info.get("bound", 0),
            "eip_unbound": eip_info.get("unbound", 0),
            "eip_unbound_rate": eip_info.get("unbound_rate", 0),
            "score_deductions": score_deductions,
            "suggestions": suggestions,
            "deep_scan_summary": scan_summary
        }
        
        cache_manager.set(resource_type="security_overview", account_name=account_name, data=result_data)
        
        return {
            "success": True,
            "data": result_data,
            "cached": False,
        }
    except Exception as e:
        raise handle_api_error(e, "get_security_overview")


@router.get("/security/checks")
def get_security_checks(
    account: Optional[str] = None, 
    force_refresh: bool = Query(False, description="强制刷新缓存"),
    locale: Optional[str] = Query("zh", description="语言设置: zh 或 en")
):
    """获取安全检查列表（带24小时缓存）"""
    lang: Locale = get_locale_from_request(
        request_headers=None,
        query_params={"locale": locale}
    )
    
    try:
        provider, account_name = _get_provider_for_account(account)
        cache_manager = CacheManager(ttl_seconds=86400)
        
        cached_result = None
        if not force_refresh and lang == "zh":
            cached_result = cache_manager.get(resource_type="security_checks", account_name=account_name)
        
        if cached_result is not None:
            return {
                "success": True,
                "data": cached_result,
                "cached": True,
            }
        
        from core.security_compliance import SecurityComplianceAnalyzer
        
        instances = provider.list_instances()
        rds_list = provider.list_rds()
        redis_list = provider.list_redis()
        all_resources = instances + rds_list + redis_list
        
        analyzer = SecurityComplianceAnalyzer()
        
        exposed = analyzer.detect_public_exposure(all_resources)
        stopped = analyzer.check_stopped_instances(instances)
        tag_coverage, no_tags = analyzer.check_missing_tags(all_resources)
        encryption_info = analyzer.check_disk_encryption(instances)
        preemptible = analyzer.check_preemptible_instances(instances)
        
        eip_info = {"total": 0, "bound": 0, "unbound": 0, "unbound_eips": []}
        try:
            eips = provider.list_eip() if hasattr(provider, 'list_eip') else (provider.list_eips() if hasattr(provider, 'list_eips') else [])
            if eips:
                eip_info = analyzer.analyze_eip_usage(eips)
        except:
            pass
        
        checks = []
        
        # 公网暴露检查
        if exposed:
            checks.append({
                "type": "public_exposure",
                "title": get_translation("security.public_exposure.title", lang),
                "description": get_translation("security.public_exposure.description_failed", lang),
                "status": "failed",
                "severity": "HIGH",
                "count": len(exposed),
                "resources": exposed[:20],
                "recommendation": get_translation("security.public_exposure.recommendation", lang),
            })
        else:
            checks.append({
                "type": "public_exposure",
                "title": get_translation("security.public_exposure.title", lang),
                "description": get_translation("security.public_exposure.description_passed", lang),
                "status": "passed",
                "severity": "INFO",
                "count": 0,
                "resources": [],
            })
            
        # 停止实例检查
        if stopped:
            checks.append({
                "type": "stopped_instances",
                "title": get_translation("security.stopped_instances.title", lang),
                "description": get_translation("security.stopped_instances.description", lang),
                "status": "warning",
                "severity": "MEDIUM",
                "count": len(stopped),
                "resources": stopped[:20],
                "recommendation": get_translation("security.stopped_instances.recommendation", lang),
            })
            
        # 标签检查
        checks.append({
            "type": "tag_coverage",
            "title": get_translation("security.tag_coverage.title", lang),
            "description": get_translation("security.tag_coverage.description_passed" if tag_coverage >= 80 else "security.tag_coverage.description_failed", lang),
            "status": "passed" if tag_coverage >= 80 else "warning",
            "severity": "INFO" if tag_coverage >= 80 else "MEDIUM",
            "coverage": tag_coverage,
            "missing_count": len(no_tags),
            "resources": no_tags[:20] if tag_coverage < 80 else [],
            "recommendation": get_translation("security.tag_coverage.recommendation", lang),
        })
        
        # 磁盘加密检查
        encryption_rate = encryption_info.get("encryption_rate", 100)
        checks.append({
            "type": "disk_encryption",
            "title": get_translation("security.disk_encryption.title", lang),
            "description": get_translation("security.disk_encryption.description_passed" if encryption_rate == 100 else "security.disk_encryption.description_failed", lang),
            "status": "passed" if encryption_rate == 100 else "warning",
            "severity": "INFO" if encryption_rate == 100 else "MEDIUM",
            "encryption_rate": encryption_rate,
            "resources": encryption_info.get("unencrypted_instances", [])[:20],
        })
        
        cache_manager.set(resource_type="security_checks", account_name=account_name, data=checks)
        
        return {
            "success": True,
            "data": checks,
            "cached": False,
        }
    except Exception as e:
        raise handle_api_error(e, "get_security_checks")


@router.get("/security/cis")
def get_cis_benchmarks(account: Optional[str] = None):
    """获取CIS合规检查结果"""
    try:
        provider, account_name = _get_provider_for_account(account)
        from core.cis_compliance import CISBenchmark
        
        instances = provider.list_instances()
        rds_list = provider.list_rds()
        all_resources = instances + rds_list
        
        checker = CISBenchmark()
        results = checker.run_all_checks(all_resources, provider)
        
        total_checks = len(results.get("results", []))
        passed_checks = sum(1 for check in results.get("results", []) if check.get("status") == "PASS")
        compliance_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        return {
            "success": True,
            "data": {
                "compliance_rate": round(compliance_rate, 2),
                "checks": results.get("results", []),
                "summary": results.get("summary", {}),
            }
        }
    except Exception as e:
        return {
            "success": True,
            "data": {
                "compliance_rate": 0,
                "checks": [],
                "message": f"CIS功能可用性受限: {str(e)}"
            }
        }

@router.post("/security/deep-scan")
def trigger_deep_scan(account: Optional[str] = None):
    """手动触发公网安全扫描"""
    try:
        provider, account_name = _get_provider_for_account(account)
        from core.security_compliance import SecurityComplianceAnalyzer
        from core.security_scanner import PublicIPScanner
        
        instances = provider.list_instances()
        analyzer = SecurityComplianceAnalyzer()
        exposed = analyzer.detect_public_exposure(instances)
        
        public_ips = []
        for res in exposed:
            ip = res.get("public_ip")
            if ip:
                public_ips.append(ip)
        
        if not public_ips:
            return {
                "success": True,
                "message": "没有发现具有公网IP的资源，无需扫描",
                "count": 0
            }
            
        # 并发扫描 IP
        results = []
        for ip in public_ips:
            scan_res = PublicIPScanner.scan_ip(ip)
            results.append(scan_res)
            
        PublicIPScanner.save_results(results)
        
        # 清除缓存强制下次计算概览时包含新结果
        cache_manager = CacheManager(ttl_seconds=86400)
        cache_manager.delete(resource_type="security_overview", account_name=account_name)
        
        return {
            "success": True,
            "message": f"成功完成 {len(public_ips)} 个公网IP的扫描",
            "results": results,
            "summary": {
                "total": len(public_ips),
                "high_risk": sum(1 for r in results if r["risk_level"] in ["HIGH", "CRITICAL"])
            }
        }
    except Exception as e:
        raise handle_api_error(e, "trigger_deep_scan")
