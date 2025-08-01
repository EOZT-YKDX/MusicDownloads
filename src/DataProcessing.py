# -*- coding:utf-8 -*- #

# Author: YKDX
# Version: V1.3.257.244
# Date Creation: 2025/7/24
# Date Modified: 2025/7/26
# Program Name: DataProcessing

import os, re, time, logging, subprocess

from datetime import datetime
from mutagen.id3 import ID3, ID3NoHeaderError

# 全局变量
DEFAULT_RETRY = 3
DEFAULT_FORMAT = "mp3"
DEFAULT_DURATION = "00:00:00"
DEFAULT_PUBTIME = "0000-00-00 00:00:00"
MATCHING_METHOD = [
    r"\((.*?)\)", # 英文圆括号
    r"\[(.*?)\]", # 英文方括号
    r"\《(.*?)\》", # 中文书名号
    r"\【(.*?)\】", # 中文方括号
]
FILTER_LABELS = [
    "伴奏", "音质", "歌词版", "完整版", "phonk",
    "4k60帧", "4k高码率", "hi-res", "音乐推荐", "动态歌词",
    "日推歌单","无损音质", "歌词排版", "hi-res无损", "动态歌词排版"
]

# 数据分类
def data_classification(data: dict, input_path: str, logger: logging.Logger) -> dict:
    """
    处理收藏夹数据，返回数据分类字典。
    :param data: 收藏夹数据。
    :param logger: 日志记录器，用于记录处理过程中的信息。
    :param input_path: 音乐文件存储路径，用于过滤掉已下载的音频。
    :return: 处理且分类后的收藏夹数据。
    """

    start_time = datetime.now()

    if not data:
        logger.info("收藏夹数据为空，无待下载的音频")
        return {}

    if not os.path.isdir(input_path):
        logger.error(f"音频目录路径无效: {input_path}")
        return {}

    media_data = data.get("data", {}).get("mediaList", [])

    if not media_data:
        logger.info("收藏夹数据为空，无待下载的音频")
        return {}

    file_tag = set()
    media_result = {}
    cnt_info_fields = [
        "coin",  # 硬币
        "play",  # 播放量
        "reply",  # 评论数
        "share",  # 分享数
        "danmaku",  # 弹幕数
        "collect",  # 收藏数
        "thumb_up",  # 点赞数
    ]

    for file in os.listdir(input_path):
        try:
            # 加载音频文件
            audio_file = ID3(os.path.join(input_path, file))
            # 获取音频标签
            audio_tags = audio_file.getall("TIT3")[0]

            if audio_tags:
                file_tag.add(str(audio_tags))
        except ID3NoHeaderError:
            continue
        except Exception as error:
            logger.error(f"音频文件标签获取失败: {error}")
            continue

    for media in media_data:
        media_title = ""
        bvid = media.get("bv_id", "")

        # 过滤标题中的无效字符
        for character in media.get("title", "未知标题"):
            if character in r'\/:*?"<>|':
                continue

            media_title += character

        if not bvid:
            logger.error(f"{media_title} 缺少bvid")
            continue

        if media_title in file_tag:
            logger.debug(f"跳过已下载的音频: {media_title}")
            continue

        cnt_info = media.get("cnt_info", {})
        media_result[bvid] = {
            "title": media_title,
            "pubtime": DEFAULT_PUBTIME,
            "duration": DEFAULT_DURATION,
            "cover": media.get("cover", "未知封面"),
        }

        # 处理核心数据
        for field in cnt_info_fields:
            media_result[bvid][field] = cnt_info.get(field, "0")

        # 处理视频时长
        try:
            media_result[bvid]["duration"] = datetime.fromtimestamp(
                media.get("duration", 0)
            ).strftime("%H:%M:%S") # 格式化为 时:分:秒
        except ValueError as value_error:
            logger.error(f"{media_title} - 视频时长处理失败: 时长无效 - {value_error}")
        except TypeError as type_error:
            logger.error(f"{media_title} - 视频时长处理失败: 类型错误 - {type_error}")
        except (OverflowError, OSError) as time_error:
            logger.error(f"{media_title} - 视频时长处理失败: 超出时间范围 - {time_error}")
        except Exception as error:
            logger.error(f"{media_title} - 视频时长处理失败: {error}")

        # 处理发布日期
        try:
            media_result[bvid]["pubtime"] = datetime.fromtimestamp(
                media.get("pubtime", 0)
            ).strftime("%Y-%m-%d %H:%M:%S") # 格式化为 年-月-日 时:分:秒
        except ValueError as value_error:
            logger.error(f"{media_title} - 发布日期处理失败: 日期无效 - {value_error}")
        except (OverflowError, OSError) as time_error:
            logger.error(f"{media_title} - 发布日期处理失败: 日期超出范围 - {time_error}")
        except TypeError as type_error:
            logger.error(f"{media_title} - 发布日期处理失败: 日期类型错误 - {type_error}")
        except Exception as error:
            logger.error(f"{media_title} - 发布日期处理失败: {error}")

    logger.info(f"视频数据处理完成 - 待下载数量: {len(media_result)} - 累计时长: {datetime.now() - start_time}")
    return media_result


# 名称提取
def name_extraction(input_path: str, logger: logging.Logger, filter_labels: list = None, matching_method: list = None) -> None:
    """
    提取音频名称，重命名为匹配的名称。
    :param input_path: 音频目录路径。
    :param logger: 日志记录器，用于记录处理过程中的信息。
    :param filter_labels: 过滤标签列表，用于排除不需要的标签。
    :param matching_method: 匹配方法列表，用于提取音频名称中的有效部分。
    :return: None
    """

    start_time = datetime.now()
    failed, succeed, invalidity = 0, 0, 0

    if not os.path.exists(input_path):
        logger.error(f"音频目录路径无效: {input_path}")
        return

    if not matching_method:
        matching_method = MATCHING_METHOD

    if not filter_labels:
        filter_labels = FILTER_LABELS

    for file in os.listdir(input_path):
        matches = []
        process_file = file.strip().lower()

        for method in matching_method:
            for match in re.findall(method, process_file):
                if not match or match in filter_labels:
                    continue

                matches.append(match)

        if not matches:
            logger.debug(f"未找到有效匹配: {file}")
            invalidity += 1
            continue

        file_name = " - ".join(matches) + os.path.splitext(file)[1]

        # 原始音频文件的路径
        orig_path = os.path.join(input_path, file)
        # 重命名后的文件路径
        rename_file = os.path.join(input_path, file_name)

        # 重命名文件
        try:
            os.rename(orig_path, rename_file)
            logger.info(f"文件重命名成功: {file} -> {os.path.basename(rename_file)}")
            succeed += 1
            continue
        except FileNotFoundError as found_error:
            logger.error(f"文件重命名失败: 源文件不存在 {found_error}")
        except FileExistsError as exist_error:
            logger.error(f"文件重命名失败: 目标文件已存在 {exist_error}")
        except Exception as error:
            logger.error(f"文件重命名失败: {error}")

        failed += 1

    logger.info(f"文件重命名完成 - 成功: {succeed} - 失败: {failed} - 无效: {invalidity} - 累计时长: {datetime.now() - start_time}")
    pass


# 下载处理
def download_processing(input_path: str, output_path: str, logger: logging.Logger, retry: int = DEFAULT_RETRY, audio_format: str = DEFAULT_FORMAT) -> None:
    """
    通过 ffmpeg 命令行工具将视频文件转换为音频文件。
    :param retry: 重试次数。
    :param audio_format: 音频格式。
    :param input_path: 视频输入路径。
    :param output_path: 音频输出路径。
    :param logger: 日志记录器，用于记录处理过程中的信息。
    :return: None
    """

    start_time = datetime.now()

    # 音频小写格式化
    audio_format = audio_format.lower()
    # 音频后缀格式化
    audio_format = f".{audio_format.lstrip('.')}"

    if not os.path.isdir(input_path):
        logger.error(f"输入目录路径无效: {input_path}")
        return

    if not os.path.isdir(output_path):
        logger.error(f"输出目录路径无效: {output_path}")
        return

    if not 1 <= retry <= 5:
        logger.error(f"无效的重试次数: {retry} - 最低为1，最高为5 - 已自动调整为{DEFAULT_RETRY}")
        retry = DEFAULT_RETRY

    for file in os.listdir(input_path):
        # 拼接文件路径
        input_file = os.path.join(input_path, file)
        output_file = os.path.join(output_path, os.path.splitext(file)[0] + audio_format)

        ffmpeg_command = [
            "ffmpeg",
            "-y",  # 覆盖存在文件
            "-vn",  # 只提取音频流
            "-nostats",  # 禁用进度信息
            "-ac", "2",  # 音频双声通道
            output_file,  # 文件输出路径
            "-i", input_file,  # 文件输入路径
            "-f", audio_format,  # 文件输出格式
        ]

        # 重试机制
        for count in range(1, retry + 1):
            command_result = subprocess.run(
                ffmpeg_command, # 命令列表
                encoding="utf-8",  # 编码格式
                text=True, # 以文本模式返回输出的结果
                errors="replace", # 替换解码错误时无效字符
                capture_output=True # 捕获标准输出和标准错误
            )

            if command_result.returncode == 0:
                logger.info(f"视频转换音频成功: {file} - 累计时长: {datetime.now() - start_time}")
                os.remove(input_file)
                return

            logger.error(f"视频转换音频失败，等待1秒后启动第 {count} 次重试")
            time.sleep(1)

        logger.error(f"视频 {file} 转换音频重试过多，本次处理已跳过")
        os.remove(input_file)
    pass


# 函数测试
if __name__ == "__main__":
    from ConfigureLogging import terminal_log
    from NetworkOperations import crawl_favorites

    input_path = r"C:\Users\Lenovo\Downloads\MusicDownloader\Music\OriginalAudio"
    logger = terminal_log(
        log_level=logging.DEBUG,
        log_format=logging.Formatter("%(asctime)s - %(levelname)s - %(lineno)d - %(message)s")
    )
    data = crawl_favorites(
        retry=2,
        timeout=10,
        page_size=200,
        logger=logger,
        fid="3570962345",
    )

    data_result = data_classification(
        data=data,
        logger=logger,
        input_path=input_path,
    )

    name_extraction(
        logger=logger,
        input_path=input_path,
    )

    download_processing(
        logger=logger,
        input_path=input_path,
        output_path=input_path,
    )
    pass
