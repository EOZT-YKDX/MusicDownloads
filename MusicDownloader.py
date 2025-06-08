# -*- coding:utf-8 -*- #

# Author: YKDX
# Version: V8.13.256.17
# Date Creation: 2025/6/1
# Date Modified: 2025/6/8
# Program Name: MusicDownloader

"""
项目介绍:
    1. MusicDownloader是一个用于自动化下载bilibili收藏夹内相关视频，并转换为音频格式的脚本。
    2. 脚本通过调用bilibili的api接口，通过收藏夹指定的fid来爬取相关数据，例如视频bvid和视频标题等。

注意事项:
    1. 未经原作者授权，禁止用于其他用途。
    2. 仅供研究学习使用，切勿用于非法途径。
    3. 本脚本仅提供下载功能，不会将任何信息上传到服务器。
    4. 请不要频繁的使用本脚本，以免对服务器造成过大的压力。
"""

# 导入模块
import os
import re
import time
import logging
import requests
import subprocess
from datetime import datetime
from selenium import webdriver
from fake_useragent import UserAgent
from selenium.webdriver.support import ui
from selenium.webdriver.common.by import By
from logging.handlers import RotatingFileHandler
from selenium.webdriver.edge import options, service
from selenium.common.exceptions import NoSuchElementException
from mutagen.id3 import ID3, TPE1, TIT3, TPUB, TDRC, TCOP, APIC, TENC, WOAR, COMM, TKEY, ID3NoHeaderError

# 创建日志记录器
logger = logging.getLogger("MusicDownloader")

# 全局变量
START_TIME = datetime.now()
DIVIDING_LINE = "-".center(150, "-")
EDGE_DRIVER = r"C:\programming\Tool-Project\msedgedriver.exe"
FILTER_LABELS = ["音质", "歌词版", "完整版", "PHONK", "hi-res", "音乐推荐", "动态歌词", "日推歌单", "无损音质", "hi-res无损", "动态歌词排版"]

# 配置日志
def setup_logging(folder_path: str, level: int = logging.INFO) -> None:
    """
    配置日志记录器的控制台输出流和文件输出流。
    参数:
        log_path (str): 日志文件输出路径。
        level (int): 日志级别，默认为 INFO。
    返回:
        None
    """

    # 设置日志记录器的级别
    logger.setLevel(level)
    # 清除所有已存在的处理器
    logger.handlers.clear()

    if level == logging.DEBUG:
        # DEBUG日志输出格式
        output_format = "%(asctime)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"
    else:
        # 默认日志输出格式
        output_format = "%(asctime)s - %(levelname)s - %(lineno)d - %(message)s"

    # 日志格式
    logger_format = logging.Formatter(fmt=output_format)

    # 控制台输出流
    terminal_handler = logging.StreamHandler()
    # 设置控制台日志等级
    terminal_handler.setLevel(level)
    # 设置控制台日志格式
    terminal_handler.setFormatter(logger_format)
    # 将日志记录器添加到终端日志记录器
    logger.addHandler(terminal_handler)

    # 检查路径是否存在
    if os.path.exists(folder_path):
        log_file = os.path.join(folder_path, f"MusicDownloader{datetime.now().strftime('%Y-%m-%d')}.log")
        # 文件输出流
        file_handler = RotatingFileHandler(
            backupCount=5,  # 最多保留5个日志文件
            encoding="utf-8",  # 编码格式
            filename=log_file,  # 日志文件路径
            maxBytes=5*1024*1024  # 单个日志文件的最大大小为5MB
        )
        # 设置文件日志等级
        file_handler.setLevel(level)
        # 设置文件日志格式
        file_handler.setFormatter(logger_format)
        # 将文件处理器添加到文件日志记录器
        logger.addHandler(file_handler)
    else:
        logger.error(f"路径无效: {folder_path}")

    logger.debug("日志配置完成")
    pass


# 初始化路径
def initialize_paths(folder_path: str, subdirectory: list = None) -> dict:
    """
    初始化路径，自动创建缺失文件夹。
    参数:
        folder_path (str): 父目录路径。
    返回:
        dict: 初始化后的路径列表。
    """

    if not os.path.exists(folder_path):
        logger.error(f"路径无效: {folder_path}")
        exit(1)

    parent_dir = os.path.join(folder_path, "MusicDownloader")

    if not subdirectory:
        # 默认子目录
        subdirectory = {
            "log": os.path.join(parent_dir, "Log"), # 日志文件
            "temp": os.path.join(parent_dir, "Temp"), # 临时文件
            "data": os.path.join(parent_dir, "Data"), # 数据文件
            "mus_orig": os.path.join(parent_dir, "Music", "OriginalAudio"), # 原始音频文件
            "mus_comp": os.path.join(parent_dir, "Music", "CompressedAudio"), # 压缩后的音频文件
        }
    else:
        # 自定义子目录
        subdirectory = {value: os.path.join(parent_dir, value) for value in subdirectory}

    # 创建子目录
    for directory in subdirectory.values():
        os.makedirs(directory, exist_ok=True)

    logger.debug("路径初始化完成")
    return subdirectory


# 爬取收藏夹
def crawl_favorites(fid: str, retry: int = 2, page_size: int = 200) -> dict:
    """
    调用bilibili的api接口，通过fid爬取收藏夹的相关数据。
    参数:
        fid (str): B站收藏夹特定序列。
        retry (int): 重试次数，默认为2。
        page_size (int): 单次返回的数量，默认为200。
    返回:
        dict: 返回爬取的收藏夹数据。
    """

    # 参数校验
    if not 0 <= page_size <= 200:
        logger.info(f"无效的page_size: {page_size} - 最低为1，最高为200 - 已自动调整为200")
        page_size = 200

    if not 0 <= retry <= 5:
        logger.info(f"无效的retry: {retry} - 最低为0，最高为5 - 已自动调整为2")
        retry = 2

    # bilibili的api接口
    url = f"https://api.bilibili.com/x/v1/medialist/resource/list?type=3&biz_id={fid}&ps={page_size}"

    # 重试机制
    for count in range(1, retry+1):
        # 随机生成UserAgent
        user_agent = UserAgent(
            min_percentage=0.1,  # 过滤使用率小于10%的浏览器版本
            fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0" # 备用UserAgent
        )

        try:
            response = requests.get(
                url=url, # 爬取的url
                timeout=3, # 超时时间
                headers={
                    "User-Agent": user_agent.random, # 随机生成的UserAgent
                    "Origin": "https://www.bilibili.com", # 来源域名
                    "Referer": "https://www.bilibili.com/", # 防盗链
                },
            )

            # 检查爬取结果
            if response.status_code == 200 and response.content:
                logger.info(f"收藏夹数据爬取成功: {fid}")
                return response.json()
        except Exception as error:
            logger.error(f"收藏夹数据爬取失败: {error}")

        logger.info(f"爬取超时，等待1秒后启动第{count}重试")
        time.sleep(1)

    logger.error(f"重试过多，停止爬取 - 累计时长: {datetime.now() - START_TIME}")
    exit(1)


# 提取标签
def extract_tags(name: str, path: str) -> bool:
    """
    提取音频文件中的指定标签。
    参数:
        name (str): 标签名称。
        file_path (str): 音频文件路径。
    返回:
        bool: 是否存在指定标签。
    """

    for file in os.listdir(path):
        try:
            audio_file = ID3(os.path.join(path, file))
        except ID3NoHeaderError:
            logger.error(f"音频加载失败: {os.path.basename(path)}")
            continue

        if not "过滤标签" in str(audio_file.getall("COMM")):
            break

        if os.path.splitext(name)[0] in str(audio_file.getall("COMM")):
            return True

    return False


# 数据处理
def data_processing(data: dict, music_dir: str) -> dict:
    """
    处理爬取的收藏夹数据。
    参数:
        data (dict): 爬取的收藏夹数据。
        music_dir (str): 音乐文件存储路径，用于过滤掉已下载的音频。
    返回:
        dict: 处理且分类后的收藏夹数据。
    注意:
        str(参数).encode("gbk", "ignore").decode("gbk")用于处理标题中的无效字符，防止在Windows系统下出现编码错误。
    """

    try:
        media_data = data["data"]["mediaList"]
    except Exception as error:
        logger.error(f"收藏夹数据处理失败: {error}")
        exit(1)

    if not media_data:
        logger.error("收藏夹数据为空")
        exit(1)

    media_result = {
        "bvid": [],  # 视频bvid
        "coin": [],  # 硬币
        "play": [],  # 播放量
        "reply": [],  # 评论数
        "title": [],  # 视频标题
        "share": [],  # 分享数
        "cover": [],  # 视频封面
        "collect": [],  # 收藏数
        "danmaku": [],  # 弹幕数
        "pubtime": [],  # 发布日期
        "thumb_up": [],  # 点赞数
        "duration": [],  # 视频时长
    }
    cnt_info_fields = ["play", "collect", "thumb_up", "share", "coin", "danmaku", "reply"]

    for media in media_data:
        # 清理标题中的无效字符
        media_title = "".join(character for character in media.get("title", "未知标题") if character not in r'\/:*?"<>|')

        # 检查是否已下载过该音频
        if extract_tags(name=media_title, path=music_dir):
            continue

        media_result["title"].append(media_title)
        media_result["bvid"].append(media.get("bv_id", ""))
        media_result["cover"].append(media.get("cover", "未知封面"))

        cnt_info = media.get("cnt_info", {})

        for field in cnt_info_fields:
            field_value = cnt_info.get(field, "0")
            media_result[field].append(str(field_value))

        # 处理视频时长
        try:
            duration = datetime.fromtimestamp(media.get("duration", 0)).strftime("%M:%S")
        except Exception as error:
            duration = "00:00"
            logger.error(f"{media.get("title", "未知标题")} - 视频时长处理失败: {error}")

        media_result["duration"].append(duration)

        # 处理发布日期
        try:
            pubtime = datetime.fromtimestamp(media.get("pubtime", datetime.now().timestamp())).strftime("%Y-%m-%d %H:%M:%S")
        except Exception as error:
            pubtime = "0000-00-00 00:00:00"
            logger.error(f"{media.get("title", "未知标题")} - 发布日期处理失败: {error}")

        media_result["pubtime"].append(pubtime)

    return media_result


# 信息统计
def information_statistics(detail: dict, folder_path: str) -> None:
    """
    统计B站下载的视频数据信息。
    参数:
        detail (dict): 视频详细信息。
        folder_path (str): 文件夹路径。
    返回:
        None
    """

    if not os.path.exists(folder_path):
        logger.error(f"路径无效: {folder_path}")
        return

    quantity_processed = 0

    try:
        for sequence in range(len(detail["title"])):
            video_info = f"""
            《{detail["title"][sequence]}》 ｜ 《{detail["bvid"][sequence]}》

            **视频时长** ｜ {detail["duration"][sequence]}
            **发布日期** ｜ {detail["pubtime"][sequence]}
            **封面链接** ｜ {detail["cover"][sequence]}

            **核心数据**
            播放量: {detail["play"][sequence]}
            评论数: {detail["reply"][sequence]} -*- 转发数: {detail["share"][sequence]} -*- 弹幕数: {detail["danmaku"][sequence]}
            点赞数: {detail["thumb_up"][sequence]} -*- 投币数: {detail["coin"][sequence]} -*- 收藏数: {detail["collect"][sequence]}

            **下载日期** ｜ {datetime.now().strftime("%Y年-%m月-%d日 %H:%M:%S")}

            {DIVIDING_LINE}
            """

            # 写入信息
            with open(os.path.join(folder_path, f"信息统计{datetime.now().strftime("%Y-%m-%d")}.txt"), mode="a+",encoding="utf-8") as file:
                file.write(video_info)

            quantity_processed += 1
            logger.debug(f"视频信息统计成功: {detail["title"][sequence]}")

        logger.info(f"已成功统计 {quantity_processed} 个视频信息 - 累计时长: {datetime.now() - START_TIME}")
    except Exception as error:
        logger.error(f"视频信息统计失败: {error}")

    logger.debug(f"视频信息统计完成")
    pass


# 下载视频
def download_video(bvid: str, video_name: str, folder_path: str, timeout: float = 60) -> None:
    """
    通过 you-get 工具下载bilibili视频。
    参数:
        bvid (str): 视频的bvid序列。
        video_name (str): 视频名称。
        folder_path (str): 视频存放路径。
        timeout (float): 下载超时，默认为20秒。
    返回:
        None
    """

    if not os.path.exists(folder_path):
        logger.error(f"路径无效: {folder_path}")
        exit(1)

    # 格式化下载链接
    if "www.bilibili.com/video/" not in bvid:
        bvid = f"www.bilibili.com/video/{bvid}"

    # 参数校验
    if not 60 <= timeout <= 120:
        timeout = 60
        logger.info(f"无效的timeout: {timeout} - 最低为60，最高为120 - 已自动调整为60")

    # 使用 you-get 下载视频
    you_get_command = [
        "you-get",
        "-n", # 禁止自动合并视频
        bvid,  # 含bvid的B站视频网址
        "--no-caption",  # 禁止下载字幕
        "-O", video_name,  # 指定输出名称
        "-o", folder_path , # 指定输出目录
    ]

    # 重试机制
    for retry in range(1, 4):
        try:
            logger.info(f"开始下载视频: {video_name}")
            command_result = subprocess.run(
                you_get_command,  # 要执行的命令列表
                text=True,  # 以文本模式返回输出的结果
                timeout=timeout,  # 设置超时时间为20秒
                encoding="utf-8",  # 指定输入输出的编码格式
                capture_output=True  # 捕获标准输出和标准错误
            )

            if command_result.returncode == 0:
                logger.debug(f"视频下载成功: {video_name}")
                return

            logger.error(f"视频下载失败: {command_result}")
        except Exception as error:
            logger.error(f"视频下载失败: {error}")

        timeout += 10
        logger.info(f"下载超时更新为{timeout}秒，等待5秒后启动第{retry}重试")
        time.sleep(5)

    logger.error(f"重试过多，跳过本次下载: {video_name}")


# 下载处理
def download_processing(input_path: str, output_path: str, audio_format: str = "mp3") -> None:
    """
    提取视频文件中的音频，输出到指定路径。
    参数:
        input_path (str): 视频输入路径。
        output_path (str): 音频输出路径。
        audio_format (str): 音频格式，默认为mp3格式。
    返回:
        None
    """

    # 音频格式小写化
    audio_format = audio_format.lower()
    # 音频格式格式化
    audio_format = f".{audio_format.lstrip(".")}"

    for file in os.listdir(input_path):
        # 跳过 you-get 下载的纯视频文件
        if file.endswith("[00].mp4"):
            continue

        input_file = os.path.join(input_path, file)
        output_file = os.path.join(output_path, file[:-8] + audio_format)

        # 使用 ffmpeg 提取音频
        ffmpeg_command = [
            "ffmpeg",
            "-y",  # 自动覆盖输出文件
            "-vn",  # 只提取音频流
            "-nostats",  # 不显示进度信息
            "-ac", "2",  # 音频通道数 - 双声道
            output_file,  # 文件输出路径
            "-i", input_file,  # 文件输入路径
            "-f", audio_format,  # 文件输出格式
        ]
        command_result = subprocess.run(
            ffmpeg_command,  # 要执行的命令列表
            text=True,  # 以文本模式返回输出的结果
            encoding="utf-8",  # 指定输入输出的编码格式
            capture_output=True  # 捕获标准输出和标准错误
        )

        if command_result.returncode != 0:
            logger.error(f"视频处理失败: {file}\n{command_result}")
            continue

        logger.info(f"视频处理成功: {os.path.splitext(file)[0]} - 累计时长: {datetime.now() - START_TIME}")
    pass


# 删除文件
def delete_file(folder_path: str) -> None:
    """
    删除指定路径下的所有文件和文件夹。
    参数:
        folder_path (str): 文件夹路径。
    返回:
        None
    """

    if not os.path.exists(folder_path):
        logger.error(f"路径无效: {folder_path}")
        return

    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)

        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                logger.debug(f"成功删除文件: {file}")
        except Exception as error:
            logger.error(f"文件删除失败: {error}")

        try:
            if os.path.isdir(file_path):
                os.rmdir(file_path)
                logger.debug(f"成功删除文件夹: {file}")
        except Exception as error:
            logger.error(f"文件夹删除失败: {error}")
    pass


# 音轨处理
def audio_track_processing(folder_path: str, audio_covers: str) -> None:
    """
    处理音频文件的音轨信息。
    参数:
        folder_path (str): 音频目录路径。
        audio_covers (str): 音频封面路径。
    返回:
        None
    """

    if not os.path.exists(folder_path):
        logger.error(f"路径无效: {folder_path}")
        return

    if not os.path.exists(audio_covers):
        logger.error(f"路径无效: {audio_covers}")
        return

    with open(file=audio_covers, mode="rb") as covers_file:
        quantity_processed = 0
        # 音轨封面文件
        audio_covers = covers_file.read()

        for file in os.listdir(folder_path):
            # 加载音频文件
            try:
                audio_file = ID3(os.path.join(folder_path, file))
            except ID3NoHeaderError:
                logger.error(f"音频加载失败: {file}")
                continue

            # 设置发布者
            audio_file.add(TPUB(encoding=3, text="YKDX"))
            # 设置编码人员
            audio_file.add(TENC(encoding=3, text="YKDX"))
            # 设置作者URL
            audio_file.add(WOAR("https://github.com/EOZT-YKDX"))
            # 设置音轨的艺术家
            audio_file.add(TPE1(encoding=3, text=["EOZT-YKDX出品"]))
            # 设置音轨的版权
            audio_file.add(TCOP(encoding=3, text=["©EOZT 2021-2025"]))
            # 设置音轨的录制年份
            audio_file.add(TDRC(encoding=3, text=[datetime.now().strftime("%Y")]))
            # 设置音轨的封面图片
            audio_file.add(APIC(encoding=3, mime="image/png", type=3, desc="Cover", data=audio_covers))
            # 设置音轨的副标题
            audio_file.add(TIT3(encoding=3, text=[f"发布日期: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"]))

            if not "过滤标签" in str(audio_file.getall("COMM")):
                # 添加过滤标签
                audio_file.add(COMM(
                    text=file,
                    lang="chi",
                    encoding=3,
                    desc="过滤标签",
                ))
                audio_file.add(TKEY(encoding=3, text=file))

            # 保存音轨信息
            audio_file.save(v2_version=3)

            quantity_processed += 1
            logger.debug(f"音轨处理成功: {file}")

    logger.info(f"已成功处理 {quantity_processed} 个音频音轨 - 累计时长: {datetime.now() - START_TIME}")
    pass


# 压缩音频
def compress_audio(input_path: str, output_path: str) -> None:
    """
    压缩音频文件。
    参数:
        folder_path (str): 文件夹路径。
    返回:
        None
    """

    if not os.path.exists(input_path):
        logger.error(f"路径无效: {input_path}")
        exit(1)

    if not os.path.exists(output_path):
        logger.error(f"路径无效: {output_path}")
        exit(1)

    # 随机生成UserAgent
    user_agent = UserAgent(
        min_percentage=0.1,  # 过滤使用率小于10%的浏览器版本
        fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0" # 备用UserAgent
    )

    quantity_processed = 0
    # 下载配置
    download_configuration = {
        "safebrowsing.enabled": True, # 防止下载恶意文件
        "download.directory_upgrade": True, # 允许自动升级下载目录
        "download.prompt_for_download": False, # 禁用下载提示，自动下载文件
        "download.default_directory": output_path, # 设置默认输出目录为output_path
    }

    # 初始化浏览器
    edge_options = options.Options()

    # 不显示浏览器窗口
    edge_options.add_argument("--headless")
    # 启用无痕模式
    edge_options.add_argument("--incognito")
    # 禁用沙盒模式，提高稳定性
    edge_options.add_argument("--no-sandbox")
    # 禁用GPU加速，提高稳定性
    edge_options.add_argument("--disable-gpu")
    # 禁用所有插件
    edge_options.add_argument("--disable-plugins")
    # 设置用户代理
    edge_options.add_argument(f"user-agent={user_agent.random}")
    # 禁用后台网络
    edge_options.add_argument("--disable-background-networking")
    # 禁用图像加载，提高性能
    edge_options.add_argument("--blink-settings=imagesEnabled=false")
    # 隐藏自动化控制特征
    edge_options.add_argument("--disable-blink-features=AutomationControlled")

    # 应用下载配置
    edge_options.add_experimental_option("prefs", download_configuration)
    # 禁用自动化扩展
    edge_options.add_experimental_option(name="useAutomationExtension", value=False)

    logger.debug(f"Edge浏览器初始化完成 - 开始压缩音频 - 累计时长: {datetime.now() - START_TIME}")

    for file in os.listdir(input_path):
        input_file = os.path.join(input_path, file)

        # 跳过特定音频文件
        try:
            audio_file = ID3(input_file)

            if file.endswith("[00].mp4") or "压缩标签" in str(audio_file.getall("COMM")):
                logger.debug(f"已跳过特定的音频文件: {file}")
                continue

        except ID3NoHeaderError:
            logger.debug(f"无效的音频文件: {file}")
            continue

        try:
            # 启动浏览器
            edge_driver = webdriver.Edge(options=edge_options, service=service.Service(EDGE_DRIVER))

            if edge_driver.service.is_connectable():
                logger.debug(f"Edge浏览器启动成功")
        except Exception as error:
            logger.error(f"浏览器启动失败: {error}")
            continue

        # 打开网页
        edge_driver.get(url=r"https://www.youcompress.com/zh-cn/")

        try:
            # 等待文件上传框
            upfile_button = ui.WebDriverWait(edge_driver, timeout=5).until(lambda key: key.find_element(By.NAME, "upfile"))
            # 上传文件
            upfile_button.send_keys(input_file)

            # 等待上传按钮
            submit_button = ui.WebDriverWait(edge_driver, timeout=5).until(lambda key: key.find_element(By.ID, "submitbutton"))
            # 点击上传按钮
            submit_button.click()
        except Exception as error:
            logger.error(f"网页资源加载失败: {error}")
            edge_driver.quit()
            continue

        try:
            # 等待文件压缩完成
            ui.WebDriverWait(edge_driver, timeout=10).until(lambda key: key.find_element(By.CLASS_NAME, "result-message"))
        except Exception as error:
            logger.error(f"文件上传失败: {error}")
            edge_driver.quit()
            continue

        try:
            edge_driver.find_element(By.XPATH, "//*[contains(text(), \"已完成：文件已经压缩完成\")]")
            logger.info(f"原音频已经过压缩: {file} - 累计时长: {datetime.now() - START_TIME}")
            edge_driver.quit()
            continue
        except NoSuchElementException:
            pass

        try:
            download_link = ui.WebDriverWait(edge_driver, timeout=5).until(
                lambda key: key.find_element(By.XPATH, "//a[contains(@href, \"download.php\")]")
            )

            if download_link:
                download_link.click()
                # 检测是否开始下载
                ui.WebDriverWait(edge_driver, 10).until(
                    lambda _: any(download_file.endswith(".crdownload") for download_file in os.listdir(output_path))
                )
                logger.debug(f"开始下载压缩音频: {file}")
        except Exception as error:
            logger.error(f"无法下载压缩音频: {error}")
            edge_driver.quit()
            continue


        try:
            # 检测下载是否完成
            ui.WebDriverWait(edge_driver, 100).until(
                lambda _: not any(complete_file.endswith(".crdownload") for complete_file in os.listdir(output_path))
            )
            logger.info(f"成功下载压缩音频: {file} - 累计时长: {datetime.now() - START_TIME}")

            # 添加新的COMM标签
            audio_file.add(COMM(
                lang="chi",
                encoding=3,
                text="YKDX",
                desc="压缩标签",
            ))
            audio_file.save()

            quantity_processed += 1
        except Exception as error:
            logger.error(f"压缩音频下载失败: {error}")
            continue
        finally:
            # 关闭浏览器
            edge_driver.quit()
    # 删除下载失败的文件
    for file in os.listdir(output_path):
        if file.endswith(".crdownload") or file.endswith(".tmp"):
            os.remove(os.path.join(output_path, file))

    logger.info(f"已成功压缩 {quantity_processed} 个音频文件 - 累计时长: {datetime.now() - START_TIME}")
    pass


# 名称提取
def name_extraction(folder_path: str) -> None:
    """
    提取文件夹内音频的名称，并重命名为匹配的名称。
    参数:
        folder_path (str): 文件夹路径。
    返回:
        None
    """

    if not os.path.exists(folder_path):
        logger.error(f"路径无效: {folder_path}")
        exit(1)

    failed, succeed, invalidity = 0, 0, 0

    # 匹配方法
    matching_method = [
        r"《(.*?)》",  # 中文书名号
        r"【(.*?)】",  # 中文方括号
        r"\((.*?)\)",  # 英文圆括号
        r"\[(.*?)\]",  # 英文方括号
    ]

    for file in os.listdir(folder_path):
        # 使用列表推导式，按照匹配方法提取内容
        matches = [
            match for pattern in matching_method
            for match in re.findall(pattern, file.strip())
            if not any(label.lower() in match.lower() for label in FILTER_LABELS)
        ]

        # 跳过无效匹配
        if not matches:
            invalidity += 1
            logger.info(f"未提取到有效名称标签: {file}")
            continue

        # 重命名文件
        try:
            # 原始音频文件的路径
            orig_path = os.path.join(folder_path, file)
            # 重命名后的文件路径
            rename_file = os.path.join(folder_path, " - ".join(matches) + os.path.splitext(file)[1])

            os.rename(orig_path, rename_file)

            succeed += 1
            logger.info(f"文件重命名成功: {file} -> {os.path.basename(rename_file)}")
        except Exception as error:
            failed += 1
            logger.error(f"文件重命名失败: {error}")

    logger.info(f"文件重命名完成 - 成功: {succeed} - 失败: {failed} - 无效: {invalidity} - 总计: {succeed + failed + invalidity}")
    pass


# 主函数
def main(fid: str, folder_path: str, audio_path: str, logging_level: int = logging.INFO) -> None:
    # 初始化程序
    subdirectory = initialize_paths(folder_path=folder_path)
    setup_logging(folder_path=subdirectory["log"], level=logging_level)

    logger.warning("开始运行 MusicDownloader")
    craw_data = crawl_favorites(fid=fid, retry=2, page_size=200)
    pro_data = data_processing(data=craw_data, music_dir=subdirectory["mus_orig"])
    information_statistics(detail=pro_data, folder_path=subdirectory["data"])

    for bvid, video_name in zip(pro_data["bvid"], pro_data["title"]):
        download_video(bvid=bvid, video_name=video_name, folder_path=subdirectory["temp"])
        download_processing(input_path=subdirectory["temp"], output_path=subdirectory["mus_orig"])
        delete_file(folder_path=subdirectory["temp"])

    audio_track_processing(folder_path=subdirectory["mus_orig"], audio_covers=audio_path)
    name_extraction(folder_path=subdirectory["mus_orig"])

    compress_audio(input_path=subdirectory["mus_orig"], output_path=subdirectory["mus_comp"])
    pass


if __name__ == "__main__":
    fid = "3570962345"
    folder_path = r"C:\Users\Lenovo\Downloads"
    audio_path = r"C:\programming\Other-Project\素材\LOGO\EOZT通用图标.png"

    try:
        main(fid=fid, folder_path=folder_path, audio_path=audio_path, logging_level=logging.INFO)
    except KeyboardInterrupt:
        logger.warning(f"已停止 MusicDownloader 的运行")
    except Exception as error:
        logger.error(error)
    finally:
        logger.warning(f"MusicDownloader 运行结束 - 累计时长: {datetime.now() - START_TIME}\n{DIVIDING_LINE}")