# -*- coding:utf-8 -*- #

# Author: YKDX
# Version: V1.2.257.141
# Date Creation: 2025/7/14
# Date Modified: 2025/7/30
# Program Name: ConfigurationFile

import os, yaml, logging

from datetime import datetime

# 默认配置
DEFAULT_CONFIG = {
    # 禁止修改键名参数

    # 配置版本
    "CONFIG_VERSION": "V1.2.257.141",

    # 重试次数
    "Retry": 3,

    # 单次爬取返回数量
    "Page_Size": 200,

    # 收藏夹Fid
    "Fid": "3104892245",

    # 音频格式
    "Audio_Format": "mp3",

    # 禁用符号
    "Forbidden_Symbols": r"\/:*?\"<>|",

    # 输出路径
    "OutputPath": r"C:\Users\Lenovo\Downloads",

    # 外部依赖工具
    "Tools": ["ffmpeg", "you-get", "msedgedriver"],

    # 无效标签
    "Invalid_Labels": [
        "伴奏", "音质", "歌词版", "完整版", "PHONK", "feat.", "studio", "有歌2024", "合成器浪潮", "OST", "4k60帧",
        "4K60帧", "4K高码率", "hi-res", "音乐推荐", "动态歌词", "每日后朋", "碧蓝档案", "歌词排版" "传说之下", "纯音乐分享",
        "日推歌单", "无损音质", "动态歌词排版", "蔚蓝档案", "hi-res百万级录音棚试听", "hi-res无损", "今日宜开心",
    ],

    # 匹配方法
    "Matching_Method": [
        r"《(.*?)》",  # 中文书名号
        r"【(.*?)】",  # 中文方括号
        r"\((.*?)\)",  # 英文圆括号
        r"\[(.*?)\]",  # 英文方括号
    ],

    # 分割线
    "Dividing_Line": {
        "filler": "-", # 分割物
        "length": 150, # 分割线长度
    },

    # 子目录
    "Subdirectory": {
        "Log": "Log", # 日志文件
        "Data": "Data", # 数据文件
        "mus_orig": os.path.join("Music", "OriginalAudio"), # 源音频文件
        "mus_comp": os.path.join("Music", "CompressedAudio"), # 压缩音频文件
    },

    # 音轨信息
    "Track_Information": {
        "Encoder": "YKDX", # 编码人员
        "Publisher": "YKDX", # 发布者
        "Artist": "EOZT-YKDX出品", # 艺术家
        "Copyright": "©EOZT 2021-2025", # 版权信息
        "Author_URL": "https://github.com/EOZT-YKDX", # 作者URL
        "Cover": r"C:\programming\Other-Project\素材\LOGO\EOZT通用图标.png", # 音频封面
    },

    # 超时时间
    "Timeout_Period": {
        # 收藏夹爬取
        "Crawl": 10,
        # 文件压缩
        "File_Compression": {
            "Load": 10, # 加载文件
            "Compress": 10, # 压缩文件
            "Completion": 10, # 压缩完成
        },
    },

    # 日志配置
    "Logger": {
        "Log_Level": "DEBUG",

        # 日志等级对应的格式
        "INFO": "%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
        "DEBUG": "%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s",

        # 文件处理器
        "File_Handler": {
            "BackupCount": 5, # 备份数量
            "Encoding": "utf-8", # 编码格式
            "MaxBytes": 5*1024*1024, # 单个日志文件大小为5MB
        },
    },
}


# 配置初始化
def configure_initialization(output_path: str, logger: logging.Logger) -> None:
    """
    初始化配置文件
    :param output_path: 输出路径
    :param logger: 日志记录器
    :return: None
    """

    start_time = datetime.now()

    if not os.path.isdir(output_path):
        logger.error(f"配置文件输出路径无效: {output_path}")
        return

    configuration_path = os.path.join(output_path, "config.yaml")

    try:
        with open(mode="w", encoding="utf-8", file=configuration_path) as file:
            # 写入默认配置
            yaml.dump(
                indent=4, # 缩进空格
                stream=file, # 文件对象
                sort_keys=False, # 禁止排序
                data=DEFAULT_CONFIG, # 待序列化数据
                Dumper=yaml.SafeDumper, # 安全序列化
                allow_unicode=True # 允许显示非 ASCII 字符
            )
            logger.info(f"配置文件已初始化完成: {configuration_path} - 累计时长: {datetime.now() - start_time}")
    except yaml.YAMLError as yaml_error:
        logger.error(f"YAML序列化错误: {yaml_error}")
    except Exception as error:
        logger.error(f"配置文件初始化失败: {error}")
    pass


# 读取配置文件
def read_configuration(input_path: str) -> dict:
    """
    读取配置文件
    :param input_path: 输入路径
    :return: 配置字典
    """

    if not os.path.isdir(input_path):
        return {}

    configuration_path = os.path.join(input_path, "config.yaml")

    if not os.path.isfile(configuration_path):
        return {}

    try:
        with open(mode="r", encoding="utf-8", file=configuration_path) as file:
            config = yaml.safe_load(file)

        return config
    except Exception as error:
        return error


# 函数测试
if __name__ == "__main__":
    from ConfigureLogging import terminal_log

    folder_path = os.path.dirname(os.getcwd())
    logger = terminal_log(
        log_level=logging.DEBUG,
        log_format=logging.Formatter("%(asctime)s - %(levelname)s - %(lineno)d - %(message)s")
    )

    configure_initialization(logger=logger, output_path=folder_path)

    config = read_configuration(input_path=folder_path)
