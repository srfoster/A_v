#!/usr/bin/env python3
"""
Day Summaries Processor
Aggregates all summaries from subfolders and creates a day-level summary.
Processes a day folder containing timestamped video subfolders.

Usage:
    python summaries.py DAY_FOLDER/
    
Output:
    DAY_FOLDER/summaries/day_summary.txt
      
The processor collects all summaries from SUBFOLDER/summaries/* and creates
a meta-summary of the entire day's content.
"""

import sys
import argparse
from pathlib import Path
import subprocess
import logging
from datetime import datetime
import re


DEFAULT_MODEL = 'llama3.2'


def strip_ansi_codes(text):
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
    return ansi_escape.sub('', text)


def setup_logging(folder_path):
    """Set up logging to logs/day_summaries.log in the target folder."""
    folder = Path(folder_path)
    logs_dir = folder / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / 'day_summaries.log'
    
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
    logger.info(f"Day summary generation started")
    logger.info(f"Target folder: {folder}")
    logger.info("="*60)
    
    return logger


def find_all_summaries(day_folder):
    """
    Find all summary files in all subfolders.
    
    Returns list of tuples: (subfolder_name, summary_path)
    """
    all_summaries = []
    
    for subfolder in sorted(day_folder.iterdir()):
        if subfolder.is_dir() and not subfolder.name.startswith('.') and subfolder.name not in ['logs', 'summaries', 'show_all']:
            summaries_dir = subfolder / 'summaries'
            if summaries_dir.exists() and summaries_dir.is_dir():
                summary_files = sorted(summaries_dir.glob('*_summary.txt'))
                for summary_file in summary_files:
                    all_summaries.append((subfolder.name, summary_file))
    
    return all_summaries


def read_summary(summary_path):
    """Read summary file content."""
    try:
        with open(summary_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        return f"[Error reading {summary_path.name}: {str(e)}]"


def create_combined_summary_text(summaries_data):
    """Create a combined text document from all summaries."""
    combined = []
    
    for subfolder_name, summary_path in summaries_data:
        summary_content = read_summary(summary_path)
        base_name = summary_path.stem
        if base_name.endswith('_summary'):
            base_name = base_name[:-8]
        
        combined.append(f"=== {subfolder_name} / {base_name} ===")
        combined.append(summary_content)
        combined.append("")  # Blank line between summaries
    
    return "\n".join(combined)


def generate_meta_summary(combined_text, model='llama3.2', max_words=100, logger=None):
    """
    Generate a meta-summary from the combined summaries using Ollama.
    
    Args:
        combined_text: The combined text of all summaries
        model: Ollama model to use
        max_words: Target word count for meta-summary
        logger: Logger instance
    
    Returns:
        The meta-summary text or None if failed
    """
    prompt = f"""Summarize what videos were created today and their topics. Be concise and factual.
Write a brief list-style summary in {max_words} words or less.
Just state what videos were made and what each covers. No narrative, no themes analysis.

===== VIDEO SUMMARIES =====
{combined_text}

===== DAY SUMMARY ({max_words} words max) ====="""

    try:
        if logger:
            logger.info(f"Generating meta-summary using {model}...")
            logger.info(f"Processing {len(combined_text)} characters of combined summaries")
        
        # Call ollama
        result = subprocess.run(
            ['ollama', 'run', model],
            input=prompt,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            summary = result.stdout.strip()
            # Strip ANSI escape codes from output
            summary = strip_ansi_codes(summary)
            if logger:
                logger.info(f"Generated meta-summary ({len(summary.split())} words)")
            return summary
        else:
            error_msg = f"Ollama failed with return code {result.returncode}"
            if logger:
                logger.error(error_msg)
                if result.stderr:
                    logger.error(f"Error output: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        error_msg = "Ollama command timed out after 5 minutes"
        if logger:
            logger.error(error_msg)
        return None
    except FileNotFoundError:
        error_msg = "Ollama not found. Please install ollama first."
        if logger:
            logger.error(error_msg)
        print(error_msg)
        return None
    except Exception as e:
        error_msg = f"Error running ollama: {str(e)}"
        if logger:
            logger.error(error_msg)
        return None


def process_folder(folder_path, model='llama3.2', max_words=800, logger=None):
    """
    Process day folder and create meta-summary.
    
    Args:
        folder_path: Path to the day folder
        model: Ollama model to use
        max_words: Target word count for meta-summary
        logger: Logger instance
    
    Returns:
        True if successful, False otherwise
    """
    folder = Path(folder_path)
    
    # Find all summaries in subfolders
    summaries_data = find_all_summaries(folder)
    
    if not summaries_data:
        msg = f"No summary files found in subfolders of {folder_path}"
        if logger:
            logger.warning(msg)
        print(msg)
        return False
    
    if logger:
        logger.info(f"Found {len(summaries_data)} summary file(s) across subfolders")
    
    # Create combined summary text
    combined_text = create_combined_summary_text(summaries_data)
    
    if logger:
        logger.info(f"Combined text: {len(combined_text)} characters")
    
    # Create output directory
    output_dir = folder / 'summaries'
    output_dir.mkdir(exist_ok=True)
    
    # Save combined summaries for reference
    combined_file = output_dir / 'all_summaries.txt'
    try:
        with open(combined_file, 'w', encoding='utf-8') as f:
            f.write(combined_text)
        if logger:
            logger.info(f"Saved combined summaries to: {combined_file.name}")
    except Exception as e:
        error_msg = f"Error saving combined summaries: {str(e)}"
        if logger:
            logger.error(error_msg)
        print(error_msg)
    
    # Generate meta-summary
    meta_summary = generate_meta_summary(combined_text, model, max_words, logger)
    
    if not meta_summary:
        if logger:
            logger.error("Failed to generate meta-summary")
        return False
    
    # Save meta-summary
    output_file = output_dir / 'day_summary.txt'
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(meta_summary)
        
        if logger:
            logger.info(f"Created: {output_file.name}")
        
        return True
        
    except Exception as e:
        error_msg = f"Error saving meta-summary: {str(e)}"
        if logger:
            logger.error(error_msg)
        print(error_msg)
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Create a day-level meta-summary from all video summaries',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python summaries.py s:\\Videos\\Raw\\2026-04-04
  python summaries.py /path/to/day/folder/
  python summaries.py ./2026-04-04/ --model llama3.1 --max-words 1000

The processor will collect all summaries from SUBFOLDER/summaries/* files,
combine them, and generate a meta-summary of the entire day.

Output files:
  - DAY_FOLDER/summaries/all_summaries.txt (combined summaries)
  - DAY_FOLDER/summaries/day_summary.txt (meta-summary)
        """
    )
    
    parser.add_argument(
        'folder',
        help='Path to day folder containing video subfolders'
    )
    
    parser.add_argument(
        '--model',
        default=DEFAULT_MODEL,
        help=f'Ollama model to use (default: {DEFAULT_MODEL})'
    )
    
    parser.add_argument(
        '--max-words',
        type=int,
        default=800,
        help='Target word count for meta-summary (default: 800)'
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
        logger.info(f"Using model: {args.model}")
        logger.info(f"Target words: {args.max_words}")
        
        # Process folder
        success = process_folder(folder_path, args.model, args.max_words, logger)
        
        # Report results
        if success:
            output_path = folder_path / 'summaries' / 'day_summary.txt'
            success_msg = f"\n✓ Successfully created day summary at {output_path}"
            logger.info(success_msg)
            print(success_msg)
        else:
            logger.info("Failed to create day summary")
        
        logger.info("="*60)
        logger.info("Session completed")
        logger.info("="*60)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
