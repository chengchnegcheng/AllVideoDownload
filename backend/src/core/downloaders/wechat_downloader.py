"""
微信视频号 专用下载器

针对微信视频号平台优化的下载器
"""

import os
from typing import Dict, Any, List
from urllib.parse import urlparse

from .base_downloader import BaseDownloader, DownloadOptions
from ..config import settings

class WeChatDownloader(BaseDownloader):
    """微信视频号专用下载器"""
    
    def get_platform_name(self) -> str:
        return "微信视频号"
    
    def get_supported_domains(self) -> List[str]:
        return [
            "channels.weixin.qq.com",
            "mp.weixin.qq.com",
            "weixin.qq.com"
        ]
    
    def supports_url(self, url: str) -> bool:
        """检查是否支持该URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            for supported_domain in self.get_supported_domains():
                if supported_domain in domain:
                    return True
            
            # 检查微信视频号特定路径
            if "channels.weixin.qq.com" in domain:
                return True
                
            return False
        except:
            return False
    
    def get_format_selector(self, options: DownloadOptions) -> str:
        """微信视频号优化的格式选择器"""
        # 微信视频号通常只有MP4格式
        return "best[ext=mp4]/best"
    
    def get_info_options(self, url: str) -> Dict[str, Any]:
        """获取信息提取时的微信视频号特定选项"""
        return {
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) MicroMessenger/8.0.13(0x18000d2c) NetType/WIFI Language/zh_CN",
            "referer": "https://channels.weixin.qq.com/",
            "extractor_retries": 5,
            "retries": 10,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) MicroMessenger/8.0.13(0x18000d2c) NetType/WIFI Language/zh_CN",
                "Referer": "https://channels.weixin.qq.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "X-Requested-With": "com.tencent.mm",
            }
        }
    
    def get_platform_specific_options(self, options: DownloadOptions, url: str) -> Dict[str, Any]:
        """获取微信视频号特定的yt-dlp选项"""
        wechat_opts = {
            "referer": "https://channels.weixin.qq.com/",
            "sleep_interval": 2,
            "max_sleep_interval": 5,
            "extractor_retries": 5,
            "retries": 15,
            
            # 微信客户端伪装
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) MicroMessenger/8.0.13(0x18000d2c) NetType/WIFI Language/zh_CN",
                "Referer": "https://channels.weixin.qq.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "X-Requested-With": "com.tencent.mm",
                "Origin": "https://channels.weixin.qq.com",
            },
            
            # 微信特定配置
            "writeinfojson": True,
            "writesubtitles": False,
            "ignoreerrors": True,
            
            # 避免检测
            "call_home": False,
            "check_formats": False,
            "no_check_certificate": True,
        }
        
        return wechat_opts 