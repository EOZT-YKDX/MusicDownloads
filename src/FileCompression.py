# -*- coding:utf-8 -*- #

# Author: YKDX
# Version: V2.9.257.281
# Date Creation: 2025/7/28
# Date Modified: 2025/7/30
# Program Name: FileCompression

import os, time, shutil, logging, tempfile

from datetime import datetime
from selenium import webdriver
from fake_useragent import UserAgent
from selenium.webdriver.support import ui
from selenium.webdriver.common.by import By
from mutagen.id3 import ID3, ID3NoHeaderError
from selenium.webdriver.edge import options, service
from selenium.common import TimeoutException, NoSuchElementException


class AudioCompressor:
    def __init__(self, config: dict, logger: logging.Logger):
        """
        初始化音频压缩器
        :param config: 配置字典
        :param logger: 日志记录器
        """

        self.browser = None
        self.config = config
        self.logger = logger
        self.file_name = None
        self.retry = config.get("retry", 3)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.timeout = config.get("Timeout_Period", {
            "load_time": 5,
            "compress_time": 20,
            "completion_time": 100,
        })
        self.download_configuration = {
            "safebrowsing.enabled": False, # 禁用安全浏览
            "useAutomationExtension": False, # 禁用自动化扩展
            "download.prompt_for_download": False, # 禁用下载提示
            "download.directory_upgrade": True, # 允许下载到指定目录
            "credentials_enable_service": False,  # 禁用密码保存提示
            "profile.default_content_settings.popups": 0, # 禁用弹窗
            "profile.password_manager_enabled": False,  # 禁用密码管理器
            "profile.managed_default_content_settings.media_stream": 2, # 禁用媒体流
            "profile.managed_default_content_settings.geolocation": 2, # 禁用地理位置
            "profile.managed_default_content_settings.media_stream_mic": 2, # 禁用麦克风
            "profile.managed_default_content_settings.media_stream_camera": 2, # 禁用摄像头
        }
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"

        # 合并超时配置
        self.timeouts = {
            key: config.get(key, self.timeout.get(key, value))
            for key, value in self.timeout.items()
        }

        # 合并下载配置
        self.download_config = {
            **self.download_configuration,
            **config.get("download_configuration", {})
        }


    def init_browser(self):
        """初始化并返回浏览器实例"""

        # 随机生成UserAgent
        user_agent = UserAgent(
            fallback=self.user_agent, # 备用UserAgent
            min_percentage=0.1, # 过滤使用率小于10%的浏览器版本
        )

        # 浏览器选项配置
        edge_options = options.Options()

        # 启用无痕模式
        edge_options.add_argument("--incognito")
        # 禁用沙盒模式
        edge_options.add_argument("--no-sandbox")
        # 禁用GPU加速
        edge_options.add_argument("--disable-gpu")
        # 禁用同步功能
        edge_options.add_argument("--disable-sync")
        # 启用无头模式
        edge_options.add_argument("--headless=new")
        # 禁用Direct3D
        edge_options.add_argument("--disable-d3d11")
        # 禁用日志记录
        edge_options.add_argument("--disable-logging")
        # 禁用3D图形
        edge_options.add_argument("--disable-3d-apis")
        # 禁用所有插件
        edge_options.add_argument("--disable-plugins")
        # 禁用崩溃报告
        edge_options.add_argument("--disable-breakpad")
        # 禁用抗锯齿
        edge_options.add_argument("--disable-canvas-aa")
        # 禁用所有扩展
        edge_options.add_argument("--disable-extensions")
        # 启用快速加载页面
        edge_options.add_argument("--enable-fast-unload")
        # 禁用所有通知
        edge_options.add_argument("--disable-notifications")
        # 禁止组件自动更新
        edge_options.add_argument("--disable-component-update")
        # 禁用备用呈现器
        edge_options.add_argument("--disable-software-rasterizer")
        # 启用并行下载
        edge_options.add_argument("--enable-parallel-downloading")
        # 设置用户代理
        edge_options.add_argument(f"user-agent={user_agent.random}")
        # 禁用后台网络
        edge_options.add_argument("--disable-background-networking")
        # 启用网络服务
        edge_options.add_argument("--enable-features=NetworkService")
        # 启用网络服务
        edge_options.add_argument("--enable-features=NetworkService")
        # 禁用信用卡填充
        edge_options.add_argument("--disable-offer-upload-credit-cards")
        # 禁用图像加载
        edge_options.add_argument("--blink-settings=imagesEnabled=false")
        # 禁用后台计时器
        edge_options.add_argument("--disable-background-timer-throttling")
        # 禁用渲染器检查
        edge_options.add_argument("--disable-features=RendererCodeIntegrity")
        # 隐藏自动化控制特征
        edge_options.add_argument("--disable-blink-features=AutomationControlled")
        # 禁用媒体数据预加载
        edge_options.add_argument("--disable-features=msEdgePreloadMediaEngagementData")

        # 设置下载目录
        self.download_config["download.default_directory"] = self.temp_dir.name
        edge_options.add_experimental_option("prefs", self.download_config)

        # 创建浏览器实例
        driver_service = service.Service(self.config.get("edge_driver"))
        self.browser = webdriver.Edge(options=edge_options, service=driver_service)

        return self.browser


    def get_file_identifier(self, file_path: str):
        """获取文件唯一标识符（优先使用ID3标签，失败则使用文件大小）"""

        try:
            audio = ID3(file_path)
            return str(audio.getall("TIT3")[0])
        except ID3NoHeaderError:
            self.logger.warning(f"文件缺少ID3标签头: {self.file_name}")
            return str(os.path.getsize(file_path))
        except Exception as error:
            self.logger.error(f"获取文件标识符失败: {self.file_name} - {error}")
            return str(os.path.getsize(file_path))


    def get_existing_identifiers(self, output_dir: str):
        """获取输出目录中已有文件的标识符"""

        identifiers = set()

        for file in os.listdir(output_dir):
            try:
                file_path = os.path.join(output_dir, file)
                identifiers.add(self.get_file_identifier(file_path))
            except Exception as error:
                self.logger.error(f"文件标识符获取失败: {file} - {error}")

        return identifiers


    def upload_file(self, file_path: str):
        """将文件上传到压缩网站"""

        try:
            # 等待上传按钮加载
            upfile_button = ui.WebDriverWait(
                self.browser, self.timeouts.get("load_time")
            ).until(lambda d: d.find_element(By.NAME, "upfile"))

            # 上传文件
            upfile_button.send_keys(file_path)
            self.logger.debug(f"文件上传成功: {self.file_name}")

            return True
        except NoSuchElementException:
            self.logger.error(f"文件上传失败: 未找到文件上传元素 - {self.file_name}")
        except TimeoutException:
            self.logger.error(f"文件上传失败: 文件上传元素加载超时 - {self.file_name}")
        except Exception as error:
            self.logger.error(f"文件上传失败: {self.file_name} - {error}")

        return False


    def start_compression(self):
        """启动压缩过程"""

        try:
            # 等待提交按钮加载
            submit_button = ui.WebDriverWait(
                self.browser, self.timeouts.get("load_time")
            ).until(lambda d: d.find_element(By.ID, "submitbutton"))

            # 提交文件
            submit_button.click()

            # 等待压缩完成提示
            ui.WebDriverWait(
                self.browser, self.timeouts.get("compress_time")
            ).until(lambda d: d.find_element(By.CLASS_NAME, "result-message"))

            self.logger.debug(f"文件压缩完成: {self.file_name}")
            return True
        except TimeoutException:
            self.logger.error(f"启动压缩失败: 压缩过程超时 - {self.file_name}")
        except NoSuchElementException:
            self.logger.error(f"启动压缩失败: 文件压缩元素加载超时 - {self.file_name}")
        except Exception as error:
            self.logger.error(f"启动压缩失败: {self.file_name} - {error}")
        return False


    def download_compressed_file(self, output_path: str):
        """下载压缩后的文件"""

        try:
            # 查找下载链接
            download_link = ui.WebDriverWait(
                self.browser, self.timeouts.get("load_time")
            ).until(lambda d: d.find_element(By.XPATH, "//a[contains(@href, \"download.php\")]"))

            if download_link:
                # 下载文件
                download_link.click()

                # 等待下载开始
                ui.WebDriverWait(
                    self.browser, self.timeouts.get("compress_time")
                ).until(lambda _: any(file.endswith(".crdownload") for file in os.listdir(self.temp_dir.name)))

                # 等待下载完成
                ui.WebDriverWait(
                    self.browser, self.timeouts.get("completion_time")
                ).until(lambda _: not any(file.endswith(".crdownload") for file in os.listdir(self.temp_dir.name)))

                # 查找下载的文件
                downloaded_files = [file for file in os.listdir(self.temp_dir.name) if not file.endswith('.crdownload')]

                if downloaded_files:
                    # 获取最新下载的文件
                    latest_file = max(
                        downloaded_files,
                        key=lambda file: os.path.getctime(os.path.join(self.temp_dir.name, file))
                    )

                    # 复制到输出目录
                    shutil.copy2(
                        os.path.join(self.temp_dir.name, latest_file),
                        os.path.join(output_path, self.file_name),
                    )
                    return True
        except TimeoutException:
            self.logger.error(f"文件下载失败: 下载过程超时 - {self.file_name}")
        except NoSuchElementException:
            self.logger.error(f"文件下载失败: 文件下载元素加载超时 - {self.file_name}")
        except Exception as error:
            self.logger.error(f"文件下载失败: {self.file_name} - {error}")

        return False


    def compress(self, input_path: str, output_path: str, retry=None) -> bool:
        """
        压缩音频文件主方法
        :param input_path: 输入文件路径
        :param output_path: 输出目录路径
        :param retry: 重试次数（可选）
        :return: 压缩结果
        """

        start_time = datetime.now()

        if not os.path.isfile(input_path):
            self.logger.error(f"输入文件路径无效: {input_path}")
            return False

        if not os.path.isdir(output_path):
            self.logger.error(f"输出目录路径无效: {output_path}")
            return False

        if retry is None:
            retry = self.retry

        self.file_name = os.path.basename(input_path)
        self.logger.info(f"开始压缩音频: {self.file_name}")

        # 重试机制
        for count in range(1, retry + 1):
            try:
                # 初始化浏览器
                if not self.browser:
                    self.init_browser()

                self.browser.get("https://www.youcompress.com/zh-cn/")

                # 执行压缩流程
                if not self.upload_file(input_path):
                    raise Exception(f"文件上传失败 - {self.file_name}")

                if not self.start_compression():
                    raise Exception(f"压缩过程失败 - {self.file_name}")

                if not self.download_compressed_file(output_path):
                    raise Exception(f"文件下载失败 - {self.file_name}")

                self.logger.info(f"音频压缩下载完成: {self.file_name} - 累计时长: {datetime.now() - start_time}")
                return True
            except Exception as error:
                # 指数退避等待，上限30秒
                wait_time = min(5 ** count, 30)
                self.logger.info(f"等待 {wait_time} 秒后音频压缩启动第 {count} 次重试 - {error}")
                time.sleep(wait_time)

                # 动态调整超时时间，上限5分钟
                for key in self.timeouts:
                    self.timeouts[key] = min(self.timeouts[key] * 2, 300)
            finally:
                try:
                    self.browser.quit()
                except Exception as error:
                    self.logger.debug(f"浏览器关闭失败: {type(error).__name__}")
                self.browser = None

        self.logger.error(f"音频压缩重试过多，跳过本次压缩: {self.file_name}")
        return False


    def __exit__(self, exc_type, exc_val, exc_tb):
        """清理资源"""

        if self.browser:
            self.browser.quit()
        if self.temp_dir:
            self.temp_dir.cleanup()


# 函数测试
if __name__ == "__main__":
    from ConfigureLogging import terminal_log
    from ProgramInitialization import tool_detection

    tools = ["msedgedriver"]
    output_dir = r"C:\Users\Lenovo\Downloads\MusicDownloader\Music\CompressedAudio"
    input_file = r"C:\Users\Lenovo\Downloads\MusicDownloader\Music\OriginalAudio\“能不能别外放听歌了！”.mp3"
    logger = terminal_log(
        log_level=logging.DEBUG,
        log_format=logging.Formatter("%(asctime)s - %(levelname)s - %(lineno)d - %(message)s")
    )
    tool_path = tool_detection(tools=tools, logger=logger)
    config = {
        "retry": 3,
        "edge_driver": tool_path["msedgedriver"],
        "Timeout_Period": {
            "load_time": 8,
            "compress_time": 15,
            "completion_time": 120,
        }
    }

    # 创建压缩器实例
    compressor = AudioCompressor(config=config, logger=logger)
    compress_result = compressor.compress(input_file, output_dir)