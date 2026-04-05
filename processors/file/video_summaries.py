#!/usr/bin/env python3
"""
Video Summary Generator - Single File Processor
Generates a 5-second sped-up summary of the entire video.

Usage:
    python video_summaries.py <video_file>

Output:
    - video_summaries/FILENAME.mp4 (5 seconds, sped up, scaled to 480p)
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


def generate_video_summary(video_path, output_path, target_duration=5.0, width=480):
    """
    Generate a short video summary from a video file.
    
    Speeds up the entire video to fit into target duration (default 5 seconds).
    
    Args:
        video_path: Path to input video file
        output_path: Path for output video file
        target_duration: Target duration in seconds (default: 5.0)
        width: Width of video in pixels (default: 480, maintains aspect ratio)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get video duration
        video_duration = get_video_duration(video_path)
        if video_duration is None:
            print("Failed to determine video duration")
            return False
        
        # Check if video has valid duration
        if video_duration <= 0:
            print(f"Invalid video duration: {video_duration:.1f}s")
            print("The video file may be corrupted or empty")
            return False
        
        # Calculate speedup factor
        speedup_factor = video_duration / target_duration
        
        print(f"Video duration: {video_duration:.1f}s")
        print(f"Target duration: {target_duration:.1f}s")
        print(f"Speedup factor: {speedup_factor:.2f}x")
        
        # Create output directory if it doesn't exist
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate video summary with speedup
        print(f"Creating sped-up video summary ({width}px wide)...")
        
        # For audio, atempo filter is limited to 0.5-2.0 range
        # For high speedup factors, we'll drop audio to keep it simple
        if speedup_factor <= 2.0:
            # Can preserve audio with atempo
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-vf', f'setpts=PTS/{speedup_factor},scale={width}:-2',
                '-af', f'atempo={speedup_factor}',
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '28',
                '-c:a', 'aac',
                '-b:a', '96k',
                '-y',
                str(output_path)
            ]
        else:
            # Drop audio for high speedup factors
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-vf', f'setpts=PTS/{speedup_factor},scale={width}:-2',
                '-an',  # No audio
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '28',
                '-y',
                str(output_path)
            ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        
        # Verify output was created
        if not output_path.exists():
            print("Video summary file was not created")
            return False
        
        file_size = output_path.stat().st_size / (1024 * 1024)  # MB
        print(f"Video summary created: {output_path.name} ({file_size:.2f} MB)")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error creating video summary: {e}")
        if e.stderr:
            print(f"FFmpeg error output:")
            print(e.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def main():
    """Main entry point for single-file video summary generation."""
    if len(sys.argv) < 2:
        print("Usage: python video_summaries.py <video_file>")
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
    known_subdirs = {'transcripts', 'logs', 'thumbs', 'summaries', 'ocr_extractions', 'gifs', 'video_summaries'}
    parent_dir = video_path.parent
    
    if parent_dir.name in known_subdirs:
        output_dir = parent_dir.parent / 'video_summaries'
    else:
        output_dir = parent_dir / 'video_summaries'
    
    output_path = output_dir / f"{video_path.stem}.mp4"
    
    # Generate video summary
    success = generate_video_summary(video_path, output_path)
    
    if success:
        print(f"Success: Video summary saved to {output_path}")
        sys.exit(0)
    else:
        print("Failed to generate video summary")
        sys.exit(1)


if __name__ == '__main__':
    main()
