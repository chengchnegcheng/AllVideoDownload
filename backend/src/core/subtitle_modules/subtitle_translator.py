"""
字幕翻译器模块

负责字幕的翻译功能，使用稳定的MarianMT和Google翻译API
参考subtitles.py优化实现
"""

import os
import re
import time
import asyncio
import random
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path

from ...utils.logger import get_logger
logger = get_logger(__name__)
from ..config import settings


class SubtitleTranslator:
    """字幕翻译器（优化版）"""
    
    def __init__(self):
        """初始化翻译器"""
        self.offline_translator = None
        self.google_available = False
        self._init_translators()
        logger.info("字幕翻译器初始化完成（优化版）")
    
    def _init_translators(self):
        """初始化翻译器组件"""
        try:
            # 初始化离线翻译器（MarianMT）
            self._init_offline_translator()
            
            # 测试Google翻译API可用性
            self._test_google_api()
            
        except Exception as e:
            logger.error(f"翻译器初始化失败: {e}")
    
    def _init_offline_translator(self):
        """初始化离线翻译器（MarianMT）"""
        try:
            # 尝试导入transformers和torch
            import torch
            from transformers import MarianMTModel, MarianTokenizer
            
            # 使用更稳定的模型选择
            self.model_map = {
                "de_to_zh": "Helsinki-NLP/opus-mt-de-zh",
                "en_to_zh": "Helsinki-NLP/opus-mt-en-zh", 
                "fr_to_zh": "Helsinki-NLP/opus-mt-fr-zh",
                "es_to_zh": "Helsinki-NLP/opus-mt-es-zh",
                "ru_to_zh": "Helsinki-NLP/opus-mt-ru-zh",
                "zh_to_en": "Helsinki-NLP/opus-mt-zh-en",
                "zh_to_de": "Helsinki-NLP/opus-mt-zh-de",
                "zh_to_fr": "Helsinki-NLP/opus-mt-zh-fr",
                "zh_to_es": "Helsinki-NLP/opus-mt-zh-es"
            }
            
            self.loaded_models = {}
            self.offline_translator = {}
            logger.info("离线翻译器（MarianMT）初始化成功")
            
        except ImportError as e:
            logger.warning(f"离线翻译模型不可用: {e}")
            self.offline_translator = None
    
    def _test_google_api(self):
        """测试Google翻译API可用性"""
        try:
            import requests
            
            # 测试简单的翻译请求
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "en",
                "tl": "zh",
                "dt": "t",
                "q": "test"
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                self.google_available = True
                logger.info("Google翻译API可用")
            else:
                self.google_available = False
                logger.warning("Google翻译API不可用")
                
        except Exception as e:
            logger.warning(f"Google翻译API测试失败: {e}")
            self.google_available = False
    
    def get_supported_languages(self) -> Dict[str, Any]:
        """获取支持的语言列表"""
        return {
            "zh": "中文",
            "zh-cn": "简体中文", 
            "zh-tw": "繁体中文",
            "en": "英语",
            "ja": "日语",
            "ko": "韩语",
            "fr": "法语",
            "de": "德语",
            "es": "西班牙语",
            "ru": "俄语",
            "ar": "阿拉伯语",
            "hi": "印地语",
            "pt": "葡萄牙语",
            "it": "意大利语",
            "th": "泰语",
            "vi": "越南语",
            "auto": "自动检测"
        }
    
    def detect_language(self, text: str) -> str:
        """检测文本语言"""
        try:
            if not text or len(text.strip()) < 3:
                return "unknown"
            
            # 基于字符的简单语言检测
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            if chinese_chars > len(text) * 0.3:
                return "zh"
            
            japanese_chars = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', text))
            if japanese_chars > len(text) * 0.2:
                return "ja"
            
            korean_chars = len(re.findall(r'[\uac00-\ud7af]', text))
            if korean_chars > len(text) * 0.2:
                return "ko"
            
            # 德语特征词检测
            text_lower = text.lower()
            german_words = ['der', 'die', 'das', 'und', 'ist', 'ein', 'eine', 'mit', 'auf', 'für']
            if sum(1 for word in german_words if word in text_lower) >= 2:
                return "de"
            
            # 法语特征词检测
            french_words = ['le', 'la', 'les', 'de', 'du', 'des', 'et', 'est', 'une', 'avec']
            if sum(1 for word in french_words if word in text_lower) >= 2:
                return "fr"
            
            # 西班牙语特征词检测
            spanish_words = ['el', 'la', 'los', 'las', 'de', 'del', 'y', 'es', 'una', 'con']
            if sum(1 for word in spanish_words if word in text_lower) >= 2:
                return "es"
            
            # 俄语字符检测
            cyrillic_chars = len(re.findall(r'[\u0400-\u04ff]', text))
            if cyrillic_chars > len(text) * 0.2:
                return "ru"
            
            return "en"  # 默认英语
            
        except Exception as e:
            logger.error(f"语言检测失败: {e}")
            return "unknown"
    
    def _clean_text_for_translation(self, text: str) -> str:
        """清理文本用于翻译"""
        if not text:
            return ""
        
        # 移除多余的空白字符，但保留换行
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        
        # 清理字幕特有的标记但保留基本格式
        text = re.sub(r'<[^>]*>', '', text)  # 移除HTML标记
        text = re.sub(r'\[[^\]]*\]', '', text)  # 移除方括号标记
        
        return text.strip()
    
    async def _try_offline_translation(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """尝试使用离线模型翻译"""
        try:
            if not self.offline_translator:
                return None
            
            # 构建模型键
            model_key = f"{source_lang}_to_{target_lang}"
            if model_key not in self.model_map:
                return None
            
            # 加载模型（如果未加载）
            if model_key not in self.loaded_models:
                from transformers import MarianMTModel, MarianTokenizer
                
                model_name = self.model_map[model_key]
                logger.info(f"加载翻译模型: {model_name}")
                
                tokenizer = MarianTokenizer.from_pretrained(model_name)
                model = MarianMTModel.from_pretrained(model_name)
                
                self.loaded_models[model_key] = {
                    'tokenizer': tokenizer,
                    'model': model
                }
            
            # 执行翻译
            components = self.loaded_models[model_key]
            tokenizer = components['tokenizer']
            model = components['model']
            
            # 分词并翻译
            tokenized = tokenizer([text], return_tensors="pt", padding=True, truncation=True, max_length=512)
            translated_tokens = model.generate(**tokenized, max_length=512, num_beams=4, early_stopping=True)
            translated_text = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
            
            logger.info(f"离线翻译成功: {text[:30]} -> {translated_text[:30]}")
            return translated_text
            
        except Exception as e:
            logger.warning(f"离线翻译失败: {e}")
            return None
    
    async def _try_google_translation(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """尝试使用Google翻译API"""
        try:
            if not self.google_available:
                return None
            
            import requests
            import json
            
            # 构建API请求
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": source_lang if source_lang != "auto" else "auto",
                "tl": target_lang,
                "dt": "t",
                "q": text
            }
            
            # 发送请求
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            translated_text = ""
            
            # 提取翻译结果
            if result and isinstance(result, list) and len(result) > 0:
                for sentence in result[0]:
                    if sentence and isinstance(sentence, list) and len(sentence) > 0:
                        translated_text += sentence[0]
            
            if translated_text:
                logger.info(f"Google翻译成功: {text[:30]} -> {translated_text[:30]}")
                return translated_text
            else:
                return None
                
        except Exception as e:
            logger.warning(f"Google翻译失败: {e}")
            return None
    
    async def translate_text(self, text: str, target_lang: str = "zh", source_lang: str = "auto") -> str:
        """
        翻译文本（优化版）
        
        Args:
            text: 要翻译的文本
            target_lang: 目标语言
            source_lang: 源语言
            
        Returns:
            str: 翻译后的文本
        """
        try:
            if not text or not text.strip():
                return text
            
            # 清理文本
            clean_text = self._clean_text_for_translation(text)
            if not clean_text:
                return text
            
            # 检测源语言
            if source_lang == "auto":
                source_lang = self.detect_language(clean_text)
            
            # 检查是否需要翻译
            if source_lang == target_lang:
                return text
            
            # 1. 首先尝试离线翻译（MarianMT）
            translated = await self._try_offline_translation(clean_text, source_lang, target_lang)
            if translated and self._is_translation_valid(clean_text, translated):
                return self._postprocess_translation(translated)
            
            # 2. 然后尝试Google翻译
            translated = await self._try_google_translation(clean_text, source_lang, target_lang)
            if translated and self._is_translation_valid(clean_text, translated):
                return self._postprocess_translation(translated)
            
            # 3. 如果都失败，使用简单字典翻译
            translated = self._try_simple_translation(clean_text, target_lang)
            if translated:
                return translated
            
            # 最后返回原文
            logger.warning(f"所有翻译方法都失败，保留原文: {text[:30]}")
            return text
            
        except Exception as e:
            logger.error(f"翻译失败: {e}")
            return text
    
    def _is_translation_valid(self, original: str, translated: str) -> bool:
        """检查翻译是否有效"""
        if not translated or translated.strip() == "":
            return False
        
        # 检查是否与原文相同（可能翻译失败）
        if original.strip() == translated.strip():
            return False
        
        # 检查长度合理性（翻译结果不应过短或过长）
        if len(translated) < len(original) * 0.1 or len(translated) > len(original) * 5:
            return False
        
        return True
    
    def _postprocess_translation(self, translated_text: str) -> str:
        """后处理翻译结果"""
        if not translated_text:
            return translated_text
        
        # 修复中文标点符号
        translated_text = translated_text.replace(' , ', '，')
        translated_text = translated_text.replace(' . ', '。')
        translated_text = translated_text.replace(' ! ', '！')
        translated_text = translated_text.replace(' ? ', '？')
        translated_text = translated_text.replace(' : ', '：')
        translated_text = translated_text.replace(' ; ', '；')
        
        # 移除中文字符间的不必要空格
        translated_text = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', translated_text)
        
        return translated_text.strip()
    
    def _try_simple_translation(self, text: str, target_lang: str) -> Optional[str]:
        """简单字典翻译（备用方案）"""
        try:
            if target_lang != "zh":
                return None
            
            # 简单的英译中字典
            translation_dict = {
                "welcome": "欢迎", "to": "到", "the": "", "world": "世界",
                "of": "的", "motion": "运动", "we": "我们", "create": "创造",
                "foundation": "基础", "for": "为了", "together": "共同",
                "our": "我们的", "mission": "使命", "is": "是", "you": "您",
                "and": "和", "with": "与", "in": "在", "on": "在", "at": "在",
                "hello": "你好", "good": "好的", "great": "伟大的",
                "new": "新的", "old": "旧的", "big": "大的", "small": "小的"
            }
            
            # 简单的词汇替换
            words = text.lower().split()
            translated_words = []
            
            for word in words:
                # 移除标点符号
                clean_word = re.sub(r'[^\w]', '', word)
                if clean_word in translation_dict:
                    translation = translation_dict[clean_word]
                    if translation:  # 忽略空字符串翻译
                        translated_words.append(translation)
                else:
                    translated_words.append(word)
            
            result = ''.join(translated_words)
            if result != text:
                logger.info(f"简单翻译成功: {text} -> {result}")
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"简单翻译失败: {e}")
            return None

    async def translate_subtitles(self, subtitle_path: str, target_language: str = "zh", 
                                source_language: str = "auto", 
                                progress_callback: Optional[Callable] = None,
                                original_title: Optional[str] = None) -> Dict[str, Any]:
        """
        翻译字幕文件（优化版）
        
        Args:
            subtitle_path: 字幕文件路径
            target_language: 目标语言
            source_language: 源语言
            progress_callback: 进度回调函数
            original_title: 原始文件标题（可选）
            
        Returns:
            Dict[str, Any]: 翻译结果
        """
        try:
            if not os.path.exists(subtitle_path):
                raise Exception("字幕文件不存在")
            
            # 智能进度回调
            async def safe_progress_callback(progress, message=""):
                if progress_callback:
                    try:
                        import inspect
                        if inspect.iscoroutinefunction(progress_callback):
                            await progress_callback(progress, message)
                        else:
                            progress_callback(progress, message)
                    except Exception as e:
                        logger.warning(f"进度回调失败: {e}")
            
            await safe_progress_callback(5, "正在解析字幕文件...")
            
            # 解析字幕文件
            from .subtitle_file_handler_enhanced import EnhancedSubtitleFileHandler as SubtitleFileHandler
            file_handler = SubtitleFileHandler()
            subtitles = file_handler.parse_srt_file(subtitle_path)
            
            if not subtitles:
                raise Exception("字幕文件解析失败或为空")
            
            total_subtitles = len(subtitles)
            translated_subtitles = []
            successful_translations = 0
            
            logger.info(f"开始翻译字幕: {total_subtitles} 条")
            await safe_progress_callback(10, f"开始翻译 {total_subtitles} 条字幕...")
            
            # 批量翻译字幕
            for i, subtitle in enumerate(subtitles):
                try:
                    # 翻译文本
                    translated_text = await self.translate_text(
                        subtitle['text'],
                        target_language,
                        source_language
                    )
                    
                    translated_subtitles.append({
                        'index': subtitle['index'],
                        'start_time': subtitle['start_time'],
                        'end_time': subtitle['end_time'],
                        'text': translated_text,
                        'original_text': subtitle['text']
                    })
                    
                    if translated_text != subtitle['text']:
                        successful_translations += 1
                    
                    # 更新进度
                    progress = 10 + (i + 1) / total_subtitles * 80
                    await safe_progress_callback(
                        progress, 
                        f"翻译进度: {i+1}/{total_subtitles} (成功:{successful_translations})"
                    )
                    
                    # 添加延迟避免API限制
                    await asyncio.sleep(random.uniform(0.1, 0.5))
                    
                except Exception as e:
                    logger.warning(f"翻译第{i+1}条字幕失败: {e}")
                    # 保留原文
                    translated_subtitles.append({
                        'index': subtitle['index'],
                        'start_time': subtitle['start_time'],
                        'end_time': subtitle['end_time'],
                        'text': subtitle['text'],
                        'original_text': subtitle['text'],
                        'error': str(e)
                    })
            
            await safe_progress_callback(95, "正在保存翻译结果...")
            
            # 生成翻译文件名 - 优先使用原始标题
            if original_title:
                subtitle_name = original_title
                logger.info(f"使用原始标题生成翻译文件名: {subtitle_name}")
            else:
                subtitle_name = Path(subtitle_path).stem
                if subtitle_name.endswith("_subtitles"):
                    subtitle_name = subtitle_name[:-10]
                logger.info(f"从文件路径提取标题生成翻译文件名: {subtitle_name}")
            
            safe_name = file_handler.sanitize_filename(subtitle_name, max_length=160, default_name="translated_subtitle")
            translated_filename = f"{safe_name}_{target_language}_subtitles.srt"
            translated_path = os.path.join(settings.FILES_PATH, translated_filename)
            
            # 保存翻译后的字幕
            file_handler.save_srt_file(translated_subtitles, translated_path)
            
            await safe_progress_callback(100, "翻译完成")
            
            success_rate = (successful_translations / total_subtitles * 100) if total_subtitles > 0 else 0
            
            return {
                "success": True,
                "translated_file": translated_path,
                "source_language": source_language,
                "target_language": target_language,
                "subtitles_count": len(translated_subtitles),
                "successful_translations": successful_translations,
                "success_rate": f"{success_rate:.1f}%",
                "message": f"翻译完成，成功率: {success_rate:.1f}%"
            }
            
        except Exception as e:
            logger.error(f"字幕翻译失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def batch_translate(self, texts: List[str], target_language: str = "zh") -> List[str]:
        """
        批量翻译文本
        
        Args:
            texts: 文本列表
            target_language: 目标语言
            
        Returns:
            List[str]: 翻译结果列表
        """
        results = []
        
        for text in texts:
            try:
                translated = await self.translate_text(text, target_language)
                results.append(translated)
                # 添加随机延迟，避免请求过于频繁
                await asyncio.sleep(random.uniform(0.1, 0.3))
            except Exception as e:
                logger.error(f"批量翻译失败: {e}")
                results.append(text)  # 返回原文
        
        return results
    
    def get_translation_config(self) -> Dict[str, Any]:
        """获取翻译配置信息"""
        return {
            "offline_available": self.offline_translator is not None,
            "google_available": self.google_available,
            "quality_mode": "离线优先，Google备用",
            "supported_languages": list(self.get_supported_languages().keys()),
            "translation_methods": ["MarianMT离线", "Google翻译", "简单字典"]
        } 