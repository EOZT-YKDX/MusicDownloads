# -*- coding:utf-8 -*- #

# Author: YKDX
# Version: V1.2.257.163
# Date Creation: 2025/7/16
# Date Modified: 2025/7/22
# Program Name: ConfigureLogging

import os, logging, codecs

from datetime import datetime
from logging.handlers import RotatingFileHandler

# 全局变量
DEFAULT_BACKUP_COUNT = 5
DEFAULT_ENCODING = "UTF-8"
DEFAULT_MAX_BYTES = 5*1024*1024

# 创建日志记录器
logger = logging.getLogger("MusicDownloader")
# 设置日志记录器的级别
logger.setLevel(logging.DEBUG)
# 清除现有Handler
logger.handlers.clear()


# 终端日志
def terminal_log(log_level: int, log_format: logging.Formatter) -> logging.Logger:
    """
    配置日志记录器的终端输出流。
    :param log_level: 日志记录器的级别。
    :param log_format: 日志记录器的格式。
    :return: 配置好的日志记录器。
    """

    start_time = datetime.now()

    # 终端输出流
    terminal_handler = logging.StreamHandler()

    # 设置终端日志等级
    terminal_handler.setLevel(log_level)
    # 设置终端日志格式
    terminal_handler.setFormatter(log_format)

    # 将日志记录器添加到终端日志记录器
    logger.addHandler(terminal_handler)

    logger.debug(f"终端日志配置完成 - 累计时长: {datetime.now() - start_time}")
    return logger


# 文件日志
def file_log(output_path: str, log_level: int, log_format: logging.Formatter, config: dict) -> logging.Logger:
    """
    配置日志记录器的文件输出流。
    :param output_path: 日志文件的输出路径。
    :param log_level: 日志记录器的级别。
    :param log_format: 日志记录器的格式。
    :param config: 日志文件的配置参数。
    :return: 配置好的日志记录器。
    """

    start_time = datetime.now()

    # 检查输出目录是否存在
    if not os.path.isdir(output_path):
        logger.error(f"父目录路径无效: {output_path}")
        return None

    # 日志编码，默认使用全局变量
    log_encoding = config.get("Encoding", DEFAULT_ENCODING)
    # 日志文件大小，默认使用全局变量
    log_max_bytes = config.get("MaxBytes", DEFAULT_MAX_BYTES)
    # 日志备份数量，默认使用全局变量
    log_backup_count = config.get("BackupCount", DEFAULT_BACKUP_COUNT)
    log_name = f"MusicDownloader{datetime.now().strftime('%Y-%m-%d')}.log"

    # 检查编码是否有效
    try:
        codecs.lookup(log_encoding)
    except LookupError:
        logger.error(f"日志编码错误: {log_encoding}，现已修改为{DEFAULT_ENCODING}")
        log_encoding = DEFAULT_ENCODING
    except Exception as error:
        logger.error(f"日志配置错误: {error}，现已修改为{DEFAULT_ENCODING}")
        log_encoding = DEFAULT_ENCODING

    # 检查日志备份数量是否有效
    if not 0 < log_backup_count < 20:
        logger.error(f"日志备份数量错误: {log_backup_count}份，现已修改为{DEFAULT_BACKUP_COUNT}份")
        log_backup_count = DEFAULT_BACKUP_COUNT

    # 检查日志文件大小是否有效
    if not 0 < log_max_bytes < 100*1024*1024:
        logger.error(f"日志文件大小错误: {log_max_bytes/1024/1024}MB，现已修改为{DEFAULT_MAX_BYTES/1024/1024}MB")
        log_max_bytes = DEFAULT_MAX_BYTES

    # 文件输出流
    file_handler = RotatingFileHandler(
        encoding=log_encoding, # 编码格式
        maxBytes=log_max_bytes, # 单个日志文件大小
        backupCount=log_backup_count, # 备份数量
        filename=os.path.join(output_path, log_name), # 日志文件路径
    )

    # 设置文件日志等级
    file_handler.setLevel(log_level)
    # 设置文件日志格式
    file_handler.setFormatter(log_format)

    # 将文件处理器添加到文件日志记录器
    logger.addHandler(file_handler)

    logger.debug(f"文件日志配置完成 - 累计时长: {datetime.now() - start_time}")
    return logger


# 函数测试
if __name__ == "__main__":
    folder_path = os.getcwd()
    config = {
        "BackupCount": 5,
        "Encoding": "UTF-8",
        "MaxBytes": 5 * 1024 * 1024,
    }
    log_format = logging.Formatter("%(asctime)s - %(levelname)s - %(lineno)d - %(message)s")

    termina_logger = terminal_log(
        log_format=log_format,
        log_level=logging.INFO,
    )
    file_logger = file_log(
        config=config,
        log_format=log_format,
        log_level=logging.INFO,
        output_path=folder_path,
    )
    pass
