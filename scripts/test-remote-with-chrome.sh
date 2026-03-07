#!/usr/bin/env bash
# 使用 Chrome 测试远端站点 https://cloudlens.songqipeng.com
# 用法：在项目根目录执行 ./scripts/test-remote-with-chrome.sh

set -e
REMOTE_URL="${BASE_URL:-https://cloudlens.songqipeng.com}"

echo "=============================================="
echo "  CloudLens 远端 Chrome 测试"
echo "  目标: $REMOTE_URL"
echo "=============================================="
echo ""

cd "$(dirname "$0")/../web/frontend"
export BASE_URL="$REMOTE_URL"
npx playwright test tests/dashboard-error-display.spec.ts --project=chromium

EXIT_CODE=$?
echo ""
if [ $EXIT_CODE -eq 0 ]; then
  echo "✅ 远端测试通过。"
else
  echo "❌ 远端测试失败。建议："
  echo "   1. SSH 登录服务器查日志: ssh -i ~/.ssh/cloudlens-key ec2-user@<实例IP>"
  echo "   2. 在服务器上: cd /opt/cloudlens/app && docker compose logs --tail=200 backend frontend nginx"
  echo "   3. 本地修复代码后: git add . && git commit -m 'fix: ...' && git push origin main"
  echo "   4. 服务器上重新部署: cd /opt/cloudlens/app && ./scripts/start.sh"
  echo "   详见: docs/迭代测试与部署流程.md"
fi
exit $EXIT_CODE
