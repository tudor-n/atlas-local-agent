import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

export default function ConsoleApp({ ws, history }) {
  const [input, setInput] = useState('');
  const scrollRef = useRef(null);

  // Auto-scroll
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
    <div className="w-full h-full flex flex-col p-6 font-mono text-sm">
      <div className="text-stark-cyan text-xl mb-4 tracking-widest font-light border-b border-stark-cyan/20 pb-4">
        FULL SYSTEM CONSOLE
      </div>
      
      {/* Output History Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-6 mb-4 pr-4 custom-scrollbar">
        {history.map((msg, idx) => (
          <motion.div 
            key={idx}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex flex-col ${msg.sender === 'TUDOR' ? 'items-end' : 'items-start'}`}
          >
            <span className={`text-xs mb-1 tracking-widest ${
              msg.sender === 'ATLAS' ? 'text-stark-cyan' : 
              msg.sender === 'TUDOR' ? 'text-white/50' : 'text-stark-orange'
            }`}>
              [{msg.sender}]
            </span>
            <div className={`px-5 py-3 rounded-lg max-w-[80%] text-base ${
              msg.sender === 'TUDOR' 
                ? 'bg-white/10 border border-white/20 text-white' 
                : 'bg-stark-cyan/10 border border-stark-cyan/40 text-stark-cyan shadow-glow-cyan'
            }`}>
              {msg.text}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Input Area */}
      <div className="relative flex items-center mt-auto">
        <span className="absolute left-4 text-stark-cyan font-bold text-lg animate-pulse">{'>'}</span>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus
          className="w-full bg-black/60 border-2 border-stark-cyan/40 text-stark-cyan rounded-xl py-4 pl-12 pr-4 focus:outline-none focus:border-stark-cyan focus:shadow-glow-cyan transition-all placeholder-stark-cyan/30 text-lg"
          placeholder="Execute protocol..."
        />
      </div>
    </div>
  );
}