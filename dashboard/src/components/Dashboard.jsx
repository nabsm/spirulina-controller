import { memo, useMemo, useState } from "react";
import { api } from "../lib/api.js";
import { usePoll } from "../lib/usePoll.js";
import { Card, Collapsible, Pill, Button, Input, ToggleSwitch, TriToggle } from "./ui.jsx";
import SimPanel from "./SimPanel.jsx";
import SettingsPanel from "./SettingsPanel.jsx";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceArea,
} from "recharts";

function fmtTime(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleTimeString();
}

function fmtNum(v, digits = 0) {
  if (v === null || v === undefined) return "-";
  return Number(v).toFixed(digits);
}

const LuxChart = memo(function LuxChart({ chartData, activeMin, activeMax }) {
  return (
    <div className="h-80 min-h-[320px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="t" tickFormatter={(v) => fmtTime(v)} minTickGap={20} stroke="#94a3b8" tick={{ fill: "#94a3b8" }} />
          <YAxis stroke="#94a3b8" tick={{ fill: "#94a3b8" }} />
          <Tooltip
            labelFormatter={(v) => `Time: ${fmtTime(v)}`}
            formatter={(val) => [val, "lux"]}
            contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #475569", borderRadius: "0.5rem", color: "#f1f5f9" }}
            labelStyle={{ color: "#94a3b8" }}
          />
          {activeMin !== null && activeMax !== null && (
            <ReferenceArea y1={activeMin} y2={activeMax} fill="#60a5fa" fillOpacity={0.08} />
          )}
          <Line
            type="monotone"
            dataKey="lux"
            dot={false}
            strokeWidth={2}
            stroke="#60a5fa"
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
});

export default function Dashboard() {
  const live = usePoll(api.live, 2500, { immediate: true });
  const readings = usePoll(() => api.readings(60, 1200), 20000, { immediate: true }); // reduce limit too
  const actions = usePoll(() => api.actions(240, 400), 20000, { immediate: true });
  const sim = usePoll(api.simStatus, 8000, { immediate: true });
  const schedule = usePoll(api.scheduleGet, 0, { immediate: true });
  const sysInfo = usePoll(api.systemInfo, 30000, { immediate: true });

  // Override
  const [overrideMins, setOverrideMins] = useState("10");
  // internal override selection when not AUTO: "on" | "off"
  const [overrideState, setOverrideState] = useState("on");

  // Simulation controls
  const [manualLux, setManualLux] = useState("3500");
  const [patternType, setPatternType] = useState("sine");
  const [patternBaseline, setPatternBaseline] = useState("4000");
  const [patternAmplitude, setPatternAmplitude] = useState("2000");
  const [patternPeriod, setPatternPeriod] = useState("600");
  const [patternNoise, setPatternNoise] = useState("80");

  // Sim panel drawer
  const [simPanelOpen, setSimPanelOpen] = useState(false);
  // Settings panel drawer
  const [settingsPanelOpen, setSettingsPanelOpen] = useState(false);

  // Schedule editing
  const [schedDraft, setSchedDraft] = useState(null);
  const [saveMsg, setSaveMsg] = useState("");
  const [schedConfirm, setSchedConfirm] = useState(null);

  // UI action error display
  const [uiError, setUiError] = useState("");

  const liveData = live.data;
  const luxNow = liveData?.last_reading?.value;
  const avg30 = liveData?.avg_lux_30s;
  const thr = useMemo(() => liveData?.thresholds || {}, [liveData?.thresholds]);
  const lightOn = liveData?.light_state;
  const ctrl = useMemo(() => liveData?.controller || {}, [liveData?.controller]);
  const mode = liveData?.mode || "unknown";

  const simEnabled = !!sim.data?.enabled;

  const healthPills = useMemo(() => {
    const lastOk = liveData?.last_reading?.ok;
    const sensorTone = lastOk ? "ok" : "warn";
    const ctrlTone = ctrl?.enabled ? "ok" : "warn";
    const lightTone = lightOn ? "accent" : "neutral";
    return { sensorTone, ctrlTone, lightTone };
  }, [liveData?.last_reading?.ok, ctrl?.enabled, lightOn]);

  const chartData = useMemo(() => {
    const rows = readings.data?.rows || [];
    return rows.map((r) => ({
      t: r.ts_utc,
      lux: r.ok ? r.value : null,
      ok: r.ok,
    }));
  }, [readings.data]);

  const activeMin = thr?.min_lux ?? null;
  const activeMax = thr?.max_lux ?? null;

  // Initialise schedule draft on first load
  if (schedule.data && schedDraft === null) {
    setSchedDraft(schedule.data.windows);
  }

  async function safe(actionFn) {
    setUiError("");
    try {
      await actionFn();
    } catch (e) {
      setUiError(String(e?.message || e));
    }
  }

  // Controller toggle
  async function setControllerEnabled(next) {
    await safe(async () => {
      if (next) await api.controllerEnable();
      else await api.controllerDisable();
      await live.refresh();
    });
  }

  // Override toggle: tri-state ("off" | "auto" | "on")
  async function setOverrideMode(v) {
    await safe(async () => {
      if (v === "auto") {
        await api.overrideCancel();
        await live.refresh();
        return;
      }
      // v is "on" or "off" (force mode)
      setOverrideState(v);
      const mins = Math.max(1, parseInt(overrideMins || "10", 10));
      await api.override(v === "on", mins * 60);
      await live.refresh();
    });
  }

  // SIM toggle
  async function setSimEnabled(next) {
    await safe(async () => {
      if (next) await api.simEnable();
      else await api.simDisable();
      await sim.refresh();
      await live.refresh();
    });
  }

  async function doSimManual() {
    await safe(async () => {
      // auto-enable sim for dev UX
      if (!simEnabled) await api.simEnable();
      await api.simManual(Number(manualLux));
      await sim.refresh();
      await live.refresh();
    });
  }

  async function doSimPattern() {
    await safe(async () => {
      if (!simEnabled) await api.simEnable();
      await api.simPattern({
        type: patternType,
        baseline: Number(patternBaseline),
        amplitude: Number(patternAmplitude),
        period_s: Number(patternPeriod),
        noise: Number(patternNoise),
        step_low: 2500,
        step_high: 6500,
        step_period_s: 120,
        ramp_min: 2000,
        ramp_max: 7000,
        ramp_period_s: 600,
      });
      await sim.refresh();
      await live.refresh();
    });
  }

  async function saveSchedule() {
    setSaveMsg("");
    await safe(async () => {
      await api.schedulePut(schedDraft || []);
      setSaveMsg("Saved.");
      await schedule.refresh();
      await live.refresh();
    });
  }

  function updateSchedRow(idx, key, value) {
    const next = [...(schedDraft || [])];
    next[idx] = { ...next[idx], [key]: value };
    setSchedDraft(next);
  }

  function addSchedRow() {
    const next = [...(schedDraft || [])];
    next.push({
      id: `win_${Date.now()}`,
      start_time: "19:00",
      end_time: "21:00",
      min_lux: 3000,
      max_lux: 6000,
      enabled: true,
      priority: 0,
      label: "New Window",
    });
    setSchedDraft(next);
  }

  function removeSchedRow(idx) {
    const next = [...(schedDraft || [])];
    next.splice(idx, 1);
    setSchedDraft(next);
  }

  // Derive override UI mode from backend state
  // If override is active, reflect last selected overrideState ("on/off")
  const overrideMode = ctrl?.override_active ? overrideState : "auto";

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <div className="text-2xl font-bold text-primary">Spirulina Controller</div>
          <div className="text-sm text-text2">Live monitoring & control (FastAPI + Raspberry Pi)</div>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <Pill tone="primary">{mode.toUpperCase()}</Pill>
          <Pill tone={healthPills.sensorTone}>Sensor {liveData?.last_reading?.ok ? "OK" : "WARN"}</Pill>
          <Pill tone={healthPills.ctrlTone}>Controller {ctrl?.enabled ? "ENABLED" : "DISABLED"}</Pill>
          <Pill tone={healthPills.lightTone}>Light {lightOn ? "ON" : "OFF"}</Pill>
          {simEnabled && <Pill tone="warn">SIM MODE</Pill>}
          <Button variant="ghost" onClick={() => setSettingsPanelOpen(true)}>
            Settings
          </Button>
        </div>
      </div>

      {/* Action errors */}
      {uiError && (
        <div className="mt-4 rounded-xl2 border border-red-500/50 bg-red-900/30 p-3 text-sm text-red-400">
          {uiError}
        </div>
      )}

      {/* Polling errors */}
      {(live.error || readings.error || actions.error) && (
        <div className="mt-4 rounded-xl2 border border-red-500/50 bg-red-900/30 p-3 text-sm text-red-400">
          {live.error && <div>Live error: {String(live.error.message || live.error)}</div>}
          {readings.error && <div>Readings error: {String(readings.error.message || readings.error)}</div>}
          {actions.error && <div>Actions error: {String(actions.error.message || actions.error)}</div>}
        </div>
      )}

      {/* KPI cards */}
      <div className="mt-5 grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card
          title="Current Lux"
          right={<span className="text-xs text-text2">{fmtTime(liveData?.last_reading?.ts_utc)}</span>}
        >
          <div className="text-3xl font-bold text-primary">{fmtNum(luxNow, 0)}</div>
          <div className="text-sm text-text2">lux</div>
        </Card>

        <Card title="Average Lux (30s)">
          <div className="text-3xl font-bold text-primary">{fmtNum(avg30, 0)}</div>
          <div className="text-sm text-text2">6 x 5s samples</div>
        </Card>

        <Card title="Active Thresholds">
          <div className="text-sm text-text2">{thr?.window_label || "Outside control window"}</div>
          <div className="mt-2 flex gap-3">
            <div>
              <div className="text-xs text-text2">Min</div>
              <div className="text-xl font-bold text-primary">{activeMin ?? "-"}</div>
            </div>
            <div>
              <div className="text-xs text-text2">Max</div>
              <div className="text-xl font-bold text-primary">{activeMax ?? "-"}</div>
            </div>
          </div>
        </Card>

        <Card title="Decision">
          <div className="text-xl font-bold text-primary">{ctrl?.last_decision || "-"}</div>
          <div className="mt-1 text-sm text-text2">{ctrl?.last_reason || "-"}</div>
        </Card>
      </div>

      {/* Chart – full width */}
      <div className="mt-5">
        <Card
          title="Lux Trend (last 60 minutes)"
          right={
            <div className="flex items-center gap-2">
              <Button variant="ghost" onClick={() => readings.togglePause()}>
                {readings.paused ? "Resume" : "Pause"}
              </Button>
              <Button variant="ghost" onClick={() => readings.refresh()}>
                Refresh
              </Button>
            </div>
          }
        >
          {readings.paused && (
            <div className="mb-2">
              <Pill tone="warn">Auto-refresh paused</Pill>
            </div>
          )}
          <LuxChart chartData={chartData} activeMin={activeMin} activeMax={activeMax} />
          <div className="mt-3 text-xs text-text2">
            Shaded band shows active min/max thresholds (when inside a schedule window).
          </div>
        </Card>
      </div>

      {/* Controls – full width below chart */}
      <div className="mt-5">
        <Collapsible title="Controls" defaultOpen={true}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Controller toggle */}
            <div>
              <div className="text-sm font-semibold text-text2">Controller</div>
              <div className="text-xs text-text2 mt-0.5">Enable or disable automatic light control.</div>
              <div className="mt-2">
                <ToggleSwitch
                  checked={!!ctrl?.enabled}
                  onChange={setControllerEnabled}
                  labelOn="Controller ENABLED"
                  labelOff="Controller DISABLED"
                />
              </div>
            </div>

            {/* Override */}
            <div>
              <div className="text-sm font-semibold text-text2">Override Mode</div>
              <div className="mt-2">
                <TriToggle
                  value={overrideMode}
                  onChange={setOverrideMode}
                  labels={[
                    { value: "off", label: "FORCE OFF" },
                    { value: "auto", label: "AUTO" },
                    { value: "on", label: "FORCE ON" },
                  ]}
                />
              </div>

              <div className="mt-2">
                <div className="text-xs text-text2 mb-1">Override duration (minutes)</div>
                <Input value={overrideMins} onChange={setOverrideMins} placeholder="Minutes" type="number" />
              </div>

              <div className="mt-2 text-xs text-text2">
                {ctrl?.override_active ? "Override is active. Switch to AUTO to cancel." : "AUTO means controller governs normally."}
              </div>
            </div>

            {/* Simulation indicator */}
            <div>
              <div className="text-sm font-semibold text-text2">Simulation</div>
              <div className="flex items-center gap-2 mt-2">
                <Pill tone={simEnabled ? "warn" : "ok"}>{simEnabled ? "SIM ACTIVE" : "LIVE"}</Pill>
                <Button variant="ghost" onClick={() => setSimPanelOpen(true)}>
                  Configure
                </Button>
              </div>
            </div>
          </div>
        </Collapsible>
      </div>

      {/* Schedule + Events */}
      <div className="mt-5">
        <Collapsible
          title="Schedule & Events"
          defaultOpen={true}
          right={
            <div className="flex items-center gap-2">
              <Button variant="ghost" onClick={() => setSchedConfirm("defaults")}>Load Defaults</Button>
              <Button variant="danger" onClick={() => setSchedConfirm("clear")}>Clear</Button>
              <Button variant="ghost" onClick={addSchedRow}>Add</Button>
              <Button variant="accent" onClick={saveSchedule} disabled={!schedDraft || schedDraft.length === 0}>
                Save
              </Button>
            </div>
          }
        >
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              {schedConfirm && (
                <div className="mb-3 flex items-center gap-3 rounded-xl2 border border-yellow-500/50 bg-yellow-900/20 p-3 text-sm">
                  <span className="text-yellow-300">
                    {schedConfirm === "defaults"
                      ? "Replace all schedule windows with defaults?"
                      : "Remove all schedule windows?"}
                  </span>
                  <Button
                    variant={schedConfirm === "defaults" ? "accent" : "danger"}
                    onClick={async () => {
                      await safe(async () => {
                        if (schedConfirm === "defaults") {
                          const data = await api.scheduleDefaults();
                          setSchedDraft(data.windows);
                          await api.schedulePut(data.windows);
                        } else {
                          setSchedDraft([]);
                          await api.schedulePut([]);
                        }
                        await schedule.refresh();
                        await live.refresh();
                      });
                      setSchedConfirm(null);
                    }}
                  >
                    Confirm
                  </Button>
                  <Button variant="ghost" onClick={() => setSchedConfirm(null)}>Cancel</Button>
                </div>
              )}
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead className="text-text2">
                    <tr className="border-b border-line">
                      <th className="py-2 text-left">Label</th>
                      <th className="py-2 text-left">Start</th>
                      <th className="py-2 text-left">End</th>
                      <th className="py-2 text-left">Min</th>
                      <th className="py-2 text-left">Max</th>
                      <th className="py-2 text-left">Enabled</th>
                      <th className="py-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {(schedDraft || []).map((w, idx) => (
                      <tr key={w.id} className="border-b border-line">
                        <td className="py-2 pr-2">
                          <Input
                            value={w.label ?? ""}
                            onChange={(v) => updateSchedRow(idx, "label", v)}
                            placeholder="Label"
                          />
                        </td>
                        <td className="py-2 pr-2">
                          <Input
                            value={w.start_time}
                            onChange={(v) => updateSchedRow(idx, "start_time", v)}
                            placeholder="HH:MM"
                          />
                        </td>
                        <td className="py-2 pr-2">
                          <Input
                            value={w.end_time}
                            onChange={(v) => updateSchedRow(idx, "end_time", v)}
                            placeholder="HH:MM"
                          />
                        </td>
                        <td className="py-2 pr-2">
                          <Input
                            value={String(w.min_lux)}
                            onChange={(v) => updateSchedRow(idx, "min_lux", Number(v))}
                            type="number"
                          />
                        </td>
                        <td className="py-2 pr-2">
                          <Input
                            value={String(w.max_lux)}
                            onChange={(v) => updateSchedRow(idx, "max_lux", Number(v))}
                            type="number"
                          />
                        </td>
                        <td className="py-2 pr-2">
                          <select
                            className="w-full rounded-xl2 border border-line bg-surface px-3 py-2 text-sm text-text outline-none focus:border-primary"
                            value={String(!!w.enabled)}
                            onChange={(e) => updateSchedRow(idx, "enabled", e.target.value === "true")}
                          >
                            <option value="true">Yes</option>
                            <option value="false">No</option>
                          </select>
                        </td>
                        <td className="py-2 text-right">
                          <Button variant="danger" onClick={() => removeSchedRow(idx)}>Remove</Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {saveMsg && <div className="mt-2 text-xs text-text2">{saveMsg}</div>}
            </div>

            <div className="lg:col-span-1">
              <div className="text-sm font-semibold text-text2 mb-2">Recent Actions</div>
              <div className="space-y-2 max-h-[420px] overflow-auto pr-1">
                {(actions.data?.rows || []).slice(-40).reverse().map((a, i) => (
                  <div key={i} className="rounded-xl2 border border-line bg-surface p-3">
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-primary">{a.state ? "LIGHT ON" : "LIGHT OFF"}</div>
                      <div className="text-xs text-text2">{fmtTime(a.ts_utc)}</div>
                    </div>
                    <div className="mt-1 text-xs text-text2">{a.reason}</div>
                    <div className="mt-1 text-xs text-text2">
                      Avg: {fmtNum(a.avg_lux, 0)} | Min/Max: {a.min_lux ?? "-"} / {a.max_lux ?? "-"} | {a.window_label ?? "-"}
                    </div>
                  </div>
                ))}
                {(actions.data?.rows || []).length === 0 && (
                  <div className="text-sm text-text2">No actions recorded yet.</div>
                )}
              </div>
            </div>
          </div>
        </Collapsible>
      </div>

      <div className="mt-8 text-xs text-text2">
        Tip: Controller decisions are based on the 30-second average (6 x 5s). After changing lux, wait ~30s to see a decision.
      </div>

      {/* System info footer */}
      {sysInfo.data && (
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-text2">
          {sysInfo.data.cpu_temp_c != null && (
            <span>
              CPU{" "}
              <span className={
                sysInfo.data.cpu_temp_c >= 80 ? "text-red-400 font-semibold"
                : sysInfo.data.cpu_temp_c >= 70 ? "text-yellow-400 font-semibold"
                : "text-green-400"
              }>
                {sysInfo.data.cpu_temp_c.toFixed(1)}°C
              </span>
            </span>
          )}
          {sysInfo.data.cpu_percent != null && (
            <span>Load {sysInfo.data.cpu_percent.toFixed(0)}%</span>
          )}
          {sysInfo.data.uptime_seconds != null && (
            <span>Up {Math.floor(sysInfo.data.uptime_seconds / 3600)}h {Math.floor((sysInfo.data.uptime_seconds % 3600) / 60)}m</span>
          )}
          {sysInfo.data.ip_address && (
            <span>IP {sysInfo.data.ip_address}</span>
          )}
          {sysInfo.data.throttled_flag && (
            <Pill tone="bad">THROTTLED {sysInfo.data.throttled}</Pill>
          )}
        </div>
      )}

      <SettingsPanel
        open={settingsPanelOpen}
        onClose={() => setSettingsPanelOpen(false)}
      />

      <SimPanel
        open={simPanelOpen}
        onClose={() => setSimPanelOpen(false)}
        simEnabled={simEnabled}
        onSimToggle={setSimEnabled}
        manualLux={manualLux}
        setManualLux={setManualLux}
        onManualApply={doSimManual}
        patternType={patternType}
        setPatternType={setPatternType}
        onPatternApply={doSimPattern}
        patternBaseline={patternBaseline}
        setPatternBaseline={setPatternBaseline}
        patternAmplitude={patternAmplitude}
        setPatternAmplitude={setPatternAmplitude}
        patternPeriod={patternPeriod}
        setPatternPeriod={setPatternPeriod}
        patternNoise={patternNoise}
        setPatternNoise={setPatternNoise}
        simData={sim.data}
      />
    </div>
  );
}
