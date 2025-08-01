# -*- coding:utf-8 -*- #
# Author: YKDX
# Version: V1.2.257.277
# Date Creation: 2025/7/27
# Date Modified: 2025/7/27
# Program Name: ConcurrentTasks

import os, logging, tempfile, concurrent

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from FileCompression import AudioCompressor
from NetworkOperations import download_video
from DataProcessing import download_processing
from AudioTrackProcessing import audio_track_processing


# 处理视频下载
def process_video_download(logger: logging.Logger, config: dict) -> None:
    """
    处理视频下载
    :param config: 配置字典。
    :param logger: 日志记录器。
    :return: None
    """

    required_data = {}
    missing_data = set()
    data_needed = ["video_name", "output_path", "download_url", "audio_format", "track_information"]

    for key in data_needed:
        if key not in config:
            missing_data.add(key)
            continue

        required_data[key] = config[key]

    if missing_data:
        logger.error(f"配置中缺少必要的数据: {' - '.join(missing_data)}")
        return

    input_file = os.path.join(required_data["output_path"], f"{required_data['video_name']}.{required_data['audio_format']}")

    with tempfile.TemporaryDirectory() as temp_dir:
        download_video(logger=logger, download_url=required_data["download_url"], video_name=required_data["video_name"], output_path=temp_dir)
        download_processing(logger=logger, input_path=temp_dir, output_path=required_data["output_path"], audio_format=required_data["audio_format"])
        audio_track_processing(logger=logger, input_file=input_file, track_information=required_data["track_information"])


# 并发处理视频下载
def concurrent_process(logger: logging.Logger, config: dict) -> bool:
    """
    并发处理视频下载
    :param config: 配置字典。
    :param logger: 日志记录器。
    :return: 下载是否成功
    """

    data_needed = ["url_list", "name_list", "output_path", "audio_format", "track_information"]
    missing_data = set(data_needed) - set(config.keys())

    if missing_data:
        logger.error(f"配置中缺少必要的数据: {' - '.join(missing_data)}")
        return False

    url_list = config.get("url_list", [])
    name_list = config.get("name_list", [])
    output_path = config.get("output_path", "")
    audio_format = config.get("audio_format", "mp3")
    track_information = config.get("track_information", {})

    if not os.path.isdir(output_path):
        logger.error(f"音频输出目录无效: {output_path}")
        return False

    if len(url_list) != len(name_list):
        logger.error("URL列表与名称列表长度不匹配")
        return False

    if not url_list or not name_list:
        logger.error("URL列表或名称列表为空")
        return False

    failed = 0
    futures = []
    max_workers = min(10, os.cpu_count() or 5)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for url, video_name in zip(url_list, name_list):
            config = {
                "download_url": url,
                "video_name": video_name,
                "output_path": output_path,
                "audio_format": audio_format,
                "track_information": track_information,
            }

            future = executor.submit(
                process_video_download,
                logger=logger,
                config=config,
            )
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as error:
                logger.error(f"并发下载任务出现错误: {error}")
                failed += 1

        return bool(failed == 0)


# 压缩任务
def compress_task(file: str, input_path: str, output_path: str, config: dict, logger: logging.Logger) -> bool:
    """
    压缩任务
    :param file: 文件名。
    :param input_path: 输入路径。
    :param output_path: 输出路径。
    :param config: 配置字典。
    :param logger: 日志记录器。
    :return: 压缩是否成功
    """

    compressor = AudioCompressor(config=config, logger=logger)

    try:
        result = compressor.compress(
            output_path=output_path,
            input_path=os.path.join(input_path, file),
        )
        return result
    except Exception as error:
        logger.error(f"压缩任务出现错误: {error}")
        return False
    finally:
        # 确保资源释放
        del compressor


# 并发压缩文件
def concurrent_compression(input_path: str, output_path: str, logger: logging.Logger, config: dict) -> bool:
    """
    并发压缩文件
    :param config: 配置字典。
    :param logger: 日志记录器。
    :param input_path: 输入路径。
    :param output_path: 输出路径。
    :return: 压缩是否成功
    """
    start_time = datetime.now()

    if not os.path.isdir(input_path):
        logger.error(f"音频输入目录无效: {input_path}")
        return False

    if not os.path.isdir(output_path):
        logger.error(f"音频输出目录无效: {output_path}")
        return False

    failed = 0
    futures = []
    # 初始化压缩器用于检查已压缩文件
    compressor = AudioCompressor(config=config, logger=logger)
    existing_ids = compressor.get_existing_identifiers(output_path)

    with ThreadPoolExecutor(max_workers=3) as executor:
        for file in os.listdir(input_path):
            input_file = os.path.join(input_path, file)
            file_id = compressor.get_file_identifier(file_path=input_file)

            if file_id in existing_ids:
                logger.debug(f"跳过已压缩的音频: {os.path.splitext(file)[0]}")
                continue

            future = executor.submit(
                compress_task,
                file=file,
                config=config,
                logger=logger,
                input_path=input_path,
                output_path=output_path,
            )
            futures.append(future)

        # 确保资源释放
        del compressor
        logger.info(f"视频文件处理完成 - 待压缩数量: {len(futures)} - 累计时长: {datetime.now() - start_time}")

        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as error:
                logger.error(f"并发压缩任务出现错误: {error}")
                failed += 1

        return bool(failed == 0)


if __name__ == "__main__":
    from ConfigureLogging import terminal_log
    from ProgramInitialization import tool_detection

    tools = ["msedgedriver"]
    input_file = r"C:\Users\Lenovo\Downloads\MusicDownloader\Music\OriginalAudio"
    output_dir = r"C:\Users\Lenovo\Downloads\MusicDownloader\Music\CompressedAudio"
    logger = terminal_log(
        log_level=logging.DEBUG,
        log_format=logging.Formatter("%(asctime)s - %(levelname)s - %(lineno)d - %(message)s")
    )
    tool_path = tool_detection(tools=tools, logger=logger)
    config = {
        "edge_driver": tool_path["msedgedriver"],
        "load_time": 10,
        "compress_time": 20,
        "completion_time": 120,
        "download_configuration": {
            "download.prompt_for_download": False
        }
    }
    compress_result = concurrent_compression(
        config=config,
        logger=logger,
        input_path=input_file,
        output_path=output_dir,
    )
