# -*- coding:utf-8 -*- #

# Author: YKDX
# Version: V6.12.25228
# Date Creation: 2025/2/10-1
# Date Modified: 2025/2/28-5
# Program Name: MD_System_Integration_Scripts(MD_SIS)

"""
项目介绍:
    1. MD_SIS是一个用于自动化处理音乐的脚本。
    2. 脚本提供高效、可靠的自动化音乐处理解决方案通过字符串搜索匹配和自动化的处理流程，大大提高音乐资源的嗅探和处理的效率，同时保证音频文件的质量和完整性。

注意事项:
    1. 未经原作者授权，禁止用于其他用途。
    2. 仅供研究学习使用，切勿用于非法途径。
    3. 本脚本仅提供下载功能，不会将任何信息上传、存储到服务器。
    4. 请不要过于频繁的使用本脚本，以免对服务器造成过大的压力。
"""

from shutil import rmtree
from subprocess import run
from eyed3 import load, id3
from datetime import datetime
from selenium import webdriver
from difflib import SequenceMatcher
from locale import getpreferredencoding
from os import path, mkdir, listdir, remove
from selenium.webdriver.common.by import By
from bilibili_api import video, sync, search
from selenium.webdriver.edge import options, service
from selenium.webdriver.support import ui, expected_conditions
from logging import StreamHandler, FileHandler, Formatter, Logger, DEBUG, INFO

# 配置输出日志
logger = Logger("md_logger")
# 获取本地编码
local_encoding = getpreferredencoding()

# 全局变量
START_TIME = datetime.now()
DIVIDING_LINE = "-".center(140, "-")
EDGE_DRIVER_PATH = r"C:\programming\Tool-Project\msedgedriver.exe"


# 初始化路径
def initialize_paths(folder_path: str) -> dict:
    """
    初始化路径。

    参数:
        folder_path (str): 父目录路径。

    返回:
        dict: 集成目录的字典。
    """

    if not path.exists(folder_path):
        logger.error(f"路径无效: {folder_path} - 累计时长: {datetime.now() - START_TIME}")
        exit()

    parent_dir = path.join(folder_path, "MusicDownloads")
    integration_dir = {
        # 注意: 父目录必须在子目录之前创建
        "parent_dir": parent_dir,
        "log": path.join(parent_dir, "Log"),
        "data": path.join(parent_dir, "Data"),
        "music": path.join(parent_dir, "Music"),
        "temporary": path.join(parent_dir, "Temporary"),
    }

    try:
        rmtree(parent_dir)
        logger.info(f"删除目录: {parent_dir}")
    except FileNotFoundError:
        pass

    # 创建集成目录对应的文件夹
    for directory in integration_dir.values():
        mkdir(directory)
        logger.info(f"创建目录: {directory} - 累计时长: {datetime.now() - START_TIME}")

    return integration_dir


# 配置日志
def setup_logging(folder_path: str, level: int = INFO) -> None:
    """
    配置日志记录器的级别和格式。

    参数:
        log_path (str): 日志文件路径。
        level (int): 日志级别，默认为 INFO。

    返回:
        None
    """

    # 默认日志格式
    log_format = Formatter("%(asctime)s - %(levelname)s - %(lineno)d - %(message)s")

    # DEBUG日志格式
    if level == DEBUG:
        log_format = Formatter("%(asctime)s - %(levelname)s - %(funcName)s - %(lineno)d - %(message)s")

    # 控制台输出流
    terminal_handler = StreamHandler()
    # 设置控制台日志等级
    terminal_handler.setLevel(level)
    # 设置控制台日志格式
    terminal_handler.setFormatter(log_format)
    # 将日志记录器添加到终端日志记录器
    logger.addHandler(terminal_handler)

    # 文件输出流 编码格式不可修改
    file_handler = FileHandler(path.join(folder_path, f"{datetime.now().strftime("%Y年-%m月-%d日")}.log"), encoding="utf-8")
    # 设置文件日志等级
    file_handler.setLevel(level)
    # 设置文件日志格式
    file_handler.setFormatter(log_format)
    # 将文件处理器添加到文件日志记录器
    logger.addHandler(file_handler)
    pass


# 名称读取
def name_read(file_path: str) -> list:
    """
    从文件中读取名称。

    参数:
        file_path (str): 文件路径。

    返回:
        list: 名称列表。
    """

    if not path.exists(file_path):
        logger.error(f"路径无效: {file_path} - 累计时长: {datetime.now() - START_TIME}")
        exit()

    processing_list, invalid_characters = [], ["\\", "/", ":", "*", "?", "\"", "<", ">", "|"]
    logger.debug(f"名称中的无效字符: {invalid_characters}")

    with open(file=file_path, mode="r", encoding="utf-8") as name_storage_file:
        # 逐行读取
        for music_name in name_storage_file.readlines():
            music_name = music_name.strip()

            # 跳过无效值
            if len(music_name) == 0 or music_name in processing_list:
                continue

            # 用空格代替名称中的无效字符
            processing_list.append("".join(value if value not in invalid_characters else " " for value in music_name))

    logger.info(f"有效名称读取数量: {len(processing_list)}")
    return processing_list


# bvid转换
def bvid_conversion(search_name: str) -> list:
    """
    将搜索名称转换为bvid。

    参数:
     search_name (str): 搜索名称。

    返回:
     list: bvid列表。
    """

    # # bvid转换
    # def bvid_conversion(search_name: str) -> list:
    #     """
    #     将搜索名称转换为bvid。
    #
    #     参数:
    #         search_name (str): 搜索名称。
    #
    #     返回:
    #         list: bvid列表。
    #     """
    #
    #     original_url = f"https://search.bilibili.com/video?keyword={search_name}"
    #     # tids=3音乐标签
    #     label_url = original_url + "&tids=3"
    #     headers = {
    #         "Referer": "https://search.bilibili.com/video",
    #         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
    #     }
    #
    #     # 第一次访问含音乐标签的网址，若爬取失败则访问原始网址
    #     for url in [label_url, original_url]:
    #         bvid_result = []
    #
    #         try:
    #             response = get(url=url, headers=headers, timeout=3)
    #             logger.debug(f"成功发送GET请求: {url}")
    #         except Exception as error:
    #             logger.error(f"GET请求错误: {error}")
    #             continue
    #
    #         # 判断GET请求状态
    #         if not response.ok:
    #             logger.error(f"GET请求错误: {response.status_code}")
    #             continue
    #
    #         # 解析网页
    #         soup = Soup(response.text, features="html.parser")
    #         logger.debug(f"成功解析网页: {url}")
    #
    #         # 分析bvid
    #         for pending_link in soup.find_all(name="a", href=True):
    #             link = pending_link["href"].replace("//", "")
    #             if "www.bilibili.com/video" in link and link not in bvid_result:
    #                 bvid_result.append(link)
    #
    #         if len(bvid_result) != 0:
    #             break
    #
    #     logger.debug(f"待排序的bvid数量: {len(bvid_result)} - 累计时长: {datetime.now() - START_TIME}")
    #     return bvid_result

    bvid_list = []

    try:
        # 用bilibili_api将搜索名称转换为bvid
        search_result = sync(search.search_by_type(time_range=1, keyword=search_name, search_type=search.SearchObjectType.VIDEO))
    except Exception as error:
        logger.error(f"无法将 {search_name} 转换为bvid: {error}")
        return []

    for bvid in search_result["result"]:
        bvid_list.append(bvid.get("bvid"))

    logger.info(f"待排序的bvid数量: {len(bvid_list)}")
    return bvid_list


# bvid排序
def bvid_sort(video_name: str, bvid_list: list) -> list:
    """
    根据计算基础分数和视频名称相似度对bvid进行排序。

    参数:
        video_name (str): 视频名称。
        bvid_list (list): bvid列表。

    返回:
        list: 排序后的bvid列表。
    """

    result_list, initial_scoring = [], 0
    foundation_scoring_rules = {"coin": 0.1, "share": 0.1, "view": 0.001, "like": 0.02, "reply": 0.02, "danmaku": 0.005, "favorite": 0.05}

    for bvid in bvid_list:
        try:
            # 获取bvid对应的视频信息
            video_obj = video.Video(bvid=bvid)
            video_info = sync(video_obj.get_info())
        except Exception as error:
            logger.error(f"无法获取视频信息: {video_name}-{error}")
            continue

        # 跳过无效时长的视频
        if not 60 <= video_info["duration"] <= 420:
            logger.debug(f"跳过时长为 {video_info["duration"]} 秒的视频: {video_info["title"]}")

        # 计算基础分数
        for key, value in video_info["stat"].items():
            if key in foundation_scoring_rules:
                initial_scoring += value * foundation_scoring_rules[key]

        initial_scoring = initial_scoring * 0.0001
        # 计算字符相似度分数
        character_similarity = SequenceMatcher(None, video_name, video_info["title"]).ratio() * 10000
        # 保留两位小数
        initial_scoring = round(initial_scoring + character_similarity, 2)
        result_list.append([bvid, initial_scoring, video_info])

    # 按照分数从大到小排序
    result_list.sort(key=lambda x: x[1], reverse=True)

    try:
        return [result_list[0][0], result_list[0][2]]
    except IndexError:
        return []


# 下载视频
def download_video(folder_path: str, download_url: str, video_name: str) -> None:
    """
    下载视频。

    参数:
        folder_path (str): 文件夹路径。
        download_url (str): 下载链接。
        video_name (str): 视频名称。

    返回:
        None
    """

    # 格式化下载链接
    if "www.bilibili.com/video/" not in download_url:
        download_url = f"www.bilibili.com/video/{download_url}"

    # you-get下载指令
    you_get_command = ["you-get", download_url, "-o", folder_path, "-O", video_name, "--no-caption", "-n"]

    try:
        logger.info(f"开始下载: {video_name} - 累计时长: {datetime.now() - START_TIME}")
        # 执行下载命令 编码格式不可修改
        command_result = run(you_get_command, text=True, capture_output=True, encoding="utf-8")

        if command_result.returncode != 0:
            logger.error(f"下载失败: {video_name}\n{command_result}")
            return

        logger.info(f"成功下载: {video_name} - 累计时长: {datetime.now() - START_TIME}")
    except Exception as error:
        logger.error(error)
    pass


# 下载处理
def download_processing(input_path: str, output_path: str, audio_format: str = ".mp3") -> None:
    """
    处理音频文件，随后删除输入目录。

    参数:
        input_path (str): 输入路径。
        output_path (str): 输出路径。
        audio_format (str): 音频格式，默认为 ".mp3"。

    返回:
        None
    """

    for file in listdir(input_path):
        if file.endswith("[00].mp4"):
            logger.debug(f"无效的音频文件: {file}")
            continue

        input_file = path.join(input_path, file)
        output_file = path.join(output_path, file[:-8] + audio_format)
        # ffmpeg处理指令
        ffmpeg_command = ["ffmpeg", "-i", input_file, output_file, "-vn", "-ac", "2", "-nostats", "-y", "-f", audio_format]
        command_result = run(ffmpeg_command, text=True, capture_output=True, encoding="utf-8")

        if command_result.returncode != 0:
            logger.error(f"处理失败: {file}\n{command_result}")
            continue

        logger.info(f"成功处理音频: {file}")

    if "Temporary" in input_path:
        # 清空临时目录
        rmtree(input_path)
        mkdir(input_path)
        logger.info(f"成功清空临时目录: {input_path} - 累计时长: {datetime.now() - START_TIME}")
    pass


# 音轨处理
def audio_track_processing(folder_path: str, audio_covers: str) -> None:
    """
    处理音频文件的音轨信息。

    参数:
        folder_path (str): 文件夹路径。
        audio_covers (str): 音频封面路径。

    返回:
        None
    """

    if not path.exists(audio_covers):
        logger.error(f"路径无效: {audio_covers}")
        return

    try:
        with open(file=audio_covers, mode="rb") as covers_file:
            # 音轨文件
            audio_covers = covers_file.read()

            for file in listdir(folder_path):
                # 加载音频文件
                audio_file = load(path.join(folder_path, file))

                if audio_file is None:
                    logger.debug(f"无效的音频文件: {file}")
                    continue

                # 写入音轨信息
                audio_file.tag.copyright = "EOZT"
                audio_file.tag.publisher = "YKDX"
                audio_file.tag.encoded_by = "YKDX"
                audio_file.tag.artist = "EOZT-YKDX出品"
                audio_file.tag.images.set(id3.frames.ImageFrame.FRONT_COVER, audio_covers, "image/png")
                audio_file.tag.save(encoding="utf-8")

            logger.info(f"成功处理所有音频文件的音轨 - 累计时长: {datetime.now() - START_TIME}")
    except Exception as error:
        logger.error(f"音轨处理失败: {error}")
    pass


# 压缩音频
def compress_audio(folder_path: str) -> None:
    """
    压缩音频文件。

    参数:
        folder_path (str): 文件夹路径。

    返回:
        None
    """

    url = "https://www.youcompress.com/zh-cn/"

    # 下载配置
    download_configuration = {
        "safebrowsing.enabled": True,
        "download.directory_upgrade": True,
        "download.prompt_for_download": False,
        "download.default_directory": folder_path,
    }

    # 初始化浏览器
    edge_options = options.Options()
    edge_options.add_argument("--headless")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--disable-plugins")
    edge_options.add_argument("--disable-3d-apis")
    edge_options.add_argument("--disable-logging")
    edge_options.add_argument("--disable-extensions")
    edge_options.add_argument("--disable-blink-features=AutomationControlled")
    edge_options.add_experimental_option("prefs", download_configuration)
    edge_options.add_experimental_option(name="useAutomationExtension", value=False)
    edge_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0"
    )
    logger.debug(f"成功初始化Edge浏览器")

    for file in listdir(folder_path):
        logger.info(f"开始压缩音频: {file} - 累计时长: {datetime.now() - START_TIME}")
        input_file = path.join(folder_path, file)

        # 跳过无效音频文件
        if load(input_file) is None or file.endswith("[00].mp4"):
            logger.debug(f"无效的音频文件: {file}")
            continue

        # 启动浏览器
        edge_driver = webdriver.Edge(options=edge_options, service=service.Service(EDGE_DRIVER_PATH))
        logger.info(f"成功启动Edge浏览器 - 累计时长: {datetime.now() - START_TIME}")
        # 设置超时时间
        wait = ui.WebDriverWait(edge_driver, timeout=10)
        # 打开网页
        edge_driver.get(url=url)

        try:
            # 等待文件上传框加载
            file_input = wait.until(
                expected_conditions.presence_of_element_located((By.XPATH, "/html/body/section[1]/div/div/div[2]/form/div[1]/div/label/span/input"))
            )
            file_input.send_keys(input_file)
            logger.debug(f"成功上传文件路径")

            # 等待上传按钮加载
            click_button = wait.until(
                expected_conditions.presence_of_element_located((By.XPATH, "/html/body/section[1]/div/div/div[2]/form/div[2]/button"))
            )
            click_button.click()
            logger.debug(f"成功点击上传按钮")
            # 等待下载按钮加载
            download_button = wait.until(
                expected_conditions.presence_of_element_located((By.XPATH, "/html/body/section[1]/div/div/div[2]/div[2]/div[2]/a")),
            )
            download_button.click()
            logger.debug(f"成功点击下载按钮")

            remove(input_file)
            logger.info(f"成功删除音频原文件: {input_file}")

            # 检查下载是否开始
            ui.WebDriverWait(edge_driver, 10).until(
                lambda driver: any(download_file.endswith(".crdownload") for download_file in listdir(folder_path))
            )
            logger.info(f"开始下载压缩音频: {file} - 累计时长: {datetime.now() - START_TIME}")
            # 检测是否下载完成
            ui.WebDriverWait(edge_driver, 100).until(
                lambda driver: not any(complete_file.endswith(".crdownload") for complete_file in listdir(folder_path))
            )
            logger.info(f"成功下载压缩音频: {file} - 累计时长: {datetime.now() - START_TIME}")
        except Exception as error:
            logger.error(error)

        edge_driver.quit()
        logger.info(f"成功关闭Edge浏览器 - 累计时长: {datetime.now() - START_TIME}")
    pass


# 名称验证
def name_validation(file_path: list, musics_dir: str, data_dir: str, audio_format: str = ".mp3") -> None:
    """
    验证文件名称是否完整。

    参数:
        file_path (list): 文件路径列表。
        musics_dir (str): 音乐文件夹路径。
        document_dir (str): 文档文件夹路径。
        audio_format (str): 音频格式，默认为 ".mp3"。

    返回:
        None
    """

    file_names = set(file_path)
    dir_names = set([name[:-4] for name in listdir(musics_dir) if name.endswith(audio_format)])

    integration_validation = {
        "正向缺失验证": file_names - dir_names,
        "逆向缺失验证": dir_names - file_names,
    }
    logger.debug(f"集成验证: {integration_validation}")

    for key, value in integration_validation.items():
        if len(value) == 0:
            continue

        with open(file=path.join(data_dir, f"{key}.txt"), mode="w", encoding=local_encoding) as document_file:
            for name in value:
                document_file.write(f"{name}\n")

    logger.info(f"成功验证所有音乐名称的完整度 - 累计时长: {datetime.now() - START_TIME}")
    pass


# 信息统计
def information_statistics(folder_path: str, detail: dict) -> None:
    """
    统计音乐信息。

    参数:
        folder_path (str): 文件夹路径。
        detail (dict): 音乐详细信息。

    返回:
        None
    """

    try:
        music_duration = datetime.fromtimestamp(detail["duration"]).strftime("%M:%S")
        release_date = datetime.fromtimestamp(detail["pubdate"]).strftime("%Y-%m-%d %H:%M:%S")

        video_info = f"""
        标题: {detail["title"]}
        BVID: {detail["bvid"]}
        音频时长: {music_duration}
        发布日期: {release_date}
    
        播放量: {detail["stat"]["view"]}
        点赞数: {detail["stat"]["like"]} -*- 投币数: {detail["stat"]["coin"]} -*- 收藏数: {detail["stat"]["favorite"]}
        评论数: {detail["stat"]["reply"]} -*- 转发数: {detail["stat"]["share"]} -*- 弹幕数: {detail["stat"]["danmaku"]}
    
        封面链接: {detail["pic"]}
        {DIVIDING_LINE}
        """

        # 写入信息
        with open(path.join(folder_path, "信息统计.txt"), "a+", encoding=local_encoding) as file:
            file.write(video_info)

        logger.debug(f"成功统计音乐信息: {detail["title"]}")
    except Exception as error:
        logger.error(f"统计音乐信息失败: {error}")
    pass


# 主函数
def main(file_path: str, folder_path: str, audio_path: str, logging_level: int = INFO) -> None:
    """
    主函数。

    参数:
        file_path (str): 文件路径。
        folder_path (str): 文件夹路径。
        audio_path (str): 音频路径。
        logging_level (int): 日志级别，默认为 INFO。

    返回:
        None
    """

    integration_dir = initialize_paths(folder_path=folder_path)
    log_dir, data_dir = integration_dir["log"], integration_dir["data"]
    music_dir, temporary_dir = integration_dir["music"], integration_dir["temporary"]

    setup_logging(folder_path=log_dir, level=logging_level)
    logger.warning(f"开始运行 MD_SIS - 累计时长: {datetime.now() - START_TIME}")
    processing_names = name_read(file_path=file_path)

    for music_name in processing_names:
        bvid_list = bvid_conversion(search_name=music_name)

        if not bvid_list:
            logger.error(f"没有找到BVID对应的视频: {music_name}")
            continue

        bvid, detail = bvid_sort(video_name=music_name, bvid_list=bvid_list)
        download_video(folder_path=temporary_dir, download_url=bvid, video_name=music_name)
        download_processing(input_path=temporary_dir, output_path=music_dir)
        information_statistics(folder_path=data_dir, detail=detail)

    audio_track_processing(folder_path=music_dir, audio_covers=audio_path)
    compress_audio(folder_path=music_dir)
    name_validation(file_path=processing_names, musics_dir=music_dir, data_dir=data_dir)
    logger.warning(f"MD_SIS 运行结束 - 累计时长: {datetime.now() - START_TIME}\n{DIVIDING_LINE}")
    pass


if __name__ == "__main__":
    folder_path = r"C:\Users\Lenovo\Downloads"
    file_path = r"C:\Users\Lenovo\Downloads\音乐.txt"
    audio_path = r"C:\programming\Other-Project\素材\LOGO\EOZT通用图标.png"

    try:
        main(file_path=file_path, folder_path=folder_path, audio_path=audio_path, logging_level=INFO)
    except KeyboardInterrupt:
        logger.warning(f"用户手动停止 wifi_blasting 模块的运行\n{DIVIDING_LINE}")
    except Exception as error:
        logger.error(f"\n{error}\n{DIVIDING_LINE}")