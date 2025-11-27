#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务调度守护进程
"""

import logging
import os
import sys

from core.scheduler import TaskScheduler

# 确保日志目录存在
os.makedirs("logs", exist_ok=True)


def main():
    # 检查配置文件
    if not os.path.exists("schedules.yaml"):
        if os.path.exists("schedules.yaml.example"):
            print("⚠️  未找到 schedules.yaml，将使用 schedules.yaml.example")
            import shutil

            shutil.copy("schedules.yaml.example", "schedules.yaml")
        else:
            print("❌ 未找到 schedules.yaml 配置文件")
            sys.exit(1)

    print("🚀 启动任务调度守护进程...")
    scheduler = TaskScheduler()
    scheduler.start()


if __name__ == "__main__":
    main()
