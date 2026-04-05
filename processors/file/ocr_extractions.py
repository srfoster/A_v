#!/usr/bin/env python3
"""
File OCR Extraction Processor
Extracts text from a single PNG image using DeepSeek-OCR-2.
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


def check_dependencies():
    """Check if required packages are available."""
    errors = []
    
    try:
        import transformers
    except ImportError:
        errors.append("transformers package not installed")
    
    try:
        import torch
        if not torch.cuda.is_available():
            errors.append("CUDA not available - DeepSeek-OCR-2 requires GPU")
    except ImportError:
        errors.append("torch package not installed")
    
    try:
        import flash_attn
    except ImportError:
        errors.append("flash-attn package not installed")
    
    if errors:
        print("ERROR: Missing dependencies!")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease install with:")
        print("  pip install torch transformers")
        print("  pip install flash-attn==2.7.3 --no-build-isolation")
        return False
    
    return True


def extract_text_from_image(image_path, use_gpu=True, lang='en'):
    """
    Extract text from an image using DeepSeek-OCR-2.
    
    Args:
        image_path: Path to image file
        use_gpu: Whether to use GPU acceleration (required for DeepSeek-OCR-2)
        lang: Language code (not used, DeepSeek is multilingual)
    
    Returns:
        Extracted text as string
    """
    try:
        from transformers import AutoModel, AutoTokenizer
        import torch
        
        if not use_gpu:
            print("Warning: DeepSeek-OCR-2 requires GPU. Falling back to GPU mode.")
        
        # Check if CUDA is available
        if not torch.cuda.is_available():
            print("Error: CUDA not available. DeepSeek-OCR-2 requires GPU.")
            return ""
        
        print("Loading DeepSeek-OCR-2 model (this may take a while on first run)...")
        model_name = 'deepseek-ai/DeepSeek-OCR-2'
        
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModel.from_pretrained(
            model_name,
            _attn_implementation='flash_attention_2',
            trust_remote_code=True,
            use_safetensors=True
        )
        model = model.eval().cuda().to(torch.bfloat16)
        
        # Use "Free OCR" prompt for simple text extraction
        prompt = "<image>\nFree OCR. "
        
        print("Running OCR inference...")
        # Perform OCR inference
        result = model.infer(
            tokenizer,
            prompt=prompt,
            image_file=str(image_path),
            base_size=1024,
            image_size=768,
            crop_mode=True,
            save_results=False
        )
        
        # Extract the text from result
        if isinstance(result, dict) and 'text' in result:
            extracted_text = result['text']
        elif isinstance(result, str):
            extracted_text = result
        else:
            extracted_text = str(result)
        
        print(f"Extracted text length: {len(extracted_text)} characters")
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
        use_gpu: Whether to use GPU acceleration (required for DeepSeek-OCR-2)
        lang: Language code (not used, DeepSeek is multilingual)
    
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
    print(f"Extracting text using DeepSeek-OCR-2 (GPU required)...")
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
        description='Extract OCR text from a single PNG file using DeepSeek-OCR-2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ocr_extractions.py image.png
  python ocr_extractions.py thumb_00-10.png
        """
    )
    parser.add_argument(
        'input_file',
        help='Path to input image file'
    )
    parser.add_argument(
        '--cpu',
        action='store_true',
        help='Use CPU instead of GPU (Note: DeepSeek-OCR-2 requires GPU, this flag is ignored)'
    )
    parser.add_argument(
        '-l', '--lang',
        default='en',
        help='Language code (not used, DeepSeek is multilingual)'
    )
    
    args = parser.parse_args()
    
    # Check dependencies
    if not check_dependencies():
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
