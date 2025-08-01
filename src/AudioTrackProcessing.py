# -*- coding:utf-8 -*- #

# Author: YKDX
# Version: V1.1.257.141
# Date Creation: 2025/7/14
# Date Modified: 2025/7/23
# Program Name: AudioTrackProcessing

import os, logging, filetype

from datetime import datetime
from mutagen.id3 import ID3, TPE1, TIT3, TPUB, TDRC, TCOP, APIC, TENC, WOAR

# 全局变量
DEFAULT_ENCODER = "YKDX"
DEFAULT_PUBLISHER = "YKDX"
DEFAULT_ARTIST = "EOZT-YKDX出品"
DEFAULT_COPYRIGHT = "©EOZT 2021-2025"
DEFAULT_AUTHOR_URL = "https://github.com/EOZT-YKDX"

# 音轨处理
def audio_track_processing(input_file: str, logger: logging.Logger, track_information: dict) -> None:
    """
    处理音频文件的音轨信息。
    :param logger: 日志记录器。
    :param input_file: 音频文件路径。
    :param track_information: 音轨元数据的字典。
    :return: None
    """

    start_time = datetime.now()
    file_name = os.path.basename(input_file)
    audio_covers = track_information.get("Cover", "")

    # 加载音频文件
    try:
        audio_file = ID3(input_file)
    except Exception as error:
        logger.error(f"音频文件加载失败: {file_name} - {error}")
        return

    try:
        # 获取封面文件类型
        covers_type = filetype.guess_mime(audio_covers)

        # 检查封面文件类型是否为图片
        if not filetype.is_image(audio_covers):
            logger.error(f"封面文件类型无效: {covers_type} - {file_name}")
            return

        # 读取封面
        with open(mode="rb", file=audio_covers) as covers_file:
            cover_data = covers_file.read()
    except FileNotFoundError:
        logger.error(f"封面文件路径无效: {file_name}")
        return
    except Exception as error:
        logger.error(f"封面文件读取失败: {file_name} - {error}")
        return

    # 将标签值转换为字符串
    for key, value in track_information.items():
        track_information[key] = str(value)

    # 删除旧标签
    for tag in ["TDRC", "TPE1", "TENC", "TPUB", "TCOP", "APIC", "WOAR"]:
        audio_file.delall(tag)

    # 设置文件的源名称，过滤已下载的音频
    if not audio_file.getall("TIT3"):
        audio_file.add(
            TIT3(encoding=3, text=os.path.splitext(file_name)[0])
        )

    # 设置发布年份
    audio_file.add(
        TDRC(encoding=3, text=[str(datetime.now().year)])
    )
    # 设置艺术家
    audio_file.add(
        TPE1(encoding=3, text=[track_information.get("Artist", DEFAULT_ARTIST)])
    )
    # 设置编码人员
    audio_file.add(
        TENC(encoding=3, text=track_information.get("Encoder", DEFAULT_ENCODER))
    )
    # 设置音轨封面
    audio_file.add(
        APIC(type=3, encoding=3, desc="Cover", data=cover_data, mime=covers_type)
    )
    # 设置发布者
    audio_file.add(
        TPUB(encoding=3, text=track_information.get("Publisher", DEFAULT_PUBLISHER))
    )
    # 设置作者URL
    audio_file.add(
        WOAR(encoding=3, url=track_information.get("Author_URL", DEFAULT_AUTHOR_URL))
    )
    # 设置音轨版权
    audio_file.add(
        TCOP(encoding=3, text=[track_information.get("Copyright", DEFAULT_COPYRIGHT)])
    )

    # 保存音轨信息
    try:
        audio_file.save(v2_version=3)
    except Exception as error:
        logger.error(f"音轨标签保存失败: {file_name} - {error}")

    logger.info(f"音轨信息处理完成 - {file_name} - 累计时长: {datetime.now() - start_time}")
    pass


# 函数测试
if __name__ == "__main__":
    from ConfigureLogging import terminal_log

    # 音轨信息
    track_information = {
        "Encoder": "YKDX", # 编码人员
        "Publisher": "YKDX", # 发布者
        "Artist": "YKDX - 纯音乐", # 艺术家
        "Copyright": "©EOZT 2021-2025", # 版权信息
        "Author_URL": "https://github.com/EOZT-YKDX", # 作者URL
        "Cover": r"C:\programming\Other-Project\素材\LOGO\EOZT通用图标.png", # 音频封面
    }

    input_path = r"C:\Users\Lenovo\Downloads\MusicDownloader\Music\CompressedAudio"
    logger = terminal_log(
        log_level=logging.DEBUG,
        log_format=logging.Formatter("%(asctime)s - %(levelname)s - %(lineno)d - %(message)s")
    )

    for file in os.listdir(input_path):
        input_file = os.path.join(input_path, file)
        audio_track_processing(logger=logger, input_file=input_file, track_information=track_information)
    pass