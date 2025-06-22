"""
配置管理模块
支持配置预设的保存、加载和管理
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import asdict
import logging

from .config import Config, load_config


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，默认为 ~/.video-draft-creator/profiles
        """
        if config_dir is None:
            self.config_dir = Path.home() / ".video-draft-creator" / "profiles"
        else:
            self.config_dir = Path(config_dir)
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志配置
        self.logger = logging.getLogger(__name__)
    
    def save_profile(self, name: str, config: Config, description: str = "") -> bool:
        """保存配置预设
        
        Args:
            name: 预设名称
            config: 配置对象
            description: 预设描述
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 清理预设名称
            safe_name = self._sanitize_name(name)
            profile_file = self.config_dir / f"{safe_name}.yaml"
            
            # 准备保存的数据
            profile_data = {
                'name': name,
                'description': description,
                'created_at': self._get_timestamp(),
                'config': self._config_to_dict(config)
            }
            
            # 保存到YAML文件
            with open(profile_file, 'w', encoding='utf-8') as f:
                yaml.dump(profile_data, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            
            self.logger.info(f"配置预设已保存: {name} -> {profile_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存配置预设失败: {e}")
            return False
    
    def load_profile(self, name: str) -> Optional[Config]:
        """加载配置预设
        
        Args:
            name: 预设名称
            
        Returns:
            Config: 配置对象，如果加载失败返回None
        """
        try:
            safe_name = self._sanitize_name(name)
            profile_file = self.config_dir / f"{safe_name}.yaml"
            
            if not profile_file.exists():
                self.logger.warning(f"配置预设不存在: {name}")
                return None
            
            # 从YAML文件加载
            with open(profile_file, 'r', encoding='utf-8') as f:
                profile_data = yaml.safe_load(f)
            
            # 转换为配置对象
            config_dict = profile_data.get('config', {})
            config = self._dict_to_config(config_dict)
            
            self.logger.info(f"配置预设已加载: {name}")
            return config
            
        except Exception as e:
            self.logger.error(f"加载配置预设失败: {e}")
            return None
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """列出所有配置预设
        
        Returns:
            List[Dict]: 预设信息列表
        """
        profiles = []
        
        try:
            for profile_file in self.config_dir.glob("*.yaml"):
                try:
                    with open(profile_file, 'r', encoding='utf-8') as f:
                        profile_data = yaml.safe_load(f)
                    
                    profiles.append({
                        'name': profile_data.get('name', profile_file.stem),
                        'description': profile_data.get('description', ''),
                        'created_at': profile_data.get('created_at', ''),
                        'file': str(profile_file)
                    })
                except Exception as e:
                    self.logger.warning(f"读取预设文件失败 {profile_file}: {e}")
                    
        except Exception as e:
            self.logger.error(f"列出配置预设失败: {e}")
        
        return sorted(profiles, key=lambda x: x['name'])
    
    def delete_profile(self, name: str) -> bool:
        """删除配置预设
        
        Args:
            name: 预设名称
            
        Returns:
            bool: 是否删除成功
        """
        try:
            safe_name = self._sanitize_name(name)
            profile_file = self.config_dir / f"{safe_name}.yaml"
            
            if not profile_file.exists():
                self.logger.warning(f"配置预设不存在: {name}")
                return False
            
            profile_file.unlink()
            self.logger.info(f"配置预设已删除: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"删除配置预设失败: {e}")
            return False
    
    def export_profile(self, name: str, export_path: Path) -> bool:
        """导出配置预设
        
        Args:
            name: 预设名称
            export_path: 导出文件路径
            
        Returns:
            bool: 是否导出成功
        """
        try:
            safe_name = self._sanitize_name(name)
            profile_file = self.config_dir / f"{safe_name}.yaml"
            
            if not profile_file.exists():
                self.logger.warning(f"配置预设不存在: {name}")
                return False
            
            # 复制文件
            import shutil
            shutil.copy2(profile_file, export_path)
            
            self.logger.info(f"配置预设已导出: {name} -> {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出配置预设失败: {e}")
            return False
    
    def import_profile(self, import_path: Path, name: Optional[str] = None) -> bool:
        """导入配置预设
        
        Args:
            import_path: 导入文件路径
            name: 新的预设名称，如果不指定则使用文件中的名称
            
        Returns:
            bool: 是否导入成功
        """
        try:
            if not import_path.exists():
                self.logger.error(f"导入文件不存在: {import_path}")
                return False
            
            # 读取配置文件
            with open(import_path, 'r', encoding='utf-8') as f:
                profile_data = yaml.safe_load(f)
            
            # 使用指定名称或文件中的名称
            profile_name = name or profile_data.get('name', import_path.stem)
            
            # 更新导入时间
            profile_data['imported_at'] = self._get_timestamp()
            if name:
                profile_data['name'] = name
            
            # 保存到配置目录
            safe_name = self._sanitize_name(profile_name)
            profile_file = self.config_dir / f"{safe_name}.yaml"
            
            with open(profile_file, 'w', encoding='utf-8') as f:
                yaml.dump(profile_data, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            
            self.logger.info(f"配置预设已导入: {profile_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"导入配置预设失败: {e}")
            return False
    
    def merge_config(self, base_config: Config, profile_name: str) -> Optional[Config]:
        """合并基础配置和预设配置
        
        Args:
            base_config: 基础配置
            profile_name: 预设名称
            
        Returns:
            Config: 合并后的配置对象
        """
        profile_config = self.load_profile(profile_name)
        if profile_config is None:
            return None
        
        try:
            # 将配置转换为字典进行合并
            base_dict = self._config_to_dict(base_config)
            profile_dict = self._config_to_dict(profile_config)
            
            # 深度合并字典
            merged_dict = self._deep_merge_dict(base_dict, profile_dict)
            
            # 转换回配置对象
            return self._dict_to_config(merged_dict)
            
        except Exception as e:
            self.logger.error(f"合并配置失败: {e}")
            return None
    
    def _sanitize_name(self, name: str) -> str:
        """清理预设名称，确保文件名安全"""
        import re
        # 移除或替换不安全的字符
        safe_name = re.sub(r'[^\w\-_.]', '_', name)
        # 移除连续的下划线
        safe_name = re.sub(r'_+', '_', safe_name)
        # 移除首尾下划线
        safe_name = safe_name.strip('_')
        
        return safe_name or 'unnamed'
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        import datetime
        return datetime.datetime.now().isoformat()
    
    def _config_to_dict(self, config: Config) -> Dict[str, Any]:
        """将配置对象转换为字典"""
        return asdict(config)
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> Config:
        """将字典转换为配置对象"""
        # 这里需要实现从字典到Config对象的转换
        # 由于Config是dataclass，我们可以使用临时文件的方式
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_dict, f, default_flow_style=False)
            temp_path = f.name
        
        try:
            config = load_config(temp_path)
            return config
        finally:
            # 清理临时文件
            os.unlink(temp_path)
    
    def _deep_merge_dict(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并两个字典"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_dict(result[key], value)
            else:
                result[key] = value
        
        return result


# 全局配置管理器实例
_config_manager = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def save_current_config_as_profile(config: Config, name: str, description: str = "") -> bool:
    """保存当前配置为预设
    
    Args:
        config: 当前配置
        name: 预设名称
        description: 预设描述
        
    Returns:
        bool: 是否保存成功
    """
    return get_config_manager().save_profile(name, config, description)


def load_config_profile(name: str) -> Optional[Config]:
    """加载配置预设
    
    Args:
        name: 预设名称
        
    Returns:
        Config: 配置对象
    """
    return get_config_manager().load_profile(name)


def list_config_profiles() -> List[Dict[str, Any]]:
    """列出所有配置预设"""
    return get_config_manager().list_profiles()


def delete_config_profile(name: str) -> bool:
    """删除配置预设
    
    Args:
        name: 预设名称
        
    Returns:
        bool: 是否删除成功
    """
    return get_config_manager().delete_profile(name) 