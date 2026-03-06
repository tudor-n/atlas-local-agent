export default function SystemVitalsWidget() {
  return (
    <div className="w-full h-16 glass-panel rounded-xl px-8 flex items-center justify-between border border-stark-cyan/20 bg-black/40 text-stark-cyan font-mono text-[10px] tracking-widest opacity-30 hover:opacity-100 transition-opacity duration-500">
      <div className="flex items-center gap-4">
        <span className="opacity-70">CPU_CORE: <span className="font-bold text-white drop-shadow-[0_0_5px_#fff] text-xs">12%</span></span>
        <div className="w-32 h-1 bg-black/80 rounded overflow-hidden border border-stark-cyan/20">
          <div className="h-full bg-stark-cyan w-[12%] shadow-glow-cyan" />
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <span className="opacity-70">MEM_ALLOC: <span className="font-bold text-white drop-shadow-[0_0_5px_#fff] text-xs">45%</span></span>
        <div className="w-32 h-1 bg-black/80 rounded overflow-hidden border border-stark-cyan/20">
          <div className="h-full bg-stark-cyan w-[45%] shadow-glow-cyan" />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <span className="opacity-70">GPU_TEMP: <span className="font-bold text-stark-orange drop-shadow-[0_0_5px_#ff5500] text-xs">68°C</span></span>
        <div className="w-32 h-1 bg-black/80 rounded overflow-hidden border border-stark-orange/20">
          <div className="h-full bg-stark-orange w-[68%] shadow-glow-orange" />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <span className="opacity-70">UPLINK</span>
        <div className="w-2 h-2 rounded-full bg-stark-cyan shadow-glow-cyan animate-pulse" />
      </div>
    </div>
  );
}