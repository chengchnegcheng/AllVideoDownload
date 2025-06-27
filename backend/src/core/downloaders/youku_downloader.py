"""
优酷 专用下载器

针对优酷平台优化的下载器
"""

import os
from typing import Dict, Any, List
from urllib.parse import urlparse

from .base_downloader import BaseDownloader, DownloadOptions
from ..config import settings

class YoukuDownloader(BaseDownloader):
    """优酷专用下载器"""
    
    def get_platform_name(self) -> str:
        return "优酷"
    
    def get_supported_domains(self) -> List[str]:
        return [
            "youku.com",
            "www.youku.com",
            "m.youku.com",
            "v.youku.com"
        ]
    
    def supports_url(self, url: str) -> bool:
        """检查是否支持该URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            for supported_domain in self.get_supported_domains():
                if supported_domain in domain:
                    return True
                    
            return False
        except:
            return False
    
    def get_format_selector(self, options: DownloadOptions) -> str:
        """优酷优化的格式选择器"""
        if options.quality == "best":
            return "best[ext=mp4]/best[ext=flv]/best"
        elif options.quality == "worst":
            return "worst[ext=mp4]/worst[ext=flv]/worst"
        elif options.quality.endswith("p"):
            height = options.quality[:-1]
            return f"best[height={height}][ext=mp4]/best[height={height}]/best[height<={height}][ext=mp4]/best[height<={height}]"
        else:
            return "best[ext=mp4]/best"
    
    def get_info_options(self, url: str) -> Dict[str, Any]:
        """获取信息提取时的优酷特定选项"""
        return {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "referer": "https://www.youku.com/",
            "extractor_retries": 3,
            "retries": 5,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.youku.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
            }
        }
    
    def get_platform_specific_options(self, options: DownloadOptions, url: str) -> Dict[str, Any]:
        """获取优酷特定的yt-dlp选项"""
        youku_opts = {
            "referer": "https://www.youku.com/",
            "sleep_interval": 1,
            "max_sleep_interval": 3,
            "extractor_retries": 3,
            "retries": 10,
            
            # 优酷特定配置
            "writesubtitles": options.subtitle,
            "writeautomaticsub": False,
            "ignoreerrors": True,
            
            # 请求头配置
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.youku.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Origin": "https://www.youku.com",
            }
        }
        
        # 添加cookies支持
        cookies_path = self._setup_cookies(options)
        if cookies_path:
            youku_opts["cookiefile"] = cookies_path
            
        return youku_opts
    
    def _setup_cookies(self, options: DownloadOptions) -> str:
        """设置优酷cookies"""
        if options.cookies_file and os.path.exists(options.cookies_file):
            return options.cookies_file
        
        cookies_path = os.path.join(settings.DOWNLOAD_PATH, "..", "cookies", "youku_cookies.txt")
        
        if not os.path.exists(cookies_path):
            os.makedirs(os.path.dirname(cookies_path), exist_ok=True)
            with open(cookies_path, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This is a generated file! Do not edit.\n\n")
        
        return cookies_path 