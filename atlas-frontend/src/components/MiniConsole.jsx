import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

export default function MiniConsole({ history, ws }) {
  const [input, setInput] = useState('');
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && input.trim()) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'user_input', text: input }));
      }
      setInput('');
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full h-full flex flex-col p-6 font-mono text-sm">
      <div className="bg-stark-cyan/20 border-b border-stark-cyan/30 px-4 py-3 flex justify-between items-center">
        <span className="text-xs tracking-widest text-stark-cyan font-semibold">SYS.LOG</span>
        <div className="flex gap-2">
          <div className="w-2 h-2 rounded-full bg-stark-cyan animate-pulse-fast" />
          <div className="w-2 h-2 rounded-full bg-stark-cyan/50" />
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar text-xs font-mono">
        {history.slice(-20).map((msg, idx) => (
          <div key={idx} className="leading-relaxed">
            <span className={
              msg.sender === 'ATLAS' ? 'text-stark-cyan font-bold mr-3' : 
              msg.sender === 'TUDOR' ? 'text-white/50 font-bold mr-3' : 'text-stark-orange font-bold mr-3'
            }>
              [{msg.sender}]
            </span>
            <span className="text-white/80">{msg.text}</span>
          </div>
        ))}
      </div>

      <div className="border-t border-stark-cyan/30 bg-black/40 flex items-center px-4 py-3 mt-auto">
        <span className="text-stark-cyan font-mono mr-3">{'>'}</span>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          className="w-full bg-transparent text-stark-cyan font-mono text-xs focus:outline-none placeholder-stark-cyan/30"
          placeholder="Override command..."
        />
      </div>
    </motion.div>
  );
}