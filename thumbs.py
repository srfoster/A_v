#!/usr/bin/env python3
"""
Video Thumbnail Extractor
Extracts thumbnails from video files at regular intervals.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


# Video file extensions
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}


def get_video_duration(video_path):
    """
    Get the duration of a video file in seconds using ffprobe.
    
    Args:
        video_path: Path to video file
    
    Returns:
        Duration in seconds (float)
    """
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        duration = float(result.stdout.strip())
        return duration
    except subprocess.CalledProcessError as e:
        print(f"Error getting video duration: {e.stderr}")
        raise
    except FileNotFoundError:
        print("Error: ffprobe not found. Please install ffmpeg:")
        print("  Windows: choco install ffmpeg  or  download from https://ffmpeg.org/")
        print("  Mac: brew install ffmpeg")
        print("  Linux: apt-get install ffmpeg  or  yum install ffmpeg")
        sys.exit(1)
    except ValueError:
        print(f"Error: Could not parse duration from video")
        raise


def extract_thumbnails(video_path, output_dir, interval=10, quality=2):
    """
    Extract thumbnails from video at regular intervals.
    
    Args:
        video_path: Path to video file
        output_dir: Directory to save thumbnails
        interval: Interval in seconds between thumbnails (default: 10)
        quality: JPEG quality 2-31, lower is better (default: 2)
    
    Returns:
        List of thumbnail file paths
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Get video duration
    print(f"Analyzing video: {video_path}")
    duration = get_video_duration(str(video_path))
    print(f"Video duration: {duration:.2f} seconds")
    
    # Calculate timestamps for thumbnails
    timestamps = []
    current = 0
    while current <= duration:
        timestamps.append(current)
        current += interval
    
    print(f"Extracting {len(timestamps)} thumbnails (1 every {interval} seconds)...")
    
    thumbnails = []
    
    try:
        for timestamp in timestamps:
            # Format timestamp for filename (e.g., 00-00, 00-10, 01-30)
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)
            time_str = f"{minutes:02d}-{seconds:02d}"
            
            output_file = output_dir / f"thumb_{time_str}.png"
            
            # Extract single frame at specific timestamp
            cmd = [
                'ffmpeg',
                '-ss', str(timestamp),  # Seek to timestamp
                '-i', str(video_path),
                '-frames:v', '1',  # Extract 1 frame
                '-q:v', str(quality),  # Quality setting
                '-y',  # Overwrite output files
                str(output_file)
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            thumbnails.append(str(output_file))
            print(f"  Extracted: {output_file.name} (at {timestamp:.1f}s)")
        
        print(f"\n{'='*60}")
        print(f"Successfully extracted {len(thumbnails)} thumbnails to:")
        print(f"  {output_dir}")
        print('='*60)
        
        return thumbnails
        
    except subprocess.CalledProcessError as e:
        print(f"Error extracting thumbnails: {e.stderr.decode()}")
        raise
    except FileNotFoundError:
        print("Error: ffmpeg not found. Please install ffmpeg:")
        print("  Windows: choco install ffmpeg  or  download from https://ffmpeg.org/")
        print("  Mac: brew install ffmpeg")
        print("  Linux: apt-get install ffmpeg  or  yum install ffmpeg")
        sys.exit(1)


def extract_thumbnails_from_file(input_file, interval=10, quality=2, output_dir=None):
    """
    Main thumbnail extraction workflow.
    
    Args:
        input_file: Path to input video file
        interval: Interval in seconds between thumbnails
        quality: Image quality (2-31, lower is better)
        output_dir: Optional output directory (default: directory named after input file)
    
    Returns:
        List of thumbnail file paths
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Check if it's a video file
    file_ext = input_path.suffix.lower()
    if file_ext not in VIDEO_EXTENSIONS:
        print(f"Warning: File extension {file_ext} is not a recognized video format.")
        print("Attempting to process anyway...")
    
    # Determine output directory
    if output_dir:
        output_dir = Path(output_dir)
    else:
        # Create directory named after input file in the same directory
        output_dir = input_path.parent / input_path.stem
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract thumbnails
    thumbnails = extract_thumbnails(
        str(input_path),
        str(output_dir),
        interval=interval,
        quality=quality
    )
    
    return thumbnails


def main():
    parser = argparse.ArgumentParser(
        description='Extract thumbnails from video files at regular intervals',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract thumbnails every 10 seconds (default)
  python thumbs.py video.mp4
  
  # Extract thumbnails every 5 seconds
  python thumbs.py video.mp4 -i 5
  
  # Extract thumbnails every 30 seconds
  python thumbs.py video.mp4 -i 30
  
  # Custom output directory
  python thumbs.py video.mp4 -o ./my_thumbnails
  
  # Higher quality thumbnails (lower number = better quality)
  python thumbs.py video.mp4 -q 1
        """
    )
    parser.add_argument(
        'input_file',
        help='Path to input video file'
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
        '-o', '--output-dir',
        help='Output directory for thumbnails (default: directory named after input file)'
    )
    
    args = parser.parse_args()
    
    try:
        extract_thumbnails_from_file(
            args.input_file,
            interval=args.interval,
            quality=args.quality,
            output_dir=args.output_dir
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
