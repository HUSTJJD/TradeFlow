import os
import sys
import time
import glob
import shutil
import logging
from logging.handlers import TimedRotatingFileHandler
from typing import Dict, Any


class CustomFormatter(logging.Formatter):
    """
    自定义日志格式化器，根据日志级别更改格式。

    DEBUG 级别包含时间戳、模块名、级别和消息。
    其他级别仅包含消息。
    """

    def __init__(self) -> None:
        super().__init__()
        # self.debug_formatter = logging.Formatter(
        #     "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        # )
        self.debug_formatter = logging.Formatter(
            "%(message)s"
        )
        self.info_formatter = logging.Formatter("%(message)s")

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno == logging.DEBUG:
            return self.debug_formatter.format(record)
        return self.info_formatter.format(record)


def _archive_old_logs(log_path: str) -> None:
    """
    启动时归档现有的日志文件。

    Args:
        log_path: 当前日志文件的路径。
    """
    if not os.path.exists(log_path):
        return

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_name = f"{log_path}.{timestamp}.log"
    try:
        shutil.copy2(log_path, backup_name)
        # 清空当前日志文件
        with open(log_path, "w") as f:
            f.truncate(0)
    except OSError as e:
        # WinError 32: 进程无法访问文件，因为它正被另一个进程使用
        if e.errno == 32:
            print(f"归档旧日志失败: 文件正在使用中，无法清空。将使用追加模式。")
        else:
            print(f"归档旧日志失败: {e}")
    except Exception as e:
        print(f"归档旧日志失败: {e}")


def _cleanup_old_backups(log_path: str, backup_count: int) -> None:
    """
    清理旧的启动日志备份。

    Args:
        log_path: 日志文件路径（备份的基础）。
        backup_count: 保留的备份数量。
    """
    try:
        # 查找所有 .bak 文件（使用 _archive_old_logs 中的模式）
        # 注意: _archive_old_logs 中的模式使用 .log 后缀作为备份
        bak_pattern = f"{log_path}.*.log"
        bak_files = glob.glob(bak_pattern)
        # 按修改时间排序（最旧的在前）
        bak_files.sort(key=os.path.getmtime)

        # 如果数量超过限制，则删除最旧的文件
        while len(bak_files) >= backup_count:
            oldest_file = bak_files.pop(0)
            try:
                os.remove(oldest_file)
            except OSError as e:
                print(f"删除旧备份 {oldest_file} 失败: {e}")
    except Exception as e:
        print(f"清理旧备份失败: {e}")


def setup_logging(config: Dict[str, Any]) -> None:
    """
    初始化日志配置。

    Args:
        config: 包含 'log' 设置的配置字典。
    """
    log_config = config.get("log", {})
    log_level_str = log_config.get("level", "INFO").upper()
    log_dir = log_config.get("dir", "logs")
    log_filename = log_config.get("filename", "tradeflow.log")
    backup_count = log_config.get("backup_count", 30)
    console_output = log_config.get("console", True)

    # 将日志级别字符串转换为 logging 常量
    log_level = getattr(logging, log_level_str, logging.INFO)

    # 创建日志目录
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except Exception as e:
            print(f"创建日志目录 {log_dir} 失败: {e}")
            return

    log_path = os.path.join(log_dir, log_filename)

    # 获取根记录器
    root_logger = logging.getLogger()

    # 关闭并移除现有处理程序以释放文件锁
    logging.shutdown()
    for handler in root_logger.handlers[:]:
        try:
            handler.close()
        except Exception:
            pass
        root_logger.removeHandler(handler)

    # 归档旧日志并清理备份
    _archive_old_logs(log_path)
    _cleanup_old_backups(log_path, backup_count)

    root_logger.setLevel(log_level)

    # 设置格式化器
    formatter = CustomFormatter()

    # 1. 文件处理程序（按天轮转）
    try:
        file_handler = TimedRotatingFileHandler(
            log_path,
            when="midnight",
            interval=1,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"创建文件日志处理程序失败: {e}")

    # 2. 控制台处理程序
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)

    logging.info(f"日志已初始化。级别: {log_level_str}, 文件: {log_path}")
