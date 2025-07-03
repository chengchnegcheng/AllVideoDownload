"""
统一的文件名处理工具
"""

import os
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any
import urllib.parse
import logging

logger = logging.getLogger(__name__)

def get_original_filename_from_mapping(file_path: str, fallback_name: str = "download") -> str:
    """从映射文件获取原始文件名"""
    try:
        file_path_obj = Path(file_path)
        uuid_part = file_path_obj.stem
        
        # 处理带后缀的UUID文件名
        if '_' in uuid_part:
            potential_uuid = uuid_part.split('_')[0]
            if len(potential_uuid) == 36 and potential_uuid.count('-') == 4:
                uuid_part = potential_uuid
        
        # 查找映射文件
        mapping_file = file_path_obj.parent / f"{uuid_part}_mapping.json"
        
        if mapping_file.exists():
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping_data = json.load(f)
            
            # 优先使用original_filename
            original_filename = mapping_data.get('original_filename')
            if original_filename:
                base_name = Path(original_filename).stem
                logger.info(f"从映射文件恢复文件名: {original_filename} -> {base_name}")
                return base_name
            
            # 尝试使用original_title
            original_title = mapping_data.get('original_title')
            if original_title:
                clean_title = original_title.strip()
                logger.info(f"从映射文件恢复标题: {original_title} -> {clean_title}")
                return clean_title
        
        logger.warning(f"映射文件不存在: {mapping_file}")
        return fallback_name
        
    except Exception as e:
        logger.error(f"获取原始文件名失败: {e}")
        return fallback_name

def build_download_filename(original_filename: str, suffix: str = "", extension: str = ".srt") -> str:
    """构建下载文件名"""
    try:
        clean_name = sanitize_filename_for_download(original_filename)
        
        if suffix:
            filename = f"{clean_name}{suffix}{extension}"
        else:
            filename = f"{clean_name}{extension}"
        
        logger.info(f"构建下载文件名: {original_filename} + {suffix} -> {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"构建下载文件名失败: {e}")
        return f"download{suffix}{extension}"

def sanitize_filename_for_download(filename: str) -> str:
    """为下载清理文件名"""
    if not filename:
        return "download"
    
    # 移除文件系统不支持的字符
    clean_name = re.sub(r'[<>:"/\\|?*]', '', filename)
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    clean_name = clean_name.strip('. ')
    
    if not clean_name:
        return "download"
    
    # 限制长度
    if len(clean_name.encode('utf-8')) > 200:
        result = ""
        for char in clean_name:
            test = result + char
            if len(test.encode('utf-8')) > 200:
                break
            result = test
        clean_name = result.strip() or "download"
    
    return clean_name

def get_subtitle_download_info(subtitle_file_path: str, operation_type: str = "") -> Dict[str, Any]:
    """获取字幕下载信息"""
    try:
        original_name = get_original_filename_from_mapping(subtitle_file_path, "subtitle")
        filename = Path(subtitle_file_path).name
        
        if operation_type == "translate" or "_zh_subtitles" in filename or "_zh_en_subtitles" in filename:
            suffix = "_中文字幕"
        elif operation_type == "generate" or "_subtitles" in filename:
            suffix = "_字幕"
        else:
            suffix = "_字幕"
        
        download_filename = build_download_filename(original_name, suffix, ".srt")
        record_id = Path(subtitle_file_path).stem.split('_')[0]
        
        return {
            "download_filename": download_filename,
            "record_id": record_id,
            "original_filename": original_name,
            "operation_type": operation_type
        }
        
    except Exception as e:
        logger.error(f"获取字幕下载信息失败: {e}")
        return {
            "download_filename": "subtitle.srt",
            "record_id": "",
            "original_filename": "subtitle",
            "operation_type": operation_type
        }
