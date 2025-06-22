"""
Audio transcription module using faster-whisper.

This module provides functionality to transcribe audio files to text
with support for multiple languages and subtitle file generation.
"""

import os
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Iterator, Tuple
from dataclasses import dataclass
from datetime import timedelta

try:
    from faster_whisper import WhisperModel
    from faster_whisper.transcribe import Segment
except ImportError:
    raise ImportError(
        "faster-whisper is required for transcription. "
        "Install it with: pip install faster-whisper"
    )

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class TranscriptionSegment:
    """Represents a transcription segment with timing and text."""
    start: float
    end: float
    text: str
    no_speech_prob: float = 0.0
    avg_logprob: float = 0.0
    compression_ratio: float = 0.0


@dataclass
class TranscriptionResult:
    """Complete transcription result."""
    segments: List[TranscriptionSegment]
    language: str
    language_probability: float
    duration: float
    text: str  # Full concatenated text


class TranscriptionError(Exception):
    """Custom exception for transcription errors."""
    pass


class AudioTranscriber:
    """Audio transcription using faster-whisper."""
    
    # Supported model sizes and their approximate VRAM requirements
    MODEL_SIZES = {
        'tiny': {'vram_gb': 1, 'description': 'Fastest, least accurate'},
        'tiny.en': {'vram_gb': 1, 'description': 'English-only, fastest'},
        'base': {'vram_gb': 1, 'description': 'Good speed/accuracy balance'},
        'base.en': {'vram_gb': 1, 'description': 'English-only, good balance'},
        'small': {'vram_gb': 2, 'description': 'Better accuracy'},
        'small.en': {'vram_gb': 2, 'description': 'English-only, better accuracy'},
        'medium': {'vram_gb': 5, 'description': 'High accuracy'},
        'medium.en': {'vram_gb': 5, 'description': 'English-only, high accuracy'},
        'large-v1': {'vram_gb': 10, 'description': 'Highest accuracy (v1)'},
        'large-v2': {'vram_gb': 10, 'description': 'Highest accuracy (v2)'},
        'large-v3': {'vram_gb': 10, 'description': 'Latest, highest accuracy'},
    }
    
    # Language codes mapping
    SUPPORTED_LANGUAGES = {
        'zh': 'Chinese',
        'en': 'English',
        'ja': 'Japanese',
        'ko': 'Korean',
        'fr': 'French',
        'de': 'German',
        'es': 'Spanish',
        'ru': 'Russian',
        'it': 'Italian',
        'pt': 'Portuguese',
        'ar': 'Arabic',
        'hi': 'Hindi',
    }
    
    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "auto",
        compute_type: str = "auto",
        cpu_threads: int = 0,
        num_workers: int = 1,
        download_root: Optional[str] = None,
        local_files_only: bool = False
    ):
        """
        Initialize the AudioTranscriber.
        
        Args:
            model_size: Size of the Whisper model to use
            device: Device to run on ('cpu', 'cuda', 'auto')
            compute_type: Compute type ('int8', 'int8_float16', 'int16', 'float16', 'float32', 'auto')
            cpu_threads: Number of CPU threads (0 for auto)
            num_workers: Number of workers for parallel processing
            download_root: Directory to save model files
            local_files_only: Only use local model files
        """
        self.model_size = model_size
        self.device = self._determine_device(device)
        self.compute_type = self._determine_compute_type(compute_type)
        self.cpu_threads = cpu_threads
        self.num_workers = num_workers
        self.download_root = download_root
        self.local_files_only = local_files_only
        
        self.model: Optional[WhisperModel] = None
        self._model_loaded = False
        
        logger.info(f"AudioTranscriber initialized with model={model_size}, device={self.device}, compute_type={self.compute_type}")
    
    def _determine_device(self, device: str) -> str:
        """Determine the best device to use."""
        if device == "auto":
            try:
                import torch
                if torch.cuda.is_available():
                    return "cuda"
                else:
                    return "cpu"
            except ImportError:
                return "cpu"
        return device
    
    def _determine_compute_type(self, compute_type: str) -> str:
        """Determine the best compute type based on device."""
        if compute_type == "auto":
            if self.device == "cuda":
                return "int8_float16"  # Good balance of speed and quality on GPU
            else:
                return "int8"  # Faster on CPU
        return compute_type
    
    def load_model(self) -> None:
        """Load the Whisper model."""
        if self._model_loaded:
            return
        
        try:
            logger.info(f"Loading Whisper model: {self.model_size}")
            start_time = time.time()
            
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
                num_workers=self.num_workers,
                download_root=self.download_root,
                local_files_only=self.local_files_only
            )
            
            load_time = time.time() - start_time
            self._model_loaded = True
            logger.info(f"Model loaded successfully in {load_time:.2f} seconds")
            
        except Exception as e:
            raise TranscriptionError(f"Failed to load model {self.model_size}: {str(e)}")
    
    def transcribe_audio(
        self,
        audio_path: Union[str, Path],
        language: Optional[str] = None,
        beam_size: int = 5,
        best_of: int = 5,
        patience: float = 1.0,
        length_penalty: float = 1.0,
        temperature: Union[float, List[float]] = 0.0,
        compression_ratio_threshold: float = 2.4,
        log_prob_threshold: float = -1.0,
        no_speech_threshold: float = 0.6,
        condition_on_previous_text: bool = True,
        prompt_reset_on_temperature: float = 0.5,
        initial_prompt: Optional[str] = None,
        prefix: Optional[str] = None,
        suppress_blank: bool = True,
        suppress_tokens: Optional[List[int]] = None,
        progress_callback: Optional[callable] = None
    ) -> TranscriptionResult:
        """
        Transcribe an audio file to text.
        
        Args:
            audio_path: Path to the audio file
            language: Language code (e.g., 'zh', 'en') or None for auto-detection
            beam_size: Beam size for decoding
            best_of: Number of candidates to consider
            patience: Patience parameter
            length_penalty: Length penalty
            temperature: Temperature(s) for sampling
            compression_ratio_threshold: Compression ratio threshold
            log_prob_threshold: Log probability threshold
            no_speech_threshold: No speech threshold
            condition_on_previous_text: Whether to condition on previous text
            prompt_reset_on_temperature: Temperature at which to reset prompt
            initial_prompt: Initial prompt for the model
            prefix: Prefix for the transcription
            suppress_blank: Whether to suppress blank outputs
            suppress_tokens: List of token IDs to suppress
            prepend_punctuations: Punctuations to prepend
            append_punctuations: Punctuations to append
            progress_callback: Callback function for progress updates
            
        Returns:
            TranscriptionResult object containing segments and metadata
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise TranscriptionError(f"Audio file not found: {audio_path}")
        
        if not self._model_loaded:
            self.load_model()
        
        try:
            logger.info(f"Starting transcription of: {audio_path}")
            start_time = time.time()
            
            # Transcribe the audio
            segments_iter, info = self.model.transcribe(
                str(audio_path),
                language=language,
                beam_size=beam_size,
                best_of=best_of,
                patience=patience,
                length_penalty=length_penalty,
                temperature=temperature,
                compression_ratio_threshold=compression_ratio_threshold,
                log_prob_threshold=log_prob_threshold,
                no_speech_threshold=no_speech_threshold,
                condition_on_previous_text=condition_on_previous_text,
                prompt_reset_on_temperature=prompt_reset_on_temperature,
                initial_prompt=initial_prompt,
                prefix=prefix,
                suppress_blank=suppress_blank,
                suppress_tokens=suppress_tokens
            )
            
            # Convert segments to our format
            segments = []
            full_text = []
            
            for segment in segments_iter:
                transcription_segment = TranscriptionSegment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip(),
                    no_speech_prob=segment.no_speech_prob,
                    avg_logprob=segment.avg_logprob,
                    compression_ratio=segment.compression_ratio
                )
                segments.append(transcription_segment)
                full_text.append(transcription_segment.text)
                
                if progress_callback:
                    progress_callback(len(segments), transcription_segment)
            
            transcription_time = time.time() - start_time
            
            result = TranscriptionResult(
                segments=segments,
                language=info.language,
                language_probability=info.language_probability,
                duration=info.duration,
                text=" ".join(full_text)
            )
            
            logger.info(
                f"Transcription completed in {transcription_time:.2f}s. "
                f"Language: {info.language} ({info.language_probability:.2f}), "
                f"Duration: {info.duration:.2f}s, "
                f"Segments: {len(segments)}"
            )
            
            return result
            
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {str(e)}")
    
    def generate_srt(self, result: TranscriptionResult, output_path: Union[str, Path]) -> None:
        """
        Generate SRT subtitle file from transcription result.
        
        Args:
            result: TranscriptionResult object
            output_path: Path to save the SRT file
        """
        output_path = Path(output_path)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(result.segments, 1):
                    start_time = self._format_time_srt(segment.start)
                    end_time = self._format_time_srt(segment.end)
                    
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{segment.text}\n\n")
            
            logger.info(f"SRT file saved: {output_path}")
            
        except Exception as e:
            raise TranscriptionError(f"Failed to generate SRT file: {str(e)}")
    
    def generate_vtt(self, result: TranscriptionResult, output_path: Union[str, Path]) -> None:
        """
        Generate VTT subtitle file from transcription result.
        
        Args:
            result: TranscriptionResult object
            output_path: Path to save the VTT file
        """
        output_path = Path(output_path)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("WEBVTT\n\n")
                
                for segment in result.segments:
                    start_time = self._format_time_vtt(segment.start)
                    end_time = self._format_time_vtt(segment.end)
                    
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{segment.text}\n\n")
            
            logger.info(f"VTT file saved: {output_path}")
            
        except Exception as e:
            raise TranscriptionError(f"Failed to generate VTT file: {str(e)}")
    
    def generate_text(self, result: TranscriptionResult, output_path: Union[str, Path]) -> None:
        """
        Generate plain text file from transcription result.
        
        Args:
            result: TranscriptionResult object
            output_path: Path to save the text file
        """
        output_path = Path(output_path)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result.text)
            
            logger.info(f"Text file saved: {output_path}")
            
        except Exception as e:
            raise TranscriptionError(f"Failed to generate text file: {str(e)}")
    
    @staticmethod
    def _format_time_srt(seconds: float) -> str:
        """Format time for SRT format (HH:MM:SS,mmm)."""
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{milliseconds:03d}"
    
    @staticmethod
    def _format_time_vtt(seconds: float) -> str:
        """Format time for VTT format (HH:MM:SS.mmm)."""
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{milliseconds:03d}"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            'model_size': self.model_size,
            'device': self.device,
            'compute_type': self.compute_type,
            'loaded': self._model_loaded,
            'supported_languages': self.SUPPORTED_LANGUAGES,
            'model_requirements': self.MODEL_SIZES.get(self.model_size, {})
        }
    
    @classmethod
    def list_available_models(cls) -> Dict[str, Dict[str, Any]]:
        """List all available model sizes and their requirements."""
        return cls.MODEL_SIZES
    
    @classmethod
    def list_supported_languages(cls) -> Dict[str, str]:
        """List all supported language codes and names."""
        return cls.SUPPORTED_LANGUAGES


def create_transcriber(
    model_size: str = "large-v3",
    device: str = "auto",
    compute_type: str = "auto",
    **kwargs
) -> AudioTranscriber:
    """
    Factory function to create an AudioTranscriber instance.
    
    Args:
        model_size: Size of the Whisper model
        device: Device to run on
        compute_type: Compute type
        **kwargs: Additional arguments for AudioTranscriber
        
    Returns:
        AudioTranscriber instance
    """
    return AudioTranscriber(
        model_size=model_size,
        device=device,
        compute_type=compute_type,
        **kwargs
    )


# Convenience functions for quick transcription
def transcribe_file(
    audio_path: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    model_size: str = "large-v3",
    language: Optional[str] = None,
    formats: List[str] = None,
    **kwargs
) -> TranscriptionResult:
    """
    Convenience function to transcribe a single audio file.
    
    Args:
        audio_path: Path to the audio file
        output_dir: Directory to save output files (defaults to same as audio)
        model_size: Whisper model size to use
        language: Language code or None for auto-detection
        formats: List of output formats ('srt', 'vtt', 'txt')
        **kwargs: Additional arguments for transcription
        
    Returns:
        TranscriptionResult object
    """
    if formats is None:
        formats = ['srt', 'vtt', 'txt']
    
    audio_path = Path(audio_path)
    if output_dir is None:
        output_dir = audio_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create transcriber
    transcriber = create_transcriber(model_size=model_size)
    
    # Transcribe
    result = transcriber.transcribe_audio(audio_path, language=language, **kwargs)
    
    # Generate output files
    base_name = audio_path.stem
    
    if 'srt' in formats:
        srt_path = output_dir / f"{base_name}.srt"
        transcriber.generate_srt(result, srt_path)
    
    if 'vtt' in formats:
        vtt_path = output_dir / f"{base_name}.vtt"
        transcriber.generate_vtt(result, vtt_path)
    
    if 'txt' in formats:
        txt_path = output_dir / f"{base_name}.txt"
        transcriber.generate_text(result, txt_path)
    
    return result


if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description="Transcribe audio files using faster-whisper")
    parser.add_argument("audio_file", help="Path to audio file")
    parser.add_argument("--model", default="large-v3", help="Model size")
    parser.add_argument("--language", help="Language code (e.g., zh, en)")
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument("--formats", nargs="+", default=["srt", "vtt", "txt"], help="Output formats")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        result = transcribe_file(
            args.audio_file,
            output_dir=args.output_dir,
            model_size=args.model,
            language=args.language,
            formats=args.formats
        )
        
        print(f"Transcription completed!")
        print(f"Language: {result.language} ({result.language_probability:.2f})")
        print(f"Duration: {result.duration:.2f}s")
        print(f"Segments: {len(result.segments)}")
        print(f"Text preview: {result.text[:200]}...")
        
    except Exception as e:
        print(f"Error: {e}")
        exit(1) 