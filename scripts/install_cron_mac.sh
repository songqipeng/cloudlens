#!/bin/bash
# 安装 CloudLens 每日定时任务 (macOS launchd)

# 获取项目根目录
PROJECT_ROOT=$(cd "$(dirname "$0")/.."; pwd)
SCRIPT_PATH="$PROJECT_ROOT/scripts/daily_tasks.sh"
PLIST_NAME="com.cloudlens.daily"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

# 确保脚本可执行
chmod +x "$SCRIPT_PATH"

echo "🚀 Installing CloudLens Daily Automation..."
echo "Target Script: $SCRIPT_PATH"

# 创建 plist 文件
cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>$SCRIPT_PATH</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$PROJECT_ROOT/logs/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_ROOT/logs/launchd.error.log</string>
</dict>
</plist>
EOF

# 卸载旧的任务 (如果存在)
launchctl unload "$PLIST_PATH" 2>/dev/null

# 加载新任务
launchctl load "$PLIST_PATH"

echo "✅ Success! Task scheduled for daily at 09:00 AM."
echo "ToCheck logs: tail -f $PROJECT_ROOT/logs/daily_tasks.log"
