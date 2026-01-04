#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面系统测试脚本 - 测试所有资源类型的查询功能
确保不会再发生类似OSS有数据但取不到的情况
"""

import sys
import json
import requests
import traceback
from typing import Dict, List, Any
from datetime import datetime

# 测试配置
BASE_URL = "http://127.0.0.1:8000"
TEST_ACCOUNT = "ydzn"  # 根据实际情况修改

# 所有资源类型
RESOURCE_TYPES = [
    "ecs", "rds", "redis", "slb", "nat", "eip", 
    "oss", "disk", "snapshot", "vpc", "mongodb", "ack"
]

class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")

def print_section(msg: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def test_backend_health() -> bool:
    """测试后端服务健康状态"""
    print_section("1. 后端服务健康检查")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"后端服务正常: {data.get('service', 'unknown')}")
            return True
        else:
            print_error(f"后端服务异常: HTTP {response.status_code}")
            return False
    except Exception as e:
        print_error(f"无法连接到后端服务: {e}")
        return False

def test_account_exists() -> str:
    """测试账号是否存在，返回可用的账号名称"""
    print_section("2. 账号配置检查")
    global TEST_ACCOUNT
    try:
        response = requests.get(f"{BASE_URL}/api/settings/accounts", timeout=5)
        if response.status_code == 200:
            data = response.json()
            accounts = data.get("data", []) if isinstance(data, dict) else data
            account_names = [acc.get("name") for acc in accounts if isinstance(acc, dict)]
            
            if TEST_ACCOUNT in account_names:
                print_success(f"测试账号 '{TEST_ACCOUNT}' 存在")
                return TEST_ACCOUNT
            else:
                print_warning(f"测试账号 '{TEST_ACCOUNT}' 不存在")
                print_info(f"可用账号: {', '.join(account_names) if account_names else '无'}")
                if account_names:
                    TEST_ACCOUNT = account_names[0]
                    print_info(f"使用账号: {TEST_ACCOUNT}")
                    return TEST_ACCOUNT
                return None
        else:
            print_error(f"获取账号列表失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print_error(f"检查账号配置失败: {e}")
        return False

def test_resource_type(resource_type: str) -> Dict[str, Any]:
    """测试单个资源类型的查询"""
    result = {
        "type": resource_type,
        "success": False,
        "error": None,
        "count": 0,
        "data_sample": None,
        "issues": []
    }
    
    try:
        print(f"\n📦 测试资源类型: {resource_type.upper()}")
        
        # 调用API
        url = f"{BASE_URL}/api/resources"
        params = {
            "type": resource_type,
            "account": TEST_ACCOUNT,
            "page": 1,
            "pageSize": 20
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        # 检查HTTP状态码
        if response.status_code != 200:
            result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
            print_error(f"  HTTP错误: {response.status_code}")
            return result
        
        # 解析JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            result["error"] = f"JSON解析失败: {e}"
            print_error(f"  JSON解析失败: {e}")
            print_error(f"  响应内容: {response.text[:500]}")
            return result
        
        # 检查响应结构
        if not isinstance(data, dict):
            result["error"] = "响应不是字典格式"
            print_error(f"  响应格式错误: 期望dict，得到{type(data)}")
            return result
        
        # 检查success字段
        if not data.get("success", False):
            error_msg = data.get("error") or data.get("message") or "未知错误"
            result["error"] = error_msg
            print_error(f"  API返回失败: {error_msg}")
            return result
        
        # 获取数据
        resources = data.get("data", [])
        if not isinstance(resources, list):
            result["error"] = f"data字段不是列表: {type(resources)}"
            print_error(f"  数据格式错误: data不是列表")
            return result
        
        result["count"] = len(resources)
        result["success"] = True
        
        # 验证数据格式
        if resources:
            sample = resources[0]
            result["data_sample"] = sample
            
            # 检查必需字段
            required_fields = ["id", "name", "type", "status", "region"]
            missing_fields = [f for f in required_fields if f not in sample]
            if missing_fields:
                result["issues"].append(f"缺少必需字段: {', '.join(missing_fields)}")
                print_warning(f"  缺少必需字段: {', '.join(missing_fields)}")
            
            # 检查字段类型
            if "id" in sample and not isinstance(sample["id"], str):
                result["issues"].append("id字段不是字符串类型")
                print_warning(f"  id字段类型错误: {type(sample['id'])}")
            
            if "name" in sample and not isinstance(sample["name"], str):
                result["issues"].append("name字段不是字符串类型")
                print_warning(f"  name字段类型错误: {type(sample['name'])}")
            
            if "status" in sample:
                status = sample["status"]
                if not isinstance(status, str):
                    result["issues"].append(f"status字段类型错误: {type(status)}")
                    print_warning(f"  status字段类型错误: {type(status)}")
            
            if "created_time" in sample and sample["created_time"]:
                created_time = sample["created_time"]
                if not isinstance(created_time, (str, type(None))):
                    result["issues"].append(f"created_time字段类型错误: {type(created_time)}")
                    print_warning(f"  created_time字段类型错误: {type(created_time)}")
            
            # 显示样本数据
            print_info(f"  样本数据: {sample.get('name', 'N/A')} ({sample.get('id', 'N/A')[:30]}...)")
            print_info(f"  区域: {sample.get('region', 'N/A')}, 状态: {sample.get('status', 'N/A')}")
        else:
            print_warning(f"  未找到资源数据（可能账号下确实没有该类型资源）")
        
        # 显示结果
        if result["count"] > 0:
            print_success(f"  找到 {result['count']} 个资源")
        else:
            print_warning(f"  未找到资源（可能是正常的，如果账号下确实没有该类型资源）")
        
        return result
        
    except requests.exceptions.Timeout:
        result["error"] = "请求超时（30秒）"
        print_error(f"  请求超时")
        return result
    except requests.exceptions.ConnectionError:
        result["error"] = "无法连接到后端服务"
        print_error(f"  连接失败")
        return result
    except Exception as e:
        result["error"] = f"未预期的错误: {str(e)}"
        print_error(f"  错误: {e}")
        traceback.print_exc()
        return result

def test_all_resource_types() -> Dict[str, Any]:
    """测试所有资源类型"""
    print_section("3. 全面资源类型测试")
    
    results = {}
    total_success = 0
    total_failed = 0
    total_resources = 0
    
    for resource_type in RESOURCE_TYPES:
        result = test_resource_type(resource_type)
        results[resource_type] = result
        
        if result["success"]:
            total_success += 1
            total_resources += result["count"]
        else:
            total_failed += 1
    
    # 汇总结果
    print_section("4. 测试结果汇总")
    
    print(f"\n{Colors.BOLD}总体统计:{Colors.RESET}")
    print(f"  总资源类型数: {len(RESOURCE_TYPES)}")
    print(f"  成功: {Colors.GREEN}{total_success}{Colors.RESET}")
    print(f"  失败: {Colors.RED}{total_failed}{Colors.RESET}")
    print(f"  总资源数: {Colors.BLUE}{total_resources}{Colors.RESET}")
    
    # 详细结果
    print(f"\n{Colors.BOLD}详细结果:{Colors.RESET}")
    for resource_type, result in results.items():
        status_icon = "✅" if result["success"] else "❌"
        status_color = Colors.GREEN if result["success"] else Colors.RED
        
        print(f"  {status_icon} {resource_type.upper():8s} - ", end="")
        if result["success"]:
            print(f"{status_color}成功{Colors.RESET} - {result['count']} 个资源", end="")
            if result["issues"]:
                print(f" {Colors.YELLOW}({len(result['issues'])} 个警告){Colors.RESET}", end="")
        else:
            print(f"{status_color}失败{Colors.RESET} - {result['error']}", end="")
        print()
    
    # 问题汇总
    all_issues = []
    for resource_type, result in results.items():
        if result["issues"]:
            for issue in result["issues"]:
                all_issues.append(f"{resource_type}: {issue}")
        if result["error"]:
            all_issues.append(f"{resource_type}: {result['error']}")
    
    if all_issues:
        print_section("5. 发现的问题")
        for i, issue in enumerate(all_issues, 1):
            print_warning(f"{i}. {issue}")
    else:
        print_section("5. 问题检查")
        print_success("未发现任何问题！")
    
    return {
        "results": results,
        "summary": {
            "total_types": len(RESOURCE_TYPES),
            "success_count": total_success,
            "failed_count": total_failed,
            "total_resources": total_resources,
            "issues": all_issues
        }
    }

def generate_report(test_results: Dict[str, Any]):
    """生成测试报告"""
    print_section("6. 生成测试报告")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = {
        "timestamp": timestamp,
        "test_account": TEST_ACCOUNT,
        "summary": test_results["summary"],
        "details": {}
    }
    
    for resource_type, result in test_results["results"].items():
        report["details"][resource_type] = {
            "success": result["success"],
            "count": result["count"],
            "error": result.get("error"),
            "issues": result.get("issues", []),
            "has_data": result["count"] > 0
        }
    
    # 保存报告
    report_file = f"comprehensive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print_success(f"测试报告已保存: {report_file}")
    
    # 生成Markdown报告
    md_file = f"comprehensive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(f"# 全面系统测试报告\n\n")
        f.write(f"**测试时间**: {timestamp}\n")
        f.write(f"**测试账号**: {TEST_ACCOUNT}\n\n")
        
        f.write(f"## 测试摘要\n\n")
        f.write(f"- 总资源类型数: {test_results['summary']['total_types']}\n")
        f.write(f"- 成功: {test_results['summary']['success_count']}\n")
        f.write(f"- 失败: {test_results['summary']['failed_count']}\n")
        f.write(f"- 总资源数: {test_results['summary']['total_resources']}\n\n")
        
        f.write(f"## 详细结果\n\n")
        f.write(f"| 资源类型 | 状态 | 资源数量 | 问题 |\n")
        f.write(f"|---------|------|---------|------|\n")
        
        for resource_type, result in test_results["results"].items():
            status = "✅ 成功" if result["success"] else "❌ 失败"
            count = result["count"]
            issues = ", ".join(result.get("issues", [])) or (result.get("error") or "无")
            f.write(f"| {resource_type.upper()} | {status} | {count} | {issues} |\n")
        
        if test_results["summary"]["issues"]:
            f.write(f"\n## 发现的问题\n\n")
            for i, issue in enumerate(test_results["summary"]["issues"], 1):
                f.write(f"{i}. {issue}\n")
        else:
            f.write(f"\n## 问题检查\n\n")
            f.write(f"✅ 未发现任何问题！\n")
    
    print_success(f"Markdown报告已保存: {md_file}")
    
    return report_file, md_file

def main():
    """主函数"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("="*60)
    print("  CloudLens 全面系统测试")
    print("  确保所有资源类型查询功能正常")
    print("="*60)
    print(f"{Colors.RESET}\n")
    
    # 1. 健康检查
    if not test_backend_health():
        print_error("后端服务不可用，测试终止")
        sys.exit(1)
    
    # 2. 账号检查
    account = test_account_exists()
    if not account:
        print_error("无法找到测试账号，测试终止")
        sys.exit(1)
    TEST_ACCOUNT = account
    
    # 3. 全面测试
    test_results = test_all_resource_types()
    
    # 4. 生成报告
    report_file, md_file = generate_report(test_results)
    
    # 5. 总结
    print_section("测试完成")
    
    summary = test_results["summary"]
    if summary["failed_count"] == 0 and len(summary["issues"]) == 0:
        print_success("🎉 所有测试通过！系统运行正常！")
        return 0
    else:
        print_warning(f"⚠️  发现 {summary['failed_count']} 个失败项和 {len(summary['issues'])} 个问题")
        print_info(f"请查看测试报告: {md_file}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

