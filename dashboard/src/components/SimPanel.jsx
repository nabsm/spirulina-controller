import { useState } from "react";
import { Drawer, Button, Input, Select, ToggleSwitch } from "./ui.jsx";

export default function SimPanel({
  open,
  onClose,
  simEnabled,
  onSimToggle,
  manualLux,
  setManualLux,
  onManualApply,
  patternType,
  setPatternType,
  onPatternApply,
  patternBaseline,
  setPatternBaseline,
  patternAmplitude,
  setPatternAmplitude,
  patternPeriod,
  setPatternPeriod,
  patternNoise,
  setPatternNoise,
  simData,
}) {
  const [confirming, setConfirming] = useState(false);

  function handleToggleClick() {
    setConfirming(true);
  }

  function handleConfirm() {
    setConfirming(false);
    onSimToggle(!simEnabled);
  }

  function handleCancel() {
    setConfirming(false);
  }

  return (
    <Drawer open={open} onClose={onClose} title="Simulation Settings">
      {/* Sim toggle with confirmation */}
      <div className="text-sm font-semibold text-text">Sensor Mode</div>
      <div className="mt-2">
        <ToggleSwitch
          checked={simEnabled}
          onChange={handleToggleClick}
          labelOn="SIM ENABLED"
          labelOff="SIM DISABLED (LIVE)"
        />
      </div>

      {confirming && (
        <div className="mt-2 rounded-xl2 border border-yellow-500/50 bg-yellow-900/30 p-3">
          <div className="text-sm font-semibold text-yellow-400">
            {simEnabled
              ? "Switch back to LIVE sensor data?"
              : "Switch to SIMULATED sensor data?"}
          </div>
          <div className="mt-2 flex gap-2">
            <Button variant="accent" onClick={handleConfirm}>
              Confirm
            </Button>
            <Button variant="ghost" onClick={handleCancel}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Manual lux */}
      <div className="mt-4 border-t border-line pt-4">
        <div className="text-sm font-semibold text-text">Manual Lux</div>
        <div className="mt-1 text-xs text-text2">Set a fixed lux value for the simulated sensor.</div>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-text2">Lux value</label>
            <Input value={manualLux} onChange={setManualLux} placeholder="Lux" type="number" />
          </div>
          <div className="flex items-end">
            <Button variant="ghost" onClick={onManualApply}>
              Set Manual
            </Button>
          </div>
        </div>
      </div>

      {/* Pattern config */}
      <div className="mt-4 border-t border-line pt-4">
        <div className="text-sm font-semibold text-text">Pattern</div>
        <div className="mt-1 text-xs text-text2">Generate a repeating lux pattern for testing.</div>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-text2">Pattern type</label>
            <Select
              value={patternType}
              onChange={setPatternType}
              options={[
                { value: "sine", label: "Sine" },
                { value: "step", label: "Step" },
                { value: "ramp", label: "Ramp" },
                { value: "random", label: "Random" },
              ]}
            />
          </div>
          <div className="flex items-end">
            <Button variant="ghost" onClick={onPatternApply}>
              Apply Pattern
            </Button>
          </div>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-text2">Baseline (lux)</label>
            <Input value={patternBaseline} onChange={setPatternBaseline} placeholder="4000" type="number" />
          </div>
          <div>
            <label className="text-xs text-text2">Amplitude (lux)</label>
            <Input value={patternAmplitude} onChange={setPatternAmplitude} placeholder="2000" type="number" />
          </div>
          <div>
            <label className="text-xs text-text2">Period (seconds)</label>
            <Input value={patternPeriod} onChange={setPatternPeriod} placeholder="600" type="number" />
          </div>
          <div>
            <label className="text-xs text-text2">Noise (lux)</label>
            <Input value={patternNoise} onChange={setPatternNoise} placeholder="80" type="number" />
          </div>
        </div>
      </div>

      {/* Status */}
      <div className="mt-4 border-t border-line pt-4">
        <div className="text-xs text-text2">
          Sim status: {simEnabled ? "enabled" : "disabled"} &bull; Mode: {simData?.pattern?.type || "-"}
        </div>
      </div>
    </Drawer>
  );
}
