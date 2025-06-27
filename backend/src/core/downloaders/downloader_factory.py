"""
下载器工厂

根据URL自动选择合适的下载器
"""

from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import logging

from .base_downloader import BaseDownloader, DownloadOptions
from .youtube_downloader import YouTubeDownloader
from .bilibili_downloader import BilibiliDownloader
from .douyin_downloader import DouyinDownloader
from .wechat_downloader import WeChatDownloader
from .xiaohongshu_downloader import XiaohongshuDownloader
from .tencent_downloader import TencentDownloader
from .youku_downloader import YoukuDownloader
from .generic_downloader import GenericDownloader

logger = logging.getLogger(__name__)

class DownloaderFactory:
    """下载器工厂"""
    
    def __init__(self):
        # 初始化所有下载器实例
        self._downloaders: List[BaseDownloader] = [
            YouTubeDownloader(),
            BilibiliDownloader(),
            DouyinDownloader(),
            WeChatDownloader(),
            XiaohongshuDownloader(),
            TencentDownloader(),
            YoukuDownloader(),
        ]
        
        # 通用下载器作为后备选项
        self._generic_downloader = GenericDownloader()
        
        # 构建域名到下载器的快速查找表
        self._domain_map: Dict[str, BaseDownloader] = {}
        self._build_domain_map()
    
    def _build_domain_map(self):
        """构建域名到下载器的映射表"""
        for downloader in self._downloaders:
            for domain in downloader.get_supported_domains():
                self._domain_map[domain.lower()] = downloader
                
        logger.info(f"下载器工厂初始化完成，支持 {len(self._domain_map)} 个域名")
    
    def get_downloader(self, url: str) -> BaseDownloader:
        """根据URL获取合适的下载器"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # 首先尝试直接域名匹配
            if domain in self._domain_map:
                downloader = self._domain_map[domain]
                logger.info(f"为URL {url} 选择了 {downloader.get_platform_name()} 下载器")
                return downloader
            
            # 尝试子域名匹配
            for supported_domain, downloader in self._domain_map.items():
                if supported_domain in domain:
                    logger.info(f"为URL {url} 选择了 {downloader.get_platform_name()} 下载器 (子域名匹配)")
                    return downloader
            
            # 最后一次检查，调用每个下载器的supports_url方法
            for downloader in self._downloaders:
                if downloader.supports_url(url):
                    logger.info(f"为URL {url} 选择了 {downloader.get_platform_name()} 下载器 (supports_url匹配)")
                    return downloader
            
            # 如果没有找到专门的下载器，使用通用下载器
            logger.info(f"为URL {url} 选择了通用下载器")
            return self._generic_downloader
            
        except Exception as e:
            logger.error(f"选择下载器失败: {e}")
            # 出错时返回通用下载器
            return self._generic_downloader
    
    def get_supported_platforms(self) -> List[Dict[str, Any]]:
        """获取所有支持的平台信息"""
        platforms = []
        
        for downloader in self._downloaders:
            platforms.append({
                "name": downloader.get_platform_name(),
                "domains": downloader.get_supported_domains(),
                "class_name": downloader.__class__.__name__
            })
        
        platforms.append({
            "name": self._generic_downloader.get_platform_name(),
            "domains": ["*"],
            "class_name": self._generic_downloader.__class__.__name__
        })
        
        return platforms
    
    def test_url_support(self, url: str) -> Dict[str, Any]:
        """测试URL支持情况"""
        try:
            downloader = self.get_downloader(url)
            return {
                "supported": True,
                "platform": downloader.get_platform_name(),
                "downloader_class": downloader.__class__.__name__,
                "is_generic": isinstance(downloader, GenericDownloader)
            }
        except Exception as e:
            return {
                "supported": False,
                "error": str(e),
                "platform": None,
                "downloader_class": None,
                "is_generic": None
            }
    
    def cleanup_all(self):
        """清理所有下载器资源"""
        try:
            for downloader in self._downloaders:
                downloader.cleanup()
            self._generic_downloader.cleanup()
            logger.info("所有下载器资源清理完成")
        except Exception as e:
            logger.error(f"清理下载器资源失败: {e}")

# 全局下载器工厂实例
downloader_factory = DownloaderFactory() 