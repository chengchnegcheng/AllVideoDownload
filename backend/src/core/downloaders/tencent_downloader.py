"""
腾讯视频 专用下载器

针对腾讯视频平台优化的下载器
"""

import os
from typing import Dict, Any, List
from urllib.parse import urlparse

from .base_downloader import BaseDownloader, DownloadOptions
from ..config import settings

class TencentDownloader(BaseDownloader):
    """腾讯视频专用下载器"""
    
    def get_platform_name(self) -> str:
        return "腾讯视频"
    
    def get_supported_domains(self) -> List[str]:
        return [
            "v.qq.com",
            "www.v.qq.com",
            "m.v.qq.com",
            "film.qq.com",
            "tv.qq.com"
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
        """腾讯视频优化的格式选择器"""
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
        """获取信息提取时的腾讯视频特定选项"""
        return {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "referer": "https://v.qq.com/",
            "extractor_retries": 3,
            "retries": 5,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://v.qq.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
            }
        }
    
    def get_platform_specific_options(self, options: DownloadOptions, url: str) -> Dict[str, Any]:
        """获取腾讯视频特定的yt-dlp选项"""
        tencent_opts = {
            "referer": "https://v.qq.com/",
            "sleep_interval": 1,
            "max_sleep_interval": 3,
            "extractor_retries": 3,
            "retries": 10,
            
            # 腾讯视频特定配置
            "writesubtitles": options.subtitle,
            "writeautomaticsub": False,
            "ignoreerrors": True,
            
            # 请求头配置
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://v.qq.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Origin": "https://v.qq.com",
            }
        }
        
        # 添加cookies支持
        cookies_path = self._setup_cookies(options)
        if cookies_path:
            tencent_opts["cookiefile"] = cookies_path
            
        return tencent_opts
    
    def _setup_cookies(self, options: DownloadOptions) -> str:
        """设置腾讯视频cookies"""
        if options.cookies_file and os.path.exists(options.cookies_file):
            return options.cookies_file
        
        cookies_path = os.path.join(settings.DOWNLOAD_PATH, "..", "cookies", "tencent_cookies.txt")
        
        if not os.path.exists(cookies_path):
            os.makedirs(os.path.dirname(cookies_path), exist_ok=True)
            with open(cookies_path, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This is a generated file! Do not edit.\n\n")
        
        return cookies_path 