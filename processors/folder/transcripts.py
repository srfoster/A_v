#!/usr/bin/env python3
"""
Folder Transcription Processor
Transcribes all audio/video files in a folder using the file processor.
Calls the file processor on each .mp4 file found.

Usage:
    python transcribe.py FOLDER/
    
Output:
    For each FILE.mp4 in FOLDER:
      FOLDER/transcripts/FILE_transcript.srt
      FOLDER/transcripts/FILE_transcript.txt
"""

import sys
import argparse
from pathlib import Path
import subprocess
import logging
from datetime import datetime

# Default processor configuration
DEFAULT_MODEL = 'base'
AVAILABLE_MODELS = ['tiny', 'base', 'small', 'medium', 'large']

# Video/audio extensions to process
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'}
ALL_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS


def setup_logging(folder_path):
    """Set up logging to logs/transcripts.log in the target folder."""
    folder = Path(folder_path)
    logs_dir = folder / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / 'transcripts.log'
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info(f"Transcription session started")
    logger.info(f"Target folder: {folder}")
    logger.info("="*60)
    
    return logger


def find_media_files(folder_path):
    """Find all audio/video files in the folder."""
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    
    if not folder.is_dir():
        raise ValueError(f"Not a directory: {folder_path}")
    
    media_files = []
    for ext in ALL_EXTENSIONS:
        media_files.extend(folder.glob(f"*{ext}"))
    
    return sorted(media_files)


def transcribe_file_with_processor(file_path, model_name='base', language=None, cleanup=True):
    """
    Call the file processor to transcribe a single file.
    
    Args:
        file_path: Path to the media file
        model_name: Whisper model size
        language: Optional language code
        cleanup: Whether to clean up temporary files
    
    Returns:
        True if successful, False otherwise
    """
    # Get path to file processor (in ../file/transcripts.py)
    current_dir = Path(__file__).parent
    file_processor = current_dir.parent / 'file' / 'transcripts.py'
    
    if not file_processor.exists():
        print(f"Error: File processor not found at {file_processor}")
        return False
    
    # Build command
    cmd = [sys.executable, str(file_processor), str(file_path)]
    
    if model_name:
        cmd.extend(['-m', model_name])
    
    if language:
        cmd.extend(['-l', language])
    
    if not cleanup:
        cmd.append('--no-cleanup')
    
    print(f"\nProcessing: {file_path.name}")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error processing {file_path.name}: {e}")
        return False


def transcribe_folder(folder_path, model_name=DEFAULT_MODEL, language=None, cleanup=True, continue_on_error=True):
    """
    Transcribe all media files in a folder.
    
    Args:
        folder_path: Path to folder containing media files
        model_name: Whisper model size
        language: Optional language code
        cleanup: Whether to clean up temporary files
        continue_on_error: Whether to continue if a file fails
    
    Returns:
        Dictionary with results
    """
    folder = Path(folder_path)
    
    # Set up logging
    logger = setup_logging(folder)
    
    print(f"\n{'='*60}")
    print(f"Folder Transcription")
    print(f"Folder: {folder}")
    print('='*60)
    
    logger.info(f"Model: {model_name}")
    if language:
        logger.info(f"Language: {language}")
    
    # Find all media files
    media_files = find_media_files(folder)
    
    if not media_files:
        msg = f"No media files found in {folder}"
        print(f"\n{msg}")
        logger.warning(msg)
        return {'total': 0, 'success': 0, 'failed': 0}
    
    print(f"\nFound {len(media_files)} media file(s):")
    logger.info(f"Found {len(media_files)} media file(s)")
    for f in media_files:
        print(f"  - {f.name}")
        logger.info(f"  - {f.name}")
    
    print(f"\nTranscribing with model: {model_name}")
    if language:
        print(f"Language: {language}")
    
    # Process each file
    results = {
        'total': len(media_files),
        'success': 0,
        'failed': 0,
        'files': []
    }
    
    for i, media_file in enumerate(media_files, 1):
        print(f"\n{'='*60}")
        print(f"File {i}/{len(media_files)}")
        print('='*60)
        
        logger.info(f"Processing file {i}/{len(media_files)}: {media_file.name}")
        
        success = transcribe_file_with_processor(
            media_file,
            model_name,
            language,
            cleanup
        )
        
        if success:
            results['success'] += 1
            results['files'].append({'file': str(media_file), 'status': 'success'})
            logger.info(f"✓ Successfully transcribed: {media_file.name}")
        else:
            results['failed'] += 1
            results['files'].append({'file': str(media_file), 'status': 'failed'})
            logger.error(f"✗ Failed to transcribe: {media_file.name}")
            
            if not continue_on_error:
                logger.warning("Stopping due to error")
                print("\nStopping due to error (use --continue to keep processing)")
                break
    
    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    print(f"Total files: {results['total']}")
    print(f"Successful: {results['success']}")
    print(f"Failed: {results['failed']}")
    
    logger.info("="*60)
    logger.info("SUMMARY")
    logger.info(f"Total files: {results['total']}")
    logger.info(f"Successful: {results['success']}")
    logger.info(f"Failed: {results['failed']}")
    
    if results['failed'] > 0:
        print("\nFailed files:")
        logger.info("Failed files:")
        for item in results['files']:
            if item['status'] == 'failed':
                failed_file = Path(item['file']).name
                print(f"  ✗ {failed_file}")
                logger.error(f"  ✗ {failed_file}")
    
    print('='*60)
    logger.info("="*60)
    logger.info("Transcription session completed")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Transcribe all media files in a folder using Whisper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python transcribe.py /path/to/videos/
  python transcribe.py ./recordings/ -m medium
  python transcribe.py ./audio/ -l en --continue
        """
    )
    parser.add_argument(
        'folder',
        help='Path to folder containing media files'
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
    parser.add_argument(
        '--continue',
        dest='continue_on_error',
        action='store_true',
        help='Continue processing even if a file fails'
    )
    
    args = parser.parse_args()
    
    try:
        results = transcribe_folder(
            args.folder,
            args.model,
            args.language,
            cleanup=not args.no_cleanup,
            continue_on_error=args.continue_on_error
        )
        
        # Exit with error code if any files failed
        if results['failed'] > 0:
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
