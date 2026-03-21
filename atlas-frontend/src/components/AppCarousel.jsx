import { memo } from 'react';
import { motion } from 'framer-motion';

const apps = [
  { id: 'settings', name: 'CONFIG' },
  { id: 'weather', name: 'WEATHER' },
  { id: 'console', name: 'CONSOLE' },
  { id: 'code', name: 'CODE' },
  { id: 'models', name: 'HOLO' },
  { id: 'cursor', name: 'CURSOR', amber: true },
];

export default memo(function AppCarousel({ activeApp, setActiveApp, onAppOpen, isOpacityFixed, isFullscreen }) {
  const activeIndex = apps.findIndex(app => app.id === activeApp);

  const handleOrbClick = (app, isCenter) => {
    if (isCenter) {
      if (onAppOpen) onAppOpen(app.id);
    } else {
      setActiveApp(app.id);
    }
  };

  return (
    <div className="absolute inset-0 flex justify-center items-center z-30 pointer-events-none">
      <div className={`relative w-full h-full flex justify-center items-center pointer-events-auto transition-opacity duration-500 ${isOpacityFixed ? 'opacity-100' : 'opacity-40 hover:opacity-100'}`}>
        {apps.map((app, index) => {
          let offset = index - activeIndex;
          if (offset < -2) offset += apps.length;
          if (offset > 2) offset -= apps.length;

          const isCenter = offset === 0;
          const angle = (Math.PI / 2) - (offset * 0.5);
          const radius = isFullscreen ? 220 : 160;
          const x = Math.cos(angle) * radius;
          const y = Math.sin(angle) * radius * 0.2;
          const amber = !!app.amber;

          return (
            <motion.div
              key={app.id}
              className="absolute flex flex-col items-center cursor-pointer group"
              animate={{ x, y, scale: isCenter ? 1.2 : 0.9, opacity: isCenter ? 1 : 0.7 }}
              transition={{ type: 'spring', stiffness: 200, damping: 20 }}
              onClick={() => handleOrbClick(app, isCenter)}
              title={isCenter ? (amber ? 'Switch to cursor mode' : `Open ${app.name}`) : `Switch to ${app.name}`}
            >
              <div className={`w-14 h-14 rounded-full border flex items-center justify-center backdrop-blur-md transition-all duration-200 ${
                isCenter
                  ? amber
                    ? 'bg-amber-400/20 border-amber-400 shadow-[0_0_18px_rgba(251,191,36,0.5)] group-hover:bg-amber-400/35 group-hover:shadow-[0_0_25px_rgba(251,191,36,0.7)]'
                    : 'bg-stark-cyan/20 shadow-glow-cyan border-stark-cyan group-hover:bg-stark-cyan/35 group-hover:shadow-[0_0_25px_rgba(0,243,255,0.6)]'
                  : amber
                    ? 'bg-black/80 border-amber-400/40 hover:border-amber-400/70'
                    : 'bg-black/80 border-stark-cyan/50 hover:border-stark-cyan/80'
              }`}>
                {amber ? (
                  /* Cursor mode icon — small crosshair */
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                    stroke={isCenter ? '#fbbf24' : 'rgba(251,191,36,0.45)'}
                    strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                    style={isCenter ? { filter: 'drop-shadow(0 0 4px #fbbf24)' } : undefined}
                  >
                    <circle cx="12" cy="12" r="3"/>
                    <line x1="12" y1="2"  x2="12" y2="6"/>
                    <line x1="12" y1="18" x2="12" y2="22"/>
                    <line x1="2"  y1="12" x2="6"  y2="12"/>
                    <line x1="18" y1="12" x2="22" y2="12"/>
                  </svg>
                ) : (
                  <div className={`w-2.5 h-2.5 rounded-full transition-all duration-200 ${
                    isCenter
                      ? 'bg-stark-cyan animate-pulse shadow-[0_0_8px_#00f3ff] group-hover:scale-125'
                      : 'bg-stark-cyan/40'
                  }`} />
                )}
              </div>

              <span className={`absolute -bottom-6 font-mono text-[9px] tracking-widest transition-colors ${
                isCenter
                  ? amber
                    ? 'text-amber-400 drop-shadow-[0_0_5px_#fbbf24]'
                    : 'text-stark-cyan drop-shadow-[0_0_5px_#00f3ff]'
                  : amber
                    ? 'text-amber-400/60'
                    : 'text-stark-cyan/70'
              }`}>
                {app.name}
              </span>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
});
