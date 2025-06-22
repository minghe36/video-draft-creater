"""
Video Draft Creator - 流媒体视频音频下载和转录工具

这个包提供了以下主要功能：
1. 从各大流媒体平台下载音频
2. 使用 faster-whisper 进行语音转录
3. 使用 DeepSeek API 进行文本纠错和结构化处理
4. 生成多种格式的结构化文档
5. 支持批量处理和并行化
"""

from .config import Config, load_config
from .downloader import AudioDownloader, create_downloader, DownloadResult, BatchProgress
from .transcriber import AudioTranscriber, create_transcriber, TranscriptionResult, TranscriptionSegment
from .corrector import (
    TextCorrector, 
    create_corrector_from_config, 
    CorrectionResult, 
    SummaryResult, 
    KeywordsResult, 
    NLPAnalysisResult
)
from .output_formatter import (
    DocumentFormatter,
    create_formatter,
    DocumentMetadata,
    FormattedDocument,
    DocumentFormatterError
)
from .progress import (
    ProgressBar,
    StatusDisplay,
    EnhancedProgress,
    create_progress_callback
)
from .config_manager import (
    ConfigManager,
    get_config_manager,
    save_current_config_as_profile,
    load_config_profile,
    list_config_profiles,
    delete_config_profile
)

__version__ = "1.0.0"
__author__ = "Video Draft Creator Team"
__description__ = "流媒体视频音频下载和转录工具"

# 导出所有公共类和函数
__all__ = [
    # 配置
    'Config',
    'load_config',
    
    # 下载器
    'AudioDownloader',
    'create_downloader',
    'DownloadResult',
    'BatchProgress',
    
    # 转录器
    'AudioTranscriber',
    'create_transcriber',
    'TranscriptionResult',
    'TranscriptionSegment',
    
    # 文本处理器
    'TextCorrector',
    'create_corrector_from_config',
    'CorrectionResult',
    'SummaryResult',
    'KeywordsResult',
    'NLPAnalysisResult',
    
    # 文档格式化器
    'DocumentFormatter',
    'create_formatter',
    'DocumentMetadata',
    'FormattedDocument',
    'DocumentFormatterError',
    
    # 进度显示
    'ProgressBar',
    'StatusDisplay',
    'EnhancedProgress',
    'create_progress_callback',
    
    # 配置管理
    'ConfigManager',
    'get_config_manager',
    'save_current_config_as_profile',
    'load_config_profile',
    'list_config_profiles',
    'delete_config_profile',
] 