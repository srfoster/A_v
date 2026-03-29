#!/usr/bin/env python3
"""
Script Compiler
Compiles .script files with embedded events into timestamped .instructions files
using word-level timestamps from AWS Transcribe JSON output.
"""

import re
import json
import argparse
from pathlib import Path


def parse_script(script_path):
    """
    Parse a .script file to extract text and embedded events.
    
    Args:
        script_path: Path to .script file
    
    Returns:
        tuple: (plain_text, events, original_content)
            plain_text: Script text with events removed
            events: List of (position, event_text) tuples (position in original content)
            original_content: Original script content with brackets
    """
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all events in square brackets
    events = []
    
    # Pattern to match [event content]
    pattern = r'\[([^\]]+)\]'
    
    # Find all matches with their positions in original content
    for match in re.finditer(pattern, content):
        event_content = match.group(1)
        # Position where the bracket starts in original content
        position = match.start()
        events.append((position, event_content))
    
    # Remove all bracketed events to get plain text
    plain_text = re.sub(pattern, '', content)
    
    # Normalize whitespace while preserving general structure
    # Replace multiple spaces with single space
    plain_text = re.sub(r' +', ' ', plain_text)
    # Clean up spaces around newlines
    plain_text = re.sub(r' *\n *', '\n', plain_text)
    # Remove leading/trailing whitespace
    plain_text = plain_text.strip()
    
    return plain_text, events, content


def load_transcription(transcription_path):
    """
    Load word-level timestamps from transcription file (JSON or .words.txt).
    
    Args:
        transcription_path: Path to transcription file (.json or .words.txt)
    
    Returns:
        List of (word, start_time, end_time) tuples
    """
    transcription_path = Path(transcription_path)
    
    # Check file extension to determine format
    if transcription_path.suffix == '.txt' and '.words' in transcription_path.name:
        # Load from .words.txt format
        return load_words_txt(transcription_path)
    else:
        # Load from JSON format
        return load_transcription_json(transcription_path)


def load_transcription_json(json_path):
    """
    Load word-level timestamps from AWS Transcribe JSON.
    
    Args:
        json_path: Path to transcription JSON file
    
    Returns:
        List of (word, start_time, end_time, comment) tuples
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    words = []
    items = data['results']['items']
    
    for item in items:
        if item['type'] == 'pronunciation':
            word = item['alternatives'][0]['content']
            start_time = float(item['start_time'])
            end_time = float(item['end_time'])
            words.append((word, start_time, end_time, None))
    
    return words


def load_words_txt(words_path):
    """
    Load word-level timestamps from .words.txt file.
    
    Args:
        words_path: Path to .words.txt file
    
    Returns:
        List of (word, start_time, end_time, comment) tuples
    """
    words = []
    with open(words_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Parse format: start_time\tend_time\tword  // original_word
            parts = line.split('\t')
            if len(parts) >= 3:
                start_time = float(parts[0])
                end_time = float(parts[1])
                # Extract word and comment
                word_and_comment = parts[2]
                if '//' in word_and_comment:
                    word_part, comment_part = word_and_comment.split('//', 1)
                    word = word_part.strip()
                    comment = comment_part.strip()
                else:
                    word = word_and_comment.strip()
                    comment = None
                words.append((word, start_time, end_time, comment))
    
    return words


def match_events_to_timestamps(script_text, events, words, original_content):
    """
    Match events in script to timestamps based on their position.
    
    Args:
        script_text: Plain text from script (events removed)
        events: List of (position, event_text) tuples (positions in original content)
        words: List of (word, start_time, end_time, comment) tuples from transcription
        original_content: Original script content with brackets
    
    Returns:
        List of (timestamp, event_text) tuples, sorted by timestamp
    """
    # Tokenize script text (split on whitespace and punctuation)
    script_words = []
    word_positions = []  # Start position of each word in script_text
    
    # Split keeping track of positions in plain text
    for match in re.finditer(r"\b\w+(?:'\w+)?\b", script_text):
        word = match.group()
        script_words.append(word.lower())
        word_positions.append(match.start())
    
    # Match script words to transcribed words
    # Build a mapping from word text to timestamp
    word_to_timestamp = {}
    
    script_idx = 0
    for word, start_time, end_time, comment in words:
        trans_word_lower = word.lower()
        
        # Find matching word in script
        if script_idx < len(script_words):
            script_word = script_words[script_idx]
            
            # Match if words are similar (handle minor transcription differences)
            if script_word == trans_word_lower or trans_word_lower.startswith(script_word) or script_word.startswith(trans_word_lower):
                # Map this word to the timestamp
                word_to_timestamp[script_word] = (start_time, end_time)
                script_idx += 1
    
    # Now match events to timestamps
    timestamped_events = []
    
    for event_pos, event_text in events:
        # Find the word that comes immediately before the event bracket in original content
        # Look backwards from event_pos to find the last word
        text_before = original_content[:event_pos]
        
        # Find the last word before the bracket
        word_matches = list(re.finditer(r"\b\w+(?:'\w+)?\b", text_before))
        
        if word_matches:
            last_word_match = word_matches[-1]
            last_word = last_word_match.group().lower()
            
            # Look up this word's timestamp
            if last_word in word_to_timestamp:
                # Use the START time of the word before the event
                timestamp = word_to_timestamp[last_word][0]
                timestamped_events.append((timestamp, event_text))
            else:
                # Word not found in transcription, use 0.0
                timestamped_events.append((0.0, event_text))
        else:
            # No word found before event, use 0.0
            timestamped_events.append((0.0, event_text))
    
    # Sort by timestamp
    timestamped_events.sort(key=lambda x: x[0])
    
    return timestamped_events


def write_instructions(output_path, words, timestamped_events):
    """
    Write instructions file with words and events interleaved.
    
    Args:
        output_path: Path to output .instructions file
        words: List of (word, start_time, end_time, comment) tuples
        timestamped_events: List of (timestamp, event_text) tuples
    """
    # Build all lines first to determine column widths
    lines = []
    
    # Convert words to output format
    for word, start_time, end_time, comment in words:
        start_str = f"{start_time:.3f}"
        end_str = f"{end_time:.3f}"
        word_str = word
        if comment:
            word_str = f"{word}  // {comment}"
        lines.append((start_time, start_str, end_str, word_str, False))
    
    # Add events with * as end_time marker
    for timestamp, event_text in timestamped_events:
        start_str = f"{timestamp:.3f}"
        lines.append((timestamp, start_str, "*", f"[{event_text}]", True))
    
    # Sort by timestamp, keeping insertion order for ties
    lines.sort(key=lambda x: x[0])
    
    # Calculate column widths
    col1_width = max(len(line[1]) for line in lines)
    col2_width = max(len(line[2]) for line in lines)
    
    # Write to file with aligned columns
    with open(output_path, 'w', encoding='utf-8') as f:
        for _, start_str, end_str, content, is_event in lines:
            line = f"{start_str:<{col1_width}}\t{end_str:<{col2_width}}\t{content}"
            f.write(line + '\n')
    
    print(f"Instructions written to: {output_path}")


def compile_script(script_path, transcription_path, output_path=None):
    """
    Compile a .script file into timestamped .instructions file.
    
    Args:
        script_path: Path to .script file
        transcription_path: Path to transcription file (.json or .words.txt)
        output_path: Optional output path (default: same as script with .instructions extension)
    
    Returns:
        Path to output file
    """
    script_path = Path(script_path)
    transcription_path = Path(transcription_path)
    
    if not script_path.exists():
        raise FileNotFoundError(f"Script file not found: {script_path}")
    
    if not transcription_path.exists():
        raise FileNotFoundError(f"Transcription file not found: {transcription_path}")
    
    print(f"Parsing script: {script_path}")
    plain_text, events, original_content = parse_script(script_path)
    
    print(f"Found {len(events)} events")
    for pos, event in events:
        print(f"  [{event}] at position {pos}")
    
    print(f"\nLoading transcription: {transcription_path}")
    words = load_transcription(transcription_path)
    print(f"Loaded {len(words)} words with timestamps")
    
    print("\nMatching events to timestamps...")
    timestamped_events = match_events_to_timestamps(plain_text, events, words, original_content)
    
    print("\nTimestamped events:")
    for timestamp, event in timestamped_events:
        print(f"  {timestamp:.3f}s: [{event}]")
    
    # Determine output path
    if output_path is None:
        output_path = script_path.with_suffix('.instructions')
    else:
        output_path = Path(output_path)
    
    print(f"\nWriting output...")
    write_instructions(output_path, words, timestamped_events)
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Compile .script files with events into timestamped .instructions files'
    )
    parser.add_argument(
        'script_file',
        help='Path to .script file'
    )
    parser.add_argument(
        'transcription_file',
        help='Path to transcription file (.json from AWS Transcribe or .words.txt)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output path for .instructions file (default: same as script with .instructions extension)'
    )
    
    args = parser.parse_args()
    
    try:
        compile_script(args.script_file, args.transcription_file, args.output)
    except Exception as e:
        print(f"Error: {e}")
        import sys
        sys.exit(1)


if __name__ == '__main__':
    main()
