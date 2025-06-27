"""
字幕特效模块

负责字幕烧录、样式设置、特效处理等高级功能
"""

import os
import subprocess
from typing import Dict, Any, Optional, Callable
from pathlib import Path

from ...utils.logger import get_logger
logger = get_logger(__name__)
from ..config import settings


class SubtitleEffects:
    """字幕特效处理器"""
    
    def __init__(self):
        """初始化字幕特效处理器"""
        logger.info("字幕特效处理器初始化完成")
    
    def get_default_subtitle_style(self) -> Dict[str, Any]:
        """
        获取默认字幕样式
        
        Returns:
            Dict[str, Any]: 默认样式配置
        """
        return {
            "font_size": 24,
            "font_color": "white",
            "font_name": "Arial",
            "outline_color": "black", 
            "outline_width": 2,
            "shadow_offset": 1,
            "margin_vertical": 50,
            "alignment": "bottom_center",
            "background_color": "transparent",
            "background_opacity": 0.0
        }
    
    def get_style_presets(self) -> Dict[str, Dict[str, Any]]:
        """
        获取样式预设
        
        Returns:
            Dict[str, Dict[str, Any]]: 样式预设字典
        """
        return {
            "default": {
                "name": "默认样式",
                "font_size": 24,
                "font_color": "white",
                "outline_color": "black",
                "outline_width": 2,
                "margin_vertical": 50
            },
            "large": {
                "name": "大字体",
                "font_size": 32,
                "font_color": "white", 
                "outline_color": "black",
                "outline_width": 3,
                "margin_vertical": 60
            },
            "cinema": {
                "name": "影院风格",
                "font_size": 28,
                "font_color": "white",
                "outline_color": "black",
                "outline_width": 2,
                "background_color": "black",
                "background_opacity": 0.7,
                "margin_vertical": 40
            },
            "colorful": {
                "name": "彩色样式",
                "font_size": 26,
                "font_color": "yellow",
                "outline_color": "red",
                "outline_width": 2,
                "margin_vertical": 45
            },
            "minimal": {
                "name": "简约风格",
                "font_size": 22,
                "font_color": "white",
                "outline_color": "transparent",
                "outline_width": 0,
                "background_color": "black",
                "background_opacity": 0.5,
                "margin_vertical": 30
            }
        }
    
    async def burn_subtitles_to_video(self,
                                    video_path: str,
                                    subtitle_path: str,
                                    output_path: str = None,
                                    subtitle_style: Dict[str, Any] = None,
                                    progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        烧录字幕到视频
        
        Args:
            video_path: 视频文件路径
            subtitle_path: 字幕文件路径
            output_path: 输出文件路径
            subtitle_style: 字幕样式配置
            progress_callback: 进度回调函数
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            if not os.path.exists(video_path):
                raise Exception("视频文件不存在")
            
            if not os.path.exists(subtitle_path):
                raise Exception("字幕文件不存在")
            
            if progress_callback:
                await progress_callback(5, "正在准备字幕烧录...")
            
            # 生成输出文件名
            if not output_path:
                video_name = Path(video_path).stem
                output_path = os.path.join(settings.FILES_PATH, f"{video_name}_with_subtitles.mp4")
            
            # 获取字幕样式
            if not subtitle_style:
                subtitle_style = self.get_default_subtitle_style()
            
            if progress_callback:
                await progress_callback(20, "正在处理字幕样式...")
            
            # 构建ffmpeg命令
            cmd = self._build_burn_command(video_path, subtitle_path, output_path, subtitle_style)
            
            if progress_callback:
                await progress_callback(30, "开始烧录字幕...")
            
            # 执行ffmpeg命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30分钟超时
            )
            
            if result.returncode != 0:
                raise Exception(f"字幕烧录失败: {result.stderr}")
            
            if progress_callback:
                await progress_callback(100, "字幕烧录完成")
            
            return {
                "success": True,
                "output_file": output_path,
                "message": "字幕烧录成功"
            }
            
        except Exception as e:
            logger.error(f"字幕烧录失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_burn_command(self, video_path: str, subtitle_path: str, output_path: str, style: Dict[str, Any]) -> list:
        """
        构建字幕烧录命令
        
        Args:
            video_path: 视频文件路径
            subtitle_path: 字幕文件路径
            output_path: 输出文件路径
            style: 字幕样式
            
        Returns:
            list: ffmpeg命令列表
        """
        # 基础命令
        cmd = ["ffmpeg", "-i", video_path]
        
        # 构建字幕滤镜
        font_size = style.get('font_size', 24)
        font_color = style.get('font_color', 'white')
        outline_color = style.get('outline_color', 'black')
        outline_width = style.get('outline_width', 2)
        font_name = style.get('font_name', 'Arial')
        
        # 字幕滤镜参数
        subtitle_filter = f"subtitles={subtitle_path}"
        
        # 添加样式参数
        style_params = []
        
        if font_size:
            style_params.append(f"FontSize={font_size}")
        
        if font_color and font_color != 'white':
            # 转换颜色名称为hex
            color_hex = self._color_to_hex(font_color)
            style_params.append(f"PrimaryColour=&H{color_hex}&")
        
        if outline_color and outline_color != 'transparent':
            outline_hex = self._color_to_hex(outline_color)
            style_params.append(f"OutlineColour=&H{outline_hex}&")
        
        if outline_width:
            style_params.append(f"Outline={outline_width}")
        
        if font_name and font_name != 'Arial':
            style_params.append(f"FontName={font_name}")
        
        # 组合样式参数
        if style_params:
            force_style = ','.join(style_params)
            subtitle_filter += f":force_style='{force_style}'"
        
        # 添加视频滤镜
        cmd.extend(["-vf", subtitle_filter])
        
        # 保持音频不变
        cmd.extend(["-c:a", "copy"])
        
        # 视频编码参数
        cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "23"])
        
        # 覆盖输出文件
        cmd.extend(["-y", output_path])
        
        return cmd
    
    def _color_to_hex(self, color: str) -> str:
        """
        将颜色名称转换为hex格式
        
        Args:
            color: 颜色名称
            
        Returns:
            str: hex颜色值
        """
        color_map = {
            'white': 'FFFFFF',
            'black': '000000',
            'red': 'FF0000',
            'green': '00FF00',
            'blue': '0000FF',
            'yellow': 'FFFF00',
            'cyan': '00FFFF',
            'magenta': 'FF00FF',
            'orange': 'FFA500',
            'purple': '800080',
            'pink': 'FFC0CB',
            'gray': '808080',
            'grey': '808080'
        }
        
        return color_map.get(color.lower(), 'FFFFFF')
    
    async def add_subtitle_effects(self,
                                 video_path: str,
                                 subtitle_path: str,
                                 effect_type: str = "fade",
                                 output_path: str = None,
                                 progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        添加字幕特效
        
        Args:
            video_path: 视频文件路径
            subtitle_path: 字幕文件路径
            effect_type: 特效类型 (fade, slide, bounce等)
            output_path: 输出文件路径
            progress_callback: 进度回调函数
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            if progress_callback:
                await progress_callback(10, f"正在应用{effect_type}特效...")
            
            # 生成输出文件名
            if not output_path:
                video_name = Path(video_path).stem
                output_path = os.path.join(settings.FILES_PATH, f"{video_name}_{effect_type}_effect.mp4")
            
            # 根据特效类型构建不同的命令
            if effect_type == "fade":
                cmd = self._build_fade_effect_command(video_path, subtitle_path, output_path)
            elif effect_type == "slide":
                cmd = self._build_slide_effect_command(video_path, subtitle_path, output_path)
            else:
                # 默认无特效
                cmd = self._build_burn_command(video_path, subtitle_path, output_path, self.get_default_subtitle_style())
            
            if progress_callback:
                await progress_callback(30, "正在处理特效...")
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            if result.returncode != 0:
                raise Exception(f"特效处理失败: {result.stderr}")
            
            if progress_callback:
                await progress_callback(100, "特效处理完成")
            
            return {
                "success": True,
                "output_file": output_path,
                "effect_type": effect_type,
                "message": f"{effect_type}特效应用成功"
            }
            
        except Exception as e:
            logger.error(f"字幕特效处理失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_fade_effect_command(self, video_path: str, subtitle_path: str, output_path: str) -> list:
        """构建淡入淡出特效命令"""
        return [
            "ffmpeg", "-i", video_path,
            "-vf", f"subtitles={subtitle_path}:force_style='Fade=300'",
            "-c:a", "copy", "-c:v", "libx264",
            "-y", output_path
        ]
    
    def _build_slide_effect_command(self, video_path: str, subtitle_path: str, output_path: str) -> list:
        """构建滑动特效命令"""
        return [
            "ffmpeg", "-i", video_path,
            "-vf", f"subtitles={subtitle_path}:force_style='ScrollUp=1'",
            "-c:a", "copy", "-c:v", "libx264",
            "-y", output_path
        ]
    
    def get_quality_options(self) -> Dict[str, str]:
        """
        获取视频质量选项说明
        
        Returns:
            Dict[str, str]: 质量选项字典
        """
        return {
            "low": "低质量 (快速编码，文件较小)",
            "medium": "中等质量 (平衡速度和质量)", 
            "high": "高质量 (慢速编码，文件较大)",
            "original": "原始质量 (保持原始编码参数，但仍需重编码以烧录字幕)"
        }
    
    def get_supported_effects(self) -> Dict[str, str]:
        """
        获取支持的特效列表
        
        Returns:
            Dict[str, str]: 特效类型和描述
        """
        return {
            "none": "无特效",
            "fade": "淡入淡出",
            "slide": "滑动显示",
            "bounce": "弹跳效果",
            "typewriter": "打字机效果"
        }
    
    async def create_subtitle_preview(self,
                                    subtitle_path: str,
                                    video_path: str = None,
                                    style: Dict[str, Any] = None,
                                    duration: int = 10) -> Dict[str, Any]:
        """
        创建字幕预览
        
        Args:
            subtitle_path: 字幕文件路径
            video_path: 视频文件路径（可选）
            style: 字幕样式
            duration: 预览时长（秒）
            
        Returns:
            Dict[str, Any]: 预览结果
        """
        try:
            if not style:
                style = self.get_default_subtitle_style()
            
            # 生成预览文件名
            preview_filename = f"subtitle_preview_{int(time.time())}.mp4"
            preview_path = os.path.join(settings.TEMP_PATH, preview_filename)
            
            if video_path and os.path.exists(video_path):
                # 使用真实视频创建预览
                cmd = [
                    "ffmpeg", "-i", video_path,
                    "-t", str(duration),
                    "-vf", f"subtitles={subtitle_path}",
                    "-c:v", "libx264", "-preset", "fast",
                    "-y", preview_path
                ]
            else:
                # 创建纯色背景的预览
                cmd = [
                    "ffmpeg", "-f", "lavfi",
                    "-i", f"color=c=black:s=1280x720:d={duration}",
                    "-vf", f"subtitles={subtitle_path}",
                    "-c:v", "libx264", "-preset", "fast",
                    "-y", preview_path
                ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                raise Exception(f"预览创建失败: {result.stderr}")
            
            return {
                "success": True,
                "preview_file": preview_path,
                "duration": duration,
                "message": "预览创建成功"
            }
            
        except Exception as e:
            logger.error(f"创建字幕预览失败: {e}")
            return {
                "success": False,
                "error": str(e)
            } 