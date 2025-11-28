#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务调度核心模块
基于 schedule 库实现定时任务调度
"""

import logging
import os
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import schedule
from croniter import croniter, CroniterBadCronError
import yaml

from utils.logger import get_logger


class TaskScheduler:
    """任务调度器"""

    def __init__(self, config_path: str = "schedules.yaml"):
        self.config_path = config_path
        self.logger = get_logger("scheduler")
        self.running = False
        self.tasks = []
        self.cron_jobs: List[Dict[str, Any]] = []

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
        self.cron_jobs = []

        self.logger.info(f"正在配置 {len(schedules)} 个定时任务...")

        for item in schedules:
            name = item.get("name", "未命名任务")
            cron_expr = item.get("cron")
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

            # 配置调度：优先使用 cron 表达式，其次间隔/每日 at
            if cron_expr:
                try:
                    next_run = croniter(cron_expr, datetime.now()).get_next(datetime)
                    self.cron_jobs.append(
                        {
                            "name": name,
                            "command": command,
                            "cron": cron_expr,
                            "next_run": next_run,
                        }
                    )
                    self.logger.info(f"  - 任务 {name} 已配置 cron: {cron_expr}, 下次执行 {next_run}")
                    continue
                except (CroniterBadCronError, Exception) as e:
                    self.logger.error(f"  - 任务 {name} cron 表达式无效: {cron_expr}, 错误: {e}")
                    continue

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
                now = datetime.now()

                # 处理 cron 任务
                for job in self.cron_jobs:
                    try:
                        if job.get("next_run") and now >= job["next_run"]:
                            self.run_task(job["name"], job["command"])
                            job["next_run"] = croniter(job["cron"], now).get_next(datetime)
                            self.logger.debug(f"  - 任务 {job['name']} 下次执行时间: {job['next_run']}")
                    except Exception as e:
                        self.logger.error(f"❌ 任务 {job.get('name')} 执行/调度失败: {e}")

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
