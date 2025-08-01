# -*- coding:utf-8 -*- #

# Author: YKDX
# Version: V1.2.257.185
# Date Creation: 2025/7/18
# Date Modified: 2025/7/26
# Program Name: NetworkOperations

import os, time, logging, requests, subprocess

from datetime import datetime
from fake_useragent import UserAgent

# 全局变量
DEFAULT_RETRY = 2
DEFAULT_PAGE_SIZE = 200
DEFAULT_CRAWL_TIMEOUT = 5
DEFAULT_DOWNLOAD_TIMEOUT = 60
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"

# 爬取收藏夹
def crawl_favorites(fid: str, logger: logging.Logger, retry: int = DEFAULT_RETRY, timeout: int = DEFAULT_CRAWL_TIMEOUT, page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    """
    调用B站的api接口，通过fid爬取收藏夹的相关数据。
    :param retry: 重试次数。
    :param timeout: 超时时间。
    :param logger: 日志记录器。
    :param fid: B站收藏夹特定序列。
    :param page_size: 单次返回的数量。
    :return: 返回爬取的收藏夹数据。
    """

    start_time = datetime.now()

    if not fid:
        logger.error("请正确填写收藏夹的fid")
        return {}

    if not 1 <= retry <= 5:
        logger.error(f"无效的重试次数: {retry} - 最低为1，最高为5 - 已自动调整为{DEFAULT_RETRY}")
        retry = DEFAULT_RETRY

    if not 0 <= timeout <= 10:
        logger.error(f"无效的超时时间: {timeout} - 最低为2，最高为10 - 已自动调整为{DEFAULT_CRAWL_TIMEOUT}")
        timeout = DEFAULT_CRAWL_TIMEOUT

    if not 1 <= page_size <= 200:
        logger.error(f"无效的单次页面返回数量: {page_size} - 最低为1，最高为200 - 已自动调整为{DEFAULT_PAGE_SIZE}")
        page_size = DEFAULT_PAGE_SIZE

    # B站的api接口
    url = f"https://api.bilibili.com/x/v1/medialist/resource/list?type=3&biz_id={fid}&ps={page_size}"
    # 随机生成UserAgent
    user_agent = UserAgent(
        fallback=DEFAULT_USER_AGENT, # 备用UserAgent
        min_percentage=0.1, # 过滤使用率小于10%的浏览器版本
    )

    # 重试机制
    for count in range(1, retry + 1):
        try:
            response = requests.get(
                url=url, timeout=timeout,
                headers={
                    "Referer": "https://www.bilibili.com", # 防盗链
                    "Origin": "https://www.bilibili.com", # 来源域名
                    "User-Agent": user_agent.random,  # 随机生成的UserAgent
                },
            )
            response_result = response.json()
            response_code = response_result.get("code")

            # 检查爬取结果
            if response.status_code == 200 and response_code == 0:
                logger.info(f"收藏夹 {fid} 数据爬取成功 - 累计时长: {datetime.now() - start_time}")
                return response_result

            logger.error(f"收藏夹 {fid} 数据爬取失败 - 状态码: {response.status_code} - 响应代码: {response_code}")
        except requests.exceptions.Timeout:
            logger.error(f"收藏夹 {fid} 数据爬取超时: {timeout}")
            timeout += min(2 ** count, 5)
        except ValueError as json_error:
            logger.error(f"收藏夹 {fid} 数据JSON解析错误: {json_error}")
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as network_error:
            logger.error(f"收藏夹 {fid} 数据爬取时出现网络错误: {network_error}")
        except Exception as error:
            logger.error(f"收藏夹 {fid} 数据爬取错误: {error}")

        waiting_time = min(2 ** count, 5)
        logger.debug(f"等待 {waiting_time} 秒后收藏夹 {fid} 开始第 {count} 次重试")
        time.sleep(waiting_time)

    logger.error(f"收藏夹 {fid} 数据爬取重试次数过多，爬取已停止 - 累计时长: {datetime.now() - start_time}")
    return {}


# 下载视频
def download_video(video_name: str, output_path: str, download_url: str, logger: logging.Logger, retry: int = DEFAULT_RETRY, timeout: int = DEFAULT_DOWNLOAD_TIMEOUT) -> None:
    """
    通过 you-get 命令行工具下载B站视频。
    :param retry: 重试次数。
    :param logger: 日志记录器。
    :param video_name: 视频名称。
    :param timeout: 下载超时时间。
    :param output_path: 视频输出路径。
    :param download_url: 包含bvid序列的下载链接。
    :return: None
    """

    start_time = datetime.now()

    if not os.path.isdir(output_path):
        logger.error(f"视频输出路径无效: {output_path}")
        return

    # 格式化下载链接
    if "www.bilibili.com/video/" not in download_url:
        download_url = f"www.bilibili.com/video/{download_url}"

    if not 30 <= timeout <= 120:
        logger.error(f"无效的超时时间: {timeout} - 最低为30，最高为120 - 已自动调整为{DEFAULT_DOWNLOAD_TIMEOUT}")
        timeout = DEFAULT_DOWNLOAD_TIMEOUT

    you_get_command = [
        "you-get",
        download_url, # 下载链接
        "--no-caption", # 禁止下载字幕
        "-O", video_name, # 指定输出名称
        "-o", output_path, # 指定输出目录
    ]

    # 重试机制
    for count in range(1, retry + 1):
        try:
            logger.info(f"开始下载视频: {video_name}")
            command_result = subprocess.run(
                you_get_command,
                timeout=timeout, # 超时时间
                text=True, # 以文本模式返回输出的结果
                errors="replace", # 替换解码错误时无效字符
                encoding="utf-8", # 指定输入输出的编码格式
                capture_output=True # 捕获标准输出和标准错误
            )

            if command_result.returncode == 0:
                logger.debug(f"视频下载成功: {video_name} - 累计时长: {datetime.now() - start_time}")
                return
        except subprocess.TimeoutExpired as timeout_error:
            logger.error(f"视频下载失败 - 视频下载超时: {timeout_error}")
        except Exception as error:
            logger.error(f"视频下载失败: {error}")

        timeout += min(3 ** count, 10)
        waiting_time = min(2 ** count, 5)
        logger.error(f"等待 {waiting_time} 秒后视频下载启动第 {count} 次重试，当前超时时间 {timeout} 秒")
        time.sleep(waiting_time)

    logger.error(f"视频下载重试过多，已跳过本次下载: {video_name} - 累计时长: {datetime.now() - start_time}")
    pass


# 函数测试
if __name__ == "__main__":
    from ConfigureLogging import terminal_log

    fid = "3570962345"
    bvid = "BV16MT1zFEQL"
    output_path = r"C:\Users\Lenovo\Downloads"
    logger = terminal_log(
        log_level=logging.DEBUG,
        log_format=logging.Formatter("%(asctime)s - %(levelname)s - %(lineno)d - %(message)s")
    )

    crawl_result = crawl_favorites(
        fid=fid,
        logger=logger,
    )

    download_video(
        logger=logger,
        download_url=bvid,
        video_name="测试视频",
        output_path=output_path,
    )
    pass