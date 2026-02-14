import { useCallback, useEffect, useRef, useState } from "react";

export function usePoll(fn, intervalMs, { immediate = true } = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading] = useState(false);
  const [paused, setPaused] = useState(false);
  const [tick, setTick] = useState(immediate ? 1 : 0);
  const alive = useRef(true);
  const fetchingRef = useRef(false);

  // Trigger a manual refresh by bumping tick
  const refresh = useCallback(() => setTick((t) => t + 1), []);

  // Fetch whenever tick changes
  useEffect(() => {
    if (tick === 0) return;
    if (fetchingRef.current) return; // skip if already in-flight
    let cancelled = false;
    fetchingRef.current = true;

    (async () => {
      try {
        const res = await fn();
        if (cancelled) return;
        // Only update state if data actually changed
        setData((prev) => {
          const next = JSON.stringify(res);
          if (JSON.stringify(prev) === next) return prev;
          return res;
        });
        setError(null);
      } catch (e) {
        if (cancelled) return;
        setError(e);
      }
      if (!cancelled) {
        fetchingRef.current = false;
      }
    })();

    return () => {
      cancelled = true;
      fetchingRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick]);

  // Auto-refresh interval
  useEffect(() => {
    if (paused || intervalMs <= 0) return;
    const timer = setInterval(() => setTick((t) => t + 1), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs, paused]);

  // Cleanup on unmount
  useEffect(() => {
    return () => { alive.current = false; };
  }, []);

  return {
    data,
    error,
    loading,
    paused,
    refresh,
    pause: () => setPaused(true),
    resume: () => setPaused(false),
    togglePause: () => setPaused((p) => !p),
  };
}
