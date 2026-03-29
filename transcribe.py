#!/usr/bin/env python3
"""
AWS Transcription Script
Transcribes audio from audio or video files using AWS Transcribe.
Automatically extracts audio from video files using ffmpeg.
"""

import os
import sys
import time
import argparse
import subprocess
import json
import re
from pathlib import Path
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

# AWS Configuration
DEFAULT_REGION = 'us-west-2'
DEFAULT_BUCKET = 'av-transcriptions-west'

# Video file extensions that require audio extraction
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}
# Audio file extensions
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'}


def extract_audio_from_video(video_path, output_path=None):
    """
    Extract audio from video file using ffmpeg.
    
    Args:
        video_path: Path to video file
        output_path: Optional output path for audio file (default: temp file)
    
    Returns:
        Path to extracted audio file
    """
    if output_path is None:
        video_name = Path(video_path).stem
        output_path = f"temp_audio_{video_name}_{int(time.time())}.mp3"
    
    print(f"Extracting audio from {video_path}...")
    
    # Use ffmpeg to extract audio
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vn',  # No video
        '-acodec', 'libmp3lame',  # Use MP3 codec
        '-q:a', '2',  # High quality
        '-y',  # Overwrite output file
        output_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        print(f"Audio extracted successfully: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e.stderr.decode()}")
        raise
    except FileNotFoundError:
        print("Error: ffmpeg not found. Please install ffmpeg:")
        print("  Windows: choco install ffmpeg  or  download from https://ffmpeg.org/")
        print("  Mac: brew install ffmpeg")
        print("  Linux: apt-get install ffmpeg  or  yum install ffmpeg")
        sys.exit(1)


def upload_to_s3(file_path, bucket_name, s3_key=None, region=DEFAULT_REGION):
    """
    Upload file to S3 bucket.
    
    Args:
        file_path: Local file path
        bucket_name: S3 bucket name
        s3_key: Optional S3 key (default: filename with timestamp)
        region: AWS region
    
    Returns:
        S3 URI of uploaded file
    """
    s3_client = boto3.client('s3', region_name=region)
    
    if s3_key is None:
        filename = Path(file_path).name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        s3_key = f"transcribe-input/{timestamp}_{filename}"
    
    print(f"Uploading {file_path} to s3://{bucket_name}/{s3_key}...")
    
    try:
        s3_client.upload_file(file_path, bucket_name, s3_key)
        s3_uri = f"s3://{bucket_name}/{s3_key}"
        print(f"Upload complete: {s3_uri}")
        return s3_uri
    except ClientError as e:
        print(f"Error uploading to S3: {e}")
        raise


def start_transcription_job(job_name, s3_uri, language_code='en-US', output_bucket=None, region=DEFAULT_REGION):
    """
    Start AWS Transcribe job.
    
    Args:
        job_name: Unique job name
        s3_uri: S3 URI of media file
        language_code: Language code (default: en-US)
        output_bucket: Optional output bucket for results
        region: AWS region
    
    Returns:
        Job name
    """
    transcribe_client = boto3.client('transcribe', region_name=region)
    
    print(f"Starting transcription job: {job_name}")
    
    job_args = {
        'TranscriptionJobName': job_name,
        'Media': {'MediaFileUri': s3_uri},
        'MediaFormat': Path(s3_uri).suffix.lstrip('.').lower(),
        'LanguageCode': language_code
    }
    
    if output_bucket:
        job_args['OutputBucketName'] = output_bucket
    
    try:
        transcribe_client.start_transcription_job(**job_args)
        print(f"Transcription job started successfully")
        return job_name
    except ClientError as e:
        print(f"Error starting transcription job: {e}")
        raise


def wait_for_transcription(job_name, poll_interval=5, region=DEFAULT_REGION):
    """
    Wait for transcription job to complete.
    
    Args:
        job_name: Transcription job name
        poll_interval: Seconds between status checks
        region: AWS region
    
    Returns:
        Job status response
    """
    transcribe_client = boto3.client('transcribe', region_name=region)
    
    print(f"Waiting for transcription to complete...")
    
    while True:
        response = transcribe_client.get_transcription_job(
            TranscriptionJobName=job_name
        )
        status = response['TranscriptionJob']['TranscriptionJobStatus']
        
        if status == 'COMPLETED':
            print("Transcription completed!")
            return response
        elif status == 'FAILED':
            failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown')
            print(f"Transcription failed: {failure_reason}")
            raise Exception(f"Transcription failed: {failure_reason}")
        else:
            print(f"Status: {status}... waiting {poll_interval}s")
            time.sleep(poll_interval)


def download_transcript(transcript_uri, region=DEFAULT_REGION):
    """
    Download and parse transcript from URI.
    
    Args:
        transcript_uri: URI of transcript JSON (S3 URL or S3 URI)
        region: AWS region
    
    Returns:
        Transcript dictionary
    """
    print(f"Downloading transcript from {transcript_uri}")
    
    # Parse S3 URL or URI to get bucket and key
    if transcript_uri.startswith('s3://'):
        # s3://bucket/key format
        parts = transcript_uri[5:].split('/', 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ''
    elif 's3' in transcript_uri and 'amazonaws.com' in transcript_uri:
        # https://s3.region.amazonaws.com/bucket/key or https://bucket.s3.region.amazonaws.com/key
        import re
        # Try bucket.s3.region.amazonaws.com/key format
        match = re.search(r'https://([^.]+)\.s3[^/]*amazonaws\.com/(.+)', transcript_uri)
        if match:
            bucket = match.group(1)
            key = match.group(2)
        else:
            # Try s3.region.amazonaws.com/bucket/key format
            match = re.search(r'https://s3[^/]*amazonaws\.com/([^/]+)/(.+)', transcript_uri)
            if match:
                bucket = match.group(1)
                key = match.group(2)
            else:
                raise ValueError(f"Could not parse S3 URL: {transcript_uri}")
    else:
        raise ValueError(f"Unsupported transcript URI format: {transcript_uri}")
    
    # Download using boto3 S3 client (uses proper credentials)
    s3_client = boto3.client('s3', region_name=region)
    
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        data = json.loads(response['Body'].read().decode())
        return data
    except ClientError as e:
        print(f"Error downloading transcript from S3: {e}")
        raise


def save_transcript(transcript_data, output_path):
    """
    Save transcript to file.
    
    Args:
        transcript_data: Transcript dictionary
        output_path: Output file path (typically .json)
    """
    base_path = Path(output_path).with_suffix('')
    
    # Extract the actual text
    text = transcript_data['results']['transcripts'][0]['transcript']
    
    # Save as plain text
    txt_path = base_path.with_suffix('.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    print(f"Transcript saved to: {txt_path}")
    
    # Save word-level timestamps
    if 'items' in transcript_data['results']:
        words_path = base_path.with_suffix('.words.txt')
        with open(words_path, 'w', encoding='utf-8') as f:
            for item in transcript_data['results']['items']:
                if item['type'] == 'pronunciation':
                    word = item['alternatives'][0]['content']
                    start = float(item.get('start_time', 0))
                    end = float(item.get('end_time', 0))
                    f.write(f"{start:.3f}\t{end:.3f}\t{word}\n")
                elif item['type'] == 'punctuation':
                    # Append punctuation to previous line if possible
                    punct = item['alternatives'][0]['content']
                    # Note: punctuation doesn't have timestamps
        
        print(f"Word timestamps saved to: {words_path}")
        
        # Also save in SRT subtitle format
        srt_path = base_path.with_suffix('.srt')
        with open(srt_path, 'w', encoding='utf-8') as f:
            subtitle_num = 1
            words = []
            for item in transcript_data['results']['items']:
                if item['type'] == 'pronunciation':
                    words.append(item)
            
            # Group words into subtitle chunks (5-10 words each)
            chunk_size = 8
            for i in range(0, len(words), chunk_size):
                chunk = words[i:i+chunk_size]
                if not chunk:
                    continue
                    
                start_time = float(chunk[0].get('start_time', 0))
                end_time = float(chunk[-1].get('end_time', 0))
                text = ' '.join(w['alternatives'][0]['content'] for w in chunk)
                
                # Format times as SRT timestamps (HH:MM:SS,mmm)
                start_str = f"{int(start_time//3600):02d}:{int((start_time%3600)//60):02d}:{int(start_time%60):02d},{int((start_time%1)*1000):03d}"
                end_str = f"{int(end_time//3600):02d}:{int((end_time%3600)//60):02d}:{int(end_time%60):02d},{int((end_time%1)*1000):03d}"
                
                f.write(f"{subtitle_num}\n")
                f.write(f"{start_str} --> {end_str}\n")
                f.write(f"{text}\n\n")
                subtitle_num += 1
        
        print(f"SRT subtitles saved to: {srt_path}")
    
    # Save full JSON
    json_path = base_path.with_suffix('.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, indent=2)
    
    print(f"Full transcript data saved to: {json_path}")
    
    return text


def transcribe_file(input_file, bucket_name=DEFAULT_BUCKET, language_code='en-US', output_dir=None, cleanup=True, region=DEFAULT_REGION):
    """
    Main transcription workflow.
    
    Args:
        input_file: Path to input audio/video file
        bucket_name: S3 bucket name (default: av-transcriptions-west)
        language_code: Language code (default: en-US)
        output_dir: Output directory for transcript (default: same as input)
        cleanup: Whether to clean up temporary files
        region: AWS region (default: us-west-2)
    
    Returns:
        Transcript text
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Determine file type and prepare audio file
    file_ext = input_path.suffix.lower()
    temp_audio = None
    
    if file_ext in VIDEO_EXTENSIONS:
        # Extract audio from video
        audio_file = extract_audio_from_video(str(input_path))
        temp_audio = audio_file
    elif file_ext in AUDIO_EXTENSIONS:
        audio_file = str(input_path)
    else:
        print(f"Warning: Unknown file extension {file_ext}, attempting to process anyway...")
        audio_file = str(input_path)
    
    try:
        # Generate unique job name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        job_name = f"transcribe_{input_path.stem}_{timestamp}"
        
        # Upload to S3
        s3_uri = upload_to_s3(audio_file, bucket_name, region=region)
        
        # Start transcription
        start_transcription_job(job_name, s3_uri, language_code, bucket_name, region=region)
        
        # Wait for completion
        result = wait_for_transcription(job_name, region=region)
        
        # Download transcript
        transcript_uri = result['TranscriptionJob']['Transcript']['TranscriptFileUri']
        transcript_data = download_transcript(transcript_uri, region=region)
        
        # Save transcript
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = input_path.parent
        
        output_path = output_dir / f"{input_path.stem}.json"
        text = save_transcript(transcript_data, str(output_path))
        
        print(f"\n{'='*60}")
        print("TRANSCRIPT:")
        print('='*60)
        print(text)
        print('='*60)
        
        return text
        
    finally:
        # Cleanup temporary audio file
        if temp_audio and cleanup and os.path.exists(temp_audio):
            print(f"Cleaning up temporary file: {temp_audio}")
            os.remove(temp_audio)


def main():
    parser = argparse.ArgumentParser(
        description='Transcribe audio/video files using AWS Transcribe'
    )
    parser.add_argument(
        'input_file',
        help='Path to input audio or video file'
    )
    parser.add_argument(
        '-b', '--bucket',
        default=DEFAULT_BUCKET,
        help=f'S3 bucket name for storing media files (default: {DEFAULT_BUCKET})'
    )
    parser.add_argument(
        '-r', '--region',
        default=DEFAULT_REGION,
        help=f'AWS region (default: {DEFAULT_REGION})'
    )
    parser.add_argument(
        '-l', '--language',
        default='en-US',
        help='Language code (default: en-US)'
    )
    parser.add_argument(
        '-o', '--output-dir',
        help='Output directory for transcript (default: same as input file)'
    )
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Keep temporary audio files (for video inputs)'
    )
    
    args = parser.parse_args()
    
    try:
        transcribe_file(
            args.input_file,
            args.bucket,
            args.language,
            args.output_dir,
            cleanup=not args.no_cleanup,
            region=args.region
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
