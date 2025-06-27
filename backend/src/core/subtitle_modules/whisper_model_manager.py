"""
Whisper模型管理器

负责Whisper模型的加载、缓存、参数配置和优化
默认使用faster-whisper最高品质模型(large-v3)
"""

import os
import torch
from typing import Dict, Any, Optional
from faster_whisper import WhisperModel

from ...utils.logger import get_logger
logger = get_logger(__name__)
from ..config import settings


class WhisperModelManager:
    """Whisper模型管理器（默认最高品质）"""
    
    def __init__(self):
        """初始化模型管理器"""
        self.model_cache = {}
        self.current_model = None
        self.current_model_size = None
        # 设置默认最高品质模型
        self.default_model_size = "large-v3"
        logger.info("Whisper模型管理器初始化完成（默认最高品质large-v3）")
    
    def get_available_models(self) -> list:
        """获取可用的模型列表（按品质排序）"""
        return [
            "large-v3",  # 最高品质（默认）
            "large-v2", 
            "large", 
            "medium", 
            "small", 
            "base",
            "tiny"
        ]
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        try:
            device = self._get_current_device()
            
            # 获取当前缓存的模型信息
            cached_models = list(self.model_cache.keys())
            current_model = self.current_model_size or self.default_model_size
            
            # 计算当前缓存大小（估算）
            cache_size_mb = len(self.model_cache) * 50  # 每个模型大约50MB缓存
            
            model_info = {
                "device": device,
                "auto_device_selection": settings.AI_AUTO_DEVICE_SELECTION,
                "current_model": current_model,
                "default_model": self.default_model_size,
                "cached_models": cached_models,
                "current_cache_size": cache_size_mb,
                "whisper_device": device,
                "compute_type": settings.WHISPER_COMPUTE_TYPE,
                "model_path": settings.MODELS_PATH,
                "available_models": self.get_available_models(),
                "quality_mode": "最高品质模式（默认large-v3）"
            }
            
            # 添加CUDA详细信息
            if device == "cuda":
                try:
                    model_info.update({
                        "cuda_device_count": torch.cuda.device_count(),
                        "cuda_current_device": torch.cuda.current_device(),
                        "cuda_memory_allocated": torch.cuda.memory_allocated() / (1024**3),  # GB
                        "cuda_memory_cached": torch.cuda.memory_reserved() / (1024**3),  # GB
                    })
                    
                    if torch.cuda.device_count() > 0:
                        props = torch.cuda.get_device_properties(0)
                        model_info.update({
                            "gpu_name": props.name,
                            "gpu_memory_total": props.total_memory / (1024**3),  # GB
                        })
                except Exception as e:
                    logger.warning(f"获取CUDA信息失败: {e}")
            
            return model_info
            
        except Exception as e:
            logger.error(f"获取模型信息失败: {e}")
            return {
                "device": "cpu",
                "auto_device_selection": True,
                "current_model": self.default_model_size,
                "default_model": self.default_model_size,
                "cached_models": [],
                "current_cache_size": 0,
                "error": str(e)
            }
    
    def _get_current_device(self) -> str:
        """获取当前设备"""
        try:
            if settings.AI_AUTO_DEVICE_SELECTION:
                return "cuda" if torch.cuda.is_available() else "cpu"
            else:
                return settings.WHISPER_DEVICE
        except Exception:
            return "cpu"
    
    def load_model(self, model_size: str = None) -> WhisperModel:
        """
        加载Whisper模型（默认最高品质）
        
        Args:
            model_size: 模型大小/名称（默认使用large-v3）
            
        Returns:
            WhisperModel: 加载的模型实例
        """
        # 如果未指定模型大小，使用默认最高品质模型
        if model_size is None:
            model_size = self.default_model_size
        
        # 检查缓存
        if model_size in self.model_cache:
            logger.info(f"使用缓存的Whisper模型: {model_size}")
            self.current_model = self.model_cache[model_size]
            self.current_model_size = model_size
            return self.current_model
        
        try:
            device = self._get_current_device()
            
            # 根据设备类型智能选择计算类型
            compute_type = self._get_optimal_compute_type(device)
            
            logger.info(f"加载Whisper模型: {model_size}（最高品质模式）, 设备: {device}, 计算类型: {compute_type}")
            
            model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                local_files_only=False,
                download_root=settings.MODELS_PATH
            )
            
            # 缓存模型
            self.model_cache[model_size] = model
            self.current_model = model
            self.current_model_size = model_size
            
            logger.info(f"Whisper模型加载成功: {model_size}（最高品质）")
            
            return model
            
        except Exception as e:
            logger.error(f"加载Whisper模型失败: {e}")
            raise
    
    def _get_optimal_compute_type(self, device: str) -> str:
        """获取最优的计算类型（针对最高品质优化）"""
        compute_type = settings.WHISPER_COMPUTE_TYPE
        
        if device == "cpu":
            # CPU模式下，使用float32确保最佳质量
            compute_type = "float32"
            logger.info("CPU模式：使用float32以确保最高品质")
        elif device == "cuda":
            # GPU模式下，优先使用float16以提高性能，但保持质量
            if torch.cuda.is_available():
                try:
                    # 检查GPU是否支持半精度
                    props = torch.cuda.get_device_properties(0)
                    if props.major >= 7:  # Volta架构及以上支持Tensor Cores
                        compute_type = "float16"
                        logger.info("GPU模式：使用float16（Tensor Cores）以获得最佳性能和质量平衡")
                    else:
                        compute_type = "float32"
                        logger.info("GPU模式：使用float32以确保最高品质")
                except Exception:
                    compute_type = "float32"
        
        return compute_type
    
    def get_model_specific_options(self, model_size: str, language: str) -> dict:
        """
        根据模型大小获取特定的转录选项（最高品质配置）
        
        Args:
            model_size: 模型大小
            language: 语言代码
            
        Returns:
            dict: 转录选项
        """
        # 如果未指定模型，使用默认最高品质模型
        if not model_size:
            model_size = self.default_model_size
        
        # 基础高品质配置
        base_options = {
            "language": None if language == "auto" else language,
            "beam_size": 8,  # 增加束搜索以提高质量
            "best_of": 8,    # 增加候选数以提高质量
            "patience": 2.0,  # 增加耐心值以获得更好结果
            "vad_filter": True,  # 启用VAD过滤噪音
            "vad_parameters": dict(
                threshold=0.3,  # 较低阈值以保留更多音频
                min_silence_duration_ms=500  # 较短静音时长以保留细节
            ),
            "temperature": [0.0, 0.2, 0.4],  # 使用温度采样提高质量
            "compression_ratio_threshold": 2.4,  # 压缩比阈值
            "no_speech_threshold": 0.6,  # 无语音阈值
            "condition_on_previous_text": True,  # 基于前文上下文
            "initial_prompt": None,  # 可以设置初始提示
            "without_timestamps": False,  # 保留时间戳
            "max_initial_timestamp": 1.0  # 最大初始时间戳
        }
        
        # 根据模型大小调整参数（所有模型都使用高品质配置）
        if "large" in model_size:
            # large模型使用最高质量参数
            base_options.update({
                "beam_size": 10,  # 最大束搜索
                "best_of": 10,    # 最大候选数
                "patience": 2.5,  # 最大耐心值
                "vad_filter": False,  # 大模型可以处理噪音
                "temperature": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]  # 更多温度选项
            })
            
        elif "medium" in model_size:
            # medium模型高品质参数
            base_options.update({
                "beam_size": 8,
                "best_of": 8,
                "patience": 2.0
            })
            
        elif "small" in model_size:
            # small模型优化参数
            base_options.update({
                "beam_size": 6,
                "best_of": 6,
                "patience": 1.5
            })
            
        elif "base" in model_size:
            # base模型平衡参数
            base_options.update({
                "beam_size": 5,
                "best_of": 5,
                "patience": 1.2
            })
            
        elif "tiny" in model_size:
            # tiny模型保守参数
            base_options.update({
                "beam_size": 3,
                "best_of": 3,
                "patience": 1.0,
                "vad_filter": True,  # tiny模型需要VAD过滤
                "vad_parameters": dict(
                    threshold=0.4,
                    min_silence_duration_ms=800
                )
            })
        
        # 对于.en模型，强制使用英语
        if ".en" in model_size:
            base_options["language"] = "en"
        
        logger.info(f"为模型 {model_size} 配置最高品质参数: beam_size={base_options['beam_size']}")
        
        return base_options
    
    def get_retry_options(self, model_size: str, language: str) -> dict:
        """
        获取重试时使用的备用选项（保持高品质）
        
        Args:
            model_size: 模型大小
            language: 语言代码
            
        Returns:
            dict: 重试选项
        """
        if not model_size:
            model_size = self.default_model_size
        
        retry_options = {
            "language": None if language == "auto" else language,
            "beam_size": 5,  # 重试时适度降低束搜索
            "best_of": 5,
            "patience": 3.0,  # 增加耐心值
            "vad_filter": False,  # 禁用VAD过滤
            "temperature": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],  # 使用完整温度范围
            "compression_ratio_threshold": 2.4,
            "no_speech_threshold": 0.6,
            "condition_on_previous_text": False,  # 重试时不依赖前文
            "initial_prompt": None
        }
        
        # 对于.en模型，强制使用英语
        if ".en" in model_size:
            retry_options["language"] = "en"
        
        return retry_options
    
    def clear_cache(self) -> bool:
        """清除模型缓存"""
        try:
            # 清理GPU内存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # 清除模型缓存
            self.model_cache.clear()
            self.current_model = None
            self.current_model_size = None
            
            logger.info("模型缓存已清除")
            return True
            
        except Exception as e:
            logger.error(f"清除模型缓存失败: {e}")
            return False
    
    def unload_model(self, model_size: str = None) -> bool:
        """
        卸载指定模型
        
        Args:
            model_size: 要卸载的模型大小，为None时卸载当前模型
            
        Returns:
            bool: 是否成功卸载
        """
        try:
            if model_size is None:
                model_size = self.current_model_size
            
            if model_size and model_size in self.model_cache:
                del self.model_cache[model_size]
                
                if model_size == self.current_model_size:
                    self.current_model = None
                    self.current_model_size = None
                
                logger.info(f"模型已卸载: {model_size}")
                
                # 清理GPU内存
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"卸载模型失败: {e}")
            return False
    
    def get_cache_status(self) -> dict:
        """获取缓存状态"""
        return {
            "cached_models": list(self.model_cache.keys()),
            "current_model": self.current_model_size,
            "cache_count": len(self.model_cache),
            "estimated_memory_mb": len(self.model_cache) * 50
        } 