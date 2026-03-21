// atlas-frontend/src/components/HandCursor.jsx
//
// Visual system for the hand tracking cursor:
//
//  • Dwell arc: SVG circle that fills clockwise as dwell progresses.
//    Turns white and pulses when fired. Aborts cleanly if cursor moves away.
//
//  • Gesture indicator: small badge below the cursor changes with gesture.
//    'point' = cyan, 'open' + swipeDir = amber arrow, 'fist' = hand is parked.
//
//  • Target hover: [data-hand-target] elements get a .atlas-hover class
//    when the cursor is within snap radius — applies a cyan outline glow.
//
//  • Mouse cursor: globally replaced with a matching HUD SVG crosshair
//    via injected CSS. Hover variant fires automatically on [data-hand-target].

import { useEffect, useRef, useState } from 'react';

const SNAP_RADIUS = 56; // must match useHandTracking

// ── Custom mouse cursor SVG ──────────────────────────────────────────────────
// Encoded as data URIs — hotspot at 16,16 (centre of 32×32)
const encodeSVG = (svg) =>
  `url("data:image/svg+xml,${encodeURIComponent(svg.trim())}") 16 16, crosshair`;

const MOUSE_NORMAL = encodeSVG(`
<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">
  <g stroke="#00f3ff" stroke-linecap="round" fill="none">
    <polyline points="4,4 9,4" stroke-width="1.5"/>
    <polyline points="4,4 4,9"  stroke-width="1.5"/>
    <polyline points="28,4 23,4" stroke-width="1.5"/>
    <polyline points="28,4 28,9" stroke-width="1.5"/>
    <polyline points="4,28 9,28" stroke-width="1.5"/>
    <polyline points="4,28 4,23" stroke-width="1.5"/>
    <polyline points="28,28 23,28" stroke-width="1.5"/>
    <polyline points="28,28 28,23" stroke-width="1.5"/>
    <line x1="13.5" y1="16" x2="15"  y2="16" stroke-width="1" opacity="0.6"/>
    <line x1="17"   y1="16" x2="18.5" y2="16" stroke-width="1" opacity="0.6"/>
    <line x1="16" y1="13.5" x2="16" y2="15"   stroke-width="1" opacity="0.6"/>
    <line x1="16" y1="17"   x2="16" y2="18.5" stroke-width="1" opacity="0.6"/>
  </g>
  <circle cx="16" cy="16" r="1.6" fill="#00f3ff"/>
</svg>`);

const MOUSE_HOVER = encodeSVG(`
<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">
  <g stroke="#00f3ff" stroke-linecap="round" fill="none">
    <polyline points="2,2 11,2"  stroke-width="2"/>
    <polyline points="2,2 2,11"  stroke-width="2"/>
    <polyline points="30,2 21,2" stroke-width="2"/>
    <polyline points="30,2 30,11" stroke-width="2"/>
    <polyline points="2,30 11,30"  stroke-width="2"/>
    <polyline points="2,30 2,21"   stroke-width="2"/>
    <polyline points="30,30 21,30" stroke-width="2"/>
    <polyline points="30,30 30,21" stroke-width="2"/>
  </g>
  <circle cx="16" cy="16" r="3"  fill="#00f3ff"/>
  <circle cx="16" cy="16" r="7"  stroke="#00f3ff" stroke-width="1" fill="none" opacity="0.45"/>
</svg>`);

const GLOBAL_CSS = `
  *, *::before, *::after {
    cursor: ${MOUSE_NORMAL} !important;
  }
  [data-hand-target], [data-hand-target] * {
    cursor: ${MOUSE_HOVER} !important;
  }
  .atlas-hover {
    outline: 1.5px solid rgba(0, 243, 255, 0.55) !important;
    outline-offset: 3px;
    box-shadow: 0 0 0 1px rgba(0,243,255,0.15), 0 0 18px rgba(0,243,255,0.18) !important;
    transition: outline 0.1s, box-shadow 0.1s;
  }
  @keyframes atlasDwellFired {
    0%   { transform: translate(-50%,-50%) scale(1);   opacity: 1;   }
    60%  { transform: translate(-50%,-50%) scale(1.35); opacity: 0.8; }
    100% { transform: translate(-50%,-50%) scale(1);   opacity: 0;   }
  }
  @keyframes atlasStatusPulse {
    0%,100% { opacity:1; }
    50%      { opacity:0.3; }
  }
  @keyframes atlasSwipeFade {
    0%   { opacity:0; transform:translate(-50%,-50%) scale(0.9); }
    15%  { opacity:1; transform:translate(-50%,-50%) scale(1);   }
    75%  { opacity:1; }
    100% { opacity:0; }
  }
`;

// ── SVG arc helper — returns a <path d> for a clockwise arc ──────────────────
function arcPath(cx, cy, r, progress) {
  if (progress <= 0)   return '';
  if (progress >= 1)   return `M ${cx} ${cy - r} A ${r} ${r} 0 1 1 ${cx - 0.001} ${cy - r} Z`;
  const angle = progress * 2 * Math.PI - Math.PI / 2;
  const x = cx + r * Math.cos(angle);
  const y = cy + r * Math.sin(angle);
  const large = progress > 0.5 ? 1 : 0;
  return `M ${cx} ${cy - r} A ${r} ${r} 0 ${large} 1 ${x} ${y}`;
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function HandCursor({
  cursor,
  dwellProgress,
  dwellTarget,
  swipeDir,
  isTracking,
  gesture,
  isReady,
}) {
  const hoveredElRef = useRef(null);
  const [firedFlash, setFiredFlash] = useState(false);

  // ── Inject global CSS once ────────────────────────────────────────────────
  useEffect(() => {
    const tag = document.createElement('style');
    tag.id    = 'atlas-hud-cursor';
    tag.textContent = GLOBAL_CSS;
    if (!document.getElementById('atlas-hud-cursor')) document.head.appendChild(tag);
    return () => tag.remove();
  }, []);

  // ── Hover class management ────────────────────────────────────────────────
  useEffect(() => {
    if (!isReady) return;
    // Find nearest target at current cursor pos
    const els     = document.querySelectorAll('[data-hand-target]');
    let nearest   = null, nearestD = Infinity;
    els.forEach(el => {
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
  }, [cursor, isReady]);

  // Cleanup on unmount
  useEffect(() => () => hoveredElRef.current?.classList.remove('atlas-hover'), []);

  // ── Dwell completion flash ────────────────────────────────────────────────
  useEffect(() => {
    if (dwellProgress >= 1) {
      setFiredFlash(true);
      setTimeout(() => setFiredFlash(false), 500);
    }
  }, [dwellProgress]);

  if (!isReady) return null;

  const { x, y } = cursor;
  const isDwelling = dwellProgress > 0 && dwellProgress < 1;
  const isFired    = dwellProgress >= 1;
  const isFist     = gesture === 'fist';
  const isSwiping  = gesture === 'open' && swipeDir;

  // Ring appearance
  const ringR      = isDwelling ? 22 : isFired ? 28 : 20;
  const ringColor  = isFired ? '#ffffff' : '#00f3ff';
  const ringOpacity= isFist   ? 0.15     : 1;

  // Status badge
  let statusText  = isTracking ? (isFist ? 'PAUSED' : 'TRACKING') : 'NO HAND';
  let statusColor = isTracking ? '#00f3ff' : '#ff5500';
  if (isSwiping)   { statusText = swipeDir === 'right' ? 'PREV ←' : '→ NEXT'; statusColor = '#fbbf24'; }
  if (isFired)     { statusText = 'SELECT'; statusColor = '#ffffff'; }
  if (isFist)      { statusColor = '#ffffff44'; }

  return (
    <>
      {/* ── Swipe overlay ─────────────────────────────────────────────────── */}
      {isSwiping && (
        <div key={swipeDir} style={{
          position:      'fixed',
          top:           '50%',
          left:          '50%',
          zIndex:        99997,
          pointerEvents: 'none',
          transform:     'translate(-50%,-50%)',
          padding:       '10px 28px',
          background:    'rgba(0,0,0,0.65)',
          border:        '1px solid rgba(251,191,36,0.5)',
          borderRadius:  '8px',
          animation:     'atlasSwipeFade 0.7s ease-out forwards',
        }}>
          <span style={{
            fontFamily: 'monospace', fontSize: '14px',
            color: '#fbbf24', letterSpacing: '0.3em',
            textShadow: '0 0 14px #fbbf24',
          }}>
            {swipeDir === 'right' ? '← PREV' : 'NEXT →'}
          </span>
        </div>
      )}

      {/* ── Status badge ─────────────────────────────────────────────────── */}
      <div style={{
        position:      'fixed',
        top:           '12px',
        left:          '50%',
        transform:     'translateX(-50%)',
        zIndex:        99999,
        pointerEvents: 'none',
        display:       'flex',
        alignItems:    'center',
        gap:           '7px',
        padding:       '3px 12px',
        background:    'rgba(0,0,0,0.6)',
        border:        `1px solid ${statusColor}33`,
        borderRadius:  '20px',
        backdropFilter:'blur(10px)',
        transition:    'border-color 0.2s',
      }}>
        <div style={{
          width:'5px', height:'5px', borderRadius:'50%',
          background: statusColor,
          boxShadow:  `0 0 6px ${statusColor}`,
          animation:  isTracking && !isFist && !isFired
            ? 'atlasStatusPulse 1.6s ease-in-out infinite' : 'none',
        }}/>
        <span style={{
          fontFamily: 'monospace', fontSize: '9px',
          letterSpacing: '0.25em', color: statusColor, fontWeight: 'bold',
        }}>
          {statusText}
        </span>
      </div>

      {/* ── Cursor ────────────────────────────────────────────────────────── */}
      <div style={{
        position:      'fixed',
        left:          x,
        top:           y,
        zIndex:        99998,
        pointerEvents: 'none',
        opacity:       isFist ? 0.12 : 1,
        transition:    'opacity 0.2s',
        willChange:    'left, top',
      }}>
        <svg
          width="80"
          height="80"
          viewBox="0 0 80 80"
          style={{ transform: 'translate(-50%, -50%)', display: 'block', overflow: 'visible' }}
        >
          {/* ── Corner brackets ─────────────────────────────────────────── */}
          {[
            [10,10, 'top-left'],
            [70,10, 'top-right'],
            [10,70, 'bottom-left'],
            [70,70, 'bottom-right'],
          ].map(([bx, by, dir]) => {
            const sx = dir.includes('left')  ?  1 : -1;
            const sy = dir.includes('top')   ?  1 : -1;
            return (
              <g key={dir} stroke={ringColor} strokeWidth="1.5" strokeLinecap="round" fill="none"
                opacity={isDwelling || isFired ? 1 : 0.5}
                style={{ transition: 'opacity 0.15s' }}>
                <line x1={bx} y1={by} x2={bx + sx * 8} y2={by}/>
                <line x1={bx} y1={by} x2={bx} y2={by + sy * 8}/>
              </g>
            );
          })}

          {/* ── Static ring ─────────────────────────────────────────────── */}
          <circle
            cx="40" cy="40" r={ringR}
            stroke={ringColor}
            strokeWidth={isDwelling ? 1 : 1.5}
            fill="none"
            opacity={isDwelling ? 0.25 : ringOpacity}
            style={{ transition: 'r 0.1s, opacity 0.1s' }}
          />

          {/* ── Dwell arc overlay ────────────────────────────────────────── */}
          {isDwelling && (
            <path
              d={arcPath(40, 40, ringR, dwellProgress)}
              stroke="#00f3ff"
              strokeWidth="2.5"
              fill="none"
              strokeLinecap="round"
              style={{ filter: 'drop-shadow(0 0 4px #00f3ff)' }}
            />
          )}

          {/* ── Dwell completion flash ───────────────────────────────────── */}
          {firedFlash && (
            <circle
              cx="40" cy="40" r="32"
              stroke="#ffffff"
              strokeWidth="2"
              fill="rgba(255,255,255,0.08)"
              style={{ animation: 'atlasDwellFired 0.45s ease-out forwards' }}
            />
          )}

          {/* ── Scan line ───────────────────────────────────────────────── */}
          {!isDwelling && !isFist && (
            <line
              x1={40 - ringR + 4} y1="40"
              x2={40 + ringR - 4} y2="40"
              stroke={ringColor} strokeWidth="0.75" opacity="0.25"
            />
          )}

          {/* ── Centre dot ──────────────────────────────────────────────── */}
          <circle
            cx="40" cy="40"
            r={isFired ? 5 : isDwelling ? 3 : 2.5}
            fill={isFired ? '#ffffff' : '#00f3ff'}
            style={{
              filter: `drop-shadow(0 0 ${isFired ? 8 : 4}px ${isFired ? '#fff' : '#00f3ff'})`,
              transition: 'r 0.1s',
            }}
          />

          {/* ── Dwell progress label ─────────────────────────────────────── */}
          {isDwelling && dwellTarget && (
            <text
              x="40" y="64"
              textAnchor="middle"
              fill="#00f3ff"
              fontSize="7"
              fontFamily="monospace"
              letterSpacing="2"
              opacity="0.7"
            >
              {dwellTarget.getAttribute('data-hand-label') || 'HOLD'}
            </text>
          )}
        </svg>
      </div>
    </>
  );
}