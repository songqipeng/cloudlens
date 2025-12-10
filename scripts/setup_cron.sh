#!/bin/bash
# Setup Daily Cron Job for CloudLens
# Compatible with Linux and macOS (using crontab)

PROJECT_ROOT=$(cd "$(dirname "$0")/.."; pwd)
SCRIPT_PATH="$PROJECT_ROOT/scripts/daily_tasks.sh"
CRON_JOB="0 9 * * * $SCRIPT_PATH"

echo "🔧 Setting up cron job..."
echo "Command: $CRON_JOB"

# Check if job already exists
(crontab -l 2>/dev/null) | grep -F "$SCRIPT_PATH" >/dev/null

if [ $? -eq 0 ]; then
    echo "⚠️  Job already exists in crontab. Skipping."
else
    # Append to crontab
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Successfully added to crontab."
fi

# Verify
echo "Current Crontab:"
crontab -l | grep CloudLens -A 1
