import { useCallback, useEffect, useRef, useState } from "react";

export function usePoll(fn, intervalMs, { immediate = true } = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [paused, setPaused] = useState(false);
  const [tick, setTick] = useState(immediate ? 1 : 0);
  const alive = useRef(true);

  // Trigger a manual refresh by bumping tick
  const refresh = useCallback(() => setTick((t) => t + 1), []);

  // Fetch whenever tick changes
  useEffect(() => {
    if (tick === 0) return;
    alive.current = true;
    let cancelled = false;

    (async () => {
      setLoading(true);
      try {
        const res = await fn();
        if (cancelled) return;
        setData(res);
        setError(null);
      } catch (e) {
        if (cancelled) return;
        setError(e);
      }
      if (!cancelled) setLoading(false);
    })();

    return () => { cancelled = true; };
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
