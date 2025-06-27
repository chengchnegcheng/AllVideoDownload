"""
通用下载器

用于处理其他不在专门平台列表中的网站
"""

import os
from typing import Dict, Any, List
from urllib.parse import urlparse

from .base_downloader import BaseDownloader, DownloadOptions
from ..config import settings

class GenericDownloader(BaseDownloader):
    """通用下载器"""
    
    def get_platform_name(self) -> str:
        return "通用下载器"
    
    def get_supported_domains(self) -> List[str]:
        # 通用下载器支持所有域名
        return ["*"]
    
    def supports_url(self, url: str) -> bool:
        """检查是否支持该URL - 通用下载器支持所有URL"""
        try:
            parsed = urlparse(url)
            # 基本的URL格式检查
            return bool(parsed.scheme and parsed.netloc)
        except:
            return False
    
    def get_format_selector(self, options: DownloadOptions) -> str:
        """通用格式选择器"""
        if options.quality == "best":
            return f"best[ext={options.format}]/best"
        elif options.quality == "worst":
            return f"worst[ext={options.format}]/worst"
        elif options.quality.endswith("p"):
            height = options.quality[:-1]
            return f"best[height<={height}][ext={options.format}]/best[height<={height}]/best"
        else:
            return f"best[ext={options.format}]/best"
    
    def get_info_options(self, url: str) -> Dict[str, Any]:
        """获取信息提取时的通用选项"""
        return {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "extractor_retries": 3,
            "retries": 5,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
            }
        }
    
    def get_platform_specific_options(self, options: DownloadOptions, url: str) -> Dict[str, Any]:
        """获取通用的yt-dlp选项"""
        generic_opts = {
            "sleep_interval": 1,
            "max_sleep_interval": 3,
            "extractor_retries": 3,
            "retries": 10,
            
            # 通用配置
            "writesubtitles": options.subtitle,
            "writeautomaticsub": options.subtitle,
            "ignoreerrors": True,
            
            # 基础请求头
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        }
        
        return generic_opts 