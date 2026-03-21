import asyncio
import json
import os as _os
import queue
import random
import re as _re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
import psutil
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
from core.brain.self.user_model import UserModel
from core.brain.cognition.task_queue import TaskQueue
from core.brain.cognition.executive import Executive
from core.senses.voice import Mouth
from core.senses.hearing import Ear
from core.brain.sensorimotor.motor import MotorCortex
from core.brain.interface.worker import WorkerNode
from config import VOICE_BLEND, SANDBOX_PATH

# ---------------------------------------------------------------------------
# App & CORS
# ---------------------------------------------------------------------------

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Shared State
# ---------------------------------------------------------------------------

connected_clients: set[WebSocket] = set()
atlas_busy        = threading.Event()        # set = busy, clear = idle
last_intent       = "CHAT"
_pool             = ThreadPoolExecutor(max_workers=3)
_ACKS             = [
    "Right away, Sir.", "At once, Sir.", "Processing.",
    "Initiating now, Sir.", "Consider it done, Sir.", "Executing, Sir."
]

# ---------------------------------------------------------------------------
# Runtime Status Tracker
# ---------------------------------------------------------------------------

_runtime_status = {
    "active":  0,   # tasks currently executing (WorkerNode busy)
    "queued":  0,   # pending TaskQueue entries
    "done":    0,   # completed this session
    "agents":  1,   # always 1 for now (the single WorkerNode)
}

def _refresh_status():
    """Recompute status from live sources. Call before emitting."""
    pending = task_queue.get_pending()
    _runtime_status["queued"]  = len(pending)
    _runtime_status["active"]  = 1 if atlas_busy.is_set() else 0

def _emit_status():
    _refresh_status()
    emit("status_update", dict(_runtime_status))

def _emit_task_files(result: str, original_task: str):
    """Extract written filenames from worker result and broadcast."""
    found = _re.findall(
        r'(?:Wrote to|Created|saved|file[s]?:?)\s+([\w./\\-]+\.\w+)',
        result, _re.IGNORECASE
    )
    if found:
        emit("task_files", {"files": found, "task": original_task[:120]})

# ---------------------------------------------------------------------------
# System Initialisation
# ---------------------------------------------------------------------------

print("Initializing ATLAS Brain Architecture...")

bus        = EventBus()
ans        = AutonomicNervousSystem(bus)
task_queue = TaskQueue(bus)
ans.set_task_queue(task_queue)
ans.start()

habits     = HabitLoop(bus)
router     = Router(bus)
brain      = LLMEngine(bus=bus)
sleep_sys  = SleepSystem()
salience   = SalienceFilter(bus)
tom        = TheoryOfMind(bus)
vta        = RewardSystem()
user_model = UserModel()
executive  = Executive(bus)
motor      = MotorCortex()

def _on_worker_step(step_index: int, action: str, result: str):
    emit("worker_step_done", {
        "step_index": step_index,
        "action":     action,
        "result":     result,
    })

worker     = WorkerNode(on_step_done=_on_worker_step)
# worker.warmup() removed — model loads on-demand via VRAMManager on first COMMAND
_main_loop = None

# Voice I/O (CUDA → CPU fallback handled inside each class)
mouth = Mouth(device="cuda")
ear   = Ear(device="cuda")

# ---------------------------------------------------------------------------
# WebSocket Broadcasting Helpers
# ---------------------------------------------------------------------------

async def broadcast_event(event_type: str, data: dict):
    """Send a JSON event to every connected frontend client."""
    message = json.dumps({"type": event_type, "payload": data})
    for client in list(connected_clients):       # snapshot for thread safety
        try:
            await client.send_text(message)
        except Exception:
            connected_clients.discard(client)

@app.on_event("startup")
async def startup_event():
    global _main_loop
    _main_loop = asyncio.get_running_loop()

    asyncio.create_task(system_vitals_broadcaster())
    asyncio.create_task(_async_greeting())


async def _async_greeting():
    """Generate the startup greeting off the event loop so it doesn't block."""
    loop = asyncio.get_running_loop()
    greeting = await loop.run_in_executor(None, brain.generate_greeting)
    print(f"[ATLAS CORE]: {greeting}")
    await asyncio.sleep(1.0)
    await broadcast_event("atlas_speak", {"text": greeting, "mode": "greeting"})


def emit(event_type: str, data: dict):
    """Thread-safe fire-and-forget wrapper around broadcast_event."""
    global _main_loop
    if _main_loop and _main_loop.is_running():
        # Safely schedule the async broadcast from any background thread
        asyncio.run_coroutine_threadsafe(broadcast_event(event_type, data), _main_loop)
    else:
        # Fallback if the loop isn't ready
        try:
            asyncio.run(broadcast_event(event_type, data))
        except RuntimeError:
            pass


# ---------------------------------------------------------------------------
# Core Cognition Pipeline  (shared by WebSocket text input AND VAD ear input)
# ---------------------------------------------------------------------------

def run_cognition(user_input: str):
    """
    Full cognitive pipeline matching main.py.
    Broadcasts results to all connected frontend clients and speaks via mouth.
    Safe to call from any thread.
    """
    global last_intent

    if atlas_busy.is_set():
        emit("atlas_speak", {"text": "One moment, Sir. I'm still processing your previous request.", "mode": "busy"})
        return

    atlas_busy.set()
    try:
        # --- 1. Reflex / Habit Check ------------------------------------------
        habit_response = habits.check_trigger(user_input)
        stop_event = threading.Event()
        ear.set_interrupt_target(stop_event)

        if habit_response:
            emit("atlas_speak", {"text": habit_response, "mode": "habit"})
            mouth.speak(habit_response, blend_config=VOICE_BLEND, stop_event=stop_event)
            ear.set_interrupt_target(None)
            return

        # --- 2. Parallel Routing / Salience / ToM -----------------------------
        intent_f  = _pool.submit(router.route, user_input)
        sal_f     = _pool.submit(salience.score_importance, user_input)
        tom_f     = _pool.submit(tom.analyze_state, user_input)

        intent     = intent_f.result()
        score      = sal_f.result()
        user_state = tom_f.result()

        emit("cognitive_metadata", {
            "intent":   intent,
            "salience": score,
            "mood":     user_state.get("mood"),
            "urgency":  user_state.get("urgency"),
        })

        # --- 3. Reward & User Model Updates ------------------------------------
        _pool.submit(user_model.update_from_interaction, user_input, user_state["mood"], intent)

        if user_state.get("mood") == "positive":
            vta.apply_feedback(last_intent, positive=True)
        elif user_state.get("mood") == "frustrated":
            vta.apply_feedback(last_intent, positive=False)
        last_intent = intent

        sleep_sys.tick(brain.session_history)

        # --- 4. Command / WorkerNode Branch ------------------------------------
        llm_input = user_input

        if intent == "COMMAND":
            ack = random.choice(_ACKS)
            emit("atlas_speak", {"text": ack, "mode": "ack"})
            mouth.speak(ack, blend_config=VOICE_BLEND, stop_event=stop_event)

            synthesized = brain.synthesize_task(user_input)
            emit("orchestrator", {"task": synthesized[:200]})

            _runtime_status["active"] = 1
            _emit_status()

            if synthesized.startswith("[MULTI_STEP]"):
                raw_steps = synthesized.replace("[MULTI_STEP]", "").strip()
                steps = [s.strip() for s in raw_steps.split("|") if s.strip()]
                if len(steps) < 2:
                    steps = executive.plan_execution(user_input)
                emit("executive_plan", {"steps": steps})
                sys_result = worker.execute_plan(steps)
            else:
                sys_result = worker.execute_task(synthesized)

            _runtime_status["active"] = 0
            _runtime_status["done"] += 1
            _emit_status()
            _emit_task_files(sys_result, user_input)

            llm_input = (
                f"Task requested: '{user_input}'.\n"
                f"Execution Result: {sys_result}\n\n"
                "[INSTRUCTION]: If [ERROR], inform the user of the exact error. "
                "If [SUCCESS], summarize concisely."
            )

        # --- 5. Streaming LLM Response ----------------------------------------
        # Speech runs in a parallel thread fed by a queue so UI tokens are
        # never blocked waiting for mouth.speak() to finish.
        speech_queue = queue.Queue()

        def speech_worker():
            """Drains the speech queue, speaking each sentence in order."""
            while True:
                sentence = speech_queue.get()
                if sentence is None:          # poison pill — we're done
                    break
                if not stop_event.is_set():
                    mouth.speak(sentence, blend_config=VOICE_BLEND, stop_event=stop_event)
                speech_queue.task_done()

        speech_thread = threading.Thread(target=speech_worker, daemon=True)
        speech_thread.start()

        response_gen     = brain.think(llm_input, intent=intent, user_state=user_state, task_queue=task_queue)
        current_sentence = ""
        full_response    = ""
        interrupted      = False

        for chunk in response_gen:
            if stop_event.is_set():
                interrupted = True
                emit("atlas_interrupted", {})
                break

            if "message" in chunk:
                content = chunk["message"]["content"].replace("*", "").replace("#", "")
                full_response    += content
                current_sentence += content

                # Emit token to UI immediately — never blocked by speech
                emit("atlas_token", {"text": content})

                # Queue each completed sentence for the speech thread
                if mouth and any(p in content for p in [".", "!", "?", "\n"]):
                    sentence = current_sentence.strip()
                    if len(sentence) > 1:
                        speech_queue.put(sentence)
                    current_sentence = ""

        # Flush any partial sentence left at end of stream
        if mouth and current_sentence.strip() and not interrupted:
            speech_queue.put(current_sentence.strip())

        # Signal the speech thread to stop after it finishes its queue
        speech_queue.put(None)
        speech_thread.join()

        # Broadcast the complete assembled response
        if full_response.strip():
            emit("atlas_speak", {"text": full_response.strip(), "mode": "response"})

        ear.set_interrupt_target(None)
    finally:
        atlas_busy.clear()


# ---------------------------------------------------------------------------
# Proactive Thinking — Default Mode Network
# ---------------------------------------------------------------------------

def handle_proactive(text: str):
    """Fires when ATLAS thinks of something unprompted."""
    if atlas_busy.is_set():
        return                          # cognition in progress — skip proactive thought

    atlas_busy.set()
    try:
        brain.session_history.append(f"ATLAS: {text}")
        emit("atlas_speak", {"text": text, "mode": "proactive"})

        stop_event = threading.Event()
        ear.set_interrupt_target(stop_event)
        t = threading.Thread(
            target=mouth.speak, args=(text, VOICE_BLEND, stop_event), daemon=True
        )
        t.start()
        while t.is_alive():
            if stop_event.is_set():
                break
            time.sleep(0.05)
    except Exception as e:
        print(f"[CRITICAL ERROR] Proactive Thread Crashed: {e}")
    finally:
        ear.set_interrupt_target(None)
        atlas_busy.clear()


def handle_task_due(task: dict):
    text = f"Sir, a scheduled task is due: {task['task'][:80]}"
    handle_proactive(text)
    task_queue.complete(task["id"])


# --- Bus Subscriptions -------------------------------------------------------
bus.subscribe("task_due",            handle_task_due)
bus.subscribe("intent_COMMAND",      lambda x: emit("switch_app", {"app": "console"}))
bus.subscribe("high_salience_event", lambda x: emit("high_salience", {"event": x}))
bus.subscribe("user_state_updated",  lambda x: emit("user_state",    {"state": x}))

# --- Default Mode Network ----------------------------------------------------
dmn = DefaultModeNetwork(bus, interoception=brain.interoception, brain=brain)
dmn.start_wandering(callback=handle_proactive)

# ---------------------------------------------------------------------------
# VAD Loop — runs in its own thread, feeds the shared cognition pipeline
# ---------------------------------------------------------------------------

_vad_thread_running = True

def vad_listener_loop():
    """Continuously listens for voice input and routes it through cognition."""
    ear.start_listening()
    print("[VAD] Voice Activity Detection active.")
    while _vad_thread_running:
        user_input = ear.wait_for_input()
        if not user_input:
            continue
        clean = user_input.lower().strip().replace(".", "")
        if any(w in clean for w in ["exit", "quit", "sleep", "shutdown", "atlas exit"]):
            continue  # Shutdown via VAD is ignored in server mode; use the API instead
        print(f"[VAD Input]: {user_input}")
        emit("user_speak", {"text": user_input, "source": "voice"})
        threading.Thread(target=run_cognition, args=(user_input,), daemon=True).start()
    ear.stop_listening()


threading.Thread(target=vad_listener_loop, daemon=True).start()

# ---------------------------------------------------------------------------
# System Vitals Streamer
# ---------------------------------------------------------------------------

_gpu_temp_cache = {"value": 0.0, "ts": 0}

def _read_gpu_temp():
    """Read NVIDIA GPU temperature via nvidia-smi (cached for 10s)."""
    now = time.time()
    if now - _gpu_temp_cache["ts"] < 10:
        return _gpu_temp_cache["value"]
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=3,
        )
        temp = float(result.stdout.strip())
        _gpu_temp_cache.update(value=temp, ts=now)
        return temp
    except Exception:
        return _gpu_temp_cache["value"]


async def system_vitals_broadcaster():
    while True:
        if connected_clients:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            gpu_temp = _read_gpu_temp()
            await broadcast_event("system_vitals", {"cpu": cpu, "mem": mem, "gpu_temp": gpu_temp})
        await asyncio.sleep(5)

# ---------------------------------------------------------------------------
# FastAPI Lifecycle & WebSocket Endpoint
# ---------------------------------------------------------------------------


@app.on_event("shutdown")
async def shutdown_event():
    global _vad_thread_running
    _vad_thread_running = False
    ans.stop()
    if hasattr(dmn, "running"):
        dmn.running = False

    goodbye = brain.generate_goodbye()
    print(f"[ATLAS CORE]: {goodbye}")

    print("[SYS] Archiving session...")
    stats = sleep_sys.sleep(
        brain.get_conversation_history(), brain.get_session_start(), consolidate=True
    )
    if stats.get("consolidation") and stats["consolidation"].get("consolidated", 0) > 0:
        print(f"[CONSOLIDATOR] Merged {stats['consolidation']['consolidated']} facts.")

    try:
        mouth.close()
    except Exception:
        pass
    print("[SYS] Server offline.")


from core.brain.cognition.memory import MemorySystem

@app.get("/memory/list")
async def memory_list():
    mem = MemorySystem()
    if mem.collection.count() == 0:
        return {"memories": [], "total": 0}
    results = mem.collection.get(include=["documents", "metadatas"])
    memories = []
    for doc_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
        memories.append({
            "id":         doc_id,
            "text":       doc,
            "importance": meta.get("importance", 5.0),
            "tags":       meta.get("tags", "").split(",") if meta.get("tags") else [],
            "timestamp":  meta.get("timestamp", ""),
        })
    memories.sort(key=lambda x: x["importance"], reverse=True)
    return {"memories": memories, "total": len(memories)}


@app.get("/memory/search")
async def memory_search(q: str = ""):
    mem = MemorySystem()
    if not q.strip() or mem.collection.count() == 0:
        return {"memories": [], "total": 0}
    results = mem.recall(q, n_results=20, similarity_threshold=0.6)
    all_data = mem.collection.get(include=["documents", "metadatas"])
    text_to_meta = {doc: meta for doc, meta in zip(all_data["documents"], all_data["metadatas"])}
    text_to_id   = {doc: doc_id for doc, doc_id in zip(all_data["documents"], all_data["ids"])}
    memories = []
    for text in results:
        meta = text_to_meta.get(text, {})
        memories.append({
            "id":         text_to_id.get(text, ""),
            "text":       text,
            "importance": meta.get("importance", 5.0),
            "tags":       meta.get("tags", "").split(",") if meta.get("tags") else [],
            "timestamp":  meta.get("timestamp", ""),
        })
    return {"memories": memories, "total": len(memories)}


@app.get("/status")
async def get_status():
    _refresh_status()
    return dict(_runtime_status)


@app.get("/sandbox/files")
async def sandbox_files():
    """Return a flat list of relative file paths inside the sandbox."""
    if not _os.path.exists(SANDBOX_PATH):
        return {"files": []}
    result = []
    for root, dirs, files in _os.walk(SANDBOX_PATH):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for f in sorted(files):
            if not f.endswith(('.pyc', '.exe', '.db')):
                rel = _os.path.relpath(_os.path.join(root, f), SANDBOX_PATH)
                result.append(rel.replace('\\', '/'))
    return {"files": sorted(result), "sandbox_path": SANDBOX_PATH}


@app.get("/sandbox/file")
async def sandbox_file(path: str = Query(...)):
    """Return raw content of a file inside the sandbox."""
    safe = _os.path.abspath(_os.path.join(SANDBOX_PATH, path))
    if not safe.startswith(_os.path.abspath(SANDBOX_PATH)):
        return PlainTextResponse("// SANDBOX ESCAPE BLOCKED", status_code=403)
    if not _os.path.isfile(safe):
        return PlainTextResponse("// FILE NOT FOUND", status_code=404)
    try:
        with open(safe, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()
        return PlainTextResponse(content)
    except Exception as e:
        return PlainTextResponse(f"// READ ERROR: {e}", status_code=500)


@app.delete("/memory/{memory_id}")
async def memory_delete(memory_id: str):
    mem = MemorySystem()
    try:
        mem.collection.delete(ids=[memory_id])
        return {"success": True, "deleted": memory_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    print("[GUI] Connection Established.")

    try:
        while True:
            raw  = await websocket.receive_text()
            payload = json.loads(raw)

            if payload.get("action") == "user_input":
                user_text = payload["text"].strip()
                if not user_text:
                    continue

                print(f"[UI Input]: {user_text}")
                await broadcast_event("user_speak", {"text": user_text, "source": "text"})

                # Run cognition off the WebSocket thread so incoming messages never block
                threading.Thread(target=run_cognition, args=(user_text,), daemon=True).start()

    except WebSocketDisconnect:
        connected_clients.discard(websocket)
        print("[GUI] UI Client Disconnected.")

# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def run_server():
    print("=" * 50)
    print(" ATLAS API Bridge Online: ws://localhost:8000/ws")
    print(" VAD listener running in parallel.")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n[SYS] Shutting down...")