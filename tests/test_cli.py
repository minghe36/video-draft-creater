"""
Unit tests for the CLI module.
"""

import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner

from video_draft_creator.cli import main


class TestCLI:
    """Test cases for CLI functionality."""

    @pytest.fixture
    def cli_runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    def test_main_help(self, cli_runner):
        """Test main help command."""
        result = cli_runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert 'process' in result.output

    def test_process_help(self, cli_runner):
        """Test process command help."""
        result = cli_runner.invoke(main, ['process', '--help'])
        
        assert result.exit_code == 0
        assert '--url' in result.output


if __name__ == '__main__':
    pytest.main([__file__]) 