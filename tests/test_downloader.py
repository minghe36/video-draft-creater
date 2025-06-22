"""
Unit tests for the downloader module.

Tests downloading functionality with mocked yt-dlp calls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from video_draft_creator.downloader import (
    VideoDownloader, 
    DownloadResult,
    BatchProgress,
    create_downloader_from_config
)


class TestVideoDownloader:
    """Test cases for VideoDownloader class."""

    @pytest.fixture
    def downloader(self, temp_dir, sample_config):
        """Create a VideoDownloader instance for testing."""
        config = sample_config.copy()
        config['temp_dir'] = temp_dir
        return VideoDownloader(config)

    def test_init_with_config(self, sample_config):
        """Test VideoDownloader initialization with configuration."""
        downloader = VideoDownloader(sample_config)
        
        assert downloader.config == sample_config
        assert downloader.temp_dir == sample_config['temp_dir']
        assert downloader.audio_quality == sample_config['audio_quality']
        assert downloader.max_workers == sample_config['max_workers']

    def test_init_with_defaults(self):
        """Test VideoDownloader initialization with minimal config."""
        minimal_config = {}
        downloader = VideoDownloader(minimal_config)
        
        assert downloader.temp_dir == './temp'
        assert downloader.audio_quality == 'best'
        assert downloader.max_workers == 4

    @patch('video_draft_creator.downloader.yt_dlp.YoutubeDL')
    def test_download_success(self, mock_yt_dlp, downloader, temp_dir):
        """Test successful video download."""
        # Mock yt-dlp behavior
        mock_ydl_instance = Mock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        
        # Mock extract_info to return video metadata
        mock_info = {
            'title': 'Test Video',
            'duration': 120.5,
            'filesize': 1024000,
            'url': 'https://test.com/video.mp4'
        }
        mock_ydl_instance.extract_info.return_value = mock_info
        
        # Create a mock downloaded file
        test_file = Path(temp_dir) / "test_audio.wav"
        test_file.write_text("fake audio content")
        
        with patch('pathlib.Path.glob', return_value=[test_file]):
            result = downloader.download("https://test.com/video")
        
        assert isinstance(result, DownloadResult)
        assert result.success is True
        assert result.title == "Test Video"
        assert result.duration == 120.5
        assert result.file_size == 1024000
        assert result.audio_file == str(test_file)
        assert result.error is None

    @patch('video_draft_creator.downloader.yt_dlp.YoutubeDL')
    def test_download_failure(self, mock_yt_dlp, downloader):
        """Test download failure handling."""
        # Mock yt-dlp to raise an exception
        mock_ydl_instance = Mock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.side_effect = Exception("Download failed")
        
        result = downloader.download("https://invalid.com/video")
        
        assert isinstance(result, DownloadResult)
        assert result.success is False
        assert result.error == "Download failed"
        assert result.audio_file is None

    @patch('video_draft_creator.downloader.yt_dlp.YoutubeDL')
    def test_download_with_progress_callback(self, mock_yt_dlp, downloader):
        """Test download with progress callback."""
        mock_ydl_instance = Mock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        
        progress_calls = []
        def progress_callback(progress):
            progress_calls.append(progress)
        
        mock_info = {
            'title': 'Test Video',
            'duration': 60.0,
            'filesize': 512000,
            'url': 'https://test.com/video.mp4'
        }
        mock_ydl_instance.extract_info.return_value = mock_info
        
        with patch('pathlib.Path.glob', return_value=[]):
            downloader.download("https://test.com/video", progress_callback)
        
        # Progress callback should be set in yt-dlp options
        call_args = mock_yt_dlp.call_args
        assert 'progress_hooks' in call_args[0][0]

    @patch('video_draft_creator.downloader.yt_dlp.YoutubeDL')
    def test_download_batch_parallel(self, mock_yt_dlp, downloader, temp_dir):
        """Test parallel batch download."""
        mock_ydl_instance = Mock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        
        # Mock successful downloads
        mock_info = {
            'title': 'Test Video',
            'duration': 60.0,
            'filesize': 512000,
            'url': 'https://test.com/video.mp4'
        }
        mock_ydl_instance.extract_info.return_value = mock_info
        
        test_file = Path(temp_dir) / "test_audio.wav"
        test_file.write_text("fake audio")
        
        urls = ["https://test1.com", "https://test2.com"]
        
        with patch('pathlib.Path.glob', return_value=[test_file]):
            results = downloader.download_batch(urls, max_workers=2)
        
        assert len(results) == 2
        assert all(result.success for result in results)

    @patch('video_draft_creator.downloader.yt_dlp.YoutubeDL')
    def test_download_batch_sequential(self, mock_yt_dlp, downloader, temp_dir):
        """Test sequential batch download."""
        mock_ydl_instance = Mock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        
        mock_info = {
            'title': 'Test Video',
            'duration': 60.0,
            'filesize': 512000,
            'url': 'https://test.com/video.mp4'
        }
        mock_ydl_instance.extract_info.return_value = mock_info
        
        test_file = Path(temp_dir) / "test_audio.wav"
        test_file.write_text("fake audio")
        
        urls = ["https://test1.com", "https://test2.com"]
        
        with patch('pathlib.Path.glob', return_value=[test_file]):
            results = downloader.download_batch_sequential(urls)
        
        assert len(results) == 2
        assert all(result.success for result in results)

    def test_get_ydl_opts(self, downloader, temp_dir):
        """Test YouTube-DL options generation."""
        opts = downloader._get_ydl_opts(temp_dir)
        
        assert 'format' in opts
        assert 'outtmpl' in opts
        assert 'extractaudio' in opts
        assert opts['extractaudio'] is True
        assert opts['audioformat'] == 'wav'
        assert temp_dir in opts['outtmpl']

    def test_progress_hook(self, downloader):
        """Test progress hook functionality."""
        callback_calls = []
        def mock_callback(progress):
            callback_calls.append(progress)
        
        # Test with different progress statuses
        progress_data = {
            'status': 'downloading',
            'downloaded_bytes': 512000,
            'total_bytes': 1024000,
            'speed': 50000,
            'eta': 10
        }
        
        hook = downloader._create_progress_hook(mock_callback)
        hook(progress_data)
        
        assert len(callback_calls) == 1

    def test_find_audio_file(self, downloader, temp_dir):
        """Test audio file finding functionality."""
        # Create test audio files
        audio_file1 = Path(temp_dir) / "test.wav"
        audio_file2 = Path(temp_dir) / "test.mp3"
        audio_file1.write_text("fake audio")
        audio_file2.write_text("fake audio")
        
        # Should find the wav file first
        found_file = downloader._find_audio_file(temp_dir, "test")
        assert found_file == str(audio_file1)
        
        # Test when no file exists
        found_file = downloader._find_audio_file(temp_dir, "nonexistent")
        assert found_file is None


class TestDownloadResult:
    """Test cases for DownloadResult dataclass."""

    def test_download_result_success(self):
        """Test DownloadResult for successful download."""
        result = DownloadResult(
            url="https://test.com",
            success=True,
            title="Test Video",
            duration=120.0,
            file_size=1024000,
            audio_file="/path/to/audio.wav"
        )
        
        assert result.success is True
        assert result.title == "Test Video"
        assert result.duration == 120.0
        assert result.file_size == 1024000
        assert result.audio_file == "/path/to/audio.wav"
        assert result.error is None

    def test_download_result_failure(self):
        """Test DownloadResult for failed download."""
        result = DownloadResult(
            url="https://test.com",
            success=False,
            error="Network error"
        )
        
        assert result.success is False
        assert result.error == "Network error"
        assert result.audio_file is None
        assert result.title is None


class TestBatchProgress:
    """Test cases for BatchProgress dataclass."""

    def test_batch_progress_creation(self):
        """Test BatchProgress dataclass creation."""
        progress = BatchProgress(
            total_urls=5,
            completed_count=2,
            current_url="https://test.com",
            success_count=1,
            failed_count=1,
            total_duration=240.0,
            total_size=2048000,
            estimated_time_remaining=180.0
        )
        
        assert progress.total_urls == 5
        assert progress.completed_count == 2
        assert progress.current_url == "https://test.com"
        assert progress.success_count == 1
        assert progress.failed_count == 1
        assert progress.total_duration == 240.0
        assert progress.total_size == 2048000
        assert progress.estimated_time_remaining == 180.0


class TestCreateDownloaderFromConfig:
    """Test cases for downloader factory function."""

    def test_create_from_dict_config(self, sample_config):
        """Test creating downloader from dictionary config."""
        downloader = create_downloader_from_config(sample_config)
        
        assert isinstance(downloader, VideoDownloader)
        assert downloader.config == sample_config

    def test_create_from_object_config(self, sample_config):
        """Test creating downloader from config object."""
        # Create a mock config object
        class MockConfig:
            def __init__(self, config_dict):
                for key, value in config_dict.items():
                    setattr(self, key, value)
        
        config_obj = MockConfig(sample_config)
        downloader = create_downloader_from_config(config_obj)
        
        assert isinstance(downloader, VideoDownloader)
        # Should convert object to dict
        assert isinstance(downloader.config, dict)

    def test_create_with_none_config(self):
        """Test creating downloader with None config."""
        downloader = create_downloader_from_config(None)
        
        assert isinstance(downloader, VideoDownloader)
        assert downloader.config == {}


if __name__ == '__main__':
    pytest.main([__file__]) 