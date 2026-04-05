#!/usr/bin/env python3
"""
All Days Show All Processor
Creates a top-level index page that links to all day show_all pages.
Processes a folder containing day subfolders (e.g., s:/Videos/Raw/).

Usage:
    python show_all.py ROOT_FOLDER/
    
Output:
    ROOT_FOLDER/show_all/index.html
      
The HTML page displays a list of all days with links to their
day-level show_all/index.html pages.
"""

import sys
import argparse
from pathlib import Path
import logging
from datetime import datetime
import re


def setup_logging(folder_path):
    """Set up logging to logs/all_show_all.log in the target folder."""
    folder = Path(folder_path)
    logs_dir = folder / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / 'all_show_all.log'
    
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
    logger.info(f"All days show all session started")
    logger.info(f"Target folder: {folder}")
    logger.info("="*60)
    
    return logger


def format_day_name(folder_name):
    """
    Parse day folder name and format it nicely.
    
    Expected format: YYYY-MM-DD
    Returns formatted string like "Friday, April 4, 2026" or original if can't parse.
    """
    match = re.match(r'(\d{4})-(\d{2})-(\d{2})', folder_name)
    if match:
        year, month, day = match.groups()
        try:
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime('%A, %B %d, %Y')  # e.g., "Friday, April 4, 2026"
        except ValueError:
            pass
    
    return folder_name


def find_day_folders(root_folder):
    """
    Find all day subfolders that contain a show_all/index.html file.
    
    Returns list of tuples: (subfolder_path, show_all_exists)
    """
    day_folders = []
    
    for item in sorted(root_folder.iterdir(), reverse=True):  # Most recent first
        if item.is_dir() and not item.name.startswith('.') and item.name not in ['logs', 'show_all']:
            show_all_index = item / 'show_all' / 'index.html'
            day_folders.append((item, show_all_index.exists()))
    
    return day_folders


def count_videos_in_day(day_folder):
    """Count how many video subfolders exist in a day folder."""
    count = 0
    for item in day_folder.iterdir():
        if item.is_dir() and not item.name.startswith('.') and item.name not in ['logs', 'show_all', 'summaries']:
            count += 1
    return count


def generate_html(root_folder, day_folders):
    """Generate the all-days index HTML page."""
    
    root_name = root_folder.name if root_folder.name else "Videos"
    
    # Build days list HTML
    days_html = ""
    for day_folder, has_show_all in day_folders:
        folder_name = day_folder.name
        display_name = format_day_name(folder_name)
        
        # Count videos in this day
        video_count = count_videos_in_day(day_folder)
        
        if has_show_all:
            link_path = f"../{folder_name}/show_all/index.html"
            days_html += f'''
        <li class="day-item">
            <a href="{link_path}" class="day-link">
                <div class="day-header">
                    <span class="icon">📅</span>
                    <div class="day-info">
                        <span class="day-name">{display_name}</span>
                        <span class="day-meta">{video_count} video{"s" if video_count != 1 else ""}</span>
                    </div>
                </div>
            </a>
        </li>
'''
        else:
            # No show_all page exists
            days_html += f'''
        <li class="day-item no-link">
            <div class="day-header">
                <span class="icon">📁</span>
                <div class="day-info">
                    <span class="day-name">{display_name}</span>
                    <span class="day-meta">{video_count} video{"s" if video_count != 1 else ""} • <span class="status">not processed</span></span>
                </div>
            </div>
        </li>
'''
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{root_name} - All Days</title>
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
            max-width: 800px;
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
        
        .day-list {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        
        .day-item {{
            background: #252526;
            border-radius: 8px;
            transition: all 0.2s;
        }}
        
        .day-item:has(.day-link) {{
            border-left: 4px solid #0e639c;
        }}
        
        .day-item.no-link {{
            border-left: 4px solid #3e3e42;
            opacity: 0.7;
            padding: 20px;
        }}
        
        .day-link {{
            text-decoration: none;
            color: inherit;
            display: block;
            padding: 20px;
        }}
        
        .day-item:has(.day-link):hover {{
            background: #2a2d2e;
            transform: translateX(4px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }}
        
        .day-header {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .icon {{
            font-size: 28px;
        }}
        
        .day-info {{
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        
        .day-name {{
            color: #ffffff;
            font-size: 18px;
            font-weight: 500;
        }}
        
        .day-meta {{
            color: #858585;
            font-size: 14px;
        }}
        
        .status {{
            color: #ce9178;
            font-style: italic;
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
    </style>
</head>
<body>
    <div class="container">
        <div class="page-header">
            <h1>🗂️ {root_name}</h1>
            <p class="subtitle">Video Archive</p>
        </div>
        
        {"<ul class='day-list'>" + days_html + "</ul>" if day_folders else '''
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <h2>No Days Found</h2>
            <p>No day folders found in this directory.</p>
        </div>
        '''}
        
        <div class="stats">
            {len([df for df in day_folders if df[1]])} of {len(day_folders)} days processed • {sum(count_videos_in_day(df[0]) for df in day_folders)} total videos
        </div>
    </div>
</body>
</html>
"""
    
    return html_content


def process_folder(folder_path, logger=None):
    """
    Process root folder and create all-days index page.
    
    Args:
        folder_path: Path to the root folder
        logger: Logger instance
    
    Returns:
        True if successful, False otherwise
    """
    folder = Path(folder_path)
    
    # Find all day folders
    day_folders = find_day_folders(folder)
    
    if logger:
        total_days = len(day_folders)
        processed_days = len([df for df in day_folders if df[1]])
        total_videos = sum(count_videos_in_day(df[0]) for df in day_folders)
        logger.info(f"Found {total_days} day folder(s)")
        logger.info(f"{processed_days} have show_all/index.html")
        logger.info(f"{total_videos} total video folders")
    
    # Create output directory
    output_dir = folder / 'show_all'
    output_dir.mkdir(exist_ok=True)
    
    # Generate HTML
    try:
        html_content = generate_html(folder, day_folders)
        output_file = output_dir / 'index.html'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        if logger:
            logger.info(f"Created: {output_file.name}")
        
        return True
        
    except Exception as e:
        error_msg = f"Error generating all-days index page: {str(e)}"
        if logger:
            logger.error(error_msg)
        print(error_msg)
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Create a top-level index page linking to all day show_all pages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python show_all.py s:\\Videos\\Raw
  python show_all.py /path/to/videos/root/

The processor will look for day subfolders (e.g., 2026-04-04) containing 
show_all/index.html files and create a master index with links to all days.

Output index.html will be created as ROOT_FOLDER/show_all/index.html
        """
    )
    
    parser.add_argument(
        'folder',
        help='Path to root folder containing day subfolders'
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
            success_msg = f"\n✓ Successfully created all-days index at {output_path}"
            logger.info(success_msg)
            print(success_msg)
        else:
            logger.info("Failed to create all-days index page")
        
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
