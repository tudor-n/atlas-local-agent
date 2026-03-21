import { useState, useEffect, useRef, useCallback, memo } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function importanceDotColor(imp) {
  if (imp >= 8) return '#ff5500';
  if (imp >= 5) return '#00f3ff';
  return 'rgba(255,255,255,0.3)';
}

function timeAgo(timestamp) {
  if (!timestamp) return '';
  const d = new Date(timestamp);
  if (isNaN(d)) return '';
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return `${Math.floor(diff / 604800)}w ago`;
}

export default memo(function MemoryApp({ onBack }) {
  const [memories, setMemories] = useState([]);
  const [total, setTotal]       = useState(0);
  const [query, setQuery]       = useState('');
  const [loading, setLoading]   = useState(true);
  const debounceRef             = useRef(null);

  const loadAll = useCallback(() => {
    setLoading(true);
    fetch(`${API}/memory/list`)
      .then(r => r.json())
      .then(d => { setMemories(d.memories); setTotal(d.total); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const handleSearch = (q) => {
    setQuery(q);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (!q.trim()) { loadAll(); return; }
      setLoading(true);
      fetch(`${API}/memory/search?q=${encodeURIComponent(q)}`)
        .then(r => r.json())
        .then(d => { setMemories(d.memories); setTotal(d.total); })
        .catch(() => {})
        .finally(() => setLoading(false));
    }, 400);
  };

  const handleDelete = (id) => {
    setMemories(prev => prev.filter(m => m.id !== id));
    setTotal(prev => Math.max(0, prev - 1));
    fetch(`${API}/memory/${encodeURIComponent(id)}`, { method: 'DELETE' }).catch(() => {});
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
            <div className="absolute w-7 h-7 rounded-full border border-stark-cyan/40 animate-spin" style={{ animationDuration: '12s' }} />
            <div className="w-2.5 h-2.5 rounded-full bg-stark-cyan/70" />
          </div>
          <div>
            <div className="text-[11px] tracking-[0.35em] text-stark-cyan font-bold leading-none mb-0.5">LONG-TERM MEMORY</div>
            <div className="text-[9px] tracking-[0.25em] text-stark-cyan/40 leading-none">CHROMADB // PERSISTENT</div>
          </div>
        </div>

        <div className="ml-auto text-[9px] tracking-[0.2em] text-stark-cyan/30 font-mono border border-stark-cyan/10 px-2 py-1 rounded">
          {memories.length} ENTRIES
        </div>
      </div>

      {/* Scanline */}
      <div className="shrink-0 h-px w-full" style={{
        background: 'linear-gradient(90deg, transparent 0%, rgba(0,243,255,0.4) 30%, rgba(0,243,255,0.8) 50%, rgba(0,243,255,0.4) 70%, transparent 100%)',
      }} />

      {/* Body */}
      <div className="flex-1 overflow-hidden flex flex-col p-6 gap-4">

        {/* Search */}
        <div className="shrink-0" data-hand-target>
          <input
            type="text"
            value={query}
            onChange={e => handleSearch(e.target.value)}
            placeholder="Search memories..."
            className="bg-black/60 border border-stark-cyan/20 rounded-lg px-3 py-2 text-xs font-mono text-stark-cyan placeholder-stark-cyan/20 focus:border-stark-cyan/50 focus:outline-none w-full"
          />
        </div>

        {/* Memory list */}
        <div className="flex-1 overflow-y-auto min-h-0 pr-1">
          {loading ? (
            <div className="flex justify-center items-center h-full gap-2">
              {[0, 1, 2].map(i => (
                <div key={i} className="w-2 h-2 rounded-full bg-stark-cyan/60 animate-pulse" style={{ animationDelay: `${i * 0.2}s` }} />
              ))}
            </div>
          ) : memories.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <span className="text-white/30 text-xs">No memories matching query</span>
            </div>
          ) : (
            <div className="flex flex-col gap-0">
              {memories.map((mem, i) => (
                <div key={mem.id}>
                  <div className="border border-stark-cyan/10 rounded-lg p-3 hover:border-stark-cyan/30 transition-colors">
                    <div className="flex items-start gap-2 mb-1.5">
                      <div
                        className="w-2 h-2 rounded-full shrink-0 mt-1"
                        style={{ background: importanceDotColor(mem.importance) }}
                      />
                      <span className="text-[11px] text-white/80 leading-relaxed flex-1">{mem.text}</span>
                    </div>
                    <div className="flex items-center justify-between mt-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[9px] text-white/30">
                          importance: {mem.importance.toFixed(1)}
                        </span>
                        {mem.tags.filter(Boolean).map(tag => (
                          <span
                            key={tag}
                            className="px-1.5 py-0.5 rounded text-[8px] border border-stark-cyan/20 text-stark-cyan/60"
                          >
                            {tag}
                          </span>
                        ))}
                        {mem.timestamp && (
                          <span className="text-[9px] text-white/20">{timeAgo(mem.timestamp)}</span>
                        )}
                      </div>
                      <button
                        data-hand-target
                        data-hand-label="DELETE"
                        onClick={() => handleDelete(mem.id)}
                        className="text-[9px] text-stark-orange/60 hover:text-stark-orange border border-stark-orange/20 hover:border-stark-orange/50 px-2 py-0.5 rounded transition-colors shrink-0 ml-2"
                      >
                        DELETE
                      </button>
                    </div>
                  </div>
                  {i < memories.length - 1 && (
                    <div className="w-full h-px bg-stark-cyan/5 my-1" />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});
