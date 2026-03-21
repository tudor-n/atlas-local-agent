# ATLAS — Phase 3 Implementation Plan
## "Live Status, IDE App, Command Intelligence"

> **Feed this file to Claude Code from the repo root.**
> Assumes Phase 2 plan has been implemented (CognitiveBadge, TaskMonitorApp, MemoryApp exist).
> Work through sections in the numbered order at the bottom.

---

## Context & Current State

```
Notification bar (dot row) → hardcoded: ACTIVE:2 QUEUED:5 DONE:12 AGENTS:4
TaskMonitorApp / MemoryApp  → no back button, no hand-tracking attributes
ConsoleFullView             → has back button but no task popup or thought panel
AppCarousel                 → 'code' slot was renamed 'tasks' in Phase 2; 'models' renamed 'memory'
                               Still has no real Code/IDE app
```

**New backend events to ADD (Section 1):**

| Event type | Payload | Purpose |
|---|---|---|
| `status_update` | `{ active, queued, done, agents }` | Drive notification bar |
| `task_files` | `{ files: string[], task: string }` | Tell frontend which files were written |
| `worker_step_done` | `{ step_index: number, result: string }` | Precise step completion |

**New REST endpoints to ADD (Section 1):**

| Route | Purpose |
|---|---|
| `GET /status` | Snapshot of task counts + active agents |
| `GET /sandbox/files` | Directory listing of the sandbox |
| `GET /sandbox/file?path=` | Raw file content for the IDE |

---

## Section 1 — Backend additions

### 1.1 — Runtime status tracker

**File:** `atlas-backend/api_server.py`

Add a module-level status dict that the cognition pipeline mutates, then expose it:

```python
# --- Add near the top, after shared state declarations ---

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
    # 'done' is incremented manually — see 1.2

def _emit_status():
    _refresh_status()
    emit("status_update", dict(_runtime_status))
```

### 1.2 — Increment done counter + emit on task completion

In `run_cognition()`, find the block that calls `worker.execute_task(synthesized)` or `worker.execute_plan(steps)` and wrap it:

```python
# BEFORE the execute call:
_runtime_status["active"] = 1
_emit_status()

# AFTER the execute call (regardless of success/failure):
_runtime_status["active"] = 0
_runtime_status["done"] += 1
_emit_status()
```

Also emit `task_files` when the result contains `[SUCCESS]` and mentions filenames. Add a helper after the execute calls:

```python
import re as _re

def _emit_task_files(result: str, original_task: str):
    """Extract written filenames from worker result and broadcast."""
    # Worker result format: "[SUCCESS] Wrote to filename.py ..."
    found = _re.findall(
        r'(?:Wrote to|Created|saved|file[s]?:?)\s+([\w./\\-]+\.\w+)',
        result, _re.IGNORECASE
    )
    if found:
        emit("task_files", {"files": found, "task": original_task[:120]})

# Call after execute:
_emit_task_files(sys_result, user_input)
```

### 1.3 — Emit `worker_step_done` from WorkerNode

**File:** `atlas-backend/core/brain/interface/worker.py`

The `execute_task` loop already tracks `execution_log`. Add a callback hook so the server can emit per-step events without coupling WorkerNode to the event bus:

```python
class WorkerNode:
    def __init__(self, model_name=WORKER_MODEL, on_step_done=None):
        # ... existing init ...
        self.on_step_done = on_step_done   # callable(step_index, action, result) | None
```

In `execute_task`, after the success branch appends to `execution_log`:

```python
# After: execution_log.append(action)
if self.on_step_done:
    self.on_step_done(len(execution_log) - 1, action, result[:200])
```

**File:** `atlas-backend/api_server.py`

Update the WorkerNode instantiation:

```python
def _on_worker_step(step_index: int, action: str, result: str):
    emit("worker_step_done", {
        "step_index": step_index,
        "action":     action,
        "result":     result,
    })

worker = WorkerNode(on_step_done=_on_worker_step)
```

### 1.4 — REST: `/status`

```python
@app.get("/status")
async def get_status():
    _refresh_status()
    return dict(_runtime_status)
```

### 1.5 — REST: `/sandbox/files` and `/sandbox/file`

```python
import os as _os
from fastapi import Query
from fastapi.responses import PlainTextResponse
from config import SANDBOX_PATH

@app.get("/sandbox/files")
async def sandbox_files():
    """Return a flat list of relative file paths inside the sandbox."""
    if not _os.path.exists(SANDBOX_PATH):
        return {"files": []}
    result = []
    for root, dirs, files in _os.walk(SANDBOX_PATH):
        # Skip hidden dirs and __pycache__
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
```

---

## Section 2 — Wire notification bar to live state

### 2.1 — Add `statusCounts` state to `App.jsx`

**File:** `atlas-frontend/src/App.jsx`

Replace the hardcoded dot-row data with live state. Add this state variable:

```jsx
const [statusCounts, setStatusCounts] = useState({
  active: 0, queued: 0, done: 0, agents: 1,
});
```

In `handleWsMessage`, add:

```jsx
} else if (data.type === 'status_update') {
  setStatusCounts({
    active: data.payload.active ?? 0,
    queued: data.payload.queued ?? 0,
    done:   data.payload.done   ?? 0,
    agents: data.payload.agents ?? 1,
  });

} else if (data.type === 'task_files') {
  setLastTaskFiles(data.payload);   // new state — see 2.2
}
```

Also add:

```jsx
const [lastTaskFiles, setLastTaskFiles] = useState(null);
// { files: string[], task: string }
```

On mount, fetch the initial snapshot so the bar isn't zero before first interaction:

```jsx
useEffect(() => {
  fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/status`)
    .then(r => r.json())
    .then(d => setStatusCounts(d))
    .catch(() => {});
}, []);
```

### 2.2 — Replace hardcoded dot rows in both layouts

Find the two dot-row `<div>` blocks (one in the fullscreen hub, one in the windowed hub) and replace the hardcoded `2`, `5`, `12`, `4` literals with `{statusCounts.X}`:

**Fullscreen dot row** — the one with `gap-5 px-8 py-3`:

```jsx
// ACTIVE dot — animate-pulse only when active > 0
<div className="w-2 h-2 rounded-full bg-[#fbbf24] shadow-[0_0_5px_#fbbf24]"
  style={{ animation: statusCounts.active > 0 ? 'pulse 1s infinite' : 'none' }} />
<span className="text-[10px] text-[#fbbf24] tracking-[0.2em] font-mono">
  ACTIVE: <span className="text-white font-bold drop-shadow-[0_0_2px_#fff]">
    {statusCounts.active}
  </span>
</span>

// QUEUED
<span ...>QUEUED: <span ...>{statusCounts.queued}</span></span>

// DONE
<span ...>DONE: <span ...>{statusCounts.done}</span></span>

// AGENTS — show a cyan live dot when atlas_busy, grey when idle
<div className={`w-2 h-2 rounded-full ${statusCounts.active > 0
  ? 'bg-stark-cyan shadow-[0_0_5px_#00f3ff] animate-pulse'
  : 'bg-stark-cyan/30'}`} />
<span ...>AGENTS: <span ...>{statusCounts.agents}</span></span>
```

Apply the same substitution to the compact windowed dot row (the `gap-2` one).

### 2.3 — Pass `lastTaskFiles` down

Pass `lastTaskFiles` to `TaskMonitorApp` and `ConsoleFullView` as a prop — they will use it in Sections 4 and 5 to show the "View in Code" button.

```jsx
// Also pass a callback to open the code app:
const handleOpenCode = useCallback((files) => {
  setLastTaskFiles(files);   // ensure it's set
  setOpenedApp('code');
}, []);
```

Pass `onOpenCode={handleOpenCode}` to `ConsoleFullView` and `TaskMonitorApp`.

Add `'code'` to `OPENABLE_APPS`:

```jsx
const OPENABLE_APPS = ['console', 'tasks', 'memory', 'code'];
```

---

## Section 3 — Back button + hand-tracking attributes in TaskMonitorApp and MemoryApp

Both `TaskMonitorApp.jsx` and `MemoryApp.jsx` currently have no back button and no `data-hand-*` attributes, unlike `ConsoleFullView`. Apply the same pattern to both.

### 3.1 — TaskMonitorApp.jsx

**Add `onBack` prop:**

```jsx
export default memo(function TaskMonitorApp({ activePlan, orchestratorTask,
  highSalienceLog, cognitiveData, onBack, onOpenCode, lastTaskFiles }) {
```

**Add header bar** at the very top of the returned JSX (before the existing content), identical in structure to ConsoleFullView's header:

```jsx
{/* Header — matches ConsoleFullView style */}
<div className="shrink-0 flex items-center gap-4 px-6 py-4 border-b border-stark-cyan/15 bg-black/60 backdrop-blur-xl no-drag">
  <button
    data-hand-target
    data-hand-label="BACK"
    onClick={onBack}
    className="flex items-center justify-center w-8 h-8 rounded-full border border-stark-cyan/30 text-stark-cyan/60 hover:text-stark-cyan hover:border-stark-cyan hover:bg-stark-cyan/10 transition-all duration-200"
  >
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="m15 18-6-6 6-6"/>
    </svg>
  </button>

  <div className="flex items-center gap-3">
    <div className="relative w-7 h-7 flex items-center justify-center">
      <div className="absolute w-7 h-7 rounded-full border border-stark-cyan/40 animate-spin" style={{ animationDuration: '8s' }} />
      <div className={`w-2.5 h-2.5 rounded-full shadow-[0_0_8px_#ff5500] ${activePlan ? 'bg-stark-orange animate-pulse' : 'bg-stark-cyan/30'}`} />
    </div>
    <div>
      <div className="text-[11px] tracking-[0.35em] text-stark-cyan font-bold leading-none mb-0.5">TASK MONITOR</div>
      <div className="text-[9px] tracking-[0.25em] text-stark-cyan/40 leading-none">
        {activePlan ? `EXECUTING — ${activePlan.steps.length} STEPS` : 'IDLE'}
      </div>
    </div>
  </div>

  {/* "View in Code" button — only when files were written */}
  {lastTaskFiles?.files?.length > 0 && (
    <button
      data-hand-target
      data-hand-label="VIEW CODE"
      onClick={() => onOpenCode(lastTaskFiles)}
      className="ml-auto flex items-center gap-2 px-3 py-1.5 rounded-lg border border-stark-cyan/30 bg-stark-cyan/10 text-stark-cyan text-[10px] font-mono tracking-widest hover:bg-stark-cyan/20 hover:border-stark-cyan/60 transition-all duration-200"
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
      </svg>
      VIEW IN CODE
    </button>
  )}
</div>

{/* Scanline */}
<div className="shrink-0 h-px w-full" style={{
  background: 'linear-gradient(90deg, transparent 0%, rgba(0,243,255,0.4) 30%, rgba(0,243,255,0.8) 50%, rgba(0,243,255,0.4) 70%, transparent 100%)',
}} />
```

**Add `data-hand-component`** to the outer container div, and **`data-hand-target`** to the DELETE-style action buttons in the salience log.

**Update step items** to add `data-hand-target` on any clickable step rows.

### 3.2 — MemoryApp.jsx

**Add `onBack` prop:**

```jsx
export default memo(function MemoryApp({ onBack }) {
```

**Add identical header bar** as above but titled `LONG-TERM MEMORY`:

```jsx
<div className="shrink-0 flex items-center gap-4 px-6 py-4 border-b border-stark-cyan/15 bg-black/60 backdrop-blur-xl no-drag">
  <button
    data-hand-target
    data-hand-label="BACK"
    onClick={onBack}
    className="flex items-center justify-center w-8 h-8 rounded-full border border-stark-cyan/30 text-stark-cyan/60 hover:text-stark-cyan hover:border-stark-cyan hover:bg-stark-cyan/10 transition-all duration-200"
  >
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="m15 18-6-6 6-6"/>
    </svg>
  </button>

  <div className="flex items-center gap-3">
    <div className="relative w-7 h-7 flex items-center justify-center">
      <div className="absolute w-7 h-7 rounded-full border border-stark-cyan/40 animate-spin" style={{ animationDuration: '12s' }} />
      <div className="w-2.5 h-2.5 rounded-full bg-stark-cyan/70" />
    </div>
    <div>
      <div className="text-[11px] tracking-[0.35em] text-stark-cyan font-bold leading-none mb-0.5">LONG-TERM MEMORY</div>
      <div className="text-[9px] tracking-[0.25em] text-stark-cyan/40 leading-none">CHROMADB // PERSISTENT</div>
    </div>
  </div>

  <div className="ml-auto text-[9px] tracking-[0.2em] text-stark-cyan/30 font-mono border border-stark-cyan/10 px-2 py-1 rounded">
    {memories.length} ENTRIES
  </div>
</div>
```

**Add `data-hand-component`** to outer container, `data-hand-target` to each DELETE button and the search input wrapper.

### 3.3 — Update App.jsx hub routing to pass `onBack`

In the `AnimatePresence` block, every opened app now needs `onBack`:

```jsx
} : openedApp === 'tasks' ? (
  <motion.div key="tasks-full" ...>
    <TaskMonitorApp
      activePlan={activePlan}
      orchestratorTask={orchestratorTask}
      highSalienceLog={highSalienceLog}
      cognitiveData={cognitiveData}
      lastTaskFiles={lastTaskFiles}
      onBack={handleConsoleBack}       // reuse same setter: () => setOpenedApp(null)
      onOpenCode={handleOpenCode}
    />
  </motion.div>
) : openedApp === 'memory' ? (
  <motion.div key="memory-full" ...>
    <MemoryApp onBack={handleConsoleBack} />
  </motion.div>
) : openedApp === 'code' ? (
  <motion.div key="code-full" ...>
    <CodeApp
      initialFiles={lastTaskFiles?.files ?? []}
      taskDescription={lastTaskFiles?.task ?? ''}
      onBack={handleConsoleBack}
    />
  </motion.div>
) : (
  // existing hub
```

---

## Section 4 — Command intelligence panel in ConsoleFullView

When ATLAS receives a COMMAND-intent message, show a collapsible panel in the console that reveals the synthesized task, cognitive metadata, and execution plan. This gives Tudor visibility into what ATLAS is actually doing before it speaks.

### 4.1 — Add props to ConsoleFullView

```jsx
export default memo(function ConsoleFullView({
  history, ws, onBack, isOpacityFixed,
  streamingText, cognitiveData, isInterrupted,
  activePlan, orchestratorTask,              // NEW
  lastTaskFiles, onOpenCode,                 // NEW
}) {
```

### 4.2 — Add `CommandIntelPanel` inside ConsoleFullView

This is an **inline sub-component** defined at the bottom of `ConsoleFullView.jsx` (not a separate file — it's tightly coupled):

```jsx
function CommandIntelPanel({ cognitiveData, orchestratorTask, activePlan }) {
  const [collapsed, setCollapsed] = useState(false);

  // Only show when there's something to display
  if (!orchestratorTask && !activePlan) return null;

  const intentColor = {
    COMMAND: '#fbbf24',
    QUERY:   '#00f3ff',
    MEMORY:  '#a78bfa',
    IMAGINE: '#34d399',
    CHAT:    'rgba(255,255,255,0.4)',
  }[cognitiveData?.intent] ?? 'rgba(255,255,255,0.4)';

  return (
    <div className="shrink-0 mx-6 mb-3 rounded-xl border border-stark-cyan/15 bg-black/50 overflow-hidden">
      {/* Collapsed header — always visible */}
      <button
        onClick={() => setCollapsed(c => !c)}
        className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-stark-cyan/5 transition-colors text-left"
      >
        <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: intentColor }} />
        <span className="text-[9px] font-mono tracking-[0.3em]" style={{ color: intentColor }}>
          {cognitiveData?.intent ?? 'PROCESSING'}
        </span>
        <span className="text-[9px] text-white/30 font-mono flex-1 truncate">
          {orchestratorTask || 'Analysing...'}
        </span>
        {/* Salience badge */}
        {cognitiveData?.salience != null && (
          <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded border ${
            cognitiveData.salience >= 8
              ? 'border-stark-orange/40 text-stark-orange bg-stark-orange/10'
              : 'border-stark-cyan/20 text-stark-cyan/50'
          }`}>
            SAL {cognitiveData.salience}/10
          </span>
        )}
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.3)"
          strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          style={{ transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
          <path d="m6 9 6 6 6-6"/>
        </svg>
      </button>

      {/* Expanded body */}
      {!collapsed && (
        <div className="border-t border-stark-cyan/10 px-4 py-3 space-y-3">

          {/* Full task description */}
          {orchestratorTask && (
            <div>
              <div className="text-[8px] tracking-[0.3em] text-stark-cyan/40 mb-1 font-mono">SYNTHESIZED TASK</div>
              <div className="text-[11px] text-white/70 font-mono leading-relaxed">
                {orchestratorTask}
              </div>
            </div>
          )}

          {/* Cognitive metadata row */}
          {cognitiveData && (
            <div className="flex gap-4 flex-wrap">
              <div>
                <div className="text-[8px] tracking-widest text-stark-cyan/30 font-mono">MOOD</div>
                <div className={`text-[10px] font-mono font-bold ${
                  cognitiveData.mood === 'positive'   ? 'text-emerald-400' :
                  cognitiveData.mood === 'frustrated' ? 'text-orange-400' :
                  cognitiveData.mood === 'panicked'   ? 'text-red-400' :
                  'text-white/40'
                }`}>{(cognitiveData.mood ?? 'neutral').toUpperCase()}</div>
              </div>
              <div>
                <div className="text-[8px] tracking-widest text-stark-cyan/30 font-mono">URGENCY</div>
                <div className={`text-[10px] font-mono font-bold ${
                  cognitiveData.urgency === 'high' ? 'text-stark-orange' : 'text-white/40'
                }`}>{(cognitiveData.urgency ?? 'low').toUpperCase()}</div>
              </div>
              <div>
                <div className="text-[8px] tracking-widest text-stark-cyan/30 font-mono">ROUTER</div>
                <div className="text-[10px] font-mono font-bold" style={{ color: intentColor }}>
                  {cognitiveData.intent ?? '—'}
                </div>
              </div>
            </div>
          )}

          {/* Plan steps */}
          {activePlan?.steps?.length > 0 && (
            <div>
              <div className="text-[8px] tracking-[0.3em] text-stark-cyan/40 mb-2 font-mono">
                EXECUTION PLAN — {activePlan.steps.length} STEPS
              </div>
              <div className="space-y-1">
                {activePlan.steps.map((step, i) => {
                  const done   = activePlan.completed?.[i];
                  const active = !done && i === activePlan.activeStep;
                  return (
                    <div key={i} className={`flex items-start gap-2.5 pl-2 border-l-2 text-[10px] font-mono py-0.5 ${
                      done   ? 'border-emerald-400/60 text-emerald-400/70' :
                      active ? 'border-stark-cyan text-stark-cyan' :
                               'border-white/10 text-white/25'
                    }`}>
                      <span className="shrink-0">
                        {done ? '✓' : active ? '►' : '○'}
                      </span>
                      <span className={active ? 'animate-pulse' : ''}>{step}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

### 4.3 — Place the panel in the ConsoleFullView layout

Insert `<CommandIntelPanel>` in the JSX **between the scanline divider and the messages area**:

```jsx
{/* Scanline decoration */}
<div className="shrink-0 h-px w-full" style={{ background: 'linear-gradient(...)' }} />

{/* Command Intel Panel — NEW */}
<CommandIntelPanel
  cognitiveData={cognitiveData}
  orchestratorTask={orchestratorTask}
  activePlan={activePlan}
/>

{/* Messages area */}
<div ref={scrollRef} ...>
```

### 4.4 — "View in Code" button in ConsoleFullView

At the bottom of the console, **between the divider and the input area**, add:

```jsx
{/* View in Code banner — appears when files were written */}
{lastTaskFiles?.files?.length > 0 && (
  <div className="shrink-0 mx-4 mb-2 flex items-center gap-3 px-4 py-2.5 rounded-lg border border-stark-cyan/25 bg-stark-cyan/5">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00f3ff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
    </svg>
    <div className="flex-1 min-w-0">
      <div className="text-[9px] text-stark-cyan/50 font-mono tracking-widest">FILES WRITTEN</div>
      <div className="text-[10px] text-stark-cyan font-mono truncate">
        {lastTaskFiles.files.join('  ·  ')}
      </div>
    </div>
    <button
      data-hand-target
      data-hand-label="VIEW CODE"
      onClick={() => onOpenCode(lastTaskFiles)}
      className="shrink-0 px-3 py-1.5 rounded-lg border border-stark-cyan/40 bg-stark-cyan/10 text-stark-cyan text-[9px] font-mono tracking-widest hover:bg-stark-cyan/25 hover:border-stark-cyan transition-all duration-200"
    >
      VIEW IN CODE →
    </button>
  </div>
)}
```

### 4.5 — Show the panel automatically on COMMAND

The panel is driven by `orchestratorTask` and `activePlan` props — it appears automatically as soon as those are set by the WebSocket events wired in Phase 2. No additional logic needed. The panel will auto-expand when a new command arrives because `orchestratorTask` changes.

However, auto-**collapse** it when `activePlan` becomes null again (task done). Add this inside `ConsoleFullView`:

```jsx
// Inside ConsoleFullView, above the return:
const prevPlanRef = useRef(activePlan);
useEffect(() => {
  if (prevPlanRef.current && !activePlan) {
    // Task finished — keep panel visible (collapsed) so user can still review
    // The "View in Code" banner will appear instead
  }
  prevPlanRef.current = activePlan;
}, [activePlan]);
```

---

## Section 5 — Code IDE App

### 5.1 — Update AppCarousel to include `code` app

**File:** `atlas-frontend/src/components/AppCarousel.jsx`

The Phase 2 plan renamed `code` → `tasks`. We need to **add `code` back as a 7th slot** — but 7 slots is too crowded at 60°-apart. Instead, replace `settings` (currently a stub) with `code`, and move settings to a gear icon in the header:

```jsx
const apps = [
  { id: 'code',    name: 'CODE' },      // replaces 'settings'
  { id: 'weather', name: 'WEATHER' },
  { id: 'console', name: 'CONSOLE' },
  { id: 'tasks',   name: 'TASKS' },
  { id: 'memory',  name: 'MEMORY' },
  { id: 'cursor',  name: 'CURSOR', amber: true },
];
```

The `code` orb shows a pulsing orange badge when `lastTaskFiles` is non-null (files ready to view):

```jsx
{app.id === 'code' && lastTaskFiles?.files?.length > 0 && (
  <div className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-stark-orange shadow-[0_0_6px_#ff5500] animate-pulse" />
)}
```

Pass `lastTaskFiles` as a prop to AppCarousel, thread it from App.jsx.

### 5.2 — Create `CodeApp.jsx`

**File:** `atlas-frontend/src/components/CodeApp.jsx`

A two-panel IDE layout: file tree on the left, code viewer on the right with syntax-highlighted display.

**Dependencies:** No new npm packages — use a `<pre>` tag with manual token coloring via regex. This keeps the bundle small and avoids version conflicts.

**Props:** `{ initialFiles, taskDescription, onBack }`

```jsx
import { useState, useEffect, useRef, memo, useCallback } from 'react';
import { motion } from 'framer-motion';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ── Very lightweight syntax highlighter ──────────────────────────────────────
// Returns an array of { text, color } tokens for a line.
// Supports Python, JS/JSX, C++, plain text. Extend as needed.
function tokenizeLine(line, lang) {
  // Order matters — first match wins
  const rules = [
    { re: /(#.*)$/,                                           color: '#6b7280' },  // comment
    { re: /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`[^`]*`)/,  color: '#86efac' },  // string
    { re: /\b(def|class|import|from|return|if|else|elif|for|while|with|as|in|not|and|or|True|False|None|lambda|yield|async|await|try|except|finally|raise|pass|break|continue|global|nonlocal|del|assert)\b/, color: '#c084fc' },  // py keywords
    { re: /\b(const|let|var|function|return|if|else|for|while|class|import|export|default|from|async|await|new|this|typeof|instanceof|throw|try|catch|finally|in|of|=>\b)/, color: '#c084fc' },  // js keywords
    { re: /\b(\d+\.?\d*)\b/,                                 color: '#fb923c' },  // number
    { re: /\b([A-Z][a-zA-Z0-9_]*)\b/,                        color: '#67e8f9' },  // PascalCase = type/class
    { re: /\b([a-zA-Z_]\w*)\s*(?=\()/,                       color: '#fde68a' },  // function call
  ];

  // Simple single-pass: find first rule that matches anywhere, split, recurse
  function tokenize(str) {
    for (const { re, color } of rules) {
      const m = re.exec(str);
      if (!m) continue;
      const before = str.slice(0, m.index);
      const match  = m[0];
      const after  = str.slice(m.index + match.length);
      return [
        ...(before ? [{ text: before, color: 'rgba(255,255,255,0.75)' }] : []),
        { text: match, color },
        ...tokenize(after),
      ];
    }
    return str ? [{ text: str, color: 'rgba(255,255,255,0.75)' }] : [];
  }

  return tokenize(line);
}

function extToLang(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  return { py: 'python', js: 'javascript', jsx: 'javascript',
           ts: 'typescript', tsx: 'typescript', cpp: 'cpp',
           c: 'c', h: 'cpp', json: 'json', md: 'markdown' }[ext] ?? 'text';
}

// ── File tree item ────────────────────────────────────────────────────────────
function FileTreeItem({ path, isSelected, isNew, onClick }) {
  const parts  = path.split('/');
  const name   = parts[parts.length - 1];
  const indent = (parts.length - 1) * 12;
  const ext    = name.split('.').pop().toLowerCase();

  const iconColor = {
    py: '#c084fc', js: '#fde68a', jsx: '#67e8f9', ts: '#60a5fa',
    tsx: '#67e8f9', cpp: '#f97316', c: '#f97316', h: '#fb923c',
    json: '#34d399', md: '#94a3b8', txt: '#94a3b8',
  }[ext] ?? '#6b7280';

  return (
    <button
      data-hand-target
      data-hand-label={name}
      onClick={onClick}
      style={{ paddingLeft: 12 + indent }}
      className={`w-full text-left flex items-center gap-2 py-1.5 pr-3 text-[11px] font-mono transition-colors group ${
        isSelected
          ? 'bg-stark-cyan/15 text-stark-cyan border-r-2 border-stark-cyan'
          : 'text-white/50 hover:text-white/80 hover:bg-white/5'
      }`}
    >
      <span style={{ color: iconColor }} className="shrink-0 text-[9px]">◆</span>
      <span className="truncate flex-1">{name}</span>
      {isNew && (
        <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-stark-orange shadow-[0_0_4px_#ff5500]" />
      )}
    </button>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default memo(function CodeApp({ initialFiles = [], taskDescription = '', onBack }) {
  const [allFiles,     setAllFiles]     = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent,  setFileContent]  = useState('');
  const [loadingFiles, setLoadingFiles] = useState(true);
  const [loadingCode,  setLoadingCode]  = useState(false);
  const [error,        setError]        = useState(null);
  const [newFiles,     setNewFiles]     = useState(new Set(initialFiles));
  const codeRef = useRef(null);

  // Fetch file tree on mount and when files are written
  const refreshFiles = useCallback(() => {
    setLoadingFiles(true);
    fetch(`${API}/sandbox/files`)
      .then(r => r.json())
      .then(d => {
        setAllFiles(d.files ?? []);
        setLoadingFiles(false);
        // Auto-select first new file if nothing selected
        if (!selectedFile && initialFiles.length > 0) {
          const first = initialFiles.find(f => d.files.includes(f));
          if (first) setSelectedFile(first);
        }
      })
      .catch(e => { setError(e.message); setLoadingFiles(false); });
  }, [selectedFile, initialFiles]);

  useEffect(() => { refreshFiles(); }, []); // eslint-disable-line

  // Update new-file highlights when initialFiles changes
  useEffect(() => {
    setNewFiles(new Set(initialFiles));
    // Clear highlights after 30 seconds
    const t = setTimeout(() => setNewFiles(new Set()), 30000);
    return () => clearTimeout(t);
  }, [initialFiles]);

  // Fetch file content when selection changes
  useEffect(() => {
    if (!selectedFile) return;
    setLoadingCode(true);
    setFileContent('');
    fetch(`${API}/sandbox/file?path=${encodeURIComponent(selectedFile)}`)
      .then(r => r.text())
      .then(text => { setFileContent(text); setLoadingCode(false); })
      .catch(e => { setFileContent(`// Error loading file: ${e.message}`); setLoadingCode(false); });
  }, [selectedFile]);

  // Scroll to top of code when file changes
  useEffect(() => {
    if (codeRef.current) codeRef.current.scrollTop = 0;
  }, [selectedFile]);

  const lang  = selectedFile ? extToLang(selectedFile) : 'text';
  const lines  = fileContent.split('\n');

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="w-full h-full flex flex-col bg-black/0"
      data-hand-component
    >
      {/* ── Header ── */}
      <div className="shrink-0 flex items-center gap-4 px-6 py-4 border-b border-stark-cyan/15 bg-black/60 backdrop-blur-xl no-drag">
        <button
          data-hand-target
          data-hand-label="BACK"
          onClick={onBack}
          className="flex items-center justify-center w-8 h-8 rounded-full border border-stark-cyan/30 text-stark-cyan/60 hover:text-stark-cyan hover:border-stark-cyan hover:bg-stark-cyan/10 transition-all duration-200"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="m15 18-6-6 6-6"/>
          </svg>
        </button>

        <div className="flex items-center gap-3">
          <div className="relative w-7 h-7 flex items-center justify-center">
            <div className="absolute w-7 h-7 rounded-full border border-stark-cyan/40 animate-spin" style={{ animationDuration: '10s' }} />
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#00f3ff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
            </svg>
          </div>
          <div>
            <div className="text-[11px] tracking-[0.35em] text-stark-cyan font-bold leading-none mb-0.5">CODE INSPECTOR</div>
            <div className="text-[9px] tracking-[0.25em] text-stark-cyan/40 leading-none">
              {selectedFile ?? 'SANDBOX EXPLORER'}
            </div>
          </div>
        </div>

        <div className="ml-auto flex items-center gap-3">
          {taskDescription && (
            <div className="max-w-xs px-3 py-1 rounded border border-stark-cyan/15 bg-stark-cyan/5">
              <div className="text-[8px] tracking-widest text-stark-cyan/30 font-mono">LAST TASK</div>
              <div className="text-[9px] text-stark-cyan/60 font-mono truncate">{taskDescription}</div>
            </div>
          )}
          <button
            data-hand-target
            data-hand-label="REFRESH"
            onClick={refreshFiles}
            className="flex items-center justify-center w-8 h-8 rounded-full border border-stark-cyan/20 text-stark-cyan/40 hover:text-stark-cyan hover:border-stark-cyan/60 transition-all duration-200"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>
            </svg>
          </button>
          <div className="text-[9px] tracking-[0.2em] text-stark-cyan/30 font-mono border border-stark-cyan/10 px-2 py-1 rounded">
            {lang.toUpperCase()}
          </div>
        </div>
      </div>

      {/* Scanline */}
      <div className="shrink-0 h-px w-full" style={{
        background: 'linear-gradient(90deg, transparent 0%, rgba(0,243,255,0.4) 30%, rgba(0,243,255,0.8) 50%, rgba(0,243,255,0.4) 70%, transparent 100%)',
      }} />

      {/* ── Body: file tree + code ── */}
      <div className="flex-1 min-h-0 flex flex-row overflow-hidden">

        {/* File tree */}
        <div className="w-56 shrink-0 border-r border-stark-cyan/10 bg-black/30 flex flex-col overflow-hidden">
          <div className="shrink-0 px-3 py-2 border-b border-stark-cyan/10">
            <span className="text-[8px] tracking-[0.3em] text-stark-cyan/30 font-mono">SANDBOX FILES</span>
          </div>
          <div className="flex-1 overflow-y-auto py-1">
            {loadingFiles ? (
              <div className="flex flex-col gap-2 p-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-3 bg-stark-cyan/10 rounded animate-pulse" style={{ width: `${60 + i * 7}%` }} />
                ))}
              </div>
            ) : allFiles.length === 0 ? (
              <div className="p-4 text-[10px] text-white/20 font-mono text-center">
                No files in sandbox
              </div>
            ) : (
              allFiles.map(f => (
                <FileTreeItem
                  key={f}
                  path={f}
                  isSelected={f === selectedFile}
                  isNew={newFiles.has(f)}
                  onClick={() => setSelectedFile(f)}
                />
              ))
            )}
          </div>
        </div>

        {/* Code viewer */}
        <div className="flex-1 min-w-0 flex flex-col overflow-hidden bg-black/20">
          {!selectedFile ? (
            // Empty state
            <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="rgba(0,243,255,0.15)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
              </svg>
              <div>
                <div className="text-[11px] text-white/20 font-mono tracking-widest mb-1">SELECT A FILE</div>
                {initialFiles.length > 0 && (
                  <div className="text-[9px] text-stark-cyan/30 font-mono">
                    {initialFiles.length} new file{initialFiles.length !== 1 ? 's' : ''} from last task
                  </div>
                )}
              </div>
            </div>
          ) : loadingCode ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="flex gap-1.5">
                {[0,1,2].map(i => (
                  <div key={i} className="w-1.5 h-1.5 rounded-full bg-stark-cyan/50 animate-pulse"
                    style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            </div>
          ) : (
            // Code with line numbers
            <div ref={codeRef} className="flex-1 overflow-auto" style={{ fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace" }}>
              <table className="w-full border-collapse text-[12px] leading-[1.6]">
                <tbody>
                  {lines.map((line, i) => (
                    <tr key={i} className="group hover:bg-stark-cyan/5 transition-colors">
                      <td className="select-none text-right pr-4 pl-4 text-white/20 group-hover:text-stark-cyan/40 transition-colors w-12 shrink-0 align-top"
                        style={{ fontSize: '10px', paddingTop: '0px', paddingBottom: '0px' }}>
                        {i + 1}
                      </td>
                      <td className="pl-2 pr-6 align-top whitespace-pre">
                        {line === '' ? (
                          <span>&nbsp;</span>
                        ) : (
                          tokenizeLine(line, lang).map((tok, j) => (
                            <span key={j} style={{ color: tok.color }}>{tok.text}</span>
                          ))
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Status bar at bottom of code panel */}
          <div className="shrink-0 flex items-center gap-4 px-4 py-1.5 border-t border-stark-cyan/10 bg-black/40">
            <span className="text-[9px] text-stark-cyan/30 font-mono tracking-wider">
              {selectedFile ? `${lines.length} lines` : '—'}
            </span>
            {selectedFile && (
              <>
                <span className="text-[9px] text-white/15 font-mono">·</span>
                <span className="text-[9px] text-stark-cyan/30 font-mono tracking-wider">
                  {lang.toUpperCase()}
                </span>
                <span className="text-[9px] text-white/15 font-mono">·</span>
                <span className="text-[9px] text-stark-cyan/30 font-mono tracking-wider">
                  {fileContent.length} chars
                </span>
              </>
            )}
            <div className="ml-auto flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400/60" />
              <span className="text-[9px] text-emerald-400/50 font-mono tracking-wider">SANDBOX</span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
});
```

---

## Section 6 — `worker_step_done` advances plan steps in real time

In Phase 2, `TaskMonitorApp` advanced steps on a naive timer. Now wire it to the real event.

**File:** `atlas-frontend/src/App.jsx`

In `handleWsMessage`, add:

```jsx
} else if (data.type === 'worker_step_done') {
  setActivePlan(prev => {
    if (!prev) return prev;
    const completed = [...prev.completed];
    if (data.payload.step_index < completed.length) {
      completed[data.payload.step_index] = true;
    }
    return {
      ...prev,
      completed,
      activeStep: Math.min(data.payload.step_index + 1, prev.steps.length - 1),
    };
  });
}
```

**File:** `atlas-frontend/src/components/TaskMonitorApp.jsx`

Remove the optimistic timer `useEffect` that was added in Phase 2 — it is no longer needed and will conflict with real events. The steps now advance only when `worker_step_done` fires.

---

## Section 7 — AppCarousel update for Code app badge

**File:** `atlas-frontend/src/components/AppCarousel.jsx`

Add `lastTaskFiles` prop and show the orange notification dot on `code`:

```jsx
export default memo(function AppCarousel({
  activeApp, setActiveApp, onAppOpen,
  isOpacityFixed, isFullscreen,
  activePlan,       // existing from Phase 2
  lastTaskFiles,    // NEW
}) {
```

```jsx
// Inside the map, for code orb:
{app.id === 'code' && lastTaskFiles?.files?.length > 0 && (
  <div className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-stark-orange shadow-[0_0_6px_#ff5500] animate-pulse" title={`${lastTaskFiles.files.length} files ready`} />
)}
```

Pass `lastTaskFiles` from `App.jsx`:

```jsx
<AppCarousel
  ...
  activePlan={activePlan}
  lastTaskFiles={lastTaskFiles}    // NEW
/>
```

---

## Implementation order

```
1. Section 1.1–1.3  (backend status tracker + WorkerNode callback)
2. Section 1.4–1.5  (backend REST endpoints)
3. Section 2.1–2.3  (wire status bar + lastTaskFiles state)
4. Section 2.2      (replace hardcoded dot rows with live counts)
5. Section 3.1      (back button + "View in Code" in TaskMonitorApp)
6. Section 3.2      (back button in MemoryApp)
7. Section 3.3      (App.jsx routing — pass onBack + onOpenCode)
8. Section 4.1–4.4  (CommandIntelPanel in ConsoleFullView)
9. Section 4.5      (auto-collapse behaviour)
10. Section 5.1     (carousel apps array — add code back)
11. Section 5.2     (CodeApp.jsx — create full file)
12. Section 6       (replace timer with real worker_step_done events)
13. Section 7       (AppCarousel badge for code app)
```

---

## Acceptance criteria

- [ ] Notification bar shows `0` active tasks at rest, increments to `1` while ATLAS is executing, increments DONE after completion
- [ ] `curl http://localhost:8000/status` returns live JSON
- [ ] TaskMonitorApp has a working back-to-hub button
- [ ] MemoryApp has a working back-to-hub button
- [ ] Both apps have `data-hand-component` and `data-hand-target` on interactive elements
- [ ] When a COMMAND is issued, `CommandIntelPanel` appears in the console with intent, mood, synthesized task, and plan steps — collapsed/expanded toggle works
- [ ] Plan steps in the panel advance in real time as `worker_step_done` fires (not on a timer)
- [ ] After a task that writes files, a "VIEW IN CODE →" banner appears in both ConsoleFullView and TaskMonitorApp
- [ ] Clicking "VIEW IN CODE →" opens CodeApp with the correct files pre-highlighted in orange in the file tree
- [ ] CodeApp file tree populates from `/sandbox/files`
- [ ] Selecting a file in CodeApp fetches and displays its content with syntax highlighting
- [ ] Line numbers are visible and correct
- [ ] Refresh button in CodeApp re-fetches the file tree
- [ ] Code app carousel slot shows an orange dot when files are ready to inspect
- [ ] `npm run lint` passes with no new errors
- [ ] `npm run build` passes

---

## Files modified summary

| File | Change type |
|---|---|
| `atlas-backend/api_server.py` | Add runtime status tracker, 3 REST routes, `_emit_task_files`, `_on_worker_step` callback wiring |
| `atlas-backend/core/brain/interface/worker.py` | Add `on_step_done` callback hook |
| `atlas-frontend/src/App.jsx` | Add `statusCounts`, `lastTaskFiles` state; wire `status_update`, `task_files`, `worker_step_done` events; add `handleOpenCode`; extend AnimatePresence routing |
| `atlas-frontend/src/components/AppCarousel.jsx` | Restore `code` app slot; add `lastTaskFiles` prop + badge |
| `atlas-frontend/src/components/TaskMonitorApp.jsx` | Add header with back button + "View in Code"; remove optimistic timer; add `data-hand-*` attributes |
| `atlas-frontend/src/components/MemoryApp.jsx` | Add header with back button; add `data-hand-*` attributes |
| `atlas-frontend/src/components/ConsoleFullView.jsx` | Add `CommandIntelPanel` sub-component; add "View in Code" banner; add props |
| `atlas-frontend/src/components/CodeApp.jsx` | **Create new** — full IDE component |

**Total: 8 files, 1 new component, ~500 lines of new code.**
