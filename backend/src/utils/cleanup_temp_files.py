#!/usr/bin/env python3
"""
临时文件清理工具
用于清理遗留的临时字幕文件和其他临时文件
"""

import os
import sys
import time
import re
import glob
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class TempFileCleanup:
    """临时文件清理类"""
    
    def __init__(self):
        self.files_path = settings.FILES_PATH      # 统一的文件路径
        self.download_path = settings.FILES_PATH   # 保持向后兼容
        self.upload_path = settings.FILES_PATH     # 保持向后兼容
        self.temp_path = settings.TEMP_PATH        # 临时文件路径
        
        # 临时文件模式
        self.temp_patterns = [
            "*.tmp",
            "*_subtitles.srt",
            "*_subtitles.vtt", 
            "*_subtitles.ass",
            "*_with_subtitles.mp4",
            "*_translated.srt",
            "tmp*",
            "subtitle_*"
        ]
        
        # UUID格式的模式（用于识别自动生成的临时文件）
        self.uuid_pattern = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}')
    
    def is_uuid_filename(self, filename: str) -> bool:
        """检查文件名是否以UUID开头"""
        return bool(self.uuid_pattern.match(filename))
    
    def is_temp_file(self, filepath: str) -> bool:
        """判断是否是临时文件"""
        filename = os.path.basename(filepath)
        
        # 检查是否匹配临时文件模式
        for pattern in self.temp_patterns:
            if any(filename.endswith(ext) for ext in pattern.replace("*", "").split()):
                return True
        
        # 检查是否是UUID命名的文件
        if self.is_uuid_filename(filename):
            return True
            
        # 检查是否在临时目录
        if filepath.startswith(self.temp_path):
            return True
            
        return False
    
    def get_file_age(self, filepath: str) -> float:
        """获取文件年龄（小时）"""
        try:
            file_mtime = os.path.getmtime(filepath)
            current_time = time.time()
            age_seconds = current_time - file_mtime
            return age_seconds / 3600  # 转换为小时
        except OSError:
            return 0
    
    def scan_temp_files(self, max_age_hours: float = 1.0) -> List[Dict[str, Any]]:
        """扫描临时文件"""
        temp_files = []
        
        # 扫描的目录列表
        scan_dirs = [self.files_path]  # 只扫描统一的文件目录
        
        for scan_dir in scan_dirs:
            if not os.path.exists(scan_dir):
                continue
                
            logger.info(f"扫描目录: {scan_dir}")
            
            try:
                for root, dirs, files in os.walk(scan_dir):
                    for filename in files:
                        filepath = os.path.join(root, filename)
                        
                        # 检查是否是临时文件
                        if self.is_temp_file(filepath):
                            file_age = self.get_file_age(filepath)
                            file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                            
                            temp_file_info = {
                                "path": filepath,
                                "filename": filename,
                                "age_hours": file_age,
                                "size_bytes": file_size,
                                "directory": root,
                                "should_delete": file_age > max_age_hours
                            }
                            
                            temp_files.append(temp_file_info)
                            
            except PermissionError as e:
                logger.warning(f"权限不足，无法扫描目录 {scan_dir}: {e}")
            except Exception as e:
                logger.error(f"扫描目录 {scan_dir} 时发生错误: {e}")
        
        return temp_files
    
    def delete_temp_file(self, filepath: str) -> bool:
        """删除单个临时文件"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"已删除临时文件: {filepath}")
                return True
            else:
                logger.info(f"文件不存在，跳过: {filepath}")
                return False
        except PermissionError as e:
            logger.error(f"权限不足，无法删除文件 {filepath}: {e}")
            return False
        except Exception as e:
            logger.error(f"删除文件 {filepath} 时发生错误: {e}")
            return False
    
    def cleanup_temp_files(self, max_age_hours: float = 1.0, dry_run: bool = False) -> Dict[str, Any]:
        """清理临时文件"""
        logger.info(f"开始清理临时文件，最大年龄: {max_age_hours} 小时，dry_run: {dry_run}")
        
        temp_files = self.scan_temp_files(max_age_hours)
        
        total_files = len(temp_files)
        files_to_delete = [f for f in temp_files if f["should_delete"]]
        total_to_delete = len(files_to_delete)
        total_size_to_delete = sum(f["size_bytes"] for f in files_to_delete)
        
        deleted_count = 0
        deleted_size = 0
        errors = []
        
        logger.info(f"发现 {total_files} 个临时文件，其中 {total_to_delete} 个需要删除 ({total_size_to_delete / 1024 / 1024:.2f} MB)")
        
        if not dry_run:
            for file_info in files_to_delete:
                if self.delete_temp_file(file_info["path"]):
                    deleted_count += 1
                    deleted_size += file_info["size_bytes"]
                else:
                    errors.append(file_info["path"])
        
        result = {
            "total_files_found": total_files,
            "files_to_delete": total_to_delete,
            "files_deleted": deleted_count,
            "size_deleted_mb": deleted_size / 1024 / 1024,
            "errors": errors,
            "dry_run": dry_run
        }
        
        if dry_run:
            logger.info(f"DRY RUN - 将删除 {total_to_delete} 个文件 ({total_size_to_delete / 1024 / 1024:.2f} MB)")
        else:
            logger.info(f"清理完成，删除了 {deleted_count} 个文件 ({deleted_size / 1024 / 1024:.2f} MB)")
            if errors:
                logger.warning(f"有 {len(errors)} 个文件删除失败")
        
        return result
    
    def cleanup_specific_files(self, file_patterns: List[str], dry_run: bool = False) -> Dict[str, Any]:
        """清理特定的文件模式"""
        logger.info(f"清理特定文件模式: {file_patterns}, dry_run: {dry_run}")
        
        deleted_count = 0
        deleted_size = 0
        errors = []
        all_files = []
        
        # 扫描的目录列表
        scan_dirs = [self.download_path, self.upload_path]
        
        for scan_dir in scan_dirs:
            if not os.path.exists(scan_dir):
                continue
                
            for pattern in file_patterns:
                search_pattern = os.path.join(scan_dir, pattern)
                matching_files = glob.glob(search_pattern)
                all_files.extend(matching_files)
        
        for filepath in all_files:
            try:
                file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                
                if not dry_run:
                    if self.delete_temp_file(filepath):
                        deleted_count += 1
                        deleted_size += file_size
                    else:
                        errors.append(filepath)
                else:
                    logger.info(f"DRY RUN - 将删除: {filepath} ({file_size} bytes)")
                    
            except Exception as e:
                logger.error(f"处理文件 {filepath} 时发生错误: {e}")
                errors.append(filepath)
        
        result = {
            "total_files_found": len(all_files),
            "files_deleted": deleted_count,
            "size_deleted_mb": deleted_size / 1024 / 1024,
            "errors": errors,
            "dry_run": dry_run
        }
        
        if dry_run:
            logger.info(f"DRY RUN - 将删除 {len(all_files)} 个文件")
        else:
            logger.info(f"清理完成，删除了 {deleted_count} 个文件 ({deleted_size / 1024 / 1024:.2f} MB)")
        
        return result
    
    def cleanup_processed_upload_files(self, max_age_hours: float = 0.5) -> Dict[str, Any]:
        """专门清理files目录中已处理的文件"""
        logger.info(f"清理files目录中超过 {max_age_hours} 小时的已处理文件")
        
        deleted_count = 0
        deleted_size = 0
        errors = []
        all_files = []
        
        if not os.path.exists(self.files_path):
            return {
                "total_files_found": 0,
                "files_deleted": 0,
                "size_deleted_mb": 0,
                "errors": [],
                "message": "files目录不存在"
            }
        
        try:
            for filename in os.listdir(self.files_path):
                filepath = os.path.join(self.files_path, filename)
                
                # 只处理UUID格式的文件
                if self.is_uuid_filename(filename):
                    file_age = self.get_file_age(filepath)
                    
                    if file_age > max_age_hours:
                        all_files.append(filepath)
                        file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                        
                        if self.delete_temp_file(filepath):
                            deleted_count += 1
                            deleted_size += file_size
                        else:
                            errors.append(filepath)
            
        except Exception as e:
            logger.error(f"清理files目录时发生错误: {e}")
            errors.append(f"目录扫描错误: {str(e)}")
        
        result = {
            "total_files_found": len(all_files),
            "files_deleted": deleted_count,
            "size_deleted_mb": deleted_size / 1024 / 1024,
            "errors": errors,
            "message": f"files目录清理完成，删除了 {deleted_count} 个文件"
        }
        
        logger.info(f"files目录清理完成，删除了 {deleted_count} 个文件 ({deleted_size / 1024 / 1024:.2f} MB)")
        return result


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="临时文件清理工具")
    parser.add_argument("--max-age", type=float, default=1.0, help="文件最大年龄（小时，默认1小时）")
    parser.add_argument("--dry-run", action="store_true", help="干运行模式，只显示将要删除的文件")
    parser.add_argument("--patterns", nargs="+", help="特定的文件模式（如 '*.tmp' '*_subtitles.srt'）")
    parser.add_argument("--force", action="store_true", help="强制清理，不询问确认")
    parser.add_argument("--uploads-only", action="store_true", help="只清理uploads目录")
    parser.add_argument("--uploads-age", type=float, default=0.5, help="uploads目录文件最大年龄（小时，默认0.5小时）")
    
    args = parser.parse_args()
    
    cleanup = TempFileCleanup()
    
    if args.uploads_only:
        # 只清理uploads目录
        if not args.force and not args.dry_run:
            print(f"即将清理uploads目录中超过 {args.uploads_age} 小时的文件")
            confirm = input("确认继续？(y/N): ")
            if confirm.lower() != 'y':
                print("操作已取消")
                return
        
        if not args.dry_run:
            result = cleanup.cleanup_processed_upload_files(max_age_hours=args.uploads_age)
        else:
            print(f"DRY RUN - 将清理uploads目录中超过 {args.uploads_age} 小时的文件")
            result = {"total_files_found": 0, "files_deleted": 0, "size_deleted_mb": 0, "errors": []}
    
    elif args.patterns:
        # 清理特定模式的文件
        if not args.force and not args.dry_run:
            print(f"即将清理匹配模式 {args.patterns} 的文件")
            confirm = input("确认继续？(y/N): ")
            if confirm.lower() != 'y':
                print("操作已取消")
                return
        
        result = cleanup.cleanup_specific_files(args.patterns, dry_run=args.dry_run)
    else:
        # 清理所有临时文件
        if not args.force and not args.dry_run:
            print(f"即将清理超过 {args.max_age} 小时的临时文件")
            confirm = input("确认继续？(y/N): ")
            if confirm.lower() != 'y':
                print("操作已取消")
                return
        
        result = cleanup.cleanup_temp_files(max_age_hours=args.max_age, dry_run=args.dry_run)
    
    print("\n清理结果:")
    print(f"发现文件: {result['total_files_found']}")
    print(f"删除文件: {result['files_deleted']}")
    print(f"释放空间: {result['size_deleted_mb']:.2f} MB")
    
    if result['errors']:
        print(f"错误: {len(result['errors'])} 个文件删除失败")
        for error_file in result['errors']:
            print(f"  - {error_file}")
            
    if result.get('message'):
        print(f"消息: {result['message']}")


if __name__ == "__main__":
    main() 