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
import threading
import queue
try:
    import websocket  # websocket-client library
except ImportError:
    websocket = None

# Debug mode - set to True to show position counter in corner
DEBUG = False

# WebSocket server URL
GRAPHICS_SERVER_URL = "ws://localhost:8000/ws"


class State:
    """Application state manager for WebSocket graphics."""
    
    def __init__(self, ws_client=None):
        self.ws_client = ws_client
        self.objects = []  # List of graphics objects as dicts
        self.variables = {}  # Map variable names to object indices
        self.next_var_id = 0
    
    def add_object(self, obj_dict, var_name=None):
        """Add a displayable object to state and send to server."""
        if var_name is None:
            var_name = f"_var{self.next_var_id}"
            self.next_var_id += 1
        
        obj_index = len(self.objects)
        self.objects.append(obj_dict)
        self.variables[var_name] = obj_index
        
        # Send to graphics server
        if self.ws_client:
            self.ws_client.send_command({
                "command": "add_object",
                "object": obj_dict
            })
        
        return var_name
    
    def update_object(self, var_name, updates):
        """Update an existing object by variable name."""
        if var_name not in self.variables:
            print(f"Error: variable '{var_name}' not found")
            return False
        
        obj_index = self.variables[var_name]
        if obj_index >= len(self.objects):
            print(f"Error: object index {obj_index} out of range")
            return False
        
        # Update local state
        self.objects[obj_index].update(updates)
        print(f"DEBUG: Updated local object at index {obj_index}: {self.objects[obj_index]}")
        
        # Send update to graphics server
        if self.ws_client:
            cmd = {
                "command": "update_object",
                "index": obj_index,
                "updates": updates
            }
            print(f"DEBUG: Sending to server: {cmd}")
            print(f"DEBUG: ws_client.connected = {self.ws_client.connected}")
            self.ws_client.send_command(cmd)
        else:
            print("DEBUG: ws_client is None!")
        
        return True
    
    def clear(self):
        """Clear all graphics."""
        self.objects = []
        if self.ws_client:
            self.ws_client.send_command({
                "command": "clear"
            })


class Interpreter:
    """Instruction interpreter - sends commands via WebSocket."""
    
    def __init__(self, state):
        self.state = state
    
    def execute_instruction(self, instruction_text):
        """Execute a square-bracketed instruction."""
        parts = self.parse_instruction(instruction_text)
        
        if not parts:
            return
        
        # Check for variable assignment: varname = command args
        var_name = None
        if len(parts) >= 3 and parts[1] == '=':
            var_name = parts[0]
            parts = parts[2:]  # Remove "varname =" from parts
        
        command = parts[0].lower()
        args = parts[1:]
        
        if command == 'circle':
            self.execute_circle(args, var_name)
        elif command == 'square':
            self.execute_square(args, var_name)
        elif command == 'scale':
            self.execute_scale(args)
        else:
            print(f"Unknown command: {command}")
    
    def parse_instruction(self, text):
        """Parse instruction text into command and arguments."""
        pattern = r'[^\s"]+|"[^"]*"'
        parts = re.findall(pattern, text)
        return parts
    
    def execute_circle(self, args, var_name=None):
        """Execute circle command: circle RADIUS COLOR"""
        if len(args) < 2:
            print(f"Error: circle requires 2 arguments (radius, color), got {len(args)}")
            return
        
        try:
            radius = float(args[0])
        except ValueError:
            print(f"Error: invalid radius '{args[0]}'")
            return
        
        color = args[1].strip('"\'')
        
        # Create circle as JSON object
        circle_obj = {
            "type": "circle",
            "radius": radius,
            "color": color
        }
        
        result_var = self.state.add_object(circle_obj, var_name)
        print(f"Created circle: radius={radius}, color={color} -> {result_var}")
    
    def execute_square(self, args, var_name=None):
        """Execute square command: square SIZE COLOR"""
        if len(args) < 2:
            print(f"Error: square requires 2 arguments (size, color), got {len(args)}")
            return
        
        try:
            size = float(args[0])
        except ValueError:
            print(f"Error: invalid size '{args[0]}'")
            return
        
        color = args[1].strip('"\'')
        
        # Create square as JSON object
        square_obj = {
            "type": "square",
            "size": size,
            "color": color
        }
        
        result_var = self.state.add_object(square_obj, var_name)
        print(f"Created square: size={size}, color={color} -> {result_var}")
    
    def execute_scale(self, args):
        """Execute scale command: scale VARNAME FACTOR"""
        if len(args) < 2:
            print(f"Error: scale requires 2 arguments (varname, factor), got {len(args)}")
            return
        
        var_name = args[0]
        try:
            factor = float(args[1])
        except ValueError:
            print(f"Error: invalid scale factor '{args[1]}'")
            return
        
        # Get the object
        if var_name not in self.state.variables:
            print(f"Error: variable '{var_name}' not found")
            return
        
        obj_index = self.state.variables[var_name]
        obj = self.state.objects[obj_index]
        
        # Scale based on object type
        updates = {}
        if obj["type"] == "circle":
            new_radius = obj["radius"] * factor
            updates["radius"] = new_radius
            print(f"Scaling {var_name}: radius {obj['radius']} -> {new_radius}")
        elif obj["type"] == "square":
            new_size = obj["size"] * factor
            updates["size"] = new_size
            print(f"Scaling {var_name}: size {obj['size']} -> {new_size}")
        else:
            print(f"Error: cannot scale object type '{obj['type']}'")
            return
        
        self.state.update_object(var_name, updates)


def parse_script(script_path):
    """
    Parse script file to extract plain text and events.
    
    Returns:
        (plain_text, events, script_words)
        - plain_text: Script with events removed
        - events: List of (word_index, event_content) where word_index is position in script_words
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
        
        # Calculate word index by counting words before this position
        text_before_event = plain_text[:position_in_plain]
        words_before = re.findall(r'\b\w+\b', text_before_event.lower())
        word_index = len(words_before)
        
        events.append((word_index, event_content))
        
        # Update offset for the next iteration
        offset += len(match.group(0))
    
    # Remove events from text
    plain_text = re.sub(event_pattern, '', content)
    
    # Extract words from plain text
    script_words = re.findall(r'\b\w+\b', plain_text.lower())
    
    return plain_text, events, script_words


class WebSocketClient:
    """Simple WebSocket client for sending graphics commands."""
    
    def __init__(self, url):
        self.url = url
        self.ws = None
        self.connected = False
        self.message_queue = queue.Queue()
        self.thread = None
        
        if websocket is None:
            print("Warning: websocket-client not installed. Graphics will not be sent to server.")
            print("Install with: pip install websocket-client")
            return
        
        # Start connection in separate thread
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def _run(self):
        """Run WebSocket connection in thread."""
        if websocket is None:
            return
            
        try:
            self.ws = websocket.WebSocketApp(
                self.url,
                on_open=self._on_open,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Run in thread
            self.ws.run_forever()
        except Exception as e:
            print(f"WebSocket error: {e}")
    
    def _on_open(self, ws):
        """Called when WebSocket connection opens."""
        self.connected = True
        print("Connected to graphics server")
        
        # Start message sender thread
        threading.Thread(target=self._send_messages, daemon=True).start()
    
    def _on_error(self, ws, error):
        """Called on WebSocket error."""
        print(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Called when WebSocket connection closes."""
        self.connected = False
        print("Disconnected from graphics server")
    
    def _send_messages(self):
        """Send queued messages to server."""
        while self.connected:
            try:
                message = self.message_queue.get(timeout=0.1)
                if self.ws and self.connected:
                    self.ws.send(json.dumps(message))
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error sending message: {e}")
    
    def send_command(self, command_dict):
        """Queue a command to send to server."""
        if websocket is None or not self.connected:
            return
        self.message_queue.put(command_dict)
    
    def close(self):
        """Close WebSocket connection."""
        if self.ws:
            self.ws.close()


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
        
        # Tracking
        self.recognized_words = []  # All recognized words so far
        self.current_position = 0  # Current position in script_words
        self.executed_events = set()  # Indices of executed events
        
        # Initialize WebSocket client
        self.ws_client = WebSocketClient(GRAPHICS_SERVER_URL)
        
        # Initialize state and interpreter
        self.state = State(ws_client=self.ws_client)
        self.interpreter = Interpreter(self.state)
        
        # Initialize Vosk
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
        self.recognizer.SetWords(True)
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        # Initialize Pygame (small window for status display)
        pygame.init()
        self.screen = pygame.display.set_mode((800, 200))
        pygame.display.set_caption("Real-time Script Interpreter - Status")
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
        """Check if we've passed any events and execute them.
        
        Args:
            position: Current word index in the script
        """
        # Check each event
        for idx, (event_word_index, event_content) in enumerate(self.events):
            if idx not in self.executed_events and position >= event_word_index:
                print(f"\n>>> Executing event at word {event_word_index}: [{event_content}]")
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
        """Draw status window (graphics are rendered in browser)."""
        # Black background
        self.screen.fill((0, 0, 0))
        
        # Show position indicator
        y = 20
        position_text = f"Position: {self.current_position}/{len(self.script_words)}"
        text_surface = self.font.render(position_text, True, (200, 200, 200))
        self.screen.blit(text_surface, (10, y))
        
        # Show recent recognized words
        y += 40
        recent = ' '.join(self.recognized_words[-5:])
        heard_text = f"Heard: {recent}"
        text_surface = self.small_font.render(heard_text, True, (100, 200, 100))
        self.screen.blit(text_surface, (10, y))
        
        # Show events status
        y += 30
        events_text = f"Events: {len(self.executed_events)}/{len(self.events)}"
        text_surface = self.small_font.render(events_text, True, (200, 200, 100))
        self.screen.blit(text_surface, (10, y))
        
        # Show connection status
        y += 30
        conn_status = "Connected" if self.ws_client.connected else "Disconnected"
        conn_color = (100, 255, 100) if self.ws_client.connected else (255, 100, 100)
        conn_text = f"Graphics Server: {conn_status}"
        text_surface = self.small_font.render(conn_text, True, conn_color)
        self.screen.blit(text_surface, (10, y))
        
        pygame.display.flip()
    
    def run(self):
        """Main loop: listen, recognize, execute, display."""
        print("\n" + "="*60)
        print("REAL-TIME INTERPRETER - BROWSER SOURCE MODE")
        print("="*60)
        print(f"Script: {self.script_path}")
        print(f"Words: {len(self.script_words)}")
        print(f"Events: {len(self.events)}")
        print("\n*** GRAPHICS SERVER MUST BE RUNNING ***")
        print("1. Start: python graphics_server.py")
        print("2. In OBS: Add 'Browser' source")
        print("3. URL: http://localhost:8000")
        print("4. Width: 1920, Height: 1080")
        print("\nThis window shows status only.")
        print("Graphics appear in the browser/OBS.")
        print("\nControls:")
        print("  R - Reset position and clear graphics")
        print("  Q or ESC - Quit")
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
                            self.state.clear()  # Clear graphics via WebSocket
                
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
            self.ws_client.close()
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
