"""
AVD Web版本 - 下载器模块

提供各种视频平台的专门下载器实现
"""

from .base_downloader import BaseDownloader, DownloadOptions
from .youtube_downloader import YouTubeDownloader
from .bilibili_downloader import BilibiliDownloader
from .douyin_downloader import DouyinDownloader
from .wechat_downloader import WeChatDownloader
from .xiaohongshu_downloader import XiaohongshuDownloader
from .tencent_downloader import TencentDownloader
from .youku_downloader import YoukuDownloader
from .generic_downloader import GenericDownloader
from .downloader_factory import DownloaderFactory

__all__ = [
    'BaseDownloader',
    'DownloadOptions',
    'YouTubeDownloader', 
    'BilibiliDownloader',
    'DouyinDownloader',
    'WeChatDownloader',
    'XiaohongshuDownloader',
    'TencentDownloader',
    'YoukuDownloader',
    'GenericDownloader',
    'DownloaderFactory',
    'downloader_factory'
] 