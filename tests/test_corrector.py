"""
Unit tests for the corrector module.

Tests text correction functionality with mocked DeepSeek API calls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from dataclasses import dataclass

from video_draft_creator.corrector import (
    TextCorrector,
    CorrectionResult,
    SummaryResult,
    KeywordsResult,
    NLPAnalysisResult,
    create_corrector_from_config
)


class TestTextCorrector:
    """Test cases for TextCorrector class."""

    @pytest.fixture
    def corrector(self, sample_config):
        """Create a TextCorrector instance for testing."""
        return TextCorrector(sample_config)

    def test_init_with_config(self, sample_config):
        """Test TextCorrector initialization with configuration."""
        corrector = TextCorrector(sample_config)
        
        assert corrector.config == sample_config
        assert corrector.api_key == sample_config['deepseek_api_key']
        assert corrector.api_url == sample_config['deepseek_api_url']
        assert corrector.model == sample_config['model']

    def test_init_with_defaults(self):
        """Test TextCorrector initialization with minimal config."""
        minimal_config = {'deepseek_api_key': 'test_key'}
        corrector = TextCorrector(minimal_config)
        
        assert corrector.api_key == 'test_key'
        assert corrector.api_url == 'https://api.deepseek.com/v1/chat/completions'
        assert corrector.model == 'deepseek-chat'

    @patch('video_draft_creator.corrector.requests.post')
    def test_correct_text_success(self, mock_post, corrector, sample_text, mock_deepseek_response):
        """Test successful text correction."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = mock_deepseek_response
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = corrector.correct_text(sample_text)
        
        assert isinstance(result, CorrectionResult)
        assert result.success is True
        assert result.corrected_text == 'This is a corrected text with proper punctuation and structure.'
        assert result.original_text == sample_text
        assert result.language == 'auto'
        assert result.error is None
        assert result.token_usage['total_tokens'] == 150

    @patch('video_draft_creator.corrector.requests.post')
    def test_correct_text_failure(self, mock_post, corrector, sample_text):
        """Test text correction API failure."""
        # Mock API failure
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        result = corrector.correct_text(sample_text)
        
        assert isinstance(result, CorrectionResult)
        assert result.success is False
        assert result.error is not None
        assert result.corrected_text is None

    @patch('video_draft_creator.corrector.requests.post')
    def test_correct_text_with_language(self, mock_post, corrector, mock_deepseek_response):
        """Test text correction with specific language."""
        mock_response = Mock()
        mock_response.json.return_value = mock_deepseek_response
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        chinese_text = "你好世界这是一个测试"
        result = corrector.correct_text(chinese_text, language='zh')
        
        assert result.language == 'zh'
        # Check that the request was made with Chinese language prompt
        call_args = mock_post.call_args
        request_data = json.loads(call_args[1]['data'])
        assert 'Chinese' in request_data['messages'][0]['content'] or 'chinese' in request_data['messages'][0]['content']

    @patch('video_draft_creator.corrector.requests.post')
    def test_summarize_text_success(self, mock_post, corrector, sample_text):
        """Test successful text summarization."""
        mock_response_data = {
            'choices': [{
                'message': {
                    'content': 'This is a brief summary of the text.'
                }
            }],
            'usage': {
                'prompt_tokens': 50,
                'completion_tokens': 20,
                'total_tokens': 70
            }
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = corrector.summarize_text(sample_text)
        
        assert isinstance(result, SummaryResult)
        assert result.success is True
        assert result.summary == 'This is a brief summary of the text.'
        assert result.original_text == sample_text
        assert result.token_usage['total_tokens'] == 70

    @patch('video_draft_creator.corrector.requests.post')
    def test_extract_keywords_success(self, mock_post, corrector, sample_text):
        """Test successful keyword extraction."""
        mock_response_data = {
            'choices': [{
                'message': {
                    'content': 'test, system, correction, world'
                }
            }],
            'usage': {
                'prompt_tokens': 40,
                'completion_tokens': 15,
                'total_tokens': 55
            }
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = corrector.extract_keywords(sample_text)
        
        assert isinstance(result, KeywordsResult)
        assert result.success is True
        assert len(result.keywords) == 4
        assert 'test' in result.keywords
        assert 'system' in result.keywords

    @patch('video_draft_creator.corrector.requests.post')
    def test_analyze_text_success(self, mock_post, corrector, sample_text):
        """Test successful comprehensive text analysis."""
        mock_response_data = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'summary': 'This is a comprehensive summary.',
                        'keywords': ['analysis', 'text', 'test'],
                        'main_topics': ['testing', 'analysis'],
                        'sentiment': 'neutral',
                        'language_detected': 'en'
                    })
                }
            }],
            'usage': {
                'prompt_tokens': 60,
                'completion_tokens': 30,
                'total_tokens': 90
            }
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = corrector.analyze_text(sample_text)
        
        assert isinstance(result, NLPAnalysisResult)
        assert result.success is True
        assert result.summary == 'This is a comprehensive summary.'
        assert len(result.keywords) == 3
        assert result.sentiment == 'neutral'
        assert result.language_detected == 'en'

    def test_build_correction_prompt(self, corrector, sample_text):
        """Test correction prompt building."""
        prompt = corrector._build_correction_prompt(sample_text, 'en')
        
        assert 'correct' in prompt.lower() or 'fix' in prompt.lower()
        assert 'english' in prompt.lower() or 'en' in prompt.lower()
        assert sample_text in prompt

    def test_build_summary_prompt(self, corrector, sample_text):
        """Test summary prompt building."""
        prompt = corrector._build_summary_prompt(sample_text, 'auto')
        
        assert 'summary' in prompt.lower() or 'summarize' in prompt.lower()
        assert sample_text in prompt

    def test_build_keywords_prompt(self, corrector, sample_text):
        """Test keywords prompt building."""
        prompt = corrector._build_keywords_prompt(sample_text, 'auto')
        
        assert 'keyword' in prompt.lower() or 'key' in prompt.lower()
        assert sample_text in prompt

    def test_build_analysis_prompt(self, corrector, sample_text):
        """Test analysis prompt building."""
        prompt = corrector._build_analysis_prompt(sample_text, 'auto')
        
        assert 'analysis' in prompt.lower() or 'analyze' in prompt.lower()
        assert sample_text in prompt

    @patch('video_draft_creator.corrector.requests.post')
    def test_api_call_with_retry(self, mock_post, corrector, sample_text):
        """Test API call retry mechanism."""
        # First call fails, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.text = "Server Error"
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            'choices': [{'message': {'content': 'Success'}}],
            'usage': {'total_tokens': 10}
        }
        
        mock_post.side_effect = [mock_response_fail, mock_response_success]
        
        result = corrector.correct_text(sample_text)
        
        # Should have made 2 API calls (1 retry)
        assert mock_post.call_count == 2
        assert result.success is True

    @patch('video_draft_creator.corrector.requests.post')
    def test_api_call_max_retries(self, mock_post, corrector, sample_text):
        """Test API call max retries exceeded."""
        # All calls fail
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_post.return_value = mock_response
        
        result = corrector.correct_text(sample_text)
        
        # Should have made maximum retries
        assert mock_post.call_count == 3  # 1 initial + 2 retries
        assert result.success is False

    def test_parse_keywords_comma_separated(self, corrector):
        """Test parsing comma-separated keywords."""
        keywords_text = "keyword1, keyword2, keyword3"
        keywords = corrector._parse_keywords(keywords_text)
        
        assert len(keywords) == 3
        assert 'keyword1' in keywords
        assert 'keyword2' in keywords
        assert 'keyword3' in keywords

    def test_parse_keywords_newline_separated(self, corrector):
        """Test parsing newline-separated keywords."""
        keywords_text = "keyword1\nkeyword2\nkeyword3"
        keywords = corrector._parse_keywords(keywords_text)
        
        assert len(keywords) == 3
        assert 'keyword1' in keywords

    def test_parse_keywords_mixed_format(self, corrector):
        """Test parsing keywords with mixed separators."""
        keywords_text = "keyword1, keyword2\nkeyword3; keyword4"
        keywords = corrector._parse_keywords(keywords_text)
        
        assert len(keywords) == 4

    def test_estimate_tokens(self, corrector):
        """Test token estimation."""
        text = "This is a test text for token estimation."
        tokens = corrector._estimate_tokens(text)
        
        # Should be approximately word count / 0.75
        expected_tokens = len(text.split()) / 0.75
        assert abs(tokens - expected_tokens) < 5

    def test_language_detection_from_text(self, corrector):
        """Test language detection from text content."""
        # English text
        lang = corrector._detect_language_from_text("Hello world this is English text")
        assert lang == 'en'
        
        # Chinese text
        lang = corrector._detect_language_from_text("你好世界这是中文文本")
        assert lang == 'zh'
        
        # Mixed or unclear
        lang = corrector._detect_language_from_text("123 456 789")
        assert lang == 'auto'


class TestCorrectionResult:
    """Test cases for CorrectionResult dataclass."""

    def test_correction_result_success(self, sample_text):
        """Test CorrectionResult for successful correction."""
        result = CorrectionResult(
            success=True,
            original_text=sample_text,
            corrected_text="This is corrected text.",
            language='en',
            token_usage={'total_tokens': 100}
        )
        
        assert result.success is True
        assert result.original_text == sample_text
        assert result.corrected_text == "This is corrected text."
        assert result.language == 'en'
        assert result.token_usage['total_tokens'] == 100
        assert result.error is None

    def test_correction_result_failure(self, sample_text):
        """Test CorrectionResult for failed correction."""
        result = CorrectionResult(
            success=False,
            original_text=sample_text,
            error="API Error"
        )
        
        assert result.success is False
        assert result.error == "API Error"
        assert result.corrected_text is None


class TestSummaryResult:
    """Test cases for SummaryResult dataclass."""

    def test_summary_result_creation(self, sample_text):
        """Test SummaryResult creation."""
        result = SummaryResult(
            success=True,
            original_text=sample_text,
            summary="Brief summary",
            language='en',
            token_usage={'total_tokens': 50}
        )
        
        assert result.success is True
        assert result.summary == "Brief summary"
        assert result.token_usage['total_tokens'] == 50


class TestKeywordsResult:
    """Test cases for KeywordsResult dataclass."""

    def test_keywords_result_creation(self, sample_text):
        """Test KeywordsResult creation."""
        keywords = ['test', 'system', 'world']
        result = KeywordsResult(
            success=True,
            original_text=sample_text,
            keywords=keywords,
            language='en',
            token_usage={'total_tokens': 30}
        )
        
        assert result.success is True
        assert result.keywords == keywords
        assert len(result.keywords) == 3


class TestNLPAnalysisResult:
    """Test cases for NLPAnalysisResult dataclass."""

    def test_nlp_analysis_result_creation(self, sample_text):
        """Test NLPAnalysisResult creation."""
        result = NLPAnalysisResult(
            success=True,
            original_text=sample_text,
            summary="Analysis summary",
            keywords=['analysis', 'nlp'],
            main_topics=['testing'],
            sentiment='positive',
            language_detected='en',
            token_usage={'total_tokens': 80}
        )
        
        assert result.success is True
        assert result.summary == "Analysis summary"
        assert result.sentiment == 'positive'
        assert result.language_detected == 'en'
        assert len(result.main_topics) == 1


class TestCreateCorrectorFromConfig:
    """Test cases for corrector factory function."""

    def test_create_from_dict_config(self, sample_config):
        """Test creating corrector from dictionary config."""
        corrector = create_corrector_from_config(sample_config)
        
        assert isinstance(corrector, TextCorrector)
        assert corrector.config == sample_config

    def test_create_from_object_config(self, sample_config):
        """Test creating corrector from config object."""
        class MockConfig:
            def __init__(self, config_dict):
                for key, value in config_dict.items():
                    setattr(self, key, value)
        
        config_obj = MockConfig(sample_config)
        corrector = create_corrector_from_config(config_obj)
        
        assert isinstance(corrector, TextCorrector)
        assert isinstance(corrector.config, dict)

    def test_create_with_none_config(self):
        """Test creating corrector with None config."""
        corrector = create_corrector_from_config(None)
        
        assert isinstance(corrector, TextCorrector)
        assert corrector.config == {}


if __name__ == '__main__':
    pytest.main([__file__]) 