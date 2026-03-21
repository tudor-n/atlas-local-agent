import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

const MOOD_COLOR = {
  positive:   '#34d399',
  frustrated: '#f97316',
  panicked:   '#ef4444',
};

export default function CognitiveBadge({ data }) {
  const [faded, setFaded] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    setFaded(false);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setFaded(true), 5000);
    return () => clearTimeout(timerRef.current);
  }, [data]);

  if (!data) return null;

  const { intent, salience, mood, urgency } = data;
  const salinceWidth = Math.min(100, (salience / 10) * 100);
  const salienceColor = salience >= 8 ? '#ff5500' : '#00f3ff';
  const moodColor = MOOD_COLOR[mood] ?? 'rgba(255,255,255,0.5)';
  const urgencyHigh = urgency === 'high';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: faded ? 0.3 : 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex items-center gap-0 bg-black/50 border border-stark-cyan/15 rounded-full px-5 py-1.5 backdrop-blur-md"
      style={{ transition: 'opacity 0.3s' }}
    >
      {/* INTENT */}
      <div className="flex flex-col items-center px-3">
        <span className="text-[8px] text-stark-cyan/40 tracking-widest">INTENT</span>
        <span className="text-[10px] font-bold text-stark-cyan font-mono">{intent ?? '—'}</span>
      </div>

      <div className="w-px self-stretch" style={{ background: 'rgba(255,255,255,0.1)' }} />

      {/* SALIENCE */}
      <div className="flex flex-col items-center px-3 gap-1">
        <span className="text-[8px] text-stark-cyan/40 tracking-widest">SAL</span>
        <div className="w-20 h-1 bg-black/60 rounded overflow-hidden">
          <div
            className="h-full rounded transition-all duration-500"
            style={{ width: `${salinceWidth}%`, background: salienceColor }}
          />
        </div>
      </div>

      <div className="w-px self-stretch" style={{ background: 'rgba(255,255,255,0.1)' }} />

      {/* MOOD */}
      <div className="flex flex-col items-center px-3">
        <span className="text-[8px] text-stark-cyan/40 tracking-widest">MOOD</span>
        <span className="text-[10px] font-bold font-mono capitalize" style={{ color: moodColor }}>
          {mood ?? '—'}
        </span>
      </div>

      <div className="w-px self-stretch" style={{ background: 'rgba(255,255,255,0.1)' }} />

      {/* URGENCY */}
      <div className="flex flex-col items-center px-3 gap-1">
        <span className="text-[8px] text-stark-cyan/40 tracking-widest">URG</span>
        <div
          className={`w-2.5 h-2.5 rounded-full ${urgencyHigh ? 'bg-stark-orange animate-pulse' : 'bg-stark-cyan/30'}`}
        />
      </div>
    </motion.div>
  );
}
