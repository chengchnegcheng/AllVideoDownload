"""
抖音 专用下载器

针对抖音平台优化的下载器
"""

import os
from typing import Dict, Any, List
from urllib.parse import urlparse

from .base_downloader import BaseDownloader, DownloadOptions
from ..config import settings

class DouyinDownloader(BaseDownloader):
    """抖音专用下载器"""
    
    def get_platform_name(self) -> str:
        return "抖音"
    
    def get_supported_domains(self) -> List[str]:
        return [
            "douyin.com",
            "www.douyin.com",
            "v.douyin.com",
            "iesdouyin.com",
            "tiktok.com",
            "www.tiktok.com",
            "vm.tiktok.com"
        ]
    
    def supports_url(self, url: str) -> bool:
        """检查是否支持该URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            for supported_domain in self.get_supported_domains():
                if supported_domain in domain:
                    return True
            
            # 检查抖音短链接模式
            if "v.douyin.com" in domain or "vm.tiktok.com" in domain:
                return True
                
            return False
        except:
            return False
    
    def get_format_selector(self, options: DownloadOptions) -> str:
        """抖音优化的格式选择器"""
        # 抖音通常只有一个格式，优先选择无水印版本
        if options.quality == "best":
            return "best[ext=mp4]/best"
        elif options.quality == "worst":
            return "worst[ext=mp4]/worst"
        else:
            return "best[ext=mp4]/best"
    
    def get_info_options(self, url: str) -> Dict[str, Any]:
        """获取信息提取时的抖音特定选项"""
        # 判断是抖音还是TikTok
        is_tiktok = "tiktok.com" in url.lower()
        
        return {
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
            "referer": "https://www.tiktok.com/" if is_tiktok else "https://www.douyin.com/",
            "extractor_retries": 5,
            "retries": 10,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
                "Referer": "https://www.tiktok.com/" if is_tiktok else "https://www.douyin.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9" if is_tiktok else "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
            }
        }
    
    def get_platform_specific_options(self, options: DownloadOptions, url: str) -> Dict[str, Any]:
        """获取抖音特定的yt-dlp选项"""
        is_tiktok = "tiktok.com" in url.lower()
        
        douyin_opts = {
            "referer": "https://www.tiktok.com/" if is_tiktok else "https://www.douyin.com/",
            "sleep_interval": 2,
            "max_sleep_interval": 5,
            "extractor_retries": 5,
            "retries": 15,
            
            # 移动端伪装
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
                "Referer": "https://www.tiktok.com/" if is_tiktok else "https://www.douyin.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9" if is_tiktok else "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "X-Requested-With": "XMLHttpRequest",
            },
            
            # 抖音特定配置
            "writeinfojson": True,
            "writesubtitles": False,  # 抖音通常没有字幕文件
            "ignoreerrors": True,
            
            # 避免下载器检测
            "call_home": False,
            "check_formats": False,
        }
        
        # 添加cookies支持
        cookies_path = self._setup_cookies(options, is_tiktok)
        if cookies_path:
            douyin_opts["cookiefile"] = cookies_path
            
        return douyin_opts
    
    def _setup_cookies(self, options: DownloadOptions, is_tiktok: bool = False) -> str:
        """设置抖音/TikTok cookies"""
        if options.cookies_file and os.path.exists(options.cookies_file):
            return options.cookies_file
        
        platform_name = "tiktok" if is_tiktok else "douyin"
        cookies_path = os.path.join(settings.DOWNLOAD_PATH, "..", "cookies", f"{platform_name}_cookies.txt")
        
        if not os.path.exists(cookies_path):
            os.makedirs(os.path.dirname(cookies_path), exist_ok=True)
            with open(cookies_path, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This is a generated file! Do not edit.\n\n")
        
        return cookies_path 