# -*- coding:utf-8 -*- #

# Author: YKDX
# Version: V1.2.257.163
# Date Creation: 2025/7/16
# Date Modified: 2025/7/24
# Program Name: ProgramInitialization

import os, shutil, logging

from datetime import datetime


# 路径初始化
def path_initialization(directory: dict, output_path: str, logger: logging.Logger) -> dict:
    """
    自动创建文件夹，返回绝对路径。
    :param directory: 子目录。
    :param logger: 日志记录器。
    :param output_path: 父目录路径。
    :return: 初始化后的路径列表。
    """

    start_time = datetime.now()

    # 检查输出目录是否存在
    if not os.path.isdir(output_path):
        logger.error(f"父目录路径无效: {output_path}")
        return {}

    subdirectory = {}
    parent_dir = os.path.join(output_path, "MusicDownloader")

    # 路径拼接
    for key, value in directory.items():
        # 跳过无效的键值对
        if not key or not value.strip():
            continue

        try:
            subdirectory[key] = os.path.join(parent_dir, value)
        except TypeError:
            logger.error(f"路径拼接错误 - 非字符串类型的值: {value}")
        except Exception as error:
            logger.error(f"路径拼接错误 - {error}: {value}")

    # 创建子目录
    for key, value in list(subdirectory.items()):
        # 跳过存在的子目录
        if os.path.isdir(value):
            continue

        try:
            os.makedirs(value, exist_ok=True)
            logger.debug(f"已创建目录: {value}")
            continue
        except NotADirectoryError:
            logger.error(f"目录创建失败 - 目录名称无效: {value}")
        except Exception as error:
            logger.error(f"目录创建失败 - {error}: {value}")

        # 移除无效的子目录
        subdirectory.pop(key)

    logger.debug(f"路径初始化已完成 - 累计时长: {datetime.now() - start_time}")
    return subdirectory


# 工具检测
def tool_detection(tools: list, logger: logging.Logger) -> dict:
    """
    检测系统环境是否包含依赖工具。
    :param logger: 日志记录器。
    :param tools: 依赖工具列表。
    :return: 依赖工具绝对路径列表。
    """

    tool_list = {}
    missing_tools = []
    failed, succeed = 0, 0
    start_time = datetime.now()

    for tool in tools:
        # 获取命令行工具的绝对路径
        tool_result = shutil.which(tool)

        if not tool_result:
            missing_tools.append(tool)
            failed += 1
            continue

        succeed += 1
        tool_list[tool] = tool_result
        logger.debug(f"{tool} 的绝对路径: {tool_result}")

    if missing_tools:
        logger.error(f"未找到以下依赖工具: {missing_tools}")

    logger.debug(f"依赖工具检测完成 - 成功: {succeed} - 失败: {failed} - 累计时长: {datetime.now() - start_time}")
    return tool_list


# 函数测试
if __name__ == "__main__":
    from ConfigureLogging import terminal_log

    output_path = os.getcwd()
    tools = ["ffmpeg", "you-get", "msedgedriver"]
    directory = {
        "Log": "Log", # 日志文件
        "Temp": "Temp", # 临时文件
        "Data": "Data", # 数据文件
        "mus_orig": os.path.join("Music", "OriginalAudio"), # 源音频文件
        "mus_comp": os.path.join("Music", "CompressedAudio"), # 压缩音频文件
    }
    logger = terminal_log(
        log_level=logging.DEBUG,
        log_format=logging.Formatter("%(asctime)s - %(levelname)s - %(lineno)d - %(message)s")
    )

    tools_list = tool_detection(tools=tools, logger=logger)
    directory_list = path_initialization(logger=logger, directory=directory, output_path=output_path)
    pass
