"""
AVD Web版本 - 工具模块

提供各种实用工具函数和增强功能
"""

from .validators import (
    validate_url,
    validate_video_url,
    validate_file_path,
    validate_quality,
    validate_format,
)
from .logger import (
    setup_logger,
    get_logger,
    request_logger,
    download_logger,
    subtitle_logger,
)

# 导入增强的字幕处理功能 - 暂时禁用以避免启动问题
ADVANCED_PROCESSOR_AVAILABLE = False
ENHANCED_CONFIG_AVAILABLE = False  
SMART_CACHE_AVAILABLE = False

# try:
#     from ..core.subtitle_modules.subtitle_processor_advanced import (
#         get_advanced_subtitle_processor,
#         ProcessingPriority,
#         TaskStatus,
#         AdvancedSubtitleProcessor
#     )
#     ADVANCED_PROCESSOR_AVAILABLE = True
# except ImportError:
#     ADVANCED_PROCESSOR_AVAILABLE = False

# try:
#     from ..core.subtitle_modules.enhanced_config_manager import (
#         get_enhanced_config_manager,
#         ConfigCategory,
#         QualityMode,
#         WhisperConfig,
#         TranslationConfig,
#         ProcessingConfig,
#         SystemConfig,
#         UserPreference,
#         PerformanceConfig,
#         EnhancedConfigManager
#     )
#     ENHANCED_CONFIG_AVAILABLE = True
# except ImportError:
#     ENHANCED_CONFIG_AVAILABLE = False

# try:
#     from ..core.subtitle_modules.smart_cache_manager import (
#         get_smart_cache_manager,
#         CacheType,
#         CacheStrategy,
#         CacheItem,
#         CacheConfig,
#         SmartCacheManager
#     )
#     SMART_CACHE_AVAILABLE = True
# except ImportError:
#     SMART_CACHE_AVAILABLE = False

__all__ = [
    # 基础工具
    "setup_logger",
    "get_logger",
    "RequestLogger",
    "DownloadLogger",
    "SubtitleLogger",
    "request_logger",
    "download_logger",
    "subtitle_logger",
    "validate_url",
    "validate_video_url",
    "validate_file_path",
    "validate_quality",
    "validate_format",
    "TempFileCleanup",
    # 新增的工具
    "TempFileManager",
    "temp_file_manager",
    "create_temp_file",
    "create_temp_dir",
    "cleanup_temp_file",
    "cleanup_all_temp_files",
    "cleanup_expired_temp_files",
    # 装饰器
    "handle_api_errors",
    "retry",
    "log_execution_time",
    "validate_input",
    "cache_result",
    "api_endpoint",
    "download_endpoint",
    "subtitle_endpoint",
    # 可用性标志
    "ADVANCED_PROCESSOR_AVAILABLE",
    "ENHANCED_CONFIG_AVAILABLE", 
    "SMART_CACHE_AVAILABLE",
]

# 有条件地添加高级功能到__all__
if ADVANCED_PROCESSOR_AVAILABLE:
    __all__.extend([
        "get_advanced_subtitle_processor",
        "ProcessingPriority",
        "TaskStatus", 
        "AdvancedSubtitleProcessor"
    ])

if ENHANCED_CONFIG_AVAILABLE:
    __all__.extend([
        "get_enhanced_config_manager",
        "ConfigCategory",
        "QualityMode",
        "WhisperConfig",
        "TranslationConfig", 
        "ProcessingConfig",
        "SystemConfig",
        "UserPreference",
        "PerformanceConfig",
        "EnhancedConfigManager"
    ])

if SMART_CACHE_AVAILABLE:
    __all__.extend([
        "get_smart_cache_manager",
        "CacheType",
        "CacheStrategy",
        "CacheItem", 
        "CacheConfig",
        "SmartCacheManager"
    ])


def get_improvement_status():
    """获取改进功能可用状态"""
    return {
        'advanced_processor': ADVANCED_PROCESSOR_AVAILABLE,
        'enhanced_config': ENHANCED_CONFIG_AVAILABLE,
        'smart_cache': SMART_CACHE_AVAILABLE,
        'all_available': all([
            ADVANCED_PROCESSOR_AVAILABLE,
            ENHANCED_CONFIG_AVAILABLE, 
            SMART_CACHE_AVAILABLE
        ])
    }


def initialize_improved_features():
    """初始化改进功能"""
    initialized = {}
    
    if ADVANCED_PROCESSOR_AVAILABLE:
        try:
            processor = get_advanced_subtitle_processor()
            initialized['advanced_processor'] = processor
        except Exception as e:
            print(f"高级处理器初始化失败: {e}")
            initialized['advanced_processor'] = None
    
    if ENHANCED_CONFIG_AVAILABLE:
        try:
            config_manager = get_enhanced_config_manager()
            initialized['enhanced_config'] = config_manager
        except Exception as e:
            print(f"增强配置管理器初始化失败: {e}")
            initialized['enhanced_config'] = None
    
    if SMART_CACHE_AVAILABLE:
        try:
            cache_manager = get_smart_cache_manager()
            initialized['smart_cache'] = cache_manager
        except Exception as e:
            print(f"智能缓存管理器初始化失败: {e}")
            initialized['smart_cache'] = None
    
    return initialized
