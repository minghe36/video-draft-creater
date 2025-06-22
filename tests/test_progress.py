"""
Unit tests for the progress module.

Tests progress display and status messaging functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import time

from video_draft_creator.progress import (
    ProgressBar,
    StatusDisplay,
    EnhancedProgress,
    create_progress_callback
)


class TestProgressBar:
    """Test cases for ProgressBar class."""

    @pytest.fixture
    def progress_bar(self):
        """Create a ProgressBar instance for testing."""
        return ProgressBar(total=100, description="Test Progress")

    def test_init(self, progress_bar):
        """Test ProgressBar initialization."""
        assert progress_bar.total == 100
        assert progress_bar.description == "Test Progress"
        assert progress_bar.current == 0
        assert progress_bar.start_time is None

    def test_start(self, progress_bar):
        """Test progress bar start."""
        progress_bar.start()
        
        assert progress_bar.start_time is not None
        assert progress_bar.current == 0

    def test_update(self, progress_bar):
        """Test progress bar update."""
        progress_bar.start()
        progress_bar.update(25)
        
        assert progress_bar.current == 25

    def test_update_with_increment(self, progress_bar):
        """Test progress bar update with increment."""
        progress_bar.start()
        progress_bar.update(25)
        progress_bar.update(25, increment=True)
        
        assert progress_bar.current == 50

    def test_finish(self, progress_bar):
        """Test progress bar finish."""
        progress_bar.start()
        progress_bar.update(50)
        progress_bar.finish()
        
        assert progress_bar.current == progress_bar.total

    def test_percentage_calculation(self, progress_bar):
        """Test percentage calculation."""
        progress_bar.start()
        progress_bar.update(25)
        
        percentage = progress_bar.get_percentage()
        assert percentage == 25.0

    def test_elapsed_time(self, progress_bar):
        """Test elapsed time calculation."""
        progress_bar.start()
        time.sleep(0.1)  # Small delay
        
        elapsed = progress_bar.get_elapsed_time()
        assert elapsed >= 0.1

    def test_estimated_remaining_time(self, progress_bar):
        """Test estimated remaining time calculation."""
        progress_bar.start()
        time.sleep(0.1)
        progress_bar.update(50)
        
        estimated = progress_bar.get_estimated_remaining_time()
        assert estimated >= 0

    @patch('sys.stdout', new_callable=StringIO)
    def test_display_console(self, mock_stdout, progress_bar):
        """Test console display output."""
        progress_bar.start()
        progress_bar.update(50)
        progress_bar.display()
        
        output = mock_stdout.getvalue()
        assert "Test Progress" in output
        assert "50%" in output

    def test_get_status_string(self, progress_bar):
        """Test status string generation."""
        progress_bar.start()
        progress_bar.update(75)
        
        status = progress_bar.get_status_string()
        assert "Test Progress" in status
        assert "75%" in status

    def test_zero_total_handling(self):
        """Test handling of zero total."""
        progress_bar = ProgressBar(total=0, description="Zero Total")
        progress_bar.start()
        
        percentage = progress_bar.get_percentage()
        assert percentage == 100.0  # Should handle gracefully


class TestStatusDisplay:
    """Test cases for StatusDisplay class."""

    @pytest.fixture
    def status_display(self):
        """Create a StatusDisplay instance for testing."""
        return StatusDisplay()

    @patch('sys.stdout', new_callable=StringIO)
    def test_success_message(self, mock_stdout, status_display):
        """Test success message display."""
        status_display.success("Operation completed successfully")
        
        output = mock_stdout.getvalue()
        assert "✅" in output or "SUCCESS" in output
        assert "Operation completed successfully" in output

    @patch('sys.stdout', new_callable=StringIO)
    def test_error_message(self, mock_stdout, status_display):
        """Test error message display."""
        status_display.error("Something went wrong")
        
        output = mock_stdout.getvalue()
        assert "❌" in output or "ERROR" in output
        assert "Something went wrong" in output

    @patch('sys.stdout', new_callable=StringIO)
    def test_warning_message(self, mock_stdout, status_display):
        """Test warning message display."""
        status_display.warning("This is a warning")
        
        output = mock_stdout.getvalue()
        assert "⚠️" in output or "WARNING" in output
        assert "This is a warning" in output

    @patch('sys.stdout', new_callable=StringIO)
    def test_info_message(self, mock_stdout, status_display):
        """Test info message display."""
        status_display.info("This is information")
        
        output = mock_stdout.getvalue()
        assert "ℹ️" in output or "INFO" in output
        assert "This is information" in output

    @patch('sys.stdout', new_callable=StringIO)
    def test_step_message(self, mock_stdout, status_display):
        """Test step message display."""
        status_display.step("Processing step 1")
        
        output = mock_stdout.getvalue()
        assert "🔄" in output or "STEP" in output
        assert "Processing step 1" in output

    def test_with_timestamp(self, status_display):
        """Test message with timestamp."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            status_display.info("Test message", with_timestamp=True)
            
            output = mock_stdout.getvalue()
            assert "Test message" in output
            # Should contain timestamp pattern
            assert any(char.isdigit() for char in output)

    def test_without_emoji(self, status_display):
        """Test message display without emoji."""
        status_display.use_emoji = False
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            status_display.success("Success without emoji")
            
            output = mock_stdout.getvalue()
            assert "SUCCESS" in output
            assert "✅" not in output

    @patch('sys.stdout', new_callable=StringIO)
    def test_custom_prefix(self, mock_stdout, status_display):
        """Test custom prefix functionality."""
        status_display.custom("Custom message", prefix="CUSTOM")
        
        output = mock_stdout.getvalue()
        assert "CUSTOM" in output
        assert "Custom message" in output


class TestEnhancedProgress:
    """Test cases for EnhancedProgress class."""

    @pytest.fixture
    def enhanced_progress(self):
        """Create an EnhancedProgress instance for testing."""
        return EnhancedProgress(total_steps=3, description="Enhanced Test")

    def test_init(self, enhanced_progress):
        """Test EnhancedProgress initialization."""
        assert enhanced_progress.total_steps == 3
        assert enhanced_progress.description == "Enhanced Test"
        assert enhanced_progress.current_step == 0
        assert len(enhanced_progress.step_descriptions) == 0

    def test_add_step(self, enhanced_progress):
        """Test adding step descriptions."""
        enhanced_progress.add_step("Step 1: Download")
        enhanced_progress.add_step("Step 2: Process")
        enhanced_progress.add_step("Step 3: Output")
        
        assert len(enhanced_progress.step_descriptions) == 3
        assert enhanced_progress.step_descriptions[0] == "Step 1: Download"

    def test_start_step(self, enhanced_progress):
        """Test starting a step."""
        enhanced_progress.add_step("Test Step")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            enhanced_progress.start_step()
            
            output = mock_stdout.getvalue()
            assert "Test Step" in output
            assert enhanced_progress.current_step == 1

    def test_update_step_progress(self, enhanced_progress):
        """Test updating step progress."""
        enhanced_progress.add_step("Test Step")
        enhanced_progress.start_step()
        
        with patch('sys.stdout', new_callable=StringIO):
            enhanced_progress.update_step_progress(50)
            
            assert enhanced_progress.step_progress == 50

    def test_complete_step(self, enhanced_progress):
        """Test completing a step."""
        enhanced_progress.add_step("Test Step")
        enhanced_progress.start_step()
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            enhanced_progress.complete_step()
            
            output = mock_stdout.getvalue()
            assert "✅" in output or "completed" in output.lower()

    def test_get_overall_progress(self, enhanced_progress):
        """Test overall progress calculation."""
        enhanced_progress.add_step("Step 1")
        enhanced_progress.add_step("Step 2")
        enhanced_progress.add_step("Step 3")
        
        enhanced_progress.start_step()  # Step 1
        enhanced_progress.complete_step()
        
        overall = enhanced_progress.get_overall_progress()
        assert overall > 0
        assert overall <= 100

    def test_get_status_summary(self, enhanced_progress):
        """Test status summary generation."""
        enhanced_progress.add_step("Download")
        enhanced_progress.add_step("Process")
        
        enhanced_progress.start_step()
        enhanced_progress.update_step_progress(75)
        
        summary = enhanced_progress.get_status_summary()
        assert "Download" in summary
        assert "75%" in summary or "75" in summary

    @patch('sys.stdout', new_callable=StringIO)
    def test_complete_all(self, mock_stdout, enhanced_progress):
        """Test completing all steps."""
        enhanced_progress.add_step("Step 1")
        enhanced_progress.add_step("Step 2")
        
        enhanced_progress.complete_all()
        
        output = mock_stdout.getvalue()
        assert "completed" in output.lower() or "✅" in output


class TestCreateProgressCallback:
    """Test cases for create_progress_callback function."""

    def test_create_basic_callback(self):
        """Test creating a basic progress callback."""
        callback = create_progress_callback("Test Operation")
        
        assert callable(callback)

    def test_callback_execution(self):
        """Test callback execution with progress data."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            callback = create_progress_callback("Test Operation")
            
            # Simulate progress data
            progress_data = {
                'current': 50,
                'total': 100,
                'description': 'Processing...'
            }
            
            callback(progress_data)
            
            # Should produce some output
            output = mock_stdout.getvalue()
            assert len(output) > 0

    def test_callback_with_custom_handler(self):
        """Test callback with custom progress handler."""
        custom_calls = []
        
        def custom_handler(data):
            custom_calls.append(data)
        
        callback = create_progress_callback("Test", handler=custom_handler)
        
        progress_data = {'current': 25, 'total': 100}
        callback(progress_data)
        
        assert len(custom_calls) == 1
        assert custom_calls[0] == progress_data

    def test_callback_with_enhanced_progress(self):
        """Test callback integration with EnhancedProgress."""
        enhanced = EnhancedProgress(total_steps=2, description="Test")
        enhanced.add_step("Step 1")
        enhanced.add_step("Step 2")
        
        callback = create_progress_callback("Test", enhanced_progress=enhanced)
        
        with patch('sys.stdout', new_callable=StringIO):
            # Test that callback works with enhanced progress
            callback({'current': 50, 'total': 100})

    def test_callback_error_handling(self):
        """Test callback error handling."""
        def failing_handler(data):
            raise Exception("Handler failed")
        
        callback = create_progress_callback("Test", handler=failing_handler)
        
        # Should not raise exception
        try:
            callback({'current': 50, 'total': 100})
        except Exception:
            pytest.fail("Callback should handle errors gracefully")


class TestProgressIntegration:
    """Integration tests for progress components."""

    def test_progress_bar_with_status_display(self):
        """Test integration of ProgressBar with StatusDisplay."""
        progress = ProgressBar(total=100, description="Integration Test")
        status = StatusDisplay()
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            status.step("Starting process")
            progress.start()
            progress.update(50)
            status.info("Halfway done")
            progress.finish()
            status.success("Process completed")
            
            output = mock_stdout.getvalue()
            assert "Starting process" in output
            assert "50%" in output
            assert "Halfway done" in output
            assert "Process completed" in output

    def test_enhanced_progress_full_workflow(self):
        """Test full workflow with EnhancedProgress."""
        enhanced = EnhancedProgress(total_steps=3, description="Full Workflow")
        enhanced.add_step("Initialize")
        enhanced.add_step("Process Data")
        enhanced.add_step("Generate Output")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            # Step 1
            enhanced.start_step()
            enhanced.update_step_progress(100)
            enhanced.complete_step()
            
            # Step 2
            enhanced.start_step()
            enhanced.update_step_progress(50)
            enhanced.update_step_progress(100)
            enhanced.complete_step()
            
            # Step 3
            enhanced.start_step()
            enhanced.complete_step()
            
            enhanced.complete_all()
            
            output = mock_stdout.getvalue()
            assert "Initialize" in output
            assert "Process Data" in output
            assert "Generate Output" in output

    def test_progress_with_time_estimation(self):
        """Test progress display with time estimation."""
        progress = ProgressBar(total=100, description="Time Test")
        
        with patch('sys.stdout', new_callable=StringIO):
            progress.start()
            time.sleep(0.1)
            progress.update(25)
            
            # Test that time calculations work
            elapsed = progress.get_elapsed_time()
            estimated = progress.get_estimated_remaining_time()
            
            assert elapsed > 0
            assert estimated >= 0


if __name__ == '__main__':
    pytest.main([__file__]) 