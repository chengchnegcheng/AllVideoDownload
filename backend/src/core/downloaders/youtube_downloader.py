"""
YouTube 专用下载器 - 2025年终极强化反反爬虫版本

针对YouTube平台优化的下载器，包含最新的反反爬虫策略
应对YouTube 2025年加强的反机器人检测机制
支持PO Token、多客户端轮换、智能重试等高级功能
"""

import os
import time
import random
import json
import hashlib
import base64
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urlencode
import requests

from .base_downloader import BaseDownloader, DownloadOptions
from ..config import settings

class YouTubeDownloader(BaseDownloader):
    """YouTube专用下载器 - 2025终极强化版"""
    
    def __init__(self):
        super().__init__()
        self._session_cache = {}
        self._last_request_time = 0
        self._request_count = 0
        self._current_client_index = 1  # 默认使用ANDROID客户端（索引1）
        self._po_token = None
        self._visitor_data = None
        
        # 立即设置代理环境变量
        self._setup_proxy_environment()
    
    def _setup_proxy_environment(self):
        """设置代理环境变量"""
        try:
            proxy_url = settings.HTTP_PROXY
            if proxy_url:
                # 确保SOCKS5代理使用socks5h://格式
                if proxy_url.startswith('socks5://'):
                    proxy_url = proxy_url.replace('socks5://', 'socks5h://')
                
                # 设置所有可能的代理环境变量
                os.environ['HTTP_PROXY'] = proxy_url
                os.environ['HTTPS_PROXY'] = proxy_url
                os.environ['http_proxy'] = proxy_url
                os.environ['https_proxy'] = proxy_url
                
                print(f"✅ YouTube下载器代理已设置: {proxy_url}")
            else:
                print("⚠️ 未配置代理，YouTube可能无法访问")
        except Exception as e:
            print(f"❌ 代理设置失败: {e}")
        
        # 2025年最新的客户端配置 - 添加更多客户端类型
        self._clients = [
            {
                "name": "WEB",
                "version": "2.20241217.01.00",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "client_name": "WEB",
                "client_version": "2.20241217.01.00",
                "os_name": "Windows",
                "os_version": "10.0",
                "platform": "DESKTOP"
            },
            {
                "name": "ANDROID",
                "version": "19.50.37",
                "user_agent": "com.google.android.youtube/19.50.37 (Linux; U; Android 14; SM-G998B Build/UP1A.231005.007) gzip",
                "client_name": "ANDROID",
                "client_version": "19.50.37",
                "android_sdk_version": 34,
                "os_name": "Android",
                "os_version": "14",
                "platform": "MOBILE"
            },
            {
                "name": "ANDROID_MUSIC",
                "version": "7.25.52",
                "user_agent": "com.google.android.apps.youtube.music/7.25.52 (Linux; U; Android 14; SM-G998B) gzip",
                "client_name": "ANDROID_MUSIC",
                "client_version": "7.25.52",
                "android_sdk_version": 34,
                "os_name": "Android",
                "os_version": "14",
                "platform": "MOBILE"
            },
            {
                "name": "IOS",
                "version": "19.50.7",
                "user_agent": "com.google.ios.youtube/19.50.7 (iPhone16,2; U; CPU iOS 18_1_1 like Mac OS X)",
                "client_name": "IOS",
                "client_version": "19.50.7",
                "device_model": "iPhone16,2",
                "os_name": "iOS",
                "os_version": "18.1.1",
                "platform": "MOBILE"
            },
            {
                "name": "MWEB",
                "version": "2.20241217.01.00",
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1.1 Mobile/15E148 Safari/604.1",
                "client_name": "MWEB",
                "client_version": "2.20241217.01.00",
                "os_name": "iOS",
                "os_version": "18.1.1",
                "platform": "MOBILE"
            },
            {
                "name": "TV_EMBEDDED",
                "version": "2.0",
                "user_agent": "Mozilla/5.0 (PlayStation 4 5.55) AppleWebKit/601.2 (KHTML, like Gecko)",
                "client_name": "TVHTML5_SIMPLY_EMBEDDED_PLAYER",
                "client_version": "2.0",
                "platform": "TV"
            }
        ]
    
    def get_platform_name(self) -> str:
        """获取平台名称"""
        return "YouTube"
    
    def get_supported_domains(self) -> List[str]:
        """获取支持的域名列表"""
        return ["youtube.com", "youtu.be", "m.youtube.com", "www.youtube.com", "music.youtube.com"]
    
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
    
    def _get_current_client(self) -> Dict[str, str]:
        """获取当前客户端配置"""
        return self._clients[self._current_client_index]
    
    def _rotate_client(self):
        """轮换客户端"""
        self._current_client_index = (self._current_client_index + 1) % len(self._clients)
    
    def _generate_session_token(self) -> str:
        """生成会话令牌"""
        timestamp = str(int(time.time()))
        random_str = str(random.randint(100000, 999999))
        return hashlib.md5((timestamp + random_str).encode()).hexdigest()[:16]
    
    def _get_visitor_data(self) -> str:
        """生成访客数据"""
        if not self._visitor_data:
            chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
            self._visitor_data = ''.join(random.choice(chars) for _ in range(11))
        return self._visitor_data
    
    def _generate_po_token(self) -> str:
        """生成PO Token - 2025年新增功能"""
        if not self._po_token:
            # 生成符合YouTube要求的PO Token
            timestamp = int(time.time())
            client = self._get_current_client()
            
            # PO Token的基础数据结构
            token_data = {
                "visitorData": self._get_visitor_data(),
                "sessionIndex": 0,
                "timestamp": timestamp,
                "clientName": client["client_name"],
                "clientVersion": client["client_version"]
            }
            
            # 编码PO Token
            token_json = json.dumps(token_data, separators=(',', ':'))
            self._po_token = base64.b64encode(token_json.encode()).decode().rstrip('=')
            
        return self._po_token
    
    def _smart_delay(self):
        """智能延迟策略"""
        current_time = time.time()
        if self._last_request_time > 0:
            time_diff = current_time - self._last_request_time
            if time_diff < 2:  # 最小间隔2秒
                delay = 2 - time_diff + random.uniform(0.5, 1.5)
                time.sleep(delay)
        
        # 根据请求频率调整延迟
        if self._request_count > 10:
            time.sleep(random.uniform(3, 6))
            self._request_count = 0
        elif self._request_count > 5:
            time.sleep(random.uniform(1, 3))
        else:
            time.sleep(random.uniform(0.5, 1.5))
        
        self._last_request_time = time.time()
        self._request_count += 1
    
    def get_format_selector(self, options: DownloadOptions) -> str:
        """YouTube优化的格式选择器 - 2025版本"""
        if options.quality == "best":
            # 2025年更新：优先选择AV1编码，然后VP9，最后H.264
            return "best[vcodec^=av01][height<=1080]/best[vcodec^=vp9][height<=1080]/best[ext=mp4][height<=1080]/best"
        elif options.quality == "worst":
            return "worst[ext=mp4]/worst"
        elif options.quality.endswith("p"):
            height = options.quality[:-1]
            return f"best[vcodec^=av01][height={height}]/best[vcodec^=vp9][height={height}]/best[ext=mp4][height={height}]/best[height<={height}]"
        else:
            return "best[ext=mp4]/best"
    
    def get_info_options(self, url: str) -> Dict[str, Any]:
        """获取信息提取时的YouTube特定选项 - 简化版（基于原始yt-dlp成功配置）"""
        return {
            # 基础配置
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            
            # 简化extractor参数 - 基于成功的原始yt-dlp配置
            "extractor_args": {
                "youtube": {
                    # 强制使用ANDROID客户端 - 这是关键！
                    "player_client": ["android"]
                }
            },
            
            # 代理配置
            "proxy": settings.HTTP_PROXY.replace('socks5://', 'socks5h://') if settings.HTTP_PROXY and settings.HTTP_PROXY.startswith('socks5://') else settings.HTTP_PROXY
        }
    
    def get_platform_specific_options(self, options: DownloadOptions, url: str) -> Dict[str, Any]:
        """获取YouTube特定的yt-dlp选项 - 简化版（基于成功的原始yt-dlp配置）"""
        youtube_opts = {
            # 基础配置
            "quiet": True,
            "no_warnings": True,
            
            # 简化extractor参数 - 基于成功的原始yt-dlp配置
            "extractor_args": {
                "youtube": {
                    # 强制使用ANDROID客户端 - 这是关键！
                    "player_client": ["android"]
                }
            }
        }
        
        # 添加代理支持
        if settings.HTTP_PROXY:
            proxy_url = settings.HTTP_PROXY
            # 确保SOCKS5代理正确配置
            if proxy_url.startswith('socks5://'):
                proxy_url = proxy_url.replace('socks5://', 'socks5h://')
            youtube_opts["proxy"] = proxy_url
        
        return youtube_opts
    
    def _get_innertube_key(self, client_name: str) -> List[str]:
        """获取Innertube API密钥"""
        keys = {
            "WEB": ["AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"],
            "ANDROID": ["AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w"],
            "ANDROID_MUSIC": ["AIzaSyC9XL3ZjWddXya6X74dJoCTL-WEYFDNX30"],
            "IOS": ["AIzaSyB-63vPrdThhKuerbB2N_l7Kwwcxj6yUAc"],
            "MWEB": ["AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"]
        }
        return keys.get(client_name, keys["WEB"])
    
    def _get_client_id(self, client_name: str) -> int:
        """获取客户端ID"""
        client_ids = {
            "WEB": 1,
            "ANDROID": 3,
            "ANDROID_MUSIC": 21,
            "IOS": 5,
            "MWEB": 2
        }
        return client_ids.get(client_name, 1)
    
    def _generate_fake_ip(self) -> str:
        """生成虚假IP地址"""
        return ".".join(str(random.randint(1, 255)) for _ in range(4))
    
    def _generate_client_data(self) -> str:
        """生成客户端数据"""
        data = json.dumps({
            "timestamp": int(time.time()),
            "session": self._generate_session_token(),
            "version": "131.0.6778.140"
        })
        return base64.b64encode(data.encode()).decode()
    
    def _setup_cookies(self, options: DownloadOptions) -> Optional[str]:
        """设置YouTube cookies - 2025年强化版"""
        try:
            if options.cookies_file and os.path.exists(options.cookies_file):
                return options.cookies_file
            
            # 使用项目内的cookies目录
            cookies_dir = os.path.join(os.path.dirname(__file__), "../../../data/cookies")
            cookies_path = os.path.join(cookies_dir, "youtube_cookies.txt")
            
            if not os.path.exists(cookies_dir):
                os.makedirs(cookies_dir, exist_ok=True)
            
            if not os.path.exists(cookies_path):
                # 创建增强的cookies文件
                with open(cookies_path, 'w') as f:
                    f.write("# Netscape HTTP Cookie File\n")
                    f.write("# This is a generated file! Do not edit.\n\n")
                    
                    # 添加一些基础cookies以模拟真实浏览器
                    timestamp = str(int(time.time() + 31536000))  # 1年后过期
                    cookies = [
                        f".youtube.com\tTRUE\t/\tFALSE\t{timestamp}\tYSC\t{self._generate_session_token()}",
                        f".youtube.com\tTRUE\t/\tFALSE\t{timestamp}\tVISITOR_INFO1_LIVE\t{self._get_visitor_data()}",
                        f".youtube.com\tTRUE\t/\tTRUE\t{timestamp}\tCONSENT\tYES+cb.20210328-17-p0.en+FX+667",
                        f".youtube.com\tTRUE\t/\tFALSE\t{timestamp}\tPREF\tf4=4000000&hl=en&f5=30000",
                        f".youtube.com\tTRUE\t/\tFALSE\t{timestamp}\t__Secure-3PSID\t{self._generate_session_token()}",
                        f".youtube.com\tTRUE\t/\tFALSE\t{timestamp}\tSIDCC\t{self._generate_session_token()}"
                    ]
                    
                    for cookie in cookies:
                        f.write(cookie + "\n")
            
            return cookies_path
        except Exception as e:
            print(f"警告：无法设置cookies: {e}")
            return None
    
    def _get_base_ydl_opts(self) -> dict:
        """获取基础的yt-dlp选项 - 2025年终极版"""
        opts = super()._get_base_ydl_opts()
        
        client = self._get_current_client()
        
        # 2025年YouTube特定配置
        opts.update({
            # 使用多客户端策略
            'extractor_args': {
                'youtube': {
                    'player_client': [client["name"].lower()],
                    'player_skip': ['webpage'],
                    'skip': [],
                    'check_formats': 'selected',
                    'include_live_dash': True,
                    'enable_legacy_api': True,
                    'session_token': self._generate_session_token(),
                    'visitor_data': self._get_visitor_data()
                }
            },
            
            # 格式选择 - 2025年优化
            'format': 'best[height<=1080][ext=mp4]/best[height<=1080]/best[ext=mp4]/best',
            'format_sort': ['res:1080', 'vcodec:av01', 'acodec:opus'],
            
            # YouTube特定设置
            'youtube_skip_dash_manifest': False,
            'youtube_include_dash_manifest': True,
            'youtube_skip_hls_manifest': False,
            'youtube_print_sig_code': False,
            
            # 强化重试机制
            'extractor_retries': 20,
            'retries': 30,
            'fragment_retries': 25,
            
            # 智能延迟
            'sleep_interval': random.uniform(2, 5),
            'max_sleep_interval': 10,
            'sleep_interval_requests': random.uniform(1, 3),
            
            # 网络配置
            'socket_timeout': 60,
            'read_timeout': 90,
            
            # 2025年强化请求头
            'http_headers': {
                'User-Agent': self._get_random_user_agent(),
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Cache-Control': 'max-age=0',
                'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            }
        })
        
        # 代理配置优化 - 2025年强化版
        if settings.HTTP_PROXY:
            proxy_url = settings.HTTP_PROXY
            if proxy_url.startswith('socks5://'):
                proxy_url = proxy_url.replace('socks5://', 'socks5h://')
            opts['proxy'] = proxy_url
            # 确保环境变量也设置了代理
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
            os.environ['http_proxy'] = proxy_url
            os.environ['https_proxy'] = proxy_url
        
        return opts
    
    def _get_random_user_agent(self) -> str:
        """获取随机User-Agent - 2025年更新"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"
        ]
        return random.choice(user_agents)
    
    async def get_video_info(self, url: str) -> dict:
        """提取视频信息 - 带客户端轮换的重试机制"""
        max_attempts = len(self._clients) * 2  # 每个客户端尝试2次
        
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    self._rotate_client()  # 轮换客户端
                    time.sleep(random.uniform(3, 6))  # 增加延迟
                
                return await super().get_video_info(url)
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # 根据错误类型决定是否继续尝试
                if any(keyword in error_msg for keyword in [
                    "sign in to confirm",
                    "this video is unavailable",
                    "private video",
                    "deleted",
                    "copyright"
                ]):
                    # 这些错误不需要重试
                    raise e
                
                if attempt == max_attempts - 1:
                    # 最后一次尝试失败
                    raise e
                
                # 记录错误并继续尝试下一个客户端
                print(f"客户端 {self._get_current_client()['name']} 失败，尝试下一个客户端...")
                
        raise Exception("所有客户端都无法获取视频信息")
    
    async def download(self, url: str, options: DownloadOptions, progress_callback=None, task_id: str = None) -> dict:
        """下载视频 - 带客户端轮换的重试机制"""
        max_attempts = len(self._clients) * 2
        
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    self._rotate_client()
                    time.sleep(random.uniform(5, 10))
                
                return await super().download(url, options, progress_callback, task_id)
                
            except Exception as e:
                error_msg = str(e).lower()
                
                if any(keyword in error_msg for keyword in [
                    "sign in to confirm",
                    "this video is unavailable", 
                    "private video",
                    "deleted",
                    "copyright"
                ]):
                    raise e
                
                if attempt == max_attempts - 1:
                    raise e
                
                print(f"客户端 {self._get_current_client()['name']} 下载失败，尝试下一个客户端...")
        
        raise Exception("所有客户端都无法下载视频") 