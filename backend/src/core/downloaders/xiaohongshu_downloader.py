"""
小红书 专用下载器

针对小红书平台优化的下载器
"""

import os
from typing import Dict, Any, List
from urllib.parse import urlparse

from .base_downloader import BaseDownloader, DownloadOptions
from ..config import settings

class XiaohongshuDownloader(BaseDownloader):
    """小红书专用下载器"""
    
    def get_platform_name(self) -> str:
        return "小红书"
    
    def get_supported_domains(self) -> List[str]:
        return [
            "xiaohongshu.com",
            "www.xiaohongshu.com",
            "xhslink.com"
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
        """小红书优化的格式选择器"""
        return "best[ext=mp4]/best"
    
    def get_info_options(self, url: str) -> Dict[str, Any]:
        """获取信息提取时的小红书特定选项"""
        return {
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
            "referer": "https://www.xiaohongshu.com/",
            "extractor_retries": 5,
            "retries": 10,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
                "Referer": "https://www.xiaohongshu.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
            }
        }
    
    def get_platform_specific_options(self, options: DownloadOptions, url: str) -> Dict[str, Any]:
        """获取小红书特定的yt-dlp选项"""
        xiaohongshu_opts = {
            "referer": "https://www.xiaohongshu.com/",
            "sleep_interval": 2,
            "max_sleep_interval": 5,
            "extractor_retries": 5,
            "retries": 15,
            
            # 移动端伪装
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
                "Referer": "https://www.xiaohongshu.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "X-Requested-With": "XMLHttpRequest",
            },
            
            # 小红书特定配置
            "writeinfojson": True,
            "writesubtitles": False,
            "ignoreerrors": True,
            "call_home": False,
            "check_formats": False,
        }
        
        return xiaohongshu_opts 