// atlas-frontend/src/components/HandCursor.jsx
//
// v6 — Simplified HUD overlay, no gesture mode-switching UI.
//
// SWIPE MODE: Shows palm indicator and swipe flash. Any swipe = NEXT.
// MOUSE MODE: Crosshair follows palm. Dwell arc for hold-to-click.
// Both modes: status badge top-centre.

import { useEffect, useRef, useState, memo } from 'react';

const SNAP_RADIUS = 72;

const enc = (svg) =>
  `url("data:image/svg+xml,${encodeURIComponent(svg.trim())}") 16 16, crosshair`;

const CURSOR_NORMAL = enc(`
<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">
  <g stroke="#00f3ff" stroke-linecap="round" fill="none">
    <polyline points="4,4 9,4"    stroke-width="1.5"/>
    <polyline points="4,4 4,9"    stroke-width="1.5"/>
    <polyline points="28,4 23,4"  stroke-width="1.5"/>
    <polyline points="28,4 28,9"  stroke-width="1.5"/>
    <polyline points="4,28 9,28"  stroke-width="1.5"/>
    <polyline points="4,28 4,23"  stroke-width="1.5"/>
    <polyline points="28,28 23,28" stroke-width="1.5"/>
    <polyline points="28,28 28,23" stroke-width="1.5"/>
    <line x1="13.5" y1="16" x2="15"   y2="16" stroke-width="1" opacity="0.6"/>
    <line x1="17"   y1="16" x2="18.5" y2="16" stroke-width="1" opacity="0.6"/>
    <line x1="16" y1="13.5" x2="16" y2="15"   stroke-width="1" opacity="0.6"/>
    <line x1="16" y1="17"   x2="16" y2="18.5" stroke-width="1" opacity="0.6"/>
  </g>
  <circle cx="16" cy="16" r="1.6" fill="#00f3ff"/>
</svg>`);

const CURSOR_HOVER = enc(`
<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">
  <g stroke="#00f3ff" stroke-linecap="round" fill="none">
    <polyline points="2,2 11,2"    stroke-width="2"/>
    <polyline points="2,2 2,11"    stroke-width="2"/>
    <polyline points="30,2 21,2"   stroke-width="2"/>
    <polyline points="30,2 30,11"  stroke-width="2"/>
    <polyline points="2,30 11,30"  stroke-width="2"/>
    <polyline points="2,30 2,21"   stroke-width="2"/>
    <polyline points="30,30 21,30" stroke-width="2"/>
    <polyline points="30,30 30,21" stroke-width="2"/>
  </g>
  <circle cx="16" cy="16" r="3" fill="#00f3ff"/>
  <circle cx="16" cy="16" r="7" stroke="#00f3ff" stroke-width="1" fill="none" opacity="0.45"/>
</svg>`);

const GLOBAL_CSS = `
  *, *::before, *::after           { cursor: ${CURSOR_NORMAL} !important; }
  .drag-region, .drag-region *     { cursor: ${CURSOR_NORMAL} !important; }
  [data-hand-target],
  [data-hand-target] *             { cursor: ${CURSOR_HOVER}  !important; }

  .atlas-hover {
    outline: 1.5px solid rgba(0,243,255,0.55) !important;
    outline-offset: 3px;
    box-shadow: 0 0 0 1px rgba(0,243,255,0.15),
                0 0 18px rgba(0,243,255,0.18) !important;
    transition: outline 0.1s, box-shadow 0.1s;
  }

  .atlas-component-hover {
    opacity: 1 !important;
  }

  @keyframes atlasDwellFired {
    0%   { transform: translate(-50%,-50%) scale(1);   opacity: 1; }
    60%  { transform: translate(-50%,-50%) scale(1.4); opacity: 0.7; }
    100% { transform: translate(-50%,-50%) scale(1);   opacity: 0; }
  }
  @keyframes atlasPinchBurst {
    0%   { transform: translate(-50%,-50%) scale(0.6); opacity: 1; }
    50%  { transform: translate(-50%,-50%) scale(1.5); opacity: 0.8; }
    100% { transform: translate(-50%,-50%) scale(2.2); opacity: 0; }
  }
  @keyframes atlasSwipeFlash {
    0%   { opacity: 0; transform: translate(-50%,-50%) scale(0.85); }
    15%  { opacity: 1; transform: translate(-50%,-50%) scale(1); }
    75%  { opacity: 1; }
    100% { opacity: 0; }
  }
  @keyframes atlasPulse {
    0%,100% { opacity: 1; }
    50%     { opacity: 0.3; }
  }
`;

function arcPath(cx, cy, r, progress) {
  if (progress <= 0) return '';
  if (progress >= 1) return `M${cx},${cy-r} A${r},${r} 0 1 1 ${cx-0.001},${cy-r} Z`;
  const a = progress * 2 * Math.PI - Math.PI / 2;
  const x = cx + r * Math.cos(a);
  const y = cy + r * Math.sin(a);
  return `M${cx},${cy-r} A${r},${r} 0 ${progress > 0.5 ? 1 : 0} 1 ${x},${y}`;
}

export default memo(function HandCursor({
  cursor,
  dwellProgress,
  dwellTarget,
  swipeDir,
  isTracking,
  gesture,
  isPinching,
  isReady,
  mode,         // 'swipe' | 'mouse'
}) {
  const hoveredElRef        = useRef(null);
  const hoveredComponentRef = useRef(null);
  const targetCacheRef      = useRef({ els: [], ts: 0 });
  const componentCacheRef   = useRef({ els: [], ts: 0 });
  const [dwellFlash,  setDwellFlash]  = useState(false);
  const [pinchFlash,  setPinchFlash]  = useState(false);
  const [swipeKey,    setSwipeKey]    = useState(0);

  // Inject CSS once
  useEffect(() => {
    if (!document.getElementById('atlas-hud-cursor')) {
      const tag = document.createElement('style');
      tag.id          = 'atlas-hud-cursor';
      tag.textContent = GLOBAL_CSS;
      document.head.appendChild(tag);
    }
    return () => document.getElementById('atlas-hud-cursor')?.remove();
  }, []);

  // Hover highlight (mouse mode only)
  useEffect(() => {
    if (!isReady || mode !== 'mouse') return;
    const now = performance.now();

    // ── [data-hand-target] buttons — snap-radius proximity check ──────────────
    if (now - targetCacheRef.current.ts > 500) {
      targetCacheRef.current.els = [...document.querySelectorAll('[data-hand-target]')];
      targetCacheRef.current.ts  = now;
    }
    let nearest = null, nearestD = Infinity;
    targetCacheRef.current.els.forEach(el => {
      if (!el.isConnected) return;
      const r  = el.getBoundingClientRect();
      const cx = r.left + r.width  / 2;
      const cy = r.top  + r.height / 2;
      const d  = Math.hypot(cursor.x - cx, cursor.y - cy);
      if (d < SNAP_RADIUS && d < nearestD) { nearestD = d; nearest = el; }
    });
    if (hoveredElRef.current && hoveredElRef.current !== nearest) {
      hoveredElRef.current.classList.remove('atlas-hover');
    }
    if (nearest) nearest.classList.add('atlas-hover');
    hoveredElRef.current = nearest;

    // ── [data-hand-component] panels — point-in-rect check ────────────────────
    if (now - componentCacheRef.current.ts > 500) {
      componentCacheRef.current.els = [...document.querySelectorAll('[data-hand-component]')];
      componentCacheRef.current.ts  = now;
    }
    let hoveredComponent = null;
    for (const el of componentCacheRef.current.els) {
      if (!el.isConnected) continue;
      const r = el.getBoundingClientRect();
      if (cursor.x >= r.left && cursor.x <= r.right &&
          cursor.y >= r.top  && cursor.y <= r.bottom) {
        hoveredComponent = el;
        break;
      }
    }
    if (hoveredComponentRef.current && hoveredComponentRef.current !== hoveredComponent) {
      hoveredComponentRef.current.classList.remove('atlas-component-hover');
    }
    if (hoveredComponent) hoveredComponent.classList.add('atlas-component-hover');
    hoveredComponentRef.current = hoveredComponent;
  }, [cursor, isReady, mode]);

  useEffect(() => () => {
    hoveredElRef.current?.classList.remove('atlas-hover');
    hoveredComponentRef.current?.classList.remove('atlas-component-hover');
  }, []);

  // Dwell completion flash
  useEffect(() => {
    if (dwellProgress >= 1) {
      setDwellFlash(true);
      setTimeout(() => setDwellFlash(false), 480);
    }
  }, [dwellProgress]);

  // Pinch flash
  useEffect(() => {
    if (isPinching) {
      setPinchFlash(true);
      setTimeout(() => setPinchFlash(false), 420);
    }
  }, [isPinching]);

  // Remount swipe badge on each swipe
  useEffect(() => {
    if (swipeDir) setSwipeKey(k => k + 1);
  }, [swipeDir]);

  if (!isReady) return null;

  const isFist     = gesture === 'fist';
  const isDwelling = dwellProgress > 0 && dwellProgress < 1;
  const { x, y }  = cursor;

  // Status badge
  let statusLabel = '';
  let statusColor = '#00f3ff';
  if (!isTracking) {
    statusLabel = 'NO HAND';
    statusColor = '#ff5500';
  } else if (isFist) {
    statusLabel = 'PAUSED';
    statusColor = 'rgba(255,255,255,0.4)';
  } else if (isPinching) {
    statusLabel = 'SELECT';
    statusColor = '#ffffff';
  } else if (mode === 'swipe') {
    statusLabel = 'SWIPE';
    statusColor = '#00f3ff';
  } else {
    statusLabel = 'TRACKING';
    statusColor = '#00f3ff';
  }

  return (
    <>
      {/* ── Swipe flash ──────────────────────────────────────────────────────── */}
      {mode === 'swipe' && swipeDir && (
        <div key={swipeKey} style={{
          position: 'fixed', top: '50%', left: '50%',
          zIndex: 99997, pointerEvents: 'none',
          padding: '10px 32px',
          background: 'rgba(0,0,0,0.7)',
          border: '1px solid rgba(0,243,255,0.4)',
          borderRadius: '8px',
          animation: 'atlasSwipeFlash 0.75s ease-out forwards',
        }}>
          <span style={{
            fontFamily: 'monospace', fontSize: '14px',
            color: '#00f3ff', letterSpacing: '0.35em',
            textShadow: '0 0 16px #00f3ff',
          }}>
            NEXT →
          </span>
        </div>
      )}

      {/* ── Swipe mode: pinch burst at center ────────────────────────────────── */}
      {mode === 'swipe' && pinchFlash && (
        <div style={{
          position: 'fixed', top: '50%', left: '50%',
          width: '80px', height: '80px',
          borderRadius: '50%',
          border: '2px solid #00f3ff',
          background: 'rgba(0,243,255,0.12)',
          zIndex: 99998, pointerEvents: 'none',
          animation: 'atlasPinchBurst 0.42s ease-out forwards',
        }}/>
      )}

      {/* ── Status badge ─────────────────────────────────────────────────────── */}
      <div style={{
        position: 'fixed', top: '12px', left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 99999, pointerEvents: 'none',
        display: 'flex', alignItems: 'center', gap: '8px',
        padding: '4px 14px',
        background: 'rgba(0,0,0,0.65)',
        border: `1px solid ${statusColor}33`,
        borderRadius: '20px',
        backdropFilter: 'blur(12px)',
        transition: 'border-color 0.2s',
      }}>
        <span style={{
          fontFamily: 'monospace', fontSize: '8px',
          letterSpacing: '0.25em', color: 'rgba(0,243,255,0.4)',
          fontWeight: 'bold', marginRight: '4px',
        }}>
          {mode === 'swipe' ? 'SWIPE' : 'MOUSE'}
        </span>
        <div style={{ width: '1px', height: '10px', background: 'rgba(255,255,255,0.12)' }}/>
        <div style={{
          width: '5px', height: '5px', borderRadius: '50%',
          background: statusColor,
          boxShadow: `0 0 6px ${statusColor}`,
          animation: isTracking && !isFist ? 'atlasPulse 1.6s ease-in-out infinite' : 'none',
        }}/>
        <span style={{
          fontFamily: 'monospace', fontSize: '9px',
          letterSpacing: '0.25em', color: statusColor, fontWeight: 'bold',
        }}>
          {statusLabel}
        </span>
      </div>

      {/* ── Mouse mode: crosshair cursor ─────────────────────────────────────── */}
      {mode === 'mouse' && (
        <div style={{
          position: 'fixed', left: x, top: y,
          zIndex: 99998, pointerEvents: 'none',
          opacity: isFist ? 0.1 : 1,
          transition: 'opacity 0.2s',
          willChange: 'left, top',
        }}>
          <svg width="80" height="80" viewBox="0 0 80 80"
            style={{ transform: 'translate(-50%,-50%)', display: 'block', overflow: 'visible' }}>

            {/* Corner brackets */}
            {[
              [10,10,  1,  1],
              [70,10, -1,  1],
              [10,70,  1, -1],
              [70,70, -1, -1],
            ].map(([bx, by, sx, sy], i) => (
              <g key={i} stroke="#00f3ff" strokeWidth="1.5" strokeLinecap="round" fill="none"
                opacity={isDwelling || isPinching ? 1 : 0.5}>
                <line x1={bx} y1={by} x2={bx + sx * 8} y2={by}/>
                <line x1={bx} y1={by} x2={bx} y2={by + sy * 8}/>
              </g>
            ))}

            {/* Base ring */}
            <circle cx="40" cy="40" r={isDwelling ? 22 : 20}
              stroke="#00f3ff" strokeWidth={isDwelling ? 1 : 1.5}
              fill="none" opacity={isDwelling ? 0.25 : 0.9}
              style={{ transition: 'r 0.1s, opacity 0.1s' }}
            />

            {/* Pinch ring */}
            {isPinching && (
              <circle cx="40" cy="40" r="26"
                stroke="#ffffff" strokeWidth="1.5"
                fill="rgba(255,255,255,0.06)"
                style={{ filter: 'drop-shadow(0 0 6px #fff)' }}
              />
            )}

            {/* Dwell arc */}
            {isDwelling && (
              <path d={arcPath(40, 40, 22, dwellProgress)}
                stroke="#00f3ff" strokeWidth="2.5" fill="none" strokeLinecap="round"
                style={{ filter: 'drop-shadow(0 0 4px #00f3ff)' }}
              />
            )}

            {/* Dwell completion flash */}
            {dwellFlash && (
              <circle cx="40" cy="40" r="32"
                stroke="#ffffff" strokeWidth="2"
                fill="rgba(255,255,255,0.08)"
                style={{ animation: 'atlasDwellFired 0.45s ease-out forwards' }}
              />
            )}

            {/* Pinch burst */}
            {pinchFlash && (
              <circle cx="40" cy="40" r="20"
                stroke="#00f3ff" strokeWidth="2"
                fill="rgba(0,243,255,0.08)"
                style={{ animation: 'atlasPinchBurst 0.4s ease-out forwards' }}
              />
            )}

            {/* Scan line */}
            {!isDwelling && !isFist && (
              <line x1="24" y1="40" x2="56" y2="40"
                stroke="#00f3ff" strokeWidth="0.75" opacity="0.25"/>
            )}

            {/* Centre dot */}
            <circle cx="40" cy="40" r={isPinching ? 5 : isDwelling ? 3 : 2.5}
              fill={isPinching ? '#ffffff' : '#00f3ff'}
              style={{
                filter: `drop-shadow(0 0 ${isPinching ? 8 : 4}px ${isPinching ? '#fff' : '#00f3ff'})`,
                transition: 'r 0.1s',
              }}
            />

            {/* Dwell label */}
            {isDwelling && dwellTarget && (
              <text x="40" y="65" textAnchor="middle"
                fill="#00f3ff" fontSize="7" fontFamily="monospace" letterSpacing="2" opacity="0.7">
                {dwellTarget.getAttribute('data-hand-label') || 'HOLD'}
              </text>
            )}
          </svg>
        </div>
      )}

      {/* ── Swipe mode: bottom hint ───────────────────────────────────────────── */}
      {mode === 'swipe' && isTracking && !isFist && (
        <div style={{
          position: 'fixed', bottom: '24px', left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 99997, pointerEvents: 'none',
          display: 'flex', gap: '6px',
          padding: '6px 20px',
          background: 'rgba(0,0,0,0.6)',
          border: '1px solid rgba(0,243,255,0.2)',
          borderRadius: '8px',
        }}>
          <span style={{
            fontFamily: 'monospace', fontSize: '11px',
            color: 'rgba(0,243,255,0.5)', letterSpacing: '0.2em',
          }}>SWIPE TO NEXT</span>
          <span style={{
            fontFamily: 'monospace', fontSize: '11px',
            color: 'rgba(0,243,255,0.25)', letterSpacing: '0.2em',
          }}>PINCH TO OPEN</span>
        </div>
      )}
    </>
  );
});
