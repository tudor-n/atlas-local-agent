import asyncio
import json
import threading
import psutil
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# --- ATLAS CORE IMPORTS ---
from core.brain.interface.bus import EventBus
from core.brain.interface.llm import LLMEngine
from core.brain.sensorimotor.habits import HabitLoop
from core.brain.interface.router import Router
from core.brain.autonomic.autonomic import AutonomicNervousSystem
from core.brain.autonomic.sleep import SleepSystem
from core.brain.limbic.salience import SalienceFilter
from core.brain.self.theory_of_mind import TheoryOfMind
from core.brain.limbic.reward import RewardSystem
from core.brain.self.default_mode import DefaultModeNetwork
from core.senses.voice import Mouth
from core.brain.sensorimotor.motor import MotorCortex
from core.brain.interface.worker import WorkerNode

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_clients = []
atlas_busy = threading.Lock()
last_intent = "CHAT"
VOICE_BLEND = {'bm_george': 0.7, 'bm_fable': 0.3}

print("Initializing ATLAS Brain Architecture...")

# --- INITIALIZE COGNITIVE & SENSORIMOTOR SYSTEMS ---
bus = EventBus()
ans = AutonomicNervousSystem(bus)
ans.start()

habits = HabitLoop(bus)
router = Router(bus)
brain = LLMEngine(bus=bus)
sleep_system = SleepSystem()
salience = SalienceFilter(bus)
tom = TheoryOfMind(bus)
vta = RewardSystem()

# Initialize Hands and Voice
motor = MotorCortex()
worker = WorkerNode()
worker.warmup()
mouth = Mouth(device="cuda") # Will fallback to CPU if cuda isn't available

async def broadcast_event(event_type: str, data: dict):
    """Sends events from ATLAS backend to the React Frontend."""
    message = json.dumps({"type": event_type, "payload": data})
    for client in connected_clients:
        try:
            await client.send_text(message)
        except:
            pass

def on_brain_thought(thought_text):
    """Fires UI updates when ATLAS has formulated a final response."""
    asyncio.run(broadcast_event("atlas_speak", {"text": thought_text}))

def on_app_switch(app_name):
    asyncio.run(broadcast_event("switch_app", {"app": app_name}))

# Internal Event Subscriptions
bus.subscribe("intent_COMMAND", lambda x: on_app_switch("console"))
bus.subscribe("high_salience_event", lambda x: print(f"[AMYGDALA] High Urgency: {x}"))

# --- PROACTIVE THINKING (DEFAULT MODE NETWORK) ---
def handle_proactive(text):
    if atlas_busy.acquire(blocking=False):
        try:
            if hasattr(brain, 'history'):
                brain.history.append({"role": "assistant", "content": text})
            elif hasattr(brain, 'messages'):
                brain.messages.append({"role": "assistant", "content": text})
            
            # Update UI and Speak
            on_brain_thought(text)
            stop_event = threading.Event()
            mouth.speak(text, blend_config=VOICE_BLEND, stop_event=stop_event)
        except Exception as e:
             print(f"\n[CRITICAL ERROR] Proactive Thread Crashed: {e}")
        finally:
            atlas_busy.release()

dmn = DefaultModeNetwork(bus, interoception=brain.interoception, brain=brain)
dmn.start_wandering(callback=handle_proactive)

# --- SYSTEM VITALS STREAMER ---
async def system_vitals_broadcaster():
    """Background task pushing live hardware metrics to the UI."""
    while True:
        if connected_clients:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            try:
                temps = psutil.sensors_temperatures()
                gpu_temp = temps.get('coretemp', [[None, 45.0]])[0][1] 
            except:
                gpu_temp = 45.0
                
            await broadcast_event("system_vitals", {
                "cpu": cpu,
                "mem": mem,
                "gpu_temp": gpu_temp
            })
        await asyncio.sleep(2)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(system_vitals_broadcaster())
    
    # Optional: Send initial greeting to console
    greeting = brain.generate_greeting()
    print(f"[ATLAS CORE]: {greeting}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    print("[GUI] Connection Established.")
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            if payload["action"] == "user_input":
                user_text = payload["text"]
                print(f"[UI Input]: {user_text}")
                await broadcast_event("user_speak", {"text": user_text})
                
                def process_cognition():
                    global last_intent
                    try:
                        with atlas_busy:
                            # 1. Reflex / Habit Check
                            habit_resp = habits.check_trigger(user_text)
                            stop_event = threading.Event() # Create an event for the voice engine
                            
                            if habit_resp:
                                on_brain_thought(habit_resp)
                                mouth.speak(habit_resp, blend_config=VOICE_BLEND, stop_event=stop_event)
                                return
                            
                            # 2. Routing, Salience & Emotion Tracking
                            intent = router.route(user_text)
                            score = salience.score_importance(user_text)
                            user_state = tom.analyze_state(user_text)
                            
                            if user_state.get('mood') == 'positive': 
                                vta.apply_feedback(last_intent, positive=True)
                            elif user_state.get('mood') == 'frustrated': 
                                vta.apply_feedback(last_intent, positive=False)
                            last_intent = intent

                            llm_input = user_text
                            
                            # 3. Handle System Commands via WorkerNode
                            if intent == "COMMAND":
                                ack = "Processing your request, Sir."
                                on_brain_thought(ack)
                                mouth.speak(ack, blend_config=VOICE_BLEND, stop_event=stop_event)
                                
                                synthesized_task = brain.synthesize_task(user_text)
                                sys_result = worker.execute_task(synthesized_task)
                                
                                llm_input = (
                                    f"Task requested: '{user_text}'.\n"
                                    f"System Execution Result: {sys_result}\n\n"
                                    "[CRITICAL INSTRUCTION]: If the Execution Result contains an [ERROR], you MUST inform the user about the exact error and do NOT pretend the task succeeded. If it is [SUCCESS], summarize what was done concisely."
                                )
                            
                            # 4. Generate Core Response
                            generator = brain.think(llm_input, intent=intent)
                            full_response = ""
                            for chunk in generator:
                                if 'message' in chunk:
                                    content = chunk['message']['content'].replace('*', '').replace('#', '')
                                    full_response += content

                            clean_response = full_response.strip()
                            
                            # Send text to UI instantly so the user can read it
                            on_brain_thought(clean_response)
                            
                            # Trigger vocal playback
                            mouth.speak(clean_response, blend_config=VOICE_BLEND, stop_event=stop_event)
                            
                    except Exception as e:
                        print(f"\n[CRITICAL ERROR] Cognition Thread Crashed: {e}")

                # Process off the main WebSocket thread so it doesn't block incoming messages
                threading.Thread(target=process_cognition, daemon=True).start()

    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print("[GUI] UI Client Disconnected.")

def run_server():
    print("==================================================")
    print(" ATLAS API Bridge Online: ws://localhost:8000/ws")
    print("==================================================")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n[SYS] Shutting down...")
        ans.stop()
        if dmn.running: dmn.running = False
        try: mouth.close()
        except: pass