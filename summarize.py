#!/usr/bin/env python3
"""
Summarize File with Ollama
Uses Ollama's Python library to generate summaries with local LLMs.

Usage:
    python summarize.py <file_path> [--model MODEL] [--output OUTPUT]

Examples:
    python summarize.py transcript.txt
    python summarize.py transcript.txt --model llama3.2
    python summarize.py transcript.txt --output summary.txt
    
Requires Ollama to be running. Install from: https://ollama.ai
"""

import sys
import argparse
from pathlib import Path


def check_dependencies():
    """Check if required packages are installed."""
    try:
        import ollama
        return True
    except ImportError:
        print("ERROR: ollama package not installed!")
        print("\nPlease install with:")
        print("  pip install ollama")
        return False


def check_ollama_running():
    """Check if Ollama is running and accessible."""
    try:
        import ollama
        # Try to list models to verify connection
        ollama.list()
        return True
    except Exception as e:
        print(f"ERROR: Cannot connect to Ollama: {e}")
        print("\nMake sure Ollama is installed and running:")
        print("  1. Download from https://ollama.ai")
        print("  2. Start Ollama")
        print("  3. Pull a model: ollama pull llama3.2")
        return False


def summarize_with_ollama(text, model_name='llama3.2', max_words=500):
    """
    Summarize text using Ollama.
    
    Args:
        text: Text to summarize
        model_name: Ollama model name (default: llama3.2)
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
        
        print(f"Calling Ollama with model: {model_name}")
        print("(This may take 30-60 seconds...)\n")
        
        # Use the ollama library to generate
        response = ollama.generate(
            model=model_name,
            prompt=prompt
        )
        
        return response['response'].strip()
    
    except Exception as e:
        return f"Error generating summary: {e}"


def summarize_file(file_path, model='llama3.2', output_file=None, max_words=500):
    """
    Summarize a text file using Ollama.
    
    Args:
        file_path: Path to file to summarize
        model: Ollama model to use
        output_file: Optional output file path
        max_words: Target words in summary
    
    Returns:
        Summary text
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return None
    
    # Read file
    print(f"Reading file: {file_path}")
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading file: {e}")
        return None
    
    # Show file stats
    word_count = len(content.split())
    print(f"File size: {len(content)} characters, ~{word_count} words")
    
    # Truncate if too long
    max_words_input = 20000
    if word_count > max_words_input:
        print(f"⚠ Text is very long, using first {max_words_input} words...")
        content = ' '.join(content.split()[:max_words_input])
    
    # Generate summary
    print(f"\nGenerating summary with {model}...")
    
    summary = summarize_with_ollama(content, model, max_words)
    
    # Display summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("=" * 60)
    print(summary)
    print("=" * 60)
    
    # Save to file if requested
    if output_file:
        output_path = Path(output_file)
        try:
            output_path.write_text(summary, encoding='utf-8')
            print(f"\n✓ Summary saved to: {output_path}")
        except Exception as e:
            print(f"\n⚠ Could not save summary: {e}")
    
    return summary


def main():
    parser = argparse.ArgumentParser(
        description='Summarize text files using Ollama',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Summarize a transcript file
  python summarize.py transcript.txt
  
  # Use a different model
  python summarize.py transcript.txt --model llama3.2
  
  # Save summary to a file
  python summarize.py transcript.txt --output summary.txt
  
  # Shorter summary
  python summarize.py transcript.txt --max-words 200

Available models (after pulling with ollama):
  - llama3.2 (default, 3B params, fast)
  - llama3.2:1b (smaller, faster)
  - llama3.1 (larger, more capable)
  - mistral (alternative good model)
  - phi3 (Microsoft, very small and fast)

Install models with: ollama pull <model_name>
List models with: ollama list
        """
    )
    
    parser.add_argument(
        'file',
        nargs='?',  # Make file optional
        help='Text file to summarize'
    )
    parser.add_argument(
        '-m', '--model',
        default='llama3.2',
        help='Ollama model to use (default: llama3.2)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file path (optional)'
    )
    parser.add_argument(
        '--max-words',
        type=int,
        default=500,
        help='Target words in summary (default: 500)'
    )
    parser.add_argument(
        '--list-models',
        action='store_true',
        help='List available Ollama models and exit'
    )
    
    args = parser.parse_args()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # List models if requested
    if args.list_models:
        try:
            import ollama
            models = ollama.list()
            print("Available Ollama models:")
            for model in models.get('models', []):
                print(f"  - {model['name']}")
        except Exception as e:
            print(f"Error listing models: {e}")
        sys.exit(0)
    
    # Check if file was provided
    if not args.file:
        parser.error("file argument is required (unless using --list-models)")
    
    # Check if Ollama is running
    if not check_ollama_running():
        sys.exit(1)
    
    # Summarize file
    try:
        summarize_file(args.file, args.model, args.output, args.max_words)
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        sys.exit(1)


if __name__ == '__main__':
    main()
