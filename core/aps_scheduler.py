"""
APScheduler-based task scheduler
Supports cron expressions, history recording, and optional webhook notification.
"""
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.background import BackgroundScheduler

from utils.logger import get_logger


class APSTaskScheduler:
    """基于 APScheduler 的任务调度器"""

    def __init__(self, config_path: str = "schedules.yaml", history_path: str = "logs/scheduler_history.jsonl"):
        self.config_path = config_path
        self.history_path = history_path
        self.logger = get_logger("aps_scheduler")
        self.scheduler = BackgroundScheduler()

    def load_config(self) -> Dict[str, Any]:
        """加载调度配置"""
        try:
            if not os.path.exists(self.config_path):
                self.logger.warning(f"配置文件 {self.config_path} 不存在")
                return {}

            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            return {}

    def _record_history(self, job_name: str, command: str, success: bool, output: str = "", error: str = ""):
        """记录任务执行历史"""
        Path(self.history_path).parent.mkdir(parents=True, exist_ok=True)
        record = {
            "time": datetime.utcnow().isoformat(),
            "job": job_name,
            "command": command,
            "success": success,
            "output": output.strip(),
            "error": error.strip(),
        }
        try:
            with open(self.history_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.error(f"写入历史记录失败: {e}")

    def _notify(self, webhook: Optional[str], message: str):
        """简单的 webhook 通知（可选）。避免新增依赖，使用 urllib."""
        if not webhook:
            return
        try:
            from urllib import request

            data = json.dumps({"text": message}).encode("utf-8")
            req = request.Request(webhook, data=data, headers={"Content-Type": "application/json"})
            request.urlopen(req, timeout=5)
        except Exception as e:
            self.logger.error(f"发送 webhook 失败: {e}")

    def _run_command(self, job_name: str, command: str, webhook: Optional[str] = None):
        """执行具体命令"""
        self.logger.info(f"🚀 运行任务: {job_name} -> {command}")
        start = datetime.now()
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            duration = (datetime.now() - start).total_seconds()

            if result.returncode == 0:
                self.logger.info(f"✅ 任务 {job_name} 成功 (耗时 {duration:.2f}s)")
                self._record_history(job_name, command, True, output=result.stdout)
            else:
                self.logger.error(f"❌ 任务 {job_name} 失败 (耗时 {duration:.2f}s)")
                self.logger.error(result.stderr)
                self._record_history(job_name, command, False, error=result.stderr)
                self._notify(webhook, f"[CloudLens Scheduler] 任务失败: {job_name}\n{result.stderr}")
        except Exception as e:
            self.logger.error(f"❌ 任务 {job_name} 异常: {e}")
            self._record_history(job_name, command, False, error=str(e))
            self._notify(webhook, f"[CloudLens Scheduler] 任务异常: {job_name}\n{e}")

    def _on_event(self, event):
        """监听 APScheduler 事件，记录日志"""
        if event.exception:
            self.logger.error(f"任务执行异常: {event.job_id}")
        else:
            self.logger.debug(f"任务执行完成: {event.job_id}")

    def setup_jobs(self):
        """解析配置并注册任务"""
        config = self.load_config()
        schedules = config.get("schedules", [])

        self.scheduler.remove_all_jobs()
        self.scheduler.add_listener(self._on_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

        self.logger.info(f"正在配置 {len(schedules)} 个 APScheduler 任务...")

        for item in schedules:
            name = item.get("name", "未命名任务")
            cron_expr = item.get("cron")
            command = item.get("command")
            enabled = item.get("enabled", True)
            webhook = item.get("webhook")

            if not enabled:
                self.logger.info(f"  - 任务 {name} 已禁用，跳过")
                continue
            if not command:
                self.logger.warning(f"  - 任务 {name} 缺少命令配置，跳过")
                continue
            if not cron_expr:
                self.logger.warning(f"  - 任务 {name} 缺少 cron 表达式，跳过")
                continue

            try:
                self.scheduler.add_job(
                    lambda n=name, c=command, w=webhook: self._run_command(n, c, w),
                    "cron",
                    id=name,
                    **self._parse_cron(cron_expr),
                    replace_existing=True,
                )
                next_run = self.scheduler.get_job(name).next_run_time
                self.logger.info(f"  - 任务 {name} 已配置: cron={cron_expr}, 下次执行 {next_run}")
            except Exception as e:
                self.logger.error(f"  - 任务 {name} 配置失败: {e}")

    @staticmethod
    def _parse_cron(cron_expr: str) -> Dict[str, Any]:
        """
        将标准5字段或6字段的 cron 表达式转换为 APScheduler 的参数。
        支持：min hour day month day_of_week [year]
        """
        parts = cron_expr.strip().split()
        if len(parts) not in (5, 6):
            raise ValueError("仅支持5或6段 cron 表达式")

        keys = ["minute", "hour", "day", "month", "day_of_week", "year"]
        mapping = dict(zip(keys, parts + ["*"] * (6 - len(parts))))
        return {k: v for k, v in mapping.items() if v != "*" or k == "day_of_week"}

    def start(self):
        """启动调度器"""
        self.setup_jobs()
        self.scheduler.start()
        self.logger.info("⏰ APScheduler 调度器已启动（Ctrl+C 停止）")

    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown(wait=False)
        self.logger.info("🛑 APScheduler 调度器已停止")


def main():
    """守护进程入口"""
    scheduler = APSTaskScheduler()
    scheduler.start()
    try:
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()


if __name__ == "__main__":
    main()
