import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

export default function MiniConsole({ history, ws }) {
  const [input, setInput] = useState('');
  const scrollRef = useRef(null);

  // Auto-scroll to the bottom of the mini log
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && input.trim()) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        // We only send it to the backend. The backend will echo it back to update the history!
        ws.send(JSON.stringify({ action: 'user_input', text: input }));
      }
      setInput('');
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full h-full flex flex-col p-6 font-mono text-sm opacity-40 hover:opacity-100 transition-opacity duration-500">
      {/* Header */}
      <div className="bg-stark-cyan/20 border-b border-stark-cyan/30 px-4 py-2 flex justify-between items-center">
        <span className="text-xs tracking-widest text-stark-cyan font-semibold">SYS.LOG</span>
        <div className="flex gap-1">
          <div className="w-2 h-2 rounded-full bg-stark-cyan animate-pulse-fast" />
          <div className="w-2 h-2 rounded-full bg-stark-cyan/50" />
        </div>
      </div>

      {/* Log History */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar text-xs font-mono">
        {history.slice(-15).map((msg, idx) => ( // Only show the last 15 messages in the mini view
          <div key={idx} className="leading-relaxed">
            <span className={
              msg.sender === 'ATLAS' ? 'text-stark-cyan font-bold mr-2' : 
              msg.sender === 'TUDOR' ? 'text-white/50 font-bold mr-2' : 'text-stark-orange font-bold mr-2'
            }>
              [{msg.sender}]
            </span>
            <span className="text-white/80">{msg.text}</span>
          </div>
        ))}
      </div>

      {/* Quick Input */}
      <div className="border-t border-stark-cyan/30 bg-black/40 flex items-center px-3 py-2">
        <span className="text-stark-cyan font-mono mr-2">{'>'}</span>
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