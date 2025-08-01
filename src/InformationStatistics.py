# -*- coding:utf-8 -*- #

# Author: YKDX
# Version: V1.1.257.244
# Date Creation: 2025/7/24
# Date Modified: 2025/7/24
# Program Name: InformationStatistics

import os, logging
from datetime import datetime

# 全局变量
DIVIDING_LINE = "-".center(120, "-")


# 信息统计
def information_statistics(data: dict, output_path: str, logger: logging.Logger, dividing_line: str = DIVIDING_LINE) -> None:
    """
    统计B站下载视频的数据信息。
    :param data: 视频数据信息。
    :param logger: 日志记录器。
    :param dividing_line: 分隔线。
    :param output_path: 信息统计文件输出路径。
    :return: None
    """

    start_time = datetime.now()

    # 检查视频数据信息是否为空
    if not data:
        logger.info("视频数据信息为空 - 未处理任何数据")
        return

    # 检查输出路径是否存在
    if not os.path.isdir(output_path):
        logger.error(f"信息统计文件输出目录无效: {output_path}")
        return

    file_info = []
    current_time = datetime.now().strftime("%Y年-%m月-%d日 %H:%M:%S")
    file_name = "信息统计" + start_time.strftime("%Y-%m-%d") + ".txt"

    for bvid, video_info in data.items():
        file_info.append(f"""\
        《{video_info.get("title", "未知标题")}》 ｜ 《{bvid}》
        
        **视频时长** ｜ {video_info.get("duration", "未知时长")}
        **发布日期** ｜ {video_info.get("pubtime", "未知日期")}
        **封面链接** ｜ {video_info.get("cover", "未知链接")}
        
        **核心数据**
        播放量: {video_info.get("play", "未知播放量")}
        评论数: {video_info.get("reply", "未知评论数")} -*- 转发数: {video_info.get("share", "未知转发数")} -*- 弹幕数: {video_info.get("danmaku", "未知弹幕数")}
        点赞数: {video_info.get("thumb_up", "未知点赞数")} -*- 投币数: {video_info.get("coin", "未知投币数")} -*- 收藏数: {video_info.get("collect", "未知收藏数")}
    
        **统计日期** ｜ {current_time}
    
        {dividing_line}
        """)

    # 输出文件
    try:
        with open(mode="w", encoding="utf-8", file=os.path.join(output_path, file_name)) as file:
            file.write("\n".join(file_info))

        logger.info(f"视频信息统计完成 - 共处理 {len(file_info)} 条数据 - 累计时长: {datetime.now() - start_time}")
    except FileNotFoundError as path_error:
        logger.error(f"视频信息统计失败 - 路径无效: {path_error}")
    except UnicodeEncodeError as encode_error:
        logger.error(f"视频信息统计失败 - 编码错误: {encode_error}")
    except Exception as error:
        logger.error(f"视频信息统计失败: {error}")
    pass


if __name__ == "__main__":
    from ConfigureLogging import terminal_log
    from NetworkOperations import crawl_favorites
    from DataProcessing import data_classification

    output_path = os.getcwd()
    input_path = r"C:\Users\Lenovo\Downloads\MusicDownloader\Music\CompressedAudio"
    logger = terminal_log(
        log_level=logging.DEBUG,
        log_format=logging.Formatter("%(asctime)s - %(levelname)s - %(lineno)d - %(message)s")
    )
    crawl_data = crawl_favorites(
        logger=logger,
        fid="3570962345",
    )
    process_data = data_classification(
        logger=logger,
        data=crawl_data,
        input_path=input_path
    )

    information_statistics(
        logger=logger,
        data=process_data,
        output_path=output_path,
        dividing_line=DIVIDING_LINE
    )
    pass
