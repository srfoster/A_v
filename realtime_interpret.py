#!/usr/bin/env python3
"""
Real-time Instruction Interpreter
Uses speech recognition to listen to script reading and display graphics in real-time.
"""

import sys
import argparse
import re
import json
from pathlib import Path
from difflib import SequenceMatcher
import pygame
import vosk
import pyaudio

# Debug mode
DEBUG = True


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
        self.x = x
        self.y = y
    
    def parse_color(self, color_str):
        """Parse color string to RGB tuple."""
        color_str = color_str.strip('"\'')
        
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
        
        if color_str.startswith('#'):
            hex_str = color_str[1:]
            if len(hex_str) == 6:
                r = int(hex_str[0:2], 16)
                g = int(hex_str[2:4], 16)
                b = int(hex_str[4:6], 16)
                return (r, g, b)
        
        return (255, 255, 255)
    
    def draw(self, surface, default_x=None, default_y=None):
        """Draw the circle on the given surface."""
        x = self.x if self.x is not None else default_x
        y = self.y if self.y is not None else default_y
        pygame.draw.circle(surface, self.color, (int(x), int(y)), int(self.radius))


class Square:
    """Square display object."""
    
    def __init__(self, size, color, x=None, y=None):
        self.size = size
        self.color = self.parse_color(color)
        self.x = x
        self.y = y
    
    def parse_color(self, color_str):
        """Parse color string to RGB tuple."""
        color_str = color_str.strip('"\'')
        
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
        
        if color_str.startswith('#'):
            hex_str = color_str[1:]
            if len(hex_str) == 6:
                r = int(hex_str[0:2], 16)
                g = int(hex_str[2:4], 16)
                b = int(hex_str[4:6], 16)
                return (r, g, b)
        
        return (255, 255, 255)
    
    def draw(self, surface, default_x=None, default_y=None):
        """Draw the square on the given surface."""
        x = self.x if self.x is not None else default_x
        y = self.y if self.y is not None else default_y
        half_size = self.size / 2
        rect = pygame.Rect(int(x - half_size), int(y - half_size), int(self.size), int(self.size))
        pygame.draw.rect(surface, self.color, rect)


class Interpreter:
    """Instruction interpreter."""
    
    def __init__(self, state):
        self.state = state
    
    def execute_instruction(self, instruction_text):
        """Execute a square-bracketed instruction."""
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
        square = Square(size, color)
        var_name = self.state.add_object(square)
        print(f"Created square: size={size}, color={color} -> {var_name}")


def parse_script(script_path):
    """
    Parse script file to extract plain text and events.
    
    Returns:
        (plain_text, events, script_words)
        - plain_text: Script with events removed
        - events: List of (position_in_plain_text, event_content)
        - script_words: List of words from script
    """
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all events
    events = []
    event_pattern = r'\[([^\]]+)\]'
    
    # Track positions in the text without events
    plain_text = content
    offset = 0
    
    for match in re.finditer(event_pattern, content):
        event_content = match.group(1)
        event_start_in_original = match.start()
        event_end_in_original = match.end()
        
        # Position in plain text (accounting for previous removals)
        position_in_plain = event_start_in_original - offset
        
        events.append((position_in_plain, event_content))
        
        # Update offset for the next iteration
        offset += len(match.group(0))
    
    # Remove events from text
    plain_text = re.sub(event_pattern, '', content)
    
    # Extract words from plain text
    script_words = re.findall(r'\b\w+\b', plain_text.lower())
    
    return plain_text, events, script_words


class RealtimeInterpreter:
    """Real-time speech recognition and instruction execution."""
    
    def __init__(self, script_path, model_path="model"):
        self.script_path = script_path
        self.model_path = model_path
        
        # Parse script
        self.plain_text, self.events, self.script_words = parse_script(script_path)
        print(f"Loaded script: {len(self.script_words)} words, {len(self.events)} events")
        if DEBUG:
            print(f"Script words: {' '.join(self.script_words[:20])}...")
            print(f"Events: {self.events}")
        
        # Initialize state and interpreter
        self.state = State(screen_width=800, screen_height=600)
        self.interpreter = Interpreter(self.state)
        
        # Tracking
        self.recognized_words = []  # All recognized words so far
        self.current_position = 0  # Current position in script_words
        self.executed_events = set()  # Indices of executed events
        
        # Initialize Vosk
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
        self.recognizer.SetWords(True)
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Real-time Script Interpreter")
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        self.clock = pygame.time.Clock()
        
    def find_position_in_script(self):
        """
        Find current position in script based on recognized words.
        Uses sequence matching to handle errors and variations.
        """
        if not self.recognized_words:
            return 0
        
        # Try to match last N recognized words against script
        window_size = min(10, len(self.recognized_words))
        recent_words = self.recognized_words[-window_size:]
        
        # Find best match in script
        best_ratio = 0
        best_position = self.current_position
        
        # Search around current position
        search_start = max(0, self.current_position - 5)
        search_end = min(len(self.script_words), self.current_position + window_size + 5)
        
        for i in range(search_start, search_end):
            script_segment = self.script_words[i:i+window_size]
            if not script_segment:
                continue
            
            matcher = SequenceMatcher(None, recent_words, script_segment)
            ratio = matcher.ratio()
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_position = i + len(script_segment)
        
        if DEBUG and best_position != self.current_position:
            print(f"Position update: {self.current_position} -> {best_position} (confidence: {best_ratio:.2f})")
        
        return best_position
    
    def check_and_execute_events(self, position):
        """Check if we've passed any events and execute them."""
        # Calculate character position in plain text from word position
        char_position = 0
        for i in range(min(position, len(self.script_words))):
            char_position += len(self.script_words[i]) + 1  # +1 for space
        
        # Check each event
        for idx, (event_pos, event_content) in enumerate(self.events):
            if idx not in self.executed_events and char_position >= event_pos:
                print(f"\n>>> Executing event: [{event_content}]")
                self.interpreter.execute_instruction(event_content)
                self.executed_events.add(idx)
    
    def process_audio(self):
        """Process audio from microphone."""
        data = self.stream.read(4000, exception_on_overflow=False)
        
        if self.recognizer.AcceptWaveform(data):
            result = json.loads(self.recognizer.Result())
            text = result.get('text', '')
            
            if text:
                # Extract words
                words = re.findall(r'\b\w+\b', text.lower())
                self.recognized_words.extend(words)
                
                print(f"Recognized: {text}")
                if DEBUG:
                    print(f"Total words recognized: {len(self.recognized_words)}")
                
                # Update position
                new_position = self.find_position_in_script()
                if new_position > self.current_position:
                    self.current_position = new_position
                    self.check_and_execute_events(self.current_position)
        else:
            # Partial result (optional: can be used for live feedback)
            partial = json.loads(self.recognizer.PartialResult())
            partial_text = partial.get('partial', '')
            # Could display this for visual feedback
    
    def draw_ui(self):
        """Draw the UI showing script, recognized text, and graphics."""
        self.screen.fill((0, 0, 0))  # Black background
        
        # Draw script text with position highlighting
        y = 20
        script_display = ' '.join(self.script_words)
        words_so_far = ' '.join(self.script_words[:self.current_position])
        
        # Draw completed words in gray
        if words_so_far:
            text_surface = self.small_font.render(words_so_far.upper(), True, (128, 128, 128))
            self.screen.blit(text_surface, (20, y))
            y += 25
        
        # Draw remaining words in white
        remaining_words = ' '.join(self.script_words[self.current_position:self.current_position + 20])
        if remaining_words:
            text_surface = self.small_font.render(remaining_words.upper(), True, (255, 255, 255))
            self.screen.blit(text_surface, (20, y))
        
        # Draw position indicator
        y = 80
        position_text = f"Position: {self.current_position}/{len(self.script_words)} words"
        text_surface = self.small_font.render(position_text, True, (200, 200, 200))
        self.screen.blit(text_surface, (20, y))
        
        # Draw recognized words (last 10)
        y = 110
        recent = ' '.join(self.recognized_words[-10:])
        recognized_text = f"Heard: {recent}"
        text_surface = self.small_font.render(recognized_text, True, (100, 200, 100))
        self.screen.blit(text_surface, (20, y))
        
        # Draw events status
        y = 140
        events_text = f"Events: {len(self.executed_events)}/{len(self.events)} executed"
        text_surface = self.small_font.render(events_text, True, (200, 200, 100))
        self.screen.blit(text_surface, (20, y))
        
        # Draw separator line
        pygame.draw.line(self.screen, (100, 100, 100), (0, 180), (800, 180), 2)
        
        # Draw graphics area (objects in state)
        # Offset graphics display down
        graphics_offset_y = 180
        for obj in self.state.get_displayable_objects():
            # Create a subsurface for graphics area
            graphics_surface = self.screen.subsurface((0, graphics_offset_y, 800, 420))
            # Draw with adjusted center
            obj.draw(graphics_surface, 400, 210)  # Center of graphics area
        
        pygame.display.flip()
    
    def run(self):
        """Main loop: listen, recognize, execute, display."""
        print("\n" + "="*60)
        print("REAL-TIME INTERPRETER")
        print("="*60)
        print(f"Script: {self.script_path}")
        print(f"Words: {len(self.script_words)}")
        print(f"Events: {len(self.events)}")
        print("\nPress 'R' to reset position")
        print("Press 'Q' or ESC to quit")
        print("="*60)
        print("\nListening...")
        
        # Start audio stream
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4000
        )
        self.stream.start_stream()
        
        running = True
        try:
            while running:
                # Handle pygame events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key == pygame.K_r:
                            # Reset
                            print("\n>>> RESET <<<")
                            self.recognized_words = []
                            self.current_position = 0
                            self.executed_events = set()
                            self.state.objects = []
                
                # Process audio
                self.process_audio()
                
                # Draw UI
                self.draw_ui()
                
                # Control frame rate
                self.clock.tick(30)
        
        finally:
            # Cleanup
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()
            pygame.quit()
            print("\nStopped listening.")


def main():
    parser = argparse.ArgumentParser(description='Real-time script interpreter with speech recognition')
    parser.add_argument('script', help='Path to script file (.script)')
    parser.add_argument('--model', default='model', help='Path to Vosk model directory (default: ./model)')
    
    args = parser.parse_args()
    
    # Check if script exists
    if not Path(args.script).exists():
        print(f"Error: Script file not found: {args.script}")
        sys.exit(1)
    
    # Check if model exists
    if not Path(args.model).exists():
        print(f"Error: Vosk model not found: {args.model}")
        print("\nTo download a Vosk model:")
        print("1. Visit https://alphacephei.com/vosk/models")
        print("2. Download a small English model (e.g., vosk-model-small-en-us)")
        print("3. Extract to ./model/ directory")
        sys.exit(1)
    
    # Run interpreter
    interpreter = RealtimeInterpreter(args.script, args.model)
    interpreter.run()


if __name__ == '__main__':
    main()
