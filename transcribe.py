#!/usr/bin/env python3
"""
Whisper Transcription Script
Transcribes audio from audio or video files using OpenAI Whisper (local).
Automatically extracts audio from video files using ffmpeg.
"""

import os
import sys
import time
import argparse
import subprocess
import json
import re
from pathlib import Path
from datetime import datetime
import whisper

# Whisper Configuration
DEFAULT_MODEL = 'base'  # Options: tiny, base, small, medium, large
AVAILABLE_MODELS = ['tiny', 'base', 'small', 'medium', 'large']

# Video file extensions that require audio extraction
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}
# Audio file extensions
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'}


def extract_audio_from_video(video_path, output_path=None):
    """
    Extract audio from video file using ffmpeg.
    
    Args:
        video_path: Path to video file
        output_path: Optional output path for audio file (default: temp file)
    
    Returns:
        Path to extracted audio file
    """
    if output_path is None:
        video_name = Path(video_path).stem
        output_path = f"temp_audio_{video_name}_{int(time.time())}.wav"
    
    print(f"Extracting audio from {video_path}...")
    
    # Use ffmpeg to extract audio as WAV (Whisper prefers 16kHz mono WAV)
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vn',  # No video
        '-acodec', 'pcm_s16le',  # PCM 16-bit
        '-ar', '16000',  # 16kHz sample rate
        '-ac', '1',  # Mono
        '-y',  # Overwrite output file
        output_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        print(f"Audio extracted successfully: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e.stderr.decode()}")
        raise
    except FileNotFoundError:
        print("Error: ffmpeg not found. Please install ffmpeg:")
        print("  Windows: choco install ffmpeg  or  download from https://ffmpeg.org/")
        print("  Mac: brew install ffmpeg")
        print("  Linux: apt-get install ffmpeg  or  yum install ffmpeg")
        sys.exit(1)


def transcribe_audio_with_whisper(audio_path, model_name='base', language=None):
    """
    Transcribe audio file using Whisper.
    
    Args:
        audio_path: Path to audio file
        model_name: Whisper model size (tiny, base, small, medium, large)
        language: Optional language code (e.g., 'en', 'es') for faster processing
    
    Returns:
        Whisper result dictionary with text and word-level timestamps
    """
    print(f"Loading Whisper model: {model_name}...")
    model = whisper.load_model(model_name)
    
    print(f"Transcribing {audio_path}...")
    
    # Transcribe with word-level timestamps
    result = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        verbose=True
    )
    
    print("Transcription completed!")
    return result


def save_transcript(whisper_result, output_path, formats=['srt']):
    """
    Save transcript to file.
    
    Args:
        whisper_result: Whisper result dictionary
        output_path: Output file path (typically .json)
        formats: List of formats to save (options: 'srt', 'txt', 'words', 'json')
    
    Returns:
        Transcript text
    """
    base_path = Path(output_path).with_suffix('')
    
    # Extract the actual text
    text = whisper_result['text'].strip()
    
    # Save as plain text
    if 'txt' in formats:
        txt_path = base_path.with_suffix('.txt')
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Transcript saved to: {txt_path}")
    
    # Save word-level timestamps
    if 'words' in formats:
        words_path = base_path.with_suffix('.words.txt')
        with open(words_path, 'w', encoding='utf-8') as f:
            for segment in whisper_result.get('segments', []):
                for word_data in segment.get('words', []):
                    word = word_data.get('word', '').strip()
                    start = word_data.get('start', 0)
                    end = word_data.get('end', 0)
                    if word:
                        f.write(f"{start:.3f}\t{end:.3f}\t{word}\n")
        print(f"Word timestamps saved to: {words_path}")
    
    # Save in SRT subtitle format
    if 'srt' in formats:
        srt_path = base_path.with_suffix('.srt')
        with open(srt_path, 'w', encoding='utf-8') as f:
            subtitle_num = 1
            for segment in whisper_result.get('segments', []):
                start_time = segment.get('start', 0)
                end_time = segment.get('end', 0)
                segment_text = segment.get('text', '').strip()
                
                if segment_text:
                    # Format times as SRT timestamps (HH:MM:SS,mmm)
                    start_str = f"{int(start_time//3600):02d}:{int((start_time%3600)//60):02d}:{int(start_time%60):02d},{int((start_time%1)*1000):03d}"
                    end_str = f"{int(end_time//3600):02d}:{int((end_time%3600)//60):02d}:{int(end_time%60):02d},{int((end_time%1)*1000):03d}"
                    
                    f.write(f"{subtitle_num}\n")
                    f.write(f"{start_str} --> {end_str}\n")
                    f.write(f"{segment_text}\n\n")
                    subtitle_num += 1
        print(f"SRT subtitles saved to: {srt_path}")
    
    # Save full JSON (Whisper format)
    if 'json' in formats:
        json_path = base_path.with_suffix('.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(whisper_result, f, indent=2)
        print(f"Full transcript data saved to: {json_path}")
    
    return text


def transcribe_file(input_file, model_name=DEFAULT_MODEL, language=None, output_dir=None, cleanup=True, formats=['srt']):
    """
    Main transcription workflow using Whisper.
    
    Args:
        input_file: Path to input audio/video file
        model_name: Whisper model size (tiny, base, small, medium, large)
        language: Optional language code (e.g., 'en', 'es', 'fr')
        output_dir: Output directory for transcript (default: directory named after input file)
        cleanup: Whether to clean up temporary files
        formats: List of formats to save (options: 'srt', 'txt', 'words', 'json')
    
    Returns:
        Transcript text
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Determine file type and prepare audio file
    file_ext = input_path.suffix.lower()
    temp_audio = None
    
    if file_ext in VIDEO_EXTENSIONS:
        # Extract audio from video
        audio_file = extract_audio_from_video(str(input_path))
        temp_audio = audio_file
    elif file_ext in AUDIO_EXTENSIONS:
        audio_file = str(input_path)
    else:
        print(f"Warning: Unknown file extension {file_ext}, attempting to process anyway...")
        audio_file = str(input_path)
    
    try:
        # Transcribe with Whisper
        whisper_result = transcribe_audio_with_whisper(audio_file, model_name, language)
        
        # Determine output directory
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            # Create directory named after input file in the same directory
            output_dir = input_path.parent / input_path.stem
            output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / f"{input_path.stem}.srt"
        text = save_transcript(whisper_result, str(output_path), formats)
        
        print(f"\n{'='*60}")
        print("TRANSCRIPT:")
        print('='*60)
        print(text)
        print('='*60)
        
        return text
        
    finally:
        # Cleanup temporary audio file
        if temp_audio and cleanup and os.path.exists(temp_audio):
            print(f"Cleaning up temporary file: {temp_audio}")
            os.remove(temp_audio)


def main():
    parser = argparse.ArgumentParser(
        description='Transcribe audio/video files using OpenAI Whisper (local)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Whisper models (larger = better accuracy but slower):
  tiny    - Fastest, least accurate (~1GB VRAM)
  base    - Good balance (default) (~1GB VRAM)
  small   - Better accuracy (~2GB VRAM)
  medium  - High accuracy (~5GB VRAM)
  large   - Best accuracy (~10GB VRAM)

Examples:
  # Transcribe a video file
  python transcribe.py video.mp4
  
  # Use a larger model for better accuracy
  python transcribe.py audio.mp3 -m medium
  
  # Specify language for faster processing
  python transcribe.py audio.wav -l es
  
  # Custom output directory
  python transcribe.py video.mp4 -o ./my_transcripts
        """
    )
    parser.add_argument(
        'input_file',
        help='Path to input audio or video file'
    )
    parser.add_argument(
        '-m', '--model',
        default=DEFAULT_MODEL,
        choices=AVAILABLE_MODELS,
        help=f'Whisper model size (default: {DEFAULT_MODEL})'
    )
    parser.add_argument(
        '-l', '--language',
        help='Language code (e.g., en, es, fr) for faster processing. Auto-detected if not specified.'
    )
    parser.add_argument(
        '-o', '--output-dir',
        help='Output directory for transcript (default: directory named after input file)'
    )
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Keep temporary audio files (for video inputs)'
    )
    parser.add_argument(
        '--all-formats',
        action='store_true',
        help='Generate all output formats (txt, words, srt, json). Default: only srt'
    )
    
    args = parser.parse_args()
    
    # Determine which formats to generate
    formats = ['srt', 'txt', 'words', 'json'] if args.all_formats else ['srt']
    
    try:
        transcribe_file(
            args.input_file,
            args.model,
            args.language,
            args.output_dir,
            cleanup=not args.no_cleanup,
            formats=formats
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
