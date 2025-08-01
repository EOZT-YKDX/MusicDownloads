# -*- coding:utf-8 -*- #

# Author: YKDX
# Version: V1.2.257.174
# Date Creation: 2025/7/17
# Date Modified: 2025/7/30
# Program Name: ProgramEntrance

import os, logging

from datetime import datetime

from NetworkOperations import crawl_favorites
from ConfigurationFile import read_configuration
from ConfigureLogging import file_log, terminal_log
from InformationStatistics import information_statistics
from DataProcessing import name_extraction, data_classification
from ProgramInitialization import tool_detection, path_initialization
from ConcurrentTasks import concurrent_process, concurrent_compression

# 全局变量
START_TIME = 0
LOGGER = logging.getLogger(__name__)
DIVIDING_LINE = "-".center(150, "-")


class Config:
    def __init__(self):
        # 初始化默认配置值
        self.retry = 3
        self.fid = None
        self.page_size = 200
        self.audio_covers = None
        self.audio_format = "mp3"
        self.log_level = logging.INFO
        self.output_path = os.path.dirname(os.getcwd())
        self.dividing_line = "-".center(150, "-")
        self.log_format = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s")

        self.tools = ["ffmpeg", "you-get", "msedgedriver"]
        self.matching_method = [
            r"《(.*?)》",  # 中文书名号
            r"【(.*?)】",  # 中文方括号
            r"\((.*?)\)",  # 英文圆括号
            r"\[(.*?)\]",  # 英文方括号
        ]
        self.invalid_labels = [
            "伴奏", "音质", "歌词版", "完整版", "PHONK",
            "4K60帧", "4K高码率", "hi-res", "音乐推荐", "动态歌词",
        ]

        self.track_label = {
            "Encoder": "YKDX",  # 编码人员
            "Publisher": "YKDX", # 发布者
            "Artist": "EOZT-YKDX出品", # 艺术家
            "Copyright": "©EOZT 2021-2025", # 版权信息
            "Author_URL": "https://github.com/EOZT-YKDX", # 作者URL
        }
        self.timeout_period = {
            "Crawl": 10,
            "File_Compression": {
                "Load": 10, # 加载文件
                "Compress": 10, # 压缩文件
                "Completion": 10, # 压缩完成
            },
        }
        self.file_handler = {
            "BackupCount": 5,  # 备份数量
            "Encoding": "utf-8",  # 编码格式
            "MaxBytes": 5 * 1024 * 1024,  # 单个日志文件大小为5MB
        }
        self.subdirectory = {
            "Log": "Log", # 日志目录
            "Temp": "Temp", # 临时目录
            "Data": "Data", # 数据目录
            "mus_orig": os.path.join("Music", "OriginalAudio"), # 原始音频目录
            "mus_comp": os.path.join("Music", "CompressedAudio"), # 压缩音频目录
        }


    def update_config(self) -> None:
        """
        从配置文件更新配置参数
        :return: None
        """

        config = read_configuration(input_path=self.output_path)

        self.fid = config.get("Fid", self.fid)
        self.retry = config.get("Retry", self.retry)
        self.tools = config.get("Tools", self.tools)
        self.page_size = config.get("Page_Size", self.page_size)
        self.output_path = config.get("OutputPath", self.output_path)
        self.audio_format = config.get("Audio_Format", self.audio_format)
        self.audio_covers = config.get("Audio_Covers", self.audio_covers)
        self.subdirectory = config.get("Subdirectory", self.subdirectory)
        self.track_label = config.get("Track_Information", self.track_label)
        self.invalid_labels = config.get("Invalid_Labels", self.invalid_labels)
        self.timeout_period = config.get("Timeout_Period", self.timeout_period)
        self.matching_method = config.get("Matching_Method", self.matching_method)

        if isinstance(config.get("Logger"), dict):
            log_config = config.get("Logger")
            log_level = log_config.get("Log_Level", "INFO")

            if log_level:
                self.log_level = getattr(logging, log_level)

            log_format = log_config.get(log_level)

            if log_format:
                self.log_format = logging.Formatter(log_format)

            file_handler = log_config.get("File_Handler")

            if file_handler:
                self.file_handler.update(file_handler)

        if config.get("Dividing_Line"):
            divider = config.get("Dividing_Line")

            filler = divider.get("filler", "-")
            length = divider.get("length", 150)

            self.dividing_line = filler.center(length, filler)


def main():
    global LOGGER, START_TIME, DIVIDING_LINE

    START_TIME = datetime.now()

    # 初始化配置
    config = Config()
    config.update_config()

    terminal_logger = terminal_log(log_level=config.log_level, log_format=config.log_format)
    path_result = path_initialization(logger=terminal_logger, directory=config.subdirectory, output_path=config.output_path)
    music_path = path_result.get("mus_orig")

    file_logger = file_log(config=config.file_handler, log_level=config.log_level, log_format=config.log_format, output_path=path_result.get("Log"))

    LOGGER = file_logger
    DIVIDING_LINE = config.dividing_line
    file_logger.warning("MusicDownloader 开始运行")

    tools = tool_detection(tools=config.tools, logger=file_logger)
    crawl_data = crawl_favorites(fid=config.fid, logger=file_logger, retry=config.retry, timeout=config.timeout_period.get("Crawl"), page_size=config.page_size)
    process_data = data_classification(data=crawl_data, logger=file_logger, input_path=music_path)

    if process_data:
        process_config = {
            "output_path": music_path,
            "audio_format": config.audio_format,
            "url_list": list(process_data.keys()),
            "track_information": config.track_label,
            "name_list": [data.get("title", "未知标题") for data in process_data.values()],
        }

        concurrent_process(
            logger=file_logger,
            config=process_config,
        )

        information_statistics(data=process_data, logger=file_logger, dividing_line=config.dividing_line, output_path=path_result.get("Data"))
        name_extraction(logger=file_logger, input_path=music_path, filter_labels=config.invalid_labels, matching_method=config.matching_method)

    concurrent_compression(
        logger=file_logger,
        input_path=music_path,
        output_path=path_result.get("mus_comp"),
        config={"edge_driver": tools.get("msedgedriver")},
    )
    pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        LOGGER.warning(f"MusicDownloader 已停止的运行")
    except Exception as error:
        LOGGER.critical(f"程序崩溃: {error}", exc_info=True)
    finally:
        LOGGER.warning(f"MusicDownloader 运行结束 - 累计时长: {datetime.now() - START_TIME}\n{DIVIDING_LINE}")
