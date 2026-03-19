"""
音频格式检测和服务
"""
import logging
import os
from typing import Dict, List, Optional

from pydub import AudioSegment

logger = logging.getLogger(__name__)


# 音频格式质量等级（数字越大质量越高）
FORMAT_QUALITY = {
    'flac': 5,
    'wav': 4,
    'm4a': 3,
    'aac': 3,
    'ogg': 2,
    'mp3': 1,
}

# 支持的输出格式
SUPPORTED_FORMATS = ['mp3', 'wav', 'flac', 'm4a', 'ogg']


class FormatService:
    """音频格式服务"""
    
    @staticmethod
    def detect_format(file_path: str) -> Optional[str]:
        """
        检测音频文件的格式
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            格式名称（小写），如果无法检测则返回 None
        """
        try:
            # 从文件扩展名获取格式
            ext = os.path.splitext(file_path)[1].lower().lstrip('.')
            if ext in FORMAT_QUALITY:
                return ext
            
            # 尝试使用 pydub 检测
            audio = AudioSegment.from_file(file_path)
            # pydub 的 format 属性可能不准确，优先使用扩展名
            return ext if ext else None
        except Exception as e:
            logger.error(f"Failed to detect format for {file_path}: {e}", exc_info=True)
            return None
    
    @staticmethod
    def get_format_quality(format_name: str) -> int:
        """
        获取格式的质量等级
        
        Args:
            format_name: 格式名称
            
        Returns:
            质量等级（数字）
        """
        return FORMAT_QUALITY.get(format_name.lower(), 0)
    
    @staticmethod
    def can_convert(source_format: str, target_format: str) -> bool:
        """
        检查是否可以从源格式转换为目标格式
        只能降级或同级，不能升级
        
        Args:
            source_format: 源格式
            target_format: 目标格式
            
        Returns:
            是否可以转换
        """
        if target_format.lower() not in SUPPORTED_FORMATS:
            return False
        
        source_quality = FormatService.get_format_quality(source_format)
        target_quality = FormatService.get_format_quality(target_format)
        
        # 只能降级或同级
        return target_quality <= source_quality
    
    @staticmethod
    def get_available_formats(source_format: str) -> List[str]:
        """
        获取可用的输出格式列表（降级或同级）
        
        Args:
            source_format: 源格式
            
        Returns:
            可用的格式列表
        """
        source_quality = FormatService.get_format_quality(source_format)
        available = []
        
        for fmt in SUPPORTED_FORMATS:
            if FormatService.get_format_quality(fmt) <= source_quality:
                available.append(fmt)
        
        return available
    
    @staticmethod
    def get_format_mime_type(format_name: str) -> str:
        """
        获取格式的 MIME 类型
        
        Args:
            format_name: 格式名称
            
        Returns:
            MIME 类型
        """
        mime_types = {
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'flac': 'audio/flac',
            'm4a': 'audio/mp4',
            'ogg': 'audio/ogg',
        }
        return mime_types.get(format_name.lower(), 'audio/mpeg')

