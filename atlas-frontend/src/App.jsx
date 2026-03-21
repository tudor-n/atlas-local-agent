// atlas-frontend/src/App.jsx
//
// Merged: ConsoleFullView + dual-hand gesture tracking (v3 — usable edition)
//
// Changes from v2:
//   • swipeVelocity replaced by swipeDir ('left'|'right'|null) — hook handles debounce
//   • dwellProgress + dwellTarget passed to HandCursor for arc rendering
//   • Swipe handler is edge-triggered on swipeDir changing (not continuous velocity)
//   • Cooldown still kept as safety net against MediaPipe latency spikes
//
// Search "HAND TRACKING" to find every related change.

import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Orb from './components/Orb';
import MiniConsole from './components/MiniConsole';
import WeatherTimeWidget from './components/WeatherTimeWidget';
import SystemVitalsWidget from './components/SystemVitalsWidget';
import AppCarousel from './components/AppCarousel';
import ConsoleFullView from './components/ConsoleFullView';

// HAND TRACKING
import { useHandTracking } from './hooks/useHandTracking';
import HandCursor from './components/HandCursor';

const APPS = ['settings', 'weather', 'console', 'code', 'models'];

function App() {
  const [appState,       setAppState]       = useState('widget');
  const [selectedModule, setSelectedModule] = useState('console');
  const [openedApp,      setOpenedApp]      = useState(null);
  const [atlasMessage,   setAtlasMessage]   = useState('');
  const [isFullscreen,   setIsFullscreen]   = useState(false);
  const [isOpacityFixed, setIsOpacityFixed] = useState(false);
  const [history,        setHistory]        = useState([{ sender: 'SYSTEM', text: 'ATLAS CORE ONLINE' }]);
  const [vitals,         setVitals]         = useState({ cpu: 12, mem: 45, gpu_temp: 68 });

  const [ws, setWs] = useState(null);
  const speakingTimeoutRef = useRef(null);

  // HAND TRACKING: cooldown so rapid swipe doesn't multi-fire
  const swipeCooldown  = useRef(false);
  // HAND TRACKING: track previous swipeDir so we only fire on the rising edge
  const prevSwipeDir   = useRef(null);

  // HAND TRACKING: hook (webcam only active in fullscreen hub)
  const {
    cursor,
    dwellProgress,
    dwellTarget,
    swipeDir,
    isTracking,
    gesture,
    isReady,
  } = useHandTracking({ enabled: isFullscreen && !openedApp });

  // HAND TRACKING: carousel rotation on rising edge of swipeDir
  useEffect(() => {
    if (!isFullscreen || openedApp) return;
    if (!swipeDir || swipeDir === prevSwipeDir.current) return;
    if (swipeCooldown.current) return;

    prevSwipeDir.current = swipeDir;
    swipeCooldown.current = true;

    setSelectedModule(prev => {
      const i = APPS.indexOf(prev);
      return swipeDir === 'right'
        ? APPS[(i - 1 + APPS.length) % APPS.length]
        : APPS[(i + 1) % APPS.length];
    });

    setTimeout(() => {
      swipeCooldown.current = false;
      prevSwipeDir.current  = null;
    }, 700);
  }, [swipeDir, isFullscreen, openedApp]);

  useEffect(() => {
    if (window.electronAPI) {
      window.electronAPI.setMode(appState);
      window.electronAPI.onMaximizedStatus((status) => setIsFullscreen(status));
    }
  }, [appState]);

  useEffect(() => {
    const socket = new WebSocket('ws://localhost:8000/ws');
    setWs(socket);
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'user_speak') {
        setHistory(prev => [...prev, { sender: 'TUDOR', text: data.payload.text }]);
      } else if (data.type === 'atlas_speak') {
        setHistory(prev => [...prev, { sender: 'ATLAS', text: data.payload.text }]);
        setAtlasMessage(data.payload.text);
        if (speakingTimeoutRef.current) clearTimeout(speakingTimeoutRef.current);
        speakingTimeoutRef.current = setTimeout(
          () => setAtlasMessage(''),
          3000 + data.payload.text.length * 50
        );
      } else if (data.type === 'system_vitals') {
        setVitals({
          cpu:      Math.round(data.payload.cpu),
          mem:      Math.round(data.payload.mem),
          gpu_temp: Math.round(data.payload.gpu_temp),
        });
      } else if (data.type === 'switch_app') {
        setSelectedModule(data.payload.app);
      }
    };
    return () => socket.close();
  }, []);

  const componentOpacityClass = `transition-opacity duration-500 ${isOpacityFixed ? 'opacity-100' : 'opacity-40 hover:opacity-100'}`;
  const minimizedOpacityClass = `transition-opacity duration-500 ${isOpacityFixed ? 'opacity-100' : 'opacity-30 group-hover:opacity-100'}`;

  // ─── Widget mode ─────────────────────────────────────────────────────────────
  if (appState === 'widget') {
    return (
      <div className="w-screen h-screen flex items-center justify-center bg-transparent drag-region p-1">
        <div className={`w-full h-full rounded-2xl border border-stark-cyan/40 flex flex-col items-center justify-between p-3 relative group transition-all duration-700 ${
          isOpacityFixed
            ? 'bg-black/85 backdrop-blur-3xl'
            : 'bg-black/10 backdrop-blur-sm hover:bg-black/90 hover:backdrop-blur-3xl'
        }`}>
          <div className={`w-full flex justify-start items-center px-1 pointer-events-auto z-10 ${minimizedOpacityClass}`}>
            <span className="text-[7px] tracking-[0.3em] text-stark-cyan font-bold drag-region">A.T.L.A.S. // WIDGET HUB</span>
          </div>
          <div className="relative flex-1 w-full flex items-center justify-center pointer-events-none group-hover:scale-105 transition-transform duration-500 my-1">
            <div className="w-20 h-20 relative flex items-center justify-center pointer-events-auto">
              <Orb isSpeaking={!!atlasMessage} />
            </div>
            <button
              onClick={() => { setAppState('hub'); if (window.electronAPI) window.electronAPI.toggleFullScreen(); }}
              className="absolute inset-0 m-auto w-10 h-10 rounded-full bg-black/60 border border-stark-cyan shadow-glow-cyan opacity-0 group-hover:opacity-100 transition-opacity duration-300 no-drag flex items-center justify-center z-50 cursor-pointer pointer-events-auto"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00f3ff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>
              </svg>
            </button>
          </div>
          <div className={`font-mono text-[9px] tracking-[0.4em] text-stark-cyan font-bold mb-1.5 text-center w-full ${minimizedOpacityClass}`}>
            A.T.L.A.S.
          </div>
          <div className={`w-full flex justify-center gap-2 mb-1 bg-black/40 py-1.5 rounded-full border border-white/5 ${minimizedOpacityClass}`}>
            <div className="w-1.5 h-1.5 rounded-full bg-[#fbbf24] shadow-[0_0_5px_#fbbf24]" />
            <div className="w-1.5 h-1.5 rounded-full bg-[#f97316] shadow-[0_0_5px_#f97316]" />
            <div className="w-1.5 h-1.5 rounded-full bg-[#1e3a8a] shadow-[0_0_5px_#1e3a8a]" />
            <div className="w-1.5 h-1.5 rounded-full bg-stark-cyan shadow-[0_0_5px_#00f3ff]" />
          </div>
        </div>
      </div>
    );
  }

  // ─── Hub / app shell ──────────────────────────────────────────────────────────
  return (
    <>
      {/* HAND TRACKING: cursor overlay — fullscreen hub only */}
      {isFullscreen && !openedApp && (
        <HandCursor
          cursor={cursor}
          dwellProgress={dwellProgress}
          dwellTarget={dwellTarget}
          swipeDir={swipeDir}
          isTracking={isTracking}
          gesture={gesture}
          isReady={isReady}
        />
      )}

      <div className={`w-screen h-screen flex flex-col relative transition-all duration-700 ${
        isFullscreen
          ? 'bg-black/85 p-0 backdrop-blur-3xl'
          : `group ${isOpacityFixed ? 'bg-black/70 p-1 backdrop-blur-3xl' : 'bg-black/10 p-1 backdrop-blur-sm hover:bg-black/70 hover:backdrop-blur-3xl'}`
      }`}>
        <div className={`flex flex-col flex-1 relative overflow-hidden transition-all duration-700 ${
          isFullscreen ? 'rounded-none border-none' : 'rounded-2xl border border-stark-cyan/20'
        }`}>

          {/* ── Title bar ── */}
          <div className={`w-full h-12 flex items-center justify-between border-b border-stark-cyan/10 px-6 drag-region transition-colors duration-500 shrink-0 ${
            isFullscreen ? 'bg-black/80' : (isOpacityFixed ? 'bg-black/40' : 'bg-transparent group-hover:bg-black/40')
          }`}>
            <span className="text-[10px] tracking-[0.4em] text-stark-cyan font-bold">
              A.T.L.A.S. // {openedApp ? openedApp.toUpperCase() : (isFullscreen ? 'PRIMARY HUB' : 'MINIMIZED HUB')}
            </span>
            <div className="flex gap-5 no-drag items-center">

              <button data-hand-target data-hand-label="OPACITY"
                onClick={() => setIsOpacityFixed(!isOpacityFixed)}
                className={`transition-colors ${isOpacityFixed ? 'text-stark-cyan' : 'text-stark-cyan/40 hover:text-white'}`}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  {isOpacityFixed ? (<><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></>) : (
                    <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61M2 2l20 20"/>
                  )}
                </svg>
              </button>

              <div className="w-px h-4 bg-stark-cyan/20 mx-1" />

              <button data-hand-target data-hand-label="MINIMIZE"
                onClick={() => { setAppState('widget'); setOpenedApp(null); }}
                className={`transition-colors ${isOpacityFixed ? 'text-stark-cyan hover:text-white' : 'text-stark-cyan/40 hover:text-white'}`}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><path d="M8 12h8"/>
                </svg>
              </button>

              <button data-hand-target data-hand-label={isFullscreen ? 'RESTORE' : 'FULLSCREEN'}
                onClick={() => window.electronAPI?.toggleFullScreen()}
                className={`transition-colors ${isOpacityFixed ? 'text-stark-cyan hover:text-white' : 'text-stark-cyan/40 hover:text-white'}`}
              >
                {isFullscreen ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"/>
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
                  </svg>
                )}
              </button>

              <button data-hand-target data-hand-label="POWER OFF"
                onClick={() => window.electronAPI?.closeApp()}
                className={`transition-colors ${isOpacityFixed ? 'text-stark-orange hover:text-white' : 'text-stark-orange/60 hover:text-stark-orange'}`}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/>
                </svg>
              </button>
            </div>
          </div>

          {/* ── Body ── */}
          <AnimatePresence mode="wait">
            {openedApp === 'console' ? (
              <motion.div key="console-full" initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }} transition={{ duration:0.2 }} className="flex-1 min-h-0 overflow-hidden">
                <ConsoleFullView history={history} ws={ws} onBack={() => setOpenedApp(null)} isOpacityFixed={isOpacityFixed} />
              </motion.div>
            ) : (
              <motion.div key="hub" initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }} transition={{ duration:0.2 }} className="flex-1 min-h-0 flex flex-col overflow-hidden">

                {isFullscreen ? (
                  <div className="flex-1 w-full flex flex-row p-8 gap-8 no-drag relative overflow-hidden">
                    <div className={`w-[360px] h-full z-10 shrink-0 ${componentOpacityClass}`}>
                      <WeatherTimeWidget isOpacityFixed={isOpacityFixed} />
                    </div>
                    <div className="flex-1 m-auto flex flex-col items-center justify-center pointer-events-none min-h-0 z-20">
                      <div className={`flex flex-col items-center mb-6 pointer-events-auto ${componentOpacityClass}`}>
                        <h1 className="glitch-text text-7xl font-bold tracking-[0.5em] mb-2" data-text="A.T.L.A.S.">A.T.L.A.S.</h1>
                        <h2 className="glitch-text text-xs tracking-[0.6em] text-stark-cyan/80 font-bold" data-text="BLACKWELL JV2.0 ARCH">BLACKWELL JV2.0 ARCH</h2>
                      </div>
                      <div className="relative flex items-center justify-center pointer-events-auto shrink-0 w-[450px] h-[450px]">
                        <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-auto">
                          <Orb isSpeaking={!!atlasMessage} />
                        </div>
                        <div className="absolute inset-0 z-20 flex items-center justify-center pointer-events-none">
                          <AppCarousel activeApp={selectedModule} setActiveApp={setSelectedModule} onAppOpen={(id) => setOpenedApp(id)} isOpacityFixed={isOpacityFixed} isFullscreen={isFullscreen} />
                        </div>
                      </div>
                      <div className={`mt-6 flex gap-5 px-8 py-3 bg-black/60 border border-stark-cyan/20 rounded-full backdrop-blur-md pointer-events-auto shrink-0 ${componentOpacityClass}`}>
                        <div className="flex items-center gap-2.5"><div className="w-2 h-2 rounded-full bg-[#fbbf24] shadow-[0_0_5px_#fbbf24] animate-pulse"/><span className="text-[10px] text-[#fbbf24] tracking-[0.2em] font-mono">ACTIVE: <span className="text-white font-bold drop-shadow-[0_0_2px_#fff]">2</span></span></div>
                        <div className="w-px h-3.5 bg-white/20 self-center"/>
                        <div className="flex items-center gap-2.5"><div className="w-2 h-2 rounded-full bg-[#f97316] shadow-[0_0_5px_#f97316]"/><span className="text-[10px] text-[#f97316] tracking-[0.2em] font-mono">QUEUED: <span className="text-white font-bold drop-shadow-[0_0_2px_#fff]">5</span></span></div>
                        <div className="w-px h-3.5 bg-white/20 self-center"/>
                        <div className="flex items-center gap-2.5"><div className="w-2 h-2 rounded-full bg-[#1e3a8a] shadow-[0_0_5px_#1e3a8a]"/><span className="text-[10px] text-[#426bdc] tracking-[0.2em] font-mono">DONE: <span className="text-white font-bold drop-shadow-[0_0_2px_#fff]">12</span></span></div>
                        <div className="w-px h-3.5 bg-white/20 self-center"/>
                        <div className="flex items-center gap-2.5"><div className="w-2 h-2 rounded-full bg-stark-cyan shadow-[0_0_5px_#00f3ff]"/><span className="text-[10px] text-stark-cyan tracking-[0.2em] font-mono">AGENTS: <span className="text-white font-bold drop-shadow-[0_0_2px_#fff]">4</span></span></div>
                      </div>
                    </div>
                    <div className={`ml-auto w-[360px] h-full z-10 shrink-0 ${componentOpacityClass}`}>
                      <div className="w-full h-full glass-panel rounded-2xl border border-stark-cyan/20 bg-black/40 overflow-hidden">
                        <MiniConsole history={history} ws={ws} />
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 w-full flex flex-col p-4 gap-3 no-drag relative overflow-hidden">
                    <div className="flex items-center justify-center gap-4 w-full shrink-0 pointer-events-auto">
                      <div className="w-16 h-16 shrink-0 relative flex items-center justify-center"><Orb isSpeaking={!!atlasMessage} /></div>
                      <div className={`flex flex-col justify-center ${minimizedOpacityClass}`}>
                        <h1 className="glitch-text text-3xl font-bold tracking-[0.4em] mb-1" data-text="A.T.L.A.S.">A.T.L.A.S.</h1>
                        <h2 className="glitch-text text-[7px] tracking-[0.4em] text-stark-cyan/80 font-bold" data-text="BLACKWELL JV2.0 ARCH">BLACKWELL JV2.0 ARCH</h2>
                      </div>
                    </div>
                    <div className={`flex-1 w-full min-h-0 glass-panel rounded-xl border border-stark-cyan/20 bg-black/40 overflow-hidden ${minimizedOpacityClass}`}>
                      <MiniConsole history={history} ws={ws} />
                    </div>
                    <div className={`w-full flex justify-between px-4 py-2.5 bg-black/60 border border-stark-cyan/20 rounded-xl backdrop-blur-md pointer-events-auto shrink-0 ${minimizedOpacityClass}`}>
                      <div className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-[#fbbf24] shadow-[0_0_5px_#fbbf24] animate-pulse"/><span className="text-[8px] text-[#fbbf24] tracking-[0.1em] font-mono">ACTIVE:<span className="text-white font-bold drop-shadow-[0_0_2px_#fff] ml-1">2</span></span></div>
                      <div className="w-px h-3 bg-white/20 self-center"/>
                      <div className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-[#f97316] shadow-[0_0_5px_#f97316]"/><span className="text-[8px] text-[#f97316] tracking-[0.1em] font-mono">QUEUED:<span className="text-white font-bold drop-shadow-[0_0_2px_#fff] ml-1">5</span></span></div>
                      <div className="w-px h-3 bg-white/20 self-center"/>
                      <div className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-[#1e3a8a] shadow-[0_0_5px_#1e3a8a]"/><span className="text-[8px] text-[#426bdc] tracking-[0.1em] font-mono">DONE:<span className="text-white font-bold drop-shadow-[0_0_2px_#fff] ml-1">12</span></span></div>
                      <div className="w-px h-3 bg-white/20 self-center"/>
                      <div className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-stark-cyan shadow-[0_0_5px_#00f3ff]"/><span className="text-[8px] text-stark-cyan tracking-[0.1em] font-mono">AGENTS:<span className="text-white font-bold drop-shadow-[0_0_2px_#fff] ml-1">4</span></span></div>
                    </div>
                  </div>
                )}

                <div className={`w-full p-4 pt-0 no-drag shrink-0 ${isFullscreen ? 'p-6' : ''}`}>
                  <div className={componentOpacityClass}>
                    <SystemVitalsWidget isOpacityFixed={isOpacityFixed} compact={!isFullscreen} vitals={vitals} />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </>
  );
}

export default App;
