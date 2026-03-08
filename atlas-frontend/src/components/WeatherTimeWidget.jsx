import { useState, useEffect } from 'react';

export default function WeatherTimeWidget({ isOpacityFixed }) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className={`w-full h-full glass-panel rounded-2xl p-8 flex flex-col justify-center gap-10 border border-stark-cyan/20 bg-black/40 transition-opacity duration-500 ${isOpacityFixed ? 'opacity-100' : 'opacity-40 hover:opacity-100'}`}>
      <div className="text-stark-cyan font-mono">
        <h2 className="text-[10px] tracking-[0.3em] opacity-50 mb-4">LOCAL TIME // SIBIU</h2>
        <div className="text-6xl font-light tracking-wider drop-shadow-[0_0_8px_rgba(0,243,255,0.5)]">
          {time.toLocaleTimeString([], { hour12: false })}
        </div>
        <div className="text-sm tracking-widest opacity-70 mt-4">
          {time.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }).toUpperCase()}
        </div>
      </div>
      
      <div className="w-full h-[1px] bg-gradient-to-r from-stark-cyan/50 to-transparent" />
      
      <div className="text-stark-cyan font-mono">
        <h2 className="text-[10px] tracking-[0.3em] opacity-50 mb-4">ATMOSPHERICS</h2>
        <div className="text-5xl font-light drop-shadow-[0_0_8px_rgba(0,243,255,0.5)]">18°C</div>
        <div className="text-xs tracking-widest opacity-70 mt-4 text-stark-orange">
          WARNING: HIGH PRECIPITATION EXPECTED
        </div>
      </div>
    </div>
  );
}