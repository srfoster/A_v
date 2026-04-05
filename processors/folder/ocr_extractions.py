#!/usr/bin/env python3
"""
Folder OCR Extraction Processor
Extracts text from all PNG images in a folder using PaddleOCR.
Calls the file processor on each .png file found.

Usage:
    python ocr_extractions.py FOLDER/
    
Output:
    For each FILE.png in FOLDER:
      FOLDER/ocr_extractions/FILE.txt
    
Logs extraction details for each file.
"""

import sys
import argparse
from pathlib import Path
import subprocess
import logging
from datetime import datetime


def setup_logging(folder_path):
    """Set up logging to logs/ocr_extractions.log in the target folder."""
    folder = Path(folder_path)
    logs_dir = folder / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / 'ocr_extractions.log'
    
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
    logger.info(f"OCR extraction session started")
    logger.info(f"Target folder: {folder}")
    logger.info("="*60)
    
    return logger


def find_png_files(folder_path):
    """Find all .png files in the folder (recursively)."""
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    
    if not folder.is_dir():
        raise ValueError(f"Not a directory: {folder_path}")
    
    # Use rglob for recursive search
    png_files = sorted(folder.rglob("*.png"))
    return png_files


def get_extraction_preview(ocr_file_path, max_length=80):
    """Get a brief preview of the extracted text for logging."""
    if not ocr_file_path.exists():
        return None
    
    try:
        content = ocr_file_path.read_text(encoding='utf-8')
        if not content:
            return "(empty)"
        
        # Get first line or first N characters
        first_line = content.split('\n')[0]
        if len(first_line) <= max_length:
            return first_line
        else:
            return first_line[:max_length] + '...'
    except:
        return None


def extract_ocr_with_processor(file_path, use_gpu=True, lang='en', logger=None):
    """
    Call the file processor to extract OCR from a single file.
    
    Args:
        file_path: Path to the PNG file
        use_gpu: Whether to use GPU
        lang: Language code
        logger: Logger instance
    
    Returns:
        Tuple of (success: bool, ocr_path: str, preview: str)
    """
    # Get path to file processor (in ../file/ocr_extractions.py)
    current_dir = Path(__file__).parent
    file_processor = current_dir.parent / 'file' / 'ocr_extractions.py'
    
    if not file_processor.exists():
        print(f"Error: File processor not found at {file_processor}")
        return False, None, None
    
    # Build command
    cmd = [sys.executable, str(file_processor), str(file_path)]
    
    if not use_gpu:
        cmd.append('--cpu')
    
    if lang and lang != 'en':
        cmd.extend(['-l', lang])
    
    print(f"\nProcessing: {file_path.name}")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            text=True
            # Don't capture output so we can see errors
        )
        
        # Determine OCR file path
        if file_path.parent.name in ['transcripts', 'logs', 'thumbs', 'summaries']:
            root_folder = file_path.parent.parent
        else:
            root_folder = file_path.parent
        
        ocr_dir = root_folder / 'ocr_extractions'
        ocr_path = ocr_dir / f"{file_path.stem}.txt"
        
        # Read the generated OCR text for preview
        if ocr_path.exists():
            preview = get_extraction_preview(ocr_path)
            return True, str(ocr_path), preview
        
        return True, str(ocr_path), None
        
    except subprocess.CalledProcessError as e:
        print(f"Error processing {file_path.name}: {e}")
        if logger:
            logger.error(f"Failed to process {file_path.name}: {e}")
        return False, None, None


def extract_ocr_from_folder(folder_path, use_gpu=True, lang='en', continue_on_error=True):
    """
    Extract OCR text from all PNG files in a folder.
    
    Args:
        folder_path: Path to folder containing PNG files
        use_gpu: Whether to use GPU
        lang: Language code
        continue_on_error: Whether to continue if a file fails
    
    Returns:
        Dictionary with results
    """
    folder = Path(folder_path)
    
    # Set up logging
    logger = setup_logging(folder)
    
    print(f"\n{'='*60}")
    print(f"Folder OCR Extraction")
    print(f"Folder: {folder}")
    print('='*60)
    
    logger.info(f"GPU: {'Enabled' if use_gpu else 'Disabled'}")
    logger.info(f"Language: {lang}")
    
    # Find all PNG files
    png_files = find_png_files(folder)
    
    if not png_files:
        msg = f"No PNG files found in {folder}"
        print(f"\n{msg}")
        logger.warning(msg)
        return {'total': 0, 'success': 0, 'failed': 0}
    
    print(f"\nFound {len(png_files)} PNG file(s):")
    logger.info(f"Found {len(png_files)} PNG file(s)")
    for f in png_files:
        # Show relative path from folder
        rel_path = f.relative_to(folder)
        print(f"  - {rel_path}")
        logger.info(f"  - {rel_path}")
    
    print(f"\nExtracting OCR text with PaddleOCR ({'GPU' if use_gpu else 'CPU'})")
    
    # Process each file
    results = {
        'total': len(png_files),
        'success': 0,
        'failed': 0,
        'files': []
    }
    
    for i, png_file in enumerate(png_files, 1):
        print(f"\n{'='*60}")
        print(f"File {i}/{len(png_files)}")
        print('='*60)
        
        rel_path = png_file.relative_to(folder)
        logger.info(f"Processing file {i}/{len(png_files)}: {rel_path}")
        
        success, ocr_path, preview = extract_ocr_with_processor(
            png_file,
            use_gpu,
            lang,
            logger
        )
        
        if success:
            results['success'] += 1
            results['files'].append({'file': str(png_file), 'status': 'success'})
            
            # Log with preview
            log_msg = f"Extracted OCR: {rel_path}"
            if preview:
                log_msg += f" → {preview}"
            
            logger.info(log_msg)
            
        else:
            results['failed'] += 1
            results['files'].append({'file': str(png_file), 'status': 'failed'})
            logger.error(f"Failed to extract OCR: {rel_path}")
            
            if not continue_on_error:
                logger.warning("Stopping due to error")
                print("\nStopping due to error (use --continue to keep processing)")
                break
    
    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    print(f"Total files: {results['total']}")
    print(f"Successful: {results['success']}")
    print(f"Failed: {results['failed']}")
    
    logger.info("="*60)
    logger.info("SUMMARY")
    logger.info(f"Total files: {results['total']}")
    logger.info(f"Successful: {results['success']}")
    logger.info(f"Failed: {results['failed']}")
    
    if results['failed'] > 0:
        print("\nFailed files:")
        logger.info("Failed files:")
        for item in results['files']:
            if item['status'] == 'failed':
                failed_path = Path(item['file']).relative_to(folder)
                print(f"  ✗ {failed_path}")
                logger.error(f"  ✗ {failed_path}")
    
    print('='*60)
    logger.info("="*60)
    logger.info("OCR extraction session completed")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Extract OCR text from all PNG files in a folder using PaddleOCR',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ocr_extractions.py /path/to/images/
  python ocr_extractions.py ./thumbs/ --cpu
  python ocr_extractions.py ./images/ --continue -l ch
        """
    )
    parser.add_argument(
        'folder',
        help='Path to folder containing PNG files'
    )
    parser.add_argument(
        '--cpu',
        action='store_true',
        help='Use CPU instead of GPU'
    )
    parser.add_argument(
        '-l', '--lang',
        default='en',
        help='Language code (default: en)'
    )
    parser.add_argument(
        '--continue',
        dest='continue_on_error',
        action='store_true',
        help='Continue processing even if a file fails'
    )
    
    args = parser.parse_args()
    
    # Check PaddleOCR
    try:
        import paddleocr
    except ImportError:
        print("ERROR: paddleocr package not installed!")
        print("\nPlease install with:")
        print("  pip install paddleocr")
        sys.exit(1)
    
    try:
        results = extract_ocr_from_folder(
            args.folder,
            use_gpu=not args.cpu,
            lang=args.lang,
            continue_on_error=args.continue_on_error
        )
        
        # Exit with error code if any files failed
        if results['failed'] > 0:
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
