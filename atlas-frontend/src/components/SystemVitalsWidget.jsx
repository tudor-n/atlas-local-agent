import { memo } from 'react';

export default memo(function SystemVitalsWidget({ isOpacityFixed, compact, vitals }) {
  const cpu = vitals?.cpu || 12;
  const mem = vitals?.mem || 45;
  const gpu = vitals?.gpu_temp || 68;

  return (
    <div className={`w-full ${compact ? 'h-10 px-5' : 'h-16 px-10'} glass-panel rounded-xl flex items-center justify-between border border-stark-cyan/20 bg-black/40 text-stark-cyan font-mono tracking-widest transition-opacity duration-500 ${isOpacityFixed ? 'opacity-100' : 'opacity-40 hover:opacity-100'}`}>
      
      <div className="flex items-center gap-2.5">
        <span className={`opacity-70 ${compact ? 'text-[9px]' : 'text-[10px]'}`}>
          {compact ? 'CPU:' : 'CPU_CORE:'} <span className={`font-bold text-white drop-shadow-[0_0_5px_#fff] ${compact ? 'text-[10px]' : 'text-xs'}`}>{cpu}%</span>
        </span>
        {!compact && (
          <div className="w-40 h-1.5 bg-black/80 rounded overflow-hidden border border-stark-cyan/20">
            <div className="h-full bg-stark-cyan shadow-glow-cyan" style={{ width: `${cpu}%` }} />
          </div>
        )}
      </div>
      
      <div className="flex items-center gap-2.5">
        <span className={`opacity-70 ${compact ? 'text-[9px]' : 'text-[10px]'}`}>
          {compact ? 'MEM:' : 'MEM_ALLOC:'} <span className={`font-bold text-white drop-shadow-[0_0_5px_#fff] ${compact ? 'text-[10px]' : 'text-xs'}`}>{mem}%</span>
        </span>
        {!compact && (
          <div className="w-40 h-1.5 bg-black/80 rounded overflow-hidden border border-stark-cyan/20">
            <div className="h-full bg-stark-cyan shadow-glow-cyan" style={{ width: `${mem}%` }} />
          </div>
        )}
      </div>

      <div className="flex items-center gap-2.5">
        <span className={`opacity-70 ${compact ? 'text-[9px]' : 'text-[10px]'}`}>
          {compact ? 'GPU:' : 'GPU_TEMP:'} <span className={`font-bold text-stark-orange drop-shadow-[0_0_5px_#ff5500] ${compact ? 'text-[10px]' : 'text-xs'}`}>{gpu}°C</span>
        </span>
        {!compact && (
          <div className="w-40 h-1.5 bg-black/80 rounded overflow-hidden border border-stark-orange/20">
            <div className="h-full bg-stark-orange shadow-glow-orange" style={{ width: `${Math.min(gpu, 100)}%` }} />
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <span className={`opacity-70 ${compact ? 'text-[9px]' : 'text-[10px]'}`}>UP</span>
        <div className={`${compact ? 'w-1.5 h-1.5' : 'w-2.5 h-2.5'} rounded-full bg-stark-cyan shadow-glow-cyan animate-pulse`} />
      </div>

    </div>
  );
});