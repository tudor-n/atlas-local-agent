// atlas-frontend/src/hooks/useHandTracking.js
//
// v6 — Comfort-first rewrite
//
// Design principles:
//  1. PALM CENTER tracking (lm[9]) for both modes — stable, works with any relaxed hand
//  2. ANY non-fist gesture = active — no awkward "hold this pose to track" requirement
//  3. ANY horizontal swipe (either direction) = NEXT — no need to remember which way
//  4. NO gesture-based mode switching — UI button only
//  5. GPU delegate first, CPU fallback
//  6. 60fps for lower perceived latency

import { useEffect, useRef, useState } from 'react';

const WASM  = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.17/wasm';
const MODEL = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task';

const TARGET_FPS = 30;
const FRAME_MS   = 1000 / TARGET_FPS;

// ── One-Euro Filter ───────────────────────────────────────────────────────────
class OneEuroFilter {
  constructor(minCutoff = 1.5, beta = 0.01, dcutoff = 1.0) {
    this.minCutoff = minCutoff;
    this.beta      = beta;
    this.dcutoff   = dcutoff;
    this.x         = null;
    this.dx        = 0;
    this.lastTs    = null;
  }
  _alpha(cutoff, dt) {
    const tau = 1.0 / (2 * Math.PI * cutoff);
    return 1.0 / (1.0 + tau / dt);
  }
  filter(x, ts) {
    if (this.x === null) { this.x = x; this.lastTs = ts; return x; }
    const dt    = Math.max(0.001, (ts - this.lastTs) / 1000);
    this.lastTs = ts;
    const dxRaw = (x - this.x) / dt;
    this.dx     = this.dx + this._alpha(this.dcutoff, dt) * (dxRaw - this.dx);
    const cutoff = this.minCutoff + this.beta * Math.abs(this.dx);
    this.x      = this.x + this._alpha(cutoff, dt) * (x - this.x);
    return this.x;
  }
  reset() { this.x = null; this.dx = 0; this.lastTs = null; }
}

// ── Tuning ────────────────────────────────────────────────────────────────────
const SWIPE = {
  FRAMES:      5,      // frames of consistent motion needed
  THRESH:      0.010,  // per-frame delta threshold
  COOLDOWN_MS: 800,    // lockout after a swipe fires
};
const DWELL = {
  MS:     600,   // hold time to trigger click
  BURST:  380,   // faster after a recent dwell
  RADIUS: 65,    // px — drift allowed during dwell
  SNAP:   72,    // px — snap-to radius
};
const MOUSE = {
  MIN_CUTOFF: 1.5,   // One-Euro: responsiveness at low speed
  BETA:       0.01,  // One-Euro: speed-dependent smoothing
  MARGIN:     0.20,  // input zone margin — 20% on each side = comfortable central zone
  PINCH_CLOSE: 0.052,
  PINCH_OPEN:  0.085,
};

const clamp  = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

function dist3D(a, b) {
  return Math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2 + (a.z-b.z)**2);
}

// ── Gesture classification ────────────────────────────────────────────────────
// Simplified: pinch | fist | open
// "open" covers relaxed hand, pointing, any non-fist non-pinch pose.
// This removes the awkward "hold exact gesture to enable tracking" UX.
const FIST_THRESH  = 0.18; // tip-to-MCP distance for "finger extended"

function classifyGesture(lm) {
  // Pinch: index tip to thumb tip
  if (dist3D(lm[8], lm[4]) < MOUSE.PINCH_CLOSE) return 'pinch';

  // Fist: all four fingers folded (tip close to base knuckle)
  const indexExt  = dist3D(lm[8],  lm[5])  > FIST_THRESH;
  const middleExt = dist3D(lm[12], lm[9])  > FIST_THRESH;
  const ringExt   = dist3D(lm[16], lm[13]) > FIST_THRESH;
  const pinkyExt  = dist3D(lm[20], lm[17]) > FIST_THRESH;
  if (!indexExt && !middleExt && !ringExt && !pinkyExt) return 'fist';

  return 'open'; // anything else — relaxed, pointing, splayed, etc.
}

// ── DOM target cache ──────────────────────────────────────────────────────────
const _targetCache = { els: [], ts: 0 };
function findNearestTarget(px, py) {
  const now = performance.now();
  if (now - _targetCache.ts > 500) {
    _targetCache.els = [...document.querySelectorAll('[data-hand-target]')];
    _targetCache.ts  = now;
  }
  let best = null, bestD = Infinity;
  for (const el of _targetCache.els) {
    if (!el.isConnected) continue;
    const r  = el.getBoundingClientRect();
    const cx = r.left + r.width  / 2;
    const cy = r.top  + r.height / 2;
    const d  = Math.hypot(px - cx, py - cy);
    if (d < DWELL.SNAP && d < bestD) { bestD = d; best = { el, cx, cy }; }
  }
  return best;
}

// ── Camera open ───────────────────────────────────────────────────────────────
async function openCamera() {
  const attempts = [
    { video: { facingMode: 'user', width: { ideal: 320 }, height: { ideal: 240 }, frameRate: { ideal: 30 } } },
    { video: { facingMode: 'user', width: { ideal: 320 }, height: { ideal: 240 } } },
    { video: { facingMode: 'user' } },
    { video: true },
  ];
  for (const c of attempts) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia(c);
      console.log('[ATLAS HandTracker] Camera OK:', JSON.stringify(c.video));
      return stream;
    } catch (e) {
      console.warn('[ATLAS HandTracker] Camera attempt failed:', e.message);
    }
  }
  throw new Error('No camera available');
}

// ── Hook ──────────────────────────────────────────────────────────────────────
export function useHandTracking({ enabled = true, mode = 'swipe' } = {}) {
  const videoRef      = useRef(null);
  const landmarker    = useRef(null);
  const rafRef        = useRef(null);
  const lastFrameTs   = useRef(0);
  const lastVideoTs   = useRef(-1);
  const cancelledRef  = useRef(false);   // used by detectLoop to self-stop

  // Filters for palm position (mouse mode)
  const filterX = useRef(new OneEuroFilter(MOUSE.MIN_CUTOFF, MOUSE.BETA));
  const filterY = useRef(new OneEuroFilter(MOUSE.MIN_CUTOFF, MOUSE.BETA));
  const cursorPx = useRef({ x: window.innerWidth / 2, y: window.innerHeight / 2 });

  // Swipe state
  const swipeFrames   = useRef([]);
  const prevPalmX     = useRef(null);
  const swipeCooldown = useRef(false);

  // Pinch state
  const wasPinching  = useRef(false);
  const pinchLockout = useRef(false);

  // Dwell state
  const dwellStart        = useRef(null);
  const dwellAnchor       = useRef(null);
  const dwellEl           = useRef(null);
  const dwellFired        = useRef(false);
  const lastDwellFireRef  = useRef(0);

  const modeRef = useRef(mode);

  // State-update guards
  const isTrackingRef    = useRef(false);
  const gestureRef       = useRef('none');
  const isPinchingRef    = useRef(false);
  const swipeDirRef      = useRef(null);
  const cursorDisplayRef = useRef({ x: window.innerWidth / 2, y: window.innerHeight / 2 });

  // Reset filter state on mode switch
  useEffect(() => {
    modeRef.current = mode;
    filterX.current.reset();
    filterY.current.reset();
    swipeFrames.current = [];
    prevPalmX.current   = null;
  }, [mode]);

  const [cursor,        setCursor]        = useState({ x: window.innerWidth / 2, y: window.innerHeight / 2 });
  const [dwellProgress, setDwellProgress] = useState(0);
  const [dwellTarget,   setDwellTarget]   = useState(null);
  const [swipeDir,      setSwipeDir]      = useState(null);
  const [isTracking,    setIsTracking]    = useState(false);
  const [gesture,       setGesture]       = useState('none');
  const [isPinching,    setIsPinching]    = useState(false);
  const [pinchClick,    setPinchClick]    = useState(0);
  const [isReady,       setIsReady]       = useState(false);
  const [initError,     setInitError]     = useState(null);

  // ── Init ────────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    cancelledRef.current = false;

    async function init() {
      try {
        const { FilesetResolver, HandLandmarker } = await import('@mediapipe/tasks-vision');
        const vision = await FilesetResolver.forVisionTasks(WASM);

        // Try GPU first — significantly better frame rate on capable hardware
        let lm;
        try {
          lm = await HandLandmarker.createFromOptions(vision, {
            baseOptions: { modelAssetPath: MODEL, delegate: 'GPU' },
            runningMode: 'VIDEO',
            numHands: 1,
          });
          console.log('[ATLAS HandTracker] GPU delegate active');
        } catch (gpuErr) {
          console.warn('[ATLAS HandTracker] GPU unavailable, falling back to CPU:', gpuErr.message);
          lm = await HandLandmarker.createFromOptions(vision, {
            baseOptions: { modelAssetPath: MODEL, delegate: 'CPU' },
            runningMode: 'VIDEO',
            numHands: 1,
          });
        }

        if (cancelled) return;
        landmarker.current = lm;

        const video = document.createElement('video');
        video.autoplay    = true;
        video.playsInline = true;
        video.muted       = true;
        video.style.cssText = 'position:fixed;top:-9999px;left:-9999px;width:1px;height:1px;pointer-events:none;';
        document.body.appendChild(video);
        videoRef.current = video;

        const stream = await openCamera();
        if (cancelled) { stream.getTracks().forEach(t => t.stop()); return; }

        video.srcObject = stream;

        await new Promise((resolve, reject) => {
          video.addEventListener('loadeddata', resolve, { once: true });
          video.addEventListener('error',      reject,  { once: true });
          setTimeout(() => reject(new Error('Video load timeout after 8s')), 8000);
        });

        if (!cancelled) {
          setIsReady(true);
          detectLoop();
        }
      } catch (err) {
        if (!cancelled) {
          console.error('[ATLAS HandTracker] Init failed:', err);
          setInitError(err.message);
        }
      }
    }

    init();

    return () => {
      cancelled = true;
      cancelledRef.current = true;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      videoRef.current?.srcObject?.getTracks?.().forEach(t => t.stop());
      videoRef.current?.remove();
      videoRef.current   = null;
      landmarker.current = null;
      setIsReady(false);
    };
  }, [enabled]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Detection loop ───────────────────────────────────────────────────────────
  function detectLoop() {
    if (cancelledRef.current) return;  // guard against stale closures on rapid toggle
    const now = performance.now();
    if (now - lastFrameTs.current >= FRAME_MS) {
      lastFrameTs.current = now;
      const video = videoRef.current;
      const lm    = landmarker.current;
      if (video && lm && video.readyState >= 2 && video.currentTime !== lastVideoTs.current) {
        lastVideoTs.current = video.currentTime;
        try {
          const results = lm.detectForVideo(video, now);
          if (results?.landmarks?.length > 0) {
            if (!isTrackingRef.current) { isTrackingRef.current = true; setIsTracking(true); }
            processHand(results.landmarks[0]);
          } else {
            handleNoHand();
          }
        } catch (err) {
          console.warn('[ATLAS HandTracker] Frame error (skipped):', err.message);
        }
      }
    }
    rafRef.current = requestAnimationFrame(detectLoop);
  }

  function handleNoHand() {
    if (isTrackingRef.current)         { isTrackingRef.current = false;  setIsTracking(false); }
    if (gestureRef.current !== 'none') { gestureRef.current = 'none';    setGesture('none'); }
    if (isPinchingRef.current)         { isPinchingRef.current = false;  setIsPinching(false); }
    if (swipeDirRef.current !== null)  { swipeDirRef.current = null;     setSwipeDir(null); }
    wasPinching.current  = false;
    prevPalmX.current    = null;
    swipeFrames.current  = [];
    pinchLockout.current = false;
    filterX.current.reset();
    filterY.current.reset();
    resetDwell();
  }

  function processHand(lm) {
    const g = classifyGesture(lm);
    if (g !== gestureRef.current) { gestureRef.current = g; setGesture(g); }

    // Fist = full pause: reset everything, hold cursor in place
    if (g === 'fist') {
      wasPinching.current  = false;
      prevPalmX.current    = null;
      swipeFrames.current  = [];
      pinchLockout.current = false;
      if (isPinchingRef.current) { isPinchingRef.current = false; setIsPinching(false); }
      if (swipeDirRef.current !== null) { swipeDirRef.current = null; setSwipeDir(null); }
      filterX.current.reset();
      filterY.current.reset();
      resetDwell();
      return;
    }

    modeRef.current === 'swipe' ? processSwipeMode(lm, g) : processMouseMode(lm, g);
  }

  // ── Swipe mode ───────────────────────────────────────────────────────────────
  // Tracks palm horizontal movement. Any consistent swipe (left OR right) = NEXT.
  // Pinch = open/select. Works with relaxed open hand.
  function processSwipeMode(lm, g) {
    // Pinch to select
    if (g === 'pinch') {
      if (!wasPinching.current && !pinchLockout.current) {
        wasPinching.current = true;
        if (!isPinchingRef.current) { isPinchingRef.current = true; setIsPinching(true); }
        setPinchClick(c => c + 1);
      }
      swipeFrames.current = [];
      prevPalmX.current   = null;
      return;
    }

    if (wasPinching.current) {
      wasPinching.current = false;
      if (isPinchingRef.current) { isPinchingRef.current = false; setIsPinching(false); }
    }

    // Track palm center for swipe — lm[9] = middle finger MCP, most stable palm point
    const palmX = 1 - lm[9].x; // mirror so motion matches visual direction
    if (prevPalmX.current !== null) {
      const delta = palmX - prevPalmX.current;
      swipeFrames.current.push(delta);
      if (swipeFrames.current.length > SWIPE.FRAMES) swipeFrames.current.shift();

      if (swipeFrames.current.length >= SWIPE.FRAMES && !swipeCooldown.current) {
        const allLeft  = swipeFrames.current.every(d => d < -SWIPE.THRESH);
        const allRight = swipeFrames.current.every(d => d >  SWIPE.THRESH);
        if (allLeft || allRight) {
          // Both directions = NEXT (no need to remember which way to swipe)
          swipeDirRef.current = 'next';
          setSwipeDir('next');
          swipeCooldown.current = true;
          pinchLockout.current  = true;
          swipeFrames.current   = [];
          setTimeout(() => {
            swipeCooldown.current   = false;
            swipeDirRef.current     = null;
            setSwipeDir(null);
          }, SWIPE.COOLDOWN_MS);
          setTimeout(() => { pinchLockout.current = false; }, SWIPE.COOLDOWN_MS + 100);
        }
      }
    }
    prevPalmX.current = palmX;
  }

  // ── Mouse mode ───────────────────────────────────────────────────────────────
  // Tracks palm center (lm[9]) directly to screen position.
  // Works with any hand gesture — open, relaxed, pinch, etc.
  // No specific pose required; just hold your hand in a comfortable position.
  function processMouseMode(lm, g) {
    swipeFrames.current = [];
    prevPalmX.current   = null;
    if (swipeDirRef.current !== null) { swipeDirRef.current = null; setSwipeDir(null); }

    // Pinch = click
    const pinchDist = dist3D(lm[8], lm[4]);
    if (!wasPinching.current && pinchDist < MOUSE.PINCH_CLOSE) {
      wasPinching.current = true;
      if (!isPinchingRef.current) { isPinchingRef.current = true; setIsPinching(true); }
      const snap = findNearestTarget(cursorPx.current.x, cursorPx.current.y);
      if (snap) snap.el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
      else      setPinchClick(c => c + 1);
    } else if (wasPinching.current && pinchDist > MOUSE.PINCH_OPEN) {
      wasPinching.current = false;
      if (isPinchingRef.current) { isPinchingRef.current = false; setIsPinching(false); }
    }

    // Absolute palm position → screen coordinates
    // lm[9] = middle finger MCP joint = center of palm — tracks with any hand shape
    const rawX = 1 - lm[9].x; // mirror
    const rawY = lm[9].y;
    const now  = performance.now();

    const smoothX = filterX.current.filter(rawX, now);
    const smoothY = filterY.current.filter(rawY, now);

    // MARGIN crops the outer 20% of the camera frame on each side,
    // so comfortable central hand positions cover the full screen.
    const sx = clamp((smoothX - MOUSE.MARGIN) / (1 - 2 * MOUSE.MARGIN), 0, 1) * window.innerWidth;
    const sy = clamp((smoothY - MOUSE.MARGIN) / (1 - 2 * MOUSE.MARGIN), 0, 1) * window.innerHeight;

    cursorPx.current = { x: sx, y: sy };

    const snap       = findNearestTarget(sx, sy);
    const displayPos = snap ? { x: snap.cx, y: snap.cy } : { x: sx, y: sy };

    if (Math.abs(displayPos.x - cursorDisplayRef.current.x) > 0.5 ||
        Math.abs(displayPos.y - cursorDisplayRef.current.y) > 0.5) {
      cursorDisplayRef.current = displayPos;
      setCursor(displayPos);
    }

    // Dwell disabled while pinching (pinch is already the click action)
    if (g !== 'pinch') tickDwell(displayPos.x, displayPos.y, snap?.el ?? null);
    else resetDwell();
  }

  // ── Dwell ────────────────────────────────────────────────────────────────────
  function tickDwell(px, py, el = null) {
    const now = performance.now();
    if (!el) { resetDwell(); return; }
    const dwellMs = (now - lastDwellFireRef.current < 3000) ? DWELL.BURST : DWELL.MS;
    if (dwellEl.current !== el) {
      dwellStart.current  = now;
      dwellAnchor.current = { x: px, y: py };
      dwellEl.current     = el;
      dwellFired.current  = false;
      setDwellTarget(el);
      setDwellProgress(0);
      return;
    }
    const drift = Math.hypot(px - dwellAnchor.current.x, py - dwellAnchor.current.y);
    if (drift > DWELL.RADIUS) {
      dwellStart.current  = now;
      dwellAnchor.current = { x: px, y: py };
      dwellFired.current  = false;
      setDwellProgress(0);
      return;
    }
    const progress = Math.min((now - dwellStart.current) / dwellMs, 1);
    setDwellProgress(progress);
    if (progress >= 1 && !dwellFired.current) {
      dwellFired.current       = true;
      lastDwellFireRef.current = now;
      el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
      setTimeout(() => resetDwell(), 900);
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

  return {
    cursor,
    dwellProgress,
    dwellTarget,
    swipeDir,
    isTracking,
    gesture,
    isPinching,
    pinchClick,
    isReady,
    initError,
  };
}
