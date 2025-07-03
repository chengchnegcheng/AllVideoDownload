"""
字幕基本信息查询API

包含语言列表、模型列表、翻译方法等基础信息查询功能
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/languages")
async def get_supported_languages():
    """获取支持的语言列表"""
    languages = {
        "zh": "中文",
        "en": "英语", 
        "ja": "日语",
        "ko": "韩语",
        "fr": "法语",
        "de": "德语",
        "es": "西班牙语",
        "it": "意大利语",
        "pt": "葡萄牙语",
        "ru": "俄语",
        "ar": "阿拉伯语",
        "hi": "印地语"
    }
    return {"languages": languages, "default": "auto"}


@router.get("/models")
async def get_available_models():
    """获取可用的AI模型列表"""
    models = {
        "tiny": "最快，准确度最低 (50MB)",
        "base": "平衡选择 (150MB)", 
        "small": "较好准确度 (250MB)",
        "medium": "高准确度 (800MB)",
        "large": "最高准确度 (1.5GB)"
    }
    return {"models": models, "default": "base"}


@router.get("/translation-methods") 
async def get_translation_methods():
    """获取支持的翻译方法"""
    methods = {
        "sentencepiece": {
            "name": "SentencePiece翻译",
            "description": "高质量本地翻译方法",
            "offline": True,
            "speed": "快速",
            "quality": "高"
        }
    }
    return {"methods": methods, "default": "sentencepiece"} 