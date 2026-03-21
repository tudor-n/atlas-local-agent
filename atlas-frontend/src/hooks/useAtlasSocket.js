// atlas-frontend/src/hooks/useAtlasSocket.js
//
// Resilient WebSocket hook with exponential-backoff reconnection.

import { useEffect, useRef, useCallback, useState } from 'react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

export function useAtlasSocket({ onMessage }) {
  const wsRef        = useRef(null);
  const reconnectRef = useRef(null);
  const delayRef     = useRef(3000);       // start at 3 s
  const mountedRef   = useRef(true);
  const [connected, setConnected] = useState(false);

  const stableOnMessage = useRef(onMessage);
  stableOnMessage.current = onMessage;

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    // Tear down any previous socket — null out its onclose FIRST so the
    // intentional close doesn't trigger the reconnect handler.
    if (wsRef.current) {
      wsRef.current.onclose = null;
      try { wsRef.current.close(); } catch (_) { /* ignore */ }
    }

    const socket = new WebSocket(WS_URL);

    socket.onopen = () => {
      console.log('[WS] Connected');
      setConnected(true);
      delayRef.current = 3000;             // reset backoff on success
    };

    socket.onmessage = (event) => {
      stableOnMessage.current?.(event);
    };

    socket.onerror = (e) => {
      console.warn('[WS] Error:', e);
    };

    socket.onclose = () => {
      setConnected(false);
      if (!mountedRef.current) return;
      console.log(`[WS] Closed — reconnecting in ${delayRef.current / 1000}s`);
      reconnectRef.current = setTimeout(() => {
        delayRef.current = Math.min(delayRef.current * 2, 30000);  // cap 30 s
        connect();
      }, delayRef.current);
    };

    wsRef.current = socket;
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;   // don't reconnect on intentional teardown
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { ws: wsRef, connected };
}
