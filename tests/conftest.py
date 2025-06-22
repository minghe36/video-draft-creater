"""
Pytest configuration and shared fixtures for video-draft-creator tests.
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from click.testing import CliRunner

# Add src to Python path for testing
import sys
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from video_draft_creator import config
from video_draft_creator.config_manager import ConfigManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_config():
    """Provide a sample configuration for testing."""
    return {
        'output_dir': './output',
        'temp_dir': './temp',
        'audio_quality': 'best',
        'language': 'auto',
        'max_workers': 4,
        'deepseek_api_key': 'test_api_key',
        'deepseek_api_url': 'https://api.deepseek.com/v1/chat/completions',
        'model': 'deepseek-chat',
        'whisper_model_size': 'base'
    }


@pytest.fixture
def sample_text():
    """Provide sample text for testing."""
    return "this is a test text with some errors and no punctuation it needs correction"


@pytest.fixture
def sample_audio_file(temp_dir):
    """Create a sample audio file for testing."""
    audio_file = Path(temp_dir) / "sample_audio.wav"
    audio_file.write_text("fake audio content")  # Not real audio, just for testing
    return str(audio_file)


@pytest.fixture
def sample_transcript():
    """Provide a sample transcript for testing."""
    return [
        {'start': 0.0, 'end': 2.5, 'text': 'Hello world'},
        {'start': 2.5, 'end': 5.0, 'text': 'this is a test'},
        {'start': 5.0, 'end': 7.5, 'text': 'of the transcription system'}
    ]


@pytest.fixture
def mock_deepseek_response():
    """Provide a mock DeepSeek API response."""
    return {
        'choices': [{
            'message': {
                'content': 'This is a corrected text with proper punctuation and structure.'
            }
        }],
        'usage': {
            'prompt_tokens': 100,
            'completion_tokens': 50,
            'total_tokens': 150
        }
    }


@pytest.fixture
def cli_runner():
    """Provide a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_video_downloader():
    """Provide a mock VideoDownloader."""
    mock = Mock()
    mock.download.return_value = Mock(
        success=True,
        audio_file='test_audio.wav',
        title='Test Video',
        duration=120.0,
        file_size=1024000,
        error=None
    )
    return mock


@pytest.fixture
def mock_audio_transcriber():
    """Provide a mock AudioTranscriber."""
    mock = Mock()
    mock.transcribe.return_value = Mock(
        success=True,
        segments=[
            {'start': 0.0, 'end': 2.0, 'text': 'Hello world'},
            {'start': 2.0, 'end': 4.0, 'text': 'this is a test'}
        ],
        language='en',
        error=None
    )
    return mock


@pytest.fixture
def mock_text_corrector():
    """Provide a mock TextCorrector."""
    mock = Mock()
    mock.correct_text.return_value = Mock(
        success=True,
        corrected_text='Hello world, this is a test.',
        original_text='hello world this is a test',
        language='en',
        error=None
    )
    return mock


@pytest.fixture
def mock_output_formatter():
    """Provide a mock OutputFormatter."""
    mock = Mock()
    mock.create_all_formats.return_value = [
        'output.md',
        'output.txt', 
        'output.docx'
    ]
    return mock


# Configure pytest
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests that require API access"
    )


# Skip API tests if no API key is available
def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip API tests when appropriate."""
    skip_api = pytest.mark.skip(reason="API key not available")
    
    for item in items:
        if "api" in item.keywords:
            # Check if API key is available in environment
            if not os.getenv('DEEPSEEK_API_KEY'):
                item.add_marker(skip_api)


@pytest.fixture
def mock_config_manager(temp_dir, sample_config):
    """Provide a mocked ConfigManager instance."""
    config_manager = ConfigManager(config_dir=temp_dir)
    with patch.object(config_manager, 'load_profile', return_value=sample_config):
        yield config_manager


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    test_env = {
        'DEEPSEEK_API_KEY': 'test_api_key',
        'DEEPSEEK_API_URL': 'https://api.deepseek.com/v1/chat/completions'
    }
    
    with patch.dict(os.environ, test_env):
        yield 