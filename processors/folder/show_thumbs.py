#!/usr/bin/env python3
"""
Folder Show Thumbs Processor
Creates an interactive HTML slideshow page from thumbnail images.
Requires a thumbs/ subfolder with thumbnail images.

Usage:
    python show_thumbs.py FOLDER/
    
Output:
    FOLDER/show_thumbs/slideshow.html
      
The HTML page displays thumbnails as a continuously looping slideshow
with playback controls and navigation.
"""

import sys
import argparse
from pathlib import Path
import logging
from datetime import datetime


# Image extensions to look for
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}


def setup_logging(folder_path):
    """Set up logging to logs/show_thumbs.log in the target folder."""
    folder = Path(folder_path)
    logs_dir = folder / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / 'show_thumbs.log'
    
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
    logger.info(f"Show thumbs session started")
    logger.info(f"Target folder: {folder}")
    logger.info("="*60)
    
    return logger


def find_thumbnail_files(thumbs_dir):
    """Find all image files in the thumbs directory, sorted naturally."""
    image_files = []
    for ext in IMAGE_EXTENSIONS:
        image_files.extend(thumbs_dir.glob(f'*{ext}'))
    
    # Sort naturally (so thumb_00-10 comes before thumb_00-100)
    return sorted(image_files, key=lambda p: p.name)


def generate_html(image_files, output_path, folder_name):
    """Generate a simple auto-looping slideshow page."""
    
    # Create relative paths from output HTML to images
    # Output is in show_thumbs/, images are in thumbs/
    image_paths = [f"../thumbs/{img.name}" for img in image_files]
    
    # Build JavaScript array of image paths
    images_js = ',\n            '.join([f'"{path}"' for path in image_paths])
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{folder_name} - Slideshow</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            background: #000;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
        }}
        
        img {{
            max-width: 100%;
            max-height: 100vh;
            object-fit: contain;
        }}
    </style>
</head>
<body>
    <img id="slideshow" src="{image_paths[0]}" alt="Slideshow">
    
    <script>
        const images = [
            {images_js}
        ];
        
        let currentIndex = 0;
        const img = document.getElementById('slideshow');
        
        function nextSlide() {{
            currentIndex = (currentIndex + 1) % images.length;
            img.src = images[currentIndex];
        }}
        
        // Auto-advance every 200ms for quick looping
        setInterval(nextSlide, 200);
    </script>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


def process_folder(folder_path, logger=None):
    """
    Process thumbnails in the thumbs/ subfolder.
    
    Args:
        folder_path: Path to the folder containing thumbs/ subfolder
        logger: Logger instance
    
    Returns:
        True if successful, False otherwise
    """
    folder = Path(folder_path)
    thumbs_dir = folder / 'thumbs'
    
    # Check if thumbs folder exists
    if not thumbs_dir.exists():
        error_msg = f"Error: thumbs/ subfolder not found in {folder_path}"
        if logger:
            logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    if not thumbs_dir.is_dir():
        error_msg = f"Error: {thumbs_dir} is not a directory"
        if logger:
            logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Find all image files
    image_files = find_thumbnail_files(thumbs_dir)
    
    if not image_files:
        msg = f"No image files found in {thumbs_dir}"
        if logger:
            logger.warning(msg)
        print(msg)
        return False
    
    # Create output directory
    output_dir = folder / 'show_thumbs'
    output_dir.mkdir(exist_ok=True)
    
    if logger:
        logger.info(f"Found {len(image_files)} thumbnail(s)")
        logger.info(f"Output directory: {output_dir}")
    
    # Generate HTML
    try:
        output_file = output_dir / 'index.html'
        folder_name = folder.name
        generate_html(image_files, output_file, folder_name)
        
        if logger:
            logger.info(f"Created: {output_file}")
        
        return True
        
    except Exception as e:
        error_msg = f"Error generating slideshow: {str(e)}"
        if logger:
            logger.error(error_msg)
        print(error_msg)
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Create an interactive HTML slideshow from thumbnails',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python show_thumbs.py my_videos/
  python show_thumbs.py /path/to/folder/

The folder must contain a thumbs/ subfolder with thumbnail images.
Output HTML file will be created as show_thumbs/index.html
        """
    )
    
    parser.add_argument(
        'folder',
        help='Path to folder containing thumbs/ subfolder'
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
            output_path = folder_path / 'show_thumbs' / 'index.html'
            success_msg = f"\n✓ Successfully created slideshow at {output_path}"
            logger.info(success_msg)
            print(success_msg)
        else:
            logger.info("No slideshow created")
        
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
