import { motion } from 'framer-motion';

const apps = [{id:'settings',name:'CONFIG'},{id:'weather',name:'WEATHER'},{id:'console',name:'CONSOLE'},{id:'code',name:'CODE'},{id:'models',name:'HOLO'}];

export default function AppCarousel({ activeApp, setActiveApp }) {
  const activeIndex = apps.findIndex(app => app.id === activeApp);

  return (
    // FIX: Significant negative margin to wrap the ORB
    <div className="relative w-full h-24 flex justify-center items-center -mt-32 z-30 pointer-events-auto">
      <div className="relative w-[400px] h-[100px] flex justify-center items-center">
        {apps.map((app, index) => {
          let offset = index - activeIndex;
          if (offset < -2) offset += apps.length;
          if (offset > 2) offset -= apps.length;

          const isCenter = offset === 0;
          const angle = (Math.PI / 2) - (offset * 0.5); 
          const radius = 160; 

          const x = Math.cos(angle) * radius;
          const y = Math.sin(angle) * radius * 0.2; // Very flat curve

          return (
            <motion.div
              key={app.id}
              className="absolute flex flex-col items-center cursor-pointer group"
              animate={{ x, y: y + 20, scale: isCenter ? 1.2 : 0.7, opacity: isCenter ? 1 : 0.4 }}
              transition={{ type: "spring", stiffness: 200, damping: 20 }}
              onClick={() => setActiveApp(app.id)}
            >
              <div className={`w-10 h-10 rounded-full border flex items-center justify-center backdrop-blur-md ${
                isCenter ? 'bg-stark-cyan/20 shadow-glow-cyan border-stark-cyan' : 'bg-black/80 border-stark-cyan/30'
              }`}>
                 <div className={`w-1.5 h-1.5 rounded-full ${isCenter ? 'bg-stark-cyan animate-pulse' : 'bg-stark-cyan/20'}`} />
              </div>
              <span className={`absolute -bottom-4 font-mono text-[7px] tracking-widest ${isCenter ? 'text-stark-cyan' : 'text-stark-cyan/20'}`}>
                {app.name}
              </span>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}