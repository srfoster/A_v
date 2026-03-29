#!/usr/bin/env python3
"""
Transcription Cleaner
Aligns AWS Transcribe JSON output with the original script to fix transcription errors.
Preserves timestamps while correcting word mismatches.
"""

import re
import json
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
    Tokenize text into words, preserving punctuation separately.
    
    Args:
        text: Input text
    
    Returns:
        List of token strings
    """
    # Split into words and punctuation
    tokens = []
    for match in re.finditer(r"\b\w+(?:'\w+)?\b|[.,!?;:]", text):
        tokens.append(match.group())
    return tokens


def align_sequences(script_tokens, transcription_tokens):
    """
    Align script tokens with transcription tokens using sequence matching.
    
    Args:
        script_tokens: List of tokens from script
        transcription_tokens: List of (token, item_dict) tuples from transcription
    
    Returns:
        List of aligned (script_token, trans_item or None) pairs
    """
    # Use SequenceMatcher to find alignment
    script_lower = [t.lower() for t in script_tokens]
    trans_lower = [t[0].lower() for t in transcription_tokens]
    
    matcher = SequenceMatcher(None, script_lower, trans_lower)
    opcodes = matcher.get_opcodes()
    
    aligned = []
    
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'equal':
            # Perfect match
            for i, j in zip(range(i1, i2), range(j1, j2)):
                aligned.append((script_tokens[i], transcription_tokens[j][1]))
        elif tag == 'replace':
            # Substitution - use script words but keep timestamps
            script_chunk = script_tokens[i1:i2]
            trans_chunk = [t[1] for t in transcription_tokens[j1:j2]]
            
            # Pair them up (if different lengths, just do best effort)
            for idx in range(max(len(script_chunk), len(trans_chunk))):
                script_word = script_chunk[idx] if idx < len(script_chunk) else None
                trans_item = trans_chunk[idx] if idx < len(trans_chunk) else None
                
                if script_word:
                    aligned.append((script_word, trans_item))
        elif tag == 'delete':
            # Script has extra words not in transcription
            for i in range(i1, i2):
                aligned.append((script_tokens[i], None))
        elif tag == 'insert':
            # Transcription has extra words not in script - skip them
            pass
    
    return aligned


def clean_transcription(script_path, json_path, output_path=None):
    """
    Clean transcription JSON using script as reference.
    
    Args:
        script_path: Path to .script file
        json_path: Path to transcription JSON file
        output_path: Optional output path (default: same as json with .clean.json extension)
    
    Returns:
        Path to output file
    """
    script_path = Path(script_path)
    json_path = Path(json_path)
    
    if not script_path.exists():
        raise FileNotFoundError(f"Script file not found: {script_path}")
    
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    
    print(f"Loading script: {script_path}")
    script_text = parse_script_text(script_path)
    script_tokens = tokenize_text(script_text)
    
    print(f"Script tokens: {script_tokens}")
    
    print(f"\nLoading transcription: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract transcription items
    items = data['results']['items']
    trans_tokens = []
    
    for item in items:
        content = item['alternatives'][0]['content']
        trans_tokens.append((content, item))
    
    print(f"Transcription tokens: {[t[0] for t in trans_tokens]}")
    
    print(f"\nAligning sequences...")
    aligned = align_sequences(script_tokens, trans_tokens)
    
    # Show alignment
    print("\nAlignment:")
    corrections = 0
    for script_word, trans_item in aligned:
        if trans_item:
            orig_word = trans_item['alternatives'][0]['content']
            if script_word.lower() != orig_word.lower():
                print(f"  '{orig_word}' -> '{script_word}' (corrected)")
                corrections += 1
            else:
                print(f"  '{orig_word}' = '{script_word}'")
        else:
            print(f"  (missing) -> '{script_word}' (added)")
            corrections += 1
    
    print(f"\nTotal corrections: {corrections}")
    
    # Build corrected items list
    corrected_items = []
    item_id = 0
    
    for script_word, trans_item in aligned:
        if trans_item:
            # Use the transcription item but fix the word
            corrected_item = trans_item.copy()
            corrected_item['id'] = item_id
            corrected_item['alternatives'] = [{'content': script_word, 'confidence': trans_item['alternatives'][0].get('confidence', '1.0')}]
            corrected_items.append(corrected_item)
            item_id += 1
        else:
            # Word exists in script but not in transcription
            # Create a new item without timestamps (punctuation-like)
            is_punctuation = script_word in '.,!?;:'
            corrected_item = {
                'id': item_id,
                'type': 'punctuation' if is_punctuation else 'pronunciation',
                'alternatives': [{'content': script_word, 'confidence': '0.5'}]
            }
            # If it's a pronunciation, we'd need to estimate timestamps, but skip for now
            corrected_items.append(corrected_item)
            item_id += 1
    
    # Rebuild the full transcript text
    transcript_words = []
    for item in corrected_items:
        word = item['alternatives'][0]['content']
        # Add space before words (but not before punctuation)
        if transcript_words and item['type'] != 'punctuation':
            transcript_words.append(' ')
        transcript_words.append(word)
    
    corrected_transcript = ''.join(transcript_words)
    
    # Update the data structure
    data['results']['items'] = corrected_items
    data['results']['transcripts'] = [{'transcript': corrected_transcript}]
    
    # Add metadata about cleaning
    if 'jobName' in data:
        data['jobName'] = data['jobName'] + '_cleaned'
    
    # Determine output path
    if output_path is None:
        stem = json_path.stem
        if stem.endswith('.clean'):
            output_path = json_path
        else:
            output_path = json_path.with_name(f"{stem}.clean.json")
    else:
        output_path = Path(output_path)
    
    print(f"\nWriting cleaned transcription to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nCleaned transcript:")
    print(f"  {corrected_transcript}")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Clean AWS Transcribe JSON using script as reference'
    )
    parser.add_argument(
        'script_file',
        help='Path to .script file'
    )
    parser.add_argument(
        'json_file',
        help='Path to transcription JSON file'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output path for cleaned JSON (default: input.clean.json)'
    )
    
    args = parser.parse_args()
    
    try:
        clean_transcription(args.script_file, args.json_file, args.output)
    except Exception as e:
        print(f"Error: {e}")
        import sys
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
