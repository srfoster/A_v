#!/usr/bin/env python3
"""
File Thumbnail Extractor
Extracts thumbnails from a single video file at regular intervals.
Outputs thumbnails to a 'thumbs/' folder alongside the input file.

Usage:
    python thumbs.py FILE.mp4
    
Output:
    thumbs/thumb_00-00.png
    thumbs/thumb_00-10.png
    thumbs/thumb_00-20.png
    ...
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Video file extensions
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}


def get_video_duration(video_path):
    """Get the duration of a video file in seconds using ffprobe."""
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
        print("Error: ffprobe not found. Please install ffmpeg.")
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
    print(f"Analyzing video: {video_path.name}")
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
                '-ss', str(timestamp),
                '-i', str(video_path),
                '-frames:v', '1',
                '-q:v', str(quality),
                '-y',
                str(output_file)
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            thumbnails.append(str(output_file))
        
        print(f"Extracted {len(thumbnails)} thumbnails")
        
        return thumbnails
        
    except subprocess.CalledProcessError as e:
        print(f"Error extracting thumbnails: {e.stderr.decode()}")
        raise
    except FileNotFoundError:
        print("Error: ffmpeg not found. Please install ffmpeg.")
        sys.exit(1)


def extract_thumbnails_from_file(input_file, interval=10, quality=2):
    """
    Extract thumbnails from a single file and output to thumbs/ folder alongside it.
    
    Args:
        input_file: Path to input video file
        interval: Interval in seconds between thumbnails
        quality: Image quality (2-31, lower is better)
    
    Returns:
        Dictionary with output information
    """
    input_path = Path(input_file).resolve()
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    print(f"\n{'='*60}")
    print(f"Processing: {input_path.name}")
    print('='*60)
    
    # Check if it's a video file
    file_ext = input_path.suffix.lower()
    if file_ext not in VIDEO_EXTENSIONS:
        print(f"Warning: File extension {file_ext} is not a recognized video format.")
        print("Attempting to process anyway...")
    
    # Create thumbs/ folder alongside the input file
    thumbs_dir = input_path.parent / 'thumbs'
    thumbs_dir.mkdir(exist_ok=True)
    
    # Extract thumbnails
    thumbnails = extract_thumbnails(
        str(input_path),
        str(thumbs_dir),
        interval=interval,
        quality=quality
    )
    
    print(f"\n{'='*60}")
    print("Thumbnail extraction complete!")
    print(f"  Location: {thumbs_dir}")
    print(f"  Count: {len(thumbnails)} images")
    print('='*60)
    
    return {
        'thumbs_dir': str(thumbs_dir),
        'thumbnails': thumbnails,
        'count': len(thumbnails)
    }


def main():
    parser = argparse.ArgumentParser(
        description='Extract thumbnails from a single video file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python thumbs.py video.mp4
  python thumbs.py video.mp4 -i 5
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
    
    args = parser.parse_args()
    
    try:
        extract_thumbnails_from_file(
            args.input_file,
            interval=args.interval,
            quality=args.quality
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
