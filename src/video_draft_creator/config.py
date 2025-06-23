"""
配置管理模块
"""

import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CorrectionConfig:
    """文本纠错配置 (DeepSeek API)"""
    api_key: str = ""
    api_endpoint: str = "https://api.deepseek.com/chat/completions"
    model: str = "deepseek-chat"
    max_retries: int = 3
    timeout: int = 30
    chunk_size: int = 2000


@dataclass
class CookieConfig:
    """Cookie配置"""
    from_browser: Optional[str] = "chrome"  # chrome, firefox, safari, edge, opera, brave
    cookie_file: Optional[str] = None
    auto_captcha: bool = True


@dataclass 
class NetworkConfig:
    """网络配置"""
    timeout: int = 30
    retries: int = 3
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


@dataclass
class DownloadConfig:
    """下载配置"""
    output_dir: str = "./temp"
    audio_quality: str = "best"
    supported_formats: list = None
    cookies: CookieConfig = None
    network: NetworkConfig = None

    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ["mp3", "wav", "m4a"]
        if self.cookies is None:
            self.cookies = CookieConfig()
        if self.network is None:
            self.network = NetworkConfig()


@dataclass
class TranscriptionConfig:
    """转录配置"""
    model_size: str = "base"
    language: str = "auto"
    temperature: float = 0.0
    beam_size: int = 5


@dataclass
class OutputConfig:
    """输出配置"""
    default_format: str = "markdown"
    include_timestamps: bool = True
    include_summary: bool = True
    include_keywords: bool = True


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    file: str = "./logs/video_draft_creator.log"


@dataclass
class Config:
    """完整配置"""
    correction: CorrectionConfig
    download: DownloadConfig
    transcription: TranscriptionConfig
    output: OutputConfig
    logging: LoggingConfig

    def validate(self) -> tuple[bool, str]:
        """验证配置是否有效"""
        # 检查API密钥
        if not self.correction.api_key or self.correction.api_key == "your_deepseek_api_key_here":
            return False, "DeepSeek API 密钥未设置，请在配置文件中设置correction.api_key"
        
        # 检查cookie文件路径
        if self.download.cookies.cookie_file:
            cookie_path = Path(self.download.cookies.cookie_file)
            if not cookie_path.exists():
                return False, f"Cookie文件不存在: {self.download.cookies.cookie_file}"
        
        # 检查输出目录权限
        try:
            output_path = Path(self.download.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return False, f"无法创建输出目录: {self.download.output_dir}"
        
        return True, "配置验证通过"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        def dataclass_to_dict(obj):
            if hasattr(obj, '__dataclass_fields__'):
                return {field: dataclass_to_dict(getattr(obj, field)) 
                       for field in obj.__dataclass_fields__}
            elif isinstance(obj, list):
                return [dataclass_to_dict(item) for item in obj]
            else:
                return obj
        
        return dataclass_to_dict(self)


def load_config(config_path: Optional[str] = None) -> Config:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径，如果为None则自动搜索
        
    Returns:
        Config: 配置对象
    """
    # 搜索配置文件路径
    search_paths = []
    if config_path:
        search_paths.append(config_path)
    
    search_paths.extend([
        "./config/config.yaml",
        "./config.yaml",
        "~/.video_draft_creator/config.yaml",
        "/etc/video_draft_creator/config.yaml"
    ])
    
    config_data = {}
    config_file_found = None
    
    for path in search_paths:
        expanded_path = Path(path).expanduser()
        if expanded_path.exists():
            try:
                with open(expanded_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}
                config_file_found = str(expanded_path)
                break
            except Exception as e:
                print(f"警告: 无法读取配置文件 {expanded_path}: {e}")
                continue
    
    # 从环境变量覆盖敏感配置
    env_overrides = {
        'correction.api_key': os.getenv('DEEPSEEK_API_KEY'),
        'correction.api_endpoint': os.getenv('DEEPSEEK_API_ENDPOINT'),
        'download.cookies.cookie_file': os.getenv('COOKIE_FILE'),
        'download.cookies.from_browser': os.getenv('COOKIES_FROM_BROWSER'),
    }
    
    for key_path, env_value in env_overrides.items():
        if env_value:
            keys = key_path.split('.')
            current = config_data
            for key in keys[:-1]:
                current = current.setdefault(key, {})
            current[keys[-1]] = env_value
    
    # 构建配置对象
    try:
        correction_config = CorrectionConfig(
            api_key=config_data.get('correction', {}).get('api_key', ''),
            api_endpoint=config_data.get('correction', {}).get('api_endpoint', 'https://api.deepseek.com/chat/completions'),
            model=config_data.get('correction', {}).get('model', 'deepseek-chat'),
            max_retries=config_data.get('correction', {}).get('max_retries', 3),
            timeout=config_data.get('correction', {}).get('timeout', 30),
            chunk_size=config_data.get('correction', {}).get('chunk_size', 2000)
        )
        
        # Cookie配置
        cookies_data = config_data.get('download', {}).get('cookies', {})
        cookie_config = CookieConfig(
            from_browser=cookies_data.get('from_browser', 'chrome'),
            cookie_file=cookies_data.get('cookie_file'),
            auto_captcha=cookies_data.get('auto_captcha', True)
        )
        
        # 网络配置
        network_data = config_data.get('download', {}).get('network', {})
        network_config = NetworkConfig(
            timeout=network_data.get('timeout', 30),
            retries=network_data.get('retries', 3),
            user_agent=network_data.get('user_agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        )
        
        download_config = DownloadConfig(
            output_dir=config_data.get('download', {}).get('output_dir', './temp'),
            audio_quality=config_data.get('download', {}).get('audio_quality', 'best'),
            supported_formats=config_data.get('download', {}).get('supported_formats', ['mp3', 'wav', 'm4a']),
            cookies=cookie_config,
            network=network_config
        )
        
        transcription_config = TranscriptionConfig(
            model_size=config_data.get('transcription', {}).get('model_size', 'medium'),
            language=config_data.get('transcription', {}).get('language', 'auto'),
            temperature=config_data.get('transcription', {}).get('temperature', 0.0),
            beam_size=config_data.get('transcription', {}).get('beam_size', 5)
        )
        
        output_config = OutputConfig(
            default_format=config_data.get('output', {}).get('default_format', 'markdown'),
            include_timestamps=config_data.get('output', {}).get('include_timestamps', True),
            include_summary=config_data.get('output', {}).get('include_summary', True),
            include_keywords=config_data.get('output', {}).get('include_keywords', True)
        )
        
        logging_config = LoggingConfig(
            level=config_data.get('logging', {}).get('level', 'INFO'),
            file=config_data.get('logging', {}).get('file', './logs/video_draft_creator.log')
        )
        
        config = Config(
            correction=correction_config,
            download=download_config,
            transcription=transcription_config,
            output=output_config,
            logging=logging_config
        )
        
        return config
        
    except Exception as e:
        # 如果配置文件格式错误，返回默认配置
        print(f"警告: 配置文件格式错误，使用默认配置: {e}")
        return Config(
            correction=CorrectionConfig(),
            download=DownloadConfig(),
            transcription=TranscriptionConfig(),
            output=OutputConfig(),
            logging=LoggingConfig()
        ) 