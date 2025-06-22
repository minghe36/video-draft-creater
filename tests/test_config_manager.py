"""
Unit tests for the config_manager module.

Tests configuration management and profile functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil
import json
import yaml

from video_draft_creator.config_manager import (
    ConfigManager,
    ConfigProfile,
    load_config,
    save_config,
    merge_configs
)


class TestConfigManager:
    """Test cases for ConfigManager class."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create a ConfigManager instance for testing."""
        return ConfigManager(config_dir=temp_config_dir)

    def test_init(self, config_manager, temp_config_dir):
        """Test ConfigManager initialization."""
        assert config_manager.config_dir == Path(temp_config_dir)
        assert config_manager.profiles_dir.exists()

    def test_init_with_default_dir(self):
        """Test ConfigManager initialization with default directory."""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path('/tmp/test_home')
            
            manager = ConfigManager()
            expected_dir = Path('/tmp/test_home/.video-draft-creator')
            assert manager.config_dir == expected_dir

    def test_save_profile(self, config_manager, sample_config):
        """Test saving a configuration profile."""
        profile_name = "test_profile"
        description = "Test configuration profile"
        
        success = config_manager.save_profile(profile_name, sample_config, description)
        
        assert success is True
        
        # Check that profile file exists
        profile_file = config_manager.profiles_dir / f"{profile_name}.json"
        assert profile_file.exists()
        
        # Check content
        with open(profile_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data['name'] == profile_name
        assert saved_data['description'] == description
        assert saved_data['config'] == sample_config

    def test_load_profile(self, config_manager, sample_config):
        """Test loading a configuration profile."""
        profile_name = "load_test_profile"
        
        # Save a profile first
        config_manager.save_profile(profile_name, sample_config, "Test profile")
        
        # Load the profile
        loaded_profile = config_manager.load_profile(profile_name)
        
        assert loaded_profile is not None
        assert isinstance(loaded_profile, ConfigProfile)
        assert loaded_profile.name == profile_name
        assert loaded_profile.config == sample_config

    def test_load_nonexistent_profile(self, config_manager):
        """Test loading a non-existent profile."""
        loaded_profile = config_manager.load_profile("nonexistent")
        
        assert loaded_profile is None

    def test_delete_profile(self, config_manager, sample_config):
        """Test deleting a configuration profile."""
        profile_name = "delete_test_profile"
        
        # Save a profile first
        config_manager.save_profile(profile_name, sample_config, "Test profile")
        
        # Verify it exists
        assert config_manager.profile_exists(profile_name)
        
        # Delete the profile
        success = config_manager.delete_profile(profile_name)
        
        assert success is True
        assert not config_manager.profile_exists(profile_name)

    def test_delete_nonexistent_profile(self, config_manager):
        """Test deleting a non-existent profile."""
        success = config_manager.delete_profile("nonexistent")
        
        assert success is False

    def test_list_profiles(self, config_manager, sample_config):
        """Test listing configuration profiles."""
        # Save multiple profiles
        profiles_data = [
            ("profile1", "First profile"),
            ("profile2", "Second profile"),
        ]
        
        for name, desc in profiles_data:
            config_manager.save_profile(name, sample_config, desc)
        
        # List profiles
        profiles = config_manager.list_profiles()
        
        assert len(profiles) >= 2

    def test_list_profiles_empty(self, config_manager):
        """Test listing profiles when none exist."""
        profiles = config_manager.list_profiles()
        
        assert len(profiles) == 0

    def test_profile_exists(self, config_manager, sample_config):
        """Test checking if a profile exists."""
        profile_name = "exists_test_profile"
        
        # Initially should not exist
        assert not config_manager.profile_exists(profile_name)
        
        # Save the profile
        config_manager.save_profile(profile_name, sample_config, "Test profile")
        
        # Now should exist
        assert config_manager.profile_exists(profile_name)

    def test_get_profile_info(self, config_manager, sample_config):
        """Test getting profile information."""
        profile_name = "info_test_profile"
        description = "Profile for info testing"
        
        config_manager.save_profile(profile_name, sample_config, description)
        
        info = config_manager.get_profile_info(profile_name)
        
        assert info is not None
        assert info['name'] == profile_name
        assert info['description'] == description
        assert 'created_at' in info
        assert 'config_keys' in info

    def test_get_profile_info_nonexistent(self, config_manager):
        """Test getting info for non-existent profile."""
        info = config_manager.get_profile_info("nonexistent")
        
        assert info is None

    def test_update_profile(self, config_manager, sample_config):
        """Test updating an existing profile."""
        profile_name = "update_test_profile"
        
        # Save initial profile
        config_manager.save_profile(profile_name, sample_config, "Initial description")
        
        # Update config
        updated_config = sample_config.copy()
        updated_config['new_key'] = 'new_value'
        updated_description = "Updated description"
        
        success = config_manager.update_profile(profile_name, updated_config, updated_description)
        
        assert success is True
        
        # Load and verify
        loaded_profile = config_manager.load_profile(profile_name)
        assert loaded_profile.config['new_key'] == 'new_value'
        assert loaded_profile.description == updated_description

    def test_update_nonexistent_profile(self, config_manager, sample_config):
        """Test updating a non-existent profile."""
        success = config_manager.update_profile("nonexistent", sample_config, "Description")
        
        assert success is False

    def test_export_profile(self, config_manager, sample_config, temp_config_dir):
        """Test exporting a profile to file."""
        profile_name = "export_test_profile"
        config_manager.save_profile(profile_name, sample_config, "Export test")
        
        export_path = Path(temp_config_dir) / "exported_profile.json"
        success = config_manager.export_profile(profile_name, str(export_path))
        
        assert success is True
        assert export_path.exists()
        
        # Verify exported content
        with open(export_path, 'r') as f:
            exported_data = json.load(f)
        
        assert exported_data['name'] == profile_name
        assert exported_data['config'] == sample_config

    def test_import_profile(self, config_manager, sample_config, temp_config_dir):
        """Test importing a profile from file."""
        # Create export file
        export_data = {
            'name': 'imported_profile',
            'description': 'Imported from file',
            'config': sample_config,
            'created_at': '2024-01-01T12:00:00'
        }
        
        import_path = Path(temp_config_dir) / "import_profile.json"
        with open(import_path, 'w') as f:
            json.dump(export_data, f)
        
        success = config_manager.import_profile(str(import_path))
        
        assert success is True
        assert config_manager.profile_exists('imported_profile')
        
        # Verify imported content
        loaded_profile = config_manager.load_profile('imported_profile')
        assert loaded_profile.config == sample_config

    def test_validate_profile_name(self, config_manager):
        """Test profile name validation."""
        # Valid names
        assert config_manager._validate_profile_name("valid_name")
        assert config_manager._validate_profile_name("valid-name")
        assert config_manager._validate_profile_name("valid123")
        
        # Invalid names
        assert not config_manager._validate_profile_name("")
        assert not config_manager._validate_profile_name("invalid/name")
        assert not config_manager._validate_profile_name("invalid name")
        assert not config_manager._validate_profile_name("invalid*name")

    def test_backup_profiles(self, config_manager, sample_config, temp_config_dir):
        """Test backing up all profiles."""
        # Create multiple profiles
        for i in range(3):
            config_manager.save_profile(f"profile_{i}", sample_config, f"Profile {i}")
        
        backup_path = Path(temp_config_dir) / "backup.json"
        success = config_manager.backup_profiles(str(backup_path))
        
        assert success is True
        assert backup_path.exists()
        
        # Verify backup content
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)
        
        assert len(backup_data['profiles']) == 3

    def test_restore_profiles(self, config_manager, sample_config, temp_config_dir):
        """Test restoring profiles from backup."""
        # Create backup data
        backup_data = {
            'version': '1.0',
            'created_at': '2024-01-01T12:00:00',
            'profiles': [
                {
                    'name': 'restored_profile_1',
                    'description': 'Restored profile 1',
                    'config': sample_config,
                    'created_at': '2024-01-01T12:00:00'
                },
                {
                    'name': 'restored_profile_2',
                    'description': 'Restored profile 2',
                    'config': sample_config,
                    'created_at': '2024-01-01T12:00:00'
                }
            ]
        }
        
        backup_path = Path(temp_config_dir) / "restore_backup.json"
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f)
        
        success = config_manager.restore_profiles(str(backup_path))
        
        assert success is True
        assert config_manager.profile_exists('restored_profile_1')
        assert config_manager.profile_exists('restored_profile_2')


class TestConfigProfile:
    """Test cases for ConfigProfile dataclass."""

    def test_config_profile_creation(self, sample_config):
        """Test ConfigProfile creation."""
        profile = ConfigProfile(
            name="test_profile",
            description="Test profile description",
            config=sample_config,
            created_at="2024-01-01T12:00:00",
            updated_at="2024-01-01T12:00:00"
        )
        
        assert profile.name == "test_profile"
        assert profile.description == "Test profile description"
        assert profile.config == sample_config
        assert profile.created_at == "2024-01-01T12:00:00"

    def test_config_profile_to_dict(self, sample_config):
        """Test ConfigProfile to dictionary conversion."""
        profile = ConfigProfile(
            name="test_profile",
            description="Test profile",
            config=sample_config,
            created_at="2024-01-01T12:00:00"
        )
        
        profile_dict = profile.to_dict()
        
        assert profile_dict['name'] == "test_profile"
        assert profile_dict['config'] == sample_config
        assert 'created_at' in profile_dict

    def test_config_profile_from_dict(self, sample_config):
        """Test ConfigProfile creation from dictionary."""
        profile_dict = {
            'name': 'dict_profile',
            'description': 'Profile from dict',
            'config': sample_config,
            'created_at': '2024-01-01T12:00:00',
            'updated_at': '2024-01-01T12:00:00'
        }
        
        profile = ConfigProfile.from_dict(profile_dict)
        
        assert profile.name == 'dict_profile'
        assert profile.config == sample_config


class TestConfigUtilityFunctions:
    """Test cases for utility functions."""

    def test_load_config_json(self, temp_dir, sample_config):
        """Test loading JSON config file."""
        config_file = Path(temp_dir) / "config.json"
        
        with open(config_file, 'w') as f:
            json.dump(sample_config, f)
        
        loaded_config = load_config(str(config_file))
        
        assert loaded_config == sample_config

    def test_load_config_yaml(self, temp_dir, sample_config):
        """Test loading YAML config file."""
        config_file = Path(temp_dir) / "config.yaml"
        
        with open(config_file, 'w') as f:
            yaml.dump(sample_config, f)
        
        loaded_config = load_config(str(config_file))
        
        assert loaded_config == sample_config

    def test_load_config_nonexistent(self):
        """Test loading non-existent config file."""
        loaded_config = load_config("/nonexistent/config.json")
        
        assert loaded_config == {}

    def test_save_config_json(self, temp_dir, sample_config):
        """Test saving JSON config file."""
        config_file = Path(temp_dir) / "save_config.json"
        
        success = save_config(sample_config, str(config_file))
        
        assert success is True
        assert config_file.exists()
        
        # Verify content
        with open(config_file, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config == sample_config

    def test_save_config_yaml(self, temp_dir, sample_config):
        """Test saving YAML config file."""
        config_file = Path(temp_dir) / "save_config.yaml"
        
        success = save_config(sample_config, str(config_file), format='yaml')
        
        assert success is True
        assert config_file.exists()
        
        # Verify content
        with open(config_file, 'r') as f:
            saved_config = yaml.safe_load(f)
        
        assert saved_config == sample_config

    def test_merge_configs(self, sample_config):
        """Test config merging functionality."""
        base_config = sample_config.copy()
        override_config = {
            'audio_quality': 'worst',  # Override existing
            'new_setting': 'new_value'  # Add new
        }
        
        merged_config = merge_configs(base_config, override_config)
        
        assert merged_config['audio_quality'] == 'worst'  # Overridden
        assert merged_config['new_setting'] == 'new_value'  # Added
        assert merged_config['output_dir'] == sample_config['output_dir']  # Preserved

    def test_merge_configs_nested(self):
        """Test merging nested configuration dictionaries."""
        base_config = {
            'section1': {
                'key1': 'value1',
                'key2': 'value2'
            },
            'section2': {
                'key3': 'value3'
            }
        }
        
        override_config = {
            'section1': {
                'key2': 'new_value2',  # Override
                'key4': 'value4'       # Add new
            },
            'section3': {              # New section
                'key5': 'value5'
            }
        }
        
        merged_config = merge_configs(base_config, override_config)
        
        assert merged_config['section1']['key1'] == 'value1'  # Preserved
        assert merged_config['section1']['key2'] == 'new_value2'  # Overridden
        assert merged_config['section1']['key4'] == 'value4'  # Added
        assert merged_config['section2']['key3'] == 'value3'  # Preserved
        assert merged_config['section3']['key5'] == 'value5'  # New section


class TestConfigManagerIntegration:
    """Integration tests for ConfigManager."""

    def test_full_workflow(self, temp_config_dir, sample_config):
        """Test complete configuration management workflow."""
        manager = ConfigManager(config_dir=temp_config_dir)
        
        # Save profile
        profile_name = "workflow_test"
        assert manager.save_profile(profile_name, sample_config, "Workflow test profile")
        
        # List profiles
        profiles = manager.list_profiles()
        assert len(profiles) == 1
        assert profiles[0].name == profile_name
        
        # Load profile
        loaded_profile = manager.load_profile(profile_name)
        assert loaded_profile.config == sample_config
        
        # Update profile
        updated_config = sample_config.copy()
        updated_config['new_key'] = 'new_value'
        assert manager.update_profile(profile_name, updated_config, "Updated description")
        
        # Verify update
        updated_profile = manager.load_profile(profile_name)
        assert updated_profile.config['new_key'] == 'new_value'
        
        # Export profile
        export_path = Path(temp_config_dir) / "exported.json"
        assert manager.export_profile(profile_name, str(export_path))
        assert export_path.exists()
        
        # Delete original profile
        assert manager.delete_profile(profile_name)
        assert not manager.profile_exists(profile_name)
        
        # Import profile back
        assert manager.import_profile(str(export_path))
        assert manager.profile_exists(profile_name)
        
        # Verify imported profile
        reimported_profile = manager.load_profile(profile_name)
        assert reimported_profile.config['new_key'] == 'new_value'

    def test_error_handling(self, temp_config_dir):
        """Test error handling in various scenarios."""
        manager = ConfigManager(config_dir=temp_config_dir)
        
        # Invalid profile name
        assert not manager.save_profile("invalid/name", {}, "Description")
        
        # Load non-existent profile
        assert manager.load_profile("nonexistent") is None
        
        # Delete non-existent profile
        assert not manager.delete_profile("nonexistent")
        
        # Export non-existent profile
        assert not manager.export_profile("nonexistent", "/tmp/export.json")
        
        # Import invalid file
        assert not manager.import_profile("/nonexistent/file.json")


if __name__ == '__main__':
    pytest.main([__file__]) 