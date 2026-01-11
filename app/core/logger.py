import os
import sys
import time
import glob
import shutil
import logging
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = "logs"
LOG_FILE_NAME = "tradeflow.log"
LOG_BACKUP_COUNT = 7

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


def _archive_old_logs() -> None:
    """
    启动时归档现有的日志文件。

    """
    if not os.path.exists(LOG_FILE_NAME):
        return

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_name = f"{LOG_FILE_NAME}.{timestamp}.log"
    try:
        shutil.copy2(LOG_FILE_NAME, backup_name)
        # 清空当前日志文件
        with open(LOG_FILE_NAME, "w") as f:
            f.truncate(0)
    except Exception as e:
        print(f"归档旧日志失败: {e}")


def _cleanup_old_backups() -> None:
    """
    清理旧的启动日志备份。
    """
    try:
        bak_pattern = f"{LOG_FILE_NAME}.*.log"
        bak_files = glob.glob(bak_pattern)
        # 按修改时间排序（最旧的在前）
        bak_files.sort(key=os.path.getmtime)
        # 如果数量超过限制，则删除最旧的文件
        while len(bak_files) >= LOG_BACKUP_COUNT:
            oldest_file = bak_files.pop(0)
            try:
                os.remove(oldest_file)
            except OSError as e:
                print(f"删除旧备份 {oldest_file} 失败: {e}")
    except Exception as e:
        print(f"清理旧备份失败: {e}")


def setup_logging(log_level_str: str) -> None:
    """
    初始化日志配置。

    Args:
        log_level_str: 日志级别字符串。
    """
    log_level = getattr(logging, log_level_str.upper() , logging.INFO)

    # 创建日志目录
    if not os.path.exists(LOG_DIR):
        try:
            os.makedirs(LOG_DIR)
        except Exception as e:
            print(f"创建日志目录 {LOG_DIR} 失败: {e}")
            return

    log_path = os.path.join(LOG_DIR, LOG_FILE_NAME)

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
    _archive_old_logs()
    _cleanup_old_backups()

    root_logger.setLevel(log_level)

    # 设置格式化器
    formatter = CustomFormatter()

    # 1. 文件处理程序（按天轮转）
    try:
        file_handler = TimedRotatingFileHandler(
            log_path,
            when="midnight",
            interval=1,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"创建文件日志处理程序失败: {e}")


    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    logging.info(f"日志已初始化。级别: {log_level_str}, 文件: {log_path}")
