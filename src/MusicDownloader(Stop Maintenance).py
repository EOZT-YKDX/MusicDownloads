# -*- coding:utf-8 -*- #

# Author: YKDX
# Version: V10.13.256.216
# Date Creation: 2025/6/21
# Date Modified: 2025/6/23
# Program Name: MusicDownloader

"""
项目介绍:
    1. MusicDownloader 自动化爬取B站收藏夹数据，
       通过数据处理，下载对应视频，转换文件格式，最后压缩输出。
    2. 脚本通过调用B站的api接口，通过收藏夹指定的fid来爬取相关数据。

注意事项:
    1. 未经原作者授权，禁止用于其他用途。
    2. 仅供研究学习使用，切勿用于非法途径。
    3. 本脚本仅提供下载功能，不会将任何信息上传到服务器。
    4. 请不要频繁的使用本脚本，以免对服务器造成过大的压力。
"""

from datetime import datetime
from selenium import webdriver
from fake_useragent import UserAgent
from selenium.webdriver.support import ui
from selenium.webdriver.common.by import By
from logging.handlers import RotatingFileHandler
from selenium.webdriver.edge import options, service
from mutagen.id3 import ID3, TPE1, TIT3, TPUB, TDRC, TCOP, APIC, TENC, WOAR, TKEY, ID3NoHeaderError

import re, os, time, shutil, logging, requests, subprocess, concurrent.futures

# 创建日志记录器
logger = logging.getLogger("MusicDownloader")

# 全局变量
TOOLS = {}
START_TIME = datetime.now()
DIVIDING_LINE = "-".center(150, "-")
FILTER_LABELS = [
    "伴奏", "音质", "歌词版", "完整版", "PHONK",
    "4K60帧", "4K高码率", "hi-res", "音乐推荐", "动态歌词",
    "日推歌单","无损音质", "hi-res无损", "动态歌词排版",
]

# 配置日志
def setup_logging(output_path: str, level: int = logging.INFO) -> None:
    """
    配置日志记录器的控制台输出流和文件输出流。
    参数:
        output_path (str): 日志输出路径。
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
    if os.path.exists(output_path):
        log_file = os.path.join(output_path, f"MusicDownloader{datetime.now().strftime('%Y-%m-%d')}.log")
        # 文件输出流
        file_handler = RotatingFileHandler(
            backupCount=5,  # 备份数量
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
        logger.error(f"日志输出路径无效: {output_path}")

    logger.debug("日志配置完成")
    pass


# 初始化路径
def initialize_paths(input_path: str) -> dict:
    """
    自动创建文件夹，返回绝对路径。
    参数:
        input_path (str): 父目录路径。
    返回:
        dict: 初始化后的路径列表。
    """

    if not os.path.exists(input_path):
        logger.error(f"父目录路径无效: {input_path}")
        exit(1)

    parent_dir = os.path.join(input_path, "MusicDownloader")
    temp_path = os.path.join(parent_dir, "Temp")

    if os.path.exists(temp_path):
        # 删除临时目录
        shutil.rmtree(temp_path)

    # 默认子目录
    subdirectory = {
        "temp": temp_path, # 临时文件
        "log": os.path.join(parent_dir, "Log"), # 日志文件
        "data": os.path.join(parent_dir, "Data"), # 数据文件
        "mus_orig": os.path.join(parent_dir, "Music", "OriginalAudio"), # 源音频文件
        "mus_comp": os.path.join(parent_dir, "Music", "CompressedAudio"), # 压缩音频文件
    }

    # 创建子目录
    for directory in subdirectory.values():
        os.makedirs(directory, exist_ok=True)

    return subdirectory


# 工具检测
def tool_detection(tools: list) -> None:
    """
    检测系统环境是否包含必要的命令行工具，
    将命令行工具的绝对路径更新至全局TOOLS字典
    参数:
        tools (list): 命令行工具列表。
    返回:
        None
    """

    # 更新全局变量
    global TOOLS

    for tool in tools:
        # 获取命令行工具的绝对路径
        tool_result = shutil.which(tool)

        if tool_result:
            TOOLS[tool] = tool_result
            logger.debug(f"{tool} 检测成功: {tool_result}")
        else:
            logger.error(f"未检测到 {tool} 工具，请安装后重试")
            exit(1)

    logger.debug("工具检测完成")
    pass


# 爬取收藏夹
def crawl_favorites(fid: str, page_size: int = 200) -> dict:
    """
    调用B站的api接口，通过fid爬取收藏夹的相关数据。
    参数:
        fid (str): B站收藏夹特定序列。
        retry (int): 重试次数，默认为2。
        page_size (int): 单次返回的数量，默认为200。
    返回:
        dict: 返回爬取的收藏夹数据。
    """

    # 参数校验
    if not 1 <= page_size <= 200:
        logger.error(f"无效的单次页面返回数据数量: {page_size} - 最低为1，最高为200 - 已自动调整为200")
        page_size = 200

    timeout = 5
    # B站的api接口
    url = f"https://api.bilibili.com/x/v1/medialist/resource/list?type=3&biz_id={fid}&ps={page_size}"

    # 重试机制
    for count in range(1, 3):
        # 随机生成UserAgent
        user_agent = UserAgent(
            min_percentage=0.1,  # 过滤使用率小于10%的浏览器版本
            fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0" # 备用UserAgent
        )

        try:
            response = requests.get(
                url=url, # 爬取的url
                timeout=timeout, # 超时时间
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
        timeout += 5
        time.sleep(1)

    logger.error(f"重试过多，停止爬取 - 累计时长: {datetime.now() - START_TIME}")
    exit(1)


# 数据处理
def data_processing(data: dict, input_path: str) -> dict:
    """
    处理爬取的收藏夹数据，并返回数据分类字典。
    参数:
        data (dict): 爬取的收藏夹数据。
        input_path (str): 音乐文件存储路径，用于过滤掉已下载的音频。
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
        logger.error("收藏夹数据为空，无待下载的音频")
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
    cnt_info_fields = [
        "coin", # 硬币
        "play", # 播放量
        "reply", # 评论数
        "share", # 分享数
        "danmaku", # 弹幕数
        "collect", # 收藏数
        "thumb_up", # 点赞数
    ]

    for media in media_data:
        download_status = False
        # 清理标题中的无效字符
        media_title = "".join(character for character in media.get("title", "未知标题") if character not in r'\/:*?"<>|')

        # 过滤掉已下载的音频
        for file in os.listdir(input_path):
            try:
                audio_file = ID3(os.path.join(input_path, file))
            except ID3NoHeaderError:
                continue

            # 检查标题是否与已下载的音频标签匹配
            if os.path.splitext(media_title)[0] in str(audio_file.getall("TKEY")):
                download_status = True

        if download_status:
            logger.debug(f"跳过已下载的音频: {media_title}")
            continue

        media_result["title"].append(media_title)
        media_result["bvid"].append(media.get("bv_id", ""))
        media_result["cover"].append(media.get("cover", "未知封面"))

        cnt_info = media.get("cnt_info", {})

        # 处理核心数据
        for field in cnt_info_fields:
            field_value = cnt_info.get(field, "0")
            media_result[field].append(str(field_value))

        # 处理视频时长
        try:
            duration = datetime.fromtimestamp(
                media.get("duration", 0)  # 视频时长，单位为秒，默认为0
            ).strftime("%M:%S")  # 格式化为 分:秒
        except Exception as error:
            logger.error(f"{media.get("title", "未知标题")} - 视频时长处理失败: {error}")
            duration = "00:00"

        media_result["duration"].append(duration)

        # 处理发布日期
        try:
            pubtime = datetime.fromtimestamp(
                media.get("pubtime", datetime.now().timestamp())  # 发布日期，单位为秒，默认为当前时间戳
            ).strftime("%Y-%m-%d %H:%M:%S")  # 格式化为 年-月-日 时:分:秒
        except Exception as error:
            pubtime = "0000-00-00 00:00:00"
            logger.error(f"{media.get("title", "未知标题")} - 发布日期处理失败: {error}")

        media_result["pubtime"].append(pubtime)

    return media_result


# 信息统计
def information_statistics(detail: dict, output_path: str) -> None:
    """
    统计B站下载视频的数据信息。
    参数:
        detail (dict): 视频详细信息。
        output_path (str): 文件夹路径。
    返回:
        None
    """

    if not os.path.exists(output_path):
        logger.error(f"信息统计输出路径无效: {output_path}")
        return

    try:
        quantity_processed = 0

        for sequence, title  in enumerate(detail["title"]):
            video_info = f"""
            《{title}》 ｜ 《{detail["bvid"][sequence]}》

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

            # 输出信息
            with open(
                    os.path.join(output_path, f"信息统计{datetime.now().strftime("%Y-%m-%d")}.txt"), # 输出路径
                    encoding="utf-8", # 编码格式
                    mode="a+", # 追加模式
            ) as file:
                # 写入信息
                file.write(video_info)

            quantity_processed += 1
            logger.debug(f"视频信息统计成功: {title}")

        logger.info(f"已成功统计 {quantity_processed} 个视频信息 - 累计时长: {datetime.now() - START_TIME}")
    except Exception as error:
        logger.error(f"视频信息统计失败: {error}")

    logger.debug(f"视频信息统计完成")
    pass


# 下载视频
def download_video(bvid: str, video_name: str, output_path: str, timeout: float = 60) -> None:
    """
    通过 you-get 工具下载B站视频。
    参数:
        bvid (str): 视频bvid序列。
        video_name (str): 视频名称。
        output_path (str): 视频输出路径。
        timeout (float): 下载超时，默认为20秒。
    返回:
        None
    """

    if not os.path.exists(output_path):
        logger.error(f"视频输出路径无效: {output_path}")
        exit(1)

    # 格式化下载链接
    if "www.bilibili.com/video/" not in bvid:
        bvid = f"www.bilibili.com/video/{bvid}"

    # 参数校验
    if not 60 <= timeout <= 120:
        logger.error(f"无效的timeout: {timeout} - 最低为60，最高为120 - 已自动调整为60")
        timeout = 60

    # 使用 you-get 下载视频
    you_get_command = [
        TOOLS["you-get"] if TOOLS["you-get"] else "you-get", # 要执行的命令
        "-n", # 禁止自动合并视频
        bvid, # 含bvid的B站视频网址
        "--no-caption", # 禁止下载字幕
        "-O", video_name, # 指定输出名称
        "-o", output_path, # 指定输出目录
    ]

    # 重试机制
    for retry in range(1, 4):
        try:
            logger.info(f"开始下载视频: {video_name}")
            command_result = subprocess.run(
                you_get_command, # 要执行的命令列表
                text=True, # 以文本模式返回输出的结果
                timeout=timeout, # 设置超时时间为20秒
                encoding="utf-8", # 指定输入输出的编码格式
                capture_output=True # 捕获标准输出和标准错误
            )

            if command_result.returncode == 0:
                logger.debug(f"视频下载成功: {video_name}")
                return
        except Exception as error:
            logger.error(f"视频下载失败: {error}")

        timeout += 10
        logger.error(f"下载超时更新为{timeout}秒，等待5秒后启动第{retry}次重试")
        time.sleep(5)

    logger.error(f"重试过多，跳过本次下载: {video_name}")
    pass


# 下载处理
def download_processing(input_path: str, output_path: str, audio_format: str = "mp3") -> None:
    """
    通过 ffmpeg 提取视频文件中的音频，输出到指定路径。
    参数:
        input_path (str): 视频输入路径。
        output_path (str): 音频输出路径。
        audio_format (str): 音频格式，默认为mp3格式。
    返回:
        None
    """

    # 音频小写格式化
    audio_format = audio_format.lower()
    # 音频后缀格式化
    audio_format = f".{audio_format.lstrip(".")}"

    for file in os.listdir(input_path):
        # 跳过 you-get 下载的纯视频文件
        if file.endswith("[00].mp4"):
            continue

        # 拼接文件路径
        input_file = os.path.join(input_path, file)
        output_file = os.path.join(output_path, file[:-8] + audio_format)

        # 使用 ffmpeg 提取音频
        ffmpeg_command = [
            TOOLS["ffmpeg"] if TOOLS["ffmpeg"] else "ffmpeg", # 要执行的命令
            "-y", # 覆盖存在文件
            "-vn", # 只提取音频流
            "-nostats", # 禁用进度信息
            "-ac", "2", # 音频双声通道
            output_file, # 文件输出路径
            "-i", input_file, # 文件输入路径
            "-f", audio_format, # 文件输出格式
        ]

        # 重试机制
        for retry in range(1, 3):
            command_result = subprocess.run(
                ffmpeg_command, # 要执行的命令列表
                text=True, # 以文本模式返回输出的结果
                encoding="utf-8", # 指定输入输出的编码格式
                capture_output=True # 捕获标准输出和标准错误
            )

            if command_result.returncode == 0:
                logger.info(f"视频处理成功: {file} - 累计时长: {datetime.now() - START_TIME}")
                return

            logger.error(f"视频处理失败，等待1秒后启动第{retry}次重试")
            time.sleep(1)

        logger.error(f"重试过多，跳过本次处理: {file}")
    pass


# 音轨处理
def audio_track_processing(input_path: str, audio_covers: str) -> None:
    """
    处理音频文件的音轨信息。
    参数:
        input_path (str): 音频目录路径。
        audio_covers (str): 音频封面路径。
    返回:
        None
    """

    if not os.path.exists(input_path):
        logger.error(f"音频目录路径无效: {input_path}")
        return

    if not os.path.exists(audio_covers):
        logger.error(f"音频封面路径无效: {audio_covers}")
        return

    with open(file=audio_covers, mode="rb") as covers_file:
        # 读取音轨封面
        audio_covers = covers_file.read()
        quantity_processed = 0

    for file in os.listdir(input_path):
        # 加载音频文件
        try:
            audio_file = ID3(os.path.join(input_path, file))
        except ID3NoHeaderError:
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

        if not audio_file.get("TKEY"):
            # 添加标签
            audio_file.add(
                TKEY(
                    text=file, # 标签文本
                    encoding=3, # 编码格式
                )
            )

        # 保存音轨信息
        try:
            audio_file.save(v2_version=3)
        except Exception as error:
            logger.error(f"音轨标签保存失败: {error}")
            continue

        quantity_processed += 1
        logger.debug(f"音轨处理成功: {file}")

    logger.info(f"已成功处理 {quantity_processed} 个音频音轨 - 累计时长: {datetime.now() - START_TIME}")
    pass


# 名称提取
def name_extraction(input_path: str) -> None:
    """
    提取文件夹内音频的名称，并重命名为匹配的名称。
    参数:
        input_path (str): 音频目录路径。
    返回:
        None
    """

    if not os.path.exists(input_path):
        logger.error(f"音频目录路径无效: {input_path}")
        exit(1)

    failed, succeed, invalidity = 0, 0, 0

    # 匹配方法
    matching_method = [
        r"《(.*?)》",  # 中文书名号
        r"【(.*?)】",  # 中文方括号
        r"\((.*?)\)",  # 英文圆括号
        r"\[(.*?)\]",  # 英文方括号
    ]

    for file in os.listdir(input_path):
        # 使用列表推导式，按照匹配方法提取内容
        matches = [
            match for pattern in matching_method
            for match in re.findall(pattern, file.strip())
            if not any(label.lower() in match.lower() for label in FILTER_LABELS)
        ]

        # 跳过无效匹配
        if not matches:
            logger.debug(f"未提取到有效名称标签: {file}")
            invalidity += 1
            continue

        # 重命名文件
        try:
            # 原始音频文件的路径
            orig_path = os.path.join(input_path, file)
            # 重命名后的文件路径
            rename_file = os.path.join(input_path, " - ".join(matches) + os.path.splitext(file)[1])

            os.rename(orig_path, rename_file)

            logger.info(f"文件重命名成功: {file} -> {os.path.basename(rename_file)}")
            succeed += 1
        except Exception as error:
            logger.error(f"文件重命名失败: {error}")
            failed += 1

    logger.info(f"文件重命名完成 - 成功: {succeed} - 失败: {failed} - 无效: {invalidity} - 总计: {succeed+failed+invalidity}")
    pass


# 下载任务
def download_task(bvid: str, video_name: str, input_path: str, output_path: str) -> None:
    """
    调用多个模块，为并行下载视频提供捆绑支持。
    参数:
        bvid (str): 视频bvid序列。
        video_name (str): 视频名称。
        input_path (str): 视频输入路径。
        output_path (str): 音频输出路径。
    返回:
        None
    """

    if not os.path.exists(input_path):
        logger.error(f"视频输入路径无效: {input_path}")
        return

    if not os.path.exists(output_path):
        logger.error(f"音频输出路径无效: {output_path}")
        return

    # 拼接文件路径
    folder_path = os.path.join(input_path, video_name)
    temp_path = os.path.join(folder_path, "temp")

    # 创建文件夹
    os.makedirs(folder_path, exist_ok=True)
    os.makedirs(temp_path, exist_ok=True)

    download_video(bvid=bvid, video_name=video_name, output_path=temp_path)
    download_processing(input_path=temp_path, output_path=output_path)

    # 删除临时下载文件
    shutil.rmtree(folder_path)
    pass


# 压缩音频
def compress_audio(input_path: str, output_path: str, temp_path: str) -> None:
    """
    压缩音频文件，输出到指定文件夹。
    参数:
        temp_path (str): 临时文件路径。
        input_path (str): 文件输入路径。
        output_path (str): 文件输出路径。
    返回:
        None
    """

    if not os.path.exists(temp_path):
        logger.error(f"文件临时路径无效: {temp_path}")
        return

    if not os.path.exists(input_path):
        logger.error(f"文件输入路径无效: {input_path}")
        return

    if not os.path.exists(output_path):
        logger.error(f"文件输出路径无效: {output_path}")
        return

    # 加载音频文件
    try:
        tag_list = []
        input_audio = ID3(input_path)
    except ID3NoHeaderError:
        return

    # 添加输出文件标签
    for file in os.listdir(output_path):
        file_path = os.path.join(output_path, file)

        if not os.path.isfile(file_path):
            continue

        try:
            output_audio = ID3(file_path)
            tag_list.append(str(output_audio.getall("TKEY")))
        except ID3NoHeaderError:
            continue

    # 跳过已压缩的音频文件
    if str(input_audio.getall("TKEY")) in tag_list:
        logger.debug(f"跳过已压缩的音频文件: {os.path.basename(input_path)}")
        return

    # 随机生成UserAgent
    user_agent = UserAgent(
        min_percentage=0.1,  # 过滤使用率小于10%的浏览器版本
        fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0" # 备用UserAgent
    )

    temp_path = os.path.join(temp_path, os.path.splitext(os.path.basename(input_path))[0])
    # 下载配置
    download_configuration = {
        "safebrowsing.enabled": True, # 防止下载恶意文件
        "download.directory_upgrade": True, # 允许自动升级下载目录
        "download.prompt_for_download": False, # 禁用下载提示，自动下载文件
        "download.default_directory": temp_path, # 设置默认输出目录为temp_path
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
    # 禁用扩展
    edge_options.add_argument("--disable-extensions")
    # 解决/dev/shm不足问题
    edge_options.add_argument("--disable-dev-shm-usage")
    # 禁用备用呈现器
    edge_options.add_argument("--disable-software-rasterizer")
    # 设置用户代理
    edge_options.add_argument(f"user-agent={user_agent.random}")
    # 禁用后台网络
    edge_options.add_argument("--disable-background-networking")
    # 防止标签页被后台化
    edge_options.add_argument("--disable-renderer-backgrounding")
    # 禁用图像加载，提高性能
    edge_options.add_argument("--blink-settings=imagesEnabled=false")
    # 隐藏自动化控制特征
    edge_options.add_argument("--disable-blink-features=AutomationControlled")

    # 应用下载配置
    edge_options.add_experimental_option("prefs", download_configuration)
    # 禁用自动化扩展
    edge_options.add_experimental_option(name="useAutomationExtension", value=False)
    logger.debug(f"Edge浏览器初始化完成 - 开始压缩音频 - 累计时长: {datetime.now() - START_TIME}")

    # 等待时间
    load_time, compress_time, completion_time = 5, 10, 100

    # 重试机制
    for retry in range(0, 3):
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)

        os.makedirs(temp_path, exist_ok=True)

        if retry > 0:
            logger.error(f"压缩 {os.path.basename(input_path)} 超时，等待5秒后启动第 {retry} 次重试")
            time.sleep(5)

        with webdriver.Edge(options=edge_options, service=service.Service(TOOLS["msedgedriver"])) as edge_driver:
            # 打开网页
            edge_driver.get(url=r"https://www.youcompress.com/zh-cn/")
            logger.info(f"开始压缩音频: {os.path.basename(input_path)}")

            # 等待页面加载
            try:
                # 等待文件上传框
                upfile_button = ui.WebDriverWait(
                    edge_driver, # 浏览器驱动
                    timeout=load_time, # 等待时间
                ).until(
                    lambda key: key.find_element(By.NAME, "upfile") # 查找元素
                )
                # 上传文件
                upfile_button.send_keys(input_path)

                # 等待上传按钮
                submit_button = ui.WebDriverWait(
                    edge_driver, # 浏览器驱动
                    timeout=load_time, # 等待时间
                ).until(
                    lambda key: key.find_element(By.ID, "submitbutton") # 查找元素
                )
                # 点击上传按钮
                submit_button.click()
                logger.debug(f"文件上传完成: {os.path.basename(input_path)}")
            except Exception as error:
                logger.error(f"网页资源加载失败: {error}")
                load_time += 5
                continue

            # 等待文件压缩完成
            try:
                ui.WebDriverWait(
                    edge_driver, # 浏览器驱动
                    timeout=compress_time, # 等待时间
                ).until(
                    lambda key: key.find_element(By.CLASS_NAME, "result-message") # 查找元素
                )
                logger.debug(f"文件压缩完成: {os.path.basename(input_path)}")
            except Exception as error:
                logger.error(f"文件上传失败: {error}")
                compress_time += 5
                continue

            # 下载压缩文件
            try:
                download_link = ui.WebDriverWait(
                    edge_driver, # 浏览器驱动
                    timeout=load_time, # 等待时间
                ).until(
                    lambda key: key.find_element(By.XPATH, "//a[contains(@href, \"download.php\")]") # 查找元素
                )

                if download_link:
                    download_link.click()
                    # 检测是否开始下载
                    ui.WebDriverWait(
                        edge_driver, # 浏览器驱动
                        timeout=compress_time, # 等待时间
                    ).until(
                        lambda _: any(download_file.endswith(".crdownload") for download_file in os.listdir(temp_path)) # 检测是否还存在.crdownload文件
                    )
                    logger.debug(f"开始下载压缩音频: {os.path.basename(input_path)}")
            except Exception as error:
                logger.error(f"无法下载压缩音频: {len(error) != 0}")
                compress_time += 5
                load_time += 5
                continue

            # 检测下载是否完成
            try:
                ui.WebDriverWait(
                    edge_driver, # 浏览器驱动
                    timeout=completion_time, # 等待时间
                ).until(
                    lambda _: not any(complete_file.endswith(".crdownload") for complete_file in os.listdir(temp_path)) # 检测是否还存在.crdownload文件
                )
                # 复制文件
                shutil.copy2(
                    os.path.join(temp_path, os.path.basename(input_path)),
                    os.path.join(output_path, os.path.basename(input_path)),
                )
                logger.info(f"压缩音频下载完成: {os.path.basename(input_path)} - 累计时长: {datetime.now() - START_TIME}")
                return
            except Exception as error:
                logger.error(f"压缩音频下载失败: {str(error) is None} - {os.path.basename(input_path)}")
                completion_time += 10
                continue
            finally:
                # 关闭浏览器
                edge_driver.quit()
                # 删除临时文件
                shutil.rmtree(temp_path)

    logger.error(f"重试过多，跳过本次压缩: {os.path.basename(input_path)}")
    pass


# 主函数
def main(fid: str, tools: list, input_path: str, audio_path: str, logging_level: int = logging.INFO) -> None:
    """
    主函数，用于启动程序。
    参数:
        fid (str): 收藏夹fid。
        tools (list): 工具列表。
        input_path (str): 输入路径。
        audio_path (str): 音频封面路径。
        logging_level (int): 日志级别，默认为INFO。
    返回:
        None
    """

    # 初始化程序
    subdirectory = initialize_paths(input_path=input_path)
    setup_logging(output_path=subdirectory["log"], level=logging_level)

    tool_detection(tools=tools)

    logger.warning("开始运行 MusicDownloader")
    craw_data = crawl_favorites(fid=fid, page_size=200)
    pro_data = data_processing(data=craw_data, input_path=subdirectory["mus_orig"])

    if pro_data["bvid"]:
        # 为视频下载创建线程池
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as download_executor:
            for bvid, video_name in zip(pro_data["bvid"], pro_data["title"]):
                # 为每个视频创建下载任务
                download_executor.submit(
                    download_task,
                    bvid=bvid, # 视频bvid
                    video_name=video_name, # 视频标题
                    input_path=subdirectory["temp"], # 临时文件夹路径
                    output_path=subdirectory["mus_orig"], # 源音频文件夹路径
                )

        audio_track_processing(input_path=subdirectory["mus_orig"], audio_covers=audio_path)
        information_statistics(detail=pro_data, output_path=subdirectory["data"])
        name_extraction(input_path=subdirectory["mus_orig"])
    else:
        logger.info(f"无待下载的音频，开始压缩音频 - 累计时长: {datetime.now() - START_TIME}")

    # 为音频压缩创建线程池
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as comp_executor:
        for file in os.listdir(subdirectory["mus_orig"]):
            # 为每个音频创建压缩任务
            comp_executor.submit(
                compress_audio,
                temp_path=subdirectory["temp"], # 临时文件夹路径
                output_path=subdirectory["mus_comp"], # 压缩文件输出路径
                input_path=os.path.join(subdirectory["mus_orig"], file), # 源音频文件路径
            )

    logger.info(f"音频压缩完成 - 累计时长: {datetime.now() - START_TIME}")
    pass


# 程序入口
if __name__ == "__main__":
    fid = ""
    tools = ["ffmpeg", "you-get", "msedgedriver"]
    folder_path = r"C:\Users\Lenovo\Downloads"
    audio_path = r"C:\programming\Other-Project\素材\LOGO\EOZT通用图标.png"

    try:
        main(fid=fid, # 收藏夹fid
             tools=tools, # 工具列表
             audio_path=audio_path, # 音频封面路径
             input_path=folder_path, # 输入路径
             logging_level=logging.DEBUG # 日志级别
             )
    except KeyboardInterrupt:
        logger.warning(f"已停止 MusicDownloader 的运行")
    except Exception as error:
        logger.error(error)
    finally:
        logger.warning(f"MusicDownloader 运行结束 - 累计时长: {datetime.now() - START_TIME}\n{DIVIDING_LINE}")
    pass
