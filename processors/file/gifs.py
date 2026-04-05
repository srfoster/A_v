#!/usr/bin/env python3
"""
GIF Generator - Single File Processor
Generates an animated GIF from a video file that is 10% of the video's length.

Usage:
    python gifs.py <video_file>

Output:
    - gifs/FILENAME.gif (10% of original video length)
"""

import os
import sys
import subprocess
from pathlib import Path


def get_video_duration(video_path):
    """
    Get the duration of a video file in seconds using ffprobe.
    
    Args:
        video_path: Path to video file
    
    Returns:
        Duration in seconds (float), or None if failed
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(video_path)
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        duration = float(result.stdout.strip())
        return duration
        
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"Error getting video duration: {e}")
        return None


def generate_gif(video_path, output_path, duration=None, fps=10, width=480):
    """
    Generate an animated GIF from a video file.
    
    Uses a two-pass approach with palette generation for better quality.
    
    Args:
        video_path: Path to input video file
        output_path: Path for output GIF file
        duration: Duration of GIF in seconds (default: 10% of video)
        fps: Frames per second for GIF (default: 10)
        width: Width of GIF in pixels (default: 480, maintains aspect ratio)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get video duration if not provided
        if duration is None:
            video_duration = get_video_duration(video_path)
            if video_duration is None:
                print("Failed to determine video duration")
                return False
            
            # Check if video has valid duration
            if video_duration <= 0:
                print(f"Invalid video duration: {video_duration:.1f}s")
                print("The video file may be corrupted or empty")
                return False
            
            # Calculate 10% of video duration
            duration = max(1.0, video_duration * 0.1)  # Minimum 1 second
            print(f"Video duration: {video_duration:.1f}s")
            print(f"GIF duration (10%): {duration:.1f}s")
        
        # Create output directory if it doesn't exist
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate palette for better GIF quality
        palette_path = output_path.parent / 'palette.png'
        
        print(f"Generating color palette...")
        palette_cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-t', str(duration),
            '-vf', f'fps={fps},scale={width}:-1:flags=lanczos,palettegen',
            '-y',
            str(palette_path)
        ]
        
        result = subprocess.run(
            palette_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        
        # Generate GIF using palette
        print(f"Creating GIF ({width}px wide, {fps} fps, {duration:.1f}s)...")
        gif_cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-i', str(palette_path),
            '-t', str(duration),
            '-filter_complex', f'fps={fps},scale={width}:-1:flags=lanczos[x];[x][1:v]paletteuse',
            '-y',
            str(output_path)
        ]
        
        result = subprocess.run(
            gif_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        
        # Clean up palette file
        if palette_path.exists():
            palette_path.unlink()
        
        # Verify output was created
        if not output_path.exists():
            print("GIF file was not created")
            return False
        
        file_size = output_path.stat().st_size / (1024 * 1024)  # MB
        print(f"GIF created: {output_path.name} ({file_size:.2f} MB)")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error creating GIF: {e}")
        if e.stderr:
            print(f"FFmpeg error output:")
            print(e.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def main():
    """Main entry point for single-file GIF generation."""
    if len(sys.argv) < 2:
        print("Usage: python gifs.py <video_file>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)
    
    # Check if file is a video
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
    if video_path.suffix.lower() not in video_extensions:
        print(f"Error: File is not a recognized video format: {video_path.suffix}")
        sys.exit(1)
    
    print(f"Processing: {video_path}")
    
    # Determine output path
    # If video is in a subdirectory (transcripts/logs/etc), go up one level
    known_subdirs = {'transcripts', 'logs', 'thumbs', 'summaries', 'ocr_extractions', 'gifs'}
    parent_dir = video_path.parent
    
    if parent_dir.name in known_subdirs:
        output_dir = parent_dir.parent / 'gifs'
    else:
        output_dir = parent_dir / 'gifs'
    
    output_path = output_dir / f"{video_path.stem}.gif"
    
    # Generate GIF
    success = generate_gif(video_path, output_path)
    
    if success:
        print(f"Success: GIF saved to {output_path}")
        sys.exit(0)
    else:
        print("Failed to generate GIF")
        sys.exit(1)


if __name__ == '__main__':
    main()
