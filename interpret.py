#!/usr/bin/env python3
"""
Instruction Interpreter
Plays video while interpreting timestamped instructions to display graphics.
"""

import sys
import argparse
import re
import tempfile
import subprocess
from pathlib import Path
import pygame
import cv2

# Debug mode - show position annotations
DEBUG = False


class State:
    """Application state manager."""
    
    def __init__(self, screen_width=800, screen_height=600):
        self.words = []  # Word buffer (not displayed)
        self.objects = []  # List of displayable objects (circles, etc.)
        self.next_var_id = 0
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.center_x = screen_width // 2
        self.center_y = screen_height // 2
    
    def add_word(self, word):
        """Add a word to the word buffer."""
        self.words.append(word)
    
    def add_object(self, obj):
        """Add a displayable object to state."""
        var_name = f"_var{self.next_var_id}"
        self.next_var_id += 1
        self.objects.append(obj)
        return var_name
    
    def get_displayable_objects(self):
        """Get all objects that should be displayed."""
        return self.objects


class Circle:
    """Circle display object."""
    
    def __init__(self, radius, color, x=None, y=None):
        self.radius = radius
        self.color = self.parse_color(color)
        # Position will be set to center if not specified
        self.x = x
        self.y = y
    
    def parse_color(self, color_str):
        """Parse color string to RGB tuple."""
        # Remove quotes if present
        color_str = color_str.strip('"\'')
        
        # Common color names
        colors = {
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'yellow': (255, 255, 0),
            'cyan': (0, 255, 255),
            'magenta': (255, 0, 255),
            'white': (255, 255, 255),
            'black': (0, 0, 0),
            'orange': (255, 165, 0),
            'purple': (128, 0, 128),
        }
        
        color_lower = color_str.lower()
        if color_lower in colors:
            return colors[color_lower]
        
        # Try parsing as hex color
        if color_str.startswith('#'):
            hex_str = color_str[1:]
            if len(hex_str) == 6:
                r = int(hex_str[0:2], 16)
                g = int(hex_str[2:4], 16)
                b = int(hex_str[4:6], 16)
                return (r, g, b)
        
        # Default to white if parsing fails
        return (255, 255, 255)
    
    def draw(self, surface, default_x=None, default_y=None):
        """Draw the circle on the given surface."""
        x = self.x if self.x is not None else default_x
        y = self.y if self.y is not None else default_y
        pygame.draw.circle(surface, self.color, (int(x), int(y)), int(self.radius))
        
        # Debug: show position annotation
        if DEBUG:
            print(f"DEBUG: Drawing circle at ({int(x)}, {int(y)}) with radius {int(self.radius)}, color {self.color}")
            # Draw crosshair at center
            pygame.draw.line(surface, (255, 0, 0), (int(x) - 20, int(y)), (int(x) + 20, int(y)), 2)
            pygame.draw.line(surface, (255, 0, 0), (int(x), int(y) - 20), (int(x), int(y) + 20), 2)
            # Draw position text
            font = pygame.font.Font(None, 24)
            text = font.render(f"({int(x)}, {int(y)})", True, (255, 255, 0))
            surface.blit(text, (int(x) + 10, int(y) + 10))


class Square:
    """Square display object."""
    
    def __init__(self, size, color, x=None, y=None):
        self.size = size
        self.color = self.parse_color(color)
        # Position will be set to center if not specified
        self.x = x
        self.y = y
    
    def parse_color(self, color_str):
        """Parse color string to RGB tuple."""
        # Remove quotes if present
        color_str = color_str.strip('"\'')
        
        # Common color names
        colors = {
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'yellow': (255, 255, 0),
            'cyan': (0, 255, 255),
            'magenta': (255, 0, 255),
            'white': (255, 255, 255),
            'black': (0, 0, 0),
            'orange': (255, 165, 0),
            'purple': (128, 0, 128),
        }
        
        color_lower = color_str.lower()
        if color_lower in colors:
            return colors[color_lower]
        
        # Try parsing as hex color
        if color_str.startswith('#'):
            hex_str = color_str[1:]
            if len(hex_str) == 6:
                r = int(hex_str[0:2], 16)
                g = int(hex_str[2:4], 16)
                b = int(hex_str[4:6], 16)
                return (r, g, b)
        
        # Default to white if parsing fails
        return (255, 255, 255)
    
    def draw(self, surface, default_x=None, default_y=None):
        """Draw the square on the given surface."""
        x = self.x if self.x is not None else default_x
        y = self.y if self.y is not None else default_y
        # Draw square centered at x, y
        half_size = self.size / 2
        rect = pygame.Rect(int(x - half_size), int(y - half_size), int(self.size), int(self.size))
        pygame.draw.rect(surface, self.color, rect)
        
        # Debug: show position annotation
        if DEBUG:
            print(f"DEBUG: Drawing square at ({int(x)}, {int(y)}) with size {int(self.size)}, color {self.color}")
            # Draw crosshair at center
            pygame.draw.line(surface, (255, 0, 0), (int(x) - 20, int(y)), (int(x) + 20, int(y)), 2)
            pygame.draw.line(surface, (255, 0, 0), (int(x), int(y) - 20), (int(x), int(y) + 20), 2)
            # Draw position text
            font = pygame.font.Font(None, 24)
            text = font.render(f"({int(x)}, {int(y)})", True, (255, 255, 0))
            surface.blit(text, (int(x) + 10, int(y) + 10))


class Interpreter:
    """Instruction interpreter."""
    
    def __init__(self, state):
        self.state = state
    
    def execute_instruction(self, instruction_text):
        """
        Execute a square-bracketed instruction.
        
        Args:
            instruction_text: Content inside square brackets (e.g., "circle 50 blue")
        """
        # Parse instruction
        parts = self.parse_instruction(instruction_text)
        
        if not parts:
            return
        
        command = parts[0].lower()
        args = parts[1:]
        
        if command == 'circle':
            self.execute_circle(args)
        elif command == 'square':
            self.execute_square(args)
        else:
            print(f"Unknown command: {command}")
    
    def parse_instruction(self, text):
        """Parse instruction text into command and arguments."""
        # Split by whitespace, but keep quoted strings together
        pattern = r'[^\s"]+|"[^"]*"'
        parts = re.findall(pattern, text)
        return parts
    
    def execute_circle(self, args):
        """Execute circle command: circle RADIUS COLOR"""
        if len(args) < 2:
            print(f"Error: circle requires 2 arguments (radius, color), got {len(args)}")
            return
        
        try:
            radius = float(args[0])
        except ValueError:
            print(f"Error: invalid radius '{args[0]}'")
            return
        
        color = args[1]
        
        # Create circle and add to state
        circle = Circle(radius, color)
        var_name = self.state.add_object(circle)
        print(f"Created circle: radius={radius}, color={color} -> {var_name}")
    
    def execute_square(self, args):
        """Execute square command: square SIZE COLOR"""
        if len(args) < 2:
            print(f"Error: square requires 2 arguments (size, color), got {len(args)}")
            return
        
        try:
            size = float(args[0])
        except ValueError:
            print(f"Error: invalid size '{args[0]}'")
            return
        
        color = args[1]
        
        # Create square and add to state
        square = Square(size, color)
        var_name = self.state.add_object(square)
        print(f"Created square: size={size}, color={color} -> {var_name}")


def load_instructions(instructions_path):
    """
    Load instructions from file.
    
    Args:
        instructions_path: Path to .instructions file
    
    Returns:
        List of (timestamp, is_instruction, content) tuples
    """
    instructions = []
    
    with open(instructions_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Parse: timestamp\tend_time\tcontent
            parts = line.split('\t', 2)
            if len(parts) < 3:
                continue
            
            timestamp = float(parts[0])
            content = parts[2]
            
            # Check if it's an instruction (square brackets) or a word
            if content.startswith('[') and content.endswith(']'):
                # Instruction
                instruction_text = content[1:-1]  # Remove brackets
                instructions.append((timestamp, True, instruction_text))
            else:
                # Word (possibly with comment)
                word = content.split('//')[0].strip()
                instructions.append((timestamp, False, word))
    
    return instructions


def extract_audio(video_path):
    """
    Extract audio from video file to temporary file.
    
    Args:
        video_path: Path to video file
    
    Returns:
        Path to temporary audio file (or None if extraction fails)
    """
    try:
        # Create temporary file for audio
        temp_audio = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        temp_audio_path = temp_audio.name
        temp_audio.close()
        
        print(f"Extracting audio to {temp_audio_path}...")
        
        # Use ffmpeg to extract audio
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'libmp3lame',
            '-q:a', '2',  # High quality
            '-y',  # Overwrite
            temp_audio_path
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        print(f"Audio extracted successfully")
        return temp_audio_path
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not extract audio: {e}")
        return None
    except FileNotFoundError:
        print("Warning: ffmpeg not found. Video will play without audio.")
        print("  Install ffmpeg to enable audio playback.")
        return None


def play_video_with_instructions(video_path, instructions_path):
    """
    Play video while interpreting instructions.
    
    Args:
        video_path: Path to video file
        instructions_path: Path to instructions file
    """
    # Initialize pygame
    pygame.init()
    pygame.mixer.init()
    
    # Extract audio from video
    audio_path = extract_audio(video_path)
    
    # Load video using OpenCV
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        print(f"Error: Could not open video file: {video_path}")
        sys.exit(1)
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"Video: {width}x{height} @ {fps} fps")
    
    # Create pygame window
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption(f"Playing: {video_path.name}")
    
    # Create clock for timing
    clock = pygame.time.Clock()
    
    # Load instructions
    instructions = load_instructions(instructions_path)
    print(f"Loaded {len(instructions)} instructions")
    
    # Initialize state and interpreter
    state = State(width, height)
    interpreter = Interpreter(state)
    
    if DEBUG:
        print(f"DEBUG: Screen size: {width}x{height}, center: ({state.center_x}, {state.center_y})")
    
    # Track which instructions have been executed
    instruction_index = 0
    
    # Load and play audio if available
    audio_loaded = False
    if audio_path:
        try:
            pygame.mixer.music.load(audio_path)
            audio_loaded = True
            print("Audio loaded successfully")
        except Exception as e:
            print(f"Warning: Could not load audio: {e}")
    
    # Main playback loop
    running = True
    paused = False
    start_time = pygame.time.get_ticks()
    current_time = 0
    
    # Start audio playback
    if audio_loaded:
        pygame.mixer.music.play()
    
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                    if paused:
                        # Pause audio
                        if audio_loaded:
                            pygame.mixer.music.pause()
                    else:
                        # Resume audio
                        if audio_loaded:
                            pygame.mixer.music.unpause()
                        # Reset start time when unpausing
                        start_time = pygame.time.get_ticks() - int(current_time * 1000)
        
        if not paused:
            # Calculate current playback time
            elapsed_ms = pygame.time.get_ticks() - start_time
            current_time = elapsed_ms / 1000.0
            
            # Read frame from video
            ret, frame = cap.read()
            
            if not ret:
                print("End of video")
                running = False
                break
            
            # Convert frame from BGR (OpenCV) to RGB (pygame)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Transpose for pygame (OpenCV uses height,width,channels; pygame uses width,height)
            frame = frame.transpose([1, 0, 2])
            frame = pygame.surfarray.make_surface(frame)
            
            # Display frame
            screen.blit(frame, (0, 0))
            
            # Draw white border around video frame to see where it is
            pygame.draw.rect(screen, (255, 255, 255), (0, 0, width, height), 5)
            
            # Execute instructions at current timestamp
            while instruction_index < len(instructions):
                timestamp, is_instruction, content = instructions[instruction_index]
                
                if timestamp <= current_time:
                    if is_instruction:
                        print(f"[{current_time:.3f}s] Executing: [{content}]")
                        interpreter.execute_instruction(content)
                    else:
                        state.add_word(content)
                    
                    instruction_index += 1
                else:
                    break
            
            # Draw all displayable objects on top of video
            for obj in state.get_displayable_objects():
                obj.draw(screen, state.center_x, state.center_y)
            
            # Update display
            pygame.display.flip()
            
            # Control playback speed
            clock.tick(fps)
        else:
            # Paused - just redraw current frame
            for obj in state.get_displayable_objects():
                obj.draw(screen, state.center_x, state.center_y)
            pygame.display.flip()
            clock.tick(30)
    
    # Cleanup
    cap.release()
    pygame.mixer.music.stop()
    pygame.quit()
    
    # Clean up temporary audio file
    if audio_path:
        try:
            import os
            os.remove(audio_path)
        except:
            pass
    
    print(f"\nFinal word buffer: {' '.join(state.words)}")


def main():
    parser = argparse.ArgumentParser(
        description='Play video with interpreted instructions'
    )
    parser.add_argument(
        'video_file',
        help='Path to video file (.mp4)'
    )
    parser.add_argument(
        'instructions_file',
        help='Path to instructions file'
    )
    
    args = parser.parse_args()
    
    video_path = Path(args.video_file)
    instructions_path = Path(args.instructions_file)
    
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)
    
    if not instructions_path.exists():
        print(f"Error: Instructions file not found: {instructions_path}")
        sys.exit(1)
    
    try:
        play_video_with_instructions(video_path, instructions_path)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
