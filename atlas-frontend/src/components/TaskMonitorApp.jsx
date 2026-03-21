import { memo } from 'react';

export default memo(function TaskMonitorApp({ activePlan, orchestratorTask, highSalienceLog, cognitiveData, onBack, onOpenCode, lastTaskFiles }) {
  const isActive = !!activePlan;
  const completedCount = activePlan ? activePlan.completed.filter(Boolean).length : 0;

  const salienceColor = (text) => {
    if (/crash|emergency|critical/i.test(text)) return 'text-stark-orange';
    return 'text-stark-cyan/60';
  };

  const formatTs = (ts) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
  };

  return (
    <div className="w-full h-full flex flex-col overflow-hidden font-mono" data-hand-component>

      {/* Header — matches ConsoleFullView style */}
      <div className="shrink-0 flex items-center gap-4 px-6 py-4 border-b border-stark-cyan/15 bg-black/60 backdrop-blur-xl no-drag">
        <button
          data-hand-target
          data-hand-label="BACK"
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
            <div className={`w-2.5 h-2.5 rounded-full shadow-[0_0_8px_#ff5500] ${activePlan ? 'bg-stark-orange animate-pulse' : 'bg-stark-cyan/30'}`} />
          </div>
          <div>
            <div className="text-[11px] tracking-[0.35em] text-stark-cyan font-bold leading-none mb-0.5">TASK MONITOR</div>
            <div className="text-[9px] tracking-[0.25em] text-stark-cyan/40 leading-none">
              {activePlan ? `EXECUTING — ${activePlan.steps.length} STEPS` : 'IDLE'}
            </div>
          </div>
        </div>

        {/* "View in Code" button — only when files were written */}
        {lastTaskFiles?.files?.length > 0 && (
          <button
            data-hand-target
            data-hand-label="VIEW CODE"
            onClick={() => onOpenCode(lastTaskFiles)}
            className="ml-auto flex items-center gap-2 px-3 py-1.5 rounded-lg border border-stark-cyan/30 bg-stark-cyan/10 text-stark-cyan text-[10px] font-mono tracking-widest hover:bg-stark-cyan/20 hover:border-stark-cyan/60 transition-all duration-200"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
            </svg>
            VIEW IN CODE
          </button>
        )}
      </div>

      {/* Scanline */}
      <div className="shrink-0 h-px w-full" style={{
        background: 'linear-gradient(90deg, transparent 0%, rgba(0,243,255,0.4) 30%, rgba(0,243,255,0.8) 50%, rgba(0,243,255,0.4) 70%, transparent 100%)',
      }} />

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-4">

        {!isActive ? (
          /* Idle state */
          <div className="flex-1 flex flex-col items-center justify-center gap-3">
            <div className="w-3 h-3 rounded-full bg-stark-cyan animate-pulse shadow-[0_0_8px_#00f3ff]" />
            <span className="text-[11px] tracking-widest text-stark-cyan/60">ATLAS IS IDLE</span>
            <span className="text-[9px] text-white/30 tracking-wider">Awaiting command...</span>
          </div>
        ) : (
          <>
            {/* Current task */}
            {orchestratorTask && (
              <div className="shrink-0">
                <div className="text-[8px] text-stark-cyan/40 tracking-widest mb-1">CURRENT TASK</div>
                <div className="text-[11px] text-stark-cyan/80 leading-relaxed border-l-2 border-stark-cyan/30 pl-3">
                  &quot;{orchestratorTask}&quot;
                </div>
              </div>
            )}

            <div className="w-full h-px bg-stark-cyan/10 shrink-0" />

            {/* Execution plan */}
            <div className="flex-1 min-h-0">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[8px] text-stark-cyan/40 tracking-widest">EXECUTION PLAN</span>
                <span className="text-[9px] text-stark-cyan/60">
                  {completedCount} / {activePlan.steps.length} steps
                </span>
              </div>
              <div className="flex flex-col gap-2">
                {activePlan.steps.map((step, i) => {
                  const isDone   = activePlan.completed?.[i];
                  const isNow    = !isDone && i === activePlan.activeStep;
                  const isPending = !isDone && !isNow;

                  return (
                    <div
                      key={i}
                      data-hand-target
                      className={`flex items-start gap-3 px-3 py-2 rounded-lg transition-all duration-300 ${
                        isDone    ? 'border-l-2 border-emerald-400/60' :
                        isNow     ? 'border-l-2 border-stark-cyan' :
                                    'border-l-2 border-white/10'
                      }`}
                    >
                      <span className={`shrink-0 text-[11px] mt-px ${
                        isDone   ? 'text-emerald-400' :
                        isNow    ? 'text-stark-cyan' :
                                   'text-white/30'
                      }`}>
                        {isDone ? '✓' : isNow ? '►' : '○'}
                      </span>
                      <span className={`text-[11px] leading-relaxed ${
                        isDone    ? 'text-emerald-400' :
                        isNow     ? 'text-stark-cyan font-bold animate-pulse' :
                                    'text-white/30'
                      }`}>
                        {step}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}

        {/* Salience log — always visible */}
        {highSalienceLog.length > 0 && (
          <>
            <div className="w-full h-px bg-stark-cyan/10 shrink-0" />
            <div className="shrink-0">
              <div className="text-[8px] text-stark-cyan/40 tracking-widest mb-2">SALIENCE LOG</div>
              <div className="flex flex-col gap-1 max-h-[120px] overflow-y-auto">
                {highSalienceLog.map((entry, i) => (
                  <div key={i} className="flex gap-2 items-start" data-hand-target>
                    <span className="text-[9px] text-white/30 shrink-0">[{formatTs(entry.ts)}]</span>
                    <span className={`text-[10px] ${salienceColor(entry.text)}`}>{entry.text}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
});
