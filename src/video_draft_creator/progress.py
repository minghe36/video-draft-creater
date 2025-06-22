"""
进度显示和用户体验模块
"""

import sys
import time
from typing import Optional, Dict, Any
from pathlib import Path
import threading


class ProgressBar:
    """进度条显示器"""
    
    def __init__(self, total: int = 100, width: int = 50, desc: str = "Progress"):
        self.total = total
        self.width = width
        self.desc = desc
        self.current = 0
        self.start_time = time.time()
        self._lock = threading.Lock()
    
    def update(self, amount: int = 1, desc: Optional[str] = None):
        """更新进度"""
        with self._lock:
            self.current += amount
            if desc:
                self.desc = desc
            self._display()
    
    def set_progress(self, current: int, desc: Optional[str] = None):
        """设置当前进度"""
        with self._lock:
            self.current = current
            if desc:
                self.desc = desc
            self._display()
    
    def _display(self):
        """显示进度条"""
        if self.total <= 0:
            return
        
        percent = min(100, (self.current / self.total) * 100)
        filled = int(self.width * self.current // self.total)
        bar = '█' * filled + '░' * (self.width - filled)
        
        # 计算时间信息
        elapsed = time.time() - self.start_time
        if self.current > 0:
            rate = self.current / elapsed
            eta = (self.total - self.current) / rate if rate > 0 else 0
            eta_str = f" ETA: {int(eta)}s" if eta > 0 else ""
        else:
            eta_str = ""
        
        # 显示进度条
        sys.stdout.write(f'\r{self.desc}: |{bar}| {percent:.1f}%{eta_str}')
        sys.stdout.flush()
        
        if self.current >= self.total:
            print()  # 换行
    
    def finish(self, message: str = "完成"):
        """完成进度条"""
        with self._lock:
            self.current = self.total
            elapsed = time.time() - self.start_time
            print(f'\r{self.desc}: |{"█" * self.width}| 100.0% - {message} (耗时: {elapsed:.1f}s)')


class StatusDisplay:
    """状态显示器"""
    
    @staticmethod
    def success(message: str, details: str = ""):
        """显示成功消息"""
        print(f"✅ {message}")
        if details:
            print(f"   {details}")
    
    @staticmethod
    def error(message: str, details: str = "", suggestions: list = None):
        """显示错误消息"""
        print(f"❌ {message}")
        if details:
            print(f"   {details}")
        if suggestions:
            print("💡 建议解决方案:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"   {i}. {suggestion}")
    
    @staticmethod
    def warning(message: str, details: str = ""):
        """显示警告消息"""
        print(f"⚠️  {message}")
        if details:
            print(f"   {details}")
    
    @staticmethod
    def info(message: str, details: str = ""):
        """显示信息消息"""
        print(f"ℹ️  {message}")
        if details:
            print(f"   {details}")
    
    @staticmethod
    def step(step_num: int, total_steps: int, message: str):
        """显示步骤信息"""
        print(f"[{step_num}/{total_steps}] {message}")
    
    @staticmethod
    def section(title: str):
        """显示章节标题"""
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}")


class EnhancedProgress:
    """增强的进度跟踪器"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.current_operation = ""
        self.start_time = time.time()
        
    def start_operation(self, operation: str):
        """开始一个操作"""
        self.current_operation = operation
        if self.verbose:
            StatusDisplay.info(f"开始: {operation}")
        else:
            print(f"🔄 {operation}...")
    
    def update_operation(self, message: str):
        """更新操作状态"""
        if self.verbose:
            StatusDisplay.info(f"{self.current_operation}: {message}")
        else:
            print(f"   {message}")
    
    def complete_operation(self, message: str = "完成"):
        """完成操作"""
        elapsed = time.time() - self.start_time
        if self.verbose:
            StatusDisplay.success(f"{self.current_operation} {message}", f"耗时: {elapsed:.2f}秒")
        else:
            print(f"✅ {message} (耗时: {elapsed:.2f}秒)")
    
    def fail_operation(self, error: str, suggestions: list = None):
        """操作失败"""
        StatusDisplay.error(f"{self.current_operation} 失败", error, suggestions)


class DownloadProgress:
    """下载进度显示器"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.current_file = ""
        
    def __call__(self, d: Dict[str, Any]):
        """yt-dlp下载进度回调"""
        if d['status'] == 'downloading':
            filename = Path(d.get('filename', 'Unknown')).name
            percent = d.get('_percent_str', 'N/A')
            speed = d.get('_speed_str', 'N/A')
            
            if self.verbose:
                if filename != self.current_file:
                    print(f"\n📥 下载: {filename}")
                    self.current_file = filename
                print(f"\r   进度: {percent} | 速度: {speed}", end='', flush=True)
            else:
                print(f"\r📥 {filename} - {percent} ({speed})", end='', flush=True)
                
        elif d['status'] == 'finished':
            filename = Path(d.get('filename', '')).name
            if self.verbose:
                print(f"\n✅ 下载完成: {filename}")
            else:
                print(f"\n✅ 完成: {filename}")
                
        elif d['status'] == 'error':
            filename = Path(d.get('filename', '')).name
            StatusDisplay.error(f"下载失败: {filename}")


class TranscriptionProgress:
    """转录进度显示器"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.segment_count = 0
        self.start_time = time.time()
        
    def __call__(self, segment_count: int, segment: Any):
        """转录进度回调"""
        self.segment_count = segment_count
        
        if self.verbose:
            elapsed = time.time() - self.start_time
            rate = segment_count / elapsed if elapsed > 0 else 0
            print(f"\r🎙️  已处理段落: {segment_count} (速度: {rate:.1f} 段/秒)", end='', flush=True)
        else:
            print(f"\r🎙️  处理中: {segment_count} 段", end='', flush=True)
    
    def finish(self):
        """完成转录"""
        elapsed = time.time() - self.start_time
        print(f"\n✅ 转录完成: {self.segment_count} 段 (耗时: {elapsed:.1f}秒)")


class BatchProgress:
    """批量处理进度显示器"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        
    def __call__(self, batch_progress, item_progress):
        """批量处理进度回调"""
        if hasattr(batch_progress, 'total'):
            total = batch_progress.total
            completed = batch_progress.completed
            successful = batch_progress.successful
            failed = batch_progress.failed
            progress_pct = batch_progress.progress_percentage
            
            # 基础进度信息
            progress_msg = f"批量进度: {completed}/{total} (✅{successful} ❌{failed}) [{progress_pct:.1f}%]"
            
            if self.verbose:
                # 详细模式显示更多信息
                print(f"\r📊 {progress_msg}", end="")
                
                if batch_progress.estimated_time_remaining:
                    remaining_mins = batch_progress.estimated_time_remaining / 60
                    print(f" - 预计剩余: {remaining_mins:.1f}分钟", end="")
                
                if batch_progress.current_item and completed < total:
                    print(f"\n📥 当前: {batch_progress.current_item}")
            else:
                # 简洁模式
                print(f"\r🔄 {progress_msg}", end="")
                
                if completed >= total:
                    print()  # 完成时换行
        else:
            # 兼容旧格式
            if 'filename' in item_progress:
                print(f"\r🔄 {item_progress.get('filename', '')} "
                      f"[{item_progress.get('_percent_str', '0%')}]", end="")


def create_progress_callback(operation_type: str, verbose: bool = False):
    """创建适合的进度回调函数"""
    if operation_type == "download":
        return DownloadProgress(verbose)
    elif operation_type == "transcription":
        return TranscriptionProgress(verbose)
    elif operation_type == "batch":
        return BatchProgress(verbose)
    else:
        return lambda *args, **kwargs: None 