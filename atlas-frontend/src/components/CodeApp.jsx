import { useState, useEffect, useRef, memo, useCallback } from 'react';
import { motion } from 'framer-motion';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ── Very lightweight syntax highlighter ──────────────────────────────────────
function tokenizeLine(line, lang) {
  const rules = [
    { re: /(#.*)$/,                                           color: '#6b7280' },
    { re: /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`[^`]*`)/,  color: '#86efac' },
    { re: /\b(def|class|import|from|return|if|else|elif|for|while|with|as|in|not|and|or|True|False|None|lambda|yield|async|await|try|except|finally|raise|pass|break|continue|global|nonlocal|del|assert)\b/, color: '#c084fc' },
    { re: /\b(const|let|var|function|return|if|else|for|while|class|import|export|default|from|async|await|new|this|typeof|instanceof|throw|try|catch|finally|in|of)\b/, color: '#c084fc' },
    { re: /\b(\d+\.?\d*)\b/,                                 color: '#fb923c' },
    { re: /\b([A-Z][a-zA-Z0-9_]*)\b/,                        color: '#67e8f9' },
    { re: /\b([a-zA-Z_]\w*)\s*(?=\()/,                       color: '#fde68a' },
  ];

  function tokenize(str) {
    for (const { re, color } of rules) {
      const m = re.exec(str);
      if (!m) continue;
      const before = str.slice(0, m.index);
      const match  = m[0];
      const after  = str.slice(m.index + match.length);
      return [
        ...(before ? [{ text: before, color: 'rgba(255,255,255,0.75)' }] : []),
        { text: match, color },
        ...tokenize(after),
      ];
    }
    return str ? [{ text: str, color: 'rgba(255,255,255,0.75)' }] : [];
  }

  return tokenize(line);
}

function extToLang(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  return { py: 'python', js: 'javascript', jsx: 'javascript',
           ts: 'typescript', tsx: 'typescript', cpp: 'cpp',
           c: 'c', h: 'cpp', json: 'json', md: 'markdown' }[ext] ?? 'text';
}

// ── File tree item ────────────────────────────────────────────────────────────
function FileTreeItem({ path, isSelected, isNew, onClick }) {
  const parts  = path.split('/');
  const name   = parts[parts.length - 1];
  const indent = (parts.length - 1) * 12;
  const ext    = name.split('.').pop().toLowerCase();

  const iconColor = {
    py: '#c084fc', js: '#fde68a', jsx: '#67e8f9', ts: '#60a5fa',
    tsx: '#67e8f9', cpp: '#f97316', c: '#f97316', h: '#fb923c',
    json: '#34d399', md: '#94a3b8', txt: '#94a3b8',
  }[ext] ?? '#6b7280';

  return (
    <button
      data-hand-target
      data-hand-label={name}
      onClick={onClick}
      style={{ paddingLeft: 12 + indent }}
      className={`w-full text-left flex items-center gap-2 py-1.5 pr-3 text-[11px] font-mono transition-colors group ${
        isSelected
          ? 'bg-stark-cyan/15 text-stark-cyan border-r-2 border-stark-cyan'
          : 'text-white/50 hover:text-white/80 hover:bg-white/5'
      }`}
    >
      <span style={{ color: iconColor }} className="shrink-0 text-[9px]">◆</span>
      <span className="truncate flex-1">{name}</span>
      {isNew && (
        <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-stark-orange shadow-[0_0_4px_#ff5500]" />
      )}
    </button>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default memo(function CodeApp({ initialFiles = [], taskDescription = '', onBack }) {
  const [allFiles,     setAllFiles]     = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent,  setFileContent]  = useState('');
  const [loadingFiles, setLoadingFiles] = useState(true);
  const [loadingCode,  setLoadingCode]  = useState(false);
  const [error,        setError]        = useState(null);
  const [newFiles,     setNewFiles]     = useState(new Set(initialFiles));
  const codeRef = useRef(null);

  const refreshFiles = useCallback(() => {
    setLoadingFiles(true);
    fetch(`${API}/sandbox/files`)
      .then(r => r.json())
      .then(d => {
        setAllFiles(d.files ?? []);
        setLoadingFiles(false);
        if (!selectedFile && initialFiles.length > 0) {
          const first = initialFiles.find(f => d.files.includes(f));
          if (first) setSelectedFile(first);
        }
      })
      .catch(e => { setError(e.message); setLoadingFiles(false); });
  }, [selectedFile, initialFiles]);

  useEffect(() => { refreshFiles(); }, []); // eslint-disable-line

  useEffect(() => {
    setNewFiles(new Set(initialFiles));
    const t = setTimeout(() => setNewFiles(new Set()), 30000);
    return () => clearTimeout(t);
  }, [initialFiles]);

  useEffect(() => {
    if (!selectedFile) return;
    setLoadingCode(true);
    setFileContent('');
    fetch(`${API}/sandbox/file?path=${encodeURIComponent(selectedFile)}`)
      .then(r => r.text())
      .then(text => { setFileContent(text); setLoadingCode(false); })
      .catch(e => { setFileContent(`// Error loading file: ${e.message}`); setLoadingCode(false); });
  }, [selectedFile]);

  useEffect(() => {
    if (codeRef.current) codeRef.current.scrollTop = 0;
  }, [selectedFile]);

  const lang  = selectedFile ? extToLang(selectedFile) : 'text';
  const lines = fileContent.split('\n');

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="w-full h-full flex flex-col bg-black/0"
      data-hand-component
    >
      {/* ── Header ── */}
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
            <div className="absolute w-7 h-7 rounded-full border border-stark-cyan/40 animate-spin" style={{ animationDuration: '10s' }} />
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#00f3ff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
            </svg>
          </div>
          <div>
            <div className="text-[11px] tracking-[0.35em] text-stark-cyan font-bold leading-none mb-0.5">CODE INSPECTOR</div>
            <div className="text-[9px] tracking-[0.25em] text-stark-cyan/40 leading-none">
              {selectedFile ?? 'SANDBOX EXPLORER'}
            </div>
          </div>
        </div>

        <div className="ml-auto flex items-center gap-3">
          {taskDescription && (
            <div className="max-w-xs px-3 py-1 rounded border border-stark-cyan/15 bg-stark-cyan/5">
              <div className="text-[8px] tracking-widest text-stark-cyan/30 font-mono">LAST TASK</div>
              <div className="text-[9px] text-stark-cyan/60 font-mono truncate">{taskDescription}</div>
            </div>
          )}
          <button
            data-hand-target
            data-hand-label="REFRESH"
            onClick={refreshFiles}
            className="flex items-center justify-center w-8 h-8 rounded-full border border-stark-cyan/20 text-stark-cyan/40 hover:text-stark-cyan hover:border-stark-cyan/60 transition-all duration-200"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>
            </svg>
          </button>
          <div className="text-[9px] tracking-[0.2em] text-stark-cyan/30 font-mono border border-stark-cyan/10 px-2 py-1 rounded">
            {lang.toUpperCase()}
          </div>
        </div>
      </div>

      {/* Scanline */}
      <div className="shrink-0 h-px w-full" style={{
        background: 'linear-gradient(90deg, transparent 0%, rgba(0,243,255,0.4) 30%, rgba(0,243,255,0.8) 50%, rgba(0,243,255,0.4) 70%, transparent 100%)',
      }} />

      {/* ── Body: file tree + code ── */}
      <div className="flex-1 min-h-0 flex flex-row overflow-hidden">

        {/* File tree */}
        <div className="w-56 shrink-0 border-r border-stark-cyan/10 bg-black/30 flex flex-col overflow-hidden">
          <div className="shrink-0 px-3 py-2 border-b border-stark-cyan/10">
            <span className="text-[8px] tracking-[0.3em] text-stark-cyan/30 font-mono">SANDBOX FILES</span>
          </div>
          <div className="flex-1 overflow-y-auto py-1">
            {loadingFiles ? (
              <div className="flex flex-col gap-2 p-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-3 bg-stark-cyan/10 rounded animate-pulse" style={{ width: `${60 + i * 7}%` }} />
                ))}
              </div>
            ) : allFiles.length === 0 ? (
              <div className="p-4 text-[10px] text-white/20 font-mono text-center">
                No files in sandbox
              </div>
            ) : (
              allFiles.map(f => (
                <FileTreeItem
                  key={f}
                  path={f}
                  isSelected={f === selectedFile}
                  isNew={newFiles.has(f)}
                  onClick={() => setSelectedFile(f)}
                />
              ))
            )}
          </div>
        </div>

        {/* Code viewer */}
        <div className="flex-1 min-w-0 flex flex-col overflow-hidden bg-black/20">
          {!selectedFile ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="rgba(0,243,255,0.15)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
              </svg>
              <div>
                <div className="text-[11px] text-white/20 font-mono tracking-widest mb-1">SELECT A FILE</div>
                {initialFiles.length > 0 && (
                  <div className="text-[9px] text-stark-cyan/30 font-mono">
                    {initialFiles.length} new file{initialFiles.length !== 1 ? 's' : ''} from last task
                  </div>
                )}
              </div>
            </div>
          ) : loadingCode ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="flex gap-1.5">
                {[0,1,2].map(i => (
                  <div key={i} className="w-1.5 h-1.5 rounded-full bg-stark-cyan/50 animate-pulse"
                    style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            </div>
          ) : (
            <div ref={codeRef} className="flex-1 overflow-auto" style={{ fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace" }}>
              <table className="w-full border-collapse text-[12px] leading-[1.6]">
                <tbody>
                  {lines.map((line, i) => (
                    <tr key={i} className="group hover:bg-stark-cyan/5 transition-colors">
                      <td className="select-none text-right pr-4 pl-4 text-white/20 group-hover:text-stark-cyan/40 transition-colors w-12 shrink-0 align-top"
                        style={{ fontSize: '10px', paddingTop: '0px', paddingBottom: '0px' }}>
                        {i + 1}
                      </td>
                      <td className="pl-2 pr-6 align-top whitespace-pre">
                        {line === '' ? (
                          <span>&nbsp;</span>
                        ) : (
                          tokenizeLine(line, lang).map((tok, j) => (
                            <span key={j} style={{ color: tok.color }}>{tok.text}</span>
                          ))
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Status bar at bottom of code panel */}
          <div className="shrink-0 flex items-center gap-4 px-4 py-1.5 border-t border-stark-cyan/10 bg-black/40">
            <span className="text-[9px] text-stark-cyan/30 font-mono tracking-wider">
              {selectedFile ? `${lines.length} lines` : '—'}
            </span>
            {selectedFile && (
              <>
                <span className="text-[9px] text-white/15 font-mono">·</span>
                <span className="text-[9px] text-stark-cyan/30 font-mono tracking-wider">
                  {lang.toUpperCase()}
                </span>
                <span className="text-[9px] text-white/15 font-mono">·</span>
                <span className="text-[9px] text-stark-cyan/30 font-mono tracking-wider">
                  {fileContent.length} chars
                </span>
              </>
            )}
            <div className="ml-auto flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400/60" />
              <span className="text-[9px] text-emerald-400/50 font-mono tracking-wider">SANDBOX</span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
});
