#!/usr/bin/env python3
"""
File OCR Extraction Processor
Extracts text from a single PNG image using Llama Vision Model via Ollama.
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


def check_ollama():
    """Check if Ollama is available."""
    try:
        import ollama
        ollama.list()
        return True
    except ImportError:
        print("ERROR: ollama package not installed!")
        print("\nPlease install with:")
        print("  pip install ollama")
        return False
    except Exception as e:
        print(f"ERROR: Cannot connect to Ollama: {e}")
        print("\nMake sure Ollama is running and a vision model is installed.")
        return False


def extract_text_from_image(image_path, model='llama3.2-vision', timeout=60):
    """
    Extract text from an image using Llama Vision Model.
    
    Args:
        image_path: Path to image file
        model: Vision model name (e.g., 'llama3.2-vision', 'llava')
        timeout: Timeout in seconds (default: 60)
    
    Returns:
        Extracted text as string
    """
    try:
        import ollama
        from threading import Thread, Event
        import time
        
        prompt = """Please extract and transcribe ALL text visible in this image. 
Output only the text you see, preserving the layout and order as much as possible.
If there is no text, simply respond with an empty string.
Do not add any commentary or explanations - just the extracted text."""
        
        print(f"  → Sending request to Ollama ({model})...", flush=True)
        
        result = {'text': '', 'error': None}
        done_event = Event()
        
        def call_ollama():
            try:
                response = ollama.chat(
                    model=model,
                    messages=[{
                        'role': 'user',
                        'content': prompt,
                        'images': [str(image_path)]
                    }]
                )
                result['text'] = response['message']['content'].strip()
            except Exception as e:
                result['error'] = str(e)
            finally:
                done_event.set()
        
        # Start request in background thread
        thread = Thread(target=call_ollama)
        thread.daemon = True
        thread.start()
        
        # Wait with progress dots
        start_time = time.time()
        while not done_event.wait(timeout=1):
            elapsed = int(time.time() - start_time)
            if elapsed >= timeout:
                print(f"\n  ✗ TIMEOUT after {timeout}s - model may be too slow or stuck", flush=True)
                return "[TIMEOUT - Consider using a faster model like llava or moondream]"
            print(f"  ... waiting ({elapsed}s/{timeout}s)", end='\r', flush=True)
        
        if result['error']:
            raise Exception(result['error'])
        
        print(f"  ✓ Response received ({int(time.time() - start_time)}s)" + " " * 20, flush=True)
        return result['text']
    
    except Exception as e:
        print(f"\n  ✗ Error processing {image_path}: {e}", flush=True)
        return ""


def extract_ocr_from_file(input_file, model='llama3.2-vision', timeout=60):
    """
    Extract OCR text from a single PNG file and output to ocr_extractions/ folder.
    
    Args:
        input_file: Path to input PNG file
        model: Vision model name (e.g., 'llama3.2-vision', 'llava')
        timeout: Timeout in seconds for each image (default: 60)
    
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
    if input_path.suffix.lower() != '.png':
        print(f"Warning: File does not have .png extension")
    
    # Extract text using Llama Vision
    print(f"Extracting text from image using {model}...")
    text = extract_text_from_image(input_path, model)
    
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
        description='Extract OCR text from a single PNG file using Llama Vision Model',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ocr_extractions.py image.png
  python ocr_extractions.py thumb_00-10.png -m llava
  python ocr_extractions.py image.png -m llama3.2-vision
        """
    )
    parser.add_argument(
        'input_file',
        help='Path to input PNG file'
    )
    parser.add_argument(
        '-m', '--model',
        default='llama3.2-vision',
        help='Vision model to use (default: llama3.2-vision)'
    )
    parser.add_argument(
        '-t', '--timeout',
        type=int,
        default=60,
        help='Timeout in seconds for each image (default: 60)'
    )
    
    args = parser.parse_args()
    
    # Check Ollama
    if not check_ollama():
        sys.exit(1)
    
    try:
        extract_ocr_from_file(
            args.input_file,
            args.model,
            args.timeout
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
