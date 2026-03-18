"""
进度跟踪服务
"""
from typing import Dict, Optional
import asyncio
from datetime import datetime
import uuid


class ProgressService:
    """进度跟踪服务"""
    
    def __init__(self):
        self.progress_store: Dict[str, Dict] = {}
    
    def create_task(self, task_id: Optional[str] = None) -> str:
        """
        创建新的任务
        
        Args:
            task_id: 可选的任务ID，如果不提供则自动生成
            
        Returns:
            任务ID
        """
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        self.progress_store[task_id] = {
            'progress': 0,
            'status': 'processing',
            'message': '初始化中...',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }
        return task_id
    
    def update_progress(self, task_id: str, progress: int, message: str = None):
        """
        更新任务进度
        
        Args:
            task_id: 任务ID
            progress: 进度百分比 (0-100)
            message: 可选的状态消息
        """
        if task_id in self.progress_store:
            self.progress_store[task_id]['progress'] = min(100, max(0, progress))
            if message:
                self.progress_store[task_id]['message'] = message
            self.progress_store[task_id]['updated_at'] = datetime.now().isoformat()
            # 确保状态保持为processing
            if self.progress_store[task_id]['status'] != 'completed' and self.progress_store[task_id]['status'] != 'failed':
                self.progress_store[task_id]['status'] = 'processing'
    
    def complete_task(self, task_id: str, result: Dict = None):
        """
        完成任务
        
        Args:
            task_id: 任务ID
            result: 可选的结果数据
        """
        if task_id in self.progress_store:
            self.progress_store[task_id]['progress'] = 100
            self.progress_store[task_id]['status'] = 'completed'
            self.progress_store[task_id]['message'] = '处理完成'
            self.progress_store[task_id]['updated_at'] = datetime.now().isoformat()
            if result:
                self.progress_store[task_id]['result'] = result
    
    def fail_task(self, task_id: str, error: str):
        """
        标记任务失败
        
        Args:
            task_id: 任务ID
            error: 错误消息
        """
        if task_id in self.progress_store:
            self.progress_store[task_id]['status'] = 'failed'
            self.progress_store[task_id]['message'] = error
            self.progress_store[task_id]['updated_at'] = datetime.now().isoformat()
    
    def get_progress(self, task_id: str) -> Optional[Dict]:
        """
        获取任务进度
        
        Args:
            task_id: 任务ID
            
        Returns:
            进度信息字典，如果任务不存在则返回 None
        """
        return self.progress_store.get(task_id)
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """
        清理旧任务（可选，用于内存管理）
        
        Args:
            max_age_hours: 最大保留时间（小时）
        """
        # 简单实现，实际可以使用定时任务
        pass


# 全局进度服务实例
progress_service = ProgressService()

