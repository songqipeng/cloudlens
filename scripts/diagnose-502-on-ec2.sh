#!/usr/bin/env bash
# 在演示环境 EC2 上运行，用于诊断 502（在本地执行：bash scripts/diagnose-502-on-ec2.sh）
# 用法：先 SSH 到实例后，在实例上执行下面命令；或从本机：ssh -i ~/.ssh/cloudlens-key ec2-user@<实例IP> 'bash -s' < scripts/diagnose-502-on-ec2.sh

set -e
echo "=== 1. 端口监听 ==="
ss -tlnp | grep -E ':80|:8000|:3000' || true
echo ""
echo "=== 2. Docker 容器状态 ==="
cd /opt/cloudlens/app 2>/dev/null && docker-compose ps -a 2>/dev/null || echo "目录不存在或 docker-compose 未找到"
echo ""
echo "=== 3. Nginx 配置是否含 alb-health ==="
grep -n "alb-health" /opt/cloudlens/app/nginx.conf 2>/dev/null || echo "无 alb-health 或文件不存在"
echo ""
echo "=== 4. 本机 curl 80 健康检查 ==="
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/health 2>/dev/null && echo " /health" || echo "failed /health"
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/alb-health 2>/dev/null && echo " /alb-health" || echo "failed /alb-health"
echo ""
echo "=== 5. user-data 日志尾部 ==="
tail -80 /var/log/cloudlens-init.log 2>/dev/null || echo "无此日志"
