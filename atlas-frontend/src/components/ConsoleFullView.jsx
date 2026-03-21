import { useState, useEffect, useRef, useMemo, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// ── CommandIntelPanel (inline sub-component) ─────────────────────────────────
function CommandIntelPanel({ cognitiveData, orchestratorTask, activePlan }) {
  const [collapsed, setCollapsed] = useState(false);

  if (!orchestratorTask && !activePlan) return null;

  const intentColor = {
    COMMAND: '#fbbf24',
    QUERY:   '#00f3ff',
    MEMORY:  '#a78bfa',
    IMAGINE: '#34d399',
    CHAT:    'rgba(255,255,255,0.4)',
  }[cognitiveData?.intent] ?? 'rgba(255,255,255,0.4)';

  return (
    <div className="shrink-0 mx-6 mb-3 rounded-xl border border-stark-cyan/15 bg-black/50 overflow-hidden">
      {/* Collapsed header — always visible */}
      <button
        onClick={() => setCollapsed(c => !c)}
        className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-stark-cyan/5 transition-colors text-left"
      >
        <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: intentColor }} />
        <span className="text-[9px] font-mono tracking-[0.3em]" style={{ color: intentColor }}>
          {cognitiveData?.intent ?? 'PROCESSING'}
        </span>
        <span className="text-[9px] text-white/30 font-mono flex-1 truncate">
          {orchestratorTask || 'Analysing...'}
        </span>
        {cognitiveData?.salience != null && (
          <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded border ${
            cognitiveData.salience >= 8
              ? 'border-stark-orange/40 text-stark-orange bg-stark-orange/10'
              : 'border-stark-cyan/20 text-stark-cyan/50'
          }`}>
            SAL {cognitiveData.salience}/10
          </span>
        )}
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.3)"
          strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          style={{ transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
          <path d="m6 9 6 6 6-6"/>
        </svg>
      </button>

      {/* Expanded body */}
      {!collapsed && (
        <div className="border-t border-stark-cyan/10 px-4 py-3 space-y-3">

          {/* Full task description */}
          {orchestratorTask && (
            <div>
              <div className="text-[8px] tracking-[0.3em] text-stark-cyan/40 mb-1 font-mono">SYNTHESIZED TASK</div>
              <div className="text-[11px] text-white/70 font-mono leading-relaxed">
                {orchestratorTask}
              </div>
            </div>
          )}

          {/* Cognitive metadata row */}
          {cognitiveData && (
            <div className="flex gap-4 flex-wrap">
              <div>
                <div className="text-[8px] tracking-widest text-stark-cyan/30 font-mono">MOOD</div>
                <div className={`text-[10px] font-mono font-bold ${
                  cognitiveData.mood === 'positive'   ? 'text-emerald-400' :
                  cognitiveData.mood === 'frustrated' ? 'text-orange-400' :
                  cognitiveData.mood === 'panicked'   ? 'text-red-400' :
                  'text-white/40'
                }`}>{(cognitiveData.mood ?? 'neutral').toUpperCase()}</div>
              </div>
              <div>
                <div className="text-[8px] tracking-widest text-stark-cyan/30 font-mono">URGENCY</div>
                <div className={`text-[10px] font-mono font-bold ${
                  cognitiveData.urgency === 'high' ? 'text-stark-orange' : 'text-white/40'
                }`}>{(cognitiveData.urgency ?? 'low').toUpperCase()}</div>
              </div>
              <div>
                <div className="text-[8px] tracking-widest text-stark-cyan/30 font-mono">ROUTER</div>
                <div className="text-[10px] font-mono font-bold" style={{ color: intentColor }}>
                  {cognitiveData.intent ?? '—'}
                </div>
              </div>
            </div>
          )}

          {/* Plan steps */}
          {activePlan?.steps?.length > 0 && (
            <div>
              <div className="text-[8px] tracking-[0.3em] text-stark-cyan/40 mb-2 font-mono">
                EXECUTION PLAN — {activePlan.steps.length} STEPS
              </div>
              <div className="space-y-1">
                {activePlan.steps.map((step, i) => {
                  const done   = activePlan.completed?.[i];
                  const active = !done && i === activePlan.activeStep;
                  return (
                    <div key={i} className={`flex items-start gap-2.5 pl-2 border-l-2 text-[10px] font-mono py-0.5 ${
                      done   ? 'border-emerald-400/60 text-emerald-400/70' :
                      active ? 'border-stark-cyan text-stark-cyan' :
                               'border-white/10 text-white/25'
                    }`}>
                      <span className="shrink-0">
                        {done ? '✓' : active ? '►' : '○'}
                      </span>
                      <span className={active ? 'animate-pulse' : ''}>{step}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main ConsoleFullView ─────────────────────────────────────────────────────
export default memo(function ConsoleFullView({
  history, ws, onBack, isOpacityFixed,
  streamingText, cognitiveData, isInterrupted,
  activePlan, orchestratorTask,
  lastTaskFiles, onOpenCode,
}) {
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const sessionId = useMemo(() => Math.floor(Math.random() * 9000 + 1000), []);

  // Track plan completion for auto-collapse awareness
  const prevPlanRef = useRef(activePlan);
  useEffect(() => {
    prevPlanRef.current = activePlan;
  }, [activePlan]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history]);

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

      {/* Command Intel Panel */}
      <CommandIntelPanel
        cognitiveData={cognitiveData}
        orchestratorTask={orchestratorTask}
        activePlan={activePlan}
      />

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

        {/* Streaming bubble */}
        <AnimatePresence>
          {streamingText && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              className="flex items-end gap-3"
            >
              <div className="shrink-0 w-8 h-8 rounded-full border border-stark-cyan/50 bg-stark-cyan/10 flex items-center justify-center">
                <div className="w-2.5 h-2.5 rounded-full bg-stark-cyan animate-pulse" />
              </div>
              <div
                className="px-5 py-3.5 rounded-2xl rounded-tl-sm border border-stark-cyan/25 max-w-[72%] text-sm font-mono text-stark-cyan/90 relative"
                style={{ background: 'rgba(0,243,255,0.05)' }}
              >
                <div className="absolute left-0 top-3 bottom-3 w-px bg-gradient-to-b from-transparent via-stark-cyan/60 to-transparent rounded-full" />
                <span className="relative">{streamingText}</span>
                <span className="inline-block w-1.5 h-3.5 bg-stark-cyan ml-1 animate-pulse align-middle" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Interrupted banner */}
        <AnimatePresence>
          {isInterrupted && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex justify-center"
            >
              <div className="px-4 py-1.5 rounded-full border border-stark-orange/30 bg-stark-orange/10">
                <span className="text-[9px] tracking-[0.25em] text-stark-orange font-mono">⚡ INTERRUPTED</span>
              </div>
            </motion.div>
          )}
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

      {/* View in Code banner — appears when files were written */}
      {lastTaskFiles?.files?.length > 0 && (
        <div className="shrink-0 mx-4 mb-2 flex items-center gap-3 px-4 py-2.5 rounded-lg border border-stark-cyan/25 bg-stark-cyan/5">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00f3ff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
          </svg>
          <div className="flex-1 min-w-0">
            <div className="text-[9px] text-stark-cyan/50 font-mono tracking-widest">FILES WRITTEN</div>
            <div className="text-[10px] text-stark-cyan font-mono truncate">
              {lastTaskFiles.files.join('  ·  ')}
            </div>
          </div>
          <button
            data-hand-target
            data-hand-label="VIEW CODE"
            onClick={() => onOpenCode(lastTaskFiles)}
            className="shrink-0 px-3 py-1.5 rounded-lg border border-stark-cyan/40 bg-stark-cyan/10 text-stark-cyan text-[9px] font-mono tracking-widest hover:bg-stark-cyan/25 hover:border-stark-cyan transition-all duration-200"
          >
            VIEW IN CODE →
          </button>
        </div>
      )}

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

        <div className="flex justify-between items-center mt-2 px-1">
          <span className="text-[9px] text-white/15 font-mono tracking-wider">ENTER to send · SHIFT+ENTER for newline</span>
          <span className="text-[9px] text-stark-cyan/20 font-mono tracking-wider">ENCRYPTED // AES-256</span>
        </div>
      </div>
      </div>
    </motion.div>
  );
});
