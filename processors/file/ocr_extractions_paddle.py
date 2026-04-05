#!/usr/bin/env python3
"""
File OCR Extraction Processor
Extracts text from a single PNG image using PaddleOCR.
Outputs OCR text to 'ocr_extractions/' folder.

Usage:
    python ocr_extractions.py FILE.png
    
Output:
    ocr_extractions/FILE.txt
"""

import os
import sys
import argparse
from pathlib import Path


def check_paddleocr():
    """Check if PaddleOCR is available."""
    try:
        import paddleocr
        return True
    except ImportError:
        print("ERROR: paddleocr package not installed!")
        print("\nPlease install with:")
        print("  pip install paddleocr")
        return False


def extract_text_from_image(image_path, use_gpu=True, lang='en'):
    """
    Extract text from an image using PaddleOCR.
    
    Args:
        image_path: Path to image file
        use_gpu: Whether to use GPU acceleration
        lang: Language code (default: 'en')
    
    Returns:
        Extracted text as string
    """
    try:
        from paddleocr import PaddleOCR
        
        # Initialize PaddleOCR
        ocr = PaddleOCR(
            use_angle_cls=True,  # Enable angle classification
            lang=lang,
            use_gpu=use_gpu,
            show_log=False  # Reduce console output
        )
        
        # Perform OCR
        result = ocr.ocr(str(image_path), cls=True)
        
        # Extract text from results
        # PaddleOCR returns: [[[bbox], (text, confidence)], ...]
        text_lines = []
        if result and result[0]:
            for line in result[0]:
                if len(line) >= 2:
                    text = line[1][0]  # Get text from (text, confidence) tuple
                    text_lines.append(text)
        
        return '\n'.join(text_lines)
    
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return ""


def extract_ocr_from_file(input_file, use_gpu=True, lang='en'):
    """
    Extract OCR text from a single PNG file and output to ocr_extractions/ folder.
    
    Args:
        input_file: Path to input PNG file
        use_gpu: Whether to use GPU acceleration
        lang: Language code
    
    Returns:
        Dictionary with output information
    """
    input_path = Path(input_file).resolve()
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    print(f"\n{'='*60}")
    print(f"Processing: {input_path.name}")
    print('='*60)
    
    # Check file extension
    if input_path.suffix.lower() not in ['.png', '.jpg', '.jpeg']:
        print(f"Warning: File may not be an image")
    
    # Extract text using PaddleOCR
    print(f"Extracting text using PaddleOCR ({'GPU' if use_gpu else 'CPU'})...")
    text = extract_text_from_image(input_path, use_gpu, lang)
    
    # Create ocr_extractions/ folder at the root level
    if input_path.parent.name in ['transcripts', 'logs', 'thumbs', 'summaries']:
        root_folder = input_path.parent.parent
    else:
        root_folder = input_path.parent
    
    ocr_dir = root_folder / 'ocr_extractions'
    ocr_dir.mkdir(exist_ok=True)
    
    # Output file: ocr_extractions/FILENAME.txt
    base_name = input_path.stem
    output_path = ocr_dir / f"{base_name}.txt"
    
    # Save OCR text
    output_path.write_text(text, encoding='utf-8')
    
    char_count = len(text)
    line_count = len(text.split('\n')) if text else 0
    
    print(f"\n{'='*60}")
    print("OCR extraction complete!")
    print(f"  Input: {input_path.name}")
    print(f"  Output: {output_path}")
    print(f"  Extracted: {char_count} characters, {line_count} lines")
    if text:
        print(f"  Preview: {text[:100]}...")
    print('='*60)
    
    return {
        'ocr_file': str(output_path),
        'text': text,
        'char_count': char_count,
        'line_count': line_count
    }


def main():
    parser = argparse.ArgumentParser(
        description='Extract OCR text from a single PNG file using PaddleOCR',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ocr_extractions.py image.png
  python ocr_extractions.py thumb_00-10.png --cpu
  python ocr_extractions.py image.png -l ch  # Chinese
        """
    )
    parser.add_argument(
        'input_file',
        help='Path to input image file'
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
    
    args = parser.parse_args()
    
    # Check PaddleOCR
    if not check_paddleocr():
        sys.exit(1)
    
    try:
        extract_ocr_from_file(
            args.input_file,
            use_gpu=not args.cpu,
            lang=args.lang
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
