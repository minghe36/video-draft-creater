"""
Unit tests for the transcriber module.

Tests audio transcription functionality with mocked faster-whisper calls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
from dataclasses import dataclass

from video_draft_creator.transcriber import (
    AudioTranscriber,
    TranscriptionResult,
    create_transcriber_from_config
)


class TestAudioTranscriber:
    """Test cases for AudioTranscriber class."""

    @pytest.fixture
    def transcriber(self, sample_config):
        """Create an AudioTranscriber instance for testing."""
        return AudioTranscriber(sample_config)

    def test_init_with_config(self, sample_config):
        """Test AudioTranscriber initialization with configuration."""
        transcriber = AudioTranscriber(sample_config)
        
        assert transcriber.config == sample_config
        assert transcriber.language == sample_config['language']

    def test_init_with_defaults(self):
        """Test AudioTranscriber initialization with minimal config."""
        minimal_config = {}
        transcriber = AudioTranscriber(minimal_config)
        
        assert transcriber.language == 'auto'

    @patch('video_draft_creator.transcriber.WhisperModel')
    def test_transcribe_success(self, mock_whisper_model, transcriber, sample_audio_file):
        """Test successful audio transcription."""
        # Mock WhisperModel instance
        mock_model = Mock()
        mock_whisper_model.return_value = mock_model
        
        # Mock transcription segments
        mock_segments = [
            Mock(start=0.0, end=2.5, text="Hello world"),
            Mock(start=2.5, end=5.0, text="this is a test"),
            Mock(start=5.0, end=7.5, text="of the transcription system")
        ]
        
        # Mock transcribe method return value
        mock_model.transcribe.return_value = (mock_segments, {'language': 'en'})
        
        result = transcriber.transcribe(sample_audio_file)
        
        assert isinstance(result, TranscriptionResult)
        assert result.success is True
        assert len(result.segments) == 3
        assert result.segments[0]['start'] == 0.0
        assert result.segments[0]['end'] == 2.5
        assert result.segments[0]['text'] == "Hello world"
        assert result.language == 'en'
        assert result.error is None

    @patch('video_draft_creator.transcriber.WhisperModel')
    def test_transcribe_failure(self, mock_whisper_model, transcriber):
        """Test transcription failure handling."""
        # Mock WhisperModel to raise an exception
        mock_model = Mock()
        mock_whisper_model.return_value = mock_model
        mock_model.transcribe.side_effect = Exception("Transcription failed")
        
        result = transcriber.transcribe("nonexistent_file.wav")
        
        assert isinstance(result, TranscriptionResult)
        assert result.success is False
        assert result.error == "Transcription failed"
        assert result.segments is None
        assert result.language is None

    @patch('video_draft_creator.transcriber.WhisperModel')
    def test_transcribe_with_language_detection(self, mock_whisper_model, transcriber, sample_audio_file):
        """Test transcription with automatic language detection."""
        mock_model = Mock()
        mock_whisper_model.return_value = mock_model
        
        # Mock segments with Chinese content
        mock_segments = [
            Mock(start=0.0, end=2.0, text="你好世界"),
            Mock(start=2.0, end=4.0, text="这是一个测试")
        ]
        
        mock_model.transcribe.return_value = (mock_segments, {'language': 'zh'})
        
        result = transcriber.transcribe(sample_audio_file, language='auto')
        
        assert result.success is True
        assert result.language == 'zh'
        assert len(result.segments) == 2
        assert result.segments[0]['text'] == "你好世界"

    @patch('video_draft_creator.transcriber.WhisperModel')
    def test_transcribe_with_specific_language(self, mock_whisper_model, transcriber, sample_audio_file):
        """Test transcription with specific language setting."""
        mock_model = Mock()
        mock_whisper_model.return_value = mock_model
        
        mock_segments = [Mock(start=0.0, end=2.0, text="Hello")]
        mock_model.transcribe.return_value = (mock_segments, {'language': 'en'})
        
        result = transcriber.transcribe(sample_audio_file, language='en')
        
        # Check that language was passed to transcribe method
        call_args = mock_model.transcribe.call_args
        assert call_args[1]['language'] == 'en'

    @patch('video_draft_creator.transcriber.WhisperModel')
    def test_transcribe_with_progress_callback(self, mock_whisper_model, transcriber, sample_audio_file):
        """Test transcription with progress callback."""
        mock_model = Mock()
        mock_whisper_model.return_value = mock_model
        
        progress_calls = []
        def progress_callback(progress):
            progress_calls.append(progress)
        
        mock_segments = [Mock(start=0.0, end=1.0, text="test")]
        mock_model.transcribe.return_value = (mock_segments, {'language': 'en'})
        
        transcriber.transcribe(sample_audio_file, progress_callback=progress_callback)
        
        # Should have called progress callback at least once
        assert len(progress_calls) >= 1

    def test_segments_to_dict(self, transcriber):
        """Test conversion of segments to dictionary format."""
        mock_segments = [
            Mock(start=0.0, end=2.5, text="Hello world"),
            Mock(start=2.5, end=5.0, text="this is a test")
        ]
        
        segments_dict = transcriber._segments_to_dict(mock_segments)
        
        assert len(segments_dict) == 2
        assert segments_dict[0]['start'] == 0.0
        assert segments_dict[0]['end'] == 2.5
        assert segments_dict[0]['text'] == "Hello world"
        assert segments_dict[1]['start'] == 2.5
        assert segments_dict[1]['end'] == 5.0
        assert segments_dict[1]['text'] == "this is a test"

    def test_format_timestamp(self, transcriber):
        """Test timestamp formatting for SRT/VTT files."""
        # Test SRT format
        srt_timestamp = transcriber._format_timestamp(65.5, 'srt')
        assert srt_timestamp == "00:01:05,500"
        
        # Test VTT format
        vtt_timestamp = transcriber._format_timestamp(65.5, 'vtt')
        assert vtt_timestamp == "00:01:05.500"
        
        # Test edge cases
        zero_timestamp = transcriber._format_timestamp(0, 'srt')
        assert zero_timestamp == "00:00:00,000"

    def test_generate_srt(self, transcriber, sample_transcript, temp_dir):
        """Test SRT subtitle file generation."""
        output_file = Path(temp_dir) / "test.srt"
        
        transcriber.generate_srt(sample_transcript, str(output_file))
        
        assert output_file.exists()
        
        content = output_file.read_text(encoding='utf-8')
        assert "1" in content  # Subtitle index
        assert "00:00:00,000" in content  # Timestamp
        assert "Hello world" in content  # Text content

    def test_generate_vtt(self, transcriber, sample_transcript, temp_dir):
        """Test VTT subtitle file generation."""
        output_file = Path(temp_dir) / "test.vtt"
        
        transcriber.generate_vtt(sample_transcript, str(output_file))
        
        assert output_file.exists()
        
        content = output_file.read_text(encoding='utf-8')
        assert "WEBVTT" in content  # VTT header
        assert "00:00:00.000" in content  # Timestamp
        assert "Hello world" in content  # Text content

    def test_extract_text(self, transcriber, sample_transcript):
        """Test text extraction from transcript segments."""
        text = transcriber.extract_text(sample_transcript)
        
        expected_text = "Hello world this is a test of the transcription system"
        assert text == expected_text

    def test_extract_text_with_timestamps(self, transcriber, sample_transcript):
        """Test text extraction with timestamp inclusion."""
        text = transcriber.extract_text(sample_transcript, include_timestamps=True)
        
        assert "[0.0s]" in text
        assert "Hello world" in text
        assert "[2.5s]" in text

    def test_get_model_size(self, transcriber):
        """Test model size determination from configuration."""
        # Test default
        size = transcriber._get_model_size()
        assert size in ['tiny', 'base', 'small', 'medium', 'large']
        
        # Test with config override
        transcriber.config['whisper_model_size'] = 'large'
        size = transcriber._get_model_size()
        assert size == 'large'

    @patch('video_draft_creator.transcriber.WhisperModel')
    def test_model_caching(self, mock_whisper_model, transcriber, sample_audio_file):
        """Test that WhisperModel is cached and reused."""
        mock_model = Mock()
        mock_whisper_model.return_value = mock_model
        mock_model.transcribe.return_value = ([], {'language': 'en'})
        
        # First transcription
        transcriber.transcribe(sample_audio_file)
        # Second transcription
        transcriber.transcribe(sample_audio_file)
        
        # WhisperModel should only be instantiated once
        assert mock_whisper_model.call_count == 1


class TestTranscriptionResult:
    """Test cases for TranscriptionResult dataclass."""

    def test_transcription_result_success(self, sample_transcript):
        """Test TranscriptionResult for successful transcription."""
        result = TranscriptionResult(
            success=True,
            segments=sample_transcript,
            language='en',
            audio_file='/path/to/audio.wav'
        )
        
        assert result.success is True
        assert result.segments == sample_transcript
        assert result.language == 'en'
        assert result.audio_file == '/path/to/audio.wav'
        assert result.error is None

    def test_transcription_result_failure(self):
        """Test TranscriptionResult for failed transcription."""
        result = TranscriptionResult(
            success=False,
            error="File not found",
            audio_file='/path/to/nonexistent.wav'
        )
        
        assert result.success is False
        assert result.error == "File not found"
        assert result.segments is None
        assert result.language is None

    def test_transcription_result_duration_calculation(self, sample_transcript):
        """Test automatic duration calculation from segments."""
        result = TranscriptionResult(
            success=True,
            segments=sample_transcript,
            language='en'
        )
        
        # Duration should be the end time of the last segment
        expected_duration = sample_transcript[-1]['end']
        assert result.duration == expected_duration

    def test_transcription_result_word_count(self, sample_transcript):
        """Test word count calculation from segments."""
        result = TranscriptionResult(
            success=True,
            segments=sample_transcript,
            language='en'
        )
        
        # Count words in all segments
        total_words = sum(len(segment['text'].split()) for segment in sample_transcript)
        assert result.word_count == total_words


class TestCreateTranscriberFromConfig:
    """Test cases for transcriber factory function."""

    def test_create_from_dict_config(self, sample_config):
        """Test creating transcriber from dictionary config."""
        transcriber = create_transcriber_from_config(sample_config)
        
        assert isinstance(transcriber, AudioTranscriber)
        assert transcriber.config == sample_config

    def test_create_from_object_config(self, sample_config):
        """Test creating transcriber from config object."""
        class MockConfig:
            def __init__(self, config_dict):
                for key, value in config_dict.items():
                    setattr(self, key, value)
        
        config_obj = MockConfig(sample_config)
        transcriber = create_transcriber_from_config(config_obj)
        
        assert isinstance(transcriber, AudioTranscriber)
        assert isinstance(transcriber.config, dict)

    def test_create_with_none_config(self):
        """Test creating transcriber with None config."""
        transcriber = create_transcriber_from_config(None)
        
        assert isinstance(transcriber, AudioTranscriber)
        assert transcriber.config == {}


if __name__ == '__main__':
    pytest.main([__file__]) 