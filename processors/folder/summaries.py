#!/usr/bin/env python3
"""
Folder Summary Processor
Summarizes all text files in a folder using the file processor.
Calls the file processor on each .txt file found.

Usage:
    python summaries.py FOLDER/
    
Output:
    For each FILE.txt in FOLDER:
      FOLDER/summaries/FILE_summary.txt
    
Logs include brief meta-summaries of each file's summary.
"""

import sys
import argparse
from pathlib import Path
import subprocess
import logging
from datetime import datetime


DEFAULT_MODEL = 'llama3.2'


def setup_logging(folder_path):
    """Set up logging to logs/summaries.log in the target folder."""
    folder = Path(folder_path)
    logs_dir = folder / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / 'summaries.log'
    
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
    logger.info(f"Summary generation session started")
    logger.info(f"Target folder: {folder}")
    logger.info("="*60)
    
    return logger


def find_text_files(folder_path):
    """Find all .txt files in the folder (recursively), excluding summary files."""
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    
    if not folder.is_dir():
        raise ValueError(f"Not a directory: {folder_path}")
    
    # Use rglob for recursive search, but exclude files ending with _summary.txt
    all_text_files = folder.rglob("*.txt")
    text_files = sorted([f for f in all_text_files if not f.name.endswith('_summary.txt')])
    return text_files


def get_brief_summary(summary_text, max_length=100):
    """Create a brief meta-summary of the summary for logging."""
    # Take first sentence or first N characters
    sentences = summary_text.split('.')
    if sentences and len(sentences[0]) < max_length:
        return sentences[0].strip() + '...'
    else:
        return summary_text[:max_length].strip() + '...'


def summarize_file_with_processor(file_path, model_name='llama3.2', max_words=500, logger=None):
    """
    Call the file processor to summarize a single file.
    
    Args:
        file_path: Path to the text file
        model_name: Ollama model to use
        max_words: Target words in summary
        logger: Logger instance
    
    Returns:
        Tuple of (success: bool, summary_path: str, brief_summary: str)
    """
    # Get path to file processor (in ../file/summaries.py)
    current_dir = Path(__file__).parent
    file_processor = current_dir.parent / 'file' / 'summaries.py'
    
    if not file_processor.exists():
        print(f"Error: File processor not found at {file_processor}")
        return False, None, None
    
    # Build command
    cmd = [sys.executable, str(file_processor), str(file_path)]
    
    if model_name:
        cmd.extend(['-m', model_name])
    
    if max_words:
        cmd.extend(['--max-words', str(max_words)])
    
    print(f"\nProcessing: {file_path.name}")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            text=True,
            capture_output=True
        )
        
        # Extract summary path from output
        # Summaries are at root/summaries/, not alongside the input file
        if file_path.parent.name in ['transcripts', 'logs', 'thumbs']:
            root_folder = file_path.parent.parent
        else:
            root_folder = file_path.parent
        
        summaries_dir = root_folder / 'summaries'
        summary_path = summaries_dir / f"{file_path.stem}_summary.txt"
        
        # Read the generated summary to create meta-summary for log
        if summary_path.exists():
            summary_content = summary_path.read_text(encoding='utf-8')
            brief = get_brief_summary(summary_content)
            return True, str(summary_path), brief
        
        return True, str(summary_path), None
        
    except subprocess.CalledProcessError as e:
        print(f"Error processing {file_path.name}: {e}")
        if logger:
            logger.error(f"Failed to process {file_path.name}: {e}")
        return False, None, None


def summarize_folder(folder_path, model_name=DEFAULT_MODEL, max_words=500, continue_on_error=True):
    """
    Summarize all text files in a folder.
    
    Args:
        folder_path: Path to folder containing text files
        model_name: Ollama model to use
        max_words: Target words in summary
        continue_on_error: Whether to continue if a file fails
    
    Returns:
        Dictionary with results
    """
    folder = Path(folder_path)
    
    # Set up logging
    logger = setup_logging(folder)
    
    print(f"\n{'='*60}")
    print(f"Folder Summary Generation")
    print(f"Folder: {folder}")
    print('='*60)
    
    logger.info(f"Model: {model_name}")
    logger.info(f"Max words: {max_words}")
    
    # Find all text files
    text_files = find_text_files(folder)
    
    if not text_files:
        msg = f"No .txt files found in {folder}"
        print(f"\n{msg}")
        logger.warning(msg)
        return {'total': 0, 'success': 0, 'failed': 0}
    
    print(f"\nFound {len(text_files)} text file(s):")
    logger.info(f"Found {len(text_files)} text file(s)")
    for f in text_files:
        print(f"  - {f.name}")
        logger.info(f"  - {f.name}")
    
    print(f"\nGenerating summaries with model: {model_name}")
    
    # Process each file
    results = {
        'total': len(text_files),
        'success': 0,
        'failed': 0,
        'files': []
    }
    
    for i, text_file in enumerate(text_files, 1):
        print(f"\n{'='*60}")
        print(f"File {i}/{len(text_files)}")
        print('='*60)
        
        logger.info(f"Processing file {i}/{len(text_files)}: {text_file.name}")
        
        success, summary_path, brief_summary = summarize_file_with_processor(
            text_file,
            model_name,
            max_words,
            logger
        )
        
        if success:
            results['success'] += 1
            results['files'].append({'file': str(text_file), 'status': 'success'})
            
            # Log with brief summary
            log_msg = f"✓ Summarized: {text_file.name}"
            if brief_summary:
                log_msg += f" → {brief_summary}"
            
            logger.info(log_msg)
            
        else:
            results['failed'] += 1
            results['files'].append({'file': str(text_file), 'status': 'failed'})
            logger.error(f"✗ Failed to summarize: {text_file.name}")
            
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
                failed_file = Path(item['file']).name
                print(f"  ✗ {failed_file}")
                logger.error(f"  ✗ {failed_file}")
    
    print('='*60)
    logger.info("="*60)
    logger.info("Summary generation session completed")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Generate summaries for all text files in a folder using Ollama',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python summaries.py /path/to/transcripts/
  python summaries.py ./documents/ -m llama3.1:8b
  python summaries.py ./files/ --max-words 200 --continue
        """
    )
    parser.add_argument(
        'folder',
        help='Path to folder containing text files'
    )
    parser.add_argument(
        '-m', '--model',
        default=DEFAULT_MODEL,
        help=f'Ollama model to use (default: {DEFAULT_MODEL})'
    )
    parser.add_argument(
        '--max-words',
        type=int,
        default=500,
        help='Target words in summary (default: 500)'
    )
    parser.add_argument(
        '--continue',
        dest='continue_on_error',
        action='store_true',
        help='Continue processing even if a file fails'
    )
    
    args = parser.parse_args()
    
    # Check Ollama
    try:
        import ollama
        ollama.list()
    except Exception as e:
        print(f"ERROR: Cannot connect to Ollama: {e}")
        print("\nMake sure Ollama is running.")
        sys.exit(1)
    
    try:
        results = summarize_folder(
            args.folder,
            args.model,
            args.max_words,
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
