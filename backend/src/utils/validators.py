"""
AVD Web版本 - 验证器模块

提供各种验证功能
"""

import re
from urllib.parse import urlparse


def validate_url(url: str) -> bool:
    """验证URL格式是否正确
    
    Args:
        url: 要验证的URL字符串
        
    Returns:
        布尔值，True表示URL格式正确
    """
    if not isinstance(url, str) or not url.strip():
        return False
    
    try:
        # 使用urlparse解析URL
        parsed = urlparse(url.strip())
        
        # 检查必要的组件
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # 检查协议是否支持
        if parsed.scheme.lower() not in ['http', 'https']:
            return False
        
        # 基本的域名格式检查
        domain_pattern = re.compile(
            r'^[a-zA-Z0-9]'  # 开始字符
            r'[a-zA-Z0-9\-\.]*'  # 中间字符
            r'[a-zA-Z0-9]$'  # 结束字符
        )
        
        if not domain_pattern.match(parsed.netloc.split(':')[0]):
            return False
        
        return True
        
    except Exception:
        return False


def validate_video_url(url: str) -> bool:
    """验证是否为支持的视频平台URL
    
    Args:
        url: 要验证的URL字符串
        
    Returns:
        布尔值，True表示是支持的视频平台
    """
    if not validate_url(url):
        return False
    
    # 支持的平台域名
    supported_domains = [
        'youtube.com', 'youtu.be', 'www.youtube.com',
        'bilibili.com', 'www.bilibili.com', 'b23.tv',
        'twitter.com', 'x.com', 'www.twitter.com',
        'tiktok.com', 'www.tiktok.com',
        'instagram.com', 'www.instagram.com',
        'facebook.com', 'www.facebook.com',
        'twitch.tv', 'www.twitch.tv',
        'vimeo.com', 'www.vimeo.com',
        'dailymotion.com', 'www.dailymotion.com'
    ]
    
    try:
        parsed = urlparse(url.lower())
        domain = parsed.netloc.lower()
        
        # 移除端口号
        if ':' in domain:
            domain = domain.split(':')[0]
        
        return any(supported_domain in domain for supported_domain in supported_domains)
        
    except Exception:
        return False


def validate_file_path(file_path: str) -> bool:
    """验证文件路径是否安全
    
    Args:
        file_path: 文件路径
        
    Returns:
        布尔值，True表示路径安全
    """
    if not isinstance(file_path, str) or not file_path.strip():
        return False
    
    # 禁止的路径模式
    forbidden_patterns = [
        '../',  # 目录遍历
        '..\\',  # Windows目录遍历
        '~/',   # 用户目录
        '/etc/',  # 系统配置目录
        '/var/',  # 系统变量目录
        '/usr/',  # 系统程序目录
        'C:\\Windows\\',  # Windows系统目录
        'C:\\Program Files\\',  # Windows程序目录
    ]
    
    path_lower = file_path.lower()
    
    # 检查是否包含禁止的模式
    for pattern in forbidden_patterns:
        if pattern.lower() in path_lower:
            return False
    
    # 检查文件名中的特殊字符
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
    for char in invalid_chars:
        if char in file_path:
            return False
    
    return True


def validate_quality(quality: str) -> bool:
    """验证视频质量参数
    
    Args:
        quality: 质量参数
        
    Returns:
        布尔值，True表示质量参数有效
    """
    if not isinstance(quality, str):
        return False
    
    valid_qualities = [
        'best', 'worst',
        '2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p'
    ]
    
    return quality.lower() in [q.lower() for q in valid_qualities]


def validate_format(format_str: str) -> bool:
    """验证视频格式参数
    
    Args:
        format_str: 格式参数
        
    Returns:
        布尔值，True表示格式参数有效
    """
    if not isinstance(format_str, str):
        return False
    
    valid_formats = [
        'mp4', 'webm', 'flv', 'avi', 'mov', 'mkv',
        'mp3', 'aac', 'ogg', 'wav', 'flac'
    ]
    
    return format_str.lower() in [f.lower() for f in valid_formats] 