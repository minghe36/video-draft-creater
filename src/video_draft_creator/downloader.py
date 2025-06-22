"""
音频下载模块
使用 yt-dlp 下载各大平台的音频
"""

import os
import tempfile
import yt_dlp
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from .config import Config, load_config


@dataclass
class DownloadResult:
    """下载结果数据类"""
    url: str
    success: bool
    message: str
    file_path: Optional[str] = None
    title: Optional[str] = None
    duration: Optional[int] = None
    file_size: Optional[int] = None
    download_time: Optional[float] = None


@dataclass
class BatchProgress:
    """批处理进度数据类"""
    total: int
    completed: int
    successful: int
    failed: int
    current_item: str
    progress_percentage: float
    estimated_time_remaining: Optional[float] = None


class AudioDownloader:
    """音频下载器"""
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化下载器
        
        Args:
            config: 配置对象，如果为None则自动加载
        """
        self.config = config or load_config()
        self.logger = logging.getLogger(__name__)
        self._progress_lock = threading.Lock()
        self._batch_start_time = None
        
        # 支持的平台列表
        self.supported_sites = {
            'youtube.com': 'YouTube',
            'youtu.be': 'YouTube Short',
            'bilibili.com': 'Bilibili',
            'b23.tv': 'Bilibili Short',
            'douyin.com': '抖音',
            'v.qq.com': '腾讯视频',
            'weibo.com': '微博视频',
            'xiaohongshu.com': '小红书',
            'kuaishou.com': '快手',
            'ixigua.com': '西瓜视频'
        }
    
    def _get_ytdl_options(self, output_path: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        构建 yt-dlp 配置选项
        
        Args:
            output_path: 输出路径
            progress_callback: 进度回调函数
            
        Returns:
            Dict: yt-dlp配置选项
        """
        # 基础配置
        ydl_opts = {
            'format': 'bestaudio/best',  # 下载最佳音质
            'outtmpl': output_path,
            'extractaudio': True,
            'audioformat': 'mp3',
            'audioquality': '192',
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': False,
            'no_warnings': False,
            'socket_timeout': self.config.download.network.timeout,
            'retries': self.config.download.network.retries,
        }
        
        # 设置用户代理
        if self.config.download.network.user_agent:
            ydl_opts['http_headers'] = {
                'User-Agent': self.config.download.network.user_agent
            }
        
        # Cookie配置
        cookie_config = self.config.download.cookies
        
        # 从浏览器导入cookie
        if cookie_config.from_browser:
            # 支持的浏览器列表
            supported_browsers = ['chrome', 'firefox', 'safari', 'edge', 'opera', 'brave']
            if cookie_config.from_browser.lower() in supported_browsers:
                ydl_opts['cookiesfrombrowser'] = (cookie_config.from_browser.lower(),)
                self.logger.info(f"使用 {cookie_config.from_browser} 浏览器的cookie")
        
        # 从文件加载cookie
        elif cookie_config.cookie_file and os.path.exists(cookie_config.cookie_file):
            ydl_opts['cookiefile'] = cookie_config.cookie_file
            self.logger.info(f"使用cookie文件: {cookie_config.cookie_file}")
        
        # 进度回调
        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]
        
        # 其他选项
        if cookie_config.auto_captcha:
            # 处理简单的验证码
            ydl_opts['sleep_interval'] = 1
            ydl_opts['max_sleep_interval'] = 5
        
        return ydl_opts
    
    def check_url_support(self, url: str) -> tuple[bool, str]:
        """
        检查URL是否支持下载
        
        Args:
            url: 视频URL
            
        Returns:
            tuple: (是否支持, 平台名称)
        """
        url_lower = url.lower()
        
        for domain, platform in self.supported_sites.items():
            if domain in url_lower:
                return True, platform
        
        # 使用yt-dlp检查是否支持
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    return True, info.get('extractor', 'Unknown')
        except:
            pass
        
        return False, "不支持的平台"
    
    def download_audio(
        self, 
        url: str, 
        output_filename: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> DownloadResult:
        """
        下载音频
        
        Args:
            url: 视频URL
            output_filename: 输出文件名（不包含扩展名）
            progress_callback: 进度回调函数
            
        Returns:
            DownloadResult: 下载结果
        """
        start_time = time.time()
        
        try:
            # 检查URL支持
            is_supported, platform = self.check_url_support(url)
            if not is_supported:
                return DownloadResult(
                    url=url,
                    success=False,
                    message=f"不支持的URL: {url}"
                )
            
            self.logger.info(f"开始从 {platform} 下载: {url}")
            
            # 创建输出目录
            output_dir = Path(self.config.download.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成输出文件路径
            if output_filename:
                output_path = output_dir / f"{output_filename}.%(ext)s"
            else:
                output_path = output_dir / "%(title)s.%(ext)s"
            
            # 获取yt-dlp配置
            ydl_opts = self._get_ytdl_options(str(output_path), progress_callback)
            
            downloaded_file = None
            title = None
            duration = None
            
            # 下载音频
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 获取视频信息
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                
                self.logger.info(f"视频标题: {title}")
                self.logger.info(f"视频时长: {duration}秒")
                
                # 下载音频
                ydl.download([url])
                
                # 查找下载的文件
                if output_filename:
                    # 查找以指定文件名开头的音频文件
                    for ext in ['mp3', 'wav', 'm4a', 'opus', 'aac']:
                        potential_file = output_dir / f"{output_filename}.{ext}"
                        if potential_file.exists():
                            downloaded_file = str(potential_file)
                            break
                else:
                    # 查找最新的音频文件
                    audio_files = []
                    for ext in ['mp3', 'wav', 'm4a', 'opus', 'aac']:
                        audio_files.extend(output_dir.glob(f"*.{ext}"))
                    
                    if audio_files:
                        # 按修改时间排序，取最新的
                        downloaded_file = str(max(audio_files, key=lambda f: f.stat().st_mtime))
            
            download_time = time.time() - start_time
            file_size = None
            
            if downloaded_file and os.path.exists(downloaded_file):
                file_size = os.path.getsize(downloaded_file)
                self.logger.info(f"下载完成: {downloaded_file}")
                return DownloadResult(
                    url=url,
                    success=True,
                    message=f"成功下载音频: {Path(downloaded_file).name}",
                    file_path=downloaded_file,
                    title=title,
                    duration=duration,
                    file_size=file_size,
                    download_time=download_time
                )
            else:
                return DownloadResult(
                    url=url,
                    success=False,
                    message="下载完成但无法找到音频文件",
                    download_time=download_time
                )
                
        except yt_dlp.DownloadError as e:
            error_msg = str(e)
            download_time = time.time() - start_time
            
            if "HTTP Error 403" in error_msg or "Sign in to confirm" in error_msg:
                message = "需要登录验证，请检查cookie配置"
            elif "Private video" in error_msg:
                message = "无法访问私有视频"
            elif "Video unavailable" in error_msg:
                message = "视频不可用或已被删除"
            else:
                message = f"下载失败: {error_msg}"
                
            self.logger.error(f"下载失败: {e}")
            return DownloadResult(
                url=url,
                success=False,
                message=message,
                download_time=download_time
            )
                
        except Exception as e:
            download_time = time.time() - start_time
            self.logger.error(f"下载过程中发生错误: {e}")
            return DownloadResult(
                url=url,
                success=False,
                message=f"下载失败: {str(e)}",
                download_time=download_time
            )
    
    def download_batch(
        self, 
        urls: List[str], 
        progress_callback: Optional[Callable] = None,
        max_workers: int = 3
    ) -> List[DownloadResult]:
        """
        批量下载音频（支持并行处理）
        
        Args:
            urls: URL列表
            progress_callback: 进度回调函数
            max_workers: 最大并行工作线程数
            
        Returns:
            List[DownloadResult]: 每个URL的下载结果
        """
        self._batch_start_time = time.time()
        results = []
        completed_count = 0
        successful_count = 0
        
        def single_download_with_progress(url_index_tuple):
            """单个下载任务的包装函数"""
            url, index = url_index_tuple
            
            def item_progress_callback(d):
                """单个项目的进度回调"""
                if progress_callback:
                    with self._progress_lock:
                        # 计算总体进度
                        current_progress = BatchProgress(
                            total=len(urls),
                            completed=completed_count,
                            successful=successful_count,
                            failed=completed_count - successful_count,
                            current_item=f"({index+1}/{len(urls)}) {url}",
                            progress_percentage=(completed_count / len(urls)) * 100
                        )
                        
                        # 估算剩余时间
                        if completed_count > 0 and self._batch_start_time:
                            elapsed_time = time.time() - self._batch_start_time
                            avg_time_per_item = elapsed_time / completed_count
                            remaining_items = len(urls) - completed_count
                            current_progress.estimated_time_remaining = avg_time_per_item * remaining_items
                        
                        progress_callback(current_progress, d)
            
            try:
                # 执行下载
                result = self.download_audio(url, progress_callback=item_progress_callback)
                
                # 更新计数器
                with self._progress_lock:
                    nonlocal completed_count, successful_count
                    completed_count += 1
                    if result.success:
                        successful_count += 1
                        
                    self.logger.info(f"批量下载进度: {completed_count}/{len(urls)} (成功: {successful_count})")
                
                return result
            except Exception as e:
                # 处理异常情况
                with self._progress_lock:
                    nonlocal completed_count, successful_count
                    completed_count += 1
                    self.logger.error(f"下载任务异常: {url} - {e}")
                
                return DownloadResult(
                    url=url,
                    success=False,
                    message=f"处理异常: {str(e)}"
                )
        
        # 使用线程池进行并行下载
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有下载任务
            url_index_pairs = [(url, i) for i, url in enumerate(urls)]
            future_to_url = {
                executor.submit(single_download_with_progress, pair): pair[0] 
                for pair in url_index_pairs
            }
            
            # 收集结果（保持原始顺序）
            results = [None] * len(urls)
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    # 找到对应的索引位置
                    url_index = urls.index(url)
                    results[url_index] = result
                except Exception as exc:
                    self.logger.error(f'URL {url} 生成异常: {exc}')
                    url_index = urls.index(url)
                    results[url_index] = DownloadResult(
                        url=url,
                        success=False,
                        message=f"处理异常: {str(exc)}"
                    )
        
        # 最终进度回调
        if progress_callback:
            final_progress = BatchProgress(
                total=len(urls),
                completed=len(urls),
                successful=successful_count,
                failed=len(urls) - successful_count,
                current_item="批量下载完成",
                progress_percentage=100.0
            )
            progress_callback(final_progress, {'status': 'finished'})
        
        return results
    
    def download_batch_sequential(
        self, 
        urls: List[str], 
        progress_callback: Optional[Callable] = None
    ) -> List[DownloadResult]:
        """
        批量下载音频（顺序处理）
        
        Args:
            urls: URL列表
            progress_callback: 进度回调函数
            
        Returns:
            List[DownloadResult]: 每个URL的下载结果
        """
        self._batch_start_time = time.time()
        results = []
        successful_count = 0
        
        for i, url in enumerate(urls):
            self.logger.info(f"批量下载进度: {i+1}/{len(urls)}")
            
            if progress_callback:
                # 计算总体进度
                current_progress = BatchProgress(
                    total=len(urls),
                    completed=i,
                    successful=successful_count,
                    failed=i - successful_count,
                    current_item=f"({i+1}/{len(urls)}) {url}",
                    progress_percentage=(i / len(urls)) * 100
                )
                
                # 估算剩余时间
                if i > 0 and self._batch_start_time:
                    elapsed_time = time.time() - self._batch_start_time
                    avg_time_per_item = elapsed_time / i
                    remaining_items = len(urls) - i
                    current_progress.estimated_time_remaining = avg_time_per_item * remaining_items
                
                progress_callback(current_progress, {
                    'status': 'downloading',
                    'filename': f'批量任务 {i+1}/{len(urls)}',
                    '_percent_str': f'{((i)/len(urls)*100):.1f}%',
                    'url': url
                })
            
            result = self.download_audio(url)
            results.append(result)
            
            if result.success:
                successful_count += 1
            else:
                self.logger.warning(f"URL {url} 下载失败: {result.message}")
        
        # 最终进度回调
        if progress_callback:
            final_progress = BatchProgress(
                total=len(urls),
                completed=len(urls),
                successful=successful_count,
                failed=len(urls) - successful_count,
                current_item="批量下载完成",
                progress_percentage=100.0
            )
            progress_callback(final_progress, {'status': 'finished'})
        
        return results
    
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        获取视频信息（不下载）
        
        Args:
            url: 视频URL
            
        Returns:
            Dict: 视频信息，如果失败则返回None
        """
        try:
            # 使用基础cookie配置进行信息提取
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': False,
                'socket_timeout': self.config.download.network.timeout,
            }
            
            # 添加cookie支持（用于获取信息）
            cookie_config = self.config.download.cookies
            if cookie_config.from_browser:
                ydl_opts['cookiesfrombrowser'] = (cookie_config.from_browser.lower(),)
            elif cookie_config.cookie_file and os.path.exists(cookie_config.cookie_file):
                ydl_opts['cookiefile'] = cookie_config.cookie_file
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'upload_date': info.get('upload_date', ''),
                    'view_count': info.get('view_count', 0),
                    'description': info.get('description', ''),
                    'platform': info.get('extractor', 'Unknown')
                }
                
        except Exception as e:
            self.logger.error(f"获取视频信息失败: {e}")
            return None
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            temp_dir = Path(tempfile.gettempdir())
            # 清理yt-dlp的临时文件
            for temp_file in temp_dir.glob("*.part"):
                try:
                    temp_file.unlink()
                except:
                    pass
                    
            for temp_file in temp_dir.glob("yt-dlp-*"):
                try:
                    temp_file.unlink()
                except:
                    pass
                    
        except Exception as e:
            self.logger.warning(f"清理临时文件失败: {e}")


def create_downloader(config_path: Optional[str] = None) -> AudioDownloader:
    """
    创建音频下载器的便捷函数
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        AudioDownloader: 下载器实例
    """
    config = load_config(config_path)
    return AudioDownloader(config) 