const API_BASE = import.meta.env.VITE_API_BASE || "";

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText} - ${text}`);
  }

  // Some endpoints may return empty body; handle safely
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return await res.json();
  return await res.text();
}

export const api = {
  live: () => request("/api/live"),
  readings: (minutes = 60, limit = 5000) =>
    request(`/api/readings?minutes=${minutes}&limit=${limit}`),
  actions: (minutes = 240, limit = 2000) =>
    request(`/api/actions?minutes=${minutes}&limit=${limit}`),

  controllerEnable: () => request("/api/controller/enable", { method: "POST" }),
  controllerDisable: () => request("/api/controller/disable", { method: "POST" }),
  override: (state, duration_s) =>
    request("/api/controller/override", {
      method: "POST",
      body: JSON.stringify({ state, duration_s }),
    }),
  overrideCancel: () =>
    request("/api/controller/override/cancel", { method: "POST" }),

  scheduleGet: () => request("/api/schedule"),
  scheduleDefaults: () => request("/api/schedule/defaults"),
  schedulePut: (windows) =>
    request("/api/schedule", {
      method: "PUT",
      body: JSON.stringify({ windows }),
    }),

  simStatus: () => request("/api/sim/status"),
  simEnable: () => request("/api/sim/enable", { method: "POST" }),
  simDisable: () => request("/api/sim/disable", { method: "POST" }),
  simManual: (lux) =>
    request("/api/sim/lux/manual", {
      method: "POST",
      body: JSON.stringify({ lux }),
    }),
  simPattern: (payload) =>
    request("/api/sim/lux/pattern", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  settingsGet: () => request("/api/settings"),
  settingsUpdate: (updates) =>
    request("/api/settings", {
      method: "PUT",
      body: JSON.stringify({ updates }),
    }),
  discoverSonoff: () =>
    request("/api/settings/discover-sonoff", { method: "POST" }),
};
