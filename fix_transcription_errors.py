#!/usr/bin/env python3
"""
Transcription Error Fixer
Aligns word-level transcription files (.words.txt) with the original script
to fix transcription errors while preserving timestamps.
"""

import re
import argparse
from pathlib import Path
from difflib import SequenceMatcher


def parse_script_text(script_path):
    """
    Parse a .script file and extract the plain text (removing events).
    
    Args:
        script_path: Path to .script file
    
    Returns:
        Plain text with events removed and normalized
    """
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove events in square brackets
    plain_text = re.sub(r'\[([^\]]+)\]', '', content)
    
    # Normalize whitespace
    plain_text = re.sub(r' +', ' ', plain_text)
    plain_text = re.sub(r' *\n *', '\n', plain_text)
    plain_text = plain_text.strip()
    
    return plain_text


def tokenize_text(text):
    """
    Tokenize text into words (excluding punctuation).
    
    Args:
        text: Input text
    
    Returns:
        List of word strings
    """
    # Split into words only (no punctuation)
    tokens = []
    for match in re.finditer(r"\b\w+(?:'\w+)?\b", text):
        tokens.append(match.group())
    return tokens


def load_words_file(words_path):
    """
    Load word-level timestamps from .words.txt file.
    
    Args:
        words_path: Path to .words.txt file
    
    Returns:
        List of (start_time, end_time, word) tuples
    """
    words = []
    with open(words_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('\t')
            if len(parts) >= 3:
                start_time = parts[0]
                end_time = parts[1]
                word = parts[2]
                words.append((start_time, end_time, word))
    
    return words


def align_sequences(script_tokens, transcription_words):
    """
    Align script tokens with transcription words using sequence matching.
    
    Args:
        script_tokens: List of tokens from script
        transcription_words: List of (start_time, end_time, word) tuples
    
    Returns:
        List of aligned (script_word, (start, end, trans_word) or None) pairs
    """
    # Use SequenceMatcher to find alignment
    script_lower = [t.lower() for t in script_tokens]
    trans_lower = [w[2].lower() for w in transcription_words]
    
    matcher = SequenceMatcher(None, script_lower, trans_lower)
    opcodes = matcher.get_opcodes()
    
    aligned = []
    
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'equal':
            # Perfect match
            for i, j in zip(range(i1, i2), range(j1, j2)):
                aligned.append((script_tokens[i], transcription_words[j]))
        elif tag == 'replace':
            # Substitution - use script words but keep timestamps
            script_chunk = script_tokens[i1:i2]
            trans_chunk = transcription_words[j1:j2]
            
            # Pair them up (if different lengths, just do best effort)
            for idx in range(max(len(script_chunk), len(trans_chunk))):
                script_word = script_chunk[idx] if idx < len(script_chunk) else None
                trans_entry = trans_chunk[idx] if idx < len(trans_chunk) else None
                
                if script_word:
                    aligned.append((script_word, trans_entry))
        elif tag == 'delete':
            # Script has extra words not in transcription
            for i in range(i1, i2):
                aligned.append((script_tokens[i], None))
        elif tag == 'insert':
            # Transcription has extra words not in script - skip them
            pass
    
    return aligned


def fix_transcription_errors(script_path, words_path, output_path=None):
    """
    Fix transcription errors in .words.txt file using script as reference.
    
    Args:
        script_path: Path to .script file
        words_path: Path to .words.txt file
        output_path: Optional output path (default: same as words with .fixed.words.txt)
    
    Returns:
        Path to output file
    """
    script_path = Path(script_path)
    words_path = Path(words_path)
    
    if not script_path.exists():
        raise FileNotFoundError(f"Script file not found: {script_path}")
    
    if not words_path.exists():
        raise FileNotFoundError(f"Words file not found: {words_path}")
    
    print(f"Loading script: {script_path}")
    script_text = parse_script_text(script_path)
    script_tokens = tokenize_text(script_text)
    
    print(f"Script words: {script_tokens}")
    
    print(f"\nLoading transcription: {words_path}")
    trans_words = load_words_file(words_path)
    
    print(f"Transcription words: {[w[2] for w in trans_words]}")
    
    print(f"\nAligning sequences...")
    aligned = align_sequences(script_tokens, trans_words)
    
    # Show alignment and build output
    print("\nAlignment:")
    corrections = 0
    output_lines = []
    
    for script_word, trans_entry in aligned:
        if trans_entry:
            start_time, end_time, orig_word = trans_entry
            if script_word.lower() != orig_word.lower():
                # Corrected word
                output_line = f"{start_time}\t{end_time}\t{script_word}  // {orig_word}"
                print(f"  '{orig_word}' -> '{script_word}' (corrected)")
                corrections += 1
            else:
                # Unchanged word
                output_line = f"{start_time}\t{end_time}\t{script_word}"
                print(f"  '{orig_word}' = '{script_word}'")
            
            output_lines.append(output_line)
        else:
            # Word exists in script but not in transcription (no timestamp available)
            print(f"  (missing) -> '{script_word}' (no timestamp)")
            # Skip words without timestamps for now
    
    print(f"\nTotal corrections: {corrections}")
    
    # Determine output path
    if output_path is None:
        stem = words_path.stem
        if stem.endswith('.fixed'):
            output_path = words_path
        elif stem.endswith('.words'):
            # Replace .words with .fixed.words
            base_stem = stem[:-6]  # Remove '.words'
            output_path = words_path.with_name(f"{base_stem}.fixed.words.txt")
        else:
            output_path = words_path.with_name(f"{stem}.fixed.txt")
    else:
        output_path = Path(output_path)
    
    print(f"\nWriting fixed transcription to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        for line in output_lines:
            f.write(line + '\n')
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Fix transcription errors in .words.txt files using script as reference'
    )
    parser.add_argument(
        'script_file',
        help='Path to .script file'
    )
    parser.add_argument(
        'words_file',
        help='Path to .words.txt file'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output path for fixed words file (default: input.fixed.words.txt)'
    )
    
    args = parser.parse_args()
    
    try:
        fix_transcription_errors(args.script_file, args.words_file, args.output)
    except Exception as e:
        print(f"Error: {e}")
        import sys
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
