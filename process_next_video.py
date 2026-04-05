#!/usr/bin/env python3
"""
Process Next Video Script
Automatically finds and processes the next unprocessed video folder in S:\Videos\Raw\

A folder is considered processed if it contains a logs/ directory.
Runs folder processors in order: transcripts -> thumbs -> ocr_extractions -> gifs -> summaries
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime


def find_unprocessed_folders(base_dir='S:/Videos/Raw'):
    """
    Find all video folders that haven't been processed.
    
    Recursively searches for folders containing video files (e.g., S:/Videos/Raw/2026-04-05/10-24-15/).
    A folder is considered processed if it contains a logs/ subdirectory.
    Only returns "leaf" folders (folders with videos, not their parents).
    
    Args:
        base_dir: Base directory to search (default: S:/Videos/Raw)
    
    Returns:
        List of Path objects for unprocessed video folders, sorted by path
    """
    base_path = Path(base_dir)
    
    if not base_path.exists():
        print(f"Error: Base directory not found: {base_dir}")
        return []
    
    # Recursively find all subdirectories at any depth
    all_folders = [d for d in base_path.rglob('*') if d.is_dir()]
    
    # Filter to video folders that don't have logs/ (unprocessed)
    video_folders = []
    for folder in all_folders:
        logs_dir = folder / 'logs'
        if not logs_dir.exists():
            # Check if this folder directly contains video files
            video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
            try:
                has_video = any(f.suffix.lower() in video_extensions for f in folder.iterdir() if f.is_file())
                
                if has_video:
                    video_folders.append(folder)
            except (PermissionError, OSError):
                # Skip folders we can't read
                continue
    
    # Filter to only "leaf" folders - folders that don't have child video folders
    # This prevents processing both "2026-04-03" and "2026-04-03/10-24-15"
    leaf_folders = []
    for folder in video_folders:
        # Check if any other video folder is a child of this one
        is_parent = any(other != folder and other.is_relative_to(folder) for other in video_folders)
        
        if not is_parent:
            leaf_folders.append(folder)
    
    return sorted(leaf_folders)


def run_processor(processor_name, folder_path, script_dir):
    """
    Run a folder processor on a directory.
    
    Args:
        processor_name: Name of the processor (e.g., 'transcripts', 'thumbs')
        folder_path: Path to folder to process
        script_dir: Path to transcriptions directory
    
    Returns:
        True if successful, False otherwise
    """
    processor_path = script_dir / 'processors' / 'folder' / f'{processor_name}.py'
    
    if not processor_path.exists():
        print(f"Error: Processor not found: {processor_path}")
        return False
    
    print(f"\n{'='*80}")
    print(f"Running {processor_name.upper()} processor...")
    print('='*80)
    
    try:
        result = subprocess.run(
            ['python', str(processor_path), str(folder_path), '--continue-on-error'],
            check=True
        )
        print(f"Success: {processor_name} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Warning: {processor_name} failed (continuing anyway)")
        return False


def process_folder(folder_path):
    """
    Process a video folder through the complete pipeline using folder processors.
    
    Args:
        folder_path: Path to folder containing video files
    
    Returns:
        True if successful, False otherwise
    """
    folder_path = Path(folder_path)
    
    if not folder_path.exists():
        print(f"Error: Folder not found: {folder_path}")
        return False
    
    print(f"\n{'='*80}")
    print(f"PROCESSING FOLDER: {folder_path.name}")
    print('='*80)
    print(f"Full path: {folder_path}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get script directory
    script_dir = Path(__file__).parent.resolve()
    
    # Pipeline order: transcripts -> thumbs -> ocr_extractions -> gifs -> summaries
    processors = ['transcripts', 'thumbs', 'ocr_extractions', 'gifs', 'summaries']
    
    print(f"\nPipeline: {' -> '.join(processors)}")
    print()
    
    results = {}
    for processor in processors:
        success = run_processor(processor, folder_path, script_dir)
        results[processor] = success
    
    # Show summary
    print(f"\n{'='*80}")
    print("PROCESSING COMPLETE")
    print('='*80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nResults:")
    for processor, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        print(f"  {processor:20s}: {status}")
    
    return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Automatically find and process the next unprocessed folder in S:\\Videos\\Raw\\',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
A folder is considered processed if it contains a logs/ subdirectory.
This script processes folders containing video files using the folder processors.

Examples:
  # Process the next unprocessed folder
  python process_next_video.py
  
  # Search in a different directory
  python process_next_video.py -d D:\\MyVideos
  
  # List all unprocessed folders
  python process_next_video.py --list
        """
    )
    
    parser.add_argument(
        '-d', '--directory',
        default='S:/Videos/Raw',
        help='Base directory to search for videos (default: S:/Videos/Raw)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all unprocessed folders and exit (don\'t process anything)'
    )
    
    args = parser.parse_args()
    
    try:
        # Find unprocessed folders
        print(f"Scanning for unprocessed folders in {args.directory}...")
        unprocessed = find_unprocessed_folders(args.directory)
        
        if not unprocessed:
            print("\nNo unprocessed folders found!")
            print("All folders have been processed.")
            sys.exit(0)
        
        print(f"\nFound {len(unprocessed)} unprocessed folder(s)")
        
        # If --list flag, just show them and exit
        if args.list:
            print("\nUnprocessed folders:")
            for i, folder in enumerate(unprocessed, 1):
                print(f"  {i}. {folder}")
            sys.exit(0)
        
        # Process the first unprocessed folder
        next_folder = unprocessed[0]
        
        print(f"\n{'='*80}")
        print(f"Processing folder 1 of {len(unprocessed)} unprocessed:")
        print(f"  {next_folder}")
        print('='*80)
        
        success = process_folder(next_folder)
        
        if success:
            remaining = len(unprocessed) - 1
            if remaining > 0:
                print(f"\nProcessing complete! {remaining} folder(s) remaining.")
            else:
                print(f"\nProcessing complete! All folders processed.")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
