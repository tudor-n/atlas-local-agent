import asyncio
import json
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import your existing ATLAS components
from core.brain.interface.bus import EventBus
from core.brain.interface.llm import LLMEngine
from core.brain.sensorimotor.habits import HabitLoop

app = FastAPI()

# Allow the frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global connections list
connected_clients = []

# Initialize ATLAS Core
bus = EventBus()
brain = LLMEngine(bus=bus)
habits = HabitLoop(bus=bus)

async def broadcast_event(event_type: str, data: dict):
    """Sends events from ATLAS backend to the React Frontend."""
    message = json.dumps({"type": event_type, "payload": data})
    for client in connected_clients:
        try:
            await client.send_text(message)
        except:
            pass

# --- HOOK INTO YOUR EXISTING EVENT BUS ---
def on_brain_thought(thought_text):
    # Fire and forget async broadcast from a sync thread
    asyncio.run(broadcast_event("atlas_speak", {"text": thought_text}))

def on_app_switch(app_name):
    asyncio.run(broadcast_event("switch_app", {"app": app_name}))

# Subscribe to ATLAS internal events so the UI updates automatically
bus.subscribe("intent_COMMAND", lambda x: on_app_switch("console"))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    print("[GUI] New UI Client Connected!")
    
    try:
        while True:
            # Receive commands from the Frontend (UI text bar or buttons)
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            if payload["action"] == "user_input":
                user_text = payload["text"]
                print(f"[UI Input]: {user_text}")
                
                # Echo user text to UI console
                await broadcast_event("user_speak", {"text": user_text})
                
                # Process through ATLAS (Run in thread to not block WebSocket)
                def process():
                    # Check habits
                    habit_resp = habits.check_trigger(user_text)
                    if habit_resp:
                        on_brain_thought(habit_resp)
                        return
                    
                    # Generate LLM response
                    generator = brain.think(user_text)
                    full_response = ""
                    for chunk in generator:
                        if 'message' in chunk:
                            content = chunk['message']['content'].replace('*', '').replace('#', '')
                            full_response += content
                            # Here you could stream chunk-by-chunk for a typing effect!
                    on_brain_thought(full_response.strip())

                threading.Thread(target=process).start()

    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print("[GUI] UI Client Disconnected.")

def run_server():
    print("Starting ATLAS API Bridge on ws://localhost:8000/ws")
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    run_server()