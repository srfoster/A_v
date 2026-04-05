#!/usr/bin/env python3
"""
Camera Frame Capture Script
Captures frames from all available cameras and saves them with timestamp naming.
"""

import cv2
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime


def find_obs_camera():
    """
    Find the OBS Virtual Camera among available video devices.
    
    Returns:
        Camera index if found, None otherwise
    """
    # Try first 10 camera indices
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            # Try to read the backend name
            backend = cap.getBackendName()
            
            # Check if this is OBS Virtual Camera
            # OBS typically shows up with "OBS" in the name on Windows
            ret, frame = cap.read()
            if ret:
                # If we can read a frame, this camera works
                cap.release()
                # You might want to manually verify which index is OBS
                # For now, we'll use index 0 (default) or let user specify
                return i
            cap.release()
    return None


def list_cameras(max_test=10):
    """
    List all available camera devices.
    
    Args:
        max_test: Maximum number of camera indices to test
    """
    print("Available cameras:")
    found = []
    
    for i in range(max_test):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                height, width = frame.shape[:2]
                backend = cap.getBackendName()
                print(f"  [{i}] Camera {i} - {width}x{height} ({backend})")
                found.append(i)
            cap.release()
    
    if not found:
        print("  No cameras found")
    
    return found


def capture_frame(camera_index=0, output_base_dir='S:\\', prefix='screenshot', verbose=False):
    """
    Capture a frame from the specified camera and save it.
    
    Args:
        camera_index: Camera device index (default: 0)
        output_base_dir: Base directory for output (default: S:\)
        prefix: Filename prefix (default: 'screenshot')
        verbose: Print detailed information
    
    Returns:
        Path to saved image or None if failed
    """
    # Get current date and time
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H-%M-%S')
    
    # Create date-based directory
    output_dir = Path(output_base_dir) / 'Videos' / 'Raw' / date_str
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename with camera index and timestamp
    filename = f"{prefix}_cam{camera_index}_{time_str}.png"
    output_path = output_dir / filename
    
    if verbose:
        print(f"Attempting to capture from camera {camera_index}...")
    
    # Open camera
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        if verbose:
            print(f"  Camera {camera_index}: Not accessible")
        return None
    
    # Read frame
    ret, frame = cap.read()
    
    if not ret:
        if verbose:
            print(f"  Camera {camera_index}: Could not read frame")
        cap.release()
        return None
    
    # Get frame info
    height, width = frame.shape[:2]
    
    # Save frame
    cv2.imwrite(str(output_path), frame)
    
    # Release camera
    cap.release()
    
    # Verify file was created
    if output_path.exists():
        file_size = output_path.stat().st_size
        print(f"✓ Camera {camera_index}: {output_path} ({width}x{height})")
        return output_path
    else:
        if verbose:
            print(f"  Camera {camera_index}: File creation failed")
        return None


def capture_all_cameras(output_base_dir='S:\\', prefix='screenshot', max_cameras=10, verbose=False):
    """
    Capture frames from all available cameras.
    
    Args:
        output_base_dir: Base directory for output (default: S:\)
        prefix: Filename prefix (default: 'screenshot')
        max_cameras: Maximum number of camera indices to test (default: 10)
        verbose: Print detailed information
    
    Returns:
        List of paths to saved images
    """
    print(f"Scanning cameras 0-{max_cameras-1}...")
    saved_files = []
    
    for i in range(max_cameras):
        result = capture_frame(
            camera_index=i,
            output_base_dir=output_base_dir,
            prefix=prefix,
            verbose=verbose
        )
        if result:
            saved_files.append(result)
    
    return saved_files


def main():
    parser = argparse.ArgumentParser(
        description='Capture frames from all available cameras',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Capture from all available cameras
  python capture_frame.py
  
  # List available cameras
  python capture_frame.py --list
  
  # Use custom prefix
  python capture_frame.py -p desk_view
  
  # Capture from specific camera only
  python capture_frame.py -c 3
  
  # Verbose output
  python capture_frame.py -v
        """
    )
    
    parser.add_argument(
        '-c', '--camera',
        type=int,
        help='Capture from specific camera index only (default: capture all)'
    )
    parser.add_argument(
        '-o', '--output-dir',
        default='S:\\',
        help='Base output directory (default: S:\\)'
    )
    parser.add_argument(
        '-p', '--prefix',
        default='screenshot',
        help='Filename prefix (default: screenshot)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Print detailed information'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available cameras and exit'
    )
    
    args = parser.parse_args()
    
    # List cameras if requested
    if args.list:
        list_cameras()
        return
    
    # Capture frame(s)
    try:
        if args.camera is not None:
            # Capture from specific camera
            result = capture_frame(
                camera_index=args.camera,
                output_base_dir=args.output_dir,
                prefix=args.prefix,
                verbose=args.verbose
            )
            if result:
                sys.exit(0)
            else:
                print(f"Failed to capture from camera {args.camera}")
                sys.exit(1)
        else:
            # Capture from all cameras
            results = capture_all_cameras(
                output_base_dir=args.output_dir,
                prefix=args.prefix,
                verbose=args.verbose
            )
            
            if results:
                print(f"\nCaptured {len(results)} frame(s)")
                sys.exit(0)
            else:
                print("\nNo cameras found or all captures failed")
                sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
