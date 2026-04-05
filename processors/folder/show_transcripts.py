#!/usr/bin/env python3
"""
Folder Show Transcripts Processor
Creates interactive HTML pages for viewing transcripts alongside videos.
Requires a transcripts/ subfolder with .srt files.

Usage:
    python show_transcripts.py FOLDER/
    
Output:
    For each FILE.srt in FOLDER/transcripts/:
      FOLDER/show_transcripts/FILE.html
      
Each HTML page embeds the original video and provides clickable
transcript lines that jump to the corresponding timestamp.
"""

import sys
import argparse
from pathlib import Path
import logging
from datetime import datetime
import re


# Video/audio extensions to look for
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}


def setup_logging(folder_path):
    """Set up logging to logs/show_transcripts.log in the target folder."""
    folder = Path(folder_path)
    logs_dir = folder / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / 'show_transcripts.log'
    
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
    logger.info(f"Show transcripts session started")
    logger.info(f"Target folder: {folder}")
    logger.info("="*60)
    
    return logger


def parse_srt_file(srt_path):
    """
    Parse an SRT file and return a list of subtitle entries.
    
    Returns:
        List of dicts with keys: index, start_time, end_time, text, start_seconds
    """
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by double newlines to separate entries
    entries = []
    blocks = content.strip().split('\n\n')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
            
        # First line is index
        index = lines[0].strip()
        
        # Second line is timestamp
        timestamp_line = lines[1].strip()
        match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', timestamp_line)
        if not match:
            continue
            
        start_time = match.group(1)
        end_time = match.group(2)
        
        # Remaining lines are text
        text = ' '.join(lines[2:])
        
        # Convert start time to seconds for video seeking
        start_seconds = srt_time_to_seconds(start_time)
        
        entries.append({
            'index': index,
            'start_time': start_time,
            'end_time': end_time,
            'text': text,
            'start_seconds': start_seconds
        })
    
    return entries


def srt_time_to_seconds(time_str):
    """Convert SRT timestamp (HH:MM:SS,mmm) to seconds."""
    # Replace comma with period for milliseconds
    time_str = time_str.replace(',', '.')
    
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    
    return hours * 3600 + minutes * 60 + seconds


def find_video_for_transcript(transcript_path, folder_path):
    """
    Find the video file corresponding to a transcript.
    
    Assumes transcript is named like: FILE_transcript.srt
    and video is in the parent folder as FILE.mp4 (or other extension)
    """
    folder = Path(folder_path)
    transcript_name = transcript_path.stem
    
    # Remove _transcript suffix if present
    if transcript_name.endswith('_transcript'):
        base_name = transcript_name[:-11]  # Remove '_transcript'
    else:
        base_name = transcript_name
    
    # Look for video with matching base name
    for ext in VIDEO_EXTENSIONS:
        video_path = folder / f"{base_name}{ext}"
        if video_path.exists():
            return video_path
    
    return None


def generate_html(srt_entries, video_path, output_path, transcript_name):
    """Generate an interactive HTML page with video and transcript."""
    
    # Create relative path from output HTML to video
    # Both should be in the same parent folder structure
    video_rel_path = f"../{video_path.name}"
    
    # Build transcript HTML
    transcript_html = ""
    for entry in srt_entries:
        transcript_html += f"""
        <div class="transcript-line" data-time="{entry['start_seconds']}">
            <span class="timestamp">{entry['start_time']}</span>
            <span class="text">{entry['text']}</span>
        </div>
"""
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{transcript_name} - Interactive Transcript</title>
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
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        h1 {{
            margin-bottom: 20px;
            color: #ffffff;
        }}
        
        .content {{
            display: grid;
            grid-template-columns: 1fr 400px;
            gap: 20px;
        }}
        
        @media (max-width: 1024px) {{
            .content {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .video-container {{
            background: #000;
            border-radius: 8px;
            overflow: hidden;
        }}
        
        video {{
            width: 100%;
            display: block;
        }}
        
        .transcript-container {{
            background: #252526;
            border-radius: 8px;
            padding: 20px;
            max-height: 600px;
            overflow-y: auto;
        }}
        
        .transcript-container::-webkit-scrollbar {{
            width: 8px;
        }}
        
        .transcript-container::-webkit-scrollbar-track {{
            background: #1e1e1e;
        }}
        
        .transcript-container::-webkit-scrollbar-thumb {{
            background: #3e3e42;
            border-radius: 4px;
        }}
        
        .transcript-container::-webkit-scrollbar-thumb:hover {{
            background: #4e4e52;
        }}
        
        .transcript-line {{
            padding: 10px;
            margin-bottom: 5px;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
            display: flex;
            gap: 10px;
        }}
        
        .transcript-line:hover {{
            background: #2a2d2e;
        }}
        
        .transcript-line.active {{
            background: #094771;
        }}
        
        .timestamp {{
            color: #6a9955;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            min-width: 90px;
            padding-top: 2px;
        }}
        
        .text {{
            flex: 1;
            line-height: 1.5;
        }}
        
        .controls {{
            margin-top: 15px;
            padding: 15px;
            background: #252526;
            border-radius: 8px;
        }}
        
        .info {{
            color: #858585;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📹 {transcript_name}</h1>
        
        <div class="content">
            <div>
                <div class="video-container">
                    <video id="videoPlayer" controls>
                        <source src="{video_rel_path}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                </div>
                
                <div class="controls">
                    <p class="info">💡 Click any transcript line to jump to that moment in the video</p>
                </div>
            </div>
            
            <div class="transcript-container" id="transcriptContainer">
                <h3 style="margin-bottom: 15px; color: #ffffff;">Transcript</h3>
                {transcript_html}
            </div>
        </div>
    </div>
    
    <script>
        const video = document.getElementById('videoPlayer');
        const transcriptLines = document.querySelectorAll('.transcript-line');
        const transcriptContainer = document.getElementById('transcriptContainer');
        
        // Click handler for transcript lines
        transcriptLines.forEach(line => {{
            line.addEventListener('click', () => {{
                const time = parseFloat(line.dataset.time);
                video.currentTime = time;
                video.play();
                
                // Update active state
                transcriptLines.forEach(l => l.classList.remove('active'));
                line.classList.add('active');
            }});
        }});
        
        // Update active line as video plays
        video.addEventListener('timeupdate', () => {{
            const currentTime = video.currentTime;
            
            // Find the current transcript line
            let activeIndex = -1;
            transcriptLines.forEach((line, index) => {{
                const lineTime = parseFloat(line.dataset.time);
                if (currentTime >= lineTime) {{
                    activeIndex = index;
                }}
            }});
            
            // Update active state
            transcriptLines.forEach((line, index) => {{
                if (index === activeIndex) {{
                    line.classList.add('active');
                    
                    // Auto-scroll to keep active line visible
                    const lineTop = line.offsetTop;
                    const lineBottom = lineTop + line.offsetHeight;
                    const containerTop = transcriptContainer.scrollTop;
                    const containerBottom = containerTop + transcriptContainer.clientHeight;
                    
                    if (lineBottom > containerBottom) {{
                        transcriptContainer.scrollTop = lineBottom - transcriptContainer.clientHeight + 20;
                    }} else if (lineTop < containerTop) {{
                        transcriptContainer.scrollTop = lineTop - 20;
                    }}
                }} else {{
                    line.classList.remove('active');
                }}
            }});
        }});
    </script>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


def process_folder(folder_path, logger=None):
    """
    Process all SRT files in the transcripts/ subfolder.
    
    Args:
        folder_path: Path to the folder containing transcripts/ subfolder
        logger: Logger instance
    
    Returns:
        Number of HTML files created
    """
    folder = Path(folder_path)
    transcripts_dir = folder / 'transcripts'
    
    # Check if transcripts folder exists
    if not transcripts_dir.exists():
        error_msg = f"Error: transcripts/ subfolder not found in {folder_path}"
        if logger:
            logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    if not transcripts_dir.is_dir():
        error_msg = f"Error: {transcripts_dir} is not a directory"
        if logger:
            logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Find all SRT files
    srt_files = sorted(transcripts_dir.glob('*.srt'))
    
    if not srt_files:
        msg = f"No .srt files found in {transcripts_dir}"
        if logger:
            logger.warning(msg)
        print(msg)
        return 0
    
    # Create output directory
    output_dir = folder / 'show_transcripts'
    output_dir.mkdir(exist_ok=True)
    
    if logger:
        logger.info(f"Found {len(srt_files)} SRT file(s)")
        logger.info(f"Output directory: {output_dir}")
    
    # Process each SRT file
    success_count = 0
    for srt_file in srt_files:
        try:
            if logger:
                logger.info(f"Processing: {srt_file.name}")
            
            # Parse SRT
            entries = parse_srt_file(srt_file)
            if logger:
                logger.info(f"  Parsed {len(entries)} transcript entries")
            
            # Find corresponding video
            video_path = find_video_for_transcript(srt_file, folder)
            if not video_path:
                warning = f"  Warning: No video found for {srt_file.name}"
                if logger:
                    logger.warning(warning)
                print(warning)
                continue
            
            if logger:
                logger.info(f"  Found video: {video_path.name}")
            
            # Generate HTML
            transcript_name = srt_file.stem
            if transcript_name.endswith('_transcript'):
                transcript_name = transcript_name[:-11]
            
            output_file = output_dir / f"{transcript_name}.html"
            generate_html(entries, video_path, output_file, transcript_name)
            
            if logger:
                logger.info(f"  Created: {output_file.name}")
            
            success_count += 1
            
        except Exception as e:
            error_msg = f"  Error processing {srt_file.name}: {str(e)}"
            if logger:
                logger.error(error_msg)
            print(error_msg)
            continue
    
    return success_count


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Create interactive HTML pages for video transcripts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python show_transcripts.py my_videos/
  python show_transcripts.py /path/to/folder/

The folder must contain a transcripts/ subfolder with .srt files.
Output HTML files will be created in show_transcripts/ subfolder.
        """
    )
    
    parser.add_argument(
        'folder',
        help='Path to folder containing transcripts/ subfolder'
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
        count = process_folder(folder_path, logger)
        
        # Report results
        if count > 0:
            success_msg = f"\n✓ Successfully created {count} HTML file(s) in {folder_path / 'show_transcripts'}"
            logger.info(success_msg)
            print(success_msg)
        else:
            logger.info("No HTML files created")
        
        logger.info("="*60)
        logger.info("Session completed")
        logger.info("="*60)
        
    except FileNotFoundError as e:
        print(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
