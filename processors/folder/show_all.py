#!/usr/bin/env python3
"""
Folder Show All Processor
Creates a unified HTML page showing summaries, thumbnails, and transcripts.
Combines content from summaries/, show_thumbs/, and show_transcripts/ if available.

Usage:
    python show_all.py FOLDER/
    
Output:
    FOLDER/show_all/index.html
      
The HTML page displays all available content in a unified interface.
"""

import sys
import argparse
from pathlib import Path
import logging
from datetime import datetime


def setup_logging(folder_path):
    """Set up logging to logs/show_all.log in the target folder."""
    folder = Path(folder_path)
    logs_dir = folder / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / 'show_all.log'
    
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
    logger.info(f"Show all session started")
    logger.info(f"Target folder: {folder}")
    logger.info("="*60)
    
    return logger


def find_summary_files(folder):
    """Find all summary text files in summaries/ folder."""
    summaries_dir = folder / 'summaries'
    if not summaries_dir.exists() or not summaries_dir.is_dir():
        return []
    
    summary_files = sorted(summaries_dir.glob('*_summary.txt'))
    return summary_files


def read_summary(summary_path):
    """Read summary file content."""
    try:
        with open(summary_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading summary: {str(e)}"


def generate_html(folder, summaries, has_thumbs, has_transcripts):
    """Generate the unified HTML page."""
    
    folder_name = folder.name
    
    # Build summaries section (with optional thumbs on the left)
    summaries_html = ""
    if summaries or has_thumbs:
        summaries_html = '<div class="section summaries-section">\n'
        
        if summaries and has_thumbs:
            summaries_html += '    <div class="summary-layout">\n'
            summaries_html += '        <div class="thumbs-sidebar">\n'
            summaries_html += '            <iframe src="../show_thumbs/index.html" title="Thumbnail Slideshow"></iframe>\n'
            summaries_html += '        </div>\n'
            summaries_html += '        <div class="summaries-main">\n'
            summaries_html += '            <h2>📝 Summaries</h2>\n'
            summaries_html += '            <div class="summaries-container">\n'
        elif summaries:
            summaries_html += '    <h2>📝 Summaries</h2>\n'
            summaries_html += '    <div class="summaries-container">\n'
        
        if summaries:
            for summary_path, content in summaries:
                # Extract base name without _summary.txt
                base_name = summary_path.stem
                if base_name.endswith('_summary'):
                    base_name = base_name[:-8]
                
                summaries_html += f'''
            <div class="summary-card">
                <h3>{base_name}</h3>
                <div class="summary-content">{content}</div>
            </div>
'''
        
        if summaries:
            summaries_html += '            </div>\n'
            
        if summaries and has_thumbs:
            summaries_html += '        </div>\n'
            summaries_html += '    </div>\n'
        
        summaries_html += '</div>\n'
    
    # Build transcripts section
    transcripts_html = ""
    if has_transcripts:
        transcripts_html = '''
<div class="section iframe-section">
    <h2>📹 Video Transcripts</h2>
    <div class="iframe-container">
        <iframe src="../show_transcripts/index.html" title="Video Transcripts"></iframe>
    </div>
</div>
'''
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{folder_name} - Overview</title>
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
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
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
            font-size: 32px;
            margin-bottom: 10px;
        }}
        
        .page-header .subtitle {{
            color: #858585;
            font-size: 16px;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section h2 {{
            color: #ffffff;
            font-size: 24px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .summary-layout {{
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 20px;
        }}
        
        @media (max-width: 1024px) {{
            .summary-layout {{
                grid-template-columns: 1fr;
            }}
            
            .thumbs-sidebar {{
                height: 400px;
            }}
        }}
        
        .thumbs-sidebar {{
            background: #1e1e1e;
            border-radius: 8px;
            border: 2px solid #3e3e42;
            overflow: hidden;
            height: 300px;
        }}
        
        .thumbs-sidebar iframe {{
            width: 100%;
            height: 100%;
            border: none;
            display: block;
        }}
        
        .summaries-main {{
            display: flex;
            flex-direction: column;
        }}
        
        .summaries-main h2 {{
            margin-bottom: 20px;
        }}
        
        .summaries-container {{
            display: grid;
            gap: 20px;
        }}
        
        .summary-card {{
            background: #252526;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #0e639c;
        }}
        
        .summary-card h3 {{
            color: #6a9955;
            font-size: 18px;
            margin-bottom: 15px;
            font-family: 'Courier New', monospace;
        }}
        
        .summary-content {{
            color: #d4d4d4;
            white-space: pre-wrap;
            line-height: 1.8;
        }}
        
        .iframe-section {{
            background: #252526;
            border-radius: 8px;
            padding: 20px;
        }}
        
        .iframe-container {{
            width: 100%;
            min-height: 700px;
            background: #1e1e1e;
            border-radius: 8px;
            border: 2px solid #3e3e42;
        }}
        
        .iframe-container iframe {{
            width: 100%;
            height: 1000px;
            border: none;
            display: block;
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
        
        .empty-state p {{
            margin-top: 10px;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="page-header">
            <h1>📂 {folder_name}</h1>
            <p class="subtitle">Complete Overview</p>
        </div>
        
        {summaries_html}
        {transcripts_html}
        
        {"" if (summaries or has_thumbs or has_transcripts) else '''
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <h2>No Content Available</h2>
            <p>Process this folder with other processors to generate summaries, thumbnails, or transcripts.</p>
        </div>
        '''}
    </div>
</body>
</html>
"""
    
    return html_content


def process_folder(folder_path, logger=None):
    """
    Process folder and create unified overview page.
    
    Args:
        folder_path: Path to the folder
        logger: Logger instance
    
    Returns:
        True if successful, False otherwise
    """
    folder = Path(folder_path)
    
    # Check for summaries
    summary_files = find_summary_files(folder)
    summaries = []
    if summary_files:
        if logger:
            logger.info(f"Found {len(summary_files)} summary file(s)")
        for summary_file in summary_files:
            content = read_summary(summary_file)
            summaries.append((summary_file, content))
    else:
        if logger:
            logger.info("No summaries found")
    
    # Check for thumbs index
    thumbs_index = folder / 'show_thumbs' / 'index.html'
    has_thumbs = thumbs_index.exists()
    if logger:
        if has_thumbs:
            logger.info("Found show_thumbs/index.html")
        else:
            logger.info("No show_thumbs/index.html found")
    
    # Check for transcripts index
    transcripts_index = folder / 'show_transcripts' / 'index.html'
    has_transcripts = transcripts_index.exists()
    if logger:
        if has_transcripts:
            logger.info("Found show_transcripts/index.html")
        else:
            logger.info("No show_transcripts/index.html found")
    
    # Create output directory
    output_dir = folder / 'show_all'
    output_dir.mkdir(exist_ok=True)
    
    # Generate HTML
    try:
        html_content = generate_html(folder, summaries, has_thumbs, has_transcripts)
        output_file = output_dir / 'index.html'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        if logger:
            logger.info(f"Created: {output_file.name}")
        
        return True
        
    except Exception as e:
        error_msg = f"Error generating overview page: {str(e)}"
        if logger:
            logger.error(error_msg)
        print(error_msg)
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Create a unified overview page combining summaries, thumbnails, and transcripts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python show_all.py my_videos/
  python show_all.py /path/to/folder/

The processor will look for:
  - summaries/ folder with summary files
  - show_thumbs/index.html (created by show_thumbs processor)
  - show_transcripts/index.html (created by show_transcripts processor)

Output index.html will be created as show_all/index.html
        """
    )
    
    parser.add_argument(
        'folder',
        help='Path to folder to create overview for'
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
            success_msg = f"\n✓ Successfully created overview page at {output_path}"
            logger.info(success_msg)
            print(success_msg)
        else:
            logger.info("Failed to create overview page")
        
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
