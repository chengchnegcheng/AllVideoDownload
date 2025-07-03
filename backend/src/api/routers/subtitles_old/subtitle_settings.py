"""
字幕设置模块 - 管理AI设置、翻译设置、模型配置等
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
import logging
import time
import os

from ....core.config import settings, TRANSLATION_METHODS
from ....core.subtitle_processor import get_subtitle_processor_instance

logger = logging.getLogger(__name__)
router = APIRouter()

# 支持的语言列表
SUBTITLE_LANGUAGES = {
    "auto": "自动检测",
    "zh": "中文",
    "en": "英语",
    "ja": "日语",
    "ko": "韩语",
    "fr": "法语",
    "de": "德语",
    "es": "西班牙语",
    "ru": "俄语"
}

@router.get("/languages")
async def get_supported_languages():
    """获取支持的字幕语言列表"""
    return {
        "languages": SUBTITLE_LANGUAGES,
        "default": "auto"
    }

@router.get("/models")
async def get_available_models():
    """获取可用的AI模型"""
    return {
        "models": {
            "tiny": "最快，准确度最低 (50MB)",
            "base": "平衡选择 (150MB)", 
            "small": "较好准确度 (250MB)",
            "medium": "高准确度 (800MB)",
            "large": "最高准确度 (1.5GB)"
        },
        "default": "base"
    }

@router.get("/translation-methods")
async def get_translation_methods():
    """获取可用的翻译方法"""
    # 构建翻译方法列表，只返回SentencePiece
    methods = []
    for code in settings.AVAILABLE_TRANSLATION_METHODS:
        method_info = TRANSLATION_METHODS.get(code, {})
        method_data = {
            "code": code,
            "name": method_info.get("name", code.replace("_", " ").title()),
            "description": method_info.get("description", ""),
            "quality": method_info.get("quality", "高"),
            "speed": method_info.get("speed", "快"),
            "requires_internet": method_info.get("requires_internet", False),
            "supports_offline": method_info.get("supports_offline", True),
            "recommended": True  # SentencePiece是唯一推荐的方法
        }
        
        # 添加图标
        if code == "sentencepiece":
            method_data["name"] = "🚀 " + method_data["name"]
            method_data["note"] = "基于SentencePiece的高效翻译"
        
        methods.append(method_data)
    
    return {
        "methods": methods,
        "current_default": settings.SUBTITLE_TRANSLATION_METHOD,
        "timeout": settings.SUBTITLE_TRANSLATION_TIMEOUT,
        "max_retries": settings.SUBTITLE_TRANSLATION_MAX_RETRIES,
        "fallback_enabled": settings.SUBTITLE_FALLBACK_ENABLED
    }

@router.get("/ai-settings")
async def get_ai_settings():
    """获取AI配置和模型信息"""
    try:
        from ....core.subtitle_processor import SubtitleProcessor
        
        # 创建处理器实例以获取实时信息
        processor = SubtitleProcessor()
        model_info = processor.get_model_info()
        
        # 设备信息检测
        device_info = {
            "current_device": model_info["device"],
            "auto_selection": model_info["auto_device_selection"],
            "cuda_available": False,
            "gpu_memory_gb": 0,
            "cpu_cores": os.cpu_count() or 1
        }
        
        # 检测CUDA
        try:
            import torch
            if torch.cuda.is_available():
                device_info["cuda_available"] = True
                if torch.cuda.device_count() > 0:
                    device_info["gpu_memory_gb"] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    device_info["gpu_name"] = torch.cuda.get_device_properties(0).name
        except ImportError:
            pass
        
        # Whisper配置
        whisper_config = {
            "model_size": settings.WHISPER_MODEL_SIZE,
            "available_models": settings.WHISPER_AVAILABLE_MODELS,
            "compute_type": settings.WHISPER_COMPUTE_TYPE,
            "available_compute_types": ["int8", "int16", "float16", "float32"],
            "beam_size": settings.WHISPER_BEAM_SIZE,
            "best_of": settings.WHISPER_BEST_OF,
            "patience": settings.WHISPER_PATIENCE,
            "vad_filter": settings.WHISPER_VAD_FILTER,
            "vad_threshold": settings.WHISPER_VAD_THRESHOLD,
            "vad_min_silence_duration_ms": settings.WHISPER_VAD_MIN_SILENCE_DURATION_MS
        }
        
        # 性能配置
        performance_config = {
            "max_memory_usage_mb": settings.AI_MAX_MEMORY_USAGE_MB,
            "batch_size": settings.AI_BATCH_SIZE,
            "num_workers": settings.AI_NUM_WORKERS,
            "model_cache_size": settings.AI_MODEL_CACHE_SIZE,
            "current_cache_size": model_info["current_cache_size"]
        }
        
        # 语言和后处理配置
        language_config = {
            "auto_language_detection": settings.AI_AUTO_LANGUAGE_DETECTION,
            "language_detection_threshold": settings.AI_LANGUAGE_DETECTION_THRESHOLD,
            "subtitle_post_processing": settings.AI_SUBTITLE_POST_PROCESSING,
            "remove_duplicate_sentences": settings.AI_REMOVE_DUPLICATE_SENTENCES,
            "sentence_min_length": settings.AI_SENTENCE_MIN_LENGTH,
            "sentence_max_length": settings.AI_SENTENCE_MAX_LENGTH
        }
        
        # 实验性功能
        experimental_config = {
            "experimental_features": settings.AI_EXPERIMENTAL_FEATURES,
            "use_enhanced_whisper": settings.AI_USE_ENHANCED_WHISPER,
            "speaker_diarization": settings.AI_SPEAKER_DIARIZATION
        }
        
        # 翻译配置（仅本地翻译）
        translation_config = {
            "strategy": settings.TRANSLATION_STRATEGY
        }
        
        return {
            "success": True,
            # 兼容性：提供顶级字段供前端使用
            "whisper_model_size": settings.WHISPER_MODEL_SIZE,
            "device": device_info["current_device"],
            "compute_type": settings.WHISPER_COMPUTE_TYPE,
            "source_language": settings.WHISPER_SOURCE_LANGUAGE,
            "post_processing": settings.AI_SUBTITLE_POST_PROCESSING,
            # 原有的详细配置结构
            "device_info": device_info,
            "whisper_config": whisper_config,
            "performance_config": performance_config,
            "language_config": language_config,
            "experimental_config": experimental_config,
            "translation_config": translation_config,
            "model_info": model_info
        }
        
    except Exception as e:
        logger.error(f"获取AI设置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取AI设置失败: {str(e)}")

@router.post("/ai-settings")
async def save_ai_settings(request: dict):
    """保存字幕生成AI设置"""
    try:
        model_size = request.get('whisper_model_size')
        device = request.get('device')
        compute_type = request.get('compute_type')
        source_language = request.get('source_language')
        post_processing = request.get('post_processing')
        
        if not model_size:
            raise HTTPException(status_code=400, detail="模型大小参数必需")
        
        # 验证模型大小是否有效
        valid_models = ["tiny", "tiny.en", "base", "base.en", "small", "small.en", 
                       "medium", "medium.en", "large", "large-v1", "large-v2", "large-v3"]
        if model_size not in valid_models:
            raise HTTPException(status_code=400, detail=f"无效的模型大小: {model_size}")
        
        # 验证设备类型
        if device and device not in ['cpu', 'cuda', 'auto']:
            raise HTTPException(status_code=400, detail=f"无效的设备类型: {device}")
            
        # 验证计算类型
        if compute_type and compute_type not in ['int8', 'int16', 'float16', 'float32']:
            raise HTTPException(status_code=400, detail=f"无效的计算类型: {compute_type}")
        
        # 验证源语言
        valid_languages = ['auto', 'en', 'zh', 'ja', 'ko', 'fr', 'de', 'es', 'ru', 'it', 'pt', 'nl', 'ar']
        if source_language and source_language not in valid_languages:
            raise HTTPException(status_code=400, detail=f"无效的源语言: {source_language}")
        
        # 更新配置
        updated_settings = {}
        
        if model_size:
            settings.WHISPER_MODEL_SIZE = model_size
            updated_settings['whisper_model_size'] = model_size
        
        if device:
            if device == 'auto':
                settings.AI_AUTO_DEVICE_SELECTION = True
                settings.WHISPER_DEVICE = 'cuda' if hasattr(settings, 'cuda_available') and settings.cuda_available else 'cpu'
            else:
                settings.AI_AUTO_DEVICE_SELECTION = False
                settings.WHISPER_DEVICE = device
            updated_settings['device'] = device
        
        if compute_type:
            settings.WHISPER_COMPUTE_TYPE = compute_type
            updated_settings['compute_type'] = compute_type
        
        if source_language is not None:
            settings.WHISPER_SOURCE_LANGUAGE = source_language
            updated_settings['source_language'] = source_language
        
        if post_processing is not None:
            settings.AI_SUBTITLE_POST_PROCESSING = bool(post_processing)
            updated_settings['post_processing'] = bool(post_processing)
            
        logger.info(f"字幕生成设置已更新: {updated_settings}")
        
        # 重新加载字幕处理器配置
        subtitle_processor = get_subtitle_processor_instance()
        reload_result = subtitle_processor.reload_config()
        
        return {
            "success": True,
            "message": "字幕生成设置保存成功",
            "updated_settings": updated_settings,
            "reload_status": reload_result,
            "note": "新设置已立即生效"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存字幕生成设置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存字幕生成设置失败: {str(e)}")

@router.get("/translation-settings")
async def get_translation_settings():
    """获取翻译设置"""
    try:
        return {
            "success": True,
            "settings": {
                "default_method": settings.SUBTITLE_TRANSLATION_METHOD,
                "timeout": settings.SUBTITLE_TRANSLATION_TIMEOUT,
                "max_retries": settings.SUBTITLE_TRANSLATION_MAX_RETRIES,
                "fallback_enabled": settings.SUBTITLE_FALLBACK_ENABLED,
                "available_methods": settings.AVAILABLE_TRANSLATION_METHODS
            },
            "methods_info": TRANSLATION_METHODS,
            "description": "翻译方法系统设置"
        }
        
    except Exception as e:
        logger.error(f"获取翻译设置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取翻译设置失败: {str(e)}")

@router.post("/translation-settings")
async def save_translation_settings(request: dict):
    """保存字幕翻译设置"""
    try:
        # 获取请求参数
        default_method = request.get('default_method')
        timeout = request.get('timeout')
        max_retries = request.get('max_retries')
        fallback_enabled = request.get('fallback_enabled')
        target_language = request.get('target_language')
        
        # 验证翻译方法
        if default_method and default_method not in settings.AVAILABLE_TRANSLATION_METHODS:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的翻译方法: {default_method}。可用方法: {', '.join(settings.AVAILABLE_TRANSLATION_METHODS)}"
            )
        
        # 验证数值参数
        if timeout is not None:
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                raise HTTPException(status_code=400, detail="超时时间必须是正数")
            if timeout > 120:
                raise HTTPException(status_code=400, detail="超时时间不能超过120秒")
        
        if max_retries is not None:
            if not isinstance(max_retries, int) or max_retries < 0 or max_retries > 5:
                raise HTTPException(status_code=400, detail="重试次数必须是0-5之间的整数")
        
        # 验证目标语言
        valid_target_languages = [
            'zh-cn', 'zh-tw', 'en', 'ja', 'ko', 'fr', 'de', 'es', 'ru', 
            'it', 'pt', 'nl', 'ar', 'hi', 'th', 'vi', 'tr', 'pl', 'sv', 'da'
        ]
        if target_language and target_language not in valid_target_languages:
            raise HTTPException(status_code=400, detail=f"无效的目标语言: {target_language}")
        
        # 更新配置
        updated_settings = {}
        
        if default_method:
            settings.SUBTITLE_TRANSLATION_METHOD = default_method
            updated_settings['default_method'] = default_method
        
        if timeout is not None:
            settings.SUBTITLE_TRANSLATION_TIMEOUT = int(timeout)
            updated_settings['timeout'] = int(timeout)
        
        if max_retries is not None:
            settings.SUBTITLE_TRANSLATION_MAX_RETRIES = max_retries
            updated_settings['max_retries'] = max_retries
        
        if fallback_enabled is not None:
            settings.SUBTITLE_FALLBACK_ENABLED = bool(fallback_enabled)
            updated_settings['fallback_enabled'] = bool(fallback_enabled)
        
        if target_language:
            settings.SUBTITLE_DEFAULT_TARGET_LANGUAGE = target_language
            updated_settings['target_language'] = target_language
        
        logger.info(f"字幕翻译设置已更新: {updated_settings}")
        
        return {
            "success": True,
            "message": "字幕翻译设置保存成功",
            "updated_settings": updated_settings,
            "current_settings": {
                "default_method": settings.SUBTITLE_TRANSLATION_METHOD,
                "timeout": settings.SUBTITLE_TRANSLATION_TIMEOUT,
                "max_retries": settings.SUBTITLE_TRANSLATION_MAX_RETRIES,
                "fallback_enabled": settings.SUBTITLE_FALLBACK_ENABLED,
                "target_language": getattr(settings, 'SUBTITLE_DEFAULT_TARGET_LANGUAGE', 'zh-cn')
            },
            "note": "新设置已立即生效"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存字幕翻译设置失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存字幕翻译设置失败: {str(e)}")

@router.post("/test-translation")
async def test_translation_service(request: dict):
    """测试翻译服务"""
    try:
        text = request.get('text', 'Hello, this is a test.')
        target_language = request.get('target_language', 'zh')
        method = request.get('method', 'sentencepiece')
        
        if method not in settings.AVAILABLE_TRANSLATION_METHODS:
            raise HTTPException(status_code=400, detail=f"不支持的翻译方法: {method}")
        
        logger.info(f"测试翻译服务: '{text}' -> {target_language}, 方法: {method}")
        
        # 测试本地翻译（SentencePiece）
        if method == 'sentencepiece':
            from ....core.subtitle_processor import SubtitleProcessor
            processor = SubtitleProcessor()
            
            start_time = time.time()
            try:
                if not processor.translator.load_model(target_language):
                    raise Exception("翻译器初始化失败")
                
                result_text = processor.translator.translate_text(text, target_language)
                execution_time = time.time() - start_time
                
                return {
                    "success": True,
                    "method": "sentencepiece",
                    "original_text": text,
                    "translated_text": result_text,
                    "target_language": target_language,
                    "execution_time": round(execution_time, 2),
                    "service_used": "local"
                }
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"本地翻译失败: {e}")
                return {
                    "success": False,
                    "method": "sentencepiece",
                    "original_text": text,
                    "execution_time": round(execution_time, 2),
                    "error": f"本地翻译失败: {str(e)}",
                    "service_used": "local"
                }
        
    except Exception as e:
        logger.error(f"翻译服务测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"翻译服务测试失败: {str(e)}")
