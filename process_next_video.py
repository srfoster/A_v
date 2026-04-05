#!/usr/bin/env python3
"""
Process Next Video Script
Automatically finds and processes the next unprocessed MP4 file in S:\Videos\Raw\

Runs the complete video processing pipeline:
1. Transcribes audio with Whisper (generates SRT and TXT)
2. Extracts thumbnail images at intervals
3. Performs OCR on thumbnails to extract text
4. Creates a SUMMARY.txt file to mark the video as processed
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime


def find_unprocessed_videos(base_dir='S:/Videos/Raw'):
    """
    Find all MP4 files in the Videos/Raw directory that haven't been processed.
    
    A video is considered processed if it has a directory with the same name
    containing a SUMMARY.txt file.
    
    Args:
        base_dir: Base directory to search (default: S:/Videos/Raw)
    
    Returns:
        List of Path objects for unprocessed MP4 files
    """
    base_path = Path(base_dir)
    
    if not base_path.exists():
        print(f"Error: Base directory not found: {base_dir}")
        return []
    
    # Find all MP4 files recursively
    all_videos = sorted(base_path.rglob('*.mp4'))
    
    unprocessed = []
    for video in all_videos:
        # Expected output directory (same parent, named after video stem)
        output_dir = video.parent / video.stem
        summary_file = output_dir / 'SUMMARY.txt'
        
        # Check if summary file exists
        if not summary_file.exists():
            unprocessed.append(video)
    
    return unprocessed


def run_command(cmd, description, shell=False):
    """
    Run a command and print status.
    
    Args:
        cmd: Command to run (list or string)
        description: Description of what the command does
        shell: Whether to run in shell
    
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"{description}...")
    print('='*60)
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        print(result.stdout)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed:")
        print(e.stdout)
        return False


def process_video(video_path, model='base', interval=10, skip_ocr=False):
    """
    Process a video file through the complete pipeline.
    
    Args:
        video_path: Path to video file
        model: Whisper model to use (default: base)
        interval: Thumbnail interval in seconds (default: 10)
        skip_ocr: Skip OCR processing (default: False)
    
    Returns:
        True if all steps succeeded, False otherwise
    """
    video_path = Path(video_path)
    
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        return False
    
    print(f"\nProcessing video: {video_path}")
    print(f"Whisper model: {model}")
    print(f"Thumbnail interval: {interval} seconds")
    
    # Determine output directory (same parent as video, named after video)
    output_dir = video_path.parent / video_path.stem
    
    # Get script directory for running commands
    script_dir = Path(__file__).parent.resolve()
    
    # Step 1: Transcribe audio
    transcribe_cmd = [
        'python', str(script_dir / 'transcribe.py'),
        str(video_path),
        '-m', model
    ]
    
    if not run_command(transcribe_cmd, "Transcribing audio"):
        print("\n⚠ Transcription failed, continuing with thumbnails...")
    
    # Step 2: Extract thumbnails
    thumbs_cmd = [
        'python', str(script_dir / 'thumbs.py'),
        str(video_path),
        '-i', str(interval)
    ]
    
    if not run_command(thumbs_cmd, "Extracting thumbnails"):
        print("\n⚠ Thumbnail extraction failed, skipping OCR")
        return False
    
    # Step 3: OCR on thumbnails
    # Use the batch wrapper to handle DLL paths
    thumbs_dir = output_dir
    
    if not thumbs_dir.exists():
        print(f"\n⚠ Thumbnails directory not found: {thumbs_dir}")
        print("Skipping OCR step")
        return False
    
    # Count PNG files
    png_files = list(thumbs_dir.glob('*.png'))
    if not png_files:
        print(f"\n⚠ No PNG files found in {thumbs_dir}")
        print("Skipping OCR step")
        return False
    
    print(f"\nFound {len(png_files)} thumbnail(s) for OCR processing")
    
    # Skip OCR if requested
    if skip_ocr:
        print("\n⚠ OCR skipped (--skip-ocr flag set)")
        ocr_success = True  # Mark as successful so we continue
    else:
        # Run OCR using the batch wrapper (Windows) or direct python (Unix)
        ocr_success = False
    if sys.platform == 'win32':
        # Use batch file wrapper on Windows to handle DLL paths
        # Must run from the script directory where the batch file is located
        script_dir = Path(__file__).parent.resolve()
        ocr_cmd = f'cd /d "{script_dir}" && run_text_extract.bat "{thumbs_dir}"'
        ocr_success = run_command(ocr_cmd, "Performing OCR on thumbnails", shell=True)
    else:
        # Direct python call on Unix
        ocr_cmd = ['python', 'text_extract.py', str(thumbs_dir)]
        ocr_success = run_command(ocr_cmd, "Performing OCR on thumbnails")
    
    if not ocr_success:
        print("\n⚠ OCR failed - continuing anyway to create summary")
    
    # Step 4: Create summary file
    summary_file = output_dir / 'SUMMARY.txt'
    
    try:
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"Video Processing Summary\n")
            f.write(f"{'='*60}\n\n")
            f.write(f"Video File: {video_path.name}\n")
            f.write(f"Full Path: {video_path}\n")
            f.write(f"Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Video file info
            file_size = video_path.stat().st_size
            size_mb = file_size / (1024 * 1024)
            f.write(f"Video Size: {size_mb:.2f} MB\n")
            
            f.write(f"\nProcessing Settings:\n")
            f.write(f"  Whisper Model: {model}\n")
            f.write(f"  Thumbnail Interval: {interval} seconds\n")
            
            f.write(f"\nOutput Directory: {output_dir}\n\n")
            
            # Count generated files
            srt_files = list(output_dir.glob('*.srt'))
            txt_files = [f for f in output_dir.glob('*.txt') if f.name != 'SUMMARY.txt']
            png_files = list(output_dir.glob('*.png'))
            json_files = list(output_dir.glob('*.json'))
            
            f.write(f"{'='*60}\n")
            f.write(f"Generated Files:\n")
            f.write(f"{'='*60}\n")
            f.write(f"  Subtitle files (SRT): {len(srt_files)}\n")
            f.write(f"  Transcript files (TXT): {len(txt_files)}\n")
            f.write(f"  Thumbnail images (PNG): {len(png_files)}\n")
            f.write(f"  OCR data (JSON): {len(json_files)}\n")
            
            # List actual files
            if srt_files:
                f.write(f"\n  SRT Files:\n")
                for srt in sorted(srt_files):
                    f.write(f"    - {srt.name}\n")
            
            if txt_files:
                f.write(f"\n  TXT Files:\n")
                for txt in sorted(txt_files):
                    f.write(f"    - {txt.name}\n")
            
            # Read and include transcript preview
            f.write(f"\n{'='*60}\n")
            f.write(f"Transcription Preview:\n")
            f.write(f"{'='*60}\n")
            
            transcript_found = False
            for txt_file in txt_files:
                if txt_file.exists():
                    try:
                        content = txt_file.read_text(encoding='utf-8')
                        preview = content[:500] if len(content) > 500 else content
                        f.write(f"\nFrom {txt_file.name}:\n")
                        f.write(f"{preview}\n")
                        if len(content) > 500:
                            f.write(f"... ({len(content) - 500} more characters)\n")
                        f.write(f"\nTotal transcript length: {len(content)} characters\n")
                        f.write(f"Word count: ~{len(content.split())} words\n")
                        transcript_found = True
                        break
                    except Exception as e:
                        f.write(f"(Could not read transcript: {e})\n")
            
            if not transcript_found:
                f.write("(No transcript generated)\n")
            
            # Read and include OCR results
            f.write(f"\n{'='*60}\n")
            f.write(f"OCR Results Summary:\n")
            f.write(f"{'='*60}\n")
            
            ocr_json = output_dir / 'ocr_results.json'
            if ocr_json.exists():
                try:
                    with open(ocr_json, 'r', encoding='utf-8') as ocr_file:
                        ocr_data = json.load(ocr_file)
                    
                    total_regions = sum(len(regions) for regions in ocr_data.values())
                    images_with_text = sum(1 for regions in ocr_data.values() if regions)
                    
                    f.write(f"\nTotal text regions detected: {total_regions}\n")
                    f.write(f"Images with text: {images_with_text} / {len(ocr_data)}\n")
                    
                    # Collect all text with confidence scores
                    all_texts = []
                    for img_name, regions in ocr_data.items():
                        for region in regions:
                            all_texts.append({
                                'text': region.get('text', ''),
                                'confidence': region.get('confidence', 0),
                                'image': img_name
                            })
                    
                    if all_texts:
                        # Sort by confidence
                        all_texts.sort(key=lambda x: x['confidence'], reverse=True)
                        
                        # Calculate statistics
                        avg_conf = sum(t['confidence'] for t in all_texts) / len(all_texts)
                        high_conf = [t for t in all_texts if t['confidence'] > 0.7]
                        
                        f.write(f"Average confidence: {avg_conf:.2%}\n")
                        f.write(f"High confidence detections (>70%): {len(high_conf)}\n")
                        
                        # Show top detections
                        f.write(f"\nTop 10 highest confidence detections:\n")
                        for i, item in enumerate(all_texts[:10], 1):
                            f.write(f"  {i}. '{item['text']}' - {item['confidence']:.2%} ({item['image']})\n")
                        
                        # Show unique text found
                        unique_texts = set(t['text'].strip().lower() for t in all_texts if t['text'].strip())
                        f.write(f"\nUnique text elements found: {len(unique_texts)}\n")
                        
                        if len(unique_texts) > 0:
                            sample_texts = sorted(unique_texts)[:20]
                            f.write(f"\nSample of detected text:\n")
                            for text in sample_texts:
                                f.write(f"  - {text}\n")
                            if len(unique_texts) > 20:
                                f.write(f"  ... and {len(unique_texts) - 20} more\n")
                    else:
                        f.write("\n(No text detected in images)\n")
                        
                except Exception as e:
                    f.write(f"\n(Could not read OCR results: {e})\n")
            else:
                f.write("\n(No OCR results file found)\n")
            
            # Add footer
            f.write(f"\n{'='*60}\n")
            f.write(f"Processing complete!\n")
            f.write(f"{'='*60}\n")
            
        print(f"\n✓ Summary file created: {summary_file}")
        
    except Exception as e:
        print(f"\n⚠ Failed to create summary file: {e}")
        return False
    
    print(f"\n{'='*60}")
    print("✓ Video processing complete!")
    print('='*60)
    print(f"\nOutput directory: {output_dir}")
    print("\nGenerated files:")
    print("  - *.srt (subtitles)")
    print("  - *.txt (transcript)")
    print("  - thumb_*.png (thumbnails)")
    print("  - thumb_*.txt (OCR text from thumbnails)")
    print("  - SUMMARY.txt (processing summary)")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Automatically find and process the next unprocessed MP4 in S:\\Videos\\Raw\\',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script scans S:\\Videos\\Raw\\ for MP4 files that haven't been processed yet.
A video is considered processed if it has a SUMMARY.txt file in its output folder.

Examples:
  # Process the next unprocessed video with default settings
  python process_next_video.py
  
  # Use a different Whisper model
  python process_next_video.py -m medium
  
  # Extract thumbnails every 5 seconds
  python process_next_video.py -i 5
  
  # Search in a different directory
  python process_next_video.py -d D:\\MyVideos
        """
    )
    
    parser.add_argument(
        '-d', '--directory',
        default='S:/Videos/Raw',
        help='Base directory to search for videos (default: S:/Videos/Raw)'
    )
    parser.add_argument(
        '-m', '--model',
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model size (default: base)'
    )
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=10,
        help='Thumbnail extraction interval in seconds (default: 10)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all unprocessed videos and exit (don\'t process anything)'
    )
    parser.add_argument(
        '--skip-ocr',
        action='store_true',
        help='Skip OCR processing (only transcribe and extract thumbnails)'
    )
    
    args = parser.parse_args()
    
    try:
        # Find unprocessed videos
        print(f"Scanning for unprocessed MP4 files in {args.directory}...")
        unprocessed = find_unprocessed_videos(args.directory)
        
        if not unprocessed:
            print("\n✓ No unprocessed videos found!")
            print("All MP4 files have been processed.")
            sys.exit(0)
        
        print(f"\nFound {len(unprocessed)} unprocessed video(s)")
        
        # If --list flag, just show them and exit
        if args.list:
            print("\nUnprocessed videos:")
            for i, video in enumerate(unprocessed, 1):
                print(f"  {i}. {video}")
            sys.exit(0)
        
        # Process the first unprocessed video
        next_video = unprocessed[0]
        
        print(f"\n{'='*60}")
        print(f"Processing next video ({1} of {len(unprocessed)} unprocessed):")
        print(f"  {next_video}")
        print('='*60)
        
        success = process_video(next_video, args.model, args.interval, args.skip_ocr)
        
        if success:
            remaining = len(unprocessed) - 1
            if remaining > 0:
                print(f"\n✓ Processing complete! {remaining} video(s) remaining.")
            else:
                print(f"\n✓ Processing complete! All videos processed.")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
