#!/usr/bin/env python3
"""
Text Extraction Script
Extracts text from PNG images using PaddleOCR.
Processes all PNG files in a directory and saves text to corresponding txt files.
"""

import os
import sys
import argparse
from pathlib import Path

# Add NVIDIA CUDA library paths for Windows (Python 3.8+)
# This ensures PaddlePaddle can find CUDNN and cuBLAS DLLs
if sys.platform == 'win32':
    import site
    site_packages = site.getsitepackages()[0]
    cuda_paths = [
        os.path.join(site_packages, 'nvidia', 'cudnn', 'bin'),
        os.path.join(site_packages, 'nvidia', 'cublas', 'bin'),
        os.path.join(site_packages, 'nvidia', 'cuda_nvrtc', 'bin'),
    ]
    
    # Add to PATH environment variable
    for cuda_path in cuda_paths:
        if os.path.exists(cuda_path):
            if cuda_path not in os.environ.get('PATH', ''):
                os.environ['PATH'] = cuda_path + os.pathsep + os.environ.get('PATH', '')
            
            # Also use add_dll_directory for Python 3.8+ on Windows
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(cuda_path)
                except (FileNotFoundError, OSError):
                    pass

from paddleocr import PaddleOCR


def extract_text_from_image(image_path, ocr_engine, lang='en'):
    """
    Extract text from an image using PaddleOCR.
    
    Args:
        image_path: Path to image file
        ocr_engine: PaddleOCR instance
        lang: Language code (default: 'en')
    
    Returns:
        Extracted text as string
    """
    try:
        result = ocr_engine.ocr(str(image_path))
        
        # Extract text from OCR results
        # PaddleOCR returns list of pages, each containing detected text regions
        if result and result[0]:
            text_lines = []
            for line in result[0]:
                # Each line is: [bbox, (text, confidence)]
                if len(line) >= 2 and line[1]:
                    text = line[1][0] if isinstance(line[1], (list, tuple)) else line[1]
                    text_lines.append(str(text))
            return '\n'.join(text_lines)
        else:
            return ""
    
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return ""


def process_directory(input_dir, lang='en', recursive=False, verbose=False):
    """
    Process all PNG files in a directory.
    
    Args:
        input_dir: Directory containing PNG files
        lang: Language code for OCR (default: 'en')
        recursive: Process subdirectories recursively (default: False)
        verbose: Print detailed progress (default: False)
    
    Returns:
        Number of files processed
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Directory not found: {input_dir}")
    
    if not input_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {input_dir}")
    
    # Find all PNG files
    if recursive:
        png_files = sorted(input_path.rglob('*.png'))
    else:
        png_files = sorted(input_path.glob('*.png'))
    
    if not png_files:
        print(f"No PNG files found in {input_dir}")
        return 0
    
    print(f"Found {len(png_files)} PNG file(s)")
    print(f"Initializing PaddleOCR (language: {lang})...")
    
    # Initialize PaddleOCR with GPU (sidesteps CPU oneDNN bug)
    ocr = PaddleOCR(
        lang=lang
    )
    
    print(f"\n{'='*60}")
    print("Processing images...")
    print('='*60)
    
    processed = 0
    for png_file in png_files:
        if verbose:
            print(f"\nProcessing: {png_file.name}")
        else:
            print(f"Processing: {png_file.name}... ", end='', flush=True)
        
        # Extract text
        text = extract_text_from_image(png_file, ocr, lang)
        
        # Save to txt file with same name
        txt_file = png_file.with_suffix('.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(text)
        
        if verbose:
            print(f"  Extracted {len(text)} characters")
            print(f"  Saved to: {txt_file}")
            if text:
                print(f"  Preview: {text[:100]}...")
        else:
            print(f"✓ ({len(text)} chars)")
        
        processed += 1
    
    print(f"\n{'='*60}")
    print(f"Successfully processed {processed} image(s)")
    print(f"Text files saved in: {input_path}")
    print('='*60)
    
    return processed


def process_single_file(input_file, lang='en', output_file=None, verbose=False):
    """
    Process a single PNG file.
    
    Args:
        input_file: Path to PNG file
        lang: Language code for OCR (default: 'en')
        output_file: Optional output path (default: same name with .txt extension)
        verbose: Print detailed progress (default: False)
    
    Returns:
        Extracted text
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_file}")
    
    if input_path.suffix.lower() != '.png':
        print(f"Warning: File does not have .png extension: {input_file}")
    
    print(f"Initializing PaddleOCR (language: {lang})...")
    
    # Initialize PaddleOCR with GPU (sidesteps CPU oneDNN bug)
    ocr = PaddleOCR(
        lang=lang
    )
    
    print(f"Processing: {input_path.name}")
    
    # Extract text
    text = extract_text_from_image(input_path, ocr, lang)
    
    # Determine output file
    if output_file:
        output_path = Path(output_file)
    else:
        output_path = input_path.with_suffix('.txt')
    
    # Save to txt file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    print(f"\n{'='*60}")
    print(f"Extracted {len(text)} characters")
    print(f"Saved to: {output_path}")
    if text and verbose:
        print(f"\nExtracted text:")
        print('-'*60)
        print(text)
        print('-'*60)
    print('='*60)
    
    return text


def main():
    parser = argparse.ArgumentParser(
        description='Extract text from PNG images using PaddleOCR',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported languages (use -l option):
  en - English (default)
  ch - Chinese & English
  fr - French
  de - German
  japan - Japanese
  korean - Korean
  es - Spanish
  ...and many more (see PaddleOCR documentation)
  # Process all PNG files in a directory
  python text_extract.py ./thumbnails
  
  # Process a single PNG file
  python text_extract.py image.png
  
  # Process with Chinese OCR
  python text_extract.py ./images -l ch
  
  # Process recursively in subdirectories
  python text_extract.py ./images -r
  
  # Verbose output
  python text_extract.py ./images -v
        """
    )
    parser.add_argument(
        'input',
        help='Path to PNG file or directory containing PNG files'
    )
    parser.add_argument(
        '-l', '--language',
        default='en',
        help='Language code for OCR (default: en)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file path (only for single file mode)'
    )
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Process subdirectories recursively (directory mode only)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Print detailed progress and extracted text'
    )
    
    args = parser.parse_args()
    
    try:
        input_path = Path(args.input)
        
        if input_path.is_dir():
            # Directory mode
            if args.output:
                print("Warning: --output option is ignored in directory mode")
            process_directory(
                args.input,
                lang=args.language,
                recursive=args.recursive,
                verbose=args.verbose
            )
        elif input_path.is_file():
            # Single file mode
            if args.recursive:
                print("Warning: --recursive option is ignored in single file mode")
            process_single_file(
                args.input,
                lang=args.language,
                output_file=args.output,
                verbose=args.verbose
            )
        else:
            print(f"Error: Input path does not exist: {args.input}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
