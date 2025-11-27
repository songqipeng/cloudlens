#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务调度核心模块
基于 schedule 库实现定时任务调度
"""

import logging
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import schedule
import yaml

from utils.logger import get_logger


class TaskScheduler:
    """任务调度器"""

    def __init__(self, config_path: str = "schedules.yaml"):
        self.config_path = config_path
        self.logger = get_logger("scheduler")
        self.running = False
        self.tasks = []

    def load_config(self) -> Dict[str, Any]:
        """加载调度配置"""
        try:
            if not os.path.exists(self.config_path):
                self.logger.warning(f"配置文件 {self.config_path} 不存在")
                return {}

            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            return {}

    def run_task(self, task_name: str, command: str):
        """执行单个任务"""
        self.logger.info(f"🚀 开始执行任务: {task_name}")
        start_time = datetime.now()

        try:
            # 使用subprocess执行命令
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            duration = (datetime.now() - start_time).total_seconds()

            if result.returncode == 0:
                self.logger.info(f"✅ 任务 {task_name} 执行成功 (耗时: {duration:.2f}s)")
                self.logger.debug(f"输出: {result.stdout}")
            else:
                self.logger.error(f"❌ 任务 {task_name} 执行失败 (耗时: {duration:.2f}s)")
                self.logger.error(f"错误: {result.stderr}")

        except Exception as e:
            self.logger.error(f"❌ 任务 {task_name} 执行异常: {e}")

    def setup_schedules(self):
        """设置调度计划"""
        config = self.load_config()
        schedules = config.get("schedules", [])

        schedule.clear()
        self.tasks = []

        self.logger.info(f"正在配置 {len(schedules)} 个定时任务...")

        for item in schedules:
            name = item.get("name", "未命名任务")
            cron = item.get("cron")  # 暂不支持复杂cron，仅支持简单间隔
            interval = item.get("interval")
            unit = item.get("unit", "minutes")
            command = item.get("command")
            enabled = item.get("enabled", True)

            if not enabled:
                self.logger.info(f"  - 任务 {name} 已禁用，跳过")
                continue

            if not command:
                self.logger.warning(f"  - 任务 {name} 缺少命令配置，跳过")
                continue

            # 构建任务执行函数
            job_func = lambda n=name, c=command: self.run_task(n, c)

            # 配置调度
            try:
                job = None
                if unit == "seconds":
                    job = schedule.every(interval).seconds
                elif unit == "minutes":
                    job = schedule.every(interval).minutes
                elif unit == "hours":
                    job = schedule.every(interval).hours
                elif unit == "days":
                    job = schedule.every(interval).days
                elif unit == "day_at":
                    # 每天特定时间，如 "10:30"
                    time_str = str(interval)
                    job = schedule.every().day.at(time_str)

                if job:
                    job.do(job_func)
                    self.tasks.append(name)
                    self.logger.info(f"  - 任务 {name} 已配置: {unit}={interval}")
                else:
                    self.logger.warning(f"  - 任务 {name} 配置无效: {unit}={interval}")

            except Exception as e:
                self.logger.error(f"  - 任务 {name} 配置失败: {e}")

    def start(self):
        """启动调度器"""
        self.setup_schedules()
        self.running = True
        self.logger.info("⏰ 调度器已启动，按 Ctrl+C 停止")

        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """停止调度器"""
        self.running = False
        self.logger.info("🛑 调度器已停止")


if __name__ == "__main__":
    # 测试运行
    import os

    scheduler = TaskScheduler()
    scheduler.start()
