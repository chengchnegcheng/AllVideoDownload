"""
增强字幕翻译器模块

提供多种翻译方案，包括在线翻译和离线翻译的备用方案
"""

import os
import re
import time
import asyncio
import json
from typing import Dict, List, Any, Optional, Callable

from ...utils.logger import get_logger
logger = get_logger(__name__)
from ..config import settings


class EnhancedSubtitleTranslator:
    """增强字幕翻译器"""
    
    def __init__(self):
        """初始化翻译器"""
        self.google_translator = None
        self.deep_google_translator = None
        self.translation_cache = {}  # 翻译缓存
        self._init_translators()
        self._load_offline_dictionary()
        logger.info("增强字幕翻译器初始化完成")
    
    def _init_translators(self):
        """初始化在线翻译器组件"""
        try:
            # 临时保存并清除代理环境变量
            proxy_env_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']
            temp_proxies = {}
            for var in proxy_env_vars:
                if var in os.environ:
                    temp_proxies[var] = os.environ[var]
                    del os.environ[var]
            
            try:
                # 初始化Google翻译器
                from googletrans import Translator as GoogleTranslator
                self.google_translator = GoogleTranslator()
                logger.info("Google翻译器初始化成功")
                
                # 初始化深度Google翻译器  
                from deep_translator import GoogleTranslator as DeepGoogleTranslator
                self.deep_google_translator = DeepGoogleTranslator(source='auto', target='zh-CN')
                logger.info("深度Google翻译器初始化成功")
                
            finally:
                # 恢复代理环境变量
                for var, value in temp_proxies.items():
                    os.environ[var] = value
            
        except Exception as e:
            logger.warning(f"在线翻译器初始化失败: {e}，将使用离线翻译")
            self.google_translator = None
            self.deep_google_translator = None
    
    def _load_offline_dictionary(self):
        """加载离线词典"""
        self.offline_dict = {
            # 德语-中文常用词汇
            "willkommen": "欢迎",
            "bei": "在",
            "auf": "在",
            "der": "的",
            "die": "的", 
            "das": "的",
            "hannover": "汉诺威",
            "messe": "展会",
            "world": "世界",
            "of": "的",
            "motion": "运动",
            "festo": "费斯托",
            "welt": "世界",
            "bewegung": "运动",
            "damit": "因此",
            "schaffen": "创造",
            "wir": "我们",
            "grundlage": "基础",
            "für": "为了",
            "eine": "一个",
            "kreislau": "循环",
            "um": "为了",
            "am": "在",
            "markt": "市场",
            "mitbewerbsfähig": "有竞争力",
            "zu": "到",
            "bleiben": "保持",
            "braucht": "需要",
            "es": "它",
            "entdecken": "发现",
            "sie": "您",
            "daktik": "教学法",
            "wie": "如何",
            "mitarbeite": "员工",
            "unsere": "我们的",
            "mission": "使命",
            "ist": "是",
            "ihnen": "您",
            "besten": "最好的",
            "möglichkeit": "可能性",
            "gemeinsam": "共同",
            "setzen": "设置",
            "in": "在",
            
            # 英语-中文常用词汇
            "welcome": "欢迎",
            "to": "到",
            "video": "视频",
            "subtitle": "字幕",
            "translation": "翻译",
            "processing": "处理",
            "complete": "完成",
            "success": "成功",
            "error": "错误",
            "failed": "失败",
            "downloading": "下载中",
            "generating": "生成中",
            "translating": "翻译中",
            "please": "请",
            "wait": "等待",
            "loading": "加载中",
            "finished": "完成",
            "file": "文件",
            "audio": "音频",
            "language": "语言",
            "model": "模型",
            "quality": "质量",
            "speed": "速度",
            "accuracy": "准确度"
        }
    
    async def translate_text_enhanced(self, text: str, target_lang: str = "zh", source_lang: str = "auto") -> str:
        """
        增强文本翻译，包含多种备用方案
        
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
            
            # 检查缓存
            cache_key = f"{clean_text}_{source_lang}_{target_lang}"
            if cache_key in self.translation_cache:
                return self.translation_cache[cache_key]
            
            # 方案1: 在线翻译
            translated = await self._try_online_translation(clean_text, target_lang, source_lang)
            if translated and translated != clean_text:
                self.translation_cache[cache_key] = translated
                return translated
            
            # 方案2: 离线词典翻译
            translated = await self._try_offline_translation(clean_text, target_lang, source_lang)
            if translated and translated != clean_text:
                self.translation_cache[cache_key] = translated
                return translated
            
            # 方案3: 基于规则的简单翻译
            translated = await self._try_rule_based_translation(clean_text, target_lang, source_lang)
            if translated and translated != clean_text:
                self.translation_cache[cache_key] = translated
                return translated
            
            # 如果所有方法都失败，返回原文但添加标记
            logger.warning(f"所有翻译方法都失败，返回原文: {text[:50]}...")
            return f"[原文] {text}"
            
        except Exception as e:
            logger.error(f"增强翻译失败: {e}")
            return text
    
    async def _try_online_translation(self, text: str, target_lang: str, source_lang: str) -> Optional[str]:
        """尝试在线翻译"""
        try:
            # 尝试Google翻译器
            if self.google_translator:
                try:
                    result = self.google_translator.translate(
                        text, 
                        src=source_lang if source_lang != "auto" else None,
                        dest=self._map_language_code(target_lang, "google")
                    )
                    
                    if result and hasattr(result, 'text') and result.text and result.text.strip():
                        translated = self._postprocess_translation(result.text, text)
                        if self._is_translation_valid(text, translated, target_lang):
                            return translated
                    
                except Exception as e:
                    logger.debug(f"Google翻译失败: {e}")
            
            # 尝试深度Google翻译器
            if self.deep_google_translator:
                try:
                    self.deep_google_translator.target = self._map_language_code(target_lang, "deep_google")
                    result = self.deep_google_translator.translate(text)
                    
                    if result and isinstance(result, str) and result.strip():
                        translated = self._postprocess_translation(result, text)
                        if self._is_translation_valid(text, translated, target_lang):
                            return translated
                    
                except Exception as e:
                    logger.debug(f"深度Google翻译失败: {e}")
                    
            return None
            
        except Exception as e:
            logger.debug(f"在线翻译尝试失败: {e}")
            return None
    
    async def _try_offline_translation(self, text: str, target_lang: str, source_lang: str) -> Optional[str]:
        """尝试离线词典翻译"""
        try:
            if target_lang not in ["zh", "zh-cn"]:
                return None  # 只支持翻译到中文
            
            # 将文本分词并翻译
            words = re.findall(r'\b\w+\b', text.lower())
            translated_words = []
            translation_found = False
            
            for word in words:
                if word in self.offline_dict:
                    translated_words.append(self.offline_dict[word])
                    translation_found = True
                else:
                    translated_words.append(word)
            
            if translation_found:
                # 重新组合翻译结果
                translated_text = ' '.join(translated_words)
                
                # 后处理：调整中文表达
                translated_text = self._improve_chinese_expression(translated_text)
                
                logger.info(f"离线翻译成功: {text[:30]} -> {translated_text[:30]}")
                return translated_text
            
            return None
            
        except Exception as e:
            logger.debug(f"离线翻译失败: {e}")
            return None
    
    async def _try_rule_based_translation(self, text: str, target_lang: str, source_lang: str) -> Optional[str]:
        """尝试基于规则的简单翻译"""
        try:
            if target_lang not in ["zh", "zh-cn"]:
                return None
            
            # 检测源语言类型
            detected_lang = self._detect_simple_language(text)
            
            if detected_lang == "de":  # 德语
                return self._simple_german_to_chinese(text)
            elif detected_lang == "en":  # 英语
                return self._simple_english_to_chinese(text)
            
            return None
            
        except Exception as e:
            logger.debug(f"规则翻译失败: {e}")
            return None
    
    def _detect_simple_language(self, text: str) -> str:
        """简单语言检测"""
        text_lower = text.lower()
        
        # 德语特征词
        german_words = ["der", "die", "das", "und", "mit", "von", "zu", "für", "auf", "bei", "wir", "sie", "ist"]
        german_count = sum(1 for word in german_words if word in text_lower)
        
        # 英语特征词
        english_words = ["the", "and", "with", "from", "to", "for", "on", "at", "we", "you", "is", "are"]
        english_count = sum(1 for word in english_words if word in text_lower)
        
        # 中文字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        
        if chinese_chars > len(text) * 0.3:
            return "zh"
        elif german_count > english_count:
            return "de"
        else:
            return "en"
    
    def _simple_german_to_chinese(self, text: str) -> str:
        """简单的德语到中文翻译"""
        # 基本的德语句式转换
        patterns = [
            (r'Willkommen bei (.+?) auf der (.+)', r'欢迎来到\1在\2'),
            (r'Willkommen in der (.+)', r'欢迎来到\1'),
            (r'(.+?) ist (.+)', r'\1是\2'),
            (r'Wir (.+)', r'我们\1'),
            (r'Sie (.+)', r'您\1'),
            (r'Unsere (.+?) ist (.+)', r'我们的\1是\2'),
            (r'Gemeinsam (.+)', r'共同\1'),
        ]
        
        result = text
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # 替换已知词汇
        for german, chinese in self.offline_dict.items():
            result = re.sub(r'\b' + re.escape(german) + r'\b', chinese, result, flags=re.IGNORECASE)
        
        return result
    
    def _simple_english_to_chinese(self, text: str) -> str:
        """简单的英语到中文翻译"""
        # 基本的英语句式转换
        patterns = [
            (r'Welcome to (.+)', r'欢迎来到\1'),
            (r'(.+?) is (.+)', r'\1是\2'),
            (r'We (.+)', r'我们\1'),
            (r'You (.+)', r'您\1'),
            (r'Our (.+?) is (.+)', r'我们的\1是\2'),
            (r'Together (.+)', r'共同\1'),
        ]
        
        result = text
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # 替换已知词汇
        for english, chinese in self.offline_dict.items():
            result = re.sub(r'\b' + re.escape(english) + r'\b', chinese, result, flags=re.IGNORECASE)
        
        return result
    
    def _improve_chinese_expression(self, text: str) -> str:
        """改善中文表达"""
        # 调整常见的中文表达
        improvements = [
            (r'的的', '的'),
            (r'在在', '在'),
            (r'我们我们', '我们'),
            (r'\s+', ''),  # 移除多余空格
            (r'([。！？])\s*([。！？])', r'\1'),  # 合并重复标点
        ]
        
        result = text
        for pattern, replacement in improvements:
            result = re.sub(pattern, replacement, result)
        
        return result.strip()
    
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
    
    def _map_language_code(self, lang_code: str, translator_type: str) -> str:
        """映射语言代码到不同翻译器的格式"""
        mappings = {
            "google": {
                "zh": "zh",
                "zh-cn": "zh-cn", 
                "en": "en",
                "de": "de",
                "ja": "ja",
                "ko": "ko",
                "fr": "fr",
                "es": "es",
                "ru": "ru"
            },
            "deep_google": {
                "zh": "zh",
                "zh-cn": "zh-CN",
                "en": "en", 
                "de": "de",
                "ja": "ja",
                "ko": "ko",
                "fr": "fr",
                "es": "es",
                "ru": "ru"
            }
        }
        
        mapping = mappings.get(translator_type, {})
        return mapping.get(lang_code, lang_code)
    
    def _is_translation_valid(self, original: str, translated: str, target_lang: str) -> bool:
        """验证翻译结果是否有效"""
        if not translated or translated.strip() == "":
            return False
        
        # 检查翻译是否与原文相同（可能翻译失败）
        if original.strip() == translated.strip():
            return False
        
        # 检查翻译长度是否合理
        if len(translated) < max(1, len(original) * 0.1):
            return False
        
        if len(translated) > len(original) * 10:
            return False
        
        return True
    
    def _postprocess_translation(self, translated_text: str, original_text: str) -> str:
        """后处理翻译结果"""
        if not translated_text:
            return original_text
        
        # 修复常见的翻译问题
        translated_text = self._fix_common_translation_issues(translated_text)
        
        return translated_text.strip()
    
    def _fix_common_translation_issues(self, text: str) -> str:
        """修复常见的翻译问题"""
        if not text:
            return text
        
        # 修复空格问题
        text = re.sub(r'\s+', ' ', text)
        
        # 修复中文标点符号
        text = text.replace(' , ', '，')
        text = text.replace(' . ', '。')
        text = text.replace(' ! ', '！')
        text = text.replace(' ? ', '？')
        
        # 移除中文字符间的不必要空格
        text = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', text)
        
        return text
    
    async def translate_subtitles_enhanced(self, subtitle_path: str, target_language: str = "zh", 
                                         source_language: str = "auto", 
                                         progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        增强字幕翻译，使用多种翻译策略
        
        Args:
            subtitle_path: 字幕文件路径
            target_language: 目标语言
            source_language: 源语言
            progress_callback: 进度回调函数
            
        Returns:
            Dict[str, Any]: 翻译结果
        """
        try:
            if not os.path.exists(subtitle_path):
                raise Exception("字幕文件不存在")
            
            # 辅助函数：智能调用progress_callback
            async def safe_progress_callback(progress, message=""):
                if progress_callback:
                    import inspect
                    
                    if inspect.iscoroutinefunction(progress_callback):
                        await progress_callback(progress, message)
                    else:
                        progress_callback(progress, message)
            
            await safe_progress_callback(5, "正在解析字幕文件...")
            
            # 解析字幕文件
            from .subtitle_file_handler import SubtitleFileHandler
            file_handler = SubtitleFileHandler()
            subtitles = file_handler.parse_srt_file(subtitle_path)
            
            if not subtitles:
                raise Exception("字幕文件解析失败或为空")
            
            total_subtitles = len(subtitles)
            translated_subtitles = []
            successful_translations = 0
            
            logger.info(f"开始增强翻译字幕: {total_subtitles} 条")
            
            # 翻译字幕
            for i, subtitle in enumerate(subtitles):
                try:
                    # 使用增强翻译
                    translated_text = await self.translate_text_enhanced(
                        subtitle['text'],
                        target_language,
                        source_language
                    )
                    
                    # 检查是否成功翻译（不是原文标记）
                    is_successful = not translated_text.startswith("[原文]") and translated_text != subtitle['text']
                    
                    translated_subtitles.append({
                        'index': subtitle['index'],
                        'start_time': subtitle['start_time'],
                        'end_time': subtitle['end_time'],
                        'text': translated_text,
                        'original_text': subtitle['text']
                    })
                    
                    if is_successful:
                        successful_translations += 1
                    
                    # 更新进度
                    progress = 5 + (i + 1) / total_subtitles * 85
                    await safe_progress_callback(
                        progress, 
                        f"翻译进度: {i+1}/{total_subtitles} (成功:{successful_translations})"
                    )
                    
                    # 添加小延迟
                    await asyncio.sleep(0.05)
                    
                except Exception as e:
                    logger.warning(f"翻译第{i+1}条字幕失败: {e}")
                    translated_subtitles.append({
                        'index': subtitle['index'],
                        'start_time': subtitle['start_time'],
                        'end_time': subtitle['end_time'],
                        'text': f"[翻译失败] {subtitle['text']}",
                        'original_text': subtitle['text'],
                        'error': str(e)
                    })
            
            await safe_progress_callback(95, "正在保存翻译结果...")
            
            # 生成翻译文件名
            from pathlib import Path
            subtitle_name = Path(subtitle_path).stem
            if subtitle_name.endswith("_subtitles"):
                subtitle_name = subtitle_name[:-10]
            
            safe_name = file_handler.sanitize_filename(subtitle_name, max_length=160, default_name="enhanced_translated_subtitle")
            translated_filename = f"{safe_name}_{target_language}_enhanced_subtitles.srt"
            translated_path = os.path.join(settings.FILES_PATH, translated_filename)
            
            # 保存翻译后的字幕
            file_handler.save_srt_file(translated_subtitles, translated_path)
            
            await safe_progress_callback(100, "增强翻译完成")
            
            success_rate = (successful_translations / total_subtitles * 100) if total_subtitles > 0 else 0
            
            return {
                "success": True,
                "translated_file": translated_path,
                "source_language": source_language,
                "target_language": target_language,
                "subtitles_count": len(translated_subtitles),
                "successful_translations": successful_translations,
                "success_rate": f"{success_rate:.1f}%",
                "translation_method": "enhanced_multi_strategy",
                "message": f"增强翻译完成，成功率: {success_rate:.1f}%"
            }
            
        except Exception as e:
            logger.error(f"增强字幕翻译失败: {e}")
            return {
                "success": False,
                "error": str(e)
            } 