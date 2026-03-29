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


def load_transcription(json_path):
    """
    Load word-level timestamps from AWS Transcribe JSON.
    
    Args:
        json_path: Path to transcription JSON file
    
    Returns:
        List of (word, start_time, end_time) tuples
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
            words.append((word, start_time, end_time))
    
    return words


def match_events_to_timestamps(script_text, events, words, original_content):
    """
    Match events in script to timestamps based on their position.
    
    Args:
        script_text: Plain text from script (events removed)
        events: List of (position, event_text) tuples (positions in original content)
        words: List of (word, start_time, end_time) tuples from transcription
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
    for trans_word, start_time, end_time in words:
        trans_word_lower = trans_word.lower()
        
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


def write_instructions(output_path, timestamped_events):
    """
    Write timestamped events to .instructions file.
    
    Args:
        output_path: Path to output .instructions file
        timestamped_events: List of (timestamp, event_text) tuples
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for timestamp, event_text in timestamped_events:
            f.write(f"{timestamp:.3f}\t{event_text}\n")
    
    print(f"Instructions written to: {output_path}")


def compile_script(script_path, json_path, output_path=None):
    """
    Compile a .script file into timestamped .instructions file.
    
    Args:
        script_path: Path to .script file
        json_path: Path to transcription JSON file
        output_path: Optional output path (default: same as script with .instructions extension)
    
    Returns:
        Path to output file
    """
    script_path = Path(script_path)
    json_path = Path(json_path)
    
    if not script_path.exists():
        raise FileNotFoundError(f"Script file not found: {script_path}")
    
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    
    print(f"Parsing script: {script_path}")
    plain_text, events, original_content = parse_script(script_path)
    
    print(f"Found {len(events)} events")
    for pos, event in events:
        print(f"  [{event}] at position {pos}")
    
    print(f"\nLoading transcription: {json_path}")
    words = load_transcription(json_path)
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
    write_instructions(output_path, timestamped_events)
    
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
        'json_file',
        help='Path to transcription JSON file (from AWS Transcribe)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output path for .instructions file (default: same as script with .instructions extension)'
    )
    
    args = parser.parse_args()
    
    try:
        compile_script(args.script_file, args.json_file, args.output)
    except Exception as e:
        print(f"Error: {e}")
        import sys
        sys.exit(1)


if __name__ == '__main__':
    main()
