#!/usr/bin/env python3
"""
Graphics Server
Serves HTML page and broadcasts graphics state via WebSocket.
"""

import asyncio
import json
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

# Add CORS middleware for browser compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store connected WebSocket clients
clients = set()

# Current graphics state
graphics_state = {
    "objects": []  # List of graphics objects to display
}


@app.get("/")
async def get_html():
    """Serve the graphics display page."""
    html_path = Path(__file__).parent / "graphics.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text())
    else:
        return HTMLResponse(content="""
        <html>
        <body>
            <h1>Graphics page not found</h1>
            <p>Make sure graphics.html exists in the same directory.</p>
        </body>
        </html>
        """)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for graphics updates."""
    await websocket.accept()
    clients.add(websocket)
    
    # Send current state to new client
    await websocket.send_json(graphics_state)
    
    try:
        while True:
            # Receive commands from clients (like realtime_interpret.py)
            data = await websocket.receive_json()
            
            # Process command
            if data.get("command") == "add_object":
                obj = data.get("object")
                graphics_state["objects"].append(obj)
                # Broadcast to all clients
                await broadcast(graphics_state)
            
            elif data.get("command") == "update_object":
                index = data.get("index")
                updates = data.get("updates", {})
                print(f"UPDATE_OBJECT: index={index}, updates={updates}")
                if index is not None and 0 <= index < len(graphics_state["objects"]):
                    print(f"  Before: {graphics_state['objects'][index]}")
                    graphics_state["objects"][index].update(updates)
                    print(f"  After: {graphics_state['objects'][index]}")
                    print(f"  Broadcasting to {len(clients)} clients")
                    await broadcast(graphics_state)
            
            elif data.get("command") == "clear":
                graphics_state["objects"] = []
                await broadcast(graphics_state)
            
            elif data.get("command") == "set_state":
                graphics_state["objects"] = data.get("objects", [])
                await broadcast(graphics_state)
    
    except WebSocketDisconnect:
        clients.remove(websocket)


async def broadcast(message):
    """Broadcast message to all connected clients."""
    disconnected = set()
    for client in clients:
        try:
            await client.send_json(message)
        except:
            disconnected.add(client)
    
    # Remove disconnected clients
    for client in disconnected:
        clients.discard(client)


if __name__ == "__main__":
    print("="*60)
    print("GRAPHICS SERVER")
    print("="*60)
    print("Starting server at http://localhost:8000")
    print("\nFor OBS:")
    print("  1. Add 'Browser' source")
    print("  2. URL: http://localhost:8000")
    print("  3. Width: 1920, Height: 1080")
    print("  4. Check 'Shutdown source when not visible' (optional)")
    print("\nServer will receive commands from realtime_interpret.py")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
