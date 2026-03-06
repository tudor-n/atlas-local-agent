import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Orb from './components/Orb';
import MiniConsole from './components/MiniConsole';
import WeatherTimeWidget from './components/WeatherTimeWidget';
import SystemVitalsWidget from './components/SystemVitalsWidget';
import AppCarousel from './components/AppCarousel';

function App() {
  const [appState, setAppState] = useState('widget'); 
  const [selectedModule, setSelectedModule] = useState('console');
  const [atlasMessage, setAtlasMessage] = useState('');
  const [isFullscreen, setIsFullscreen] = useState(false); 
  const [history, setHistory] = useState([{ sender: 'SYSTEM', text: 'ATLAS CORE ONLINE' }]);
  const ws = useRef(null);

  useEffect(() => {
    if (window.electronAPI) {
      window.electronAPI.setMode(appState);
      window.electronAPI.onMaximizedStatus((status) => setIsFullscreen(status));
    }
  }, [appState]);

  // ==========================================
  // MODE 1: COMPACT SURGICAL WIDGET
  // ==========================================
  if (appState === 'widget') {
    return (
      <div className="w-screen h-screen flex items-center justify-center bg-transparent drag-region p-1">
        <div className="w-full h-full glass-panel rounded-xl border border-stark-cyan/40 flex flex-col items-center justify-center p-2 bg-black/80 backdrop-blur-xl relative group">
          <div className="w-24 h-24 pointer-events-none group-hover:scale-105 transition-transform">
            <Orb isSpeaking={!!atlasMessage} />
          </div>
          {/* Centered Expand Button */}
          <button onClick={() => setAppState('hub')} className="absolute inset-0 m-auto w-10 h-10 rounded-full bg-stark-cyan/20 border border-stark-cyan shadow-glow-cyan opacity-0 group-hover:opacity-100 transition-opacity no-drag flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00f3ff" strokeWidth="3"><path d="M15 3h6v6M9 21H3v-6"/></svg>
          </button>
          <div className="mt-1 font-mono text-[8px] tracking-[0.4em] text-stark-cyan font-bold opacity-80">A.T.L.A.S.</div>
        </div>
      </div>
    );
  }

  // ==========================================
  // MODE 2: HUB (Windowed & Fullscreen)
  // ==========================================
  return (
    <div className={`w-screen h-screen flex flex-col relative transition-all duration-700 ${isFullscreen ? 'bg-black/70 p-0' : 'bg-black/40 p-1'}`}>
      
      {/* NATIVE RESIZE HANDLES (Invisible edges) */}
      {!isFullscreen && (
        <>
          <div className="absolute top-0 left-0 w-full h-1 cursor-ns-resize z-[100]" />
          <div className="absolute bottom-0 left-0 w-full h-1 cursor-ns-resize z-[100]" />
          <div className="absolute top-0 left-0 h-full w-1 cursor-ew-resize z-[100]" />
          <div className="absolute top-0 right-0 h-full w-1 cursor-ew-resize z-[100]" />
        </>
      )}

      <div className={`flex flex-col flex-1 relative overflow-hidden rounded-2xl border border-stark-cyan/20 backdrop-blur-3xl ${isFullscreen ? 'rounded-none border-none' : ''}`}>
        
        {/* Top Header */}
        <div className="w-full h-10 flex items-center justify-between bg-black/60 border-b border-stark-cyan/10 px-6 drag-region">
          <span className="text-[10px] tracking-[0.4em] text-stark-cyan font-bold">A.T.L.A.S. // PRIMARY HUB</span>
          <div className="flex gap-6 no-drag items-center">
            <button onClick={() => setAppState('widget')} className="text-stark-cyan/40 hover:text-white transition-colors">WIDGET</button>
            <button onClick={() => window.electronAPI.toggleFullScreen()} className="text-stark-cyan/40 hover:text-white transition-colors">FULLSCREEN</button>
            <button onClick={() => window.electronAPI.closeApp()} className="text-stark-orange/60 hover:text-stark-orange transition-colors">SHUTDOWN</button>
          </div>
        </div>

        <div className="flex-1 w-full flex flex-row p-8 gap-8 no-drag">
          {/* LEFT: Weather/Time */}
          <div className="w-[280px] h-full opacity-60 hover:opacity-100 transition-opacity">
            <WeatherTimeWidget />
          </div>

          {/* CENTER: Main Engine */}
          <div className="flex-1 h-full flex flex-col items-center justify-center relative">
            <h1 className="glitch-text text-6xl font-bold tracking-[0.5em] mb-4" data-text="A.T.L.A.S.">A.T.L.A.S.</h1>
            <div className="w-[500px] h-[500px] relative"><Orb isSpeaking={!!atlasMessage} /></div>
            <AppCarousel activeApp={selectedModule} setActiveApp={setSelectedModule} />
          </div>

          {/* RIGHT: Console with Fixed Boundaries */}
          <div className="w-[380px] h-full">
             <div className="w-full h-full glass-panel rounded-2xl border border-stark-cyan/20 bg-black/40 opacity-60 hover:opacity-100 transition-opacity overflow-hidden">
               <MiniConsole history={history} ws={null} />
             </div>
          </div>
        </div>

        {/* BOTTOM: Vitals */}
        <div className="w-full p-6 pt-0 no-drag"><SystemVitalsWidget /></div>
      </div>
    </div>
  );
}

export default App;