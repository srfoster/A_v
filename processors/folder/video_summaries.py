#!/usr/bin/env python3
"""
Video Summary Generator - Folder Processor
Recursively finds all video files and generates 5-second sped-up summaries.

Usage:
    python video_summaries.py <folder_path> [--continue-on-error]

Output:
    - video_summaries/FILENAME.mp4 for each video (5 seconds, sped up)
    - logs/video_summaries.log with processing details
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime


# Video file extensions to process
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}


def setup_logging(log_dir):
    """
    Set up logging to both file and console.
    
    Args:
        log_dir: Directory to store log file
    
    Returns:
        Logger instance
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / 'video_summaries.log'
    
    # Create logger
    logger = logging.getLogger('video_summaries_processor')
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    logger.handlers = []
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


def find_video_files(folder_path):
    """
    Recursively find all video files in a folder.
    
    Args:
        folder_path: Root folder to search
    
    Returns:
        List of Path objects for video files
    """
    folder_path = Path(folder_path)
    video_files = []
    
    for ext in VIDEO_EXTENSIONS:
        video_files.extend(folder_path.rglob(f'*{ext}'))
    
    return sorted(video_files)


def process_video_file(video_path, folder_root, file_processor_path, logger):
    """
    Process a single video file by calling the file processor.
    
    Args:
        video_path: Path to video file to process
        folder_root: Root folder being processed (for relative path display)
        file_processor_path: Path to the file processor script
        logger: Logger instance
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get relative path for display
        try:
            rel_path = video_path.relative_to(folder_root)
        except ValueError:
            rel_path = video_path
        
        logger.info(f"Processing: {rel_path}")
        
        # Call file processor
        result = subprocess.run(
            ['python', str(file_processor_path), str(video_path)],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Log output from file processor
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    logger.info(f"  {line}")
        
        logger.info(f"Success: {rel_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed: {rel_path}")
        if e.stdout:
            logger.error(f"  Output: {e.stdout}")
        if e.stderr:
            logger.error(f"  Error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error processing {rel_path}: {e}")
        return False


def main():
    """Main entry point for folder video summary generation."""
    if len(sys.argv) < 2:
        print("Usage: python video_summaries.py <folder_path> [--continue-on-error]")
        sys.exit(1)
    
    folder_path = Path(sys.argv[1])
    continue_on_error = '--continue-on-error' in sys.argv
    
    if not folder_path.exists():
        print(f"Error: Folder not found: {folder_path}")
        sys.exit(1)
    
    if not folder_path.is_dir():
        print(f"Error: Not a folder: {folder_path}")
        sys.exit(1)
    
    # Set up logging
    log_dir = folder_path / 'logs'
    logger = setup_logging(log_dir)
    
    logger.info("="*80)
    logger.info("VIDEO SUMMARY GENERATION - FOLDER PROCESSOR")
    logger.info("="*80)
    logger.info(f"Folder: {folder_path}")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Continue on error: {continue_on_error}")
    logger.info("")
    
    # Find all video files
    logger.info("Searching for video files...")
    video_files = find_video_files(folder_path)
    
    if not video_files:
        logger.info("No video files found")
        logger.info("="*80)
        sys.exit(0)
    
    logger.info(f"Found {len(video_files)} video file(s)")
    logger.info("")
    
    # Get path to file processor
    script_dir = Path(__file__).parent.parent  # Go up from folder/ to processors/
    file_processor_path = script_dir / 'file' / 'video_summaries.py'
    
    if not file_processor_path.exists():
        logger.error(f"File processor not found: {file_processor_path}")
        sys.exit(1)
    
    # Process each video file
    success_count = 0
    failure_count = 0
    
    for i, video_path in enumerate(video_files, 1):
        logger.info(f"[{i}/{len(video_files)}] " + "-"*60)
        
        success = process_video_file(video_path, folder_path, file_processor_path, logger)
        
        if success:
            success_count += 1
        else:
            failure_count += 1
            if not continue_on_error:
                logger.error("Stopping due to error (use --continue-on-error to continue)")
                break
        
        logger.info("")
    
    # Summary
    logger.info("="*80)
    logger.info("PROCESSING COMPLETE")
    logger.info("="*80)
    logger.info(f"Total videos: {len(video_files)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {failure_count}")
    logger.info(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    # Exit with appropriate code
    if failure_count > 0 and not continue_on_error:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
