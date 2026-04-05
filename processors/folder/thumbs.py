#!/usr/bin/env python3
"""
Folder Thumbnail Extractor
Extracts thumbnails from all video files in a folder using the file processor.
Calls the file processor on each video file found.

Usage:
    python thumbs.py FOLDER/
    
Output:
    For each FILE.mp4 in FOLDER:
      FOLDER/thumbs/thumb_00-00.png
      FOLDER/thumbs/thumb_00-10.png
      ...
"""

import sys
import argparse
from pathlib import Path
import subprocess
import logging
from datetime import datetime

# Video file extensions
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}


def setup_logging(folder_path):
    """Set up logging to logs/thumbs.log in the target folder."""
    folder = Path(folder_path)
    logs_dir = folder / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / 'thumbs.log'
    
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
    logger.info(f"Thumbnail extraction session started")
    logger.info(f"Target folder: {folder}")
    logger.info("="*60)
    
    return logger


def find_video_files(folder_path):
    """Find all video files in the folder."""
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    
    if not folder.is_dir():
        raise ValueError(f"Not a directory: {folder_path}")
    
    video_files = []
    for ext in VIDEO_EXTENSIONS:
        video_files.extend(folder.glob(f"*{ext}"))
    
    return sorted(video_files)


def extract_thumbnails_with_processor(file_path, interval=10, quality=2):
    """
    Call the file processor to extract thumbnails from a single file.
    
    Args:
        file_path: Path to the video file
        interval: Interval in seconds between thumbnails
        quality: Image quality (2-31, lower is better)
    
    Returns:
        True if successful, False otherwise
    """
    # Get path to file processor (in ../file/thumbs.py)
    current_dir = Path(__file__).parent
    file_processor = current_dir.parent / 'file' / 'thumbs.py'
    
    if not file_processor.exists():
        print(f"Error: File processor not found at {file_processor}")
        return False
    
    # Build command
    cmd = [sys.executable, str(file_processor), str(file_path)]
    
    if interval:
        cmd.extend(['-i', str(interval)])
    
    if quality:
        cmd.extend(['-q', str(quality)])
    
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


def extract_thumbnails_from_folder(folder_path, interval=10, quality=2, continue_on_error=True):
    """
    Extract thumbnails from all video files in a folder.
    
    Args:
        folder_path: Path to folder containing video files
        interval: Interval in seconds between thumbnails
        quality: Image quality (2-31, lower is better)
        continue_on_error: Whether to continue if a file fails
    
    Returns:
        Dictionary with results
    """
    folder = Path(folder_path)
    
    # Set up logging
    logger = setup_logging(folder)
    
    print(f"\n{'='*60}")
    print(f"Folder Thumbnail Extraction")
    print(f"Folder: {folder}")
    print('='*60)
    
    logger.info(f"Interval: {interval}s")
    logger.info(f"Quality: {quality}")
    
    # Find all video files
    video_files = find_video_files(folder)
    
    if not video_files:
        msg = f"No video files found in {folder}"
        print(f"\n{msg}")
        logger.warning(msg)
        return {'total': 0, 'success': 0, 'failed': 0}
    
    print(f"\nFound {len(video_files)} video file(s):")
    logger.info(f"Found {len(video_files)} video file(s)")
    for f in video_files:
        print(f"  - {f.name}")
        logger.info(f"  - {f.name}")
    
    print(f"\nExtracting thumbnails (interval: {interval}s, quality: {quality})")
    
    # Process each file
    results = {
        'total': len(video_files),
        'success': 0,
        'failed': 0,
        'files': []
    }
    
    for i, video_file in enumerate(video_files, 1):
        print(f"\n{'='*60}")
        print(f"File {i}/{len(video_files)}")
        print('='*60)
        
        logger.info(f"Processing file {i}/{len(video_files)}: {video_file.name}")
        
        success = extract_thumbnails_with_processor(
            video_file,
            interval,
            quality
        )
        
        if success:
            results['success'] += 1
            results['files'].append({'file': str(video_file), 'status': 'success'})
            logger.info(f"✓ Successfully extracted thumbnails from: {video_file.name}")
        else:
            results['failed'] += 1
            results['files'].append({'file': str(video_file), 'status': 'failed'})
            logger.error(f"✗ Failed to extract thumbnails from: {video_file.name}")
            
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
    logger.info("Thumbnail extraction session completed")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Extract thumbnails from all video files in a folder',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python thumbs.py /path/to/videos/
  python thumbs.py ./recordings/ -i 5
  python thumbs.py ./videos/ -q 1 --continue
        """
    )
    parser.add_argument(
        'folder',
        help='Path to folder containing video files'
    )
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=10,
        help='Interval in seconds between thumbnails (default: 10)'
    )
    parser.add_argument(
        '-q', '--quality',
        type=int,
        default=2,
        choices=range(1, 32),
        metavar='1-31',
        help='Image quality: 1 (best) to 31 (worst), default: 2'
    )
    parser.add_argument(
        '--continue',
        dest='continue_on_error',
        action='store_true',
        help='Continue processing even if a file fails'
    )
    
    args = parser.parse_args()
    
    try:
        results = extract_thumbnails_from_folder(
            args.folder,
            args.interval,
            args.quality,
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
