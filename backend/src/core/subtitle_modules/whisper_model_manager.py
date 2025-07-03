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
        # 设置默认中等性能模型（速度质量平衡）
        self.default_model_size = "medium"  # 从large-v3改为medium以提升速度
        logger.info("Whisper模型管理器初始化完成（默认medium模型：速度质量平衡）")
    
    def get_available_models(self) -> list:
        """获取可用的模型列表（按推荐度排序）"""
        return [
            "large-v3",  # 推荐：最高品质模型（默认）
            "large-v2",  # 高品质：较新的大模型
            "large",     # 高品质：标准大模型
            "medium",    # 平衡：中等性能和品质
            "small",     # 快速：较好的性能
            "base",      # 基础：轻量级选择
            "tiny"       # 最快：最小模型
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
                "quality_mode": "平衡性能模式（默认medium）"
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
            
            # 为CPU模式设置性能优化
            if device == "cpu":
                self._setup_cpu_optimization()
            
            # 根据设备类型智能选择计算类型
            compute_type = self._get_optimal_compute_type(device)
            
            logger.info(f"加载Whisper模型: {model_size}（性能优化模式）, 设备: {device}, 计算类型: {compute_type}")
            
            model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                local_files_only=False,
                download_root=settings.MODELS_PATH,
                num_workers=self._get_optimal_num_workers(device),
                cpu_threads=self._get_optimal_cpu_threads()
            )
            
            # 缓存模型
            self.model_cache[model_size] = model
            self.current_model = model
            self.current_model_size = model_size
            
            logger.info(f"Whisper模型加载成功: {model_size}（性能优化）")
            
            return model
            
        except Exception as e:
            logger.error(f"加载Whisper模型失败: {e}")
            raise
    
    def _get_optimal_compute_type(self, device: str) -> str:
        """获取最优的计算类型（解除内存限制，优先性能）"""
        # 解除内存限制，优先使用更高精度的计算类型
        if device == "cpu":
            # CPU模式下，使用float32获得最佳精度（解除内存限制）
            compute_type = "float32"
            logger.info("CPU模式：使用float32以获得最佳精度（已解除内存限制）")
        elif device == "cuda":
            # GPU模式下，优先使用float16以提高性能
            if torch.cuda.is_available():
                try:
                    # 检查GPU是否支持半精度
                    props = torch.cuda.get_device_properties(0)
                    if props.major >= 7:  # Volta架构及以上支持Tensor Cores
                        compute_type = "float16"
                        logger.info("GPU模式：使用float16（Tensor Cores）以获得最佳性能")
                    else:
                        compute_type = "float32"
                        logger.info("GPU模式：使用float32以获得最佳精度")
                except Exception:
                    compute_type = "float32"
            else:
                compute_type = "float32"
        else:
            # 默认使用float32获得最佳精度
            compute_type = "float32"
            logger.info("默认模式：使用float32以获得最佳精度（已解除内存限制）")
        
        return compute_type

    def _get_optimal_num_workers(self, device: str) -> int:
        """获取最优的工作进程数（解除进程数限制）"""
        if device == "cpu":
            # CPU模式下，充分利用所有CPU核心（解除进程数限制）
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            
            # 解除进程数限制，使用更多工作进程提升性能
            if cpu_count >= 16:
                num_workers = min(cpu_count * 3 // 4, 16)  # 使用3/4核心数，最多16个
            elif cpu_count >= 8:
                num_workers = min(cpu_count, 12)  # 使用所有核心，最多12个
            elif cpu_count >= 4:
                num_workers = cpu_count  # 使用所有核心
            else:
                num_workers = max(cpu_count, 2)  # 至少2个进程
            
            logger.info(f"CPU模式：使用 {num_workers} 个工作进程（总CPU核心数: {cpu_count}，已解除进程数限制）")
            return num_workers
        else:
            # GPU模式下使用适度的工作进程
            return 2
    
    def _get_optimal_cpu_threads(self) -> int:
        """获取最优的CPU线程数（高性能模式）"""
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        
        # 高性能模式：充分利用所有CPU资源
        if cpu_count >= 16:
            # 高性能CPU：使用所有核心
            cpu_threads = cpu_count
        elif cpu_count >= 8:
            # 中高性能CPU：使用所有核心
            cpu_threads = cpu_count
        elif cpu_count >= 4:
            # 中等性能CPU：使用所有核心
            cpu_threads = cpu_count
        else:
            # 低性能CPU：使用所有可用核心
            cpu_threads = cpu_count
        
        logger.info(f"高性能模式CPU线程配置：{cpu_threads} 个线程（总CPU核心数: {cpu_count}）")
        return cpu_threads

    def _setup_cpu_optimization(self):
        """设置CPU性能优化环境变量（高性能模式）"""
        import os
        import multiprocessing
        
        cpu_count = multiprocessing.cpu_count()
        
        # 高性能模式：设置OpenMP线程数（用于数学库优化）
        os.environ['OMP_NUM_THREADS'] = str(cpu_count)
        
        # 设置MKL线程数（Intel数学库优化）
        os.environ['MKL_NUM_THREADS'] = str(cpu_count)
        
        # 设置BLAS线程数（基础线性代数库优化）
        os.environ['OPENBLAS_NUM_THREADS'] = str(cpu_count)
        
        # 高性能模式：优化内存分配策略
        os.environ['MALLOC_ARENA_MAX'] = '4'  # 限制内存分配区域数量
        
        # 设置PyTorch线程数（高性能模式）
        import torch
        torch.set_num_threads(cpu_count)
        
        # 设置线程间并行处理（充分利用多核）
        torch.set_num_interop_threads(cpu_count)
        
        # 启用PyTorch性能优化（如果可用）
        if hasattr(torch.backends.mkldnn, 'enabled'):
            torch.backends.mkldnn.enabled = True
        
        logger.info(f"高性能CPU优化已启用：使用 {cpu_count} 个线程进行并行计算（已解除内存限制）")
    
    def get_model_specific_options(self, model_size: str, language: str) -> dict:
        """
        根据模型大小获取特定的转录选项（高速优化配置）
        
        Args:
            model_size: 模型大小
            language: 语言代码
            
        Returns:
            dict: 转录选项
        """
        # 如果未指定模型，使用默认平衡性能模型
        if not model_size:
            model_size = self.default_model_size
        
        # 高速优化基础配置
        base_options = {
            "language": None if language == "auto" else language,
            "beam_size": 1,  # 高速优化：使用最小束搜索（greedy decode）
            "best_of": 1,    # 高速优化：只生成一个候选
            "patience": 0.5,  # 高速优化：最小耐心值
            "vad_filter": True,  # 启用VAD过滤减少处理量
            "vad_parameters": dict(
                threshold=0.5,  # 稍高阈值快速过滤
                min_silence_duration_ms=600  # 减少静音时长，快速切分
            ),
            "temperature": [0.0],  # 高速优化：只使用确定性解码
            "compression_ratio_threshold": 2.4,  # 压缩比阈值
            "no_speech_threshold": 0.6,  # 无语音阈值
            "condition_on_previous_text": False,  # 高速优化：不依赖前文上下文
            "initial_prompt": None,  # 无初始提示
            "without_timestamps": False,  # 保留时间戳
            "max_initial_timestamp": 1.0,  # 最大初始时间戳
            "word_timestamps": False,  # 高速优化：禁用单词级时间戳
            "hallucination_silence_threshold": 2.0  # 减少幻觉检测时间
        }
        
        # 根据模型大小调整参数（所有模型都使用高速优化配置）
        if "large" in model_size:
            # large模型：平衡速度和质量
            base_options.update({
                "beam_size": 2,  # 适度束搜索平衡速度质量
                "best_of": 2,    # 适度候选数
                "patience": 0.8,  # 适度耐心值
                "temperature": [0.0, 0.2]  # 最多两个温度选项
            })
            
        elif "medium" in model_size:
            # medium模型：快速参数
            base_options.update({
                "beam_size": 1,
                "best_of": 1,
                "patience": 0.5
            })
            
        elif "small" in model_size:
            # small模型：极速参数
            base_options.update({
                "beam_size": 1,
                "best_of": 1,
                "patience": 0.3
            })
            
        elif "base" in model_size:
            # base模型：超快参数
            base_options.update({
                "beam_size": 1,
                "best_of": 1,
                "patience": 0.2
            })
            
        elif "tiny" in model_size:
            # tiny模型：极速参数
            base_options.update({
                "beam_size": 1,
                "best_of": 1,
                "patience": 0.1,
                "vad_parameters": dict(
                    threshold=0.6,
                    min_silence_duration_ms=500
                )
            })
        
        # 对于.en模型，强制使用英语
        if ".en" in model_size:
            base_options["language"] = "en"
        
        logger.info(f"为模型 {model_size} 配置高速优化参数: beam_size={base_options['beam_size']}, 快速模式已启用")
        
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