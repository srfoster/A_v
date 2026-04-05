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
        
        # Initialize PaddleOCR with document processing disabled
        ocr = PaddleOCR(
            lang=lang,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False
        )
        
        # Use predict() with very lenient detection parameters to maximize detection
        result = ocr.predict(
            str(image_path),
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            text_det_limit_side_len=1920,    # Higher resolution
            text_det_limit_type="max",       
            text_det_thresh=0.1,             # Much lower threshold (0.1 instead of 0.3)
            text_det_box_thresh=0.3,         # Lower box threshold (0.3 instead of 0.5)
            text_rec_score_thresh=0.3        # Lower recognition threshold
        )
        
        # Debug: Print full result structure
        import json
        print(f"\nDEBUG: Got {len(result)} result(s)")
        for idx, res in enumerate(result):
            print(f"\nDEBUG: Result {idx} type: {type(res)}")
            if isinstance(res, dict):
                print(f"DEBUG: Result {idx} keys: {list(res.keys())}")
                
                # Check detection results
                dt_polys = res.get('dt_polys', [])
                print(f"DEBUG: Detected {len(dt_polys)} text regions (dt_polys)")
                
                # Check recognition results
                rec_texts = res.get('rec_texts', [])
                rec_scores = res.get('rec_scores', [])
                print(f"DEBUG: Recognized {len(rec_texts)} text(s)")
                
                # Check important fields
                if 'input_path' in res:
                    print(f"DEBUG: Input path: {res['input_path']}")
                if 'page_orientation' in res:
                    orientation = res.get('page_orientation', {})
                    if isinstance(orientation, dict):
                        print(f"DEBUG: Page orientation angle: {orientation.get('angle', 'N/A')}")
                    else:
                        print(f"DEBUG: Page orientation: {orientation}")
                
                # Show detection parameters
                det_params = res.get('text_det_params', {})
                if det_params:
                    print(f"DEBUG: Detection params: {json.dumps(det_params, indent=2)}")
                
                # Show a sample of the result for diagnosis (truncate large fields)
                sample = {}
                for k, v in res.items():
                    if isinstance(v, (list, dict)):
                        sample[k] = f"<{type(v).__name__} len={len(v)}>"
                    elif isinstance(v, str) and len(v) > 100:
                        sample[k] = v[:100] + "..."
                    else:
                        sample[k] = v
                print(f"DEBUG: Result summary: {json.dumps(sample, indent=2, default=str)}")
            else:
                print(f"DEBUG: Result {idx}: {res}")
        
        # Extract text from results
        text_lines = []
        for idx, res in enumerate(result):
            if isinstance(res, dict):
                rec_texts = res.get('rec_texts', [])
                rec_scores = res.get('rec_scores', [])
                for text, score in zip(rec_texts, rec_scores):
                    print(f"DEBUG: Text='{text}' (confidence: {score:.3f})")
                    text_lines.append(str(text))
        
        extracted_text = '\n'.join(text_lines)
        print(f"\nExtracted {len(text_lines)} line(s) of text")
        return extracted_text
    
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        import traceback
        traceback.print_exc()
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
