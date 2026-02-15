import { useState, useEffect } from "react";
import { api } from "../lib/api.js";
import { Drawer, Card, Button, Input, Select, Pill, ToggleSwitch } from "./ui.jsx";

const RESTART_KEYS = new Set([
  "sensor_mode", "actuator_mode", "rs485_port", "rs485_baudrate",
  "rs485_slave_id", "lux_functioncode", "lux_register_address",
  "lux_register_count", "lux_scale", "sqlite_path",
]);

export default function SettingsPanel({ open, onClose }) {
  const [original, setOriginal] = useState(null);
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");
  const [error, setError] = useState("");
  const [discovering, setDiscovering] = useState(false);
  const [devices, setDevices] = useState([]);

  // Load settings when panel opens
  useEffect(() => {
    if (open) {
      loadSettings();
      setDevices([]);
    }
  }, [open]);

  async function loadSettings() {
    setError("");
    try {
      const res = await api.settingsGet();
      setOriginal(res.settings);
      setDraft({ ...res.settings });
    } catch (e) {
      setError(String(e?.message || e));
    }
  }

  function update(key, value) {
    setDraft((prev) => ({ ...prev, [key]: value }));
    setSaveMsg("");
  }

  function hasChanges() {
    if (!original || !draft) return false;
    return Object.keys(draft).some((k) => String(draft[k]) !== String(original[k]));
  }

  function changedKeys() {
    if (!original || !draft) return [];
    return Object.keys(draft).filter((k) => String(draft[k]) !== String(original[k]));
  }

  function hasRestartChanges() {
    return changedKeys().some((k) => RESTART_KEYS.has(k));
  }

  async function save() {
    setSaving(true);
    setSaveMsg("");
    setError("");
    try {
      const updates = {};
      for (const k of changedKeys()) {
        updates[k] = draft[k];
      }
      const res = await api.settingsUpdate(updates);
      setSaveMsg(
        `Saved ${res.updated_keys.length} setting(s). ` +
        (res.runtime_applied.length < res.updated_keys.length
          ? "Some changes require a restart."
          : "All changes applied immediately.")
      );
      setOriginal({ ...draft });
    } catch (e) {
      setError(String(e?.message || e));
    } finally {
      setSaving(false);
    }
  }

  async function discover() {
    setDiscovering(true);
    setError("");
    try {
      const res = await api.discoverSonoff();
      setDevices(res.devices || []);
      if ((res.devices || []).length === 0) {
        setSaveMsg("No Sonoff devices found on the network.");
      }
    } catch (e) {
      setError(String(e?.message || e));
    } finally {
      setDiscovering(false);
    }
  }

  function selectDevice(dev) {
    update("sonoff_ip", dev.ip || "");
    update("sonoff_port", dev.port || 8081);
    update("sonoff_device_id", dev.id || "");
    setDraft((prev) => ({
      ...prev,
      sonoff_ip: dev.ip || "",
      sonoff_port: dev.port || 8081,
      sonoff_device_id: dev.id || "",
    }));
    setSaveMsg(`Selected device ${dev.id} at ${dev.ip}:${dev.port}. Click Save to apply.`);
  }

  if (!draft) {
    return (
      <Drawer open={open} onClose={onClose} title="Settings">
        <div className="text-sm text-text2">Loading settings...</div>
        {error && <div className="mt-2 text-sm text-red-400">{error}</div>}
      </Drawer>
    );
  }

  return (
    <Drawer open={open} onClose={onClose} title="Settings">
      {error && (
        <div className="mb-3 rounded-xl2 border border-red-500/50 bg-red-900/30 p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* General */}
      <Section title="General">
        <Field label="App Name">
          <Input value={draft.app_name || ""} onChange={(v) => update("app_name", v)} />
        </Field>
        <Field label="Timezone">
          <Input value={draft.timezone || ""} onChange={(v) => update("timezone", v)} />
        </Field>
      </Section>

      {/* Control */}
      <Section title="Control">
        <div className="grid grid-cols-2 gap-2">
          <Field label="Sample Seconds">
            <Input
              value={String(draft.sample_seconds ?? "")}
              onChange={(v) => update("sample_seconds", v)}
              type="number"
            />
          </Field>
          <Field label="Avg Samples">
            <Input
              value={String(draft.avg_samples ?? "")}
              onChange={(v) => update("avg_samples", v)}
              type="number"
            />
          </Field>
          <Field label="Hysteresis Lux">
            <Input
              value={String(draft.hysteresis_lux ?? "")}
              onChange={(v) => update("hysteresis_lux", v)}
              type="number"
            />
          </Field>
          <Field label="Min Switch Interval (s)">
            <Input
              value={String(draft.min_switch_interval_seconds ?? "")}
              onChange={(v) => update("min_switch_interval_seconds", v)}
              type="number"
            />
          </Field>
          <Field label="Default Min Lux">
            <Input
              value={String(draft.default_min_lux ?? "")}
              onChange={(v) => update("default_min_lux", v)}
              type="number"
            />
          </Field>
          <Field label="Default Max Lux">
            <Input
              value={String(draft.default_max_lux ?? "")}
              onChange={(v) => update("default_max_lux", v)}
              type="number"
            />
          </Field>
        </div>
        <Field label="Fail-Safe Light State">
          <ToggleSwitch
            checked={!!draft.fail_safe_light_state}
            onChange={(v) => update("fail_safe_light_state", v)}
            labelOn="ON (lights on if sensor fails)"
            labelOff="OFF (lights off if sensor fails)"
          />
        </Field>
      </Section>

      {/* Sensor */}
      <Section title="Sensor">
        <Field label="Sensor Mode" badge={changedKeys().includes("sensor_mode") ? "restart required" : null}>
          <Select
            value={draft.sensor_mode || "sim"}
            onChange={(v) => update("sensor_mode", v)}
            options={[
              { value: "sim", label: "Simulated" },
              { value: "rs485", label: "RS485 Modbus RTU" },
            ]}
          />
        </Field>
        {draft.sensor_mode === "rs485" && (
          <div className="mt-2 grid grid-cols-2 gap-2">
            <Field label="RS485 Port" badge="restart required">
              <Input value={draft.rs485_port || ""} onChange={(v) => update("rs485_port", v)} />
            </Field>
            <Field label="Baudrate" badge="restart required">
              <Input
                value={String(draft.rs485_baudrate ?? "")}
                onChange={(v) => update("rs485_baudrate", v)}
                type="number"
              />
            </Field>
            <Field label="Slave ID" badge="restart required">
              <Input
                value={String(draft.rs485_slave_id ?? "")}
                onChange={(v) => update("rs485_slave_id", v)}
                type="number"
              />
            </Field>
            <Field label="Function Code" badge="restart required">
              <Input
                value={String(draft.lux_functioncode ?? "")}
                onChange={(v) => update("lux_functioncode", v)}
                type="number"
              />
            </Field>
            <Field label="Register Address" badge="restart required">
              <Input
                value={String(draft.lux_register_address ?? "")}
                onChange={(v) => update("lux_register_address", v)}
                type="number"
              />
            </Field>
            <Field label="Register Count" badge="restart required">
              <Input
                value={String(draft.lux_register_count ?? "")}
                onChange={(v) => update("lux_register_count", v)}
                type="number"
              />
            </Field>
            <Field label="Lux Scale" badge="restart required">
              <Input
                value={String(draft.lux_scale ?? "")}
                onChange={(v) => update("lux_scale", v)}
                type="number"
              />
            </Field>
          </div>
        )}
      </Section>

      {/* Actuator */}
      <Section title="Actuator">
        <Field label="Actuator Mode" badge={changedKeys().includes("actuator_mode") ? "restart required" : null}>
          <Select
            value={draft.actuator_mode || "sim"}
            onChange={(v) => update("actuator_mode", v)}
            options={[
              { value: "sim", label: "Simulated" },
              { value: "sonoff", label: "Sonoff BASICR3" },
            ]}
          />
        </Field>
        {draft.actuator_mode === "sonoff" && (
          <>
            <div className="mt-2 grid grid-cols-2 gap-2">
              <Field label="Sonoff IP">
                <Input value={draft.sonoff_ip || ""} onChange={(v) => update("sonoff_ip", v)} />
              </Field>
              <Field label="Sonoff Port">
                <Input
                  value={String(draft.sonoff_port ?? "")}
                  onChange={(v) => update("sonoff_port", v)}
                  type="number"
                />
              </Field>
              <Field label="Device ID">
                <Input value={draft.sonoff_device_id || ""} onChange={(v) => update("sonoff_device_id", v)} />
              </Field>
              <Field label="Timeout (s)">
                <Input
                  value={String(draft.sonoff_timeout_seconds ?? "")}
                  onChange={(v) => update("sonoff_timeout_seconds", v)}
                  type="number"
                />
              </Field>
            </div>

            <div className="mt-3">
              <Button variant="ghost" onClick={discover} disabled={discovering}>
                {discovering ? "Scanning..." : "Discover Sonoff Devices"}
              </Button>
            </div>

            {devices.length > 0 && (
              <div className="mt-2 space-y-2">
                <div className="text-xs text-text2">Found {devices.length} device(s). Click to auto-fill:</div>
                {devices.map((dev, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => selectDevice(dev)}
                    className="w-full text-left rounded-xl2 border border-line bg-surface p-3 hover:bg-surfaceHover hover:shadow-soft transition-all"
                  >
                    <div className="text-sm font-semibold text-primary">{dev.id || "Unknown ID"}</div>
                    <div className="text-xs text-text2">
                      {dev.ip}:{dev.port} &bull; {dev.hostname || ""} &bull; {dev.type || ""}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </Section>

      {/* Storage */}
      <Section title="Storage">
        <Field label="SQLite Path" badge="restart required">
          <Input value={draft.sqlite_path || ""} onChange={(v) => update("sqlite_path", v)} />
        </Field>
      </Section>

      {/* Save */}
      <div className="mt-4 border-t border-line pt-4">
        {hasRestartChanges() && (
          <div className="mb-3 rounded-xl2 border border-yellow-500/50 bg-yellow-900/20 p-3 text-sm text-yellow-300">
            Some changes require a restart to take effect.
          </div>
        )}
        <div className="flex items-center gap-3">
          <Button variant="accent" onClick={save} disabled={!hasChanges() || saving}>
            {saving ? "Saving..." : "Save Settings"}
          </Button>
          {hasChanges() && (
            <span className="text-xs text-text2">{changedKeys().length} change(s)</span>
          )}
        </div>
        {saveMsg && <div className="mt-2 text-xs text-text2">{saveMsg}</div>}
      </div>
    </Drawer>
  );
}

function Section({ title, children }) {
  return (
    <div className="mt-4 border-t border-line pt-4 first:mt-0 first:border-t-0 first:pt-0">
      <div className="text-sm font-semibold text-text">{title}</div>
      <div className="mt-2">{children}</div>
    </div>
  );
}

function Field({ label, badge, children }) {
  return (
    <div className="mt-2">
      <div className="flex items-center gap-2">
        <label className="text-xs text-text2">{label}</label>
        {badge && <Pill tone="warn">{badge}</Pill>}
      </div>
      <div className="mt-1">{children}</div>
    </div>
  );
}
