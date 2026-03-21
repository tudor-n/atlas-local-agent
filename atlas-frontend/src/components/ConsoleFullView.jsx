import { useState, useEffect, useRef, useMemo, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default memo(function ConsoleFullView({ history, ws, onBack, isOpacityFixed }) {
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const sessionId = useMemo(() => Math.floor(Math.random() * 9000 + 1000), []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history]);

  // Detect when ATLAS is "typing" (last message from ATLAS was very recent)
  useEffect(() => {
    const lastMsg = history[history.length - 1];
    if (lastMsg?.sender === 'TUDOR') {
      setIsTyping(true);
      const t = setTimeout(() => setIsTyping(false), 1500);
      return () => clearTimeout(t);
    }
  }, [history]);

  const handleSend = () => {
    if (!input.trim()) return;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'user_input', text: input }));
    }
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatTime = (idx) => {
    const now = new Date();
    const offsetMs = (history.length - 1 - idx) * 12000;
    const t = new Date(now.getTime() - offsetMs);
    return t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="w-full h-full flex flex-col bg-black/0"
    >
      <div className={`flex-1 w-full h-full flex flex-col transition-opacity duration-500 overflow-hidden ${isOpacityFixed ? 'opacity-100' : 'opacity-40 hover:opacity-100'}`}>
        {/* Header */}
      <div className="shrink-0 flex items-center gap-4 px-6 py-4 border-b border-stark-cyan/15 bg-black/60 backdrop-blur-xl no-drag">
        <button
          onClick={onBack}
          className="flex items-center justify-center w-8 h-8 rounded-full border border-stark-cyan/30 text-stark-cyan/60 hover:text-stark-cyan hover:border-stark-cyan hover:bg-stark-cyan/10 transition-all duration-200"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="m15 18-6-6 6-6"/>
          </svg>
        </button>

        <div className="flex items-center gap-3">
          {/* Mini orb indicator */}
          <div className="relative w-7 h-7 flex items-center justify-center">
            <div className="absolute w-7 h-7 rounded-full border border-stark-cyan/40 animate-spin" style={{ animationDuration: '8s' }} />
            <div className="w-2.5 h-2.5 rounded-full bg-stark-cyan shadow-[0_0_8px_#00f3ff] animate-pulse" />
          </div>
          <div>
            <div className="text-[11px] tracking-[0.35em] text-stark-cyan font-bold leading-none mb-0.5">A.T.L.A.S.</div>
            <div className="text-[9px] tracking-[0.25em] text-stark-cyan/40 leading-none">NEURAL CONSOLE // ACTIVE</div>
          </div>
        </div>

        <div className="ml-auto flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full border border-stark-cyan/20 bg-stark-cyan/5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_4px_#34d399] animate-pulse" />
            <span className="text-[9px] tracking-[0.2em] text-emerald-400 font-mono">ONLINE</span>
          </div>
          <div className="text-[9px] tracking-[0.2em] text-stark-cyan/30 font-mono border border-stark-cyan/10 px-2 py-1 rounded">
            SESSION-{sessionId}
          </div>
        </div>
      </div>

      {/* Scanline decoration */}
      <div className="shrink-0 h-px w-full" style={{
        background: 'linear-gradient(90deg, transparent 0%, rgba(0,243,255,0.4) 30%, rgba(0,243,255,0.8) 50%, rgba(0,243,255,0.4) 70%, transparent 100%)',
        boxShadow: '0 0 8px rgba(0,243,255,0.3)'
      }} />

      {/* Messages area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-6 py-6 space-y-6 no-drag"
        style={{ scrollBehavior: 'smooth' }}
      >
        {/* System boot message at top */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex justify-center"
        >
          <div className="flex items-center gap-3 px-4 py-1.5 rounded-full border border-stark-cyan/10 bg-stark-cyan/5">
            <div className="w-1 h-1 rounded-full bg-stark-cyan/50" />
            <span className="text-[9px] tracking-[0.3em] text-stark-cyan/40 font-mono">SECURE CHANNEL ESTABLISHED</span>
            <div className="w-1 h-1 rounded-full bg-stark-cyan/50" />
          </div>
        </motion.div>

        <AnimatePresence initial={false}>
          {history.map((msg, idx) => {
            const isAtlas = msg.sender === 'ATLAS';
            const isSystem = msg.sender === 'SYSTEM';
            const isUser = msg.sender === 'TUDOR';

            if (isSystem) {
              return (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex justify-center"
                >
                  <div className="px-4 py-1.5 rounded-full border border-stark-orange/20 bg-stark-orange/5">
                    <span className="text-[9px] tracking-[0.25em] text-stark-orange/60 font-mono">[SYS] {msg.text}</span>
                  </div>
                </motion.div>
              );
            }

            return (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 12, x: isUser ? 12 : -12 }}
                animate={{ opacity: 1, y: 0, x: 0 }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
                className={`flex items-end gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
              >
                {/* Avatar */}
                <div className={`shrink-0 w-8 h-8 rounded-full border flex items-center justify-center ${
                  isAtlas
                    ? 'border-stark-cyan/50 bg-stark-cyan/10 shadow-[0_0_10px_rgba(0,243,255,0.2)]'
                    : 'border-white/20 bg-white/5'
                }`}>
                  {isAtlas ? (
                    <div className="w-2.5 h-2.5 rounded-full bg-stark-cyan shadow-[0_0_6px_#00f3ff] animate-pulse" />
                  ) : (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.5)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                      <circle cx="12" cy="7" r="4"/>
                    </svg>
                  )}
                </div>

                {/* Bubble */}
                <div className={`flex flex-col gap-1.5 max-w-[72%] ${isUser ? 'items-end' : 'items-start'}`}>
                  <div className={`text-[9px] tracking-[0.25em] font-mono ${
                    isAtlas ? 'text-stark-cyan/50' : 'text-white/30'
                  } ${isUser ? 'mr-1' : 'ml-1'}`}>
                    {isAtlas ? 'A.T.L.A.S.' : 'OPERATOR'} · {formatTime(idx)}
                  </div>

                  <div className={`relative px-5 py-3.5 rounded-2xl text-sm leading-relaxed font-mono ${
                    isAtlas
                      ? 'bg-stark-cyan/8 border border-stark-cyan/25 text-stark-cyan/90 rounded-tl-sm shadow-[inset_0_0_20px_rgba(0,243,255,0.03),0_0_15px_rgba(0,243,255,0.08)]'
                      : 'bg-white/8 border border-white/15 text-white/85 rounded-tr-sm'
                  }`}
                  style={isAtlas ? { background: 'rgba(0,243,255,0.05)' } : { background: 'rgba(255,255,255,0.06)' }}
                  >
                    {/* Glow line for ATLAS messages */}
                    {isAtlas && (
                      <div className="absolute left-0 top-3 bottom-3 w-px bg-gradient-to-b from-transparent via-stark-cyan/60 to-transparent rounded-full" />
                    )}
                    <span className="relative">{msg.text}</span>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* Typing indicator */}
        <AnimatePresence>
          {isTyping && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              className="flex items-end gap-3"
            >
              <div className="shrink-0 w-8 h-8 rounded-full border border-stark-cyan/50 bg-stark-cyan/10 flex items-center justify-center">
                <div className="w-2.5 h-2.5 rounded-full bg-stark-cyan animate-pulse" />
              </div>
              <div className="px-5 py-3.5 rounded-2xl rounded-tl-sm border border-stark-cyan/25"
                style={{ background: 'rgba(0,243,255,0.05)' }}>
                <div className="flex gap-1.5 items-center h-4">
                  {[0, 1, 2].map(i => (
                    <motion.div
                      key={i}
                      className="w-1.5 h-1.5 rounded-full bg-stark-cyan/60"
                      animate={{ scale: [1, 1.4, 1], opacity: [0.4, 1, 0.4] }}
                      transition={{ duration: 0.8, delay: i * 0.18, repeat: Infinity }}
                    />
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Divider */}
      <div className="shrink-0 h-px mx-6" style={{ background: 'linear-gradient(90deg, transparent, rgba(0,243,255,0.15), transparent)' }} />

      {/* Input area */}
      <div className="shrink-0 p-4 bg-black/40 backdrop-blur-xl no-drag">
        <div className="flex items-end gap-3 p-3 rounded-2xl border border-stark-cyan/20 bg-black/60 focus-within:border-stark-cyan/50 focus-within:shadow-[0_0_20px_rgba(0,243,255,0.08)] transition-all duration-300">
          
          <div className="flex items-center justify-center w-7 h-7 shrink-0 mb-0.5">
            <div className="w-1.5 h-1.5 rounded-full bg-stark-cyan/40 animate-pulse" />
          </div>

          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
            }}
            onKeyDown={handleKeyDown}
            rows={1}
            autoFocus
            className="flex-1 bg-transparent text-white/90 font-mono text-[13px] leading-relaxed resize-none focus:outline-none placeholder-white/20 min-h-[28px] max-h-[120px]"
            placeholder="Issue command to A.T.L.A.S. ..."
            style={{ scrollbarWidth: 'none' }}
          />

          {/* Char counter */}
          {input.length > 0 && (
            <span className="text-[9px] text-stark-cyan/30 font-mono self-end mb-1 shrink-0">
              {input.length}
            </span>
          )}

          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className={`shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-200 mb-0.5 ${
              input.trim()
                ? 'bg-stark-cyan/20 border border-stark-cyan/50 text-stark-cyan hover:bg-stark-cyan/30 shadow-[0_0_10px_rgba(0,243,255,0.2)]'
                : 'bg-white/5 border border-white/10 text-white/20 cursor-not-allowed'
            }`}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="m22 2-7 20-4-9-9-4 20-7z"/>
            </svg>
          </button>
        </div>

        {/* Bottom hint */}
        <div className="flex justify-between items-center mt-2 px-1">
          <span className="text-[9px] text-white/15 font-mono tracking-wider">ENTER to send · SHIFT+ENTER for newline</span>
          <span className="text-[9px] text-stark-cyan/20 font-mono tracking-wider">ENCRYPTED // AES-256</span>
        </div>
      </div>
      </div>
    </motion.div>
  );
});
