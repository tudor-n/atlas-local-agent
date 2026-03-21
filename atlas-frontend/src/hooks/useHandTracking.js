// atlas-frontend/src/hooks/useHandTracking.js
//
// ═══════════════════════════════════════════════════════════════
//  THE THREE FIXES THAT MAKE HAND TRACKING USABLE
// ═══════════════════════════════════════════════════════════════
//
//  1. RELATIVE MODE (most important)
//     Absolute mapping = arm must stay raised at exact screen coords. Exhausting.
//     Relative mode = only the *delta* matters. Hand rests naturally.
//     Identical to how a mouse works — you don't map your wrist to the screen,
//     you move from wherever your hand already is.
//
//  2. DWELL-TO-CLICK (replaces pinch)
//     Pinch is unreliable — the model sees a "pinch" when fingers just get close.
//     Dwell = cursor stays inside a target for DWELL_MS → fires click.
//     Used by every serious accessibility / kiosk hand-tracking system.
//     A visible arc countdown gives the user time to abort by moving away.
//
//  3. DEAD ZONE + DOUBLE-EXPONENTIAL SMOOTHING (replaces lerp)
//     Simple lerp just delays jitter — you still see the jitter, just slower.
//     Dead zone: ignore movements below DEAD_ZONE threshold entirely.
//     Double-exp (Holt's method): tracks both position AND velocity so the
//     cursor predicts ahead slightly, making it feel responsive not laggy.
//
// ───────────────────────────────────────────────────────────────
//  Returned values
// ───────────────────────────────────────────────────────────────
//  cursor        { x, y }  — pixel coords, clamped to viewport
//  dwellProgress number    — 0..1, how close to a dwell-click firing
//  dwellTarget   element   — the DOM element being dwelled on (or null)
//  isTracking    bool
//  gesture       string    — 'point' | 'fist' | 'open' | 'none'
//  isReady       bool

import { useEffect, useRef, useState, useCallback } from 'react';

// ── CDN paths ────────────────────────────────────────────────────────────────
const WASM  = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.17/wasm';
const MODEL = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task';

// ── Tuning ───────────────────────────────────────────────────────────────────
// Relative mode sensitivity — how many pixels the cursor moves per unit of hand delta
// Increase if the cursor feels sluggish, decrease if it overshoots
const SENSITIVITY   = 3.2;

// Movement below this threshold (normalised 0..1) is ignored entirely.
// Eliminates camera noise and hand tremor without making the cursor feel sticky.
const DEAD_ZONE     = 0.008;

// Double-exponential smoothing factors (Holt's method)
// ALPHA: how quickly position tracks the raw signal  (0=frozen, 1=raw)
// BETA:  how quickly velocity adapts                 (0=no prediction, 1=instant)
const ALPHA         = 0.35;
const BETA          = 0.08;

// How long (ms) the cursor must stay inside a [data-hand-target] to fire a click
const DWELL_MS      = 820;

// Cursor must stay within this pixel radius for dwell to count
const DWELL_RADIUS  = 48;

// Snap-to-target radius — cursor visually snaps when this close
const SNAP_RADIUS   = 56;

// Open palm swipe: requires this many consecutive frames of consistent velocity
const SWIPE_FRAMES  = 8;
const SWIPE_THRESH  = 0.014; // normalised delta per frame to count as "swipe intent"

// ── Helpers ──────────────────────────────────────────────────────────────────
function dist2D(a, b) { return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2); }
function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

// Classify gesture from landmarks
function classifyGesture(lm) {
  const pinchDist = dist2D(lm[8], lm[4]);
  const indexExt  = lm[8].y  < lm[6].y;
  const middleExt = lm[12].y < lm[10].y;
  const ringExt   = lm[16].y < lm[14].y;
  const pinkyExt  = lm[20].y < lm[18].y;
  const extCount  = [indexExt, middleExt, ringExt, pinkyExt].filter(Boolean).length;

  if (pinchDist < 0.045)                  return 'pinch'; // kept as backup
  if (extCount === 0)                     return 'fist';  // fist = pause tracking
  if (extCount >= 3)                      return 'open';  // flat palm = swipe mode
  if (indexExt && extCount === 1)         return 'point'; // finger gun = move cursor
  return 'none';
}

function findNearestTarget(px, py) {
  const els = document.querySelectorAll('[data-hand-target]');
  let best = null, bestD = Infinity;
  els.forEach(el => {
    const r  = el.getBoundingClientRect();
    const cx = r.left + r.width  / 2;
    const cy = r.top  + r.height / 2;
    const d  = Math.hypot(px - cx, py - cy);
    if (d < SNAP_RADIUS && d < bestD) { bestD = d; best = { el, cx, cy, d }; }
  });
  return best;
}

// ── Hook ─────────────────────────────────────────────────────────────────────
export function useHandTracking({ enabled = true } = {}) {
  const videoRef   = useRef(null);
  const landmarker = useRef(null);
  const rafRef     = useRef(null);
  const lastTime   = useRef(-1);

  // ── Relative cursor state ──────────────────────────────────────────────────
  // We accumulate cursor position in pixels (not normalised) for precision
  const cursorPx    = useRef({ x: window.innerWidth / 2, y: window.innerHeight / 2 });
  // Double-exponential state
  const dex         = useRef({ pos: { x: 0.5, y: 0.5 }, vel: { x: 0, y: 0 } });
  const prevRaw     = useRef(null); // normalised, for delta calculation

  // ── Swipe state ────────────────────────────────────────────────────────────
  const swipeFrames = useRef([]);   // ring buffer of per-frame palm X deltas
  const prevPalmX   = useRef(null);

  // ── Dwell state ────────────────────────────────────────────────────────────
  const dwellStart  = useRef(null);       // timestamp when dwell began
  const dwellAnchor = useRef(null);       // { x, y } where dwell started
  const dwellEl     = useRef(null);       // element being dwelled on
  const dwellFired  = useRef(false);      // prevent re-firing same dwell

  // ── Published state ────────────────────────────────────────────────────────
  const [cursor,        setCursor]        = useState({ x: window.innerWidth/2, y: window.innerHeight/2 });
  const [dwellProgress, setDwellProgress] = useState(0);
  const [dwellTarget,   setDwellTarget]   = useState(null);
  const [swipeDir,      setSwipeDir]      = useState(null); // 'left'|'right'|null
  const [isTracking,    setIsTracking]    = useState(false);
  const [gesture,       setGesture]       = useState('none');
  const [isReady,       setIsReady]       = useState(false);

  // ── Init ───────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;

    async function init() {
      try {
        const { FilesetResolver, HandLandmarker } = await import('@mediapipe/tasks-vision');
        const vision = await FilesetResolver.forVisionTasks(WASM);
        landmarker.current = await HandLandmarker.createFromOptions(vision, {
          baseOptions: { modelAssetPath: MODEL, delegate: 'GPU' },
          runningMode: 'VIDEO',
          numHands: 1,  // single hand = lower latency, simpler UX
        });
        if (cancelled) return;

        const video = document.createElement('video');
        video.autoplay = true; video.playsInline = true; video.style.display = 'none';
        document.body.appendChild(video);
        videoRef.current = video;

        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: 640, height: 480, frameRate: { ideal: 60 } },
        });
        video.srcObject = stream;
        video.addEventListener('loadeddata', () => {
          if (!cancelled) { setIsReady(true); detectFrame(); }
        });
      } catch (err) {
        console.warn('[ATLAS HandTracker] Init failed:', err);
      }
    }
    init();
    return () => {
      cancelled = true;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      videoRef.current?.srcObject?.getTracks?.().forEach(t => t.stop());
      videoRef.current?.remove();
      videoRef.current = null;
      landmarker.current = null;
      setIsReady(false);
    };
  }, [enabled]); // eslint-disable-line

  // ── Detection loop ─────────────────────────────────────────────────────────
  function detectFrame() {
    const video = videoRef.current;
    const lm    = landmarker.current;
    if (!video || !lm || video.readyState < 2) {
      rafRef.current = requestAnimationFrame(detectFrame); return;
    }
    if (video.currentTime === lastTime.current) {
      rafRef.current = requestAnimationFrame(detectFrame); return;
    }
    lastTime.current = video.currentTime;

    const results = lm.detectForVideo(video, performance.now());
    if (results.landmarks?.length > 0) {
      setIsTracking(true);
      processHand(results.landmarks[0]);
    } else {
      setIsTracking(false);
      setGesture('none');
      prevRaw.current = null;
      prevPalmX.current = null;
      resetDwell();
      setSwipeDir(null);
    }
    rafRef.current = requestAnimationFrame(detectFrame);
  }

  // ── Main hand processor ────────────────────────────────────────────────────
  function processHand(lm) {
    const g = classifyGesture(lm);
    setGesture(g);

    // ── FIST: pause all tracking ─────────────────────────────────────────────
    if (g === 'fist') {
      prevRaw.current = null;
      prevPalmX.current = null;
      resetDwell();
      setSwipeDir(null);
      return;
    }

    // ── OPEN PALM: swipe detection only ─────────────────────────────────────
    // We track palm centre horizontal velocity over SWIPE_FRAMES frames.
    // Only publish swipeDir when we see consistent unidirectional movement.
    if (g === 'open') {
      const palmX = 1 - lm[9].x; // mirror X
      if (prevPalmX.current !== null) {
        const delta = palmX - prevPalmX.current;
        swipeFrames.current.push(delta);
        if (swipeFrames.current.length > SWIPE_FRAMES) swipeFrames.current.shift();

        if (swipeFrames.current.length >= SWIPE_FRAMES) {
          const allRight = swipeFrames.current.every(d => d >  SWIPE_THRESH);
          const allLeft  = swipeFrames.current.every(d => d < -SWIPE_THRESH);
          if (allRight)      setSwipeDir('right');
          else if (allLeft)  setSwipeDir('left');
          else               setSwipeDir(null);
        }
      }
      prevPalmX.current = palmX;
      prevRaw.current   = null; // don't blend with point mode
      return;
    }

    // Clear swipe when not using open palm
    swipeFrames.current = [];
    prevPalmX.current = null;
    setSwipeDir(null);

    // ── POINT / PINCH: cursor movement ───────────────────────────────────────
    const rawX = 1 - lm[8].x; // mirror X
    const rawY = lm[8].y;

    if (prevRaw.current === null) {
      // First frame after re-acquiring — just anchor, don't jump cursor
      prevRaw.current = { x: rawX, y: rawY };
      dex.current.pos = { x: rawX, y: rawY };
      dex.current.vel = { x: 0,    y: 0    };
      return;
    }

    // ── Dead zone ────────────────────────────────────────────────────────────
    const dx = rawX - prevRaw.current.x;
    const dy = rawY - prevRaw.current.y;
    const mag = Math.sqrt(dx * dx + dy * dy);

    if (mag < DEAD_ZONE) {
      // Below dead zone — still run dwell tick but don't move cursor
      tickDwell(cursorPx.current.x, cursorPx.current.y);
      return;
    }
    prevRaw.current = { x: rawX, y: rawY };

    // ── Double-exponential smoothing ─────────────────────────────────────────
    const prev = dex.current;
    const newPos = {
      x: ALPHA * rawX + (1 - ALPHA) * (prev.pos.x + prev.vel.x),
      y: ALPHA * rawY + (1 - ALPHA) * (prev.pos.y + prev.vel.y),
    };
    const newVel = {
      x: BETA * (newPos.x - prev.pos.x) + (1 - BETA) * prev.vel.x,
      y: BETA * (newPos.y - prev.pos.y) + (1 - BETA) * prev.vel.y,
    };
    dex.current = { pos: newPos, vel: newVel };

    // ── Relative accumulation ─────────────────────────────────────────────────
    // Smoothed delta drives the cursor, not the absolute position.
    const sdx = (newPos.x - prev.pos.x) * window.innerWidth  * SENSITIVITY;
    const sdy = (newPos.y - prev.pos.y) * window.innerHeight * SENSITIVITY;

    cursorPx.current = {
      x: clamp(cursorPx.current.x + sdx, 0, window.innerWidth),
      y: clamp(cursorPx.current.y + sdy, 0, window.innerHeight),
    };

    // ── Snap to nearest target ────────────────────────────────────────────────
    const snap = findNearestTarget(cursorPx.current.x, cursorPx.current.y);
    const displayPos = snap
      ? { x: snap.cx, y: snap.cy }
      : { x: cursorPx.current.x, y: cursorPx.current.y };

    setCursor(displayPos);

    // ── Dwell tick ────────────────────────────────────────────────────────────
    tickDwell(displayPos.x, displayPos.y, snap?.el ?? null);
  }

  // ── Dwell logic ────────────────────────────────────────────────────────────
  function tickDwell(px, py, el = null) {
    const now = performance.now();

    if (!el) {
      resetDwell();
      return;
    }

    // New target or cursor moved too far from anchor
    if (dwellEl.current !== el) {
      dwellStart.current  = now;
      dwellAnchor.current = { x: px, y: py };
      dwellEl.current     = el;
      dwellFired.current  = false;
      setDwellTarget(el);
      setDwellProgress(0);
      return;
    }

    // Check cursor hasn't wandered off (even if still over same element)
    const drift = Math.hypot(px - dwellAnchor.current.x, py - dwellAnchor.current.y);
    if (drift > DWELL_RADIUS) {
      // Reset but keep element — user is still hovering, just wiggling
      dwellStart.current  = now;
      dwellAnchor.current = { x: px, y: py };
      dwellFired.current  = false;
      setDwellProgress(0);
      return;
    }

    const elapsed  = now - dwellStart.current;
    const progress = Math.min(elapsed / DWELL_MS, 1);
    setDwellProgress(progress);

    if (progress >= 1 && !dwellFired.current) {
      dwellFired.current = true;
      // Synthesise a real click so React onClick handlers fire normally
      el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
      // Brief lockout to prevent repeat-firing
      setTimeout(() => {
        resetDwell();
      }, 900);
    }
  }

  function resetDwell() {
    dwellStart.current  = null;
    dwellAnchor.current = null;
    dwellEl.current     = null;
    dwellFired.current  = false;
    setDwellTarget(null);
    setDwellProgress(0);
  }

  return { cursor, dwellProgress, dwellTarget, swipeDir, isTracking, gesture, isReady };
}