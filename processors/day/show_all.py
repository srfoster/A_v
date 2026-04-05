#!/usr/bin/env python3
"""
Day Show All Processor
Creates a day-level index page that links to all video show_all pages.
Processes a day folder (e.g., 2026-04-04) containing timestamped subfolders.

Usage:
    python show_all.py DAY_FOLDER/
    
Output:
    DAY_FOLDER/show_all/index.html
      
The HTML page displays a list of all videos in subfolders with links to their
individual show_all pages and summary snippets.
"""

import sys
import argparse
from pathlib import Path
import logging
from datetime import datetime
import re


def setup_logging(folder_path):
    """Set up logging to logs/day_show_all.log in the target folder."""
    folder = Path(folder_path)
    logs_dir = folder / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / 'day_show_all.log'
    
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
    logger.info(f"Day show all session started")
    logger.info(f"Target folder: {folder}")
    logger.info("="*60)
    
    return logger


def format_folder_timestamp(folder_name):
    """
    Parse folder name as timestamp and format it nicely.
    
    Expected formats:
    - YYYY-MM-DD_HH-MM-SS
    - HH-MM-SS
    - YYYY-MM-DDTHH-MM-SS
    
    Returns formatted string like "2:30 PM" or original if can't parse.
    """
    # Try to parse time patterns
    # Pattern 1: Full datetime with underscore (2024-04-04_14-30-00)
    match = re.match(r'(\d{4})-(\d{2})-(\d{2})[_T](\d{2})-(\d{2})-(\d{2})', folder_name)
    if match:
        year, month, day, hour, minute, second = match.groups()
        try:
            dt = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
            return dt.strftime('%I:%M %p').lstrip('0')  # e.g., "2:30 PM"
        except ValueError:
            pass
    
    # Pattern 2: Just time (14-30-00)
    match = re.match(r'(\d{2})-(\d{2})-(\d{2})', folder_name)
    if match:
        hour, minute, second = match.groups()
        try:
            dt = datetime(2000, 1, 1, int(hour), int(minute), int(second))
            return dt.strftime('%I:%M %p').lstrip('0')  # e.g., "2:30 PM"
        except ValueError:
            pass
    
    # If can't parse, return original
    return folder_name


def find_video_folders(day_folder):
    """
    Find all subfolders that contain a show_all/index.html file.
    
    Returns list of tuples: (subfolder_path, show_all_exists, video_file)
    """
    # Video extensions to look for
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}
    
    subfolders = []
    
    for item in sorted(day_folder.iterdir()):
        if item.is_dir() and not item.name.startswith('.') and item.name not in ['logs', 'show_all', 'summaries']:
            show_all_index = item / 'show_all' / 'index.html'
            
            # Find first video file in subfolder
            video_file = None
            for ext in VIDEO_EXTENSIONS:
                video_files = list(item.glob(f'*{ext}'))
                if video_files:
                    video_file = video_files[0]
                    break
            
            subfolders.append((item, show_all_index.exists(), video_file))
    
    return subfolders


def read_first_summary(folder):
    """Read the first summary file in a folder and return a snippet."""
    summaries_dir = folder / 'summaries'
    if not summaries_dir.exists():
        return None
    
    summary_files = sorted(summaries_dir.glob('*_summary.txt'))
    if not summary_files:
        return None
    
    try:
        with open(summary_files[0], 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # Return first 200 characters as snippet
            if len(content) > 200:
                return content[:200] + '...'
            return content
    except Exception:
        return None


def read_day_summary(day_folder):
    """Read the day summary file if it exists."""
    summary_file = day_folder / 'summaries' / 'day_summary.txt'
    if not summary_file.exists():
        return None
    
    try:
        with open(summary_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return None


def generate_html(day_folder, video_folders):
    """Generate the day-level index HTML page."""
    
    day_name = day_folder.name
    
    # Read day summary if it exists
    day_summary = read_day_summary(day_folder)
    
    # Build video list HTML
    videos_html = ""
    for subfolder, has_show_all, video_file in video_folders:
        folder_name = subfolder.name
        display_name = format_folder_timestamp(folder_name)
        
        # Read summary snippet
        summary_snippet = read_first_summary(subfolder)
        
        # Get relative path to video
        video_rel_path = None
        if video_file:
            video_rel_path = f"../{folder_name}/{video_file.name}"
        
        if has_show_all:
            link_path = f"../{folder_name}/show_all/index.html"
            videos_html += f'''
        <li class="video-item">
            <div class="video-content">
'''
            if video_rel_path:
                videos_html += f'''
                <div class="video-preview">
                    <video src="{video_rel_path}" controls preload="metadata"></video>
                </div>
'''
            videos_html += f'''
                <div class="video-info">
                    <a href="{link_path}" class="video-link">
                        <div class="video-header">
                            <span class="icon">🎬</span>
                            <span class="video-name">{display_name}</span>
                        </div>
                    </a>
'''
            if summary_snippet:
                videos_html += f'''
                    <div class="video-summary">{summary_snippet}</div>
'''
            videos_html += '''
                </div>
            </div>
        </li>
'''
        else:
            # No show_all page exists
            videos_html += f'''
        <li class="video-item no-link">
            <div class="video-content">
'''
            if video_rel_path:
                videos_html += f'''
                <div class="video-preview">
                    <video src="{video_rel_path}" controls preload="metadata"></video>
                </div>
'''
            videos_html += f'''
                <div class="video-info">
                    <div class="video-header">
                        <span class="icon">📁</span>
                        <span class="video-name">{display_name}</span>
                        <span class="status">(not processed)</span>
                    </div>
'''
            if summary_snippet:
                videos_html += f'''
                    <div class="video-summary">{summary_snippet}</div>
'''
            videos_html += '''
                </div>
            </div>
        </li>
'''
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{day_name} - Videos</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 40px 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        
        .page-header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #3e3e42;
        }}
        
        .page-header h1 {{
            color: #ffffff;
            font-size: 36px;
            margin-bottom: 10px;
        }}
        
        .page-header .subtitle {{
            color: #858585;
            font-size: 16px;
        }}
        
        .video-list {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        
        .video-item {{
            background: #252526;
            border-radius: 8px;
            padding: 20px;
            transition: all 0.2s;
        }}
        
        .video-item:has(.video-link) {{
            border-left: 4px solid #0e639c;
        }}
        
        .video-item.no-link {{
            border-left: 4px solid #3e3e42;
            opacity: 0.7;
        }}
        
        .video-item:hover {{
            background: #2a2d2e;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }}
        
        .video-content {{
            display: flex;
            gap: 20px;
            align-items: flex-start;
        }}
        
        .video-preview {{
            flex-shrink: 0;
            width: 240px;
            background: #000;
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .video-preview video {{
            width: 100%;
            display: block;
        }}
        
        .video-info {{
            flex: 1;
            min-width: 0;
        }}
        
        .video-link {{
            text-decoration: none;
            color: inherit;
            display: block;
            margin-bottom: 12px;
        }}
        
        .video-link:hover .video-name {{
            color: #1177bb;
        }}
        
        .video-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }}
        
        .icon {{
            font-size: 24px;
        }}
        
        .video-name {{
            color: #ffffff;
            font-size: 18px;
            font-weight: 500;
            flex: 1;
        }}
        
        .status {{
            color: #858585;
            font-size: 14px;
            font-style: italic;
        }}
        
        .video-summary {{
            color: #d4d4d4;
            font-size: 14px;
            line-height: 1.6;
            white-space: pre-wrap;
        }}
        
        @media (max-width: 768px) {{
            .video-content {{
                flex-direction: column;
            }}
            
            .video-preview {{
                width: 100%;
            }}
        }}
        
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #858585;
            background: #252526;
            border-radius: 8px;
        }}
        
        .empty-state-icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        
        .stats {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            background: #252526;
            border-radius: 8px;
            color: #858585;
            font-size: 14px;
        }}
        
        .day-summary {{
            background: #2d2d30;
            border-left: 4px solid #0e639c;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 30px;
        }}
        
        .day-summary-header {{
            color: #ffffff;
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .day-summary-content {{
            color: #d4d4d4;
            font-size: 15px;
            line-height: 1.7;
            white-space: pre-wrap;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="page-header">
            <h1>📅 {day_name}</h1>
            <p class="subtitle">Video Collection</p>
        </div>
        
        {f'''<div class="day-summary">
            <div class="day-summary-header">
                <span>📝</span>
                <span>Day Summary</span>
            </div>
            <div class="day-summary-content">{day_summary}</div>
        </div>''' if day_summary else ''}
        
        {"<ul class='video-list'>" + videos_html + "</ul>" if video_folders else '''
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <h2>No Videos Found</h2>
            <p>No subfolders found in this day folder.</p>
        </div>
        '''}
        
        <div class="stats">
            {len([vf for vf in video_folders if vf[1]])} of {len(video_folders)} videos processed
        </div>
    </div>
</body>
</html>
"""
    
    return html_content


def process_folder(folder_path, logger=None):
    """
    Process day folder and create index page.
    
    Args:
        folder_path: Path to the day folder
        logger: Logger instance
    
    Returns:
        True if successful, False otherwise
    """
    folder = Path(folder_path)
    
    # Find all video subfolders
    video_folders = find_video_folders(folder)
    
    if logger:
        total_folders = len(video_folders)
        processed_folders = len([vf for vf in video_folders if vf[1]])
        videos_with_files = len([vf for vf in video_folders if vf[2] is not None])
        logger.info(f"Found {total_folders} subfolder(s)")
        logger.info(f"{processed_folders} have show_all/index.html")
        logger.info(f"{videos_with_files} have video files")
    
    # Create output directory
    output_dir = folder / 'show_all'
    output_dir.mkdir(exist_ok=True)
    
    # Generate HTML
    try:
        html_content = generate_html(folder, video_folders)
        output_file = output_dir / 'index.html'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        if logger:
            logger.info(f"Created: {output_file.name}")
        
        return True
        
    except Exception as e:
        error_msg = f"Error generating day index page: {str(e)}"
        if logger:
            logger.error(error_msg)
        print(error_msg)
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Create a day-level index page linking to all video show_all pages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python show_all.py s:\\Videos\\Raw\\2026-04-04
  python show_all.py /path/to/day/folder/

The processor will look for subfolders containing show_all/index.html files
and create a day-level index with links and summary snippets.

Output index.html will be created as DAY_FOLDER/show_all/index.html
        """
    )
    
    parser.add_argument(
        'folder',
        help='Path to day folder containing video subfolders'
    )
    
    args = parser.parse_args()
    
    try:
        # Validate folder path
        folder_path = Path(args.folder)
        if not folder_path.exists():
            print(f"Error: Folder not found: {args.folder}")
            sys.exit(1)
        
        if not folder_path.is_dir():
            print(f"Error: Not a directory: {args.folder}")
            sys.exit(1)
        
        # Setup logging
        logger = setup_logging(folder_path)
        
        # Process folder
        success = process_folder(folder_path, logger)
        
        # Report results
        if success:
            output_path = folder_path / 'show_all' / 'index.html'
            success_msg = f"\n✓ Successfully created day index at {output_path}"
            logger.info(success_msg)
            print(success_msg)
        else:
            logger.info("Failed to create day index page")
        
        logger.info("="*60)
        logger.info("Session completed")
        logger.info("="*60)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
