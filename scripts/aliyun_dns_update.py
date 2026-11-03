#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云云解析 DNS：根据新 IP 更新 A 记录（用于一键创建资源后联动域名）。
使用方式：
  环境变量：ALIYUN_ACCESS_KEY_ID, ALIYUN_ACCESS_KEY_SECRET, ALIYUN_DNS_DOMAIN, ALIYUN_DNS_RR
  或参数：  --domain songqipeng.com --rr cloudlens --ip 1.2.3.4
"""

import argparse
import json
import os
import sys

# 项目根目录加入 path，便于在任意目录执行
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def load_env_aliyun():
    """从 scripts/.env.aliyun 加载变量（若存在）"""
    env_file = os.path.join(SCRIPT_DIR, ".env.aliyun")
    if not os.path.isfile(env_file):
        return
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:
                    os.environ[k] = v


def get_aliyun_client(access_key_id: str, access_key_secret: str):
    from aliyunsdkcore.client import AcsClient
    return AcsClient(access_key_id, access_key_secret, "cn-hangzhou")


def describe_domain_records(client, domain_name: str, rr: str, record_type: str = "A"):
    """查询域名下指定 RR 和类型的解析记录，返回 RecordId 等"""
    from aliyunsdkcore.request import CommonRequest
    request = CommonRequest()
    request.set_domain("alidns.aliyuncs.com")
    request.set_method("POST")
    request.set_version("2015-01-09")
    request.set_action_name("DescribeDomainRecords")
    request.add_query_param("DomainName", domain_name)
    request.add_query_param("RRKeyWord", rr)
    request.add_query_param("Type", record_type)
    request.add_query_param("PageSize", 50)
    response = client.do_action_with_exception(request)
    data = json.loads(response)
    records = data.get("DomainRecords", {}).get("Record", [])
    if not isinstance(records, list):
        records = [records]
    return [r for r in records if (r.get("RR") or "").strip().lower() == rr.strip().lower()]


def update_domain_record(client, record_id: str, rr: str, record_type: str, value: str, ttl: int = 600):
    """更新一条解析记录的值（如 A 记录改为新 IP）"""
    from aliyunsdkcore.request import CommonRequest
    request = CommonRequest()
    request.set_domain("alidns.aliyuncs.com")
    request.set_method("POST")
    request.set_version("2015-01-09")
    request.set_action_name("UpdateDomainRecord")
    request.add_query_param("RecordId", record_id)
    request.add_query_param("RR", rr)
    request.add_query_param("Type", record_type)
    request.add_query_param("Value", value)
    request.add_query_param("TTL", ttl)
    client.do_action_with_exception(request)


def main():
    load_env_aliyun()
    parser = argparse.ArgumentParser(description="更新阿里云云解析 A 或 CNAME 记录")
    parser.add_argument("--domain", default=os.environ.get("ALIYUN_DNS_DOMAIN"), help="主域名，如 songqipeng.com")
    parser.add_argument("--rr", default=os.environ.get("ALIYUN_DNS_RR"), help="主机记录（子域名），如 cloudlens")
    parser.add_argument("--ip", help="新的 A 记录 IP 地址（与 --cname 二选一）")
    parser.add_argument("--cname", help="新的 CNAME 记录目标（如 ALB 地址，与 --ip 二选一）")
    parser.add_argument("--ttl", type=int, default=600, help="TTL，默认 600")
    args = parser.parse_args()

    domain = (args.domain or "").strip()
    rr = (args.rr or "").strip()
    if not domain or not rr:
        print("错误：请提供 --domain 和 --rr，或设置环境变量 ALIYUN_DNS_DOMAIN、ALIYUN_DNS_RR", file=sys.stderr)
        sys.exit(1)
    if not args.ip and not args.cname:
        print("错误：请提供 --ip（A 记录）或 --cname（CNAME 记录）", file=sys.stderr)
        sys.exit(1)
    if args.ip and args.cname:
        print("错误：--ip 与 --cname 只能二选一", file=sys.stderr)
        sys.exit(1)

    access_key_id = os.environ.get("ALIYUN_ACCESS_KEY_ID", "").strip()
    access_key_secret = os.environ.get("ALIYUN_ACCESS_KEY_SECRET", "").strip()
    if not access_key_id or not access_key_secret:
        print("错误：请设置环境变量 ALIYUN_ACCESS_KEY_ID、ALIYUN_ACCESS_KEY_SECRET，或使用 scripts/.env.aliyun", file=sys.stderr)
        sys.exit(1)

    if args.cname:
        record_type = "CNAME"
        new_value = args.cname.strip()
    else:
        record_type = "A"
        new_value = args.ip.strip()

    try:
        client = get_aliyun_client(access_key_id, access_key_secret)
        records = describe_domain_records(client, domain, rr, record_type)
        if not records:
            print(f"错误：在域名 {domain} 下未找到主机记录为「{rr}」的 {record_type} 记录", file=sys.stderr)
            sys.exit(1)
        rec = records[0]
        record_id = rec.get("RecordId")
        old_value = rec.get("Value", "")
        ttl = int(rec.get("TTL", 600) or 600)
        if args.ttl > 0:
            ttl = args.ttl
        update_domain_record(client, record_id, rr, record_type, new_value, ttl)
        print(f"已更新解析：{rr}.{domain} {record_type} 记录 {old_value} -> {new_value}")
    except Exception as e:
        print(f"更新解析失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
