#!/usr/bin/env python3
"""
File Transcription Processor
Transcribes a single audio/video file using OpenAI Whisper (local).
Outputs transcripts alongside the input file in a 'transcripts/' folder.

Usage:
    python transcribe.py FILE.mp4
    
Output:
    transcripts/FILE_transcript.srt
    transcripts/FILE_transcript.txt
"""

import os
import sys
import time
import argparse
import subprocess
from pathlib import Path
import whisper

# Whisper Configuration
DEFAULT_MODEL = 'base'
AVAILABLE_MODELS = ['tiny', 'base', 'small', 'medium', 'large']

# File extensions
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'}


def extract_audio_from_video(video_path, output_path=None):
    """Extract audio from video file using ffmpeg."""
    if output_path is None:
        video_name = Path(video_path).stem
        output_path = f"temp_audio_{video_name}_{int(time.time())}.wav"
    
    print(f"Extracting audio from {video_path}...")
    
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vn',
        '-acodec', 'pcm_s16le',
        '-ar', '16000',
        '-ac', '1',
        '-y',
        output_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        print(f"Audio extracted: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e.stderr.decode()}")
        raise
    except FileNotFoundError:
        print("Error: ffmpeg not found. Please install ffmpeg.")
        sys.exit(1)


def transcribe_audio_with_whisper(audio_path, model_name='base', language=None):
    """Transcribe audio file using Whisper."""
    print(f"Loading Whisper model: {model_name}...")
    model = whisper.load_model(model_name)
    
    print(f"Transcribing {audio_path}...")
    result = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        verbose=True
    )
    
    print("Transcription completed!")
    return result


def save_srt(whisper_result, output_path):
    """Save transcript in SRT subtitle format."""
    with open(output_path, 'w', encoding='utf-8') as f:
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
    print(f"SRT saved: {output_path}")


def save_txt(whisper_result, output_path):
    """Save transcript as plain text."""
    text = whisper_result['text'].strip()
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"TXT saved: {output_path}")


def transcribe_file(input_file, model_name=DEFAULT_MODEL, language=None, cleanup=True):
    """
    Transcribe a single file and output to transcripts/ folder alongside it.
    
    Args:
        input_file: Path to input audio/video file
        model_name: Whisper model size
        language: Optional language code
        cleanup: Whether to clean up temporary files
    
    Returns:
        Dictionary with output paths
    """
    input_path = Path(input_file).resolve()
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    print(f"\n{'='*60}")
    print(f"Processing: {input_path.name}")
    print('='*60)
    
    # Determine file type and prepare audio
    file_ext = input_path.suffix.lower()
    temp_audio = None
    
    if file_ext in VIDEO_EXTENSIONS:
        audio_file = extract_audio_from_video(str(input_path))
        temp_audio = audio_file
    elif file_ext in AUDIO_EXTENSIONS:
        audio_file = str(input_path)
    else:
        print(f"Warning: Unknown file extension {file_ext}, attempting anyway...")
        audio_file = str(input_path)
    
    try:
        # Transcribe with Whisper
        whisper_result = transcribe_audio_with_whisper(audio_file, model_name, language)
        
        # Create transcripts/ folder alongside the input file
        transcripts_dir = input_path.parent / 'transcripts'
        transcripts_dir.mkdir(exist_ok=True)
        
        # Output files: transcripts/FILENAME_transcript.srt and .txt
        base_name = input_path.stem
        srt_path = transcripts_dir / f"{base_name}_transcript.srt"
        txt_path = transcripts_dir / f"{base_name}_transcript.txt"
        
        # Save outputs
        save_srt(whisper_result, srt_path)
        save_txt(whisper_result, txt_path)
        
        print(f"\n{'='*60}")
        print("✓ Transcription complete!")
        print(f"  SRT: {srt_path}")
        print(f"  TXT: {txt_path}")
        print('='*60)
        
        return {
            'srt': str(srt_path),
            'txt': str(txt_path),
            'text': whisper_result['text'].strip()
        }
        
    finally:
        # Cleanup temporary audio file
        if temp_audio and cleanup and os.path.exists(temp_audio):
            print(f"Cleaning up: {temp_audio}")
            os.remove(temp_audio)


def main():
    parser = argparse.ArgumentParser(
        description='Transcribe a single audio/video file using Whisper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python transcribe.py video.mp4
  python transcribe.py audio.mp3 -m medium
  python transcribe.py video.mp4 -l en
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
        help='Language code (e.g., en, es, fr)'
    )
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Keep temporary audio files'
    )
    
    args = parser.parse_args()
    
    try:
        transcribe_file(
            args.input_file,
            args.model,
            args.language,
            cleanup=not args.no_cleanup
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
