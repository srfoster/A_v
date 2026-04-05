#!/usr/bin/env python3
"""
File Summary Processor
Summarizes a single text file using Ollama's local LLM.
Outputs summary to 'summaries/' folder alongside the input file.

By default, generates a summary that is ~10% of the input file's word count
(minimum 50 words, maximum 1000 words).

Usage:
    python summaries.py FILE.txt
    
Output:
    summaries/FILE_summary.txt
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
    except Exception as e:
        print(f"ERROR: Cannot connect to Ollama: {e}")
        print("\nMake sure Ollama is running and a model is installed.")
        return False


def summarize_with_ollama(text, model_name='llama3.2', max_words=500):
    """
    Summarize text using Ollama.
    
    Args:
        text: Text to summarize
        model_name: Ollama model name
        max_words: Target length for summary
    
    Returns:
        Summary text
    """
    try:
        import ollama
        
        prompt = f"""Please provide a concise summary of the following text in approximately {max_words} words or less.
Focus on the main points, key topics, and important details.

TEXT TO SUMMARIZE:
{text}

SUMMARY:"""
        
        response = ollama.generate(
            model=model_name,
            prompt=prompt
        )
        
        return response['response'].strip()
    
    except Exception as e:
        return f"Error generating summary: {e}"


def summarize_file(input_file, model='llama3.2', max_words=500):
    """
    Summarize a text file and output to summaries/ folder alongside it.
    
    Args:
        input_file: Path to input text file
        model: Ollama model to use
        max_words: Target words in summary
    
    Returns:
        Dictionary with output information
    """
    input_path = Path(input_file).resolve()
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    print(f"\n{'='*60}")
    print(f"Processing: {input_path.name}")
    print('='*60)
    
    # Read file
    print(f"Reading file...")
    try:
        content = input_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading file: {e}")
        raise
    
    # Show file stats
    word_count = len(content.split())
    print(f"File size: {len(content)} characters, ~{word_count} words")
    
    # Calculate target summary size (10% of input, with reasonable bounds)
    calculated_max_words = max(50, min(1000, int(word_count * 0.1)))
    
    # Override max_words if it was user-specified, otherwise use calculated
    if max_words == 500:  # Default value, use calculated instead
        max_words = calculated_max_words
        print(f"Target summary size: ~{max_words} words (10% of input)")
    else:
        print(f"Target summary size: ~{max_words} words (user-specified)")
    
    # Truncate if too long
    max_words_input = 20000
    if word_count > max_words_input:
        print(f"⚠ Text is very long, using first {max_words_input} words...")
        content = ' '.join(content.split()[:max_words_input])
    
    # Generate summary
    print(f"Generating summary with {model}...")
    print("(This may take 30-60 seconds...)\n")
    
    summary = summarize_with_ollama(content, model, max_words)
    
    # Create summaries/ folder at the root level (parent of input file's parent if nested)
    # If file is at: folder/transcripts/file.txt
    # Output goes to: folder/summaries/file_summary.txt
    # If file is at: folder/file.txt
    # Output goes to: folder/summaries/file_summary.txt
    
    # Determine the root folder (go up from input if in subdirectory)
    if input_path.parent.name in ['transcripts', 'logs', 'thumbs']:
        # File is in a subfolder, go up one more level
        root_folder = input_path.parent.parent
    else:
        # File is at top level
        root_folder = input_path.parent
    
    summaries_dir = root_folder / 'summaries'
    summaries_dir.mkdir(exist_ok=True)
    
    # Output file: summaries/FILENAME_summary.txt
    base_name = input_path.stem
    output_path = summaries_dir / f"{base_name}_summary.txt"
    
    # Save summary
    output_path.write_text(summary, encoding='utf-8')
    
    print(f"\n{'='*60}")
    print("Summary generation complete!")
    print(f"  Input: {input_path.name}")
    print(f"  Output: {output_path}")
    print(f"  Summary length: ~{len(summary.split())} words")
    print('='*60)
    
    return {
        'summary_file': str(output_path),
        'summary': summary,
        'word_count': len(summary.split())
    }


def main():
    parser = argparse.ArgumentParser(
        description='Summarize a single text file using Ollama',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python summaries.py transcript.txt
  python summaries.py transcript.txt -m llama3.1:8b
  python summaries.py transcript.txt --max-words 200
        """
    )
    parser.add_argument(
        'input_file',
        help='Path to input text file'
    )
    parser.add_argument(
        '-m', '--model',
        default='llama3.2',
        help='Ollama model to use (default: llama3.2)'
    )
    parser.add_argument(
        '--max-words',
        type=int,
        default=500,
        help='Target words in summary (default: auto-calculate as 10%% of input, min 50, max 1000)'
    )
    
    args = parser.parse_args()
    
    # Check Ollama
    if not check_ollama():
        sys.exit(1)
    
    try:
        summarize_file(
            args.input_file,
            args.model,
            args.max_words
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
