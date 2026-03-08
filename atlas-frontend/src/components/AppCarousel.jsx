import { motion } from 'framer-motion';

const apps = [{id:'settings',name:'CONFIG'},{id:'weather',name:'WEATHER'},{id:'console',name:'CONSOLE'},{id:'code',name:'CODE'},{id:'models',name:'HOLO'}];

export default function AppCarousel({ activeApp, setActiveApp, isOpacityFixed, isFullscreen }) {
  const activeIndex = apps.findIndex(app => app.id === activeApp);

  return (
    <div className="absolute inset-0 flex justify-center items-center z-30 pointer-events-none">
      <div className={`relative w-full h-full flex justify-center items-center pointer-events-auto transition-opacity duration-500 ${isOpacityFixed ? 'opacity-100' : 'opacity-40 hover:opacity-100'}`}>
        {apps.map((app, index) => {
          let offset = index - activeIndex;
          if (offset < -2) offset += apps.length;
          if (offset > 2) offset -= apps.length;

          const isCenter = offset === 0;
          const angle = (Math.PI / 2) - (offset * 0.5); 
          
          // Tighten the orbit radius when the window is restored down!
          const radius = isFullscreen ? 220 : 160; 

          const x = Math.cos(angle) * radius;
          const y = Math.sin(angle) * radius * 0.2; 

          return (
            <motion.div
              key={app.id}
              className="absolute flex flex-col items-center cursor-pointer group"
              animate={{ x, y: y, scale: isCenter ? 1.2 : 0.9, opacity: isCenter ? 1 : 0.7 }}
              transition={{ type: "spring", stiffness: 200, damping: 20 }}
              onClick={() => setActiveApp(app.id)}
            >
              <div className={`w-14 h-14 rounded-full border flex items-center justify-center backdrop-blur-md transition-colors ${
                isCenter ? 'bg-stark-cyan/20 shadow-glow-cyan border-stark-cyan' : 'bg-black/80 border-stark-cyan/50 hover:border-stark-cyan/80'
              }`}>
                 <div className={`w-2.5 h-2.5 rounded-full ${isCenter ? 'bg-stark-cyan animate-pulse shadow-[0_0_8px_#00f3ff]' : 'bg-stark-cyan/40'}`} />
              </div>
              <span className={`absolute -bottom-6 font-mono text-[9px] tracking-widest transition-colors ${isCenter ? 'text-stark-cyan drop-shadow-[0_0_5px_#00f3ff]' : 'text-stark-cyan/70'}`}>
                {app.name}
              </span>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}