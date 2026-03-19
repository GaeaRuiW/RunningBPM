"""
进度跟踪服务 (线程安全版本)
"""
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional


class ProgressService:
    """进度跟踪服务 - 使用线程锁保证并发安全"""

    def __init__(self):
        self._lock = threading.Lock()
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

        with self._lock:
            self.progress_store[task_id] = {
                'task_id': task_id,
                'progress': 0,
                'status': 'processing',
                'message': '初始化中...',
                'result': None,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'cancelled': False,
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
        with self._lock:
            if task_id in self.progress_store:
                self.progress_store[task_id]['progress'] = min(100, max(0, progress))
                if message:
                    self.progress_store[task_id]['message'] = message
                self.progress_store[task_id]['updated_at'] = datetime.now().isoformat()
                # 确保状态保持为processing
                if self.progress_store[task_id]['status'] not in ('completed', 'failed'):
                    self.progress_store[task_id]['status'] = 'processing'

    def complete_task(self, task_id: str, result: Dict = None):
        """
        完成任务

        Args:
            task_id: 任务ID
            result: 可选的结果数据
        """
        with self._lock:
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
        with self._lock:
            if task_id in self.progress_store:
                self.progress_store[task_id]['status'] = 'failed'
                self.progress_store[task_id]['message'] = error
                self.progress_store[task_id]['updated_at'] = datetime.now().isoformat()

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        with self._lock:
            if task_id in self.progress_store:
                task = self.progress_store[task_id]
                if task['status'] == 'processing':
                    task['cancelled'] = True
                    task['status'] = 'failed'
                    task['message'] = '任务已取消'
                    task['updated_at'] = datetime.now().isoformat()
                    return True
        return False

    def is_cancelled(self, task_id: str) -> bool:
        """
        检查任务是否已取消

        Args:
            task_id: 任务ID

        Returns:
            是否已取消
        """
        with self._lock:
            if task_id in self.progress_store:
                return self.progress_store[task_id].get('cancelled', False)
        return False

    def get_progress(self, task_id: str) -> Optional[Dict]:
        """
        获取任务进度

        Args:
            task_id: 任务ID

        Returns:
            进度信息字典，如果任务不存在则返回 None
        """
        with self._lock:
            task = self.progress_store.get(task_id)
            if task is not None:
                return dict(task)  # Return a copy to avoid race conditions
            return None

    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """
        清理旧任务

        Args:
            max_age_hours: 最大保留时间（小时）

        Returns:
            清理的任务数量
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        with self._lock:
            to_delete = []
            for task_id, data in self.progress_store.items():
                try:
                    created = datetime.fromisoformat(data['created_at'])
                    if created < cutoff:
                        to_delete.append(task_id)
                except (KeyError, ValueError):
                    to_delete.append(task_id)
            for task_id in to_delete:
                del self.progress_store[task_id]
        return len(to_delete)


# 全局进度服务实例
progress_service = ProgressService()
